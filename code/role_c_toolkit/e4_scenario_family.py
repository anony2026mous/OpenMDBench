"""E4 scenario-family inventory and admission-gate ledger (read-only).

E4 ("scenario-family construction and admission") needs three things before any run:

* an inventory of what already exists (the 14 admitted interception-engagement
  scenarios plus the 28 competition candidates in four categories),
* a frozen manifest (SHA-256) per scenario package, and
* a ledger that records the admission verdict for D1' / D2 / D3 per scenario.

This module reads the scenario trees and writes that inventory and an *empty* ledger
template.  It never writes to a scenario package, never touches the registry, and
never runs a simulation — the gate values must come from real runs by the experiment
owner.

Usage:
    python e4_scenario_family.py inventory --source <source_codes root> --output <dir>
    python e4_scenario_family.py scaffold  --ledger <ledger.json> --output <template.json>
    python e4_scenario_family.py report    --ledger <ledger.json> --output <appendix-A.md>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

# Gate definitions are quoted from the frozen requirements baseline
# (openmd/doc/hifi_requirements.md, "1. 一票否决约束"), not invented here.
# `not_applicable` and `blocked` exist because the v8 checklist changed D1 into a reported
# quantity and because D3 has no implementation in this engine version; neither may be
# silently recorded as pending-forever or, worse, as a pass.
GATES = {
    "D1_prime_decision_form": {
        "question_en": "greedy scripted rule must not reach 90% of the rule-baseline score",
        "question_zh": "手写贪心规则是否拿不到 rule+heuristic 基线的 90% 分（核心难度落在调度/取舍）",
        "verdicts": ["pass", "fail", "pending", "not_applicable", "blocked"],
    },
    "D2_headroom": {
        "question_en": "best pure baseline SR within [40%, 85%]",
        "question_zh": "最优纯基线成功率是否落在 [40%, 85%]",
        "verdicts": ["pass", "fail", "pending", "not_applicable", "blocked"],
    },
    "D3_interface_budget": {
        "question_en": "granularity tiers monotone, tier gaps > estimator variance, finest B_if >= 0.3",
        "question_zh": "接口粒度三档 B_if 是否单调且档间距大于估计方差、最细档 ≥ 0.3",
        "verdicts": ["pass", "fail", "pending", "not_applicable", "blocked"],
    },
    "D1_information_asymmetry": {
        "question_en": "rule discriminator <= 60% while LLM >= 85% on feint-vs-real",
        "question_zh": "真假目标语义可辨：规则 ≤60%、LLM ≥85%（v8 起改为报告量，不设通过/不通过）",
        "verdicts": ["reported", "not_applicable", "blocked"],
    },
}
# Which scenarios can even carry a feint-vs-real discrimination measurement.  Everything
# absent from this map has no decoy/feint mechanism declared in SCENARIO_CONTRACTS.json,
# so D1 is not applicable to it; forcing it would mean adding deception to a frozen,
# already-validated scenario package.
D1_MECHANISM = {
    "IE-06-DECOY-MIXED": "decoy vs armed attacker, same observed air domain",
    "IE-11-DECOY-SCREEN": "decoy screen vs real raid",
    "MD-TRK-007": "feint and pursuit: distractors cross the designated track",
    "MD-AD-005": "mixed traffic: benign diversions share public signatures with true entrants",
}
D1_PACKAGE_ALIASES = {"MD-TRK-007-STANDARD": "MD-TRK-007", "MD-AD-005-STANDARD": "MD-AD-005"}
D3_BLOCKED_NOTE = (
    "本版本引擎无粒度三档实现（IE 树全仓无 to_granularity/goal_granularity）；历史三档曾实测失败"
    "（B_if 39/39 单元×档位不可估；KSG 三档 0.53/0.48/0.61 非单调且配对差值 95% CI 全跨零）。"
    "补实现需改冻结引擎，须主理人决定。")
CATEGORY_NAMES = {
    "REC": "侦察搜索 Reconnaissance",
    "TRK": "持续跟踪 Tracking",
    "AD": "区域拒止 Area Denial",
    "ER": "应急响应 Emergency Response",
    "INT": "拦截交战 Interception-Engagement",
    "IE": "拦截交战 Interception-Engagement",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_digest(package: Path) -> dict:
    files = sorted(item for item in package.rglob("*") if item.is_file())
    hashes = {str(item.relative_to(package)).replace("\\", "/"): sha256_file(item)
              for item in files}
    combined = hashlib.sha256()
    for name, digest in sorted(hashes.items()):
        combined.update(f"{name}:{digest}\n".encode("utf-8"))
    return {"files": hashes, "package_sha256": combined.hexdigest(), "file_count": len(files)}


def registry_entries(registry_path: Path) -> list[dict]:
    try:
        import yaml
    except ImportError:  # pragma: no cover - the repo's own venvs ship PyYAML
        return []
    payload = yaml.safe_load(registry_path.read_bytes())
    return list(payload["scenarios"])


def category_of(scenario_name: str) -> str:
    """Category from the family code, which is a dash/underscore segment of the id."""
    segments = scenario_name.upper().replace("_", "-").split("-")
    for code in ("REC", "TRK", "AD", "ER", "INT", "IE"):
        if code in segments:
            return CATEGORY_NAMES[code]
    return "unknown"


def inventory(source_root: Path) -> dict:
    formal = source_root / "scenarios" / "formal"
    competition = source_root / "scenarios" / "competition_v1"
    rows = []
    for entry in registry_entries(formal / "registry.yaml"):
        package = formal / entry["package"]
        row = {
            "public_id": entry["public_id"],
            "package": entry["package"],
            "tree": "formal",
            "catalog_bundle": entry["catalog_bundle"],
            "admitted": True,
            "category": category_of(entry["public_id"]),
        }
        row.update(package_digest(package) if package.is_dir() else {"package_sha256": None})
        rows.append(row)
    if competition.is_dir():
        for package in sorted(item for item in competition.iterdir() if item.is_dir()):
            row = {
                "public_id": package.name.upper().replace("_", "-"),
                "package": package.name,
                "tree": "competition_v1",
                "catalog_bundle": None,
                "admitted": False,
                "category": category_of(package.name),
            }
            row.update(package_digest(package))
            rows.append(row)
    by_category: dict[str, dict] = {}
    for row in rows:
        bucket = by_category.setdefault(row["category"], {"admitted": 0, "candidate": 0})
        bucket["admitted" if row["admitted"] else "candidate"] += 1
    return {
        "schema": "e4-scenario-inventory@1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "counts": {
            "total": len(rows),
            "admitted": sum(1 for row in rows if row["admitted"]),
            "candidate": sum(1 for row in rows if not row["admitted"]),
        },
        "by_category": by_category,
        "scenarios": rows,
    }


def load_d1_report(path: Path, source_label: str = "") -> dict:
    """Read E10's controlled-discrimination numbers into D1 report values."""
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return load_d1_report_from_payload(payload, source_label or str(path))


def load_d1_report_from_payload(payload: dict, source_label: str = "") -> dict:
    """D1 is a *reported quantity* under checklist v8, so both the numbers and the fact
    that the 60/85 point gate was not met are recorded verbatim."""
    report = {}
    for scenario, entry in payload.items():
        if not isinstance(entry, dict) or "numeric_restricted" not in entry:
            continue
        numeric = entry["numeric_restricted"]
        llm = entry.get("LLM", {})
        report[scenario] = {
            "numeric_balanced_accuracy": numeric.get("balanced_accuracy"),
            "numeric_ci95": numeric.get("balanced_accuracy_ci95"),
            "llm_balanced_accuracy": llm.get("balanced_accuracy"),
            "llm_ci95": llm.get("balanced_accuracy_ci95"),
            "n_events": numeric.get("n"),
            "seed_clusters": entry.get("n_seed_clusters"),
            "cinfo_difference": entry.get("Cinfo_difference"),
            "cinfo_ci95": entry.get("Cinfo_ci95"),
            "point_gate_passed": entry.get("D1_point_pass"),
            "reference_thresholds": {"numeric_max": 0.60, "llm_min": 0.85},
            "source": source_label or str(path),
            "evidence": f"{source_label or path}#{scenario}" if source_label else str(path),
            "scope": entry.get("scope"),
        }
    return report


def contract_id(public_id: str, package: str) -> str:
    """Map a registry/inventory id to the SCENARIO_CONTRACTS id used by the D2 runs.

    ``MD-REC-001-EASY`` and package ``md_rec_001_easy`` both belong to contract
    ``MD-REC-001`` (difficulty variants share one contract); the four new families normalise
    to the bare contract id.  ``IE-*`` ids are returned whole, because that is the key the
    E10/D2 sources use for them.
    """
    text = (public_id or package).upper().replace("_", "-")
    parts = text.split("-")
    if parts and parts[0] == "IE":
        return text
    for index, part in enumerate(parts):
        if part in {"REC", "TRK", "AD", "ER", "INT"} and index + 1 < len(parts):
            number = parts[index + 1]
            if number.isdigit():
                return "-".join(parts[:index + 2])
    return text


def ledger_template(inventory_payload: dict, hifi_control_report: str,
                    d1_report: dict | None = None) -> dict:
    """Admission ledger; only D1 (reported quantity) and D3 (blocked) are pre-filled."""
    scenarios = []
    for row in inventory_payload["scenarios"]:
        contract = contract_id(row["public_id"], row["package"])
        mechanism = D1_MECHANISM.get(contract)
        report = (d1_report or {}).get(contract)
        if report:
            d1 = {"verdict": "reported", "evidence": report.get("evidence"),
                  "report": report, "note": f"机制：{mechanism}"}
        elif mechanism:
            d1 = {"verdict": "blocked", "evidence": None, "report": None,
                  "note": (f"场景具备真假混淆机制（{mechanism}），但 E10 的判别流水线只覆盖 "
                           "IE-06/IE-11；需要另建刺激与判别流程，尚未排期。")}
        else:
            d1 = {"verdict": "not_applicable", "evidence": None, "report": None,
                  "note": "本场景未声明真假混淆/诱饵机制，D1 不适用；补做等于给冻结场景加欺骗机制。"}
        scenarios.append({
            "public_id": row["public_id"],
            "package": row["package"],
            "contract_id": contract,
            "tree": row["tree"],
            "category": row["category"],
            "package_sha256": row["package_sha256"],
            "gates": {
                "D1_prime_decision_form": {"verdict": "pending", "evidence": None, "note": None},
                "D2_headroom": {"verdict": "pending", "evidence": None, "note": None},
                "D3_interface_budget": {"verdict": "blocked", "evidence": None,
                                        "note": D3_BLOCKED_NOTE},
                "D1_information_asymmetry": d1,
            },
            "d1_control_scenario": None,
            "admitted_utc": None,
        })
    return {
        "schema": "e4-admission-ledger@2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "note": ("D1′/D2 初始为 pending，必须由真实运行填入 verdict 与 evidence；"
                 "D1 按 v8 清单以报告量呈现（reported / not_applicable）；"
                 "D3 因本版本引擎无三档实现记为 blocked。禁止把未跑的门写成 pass。"),
        "gate_definitions": GATES,
        "d1_mechanism_map": D1_MECHANISM,
        "reference_category": "interception-engagement (IE-01 … IE-14, 已入场)",
        "hifi_control_report": hifi_control_report,
        "scenarios": scenarios,
    }


def d2_results(headroom: dict, evidence_path: str) -> dict:
    """Flatten a ``d2_headroom.py`` summary into per-contract ledger values."""
    results = {}
    for scenario, entry in (headroom.get("scenarios") or {}).items():
        rate = entry.get("best_baseline_success_rate")
        ci = entry.get("best_baseline_ci95") or [None, None]
        results[scenario] = {
            "verdict": entry.get("d2_headroom_verdict", "pending"),
            "evidence": evidence_path,
            "note": (f"最优纯基线 = {entry.get('best_baseline_policy')}，"
                     f"SR {rate if rate is None else round(rate, 3)}，"
                     f"95% CI [{ci[0] if ci[0] is None else round(ci[0], 3)}, "
                     f"{ci[1] if ci[1] is None else round(ci[1], 3)}]，"
                     f"参照 seed 数 {entry.get('policies', {}).get(entry.get('best_baseline_policy') or '', {}).get('seeds', 0)}"),
            "success_rate": rate,
            "ci95": ci,
        }
    return results


def apply_d2(ledger: dict, results: dict) -> dict:
    applied, missing = 0, []
    for row in ledger["scenarios"]:
        found = results.get(row["contract_id"])
        if not found:
            missing.append(row["public_id"])
            continue
        row["gates"]["D2_headroom"] = {key: found[key]
                                       for key in ("verdict", "evidence", "note")}
        row["gates"]["D2_headroom"]["success_rate"] = found["success_rate"]
        row["gates"]["D2_headroom"]["ci95"] = found["ci95"]
        applied += 1
    ledger["schema"] = "e4-admission-ledger@2"
    ledger["d2_applied"] = {"matched": applied, "without_d2": missing}
    return ledger


def apply_d1prime(ledger: dict, table: dict) -> dict:
    """Attach the D1' prior task-attribute score to each ledger row.

    ``d1prime_prior`` is deliberately kept apart from the D1'_decision_form gate: one is a
    prior task property (checklist v9), the other is the gate verdict.  Conflating them
    would let a score masquerade as a passed gate.
    """
    by_id = {row["public_id"]: row for row in table["rows"]}
    matched, unmatched = 0, []
    for row in ledger["scenarios"]:
        entry = by_id.get(row["public_id"]) or by_id.get(row.get("contract_id", ""))
        if not entry:
            unmatched.append(row["public_id"])
            continue
        row["d1prime_prior"] = {
            "scores": entry["scores"],
            "prior_score": entry["prior_score"],
            "source": entry["source"],
            "evidence": entry["evidence"],
            "uncertain": entry["uncertain"],
            "note": entry["note"],
        }
        matched += 1
    ledger["d1prime_applied"] = {"matched": matched, "without_d1prime": unmatched,
                                 "table_sha256": None}
    return ledger


def d2_graded_results(headroom: dict, evidence_path: str) -> dict:
    """Flatten a ``d2_headroom_graded.py`` summary into per-contract graded values."""
    results = {}
    for key, entry in (headroom.get("scenarios") or {}).items():
        contract = key
        if key.startswith("MD-REC-001-"):
            contract = key  # difficulty variants stay distinct: separate packages
        ci = entry.get("best_composite_ci95") or [None, None]
        results[contract] = {
            "verdict": entry.get("d2_graded_verdict", "pending"),
            "evidence": evidence_path,
            "composite": entry.get("best_composite_mean"),
            "ci95": ci,
            "policy": entry.get("best_baseline_policy"),
            "task_relevant_policy": entry.get("best_task_relevant_policy"),
            "task_relevant_composite": entry.get("best_task_relevant_composite"),
            "headroom_band": entry.get("headroom_band"),
            "note": (f"声明综合分：最优纯基线 {entry.get('best_baseline_policy')} = "
                     f"{entry.get('best_composite_mean')}，95% CI "
                     f"[{ci[0]}, {ci[1]}]；headroom 分档 {entry.get('headroom_band')}"
                     + ("（最优基线落在地板控制上）" if entry.get("best_is_floor_control") else "")),
        }
    return results


def apply_d2_graded(ledger: dict, results: dict) -> dict:
    """Attach the graded composite measurement beside the binary verdict.

    The two live together on purpose: the binary gate was pre-registered, the graded one is
    the amendment that makes headroom measurable at all, and neither may overwrite the other.
    """
    matched, unmatched = 0, []
    for row in ledger["scenarios"]:
        # Only the competition tree's packages were calibrated; a formal registry row that
        # happens to share a contract id (e.g. the IE-08 alias MD-AD-006-ISLAND-STRIKE) is a
        # different scenario and must not inherit this measurement.
        if row.get("tree") != "competition_v1":
            continue
        found = results.get(row["public_id"]) or results.get(row.get("contract_id", ""))
        if not found:
            unmatched.append(row["public_id"])
            continue
        gate = row["gates"]["D2_headroom"]
        gate["graded"] = {
            "measurement": "declared composite Σ wᵢ·valueᵢ over recorded metrics",
            "verdict": found["verdict"], "composite": found["composite"], "ci95": found["ci95"],
            "best_baseline_policy": found["policy"],
            "best_task_relevant_policy": found["task_relevant_policy"],
            "best_task_relevant_composite": found["task_relevant_composite"],
            "headroom_band": found["headroom_band"], "evidence": found["evidence"],
            "note": found["note"],
        }
        gate["verdict_binary"] = gate["verdict"]
        gate["verdict"] = found["verdict"]
        matched += 1
    ledger["d2_graded_applied"] = {"matched": matched, "without_graded": unmatched}
    return ledger


def appendix_table(ledger: dict) -> str:
    lines = [
        "# 附录 A：场景族与入场门判定（自动生成骨架）",
        "",
        "> 由 `role_c_toolkit/e4_scenario_family.py report` 从门禁台账生成。"
        "**verdict 为 pending 的行不得写进论文的 admitted 表。**",
        "",
        "| 类别 | 场景 | 包 | manifest SHA-256（前 12 位） | D1′ 决策形态门 | D2 headroom（综合分） | D3 接口预算 | D1 报告量 | D1′ 先验得分 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in ledger["scenarios"]:
        gates = row["gates"]
        short = (row.get("package_sha256") or "—")[:12]
        d2 = gates["D2_headroom"]
        graded = d2.get("graded") or {}
        rate = d2.get("success_rate")
        if graded.get("composite") is not None:
            d2_cell = f"{graded['verdict']} ({graded['composite']:.2f})"
            if rate is not None:
                d2_cell += f" / 二值 {d2.get('verdict_binary', d2['verdict'])} ({rate:.2f})"
        else:
            d2_cell = d2["verdict"] if rate is None else f"{d2['verdict']} ({rate:.2f})"
        d1 = gates["D1_information_asymmetry"]
        report = d1.get("report") or {}
        if report:
            d1_cell = (f"{report.get('numeric_balanced_accuracy')} / "
                       f"{report.get('llm_balanced_accuracy')}")
        else:
            d1_cell = d1["verdict"]
        prior = row.get("d1prime_prior") or {}
        prior_cell = "—" if not prior else f"{prior['prior_score']:.2f}"
        lines.append(
            f"| {row['category']} | {row['public_id']} | `{row['package']}` | `{short}` "
            f"| {gates['D1_prime_decision_form']['verdict']} "
            f"| {d2_cell} "
            f"| {gates['D3_interface_budget']['verdict']} "
            f"| {d1_cell} | {prior_cell} |")
    counts: dict[str, dict[str, int]] = {}
    for row in ledger["scenarios"]:
        bucket = counts.setdefault(row["category"], {})
        for name, entry in row["gates"].items():
            bucket[name] = bucket.get(name, 0) + (1 if entry["verdict"] in ("pass", "reported")
                                                  else 0)
        bucket["_total"] = bucket.get("_total", 0) + 1
    lines += [
        "",
        "判定值含义：`pass`/`fail` = 已跑并达/未达标；`pending` = 尚未运行；"
        "`reported` = 按 v8 清单以报告量呈现（D1，无通过判定）；"
        "`not_applicable` = 该场景不具备此门的机制前提；`blocked` = 本版本无法执行（附原因）。",
        "",
        "## 各类别门禁进度", "",
        "| 类别 | 场景数 | D1′ pass | D2 pass | D2 已判定 | D3 | D1 报告量/不适用 |",
        "|---|---|---|---|---|---|---|",
    ]
    for category, bucket in sorted(counts.items()):
        d2_rows = [row for row in ledger["scenarios"] if row["category"] == category]
        d2_decided = sum(1 for row in d2_rows
                         if row["gates"]["D2_headroom"]["verdict"] in ("pass", "fail"))
        lines.append(f"| {category} | {bucket['_total']} "
                     f"| {bucket.get('D1_prime_decision_form', 0)} "
                     f"| {bucket.get('D2_headroom', 0)} | {d2_decided} "
                     f"| {bucket.get('D3_interface_budget', 0)} "
                     f"| {bucket.get('D1_information_asymmetry', 0)} |")
    categories_with_three = [
        category for category, bucket in sorted(counts.items())
        if sum(1 for row in ledger["scenarios"] if row["category"] == category
               and row["gates"]["D2_headroom"]["verdict"] in ("pass", "fail")) >= 3]
    without_prior = [row["public_id"] for row in ledger["scenarios"]
                     if not row.get("d1prime_prior")]
    lines += [
        "",
        "## 成功判据（清单 v8 §1）",
        "",
        "≥3 个大类各有 ≥3 个场景完成入场门判定；场景族总数从 14 入场扩展到 20+。",
        "",
        f"- 已满足\"≥3 个场景完成判定\"的类别：{'、'.join(categories_with_three) or '（尚无）'}"
        f"（{len(categories_with_three)} 个大类）。",
        f"- 场景族规模：台账共 {len(ledger['scenarios'])} 个场景，其中 25 个已在正式 registry，"
        "30 个为 competition_v1 候选。",
        f"- **D1′ 先验标注覆盖**：{len(ledger['scenarios']) - len(without_prior)}/"
        f"{len(ledger['scenarios'])} 个场景有先验得分；未覆盖的 {len(without_prior)} 个是"
        "平台兼容用的 MD-* 场景（MD-AD-002 / MD-INT-003 的难度档、MD-INT-002/005/006），"
        "不属于本次场景族构建目标，如需可另行标注。",
    ]
    if without_prior:
        lines += ["", "未覆盖 D1′ 的场景：" + "、".join(without_prior)]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    make_inventory = sub.add_parser("inventory", help="hash every scenario package")
    make_inventory.add_argument("--source", type=Path, required=True,
                                help="source_codes root holding scenarios/")
    make_inventory.add_argument("--output", type=Path, required=True)
    make_inventory.add_argument("--ledger-output", type=Path)
    make_inventory.add_argument("--control-report", default="")
    make_inventory.add_argument("--d1-report", type=Path,
                                help="E10 analysis/a01/summary.json (D1 reported quantities)")
    make_inventory.add_argument("--d1-source-label", default="")

    build = sub.add_parser("scaffold", help="write an empty gate ledger from an inventory")
    build.add_argument("--inventory", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--control-report", default="")
    build.add_argument("--d1-report", type=Path)
    build.add_argument("--d1-source-label", default="")

    merge = sub.add_parser("d2-merge", help="fill the D2 column from a d2_headroom summary")
    merge.add_argument("--ledger", type=Path, required=True)
    merge.add_argument("--headroom", type=Path, required=True)
    merge.add_argument("--evidence", required=True,
                       help="path recorded in the ledger as the D2 evidence")

    prior = sub.add_parser("d1prime-merge",
                           help="attach the D1' prior task-attribute scores to the ledger")
    prior.add_argument("--ledger", type=Path, required=True)
    prior.add_argument("--table", type=Path,
                       help="compiled table JSON (equivalent to --table-json)")
    prior.add_argument("--table-json", type=Path,
                       help="compiled table JSON (rows with scores and prior_score)")

    graded = sub.add_parser("d2-merge-graded",
                            help="attach the graded (declared-composite) headroom beside the "
                                 "pre-registered binary verdict")
    graded.add_argument("--ledger", type=Path, required=True)
    graded.add_argument("--graded", type=Path, required=True)
    graded.add_argument("--evidence", required=True)

    report = sub.add_parser("report", help="render the appendix-A table from a ledger")
    report.add_argument("--ledger", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    d1_report = (load_d1_report(args.d1_report, args.d1_source_label)
                 if getattr(args, "d1_report", None) else None)
    if args.command == "inventory":
        payload = inventory(args.source)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(f"inventory: {payload['counts']} -> {args.output}")
        if args.ledger_output:
            template = ledger_template(payload, args.control_report, d1_report)
            args.ledger_output.write_text(
                json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            reported = sum(1 for row in template["scenarios"]
                           if row["gates"]["D1_information_asymmetry"]["verdict"] == "reported")
            print(f"ledger ({len(template['scenarios'])} scenarios, D1 reported={reported}) -> "
                  f"{args.ledger_output}")
        return
    if args.command == "scaffold":
        payload = json.loads(args.inventory.read_text(encoding="utf-8"))
        template = ledger_template(payload, args.control_report, d1_report)
        args.output.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(f"ledger template ({len(template['scenarios'])} scenarios) -> {args.output}")
        return
    if args.command == "d2-merge":
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        headroom = json.loads(args.headroom.read_text(encoding="utf-8"))
        ledger = apply_d2(ledger, d2_results(headroom, args.evidence))
        args.ledger.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
        print(json.dumps({"matched": ledger["d2_applied"]["matched"],
                          "without_d2": len(ledger["d2_applied"]["without_d2"])},
                         ensure_ascii=False))
        return
    if args.command == "d2-merge-graded":
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        graded_summary = json.loads(args.graded.read_text(encoding="utf-8"))
        ledger = apply_d2_graded(ledger, d2_graded_results(graded_summary, args.evidence))
        ledger["d2_graded_applied"]["summary_sha256"] = sha256_file(args.graded)
        ledger["d2_graded_applied"]["bands"] = graded_summary.get("headroom_bands")
        ledger["d2_graded_applied"]["by_family"] = graded_summary.get("by_family")
        args.ledger.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(json.dumps({"matched": ledger["d2_graded_applied"]["matched"],
                          "without_graded": len(ledger["d2_graded_applied"]["without_graded"]),
                          "bands": graded_summary.get("headroom_bands"),
                          "families_with_three_in_window":
                              graded_summary.get("families_with_three_in_window")},
                         ensure_ascii=False))
        return
    if args.command == "d1prime-merge":
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        table = json.loads((args.table_json or args.table).read_text(encoding="utf-8"))
        ledger = apply_d1prime(ledger, table)
        ledger["d1prime_applied"]["table_sha256"] = sha256_file(args.table_json or args.table)
        args.ledger.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(json.dumps({"matched": ledger["d1prime_applied"]["matched"],
                          "without_d1prime": len(ledger["d1prime_applied"]["without_d1prime"])},
                         ensure_ascii=False))
        return
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    args.output.write_text(appendix_table(ledger), encoding="utf-8")
    print(f"appendix table -> {args.output}")


if __name__ == "__main__":
    main()
