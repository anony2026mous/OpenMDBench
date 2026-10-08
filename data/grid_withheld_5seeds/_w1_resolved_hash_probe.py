"""记录/比对若干场景的 resolved_hash（改名是否改变抽签流的判据）。

`ResolvedScenarioV2.compute_resolved_hash` 在哈希前 `pop` 掉 `scenario_id` 与
四个包哈希字段，所以**理论上**改名/换目录不会改变 resolved_hash，交战命中判定
（种子 = f(resolved_hash, session_id, ...)）因此不受影响、历史分数不会漂移。
本脚本把这个"理论上"变成可核对的数字。

用法：
    python _w1_resolved_hash_probe.py --ids IE-01-SINGLE-TARGET IE-08-ISLAND-STRIKE
    python _w1_resolved_hash_probe.py --ids ... --save before.json
    python _w1_resolved_hash_probe.py --ids ... --compare before.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DEFAULT_IDS = (
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN",
    # 第 8 员 = 岛礁突击：新编号 IE-08，历史别名 MD-AD-006（同一包，两条 registry 记录）
    "IE-08-ISLAND-STRIKE", "IE-08-ISLAND-STRIKE",
    "IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN",
    "IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
)


def probe(public_ids: list[str]) -> dict[str, dict]:
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2

    out: dict[str, dict] = {}
    for public_id in public_ids:
        try:
            resolved, _catalog = compile_formal_scenario_v2(public_id)
        except Exception as error:                       # noqa: BLE001
            out[public_id] = {"error": f"{type(error).__name__}: {error}"}
            continue
        out[public_id] = {
            "resolved_hash": resolved.resolved_hash,
            "scenario_id": resolved.scenario_id,
            "entities": len(resolved.entities),
            "controller_slots": len(resolved.controller_slots),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", default=list(DEFAULT_IDS))
    parser.add_argument("--save", default=None)
    parser.add_argument("--compare", default=None)
    args = parser.parse_args()

    result = probe(args.ids)
    if args.save:
        pathlib.Path(args.save).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[saved] {args.save}")
    if args.compare:
        before = json.loads(pathlib.Path(args.compare).read_text(encoding="utf-8"))
        print(f"{'public_id':30} {'resolved_hash 一致?':20} 说明")
        print("-" * 78)
        for public_id, current in result.items():
            old = before.get(public_id)
            if old is None:
                print(f"{public_id:30} {'（旧记录无此项）':20}")
                continue
            same = old.get("resolved_hash") == current.get("resolved_hash")
            note = "" if same else f"旧 {str(old.get('resolved_hash'))[:20]}…"
            print(f"{public_id:30} {'一致 ✓' if same else '不一致 ✗':20} {note}")
    for public_id, info in result.items():
        if "error" in info:
            print(f"  [FAIL] {public_id}: {info['error']}")
        else:
            print(f"  [ok  ] {public_id:30} {info['resolved_hash'][:26]}… "
                  f"实体={info['entities']} 槽={info['controller_slots']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
