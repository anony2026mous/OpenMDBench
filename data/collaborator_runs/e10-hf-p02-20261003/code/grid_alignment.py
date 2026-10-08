"""E10 grid-plane-only reanalysis; no engine edits, no new LLM calls.

This is retrospective reuse of an already inspected confirmation set, not a
new independent confirmation and not the full executor-observation channel.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

import numpy as np


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plane(rows):
    x = np.asarray([r["local_features"] for r in rows], dtype=float)
    if x.ndim != 2 or x.shape[1] != 84 or not np.isfinite(x).all():
        raise ValueError("Unexpected original local-feature layout")
    # Identical normalization/centering to get_local_observation -> actor plane.
    return x[:, :64]


def balanced(y, p):
    y = np.asarray(y, bool)
    if not y.any() or y.all():
        raise ValueError("Both classes required")
    correct = (np.asarray(p) > .5) == y
    return float((correct[y].mean() + correct[~y].mean()) / 2)


def transform(x, square):
    return np.c_[x, x*x] if square else np.asarray(x)


def train(rows, channel):
    x = plane(rows)
    y = np.asarray([r["gold_real"] for r in rows], bool)
    seeds = sorted({r["seed"] for r in rows})
    if len(rows) < 80 or len(seeds) < 20:
        raise ValueError("Development coverage insufficient")
    random.Random(20261002).shuffle(seeds)
    folds = {s: i % 4 for i, s in enumerate(seeds)}
    candidates = []
    for square in (False, True):
        z = transform(x, square)
        for lam in (.01, .1, 1., 10.):
            scores = []
            for k in range(4):
                tr = np.array([folds[r["seed"]] != k for r in rows])
                te = ~tr
                model = channel.fit(z[tr], y[tr], lam, False)
                scores.append(balanced(y[te], channel.predict(model, z[te])))
            candidates.append({"square": square, "lambda": lam, "balanced_CV": float(np.mean(scores))})
    best = min(candidates, key=lambda v: (-v["balanced_CV"], v["square"], -v["lambda"]))
    return {"model": channel.fit(transform(x, best["square"]), y, best["lambda"], False),
            "selection": best, "development_CV": candidates,
            "n_events": len(rows), "n_seed_clusters": len(seeds)}


def bootstrap_metrics(rows, key, weights, clusters):
    y = np.array([r["gold_real"] for r in rows], bool)
    p = np.array([.5 if r[key] is None else r[key] for r in rows], float)
    valid = np.array([r[key] is not None for r in rows])
    correct = valid & ((p > .5) == y)
    # Each seed is sampled once as a cluster; all its events inherit multiplicity.
    ew = weights[:, clusters]
    npos = ew[:, y].sum(1)
    nneg = ew[:, ~y].sum(1)
    ok = (npos > 0) & (nneg > 0)
    acc = (ew @ correct.astype(float)) / ew.sum(1)
    ba = .5*((ew[:, y] @ correct[y].astype(float))/np.maximum(npos, 1)
             + (ew[:, ~y] @ correct[~y].astype(float))/np.maximum(nneg, 1))
    order = np.argsort(p, kind="stable")
    scores = p[order]
    starts = np.r_[0, np.flatnonzero(np.diff(scores)) + 1]
    pos = np.add.reduceat(ew[:, order]*y[order], starts, axis=1)
    neg = np.add.reduceat(ew[:, order]*(~y[order]), starts, axis=1)
    wins = (pos*(np.cumsum(neg, axis=1)-neg+.5*neg)).sum(1)
    aucs = wins[ok]/(npos[ok]*nneg[ok])
    point = float((np.sum(p[y, None] > p[None, ~y]) + .5*np.sum(p[y, None] == p[None, ~y]))/(y.sum()*(~y).sum()))
    return {"n": len(rows), "accuracy": float(correct.mean()),
            "balanced_accuracy": float(.5*(correct[y].mean()+correct[~y].mean())),
            "accuracy_ci95": np.quantile(acc, [.025, .975]).tolist(),
            "balanced_accuracy_ci95": np.quantile(ba[ok], [.025, .975]).tolist(),
            "auc": point, "auc_ci95": np.quantile(aucs, [.025, .975]).tolist(),
            "n_errors": int((~valid).sum())}, ba, ok


def roc(rows, key):
    y = np.array([r["gold_real"] for r in rows], bool)
    p = np.array([.5 if r[key] is None else r[key] for r in rows], float)
    return [{"threshold": float(t), "fpr": float(np.mean(p[~y] > t)),
             "tpr": float(np.mean(p[y] > t))} for t in sorted(set([-.000001, 1.000001, *p]), reverse=True)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    if out.exists():
        raise ValueError("Existing batch must not be overwritten")
    out.mkdir(parents=True)
    code = args.root / "code-complex"
    sys.path.insert(0, str(code))
    spec = importlib.util.spec_from_file_location("e10_channel", code / "channel_experiment.py")
    channel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(channel)
    sources = {
        "medium": (args.root/"E3-channel-v3", args.root/"E3-format-engineering-full/results.json", "p_real"),
        "complex": (args.root/"E3-channel-complex", args.root/"E3-channel-complex/channel_predictions.json", "llm_p_real")}
    frozen = {}
    for tier, (source, llm_file, _) in sources.items():
        paths = [source/"development_events.json", source/"classification/dataset.json", source/"protocol.json", llm_file]
        frozen[tier] = [{"path": str(p), "sha256": sha(p)} for p in paths]
    manifest = {"kind": "retrospective-feature-restriction-reanalysis-not-independent-confirmation",
                "protocol": "E10-grid-plane-p01", "source_inputs": frozen,
                "code_sha256": sha(Path(__file__)), "learner_source_sha256": sha(code/"channel_experiment.py"),
                "thresholds": {"numeric_max": .60, "LLM_min": .85, "classification": "p_real>0.5"},
                "features": {"numeric": "64 centered normalized grid cells only; no own state, coordinates, pointer, lock, kind, Goal or history",
                             "LLM": "exact original anonymous 8-contact controlled briefing, responses reused by event ID; not certified native prompt"},
                "model_selection": "development-only four seed folds, linear/elementwise-square L2 logistic; lambda .01/.1/1/10",
                "bootstrap": {"draws": 20000, "seed": 20261002, "unit": "seed cluster", "paired": True},
                "known_outcomes": "source confirmation outcomes and development ablations previously inspected; do not claim fresh confirmation",
                "limitations": ["grid plane is only a subset of actual executor inputs",
                                "candidate pointer omitted as required by grid-only scope; multiple code-4 contacts may be ambiguous",
                                "restricted-family classifier score does not prove numerical impossibility",
                                "high-fidelity has continuous observation, not native local grid; needs explicit mapping before its400 protocol"],
                "new_LLM_calls": 0, "engine_or_scene_modified": False}
    write(out/"manifest/protocol.json", manifest)
    start = time.time()
    results = {}
    for tier, (source, llm_file, llm_key) in sources.items():
        dev = read(source/"development_events.json")
        dataset = read(source/"classification/dataset.json")
        if len(dataset) != 400 or sum(r["gold_real"] for r in dataset) != 200:
            raise ValueError("Confirmation must be fixed 200+200")
        if {r["seed"] for r in dev} & {r["seed"] for r in dataset}:
            raise ValueError("Development/confirmation seed overlap")
        llm = {r["id"]: r for r in read(llm_file)}
        if len(llm) != 400 or set(llm) != {r["id"] for r in dataset}:
            raise ValueError("Response and event set mismatch")
        model = train(dev, channel)
        write(out/f"analysis/a01/{tier}/numeric_model.json", model)
        scores = channel.predict(model["model"], transform(plane(dataset), model["selection"]["square"]))
        preds = []
        for event, probability in zip(dataset, scores):
            response = llm[event["id"]]
            if response["seed"] != event["seed"] or response["gold_real"] != event["gold_real"]:
                raise ValueError("Response metadata mismatch")
            request = response["request"]
            if request["model"] != "Qwen3.8-27B" or request["messages"][-1]["content"] != event["prompt"]:
                raise ValueError("Model or stimulus mismatch")
            preds.append({"id": event["id"], "seed": event["seed"], "gold_real": event["gold_real"],
                          "grid_p_real": probability, "llm_p_real": response[llm_key]})
        write(out/f"raw/{tier}/frozen_events.json", dataset)
        write(out/f"raw/{tier}/LLM_responses_reused.json", list(llm.values()))
        write(out/f"analysis/a01/{tier}/predictions.json", preds)
        seeds = sorted({r["seed"] for r in preds})
        clusters = np.array([seeds.index(r["seed"]) for r in preds])
        weights = np.random.default_rng(20261002).multinomial(len(seeds), np.ones(len(seeds))/len(seeds), size=20000)
        nm, nb, ok = bootstrap_metrics(preds, "grid_p_real", weights, clusters)
        lm, lb, _ = bootstrap_metrics(preds, "llm_p_real", weights, clusters)
        result = {"numeric_grid_only": nm, "LLM_reused": lm, "n_seed_clusters": len(seeds),
                  "Cinfo_accuracy_gap": lm["balanced_accuracy"]-nm["balanced_accuracy"],
                  "Cinfo_gap_ci95": np.quantile((lb-nb)[ok], [.025, .975]).tolist(),
                  "D1_point_thresholds_met": nm["balanced_accuracy"] <= .6 and lm["balanced_accuracy"] >= .85,
                  "D1_CI_strict_met": nm["balanced_accuracy_ci95"][1] <= .6 and lm["balanced_accuracy_ci95"][0] >= .85,
                  "scope": manifest["kind"]}
        for key in ["grid_p_real", "llm_p_real"]:
            rs = roc(preds, key)
            dest = out/f"analysis/a01/{tier}/ROC_{key}.csv"
            with dest.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["threshold", "fpr", "tpr"])
                writer.writeheader(); writer.writerows(rs)
        write(out/f"analysis/a01/{tier}/summary.json", result)
        # Preserve complete per-event prompt templates, not only an informal label.
        req = next(iter(llm.values()))["request"]
        write(out/f"manifest/{tier}_LLM_template.json", {"example_request": req, "all_prompts": f"raw/{tier}/frozen_events.json"})
        results[tier] = result
        print(json.dumps({"tier": tier, "result": result}), flush=True)
    for files in frozen.values():
        for item in files:
            if sha(item["path"]) != item["sha256"]:
                raise ValueError("Source input changed during analysis")
    write(out/"analysis/a01/summary.json", results)
    lines = ["# E10 Grid特征域限制重测报告", "", "中等与困难各复用固定200+200事件；两批独立统计。未改变引擎、场景、阈值或LLM提示。",
             "此次新训练仅64格网格判别器；模型选择仅开发集，LLM响应按事件ID验证后复用，无新增LLM调用。",
             "这是已知确认数据的回顾性协议变更分析，不是新的独立确认。", "",
             "|难度|仅网格平衡准确率[95%CI]|LLM平衡准确率[95%CI]|网格AUC|LLM AUC|D1点阈值|",
             "|---|---|---|---:|---:|---|"]
    for tier, r in results.items():
        def cell(m):
            ci=m['balanced_accuracy_ci95'];return f"{m['balanced_accuracy']:.2%} [{ci[0]:.2%}, {ci[1]:.2%}]"
        lines.append(f"|{tier}|{cell(r['numeric_grid_only'])}|{cell(r['LLM_reused'])}|{r['numeric_grid_only']['auc']:.4f}|{r['LLM_reused']['auc']:.4f}|{r['D1_point_thresholds_met']}|")
    lines += ["", "## 特征域核实", "",
              "旧87%/93.5%来自84维当前局部输入：网格、自身状态、锁定摘要、候选当前位置/相对格、单位类型及通信等，并非8次历史。历史运动学是另一个单独对照。不能把旧数值成绩错误描述为历史序列成绩。",
              "真实Grid MAPPO actor也读取自身状态、单位类型及Goal向量，GOAI控制器亦使用其他状态；仅64格网格是明确的受限子通道，不等于完整真实执行器输入。网格边界/障碍/周围布局本身仍可能携带空间关联。",
              "LLM输入包含8次接触历史及当前公开态势，是受控诊断文本，不宣称原生在线提示完全一致。阈值不调，保留完整原始比较；判别器的低成绩也不证明所有数值算法都无法判别。", "",
              "## 交付与后续", "",
              "analysis/a01分别保存完整平衡准确率、AUC、seed聚类CI、配对Cinfo差、ROC CSV、模型与逐事件预测；manifest保存来源哈希和完整提示示例，raw分别保存固定刺激与响应副本。",
              "若D1未通过，不能因缩窄特征而宣称已通过。新的简报/窗口设计只能开发集验证后另建独立确认。高保真真实执行器为连续观测，400事件协议须先明确该通道对应，不造出不存在的真实网格接口。",
              "未编辑论文或附录；本报告将通道限制、完整当前数值及历史对照的差异交给论文负责人，不预先写成‘网格不可分’。"]
    (out/"reports/r01").mkdir(parents=True)
    (out/"reports/r01/E10_Grid特征域对齐重测报告_v1.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    write(out/"status.json", {"state": "completed", "elapsed_seconds": time.time()-start,
                             "source_inputs_unchanged": True, "new_LLM_calls": 0,
                             "HF400": "pending-real-executor-domain-mapping"})


if __name__ == "__main__":
    main()
