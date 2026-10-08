"""把 IE 场景集的编号落定（用户 2026-09-24 指定）：

* **IE-08 = 岛礁突击**。它的历史 public_id 是 `MD-AD-006-ISLAND-STRIKE`；
  该场景本来就是 IE 场景集的第八个成员，因此新编号是 `IE-08-ISLAND-STRIKE`。
  registry 里**同时保留**两条记录（同一包、同一 `resolved_hash`）⇒ 旧 id 仍可解析，
  `compute_resolved_hash` 会 `pop("scenario_id")` 与包哈希，所以改名**不改变抽签流**，
  历史分数不漂移（实测见 `_w1_resolved_hash_probe.py`）。
* 本轮新建的六个场景因此顺延为 **IE-09 … IE-14**（原 IE-08..IE-13）。

本脚本只做两件事：
1. `code/eval/*.py` 里把**功能性引用**的字面量 `MD-AD-006-ISLAND-STRIKE`
   改成 `IE-08-ISLAND-STRIKE`；
2. 把六个新场景 id 追加进各脚本的"全场景列表"（`IE_SET` / `ALL` 之类）。

刻意**不改**的文件（历史产物的记录，改了等于篡改历史）：
* `_gen_md_ad_006.py`（岛礁突击场景的历史生成器，输出就是旧名包）
* `_gen_ie_set.py` 的 docstring（记录当时的编号沿革）
* `_gen_ie_set_ext.py`（别名逻辑本身要引旧名）
* `md_ad_006_*.md` / `HANDOFF_*.md`（历史交接与场景专档；已归档出公开仓）

用法：
    python _w1_apply_ie_renumber.py --dry-run
    python _w1_apply_ie_renumber.py
"""
from __future__ import annotations

import argparse
import pathlib
import re

EVAL = pathlib.Path(__file__).resolve().parent

LEGACY = "MD-AD-006-ISLAND-STRIKE"
NEW = "IE-08-ISLAND-STRIKE"
NEW_SET = ["IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER",
           "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE",
           "IE-14-SATURATION-THREE-WAVE"]

SKIP_FILES = {
    "_w1_apply_ie_renumber.py",
    "_gen_md_ad_006.py",          # 历史生成器：它的输出就是旧名包
    "_gen_ie_set.py",             # docstring 记录编号沿革
    "_gen_ie_set_ext.py",         # 别名逻辑要引旧名
}

# 各脚本里"全场景列表"的最后一项（用来定位并追加六个新场景）
LIST_ANCHORS = {
    "_w1_ie_sweep.py": ['    "MD-AD-006-ISLAND-STRIKE",\n'],
    "_w1_ie_export.py": ['"IE-07-CROSS-DOMAIN", "MD-AD-006-ISLAND-STRIKE",\n'],
    "_w1_ie_table.py": ['"IE-07-CROSS-DOMAIN", "MD-AD-006-ISLAND-STRIKE",\n'],
    "_w1_multiseed.py": ['"IE-07-CROSS-DOMAIN", "MD-AD-006-ISLAND-STRIKE",\n'],
    "_w1_rl_scenario_check.py": ['"IE-07-CROSS-DOMAIN", "MD-AD-006-ISLAND-STRIKE",\n'],
    "_w1_ladder_calc.py": ['"IE-07-CROSS-DOMAIN", "MD-AD-006-ISLAND-STRIKE",\n'],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed: list[str] = []
    for path in sorted(EVAL.glob("*.py")):
        if path.name in SKIP_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        # 1) 功能性改名（含 docstring 里的用法示例）
        text = text.replace(LEGACY, NEW)

        # 2) 全场景列表追加六个新场景
        anchors = LIST_ANCHORS.get(path.name, [])
        for anchor in anchors:
            renamed = anchor.replace(LEGACY, NEW)
            if renamed in text and NEW_SET[0] not in text:
                addition = "".join(f'    "{item}",\n' for item in NEW_SET)
                text = text.replace(renamed, renamed + addition, 1)
        if text == original:
            continue
        count = original.count(LEGACY)
        added = " + 六个新场景" if NEW_SET[0] in text and NEW_SET[0] not in original else ""
        changed.append(f"{path.name}: 改名 {count} 处{added}")
        if not args.dry_run:
            path.write_text(text, encoding="utf-8")

    for line in changed:
        print(f"  {line}")
    print(f"{'（dry-run，未写入）' if args.dry_run else '已写入'}：{len(changed)} 个文件")

    # 残留检查
    leftovers: list[str] = []
    for path in sorted(EVAL.glob("*.py")):
        if path.name in SKIP_FILES:
            continue
        if LEGACY in path.read_text(encoding="utf-8"):
            leftovers.append(path.name)
    print(f"仍引用旧名（应当只剩别名/历史脚本）：{leftovers or '（无）'}")

    # 新场景是否进了全场景列表
    sweep = (EVAL / "_w1_ie_sweep.py").read_text(encoding="utf-8")
    missing = [item for item in NEW_SET if item not in sweep]
    print(f"_w1_ie_sweep.py 缺少的新场景：{missing or '（无）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
