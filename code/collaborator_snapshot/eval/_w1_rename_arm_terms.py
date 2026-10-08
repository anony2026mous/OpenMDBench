"""一次性术语改名：`冻结 llm` → `llm-rule`。

用户指示（2026-09-24）：以后不要把这个臂叫"冻结"。它其实就是
**LLM 规划层 + 规则执行器**的混合臂（代码里 `--planner llm`），
在与 `llm-rl` 配对时只有执行器不同。

命名规范（对称的 2×2 因子设计）：

| 名字 | 规划层 | 执行器 | 代码 |
|---|---|---|---|
| `rule-rule` | 规则 | 规则 | `--planner rule` |
| `llm-rule`  | LLM  | 规则 | `--planner llm`  ← 原"冻结 llm" |
| `rule-rl`   | 规则 | RL   | `--planner rule-rl` |
| `llm-rl`    | LLM  | RL   | `--planner llm-rl` |
| `rl`        | —    | RL   | `--planner rl`（纯 RL 单架构） |
| `pure-llm`  | LLM 直接出动作 | — | `--planner pure-llm` |

"不许改动该臂"这条**约束**仍然成立，但改成直说"不改动/不许动"，
不再用"冻结"当名字。只改我自己维护的三份文档；历史交接文档
（HANDOFF_*）是过去指示的记录，不改写。
"""
from __future__ import annotations

import pathlib

DOCS = [
    "LLMRL_EXPERIMENT_DESIGN.md",
    "LLMRL_CURRENT_AUDIT.md",
    "LLMRL_STATUS_REPORT.md",
]

# 顺序重要：先长后短，避免短模式先吃掉长模式的前缀。
REPLACEMENTS: list[tuple[str, str]] = [
    ("`llm`（**冻结臂**）", "`llm-rule`"),
    ("`llm`（冻结）", "`llm-rule`"),
    ("`llm-rl` > `llm`（冻结）", "`llm-rl` > `llm-rule`"),
    ("冻结臂 `llm`", "`llm-rule`"),
    ("冻结的 `llm`", "`llm-rule`"),
    ("冻结 `llm`", "`llm-rule`"),
    ("原 llm（冻结）", "`llm-rule`"),
    ("原 `llm` 臂冻结", "`llm-rule` 的规划器 / 客户端 / 执行器一律不改动"),
    ("冻结的原 llm 臂", "`llm-rule` 臂"),
    ("原 llm 臂", "`llm-rule` 臂"),
    ("冻结层级臂", "`llm-rule`"),
    ("冻结规则执行器", "规则执行器"),
    ("与冻结规则臂同语义", "与 `llm-rule` 臂同语义"),
    ("冻结的规则执行器", "`llm-rule` 的规则执行器"),
    ("动冻结的规则执行器", "改 `llm-rule` 的规则执行器"),
    ("动冻结臂", "改 `llm-rule` 臂"),
    ("（动冻结臂）", "（要改 `llm-rule` 臂）"),
    ("冻结臂自身", "`llm-rule` 自身"),
    ("冻结臂需当前口径重跑", "`llm-rule` 需当前口径重跑"),
    ("冻结臂不能动", "`llm-rule` 臂不能动"),
    ("与冻结臂同构", "与 `llm-rule` 同构"),
    ("与冻结臂对等", "与 `llm-rule` 对等"),
    ("冻结臂在 t=10", "`llm-rule` 在 t=10"),
    ("冻结臂同样只打 6 发", "`llm-rule` 同样只打 6 发"),
    ("冻结臂 IE-05 seed 7 同配置重复", "`llm-rule` IE-05 seed 7 同配置重复"),
    ("冻结臂 IE-03", "`llm-rule` IE-03"),
    ("冻结臂", "`llm-rule` 臂"),
    ("# 3. 三组实验框架（文件地图 + 冻结线）", "# 3. 三组实验框架（文件地图 + 不许改动清单）"),
    ('撞到"冻结"边界', "撞到用户边界"),
    ("保持冻结", "保持不动"),
]


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    for name in DOCS:
        path = root / name
        text = path.read_text(encoding="utf-8")
        original = text
        counts: dict[str, int] = {}
        for old, new in REPLACEMENTS:
            n = text.count(old)
            if n:
                text = text.replace(old, new)
                counts[old] = n
        if text == original:
            print(f"[skip] {name}（无需改动）")
            continue
        path.write_text(text, encoding="utf-8")
        print(f"[done] {name}: {sum(counts.values())} 处")
        for old, n in counts.items():
            print(f"        {n:2}× {old!r} -> {dict(REPLACEMENTS)[old]!r}")
    # 残留检查
    print("\n== 残留 '冻结' 检查 ==")
    for name in DOCS:
        text = (root / name).read_text(encoding="utf-8")
        left = [line.strip() for line in text.splitlines() if "冻结" in line]
        print(f"{name}: {len(left)} 行")
        for line in left:
            print(f"    {line[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
