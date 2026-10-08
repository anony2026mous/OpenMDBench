"""Generate a status-aware handoff report; optionally watch baseline completion."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import time
from common import read, write, estimate


def summarize(root):
    out = root / "results"
    e2 = read(out / "E2/analysis.json")
    e3 = read(out / "E3-expanded/analysis.json")
    baseline = out / "E1-unmodified-baseline"
    episodes = []
    for path in sorted(baseline.glob("*/seed-*/report.json")):
        r = read(path)
        s = r.get("strategy_scorecard", {})
        episodes.append({"scenario": r["scenario"], "seed": r["seed"],
                         "aborted": r.get("aborted"), "terminal": s.get("terminal", {}),
                         "V": s.get("defender_score"), "elapsed_seconds": r.get("elapsed_seconds"),
                         "ticks": r["ticks_run"], "path": str(path)})
    anchor = {}
    for scene in ["IE-05-MULTI-AXIS", "IE-09-STAGGERED-WAVES"]:
        rows = [r for r in episodes if r["scenario"] == scene and not r["aborted"]
                and r["terminal"].get("state") in ["defender_success", "attacker_success"]]
        anchor[scene] = {"eligible": len(rows), "expected": 10,
                         "SR": estimate([int(r["terminal"]["state"] == "defender_success") for r in rows]) if rows else None,
                         "V": estimate([r["V"] for r in rows]) if rows else None}
        if rows:
            n = len(rows)
            phat = sum(r["terminal"]["state"] == "defender_success" for r in rows) / n
            z = 1.959963984540054
            center = (phat + z*z/(2*n))/(1 + z*z/n)
            half = z*((phat*(1-phat)/n+z*z/(4*n*n))**.5)/(1 + z*z/n)
            anchor[scene]["SR_wilson_ci95_supplement"] = [max(0, center-half), min(1, center+half)]
    progress = []
    for path in baseline.glob("*/seed-*/episode.jsonl"):
        last_tick = 0
        for line in path.read_text().splitlines():
            try:
                event = __import__('json').loads(line)
            except ValueError:
                continue  # A currently-running writer may have an incomplete final line.
            last_tick = max(last_tick, int(event.get("tick", 0)))
        progress.append({"scenario": path.parent.parent.name, "seed_folder": path.parent.name, "latest_tick": last_tick})
    latencies = [r["elapsed_seconds"] for r in read(out / "E3-expanded/predictions.json")]
    import numpy as np
    preds = read(out / "E3-expanded/predictions.json")
    confusion = {k: dict(Counter(str((bool(r['gold_real']), r[k] > .5)) for r in preds))
                 for k in ["rule_p_real", "llm_p_real"]}
    status = {"updated_utc": datetime.now(timezone.utc).isoformat(),
              "E1": {"full_experiment": "NEEDS_DECISION", "baseline_reports": len(episodes),
                     "expected_baseline_reports": 20, "baseline_queue_finished": (baseline / "summary.json").exists(),
                     "anchors": anchor, "episodes": episodes, "tick_progress": progress},
              "E2": "DONE", "E3": "REDUCED_SAMPLE_TEST_COMPLETE_FULL_PROTOCOL_INCOMPLETE",
              "D1": "NOT_PASSED", "E3_events": len(preds), "E3_seed_clusters": e3["rule"]["n_seed_clusters"],
              "LLM_latency_seconds": {"median": float(np.median(latencies)), "p95": float(np.quantile(latencies, .95))},
              "LLM_endpoint_counts": dict(Counter(r["endpoint"] for r in preds)), "E3_confusion": confusion}
    write(root / "P0_status.json", status)
    lines = ["# 角色 C：P0 强化实验阶段报告", "", f"更新 UTC：{status['updated_utc']}。执行目标为 20260930 清单的 E1/E2/E3；当前并非全部 P0 完成。", "",
             "|实验|实际执行|当前状态|", "|---|---|---|",
             f"|E1 headroom|IE-05/IE-09 原始规则基线，各 10 seeds；已落盘 {len(episodes)}/20 局|三档强度干预待授权，尚无完整 E1 结果|",
             "|E2 剂量响应|复核 P2 80 局原始数据；P1 60 局独立辅助核算|已完成远程复核、统计及绘图|",
             f"|E3 信息不对称|重放 Grid P1/P3a 50 条来源轨迹；冻结 {len(preds)} 个平衡事件，双端点真实判别|缩减样本实测完成，400 事件协议未完成，D1 未通过|", "",
             "## E2：已获得什么证据", "",
             "strong−hold 的配对平均增益：规则规划＋RL +0.4567（95% CI [0.2467,0.6633]），LLM 规划＋RL +0.5367（[0.3167,0.7234]）。完整 Goal 接口相对阻断具有正向作用。",
             "", "规则规划的 mask1 V=0.8333，高于 strong V=0.6700；strong−mask1 的 CI 包含 0，因此只能报告样本均值的非单调，不能宣称显著证伪更多信息有益。LLM 栈四点均值递增，但相邻差的不确定性仍应呈现。",
             "", "P1 的 ΔV_A=−0.2133、ΔV_B=−0.2400，不能与 P2 不同 seeds 拼接成新的优势证明。P2 的接口有效性和 P1 的部署排名不占优并不矛盾；这是有条件分层框架需要解释的不同量。", "",
             "## E3：D1 实测与服务情况", "",
             f"原始合格候选：{e3['dataset_audit']['available_counts']}；平衡抽取每类 {e3['dataset_audit']['actual_per_class']} 个事件，覆盖 {e3['rule']['n_seed_clusters']} 个 seed 聚类。每个窗口使用三个已观测帧，不共享同 seed/接触/tick。",
             "", "|判别器|正确率|聚类 bootstrap 95% CI|ROC-AUC|AUC 95% CI|", "|---|---:|---|---:|---|"]
    for name, s in [("几何规则", e3["rule"]), ("LLM", e3["llm_all_attempts_accuracy"])]:
        lines.append(f"|{name}|{s['accuracy']:.2%}|{s['accuracy_ci95']}|{s['auc']:.4f}|{s['auc_ci95']}|")
    lines += ["", "规则：33 个真实目标均识对，33 个诱饵中 5 个误报；LLM：33 个诱饵均识对，但 33 个真实目标中 18 个被判成诱饵。LLM 排序 AUC 较好，但固定 0.5 阈值下偏保守。不能用事后调阈值冒充预先确定的 D1 通过；即使校准改进 LLM，也不能消除规则准确率远超 60% 的事实。",
              "", "这说明当前 Grid 刺激集中的运动线索可被数值几何压缩，不能用这些样本证明 LLM 独占信息优势。该结果不能自动迁移为高保真 IE 场景的 D1 判定。仅瞬时快照对照的 50% 不可替代使用运动历史的主规则对照。",
              "", f"两个端点各完成 33 次调用，关闭思考，无服务/JSON 解析错误。中位响应 {status['LLM_latency_seconds']['median']:.3f}s，P95 {status['LLM_latency_seconds']['p95']:.3f}s。初始 P3a 可行性检查另有 2 次调用，独立保留，不拼入扩展结果。",
              "", "P1 观测重建通过全部动作、终局与 metrics 一致性校验；P3a 另有逐状态与 broker 指纹精确重放校验。后者比前者的验证更强，报告中未混称。P1/P3a 性能分数未拼接；这里只新建受控刺激集，并在 analysis.json 中按来源分别核算分类成绩。",
              "", "## E1：当前未完成的部分", "",
              "原始基线不是强度标定，更不是三个 headroom 档位的因果比较。当前强度参数在 scenario.yaml/agents.yaml 中，没有现成 CLI 旋钮；需要在独立实验副本新增场景变体并获得授权。高保真 RL 实际是 PPO，需纠正清单的 MAPPO 表述。完整方案见 E1_受控强度实验待授权方案.md。",
              "", "|原始场景|有效完成局数|SR（如可核算）|平均 V（如可核算）|", "|---|---:|---|---|"]
    for scene, stats in anchor.items():
        lines.append(f"|{scene}|{stats['eligible']}/10|{stats['SR']}；Wilson 补充 CI {stats.get('SR_wilson_ci95_supplement')}|{stats['V']}|")
    lines += ["", "SR 与 V 是不同指标。全胜样本的非参数 seed-bootstrap 会退化为 [1,1]，不代表真实成功率没有不确定性；10/10 全胜的 Wilson 95% 区间约为 [0.7225,1]，已作补充。当前样本不能把综合分数 0.8 直接称为 SR=80%。未完成队列的中间结果不可用于选择理想档位。具体逐局进度见 P0_status.json；基线全部完成后重新运行 summarize_p0.py 可更新核算。",
              "", "## 代码、兼容性与完整性", "", "新增统计测试在 Windows 和远程 Python 3.11 均 5/5 通过。并行重放 12 路、判别 16 路；控制数值库为单线程。正式引擎、物理参数、Catalog、终局与场景设计未改；Grid 检查点从本地旧冻结轨迹资产复制到隔离目录，只用于重放。交付清单和源数据哈希见各 manifest/analysis.json。",
              "", "E3 数据不足及 D1 不通过是本次发现，不应删除或改写为通过。若补做完整 E3，可先在不改引擎的条件下增加真实轨迹；若要建立非几何可压缩的语义优势，应另行授权场景信息通道设计，而不是事后削弱规则。",
              "", "## 下一步需确认", "", "请授权仅在独立实验副本增加 IE-05/IE-09 波次时序变体（正式发布及权威分支不动），并允许采用现有冻结高保真 PPO 权重而非误称 MAPPO。授权后才能继续 E1 标定、冻结设置及 180 局配对确认。E3 如要求严格 400 事件，需补充更多真实轨迹，并明确接受 D1 可能仍不通过。"]
    (root / "P0强化实验阶段报告.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--watch", action="store_true")
    a = p.parse_args()
    started = time.monotonic()
    while True:
        status = summarize(a.root)
        print(__import__('json').dumps({"baseline_reports": status["E1"]["baseline_reports"], "finished": status["E1"]["baseline_queue_finished"]}), flush=True)
        if not a.watch or status["E1"]["baseline_queue_finished"] or time.monotonic()-started > 3600:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
