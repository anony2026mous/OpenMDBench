"""Re-derive the terminal layer of already-recorded arm reports.

Runs recorded before the harness expanded the engine's frozen terminal receipt
carry ``{"result": "<repr>"}``, and their embedded ``layers.terminal`` was
computed from a misclassified state (a defender hold could read as an attacker
win because the blob's ranking map contains ``'coalition.intruder'``).

This rewrites only that layer plus the overall score, from the same recorded
evidence, so old and new arms stay comparable without re-running episodes.

Usage:
    python _w1_rescore.py --apply arm_hybrid.json [arm_pure.json ...]
    python _w1_rescore.py arm_hybrid.json          # dry run: show the diff
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from strategy_metrics import rescore_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="写回文件（默认只预览）；原文件备份为 *.bak")
    args = parser.parse_args()

    for path in args.reports:
        if not path.is_file():
            print(f"[skip] {path} 不存在")
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        # 深拷贝快照：rescore 是就地改写，直接持引用会把"改前"也一起改掉
        before = json.loads(json.dumps(report, default=str))
        before_card = before.get("strategy_scorecard") or {}
        before_term = (before_card.get("terminal") or {}).get("state")
        before_layer = (before_card.get("layers") or {}).get("terminal")
        before_depth = (before_card.get("layers") or {}).get("depth")
        before_score = before_card.get("defender_score")

        rescore_report(report)

        after_card = report["strategy_scorecard"]
        after_term = after_card["terminal"]["state"]
        after_score = after_card["defender_score"]
        print(f"{path.name}")
        print(f"  terminal       : {before_term} -> {after_term}"
              f"   (unstructured={after_card['terminal'].get('unstructured_receipt')})")
        print(f"  terminal_layer : {before_layer} -> {after_card['layers']['terminal']}")
        print(f"  depth_layer    : {before_depth} -> {after_card['layers']['depth']}"
              f"   {json.dumps(after_card['air_layer'].get('depth_layer'))}")
        print(f"  defender_score : {before_score} -> {after_score}")
        print(f"  layers : {json.dumps(after_card['layers'])}")

        if args.apply:
            backup = path.with_suffix(path.suffix + ".bak")
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                       sort_keys=True, default=str) + "\n",
                            encoding="utf-8")
            print(f"  已写回（备份 {backup.name}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
