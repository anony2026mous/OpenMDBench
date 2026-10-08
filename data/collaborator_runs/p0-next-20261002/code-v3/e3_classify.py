"""Freeze balanced observed events, then classify through two no-thinking vLLMs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import random
import re
import time
import numpy as np
import requests
from common import read, write, digest


SYSTEM = ('Classify an observed transport contact as feint or real. A real threat '
          'makes persistent progress toward the protected port at (1,18). Feints '
          'hold position or drift laterally without persistent port approach. '
          'Do not infer the answer from contact IDs or priors. Use only the supplied '
          'observable motion history. Return JSON only: '
          '{"label":"feint" or "real","p_real":number from 0 to 1}.')


def freeze(folder, out, per_class):
    candidates, used, proofs = [], set(), []
    # Prefer one trajectory per contact-time window; no duplicate arms/ticks.
    for path in sorted(folder.glob("*/frames.json")):
        meta = read(path)
        audit = read(path.with_name("audit.json"))
        if not audit.get("eligible") or digest(path) != audit["frame_file_sha256"]:
            raise ValueError(f"Unverified frames: {path}")
        proofs.append({"path": str(path), "sha256": digest(path), **audit})
        contacts = {}
        for frame in meta["frames"]:
            contacts.setdefault(frame["contact"], []).append(frame)
        for cid, frames in sorted(contacts.items()):
            for index in range(0, len(frames) - 2, 3):
                window = frames[index:index+3]
                keys = {(meta["seed"], cid, r["tick"]) for r in window}
                if used.intersection(keys) or any(r["heading"] is None for r in window):
                    continue
                used.update(keys)
                positions = [r["position"] for r in window]
                headings = [r["heading"] for r in window]
                last = window[-1]
                text = ["Anonymous contact. Port at (1,18). Observed motion history:"]
                for r in window:
                    x, y = r["position"]
                    dx, dy = r["heading"]
                    closing = dx * (1 - x) + dy * (18 - y)
                    description = "holding" if dx == dy == 0 else (
                        "closing toward the port" if closing > 0 else "lateral or moving away")
                    text.append(f"t={r['tick']}: position=({x},{y}); observed delta=({dx},{dy}); {description}.")
                text.append("Local unit grid snapshots (4 denotes transport; role is not encoded): "
                            + json.dumps(last["local_grid"], separators=(",", ":")))
                token = f"{meta['seed']}:{cid}:{[r['tick'] for r in window]}"
                candidates.append({"id": hashlib.sha256(token.encode()).hexdigest()[:20],
                                   "seed": meta["seed"], "source_contact_offline": cid,
                                   "source_batch": meta.get("source_batch", "P3a"),
                                   "gold_real": last["gold_real"],
                                   "numeric": {"positions": positions, "headings": headings,
                                               "local_grid": last["local_grid"]},
                                   "prompt": "\n".join(text), "ticks": [r["tick"] for r in window]})
    classes = {v: [r for r in candidates if r["gold_real"] == v] for v in [False, True]}
    counts = {"feint": len(classes[False]), "real": len(classes[True])}
    # A balanced reduced dataset is still reported, never duplicated to reach 400.
    n = min(per_class, *counts.values())
    if n < 1:
        write(out / "dataset_audit.json", {"counts": counts, "eligible": False, "reason": "No balanced events"})
        raise ValueError(f"No balanced semantic events: {counts}")
    rng = random.Random(20261001)
    selected = []
    for v in [False, True]:
        rng.shuffle(classes[v])
        selected += classes[v][:n]
    rng.shuffle(selected)
    if len({r["id"] for r in selected}) != len(selected):
        raise ValueError("Duplicate events")
    write(out / "dataset.json", selected)
    audit = {"schema": "p0-e3-controlled-events@1", "available_counts": counts,
             "requested_per_class": per_class, "actual_per_class": n,
             "requested_budget_met": n == per_class,
             "full_400_event_budget_met": n == 200 and per_class == 200,
             "seed_clusters": sorted({r["seed"] for r in selected}),
             "window": "3 observed frames, disjoint for each seed/contact",
             "source": "Released P1/P3a trajectories; replay validation levels recorded separately",
             "truth_boundary": "Offline labels/IDs are not included in LLM requests",
             "engine_changes": False, "provenance": proofs,
             "dataset_sha256": digest(out / "dataset.json"),
             "classifier_protocol": SYSTEM,
             "primary_rule": "Port-projection of mean observed heading; ties p_real=.5",
             "secondary_control": "Snapshot-only baseline p_real=.5; not substituted for primary rule",
             "frozen_before_llm_calls": True}
    write(out / "dataset_audit.json", audit)
    return selected


def rule(row):
    headings = np.array(row["numeric"]["headings"], float)
    x, y = row["numeric"]["positions"][-1]
    dx, dy = headings.mean(axis=0)
    projection = dx * (1 - x) + dy * (18 - y)
    return 1.0 if projection > 0 else .0 if projection < 0 else .5


def auc_matrix(gold, scores, clusters):
    seeds = sorted(set(clusters))
    matrix = np.zeros((len(seeds), len(seeds)))
    positive, negative = [], []
    for seed in seeds:
        positive.append(np.sum((clusters == seed) & gold))
        negative.append(np.sum((clusters == seed) & ~gold))
    for i, s in enumerate(seeds):
        p = scores[(clusters == s) & gold]
        for j, t in enumerate(seeds):
            n = scores[(clusters == t) & ~gold]
            matrix[i, j] = np.sum(p[:, None] > n[None, :]) + .5 * np.sum(p[:, None] == n[None, :])
    return seeds, matrix, np.array(positive), np.array(negative)


def metrics(rows, score_key, valid_only=False):
    original_count = len(rows)
    if valid_only:
        rows = [r for r in rows if r[score_key] is not None]
    if not rows:
        return {"n": 0, "auc": None, "accuracy": None}
    gold = np.array([r["gold_real"] for r in rows], bool)
    score = np.array([r[score_key] if r[score_key] is not None else .5 for r in rows])
    correct = np.array([r[score_key] is not None and (r[score_key] > .5) == r["gold_real"] for r in rows])
    clusters = np.array([r["seed"] for r in rows])
    seeds, pairwin, pos, neg = auc_matrix(gold, score, clusters)
    count = np.array([np.sum(clusters == s) for s in seeds])
    wins = np.array([np.sum(correct[clusters == s]) for s in seeds])
    rng = np.random.default_rng(20261001)
    weights = rng.multinomial(len(seeds), np.ones(len(seeds))/len(seeds), size=20000)
    accuracy_boot = weights @ wins / (weights @ count)
    denominator = (weights @ pos) * (weights @ neg)
    numerator = np.einsum("bi,ij,bj->b", weights, pairwin, weights)
    auc_boot = numerator[denominator > 0] / denominator[denominator > 0]
    return {"n": len(rows), "total_attempts": original_count, "n_seed_clusters": len(seeds),
            "accuracy": float(correct.mean()), "accuracy_ci95": np.quantile(accuracy_boot, [.025,.975]).tolist(),
            "auc": float(pairwin.sum()/(pos.sum()*neg.sum())) if pos.sum()*neg.sum() else None,
            "auc_ci95": np.quantile(auc_boot, [.025,.975]).tolist() if len(auc_boot) else None,
            "bootstrap": "20,000 seed-cluster resamples, event-weighted within resampled clusters"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--frames", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--endpoints", nargs="+", required=True)
    p.add_argument("--model", default="Qwen3.8-27B")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--per-class", type=int, default=200)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    endpoint_models = {}
    for endpoint in a.endpoints:
        response = requests.get(endpoint.rstrip("/") + "/models", timeout=20)
        response.raise_for_status()
        body = response.json()
        if a.model not in [m["id"] for m in body.get("data", [])]:
            raise ValueError(f"Requested model absent at {endpoint}")
        endpoint_models[endpoint] = body
    write(a.output / "endpoint_models.json", endpoint_models)
    if (a.output / "dataset.json").exists():
        events = read(a.output / "dataset.json")
        if digest(a.output / "dataset.json") != read(a.output / "dataset_audit.json")["dataset_sha256"]:
            raise ValueError("Frozen dataset changed")
    else:
        events = freeze(a.frames, a.output, a.per_class)
    def call(index, row):
        path = a.output / "responses" / f"{row['id']}.json"
        if path.exists():
            cached = read(path)
            if cached["model"] != a.model or cached["prompt_sha256"] != hashlib.sha256(row["prompt"].encode()).hexdigest():
                raise ValueError("Resume configuration mismatch")
            return cached
        endpoint = a.endpoints[index % len(a.endpoints)].rstrip("/")
        start = time.monotonic()
        result = {"id": row["id"], "seed": row["seed"], "gold_real": row["gold_real"],
                  "source_batch": row["source_batch"],
                  "rule_p_real": rule(row), "snapshot_p_real": .5, "llm_p_real": None,
                  "model": a.model, "endpoint": endpoint,
                  "prompt_sha256": hashlib.sha256(row["prompt"].encode()).hexdigest()}
        payload = {"model": a.model, "temperature": 0, "max_tokens": 128,
                   "chat_template_kwargs": {"enable_thinking": False},
                   "messages": [{"role": "system", "content": SYSTEM},
                                {"role": "user", "content": row["prompt"]}]}
        try:
            response = requests.post(endpoint + "/chat/completions", json=payload, timeout=120)
            response.raise_for_status()
            raw = response.json()
            if raw.get("model") != a.model:
                raise ValueError("Returned model does not match frozen served model ID")
            content = raw["choices"][0]["message"].get("content") or ""
            result.update(raw_response=raw, raw_content=content, request=payload)
            match = re.search(r"\{.*\}", content, re.S)
            parsed = json.loads(match.group(0) if match else content)
            probability = float(parsed["p_real"])
            label = parsed["label"]
            if not np.isfinite(probability) or not 0 <= probability <= 1 or label not in ["real", "feint"]:
                raise ValueError("Invalid classifier schema")
            if (probability > .5) != (label == "real"):
                raise ValueError("Label/probability inconsistent; threshold .5 belongs to feint")
            result["llm_p_real"] = probability
        except Exception as error:
            result["error"] = f"{type(error).__name__}: {error}"
        result["elapsed_seconds"] = time.monotonic() - start
        write(path, result)
        return result
    results = []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(call, i, row) for i, row in enumerate(events)]
        for f in as_completed(futures):
            results.append(f.result())
            if len(results) % 25 == 0:
                print(json.dumps({"complete": len(results), "total": len(events)}, ensure_ascii=False), flush=True)
    results.sort(key=lambda r: r["id"])
    rule_stats = metrics(results, "rule_p_real")
    llm_stats = metrics(results, "llm_p_real")
    valid_auc = metrics(results, "llm_p_real", valid_only=True)
    audit = read(a.output / "dataset_audit.json")
    gate = rule_stats["accuracy"] <= .60 and llm_stats["accuracy"] >= .85
    errors = sum(r["llm_p_real"] is None for r in results)
    summary = {"schema": "p0-e3-classifier@1", "dataset_audit": audit,
               "rule": rule_stats, "llm_all_attempts_accuracy": llm_stats,
               "llm_valid_response_auc": valid_auc,
               "snapshot_only_control": metrics(results, "snapshot_p_real"),
               "parse_or_service_errors": errors,
               "source_batch_strata": {batch: {"rule": metrics([r for r in results if r["source_batch"] == batch], "rule_p_real"),
                                                "llm": metrics([r for r in results if r["source_batch"] == batch], "llm_p_real")}
                                       for batch in sorted({r["source_batch"] for r in results})},
               "D1_point_thresholds_met": gate,
               "full_requested_protocol_complete": audit["full_400_event_budget_met"] and errors == 0,
               "D1_full_protocol_pass": gate and audit["full_400_event_budget_met"] and errors == 0,
               "D1_CI_strict_pass": rule_stats["accuracy_ci95"][1] <= .60 and llm_stats["accuracy_ci95"][0] >= .85,
               "limitations": ["Controlled classification only, not online autonomous identification",
                               "Numeric motion and semantic paraphrase share observable information",
                               "Snapshot-only control does not replace the primary kinematic rule",
                               "Repeated contacts clustered by seed; 400 events are not 400 independent simulations",
                               "If fewer than 400 valid disjoint events exist, result is a reduced-sample pilot",
                               "Invalid outputs count as accuracy failures; report AUC on valid outputs if any fail"]}
    write(a.output / "predictions.json", results)
    write(a.output / "analysis.json", summary)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 4))
    for key, label in [("rule_p_real", "Kinematic rule"), ("llm_p_real", "Qwen3.8-27B")]:
        valid = [r for r in results if r[key] is not None]
        y = np.array([r["gold_real"] for r in valid], bool)
        scores = np.array([r[key] for r in valid])
        thresholds = [float("inf"), *sorted(set(scores), reverse=True), -float("inf")]
        fpr = [float(np.sum((scores >= t) & ~y) / np.sum(~y)) for t in thresholds]
        tpr = [float(np.sum((scores >= t) & y) / np.sum(y)) for t in thresholds]
        ax.plot(fpr, tpr, label=label)
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey")
    ax.set(xlabel="False-positive rate", ylabel="True-positive rate",
           title=f"Controlled observed-event ROC (n={len(results)})", xlim=(0, 1), ylim=(0, 1.02))
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(a.output / "roc.png", dpi=200)
    fig.savefig(a.output / "roc.svg")
    lines = ["# P0 E3：受控诱饵判别实测", "", f"可用候选事件：{audit['available_counts']}；实际每类 {audit['actual_per_class']} 个；{len(audit['seed_clusters'])} 个 seed 聚类。",
             "", "真值只用于离线核算。LLM 输入不含角色标签或原始接触 ID；关闭 Qwen 思考，temperature=0。语义描述由真实可观测运动构造，而非真值生成。", "",
             "|判别器|正确率|seed-cluster 95% CI|ROC-AUC|", "|---|---:|---|---:|"]
    for name, stats in [("运动几何规则（主对照）", rule_stats), ("LLM", llm_stats),
                        ("仅瞬时快照（次要对照）", summary["snapshot_only_control"])]:
        lines.append(f"|{name}|{stats['accuracy']:.3%}|{stats['accuracy_ci95']}|{stats['auc']}|")
    lines += ["", f"服务/解析错误：{errors}。D1 点阈值是否同时达到：{gate}；完整请求协议通过：{summary['D1_full_protocol_pass']}。",
              "", "## 解读", "", "如果几何规则也能准确识别，表明这些语义线索可数值压缩，而不是 LLM 独占的信息优势。不能选用较弱的瞬时快照规则替代主对照来宣称 D1 通过。即使 LLM 判别良好，也不等于在线自主识骗或混合架构胜出。",
              "", "样本不足时保留全部真实候选及平衡子样本，不复制事件凑数；此时结果为缩减样本试验。完整数据、原始模型响应、源轨迹哈希和精确重放验证见同目录 JSON。"]
    (a.output / "report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "dataset_audit"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
