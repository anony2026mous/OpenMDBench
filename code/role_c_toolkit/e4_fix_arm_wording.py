"""Correct the arm description in the earlier 2x2 result document.

The arms were originally described as differing in goal information.  Per-episode
``completion.json`` shows both carry ``dose=strong``; the difference is ``config.greedy``.  This
script rewrites those specific lines in the two copies of that document and leaves everything else
untouched, so the corrected file is a faithful record rather than a regenerated one.
"""

from __future__ import annotations

from pathlib import Path

TARGETS = [
    Path("e5_ascii/Exp2_2x2_result.md"),
    Path("role_c_toolkit/artifacts/e4-scenario-family/实验2_2x2_交互结果.md"),
]

OLD_TABLE = """| 臂 | 含义 |
|---|---|
| **`rule-strong-g1`** | 规则规划器 + **有**目标信息（规划信息多） |
| **`rule-strong-g0`** | 规则规划器 + **无**目标信息（规划信息少） |
| `rule-hold-g0` | 不做规划（空转对照） |
| `rule-rl-strong-g0` | 分层：规则规划 + RL 执行 |
| `rule-rl-hold-g0` | 分层：空转规划 + RL 执行 |

**关键**：`rule-strong-g1` 与 `rule-strong-g0` 是**同一规划器、同一执行器，只差目标信息**——
这正是 v3 要求的「同一执行器，只改变规划信息量」。"""

NEW_TABLE = """| 臂 | `config.dose` | `config.greedy` | 含义 |
|---|---|---|---|
| **`rule-strong-g1`** | `strong` | **`true`** | 规则规划器 + 最近接触贪心分配 |
| **`rule-strong-g0`** | `strong` | **`false`** | 规则规划器 + 默认分配 |
| `rule-hold-g0` | `hold` | `false` | 目标被改写为 hold（空转对照） |
| `rule-rl-strong-g0` | `strong` | `false` | 分层：规则规划 + RL 执行 |
| `rule-rl-hold-g0` | `hold` | `false` | 分层：空转规划 + RL 执行 |

**更正（后续核实）**：`rule-strong-g1` 与 `rule-strong-g0` 的**剂量相同（均为 `strong`）**，
差异是 `greedy` 分配规则——即**规划器的分配决策规则**，**不是信息量**。
本节因此衡量的是「决策形态」，不是「规划信息量」。
量级对照（供参考）：本节的分配规则差异约 **+0.08**，而真正的信息量操纵（完整计划 vs
降级计划，见合并报告 Study 2）约为 **+0.70**。"""

OLD_SECTION = "## 2. 2×2 结果（规划信息 × 数量条件）"
NEW_SECTION = "## 2. 结果（分配规则 × 数量条件）"

OLD_HEADER = "| 条件 | n | 信息多 | 信息少 | **增益** | 95% CI |"
NEW_HEADER = "| 条件 | n | `greedy=true` | `greedy=false` | **差值** | 95% CI |"

OLD_IMPACT = "1. **规划信息杠杆有效**：四个条件全部为正增益，两个条件（N017、N027）的 95% CI 不含 0。\n   → v3 要求的「操纵有效性」得到了验证，**阳性对照成立**。"
NEW_IMPACT = "1. **分配规则差异可测**：四个条件全部为正差值，两个条件（N017、N027）的 95% CI 不含 0。\n   → 决策形态在本族中确有约 +0.08 的代价。"


def main() -> None:
    for path in TARGETS:
        if not path.is_file():
            print(f"skip (missing): {path}")
            continue
        text = path.read_text(encoding="utf-8")
        changes = 0
        for old, new in ((OLD_TABLE, NEW_TABLE), (OLD_SECTION, NEW_SECTION),
                         (OLD_HEADER, NEW_HEADER), (OLD_IMPACT, NEW_IMPACT)):
            if old in text:
                text = text.replace(old, new)
                changes += 1
        if changes:
            path.write_text(text, encoding="utf-8")
        print(f"{path}: {changes} 处已修正")
        remaining = [line.strip()[:70] for line in text.splitlines()
                     if ("信息多" in line or "信息少" in line
                         or "有**目标信息" in line or "无**目标信息" in line)
                     and "更正" not in line]
        if remaining:
            print(f"  仍有可疑行 {len(remaining)}:")
            for line in remaining[:4]:
                print(f"    {line}")


if __name__ == "__main__":
    main()
