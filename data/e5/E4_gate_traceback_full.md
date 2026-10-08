# 门禁排除名单：追溯、构成、污染核查与措辞改动

> 本文回应三个问题：**门禁排除名单是谁设的、名单在哪**；
> **55 个条目是怎么构成的**；**论文图与数据有没有被不该计入的场景污染**。
> 所有数字在生成时从 `admission_ledger.json`、`analysis/d2_graded_final2.json`、
> `d1prime_FROZEN.json` 读出，可复算。

## 1. 门禁排除名单是谁设的、在哪

**不是更早的实验负责人做的，是本次 E4 场景族重标定建立的。**

| 问题 | 答案 |
|---|---|
| 谁做的 | 本角色（<author-C>），E4 交付项「场景族构建与入场 + D1′ 属性标注」 |
| 什么时候 | 2026-10-03～04 的标定批次（seeds 2001–2005 → 2101–2105 → 2201–2205 → 2301–2305） |
| 名单在哪 | `role_c_toolkit/artifacts/e4-scenario-family/admission_ledger.json`（schema `e4-admission-ledger@2`） |
| 每条含什么 | `public_id`、`package`、`package_sha256`、`gates.*.verdict`、`gates.*.evidence`、`note`、`success_rate`、`ci95` |
| 工具 | `role_c_toolkit/d2_headroom.py`（二值口径）、`d2_headroom_graded.py`（综合分口径）、`e4_build_ledger.py`（按序重建） |

**对方提到的两个说法需要更正：**

| 外部说法 | 实际 |
|---|---|
| 「原冻结门禁筛查记录未提供」 | 记录存在且为机读 JSON，55 条逐场景，每条带证据文件路径 |
| 「当前只核实到 24 个独立正式包」 | 24 是 `formal` 树的包数；D2 判定覆盖的是 `competition_v1` 的 30 个包 |
| 「在 2 号服务器 `/root/huairou-project`」 | 本项目在怀柔机 `/mnt/<lab>/<user>-codex/`，无 `/root/huairou-project` 路径 |

## 2. 55 个条目是怎么构成的

台账共 **55 条 = 54 个场景包 + 1 条别名重复**。

| 来源 | 包数 | 明细 |
|---|---|---|
| `competition_v1`（本次重标定，<author-C>） | **30** | 侦察搜索 10、持续跟踪 8、区域拒止 6、应急响应 6 |
| `formal` 正式 IE（早期实验，非本次） | **14** | IE-01…IE-14 |
| `formal` 演示包（不计入正式实验） | **10** | MD-INT-002、MD-INT-003×3、MD-INT-005、MD-INT-006、MD-AD-002×3、MD-AD-004 |
| **合计** | **54** | |

**别名重复**（同包两个 public_id）：

- `ie_08_island_strike` ← IE-08-ISLAND-STRIKE、MD-AD-006-ISLAND-STRIKE

### 各种「多少个场景」的口径换算

| 口径 | 数 | 定义 |
|---|---|---|
| 台账条目 | **55** | 含 1 条别名 |
| 去重场景包 | **54** | 30 + 14 + 10 |
| 剔除演示包 | **44** | = D1′ 先验标注覆盖数（两者完全一致） |
| 再合并 REC-001 三档 | **42** | 若一个难度算一个实验 |
| **本次重标定的场景数** | **28** | competition_v1 去 REC-001 变体（30 − 2） |
| 其中早期正式 IE | **14** | 非本次工作 |

## 3. 门禁判定：两个口径必须分列

台账同时记录两个口径，**它们回答不同问题，数字也不同**：

| 口径 | 判据 | 全台账 (55 条) | 竞争族 (30 包) | **本次 28 场景** |
|---|---|---|---|---|
| **二值成功**（事前预注册） | 场景声明的 terminal outcome 成功率 ∈ [0.40, 0.85] | pass 3 / fail 32 | pass 3 / fail 27 | **pass 3 / fail 25** |
| **声明综合分**（utility-v1） | 场景声明的 Σ wᵢ·valueᵢ ∈ [0.40, 0.85] | — | pass 16 / fail 14 | **pass 16 / fail 12** |

**为什么必须有综合分口径**：确定性脚本策略的成功率只有 0/1，跨 5 个 seed 也只会取 0、0.2 … 1.0；因此二值口径下多数场景恒为 1.000，**永远进不了窗口**，判据不可判。

**落在窗口之外的场景**：全台账 14 个；本次 28 场景口径 12 个。

> 全台账的 14 个 = 竞争族 12 个（综合分口径）+ 早期 `formal` 包 2 个（MD-AD-002 一档、MD-AD-004-DECEPTION，只有二值口径的判定，无综合分）。

## 4. 论文数据与附图的污染核查

黑名单 = 上表 10 个演示包 + 别名 `MD-AD-006-ISLAND-STRIKE`。对被检查的每一份数据/脚本/图，做包名与公开 ID 双模式扫描。

| 被检对象 | 场景引用 | 是否命中黑名单 |
|---|---|---|
| `figA4_natural_failure_pilot_12.csv`（<author-C>） | IE-03、IE-08、grid | **否** |
| `figA2_replanning_sweep.csv`（<author-C>） | 无 | **否** |
| `make_figs_A2_A4.py` / `设计说明_A2_A4.md`（<author-C>） | 无 | **否** |
| `fig3_hifi_gap.csv`（<author-B>） | **正好 IE-01…IE-14** | **否** |
| `figA1_model_invariance.csv`（<author-B>） | 无（模型 × 指标） | **否** |
| `figA3_dose_gain.csv`（<author-B>） | 无（stack × dose） | **否** |
| Fig.1 / Fig.2（阚思颖） | 无数据（纯示意） | **否** |
| v11 实验强化清单 | 仅 IE-05、MD-AD-001、MD-TRK-002、MD-TRK-005 | **否** |

**结论：论文图与数据没有用到任何不该计入的场景。**

补充核查（<author-B>数据内部一致性）：

| README 声称 | 从 CSV 复算 | 结论 |
|---|---|---|
| LLM+RL beat Rule **11/14** | 11/14（败于 IE-03、IE-04、IE-12） | 一致 |
| LLM+RL beat RL **12/14** | 12/14（败于 IE-01、IE-03） | 一致 |
| Pure LLM trails LLM+RL on **13/14** | 13/14（例外 IE-03） | 一致 |
| gap 列 = 两列之差 | 14 行 × 2 列全部成立 | 一致 |
| 「end-to-end LLM trails (0.43; **14/14 behind**)」 | 落后于 **layered 最优**：14/14；落后于**全部四个基线**：9/14 | **建议显式写「behind the layered stack」** |

## 5. 措辞改动清单

### 5.1 v11 清单 L50（必须改，属口径混淆）

**原文：**

> 门禁台账：55 场景；D1′ 先验覆盖 44；D2 16 pass / 19 fail / 20 pending；D1 blocked 2 / not_applicable 51 / reported 2。

**问题**：「16 pass」是综合分口径、「19 fail」是二值口径，并列后会被读成同一口径的 16/19/20。

**建议改为：**

> **门禁台账**：55 条目（54 个包 + 1 条别名）；D1′ 先验覆盖 44。
> **D2 两口径分列**：二值口径 pass 3 / fail 32 / pending 20；综合分口径（竞争族 30 包）pass 16 / fail 14。
> 窗口外场景 12 个（11 个天然饱和 + 1 个触底），逐场景清单见 `E4_28场景数据汇总.md`。

### 5.2 关于「多少个场景」

- 报包数时写「**30 个竞争包**」，报场景数时写「**28 个场景**（REC-001 三档合并）」——两个数都要带单位。
- 论文附录若要写总场景数，建议写「**44 个正式场景**（54 包 − 10 个演示包）」，并注明「其中本次重标定 28 个」。

### 5.3 关于「IE-05 数量 19」

- E1 承接里的「IE-05 数量 19」指**正式 IE-05-MULTI-AXIS 场景的目标数量档**，与演示包 `MD-INT-005` 无关。
- 建议写成「`IE-05-MULTI-AXIS` 的 19 目标档」，避免与 `MD-INT-005` 混淆。

### 5.4 关于「gates 外 layered 输」的验证对象

不必手动筛选，窗口外场景已逐条列出；**优先用 11 个天然饱和场景**（未被本次标定调整过），最干净。

## 6. 复算方式

```bash
# 门禁判定（二值口径）
python role_c_toolkit/d2_headroom.py --plan <plan.json> --state <state.json> \
  --output .../analysis/d2_headroom_final2.json

# 声明综合分口径
python role_c_toolkit/d2_headroom_graded.py --plan <plan.json> --state <state.json> \
  --scenarios openmd/source-code/source_codes/scenarios/competition_v1 \
  --evidence-root .../analysis/evidence-final2 \
  --output .../analysis/d2_graded_final2.json

# 台账重建（按顺序：inventory → d1prime → d2 → d2-graded → report）
python role_c_toolkit/e4_build_ledger.py --artifacts role_c_toolkit/artifacts/e4-scenario-family \
  --source openmd/source-code/source_codes \
  --grid-doc openmd/doc/grid_environment_reference.md \
  --contracts openmd/doc/competition_four_categories/SCENARIO_CONTRACTS.json \
  --design-root . --d1-report <E10 summary.json>

# 28 场景汇总（本文件引用的窗口外清单）
python role_c_toolkit/e4_scenario28_pack.py
```

---

**一句话总结**：门禁名单是本次 E4 重标定产出的、就在 `admission_ledger.json` 里（55 条 = 54 包 + 1 别名）；论文图与数据**未污染**；v11 清单 L50 的「16 pass / 19 fail」需按两口径分列。
