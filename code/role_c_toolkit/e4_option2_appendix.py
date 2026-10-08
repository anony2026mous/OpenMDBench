"""Add the provenance and coverage appendix to the Option-2 document.

The result document reports the analysis; this appendix records what was actually executed, which
raw artefacts back each number, and what is deliberately *not* claimed from them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path("/mnt/<lab>/<user>-codex/experiments/e4-headroom-2x2/P1/option2_result.json")
DEFAULT_DOC = HERE / "artifacts/e4-scenario-family/实验2_选项2_真交互结果.md"

APPENDIX = """
---

## 附录 A. 覆盖范围与出处（逐项可核对）

### A.1 本轮实际执行的局数

| 批次 | 档位 | 臂 / 条件 | seed | 局数 |
|---|---|---|---|---|
| 饱和档定位扫描 | 全部 32 档 | 基线（`--planner rule`，无剂量干预） | 64101 | 32 |
| 配对 2×2 | 5 档（N009/N013/N016/N018/N027） | `--dose strong` 与 `--dose hold` | 64101–64105 | 50 |
| weak 臂（机制对照） | 同上 5 档 | `--goal-granularity weak` | 64101–64105 | 25 |
| 粒度探针 | N013 | 原生 / `medium` / `weak` | 64101 | 3 |
| **合计** | | | | **110** |

### A.2 原始数据位置

- 服务器根目录：`/mnt/<lab>/<user>-codex/experiments/e4-headroom-2x2/P1/`
  - `scan/<package>/`：每档 `report.json`（完整结果 JSON）、`episode.jsonl`（过程日志）
  - `paired/<tier>/<dose>/seed-<n>/`：`report.json`、`episode.jsonl`、
    `action_batches.jsonl`、`defender_states.jsonl`、`stdout.log`、`stderr.log`
  - `granprobe/{none,medium,weak}/`：粒度探针三局
- 交付材料（合作者提供，哈希已全量核验 5077/5077 一致）：
  `…/E1_Exp2_option2_runner_materials_20261006_v1/unpacked/…`
- 分析产物（随本文件交付）：`analysis/e1_2x2_option2.json`

### A.3 判据字段

`report.json → layered_metrics.performance_v`，与既有 E1 证据同字段，故新旧可比。
每局的 `config.arm` / `config.dose` 记录在 `completion.json`，
命令原文在 `attempt_manifest.json`。

### A.4 本文件**未**声称的内容

1. **未与 4151–4160 批次合并**：本文件全部统计只用新跑的 64101–64105，
   旧批次仅作为环境一致性参照（如 N027 旧 0.7482 vs 本扫描 0.7444）。
2. **未把 weak 臂当作独立结果**：实测 weak 与 hold 逐格完全相同
   （总均值均为 0.1774，且对 seed 不敏感），故它只是**机制证据**，
   不构成第二组信息条件。
3. **未声称 headroom 因果**：见正文 §3 的三条限制。
4. **未做跨族合并**：竞争族饱和档（MD-TRK-004 = 0.9666）与本族结果
   分属不同任务与执行器，未合成任何单一统计量。

### A.5 粒度探针的完整取值（可复算）

| 条件 | V |
|---|---|
| 原生 runner（无转换） | 0.9692 |
| `--goal-granularity medium` | 0.9692 |
| `--goal-granularity weak` | 0.1808 |
| 适配器 `--dose strong` | 0.9692 |
| 适配器 `--dose hold` | 0.1808 |

适用边界：这是**单一档位（N013）单一 seed（64101）**的探针，
用于确定操纵机制的量级与是否存在中间档；不是跨档位的分布结论。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()

    if not args.doc.is_file():
        raise SystemExit(f"document not found: {args.doc}")
    text = args.doc.read_text(encoding="utf-8")
    marker = "## 附录 A."
    if marker in text:
        head = text.split(marker)[0].rstrip() + "\n"
        print("已存在附录，重写")
    else:
        head = text.rstrip() + "\n"
    args.doc.write_text(head + APPENDIX, encoding="utf-8")

    data = json.loads(args.source.read_text(encoding="utf-8")) if args.source.is_file() else {}
    lines = args.doc.read_text(encoding="utf-8").splitlines()
    print(f"written {args.doc} ({len(lines)} lines)")
    print(f"  scan={len(data.get('scan') or [])} cells={len(data.get('cells') or [])}")
    print(f"  含附录: {'附录 A' in args.doc.read_text(encoding='utf-8')}")


if __name__ == "__main__":
    main()
