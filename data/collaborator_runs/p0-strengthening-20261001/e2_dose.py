"""Reanalyse archived raw episodes; never pool the P1 and P2 seed batches."""
import argparse
import csv
from pathlib import Path
import numpy as np
from common import read, write, digest, estimate


def episodes(folder, seeds, arms, mode):
    result, provenance = {}, []
    for path in sorted(folder.glob("*/episode.json")):
        row = read(path)
        c = row["config"]
        key = (c["seed"], c["arm"])
        if c["seed"] not in seeds or c["arm"] not in arms:
            continue
        if not row.get("complete") or row.get("aborted") or c["goal_mode"] != mode:
            continue
        # Latest valid attempt, by numeric attempt index, NOT by score.
        attempt = int(path.parent.name.rsplit("_a", 1)[1])
        if key not in result or attempt > result[key][0]:
            result[key] = (attempt, row, path)
    if set(result) != {(s, a) for s in seeds for a in arms}:
        raise ValueError(f"Incomplete batch {folder}: {sorted(result)}")
    for _, row, path in result.values():
        event = path.with_name("events.jsonl")
        if event.is_file() and digest(event) != row["events_sha256"]:
            raise ValueError(f"Trace hash mismatch: {event}")
        requests = path.with_name("requests.jsonl")
        if row.get("requests_sha256") and (not requests.exists() or digest(requests) != row["requests_sha256"]):
            raise ValueError(f"LLM request trace hash mismatch: {requests}")
        provenance.append({"path": str(path), "sha256": digest(path),
                           "engine_hashes": row["source_hashes"],
                           "checkpoint_sha256": row["config"]["checkpoint_sha256"]})
    if len({str(r["engine_hashes"]) for r in provenance}) != 1:
        raise ValueError("Engine fingerprints differ within batch")
    return {k: v[1] for k, v in result.items()}, provenance


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root, out = args.input, args.output
    out.mkdir(parents=True, exist_ok=True)
    modes = ["hold", "mask2", "mask1", "strong"]
    arms = ["rule-rl", "llm-rl"]
    seeds = list(range(512, 522))
    raw, provenance = {}, {}
    for mode in modes:
        raw[mode], provenance[mode] = episodes(
            root / f"P2__goal_dose__s512-521__{mode}__v1", seeds, arms, mode)
    engine_sets = {str(v[0]["engine_hashes"]) for v in provenance.values()}
    checkpoints = {r["checkpoint_sha256"] for v in provenance.values() for r in v}
    if len(engine_sets) != 1 or len(checkpoints) != 1:
        raise ValueError("P2 dose conditions do not share frozen components")
    rows, contrasts = [], []
    for arm in arms:
        for availability, mode in enumerate(modes):
            values = [raw[mode][s, arm]["V"] for s in seeds]
            gain = [raw[mode][s, arm]["V"] - raw["hold"][s, arm]["V"] for s in seeds]
            rows.append({"arm": arm, "dose": mode, "available_units_nominal": availability,
                         "masked_units_nominal": 3 - availability,
                         "V": estimate(values), "gain_over_hold": estimate(gain),
                         "seed_values": dict(zip(map(str, seeds), values)),
                         "seed_gains": dict(zip(map(str, seeds), gain))})
        for low, high in zip(modes, modes[1:]):
            differences = [raw[high][s, arm]["V"] - raw[low][s, arm]["V"] for s in seeds]
            contrasts.append({"arm": arm, "contrast": f"{high}-{low}", **estimate(differences)})
    p1seeds = list(range(501, 511))
    p1arms = ["rule-rule", "llm-rule", "rule-rl", "llm-rl", "rl", "pure-llm"]
    p1, p1proof = episodes(root / "P1__six_arm__s501-510__main__v1", p1seeds, p1arms, "strong")
    p1stats = {}
    # Best-pure is a batch-mean selector, not a per-seed hindsight oracle.
    pure = ["rule-rule", "rl", "pure-llm"]
    best = max(pure, key=lambda a: np.mean([p1[s, a]["V"] for s in p1seeds]))
    for name, a, b in [("delta_V_A", "llm-rule", best),
                       ("delta_V_B", "llm-rl", best),
                       ("planner_gain_rule_executor", "llm-rule", "rule-rule"),
                       ("planner_gain_rl_executor", "llm-rl", "rule-rl")]:
        p1stats[name] = estimate([p1[s, a]["V"] - p1[s, b]["V"] for s in p1seeds])
    p1stats["delta_I_factorial_interaction"] = estimate([
        p1[s, "llm-rl"]["V"] - p1[s, "rule-rl"]["V"]
        - p1[s, "llm-rule"]["V"] + p1[s, "rule-rule"]["V"] for s in p1seeds])
    p1stats["best_pure_selected_by_batch_mean"] = best
    result = {"schema": "p0-e2-dose@1", "P2_seeds": seeds, "P1_seeds": p1seeds,
              "P2_rows": rows, "P2_adjacent_contrasts": contrasts, "P1": p1stats,
              "limitations": ["Ordinal unit availability, not bits or measured B_if",
                              "No analytic f is fitted; P1/P2 statistics are kept separate",
                              "Paired seeds do not freeze the stochastic LLM Goal stream",
                              "P1 best-pure selection is exploratory, not held-out selection"],
              "provenance": {"P2": provenance, "P1": p1proof}}
    write(out / "analysis.json", result)
    with (out / "dose_gain.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["arm", "dose", "availability", "V", "gain", "gain_ci_low", "gain_ci_high"])
        for r in rows:
            w.writerow([r["arm"], r["dose"], r["available_units_nominal"], r["V"]["mean"],
                        r["gain_over_hold"]["mean"], *r["gain_over_hold"]["ci95"]])
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for arm in arms:
        selected = [r for r in rows if r["arm"] == arm]
        y = np.array([r["gain_over_hold"]["mean"] for r in selected])
        ci = np.array([r["gain_over_hold"]["ci95"] for r in selected])
        ax.errorbar(range(4), y, yerr=np.maximum(0, np.array([y-ci[:, 0], ci[:, 1]-y])),
                    marker="o", capsize=4, label=arm)
    ax.set_xticks(range(4), modes)
    ax.set_xlabel("Nominal Goal availability: 0 / 1 / 2 / 3 units (NOT bits)")
    ax.set_ylabel("Paired score gain versus hold")
    ax.set_title("Dose response: seed-bootstrap 95% CI")
    ax.axhline(0, color="grey", linewidth=.7)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "dose_gain.png", dpi=200)
    fig.savefig(out / "dose_gain.svg")
    lines = ["# P0 E2：接口剂量—增益实测报告", "", "统计单位为 seed；P2 10 个配对 seeds，20,000 次 bootstrap。P1 独立核算，不与 P2 拼接。", "",
             "|栈|剂量|平均 V|相对 hold 增益|95% CI|", "|---|---|---:|---:|---|"]
    for r in rows:
        g = r["gain_over_hold"]
        lines.append(f"|{r['arm']}|{r['dose']}|{r['V']['mean']:.4f}|{g['mean']:+.4f}|[{g['ci95'][0]:+.4f}, {g['ci95'][1]:+.4f}]|")
    lines += ["", "## 相邻剂量对比", ""]
    for r in contrasts:
        sign = "CI 不含 0" if r["ci95"][0] > 0 or r["ci95"][1] < 0 else "CI 包含 0，方向未获显著确认"
        lines.append(f"- {r['arm']}，{r['contrast']}：{r['mean']:+.4f}，95% CI {r['ci95']}；{sign}。")
    lines += ["", "## 独立 P1 核算", "", "```json", __import__('json').dumps(p1stats, ensure_ascii=False, indent=2), "```", "",
              "## 结论与边界", "", "完整接口相对 hold 的改善与逐档单调改善是不同命题。规则规划栈 mask1 到 strong 的样本均值下降必须保留，但其相邻对比 CI 包含 0，不能宣称已统计证明更多信息有害。这里得到的是特定部署的接口剂量响应，不是 f(C_info,B_if) 的解析拟合或分层定律的普遍证明。",
              "", "名义单位可用性是干预级别；实际活跃单位数、指令数量可能随终局与执行过程变化。源文件哈希、冻结组件、全部逐 seed 数值见 analysis.json。"]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(__import__('json').dumps({"output": str(out), "rows": rows, "P1": p1stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
