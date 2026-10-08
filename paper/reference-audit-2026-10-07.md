# OpenMDBench 投稿（AAMAS 2027）参考文献核验报告（修订版 v3）

**核验对象**：`main.pdf` 第 8–9 页 References 列表 47 条（[1]–[47]），逐一对应 `refs.bib` 中的 47 个被引用条目。  
**核验日期**：2026-10-07（第 5 轮终审后更新）　**核验文件**：`main.pdf`、`refs.bib`（路径见文末）  
**核验轮次**：第 1 轮全量核验（8 单元）→ 第 2 轮对抗式证伪（8 单元）→ 第 3 轮定向复核（3 单元）→ 第 4 轮**盲审式重推**（8 单元，不给任何既有结论，从一手来源重新推导官方记录并自行判定 must-fix/minor）→ 第 5 轮终审（5 单元：新数据裁定、对“干净条目”与“需小修条目”各做一次 must-fix 红队、正文引用与被引文献一致性检查）。另有我本人逐条打开出版社/会议一手记录复核：ACL 录用版 PDF（[1]、[47]）、JMLR/PMLR/TMLR 官方页与 BibTeX、NeurIPS 官方 BibTeX 与论文页、IFAAMAS 会议录目录与 PDF（[27]、[28]）、Crossref（12 个 DOI）、arXiv API（12 个预印本的 journal_ref/doi/comment 全扫）。

## 一、结论摘要

- **真实性**：46 条能查到真实文献；**[37] `fedrlsurvey` 经 10 个检索通道复核仍查无此文，判定为虚构/严重错配**（见第四节 [37] 行与第十节检索清单）。
- **必须修改 17 条**（每条都至少经两轮独立核验复现）：[4] [7] [19] [28] [26] [14] [46] [38] [5] [20] [21] [45] [44] [18] [33] [40] ＋ 查无此文 [37]。其中 8 条是“已正式发表却只引 arXiv”（[14] [19] [26] [28] [38] [46] 等）或“出处/年份错”，4 条是作者姓名错（[4] [7] [33] [44]）或漏作者（[18] [21] [45]），3 条是标题措辞/题名错（[4] [5] [40] 类型）。
- **需小修 11 条**：[3] [13] [24] [25] [30] [36] [10] [31] [47] [1] [2]。
- **仅缺页码/DOI/卷次 19 条**：[6] [8] [9] [11] [12] [15] [16] [17] [22] [23] [27] [29] [32] [34] [35] [39] [41] [42] [43]。
- **格式**：47 条**全部没有 DOI**；42 条没有页码；6 条条目类型明确错误（[4] [14] [19] [26] [28] [40]），另有 [38] 应引期刊版而非预印本、[36] 未标研讨会出处（可商榷档）；多条 booktitle 缺会议录卷次/分卷。
- **结论稳定性**：第一轮的 13 条必须修改项在第 2–5 轮**全部被独立复现**；第 4 轮盲审另把 [18] [33] [40] 从“需小修”提升为 must-fix，第 5 轮红队又独立坐实 [33] 的作者名错误，并确认 [38] 的期刊版真实存在。同时有 **3 条我先前的轻微指控被推翻**（见第二节）。
- **未发现的问题类别**（已专门检查、结果为空）：参考文献重复或近似重复 0 处；正文引用键与印刷列表一一对应、无悬空引用；12 个 arXiv 编号全部对应该文，无“编号指向他文”；13 处正文引用断言与被引文献摘要一致（无“引错文献支持论点”）。

## 二、对上一版报告的更正（诚实说明）

| # | 上一版说法 | 复核结果 | 处理 |
|---|---|---|---|
| 1 | [1] `whenbenchtargets`：部分作者被加了官方没有的中间名 | 已下载 ACL 录用版 PDF（`aclanthology.org/2024.acl-long.744.pdf`）第 1 页逐字比对，论文署名本身就是 “Norah A. Alzahrani, Hisham Abdullah Alyahya, …, Shaykhah Z. Alsubaie, …, Faisal Abdulrahman Mirza, Nouf M. Alotaibi”，与 `.bib` 完全一致；是 ACL Anthology 的元数据把中间名规范化掉了 | **撤回**该指控；仅保留 “Altwairesh 应为 Al-Twairesh” 与 “M. Saiful Bari 多一个句点” |
| 2 | [31] `coala`：第一作者应为 “Theodore R. Sumers” | TMLR 官方 BibTeX（`jmlr.org/tmlr/papers/bib/1i6ZCvflQJ.bib`）作者为 “Theodore Sumers and Shunyu Yao and Karthik R Narasimhan and Thomas L. Griffiths”，“R.” 只出现在 arXiv 版 | **撤回**；[31] 降为“可选微调”（第三作者可补 R、期刊名可去 “(TMLR)”） |
| 3 | [33] `pettingzoo`：第一作者 “Justin” 属可接受的全名展开（**v2 曾据此降级**） | 第 5 轮红队指出应为 Jordan：作者本人维护的 `Farama-Foundation/PettingZoo` **CITATION.cff** 写明 `given-names: Jordan / family-names: Terry / email: j.k.terry@swarmlabs.com`，与 NeurIPS 论文 PDF 首页脚注邮箱完全一致；NeurIPS 官方 BibTeX 亦作 “Terry, J”。OpenAlex 的 “Justin K. Terry” 是第三方索引的臆测。 | **推翻 v2 的降级**：[33] 重新列为必须修改（given name 应为 Jordan），并补卷 34 与页码 15032–15043 |
| 4 | [35] `valmeekam23` / [32] `sutton99` 的题名标点与大小写差异 | [35] 属官方记录内部不一致（会议录目录用破折号、论文 PDF 与 arXiv 用冒号）；[32] 属 BibTeX 花括号保护缩写的标准写法 | **不计为错误**，仅在“新增发现”中说明 |
| 5 | [38] `weinberg25`：第 5 轮某一核验单元称“未检索到正式出版版本，预印本引用恰当” | 该单元只查了 arXiv。Crossref（DOI 10.1007/s44163-026-01543-2）明确记录 Springer《Discover Artificial Intelligence》**vol. 6, issue 1, article 566，2026-06-18 在线发表**；OpenAlex 亦同 | **维持** [38] 为必须修改（应引期刊版、年份 2026）；该单元结论系检索面不足所致 |

## 三、本轮新增发现（此前未列）

| 编号 | 键 | 新增问题 |
|---|---|---|
| [1] | `whenbenchtargets` | booktitle 缺 “(Volume 1: Long Papers)”；`M. Saiful Bari` 官方作 `M Saiful Bari`（无句点，极轻微） |
| [3] | `reflectivellm` | booktitle 缺会议录卷次 “Advances in Neural Information Processing Systems 37” |
| [5] | `llmarena` | booktitle 缺 “(Volume 1: Long Papers)” |
| [6] | `hemac` | 作者连字符形式与 IOS Press/Crossref 规范化记录不同（`Junior Samuel Lopez Yepez` vs `Junior-Samuel Lopez-Yepez`）——与作者自署的 arXiv 版一致，**非错误**，仅记录 |
| [7] | `smacv2` | booktitle 缺卷 36 且未标 “Datasets and Benchmarks Track”（官方 OpenReview BibTeX 明确标注该 track） |
| [11] | `l2m2` | 官方标注 Main Track，条目未注 |
| [13] | `marllib` | **题名大小写错误**：官方 JMLR 页面、官方 BibTeX、arXiv 三处均为 “Multi-agent”（小写 a），条目作 “Multi-Agent” |
| [21] | `gaia` | **题名大小写错误**：官方题名为 “GAIA: a benchmark for General AI Assistants”（小写 a benchmark），条目作 “A Benchmark” |
| [47] | `multiagentbench` | **题名末词大小写错误**：官方为 “LLM agents”（arXiv 与 ACL 官方 BibTeX 一致），条目作 “LLM Agents”；booktitle 缺 “(Volume 1: Long Papers)” |
| [33] | `pettingzoo` | **第一作者 given name 错误**（应为 Jordan Terry，见第二节第 3 条）；booktitle 缺卷 34；作者截断（官方 13 人） |
| [28] | `shefin26` | 官方页码 **2347–2355** 已确认（IFAAMAS 会议录目录 “(Page 2347)” ＋ 官方 PDF 末页页脚 “2355”），条目缺页码与正式出处 |
| [27] | `smac` | 官方页码 **2186–2188** 已由 IFAAMAS 官方 PDF 三页页眉 (2186)(2187)(2188) 确认，条目缺页码 |
| [23] | `llmagentsurvey25` | 官方会议录卷册标识为 **V.2**（Crossref container-title），条目 booktitle 未标 |
| [15] | `kambhampati24` | 官方 PMLR 作者表为 “Lucas Paul Saldyt”“Anil B Murthy”，条目用 arXiv 简写（可选） |
| [35] | `valmeekam23` | 会议录目录题名用破折号、论文与 arXiv 用冒号，属出版方内部不一致；条目采用作者定稿形式，无需修改 |
| [32] | `sutton99` | 题名大小写为 Elsevier 句首式与标题式之别，BibTeX 花括号已保护缩写，无需修改 |

## 四、必须修改（P0，17 条，每条均经 ≥2 轮独立核验复现）

| 编号 | 键 | 问题 | 建议 |
|---|---|---|---|
| [4] | `benchmarl` | 作者全错（真实作者 Bettini/Prorok/Moens）；出处错（JMLR 25(217):1–10, 2024，非 ICML 2023）；年份、类型、副标题亦错。 | 整条重写：`@article`，作者 Bettini, Matteo; Prorok, Amanda; Moens, Vincent；journal=Journal of Machine Learning Research, volume=25, number=217, pages=1--10, year=2024；标题改 “BenchMARL: Benchmarking Multi-Agent Reinforcement Learning” |
| [7] | `smacv2` | 第 2 作者错位，第 3 作者 “Robert Faulkner” 在全部官方记录中不存在（应为 Cook、Moalla）；缺 Datasets & Benchmarks track、卷 36、页码 37567–37593。 | 作者改为 Ellis, Benjamin; Cook, Jonathan; Moalla, Skander; Samvelyan, Mikayel; Sun, Mingfei; Mahajan, Anuj; Foerster, Jakob N.; Whiteson, Shimon；booktitle 注明 Datasets and Benchmarks Track，补 pages=37567--37593 |
| [37] | `fedrlsurvey` | 题名、作者、期刊、年份四项在 10 个检索通道（arXiv/OpenAlex 题名与全文/Crossref 题名与 ISSN 限定/Semantic Scholar 精确匹配/IEEE 存缴/Google·Bing 精确串等）中均查无记录，判定为虚构或严重错配。 | **删除**，或替换为可核验的真实综述（如 Qi, Jiaju; Zhou, Qihao; Lei, Lei; Zheng, Kan. Federated reinforcement learning: techniques, applications, and open challenges. Intelligence & Robotics 1(1):15--30, 2021, doi=10.20517/ir.2021.02） |
| [19] | `decrypto` | 已正式发表 ICML 2026（PMLR 306:83284–83323），条目仍按 2025 arXiv 引用，年份错误，类型应为 @inproceedings。 | 改为 ICML 2026 正式版：`@inproceedings`，booktitle=Proceedings of the 43rd International Conference on Machine Learning, series=PMLR, volume=306, pages=83284--83323, year=2026 |
| [28] | `shefin26` | 题目/作者/年份正确，但该文已正式发表于 AAMAS 2026（官方页码 2347–2355 已确认），条目仅按 arXiv 引用，类型应为 @inproceedings。 | 改为 AAMAS 2026 正式版：`@inproceedings`，booktitle=Proceedings of the 25th International Conference on Autonomous Agents and Multiagent Systems (AAMAS), year=2026, doi=10.65109/GWFE6009 |
| [26] | `rigaki23` | 作者拼写错误（Lukoš 应为 Lukáš）；已正式发表 ICAART 2024（pp. 774–781），条目按 2023 arXiv 引用，年份与出处均需更新。 | 作者改 Lukáš, Ondřej；改为 ICAART 2024 会议版：`@inproceedings`，pages=774--781, year=2024, doi=10.5220/0012391800003636 |
| [14] | `lgcmarl` | 题目/作者/年份正确，但该文已正式发表于 ICRA 2025（pp. 1240–1246），条目仅按 arXiv 引用，类型应为 @inproceedings。 | 改为 ICRA 2025 会议版：`@inproceedings`，booktitle=2025 IEEE International Conference on Robotics and Automation (ICRA), pages=1240--1246, doi=10.1109/ICRA55743.2025.11127486 |
| [46] | `lamarl` | 题目/4 位作者/年份正确；该文已正式发表于 IEEE RA-L 10(7):7476–7483, 2025，条目仅按 arXiv 引用，字段需改为正式期刊信息。 | 改为期刊版：journal=IEEE Robotics and Automation Letters, volume=10, number=7, pages=7476--7483, year=2025, doi=10.1109/LRA.2025.3577527 |
| [38] | `weinberg25` | 预印本本身真实（arXiv:2511.15716）；但该文已正式发表于 Discover Artificial Intelligence 6(1):566, 2026，条目应改为期刊版、年份 2026。 | 改为期刊正式版：`@article`，journal=Discover Artificial Intelligence, volume=6, number=1, pages=566, year=2026, doi=10.1007/s44163-026-01543-2 |
| [5] | `llmarena` | 作者/会议/年份正确；标题副题错误（官方 “Assessing Capabilities of …”，非 “Evaluating …”）；缺页码 13055–13077、DOI，booktitle 缺卷次。 | 副标题改 “Assessing Capabilities of Large Language Models in Dynamic Multi-Agent Environments”；booktitle 补 “(Volume 1: Long Papers)”；补 pages=13055--13077, doi=10.18653/v1/2024.acl-long.705 |
| [20] | `ape` | 作者/年份/研讨会论文性质正确，但研讨会名错误：EWRL = European Workshop on Reinforcement Learning（第 17 届，2024，图卢兹），非 “Deep Reinforcement Learning Workshop”。 | booktitle 改为 17th European Workshop on Reinforcement Learning (EWRL 2024)，可补 address=Toulouse, France 与 note=Non-archival |
| [21] | `gaia` | 作者多一人（Craig Swift 仅见 arXiv 版，ICLR 2024 正式版 5 人）；题名大小写与官方不符（官方 “a benchmark”）；ICLR 无页码属正常。 | 删除 Craig Swift（ICLR 2024 正式版为 Mialon, Fourrier, Wolf, LeCun, Scialom 五人）；题名改 “GAIA: a benchmark for General AI Assistants” |
| [45] | `webarena` | 题名/ICLR 2024/年份正确；作者表漏第 8 作者 Tianyue Ou（官方 12 人）。 | 补第 8 作者 Ou, Tianyue（位于 Cheng, Xianyi 之后） |
| [44] | `defenderbench` | 第 3 作者应为 Michael Albada（条目作 Albadawy）；其余 8 位作者、题名、年份正确；该工作仅有非存档 workshop 海报，按 arXiv 引用符合政策。 | 第 3 作者改为 Albada, Michael |
| [18] | `agentbench` | 题目/ICLR 2024/年份正确；作者表漏 Yuxiao Dong 与 Jie Tang（官方 22 人，条目仅 20 人且未标 “and others”，等于谎报作者表完整）。 | 补齐作者表（官方 22 人，补 Dong, Yuxiao 与 Tang, Jie 两位），或明确以 “and others” 截断 |
| [33] | `pettingzoo` | 第一作者名错误：NeurIPS 官方 PDF 作 “J. K. Terry”，而作者本人的 CITATION.cff（j.k.terry@swarmlabs.com，与论文 PDF 邮箱一致）写明 given name 为 Jordan，条目作 “Justin” 不实；作者表截断（官方 13 人），缺卷 34 与页码 15032–15043。 | 第一作者改为 Terry, Jordan（官方 proceedings 作 “J. K. Terry”）；booktitle 补卷 34（Advances in NeurIPS 34）；补 pages=15032--15043；按需补齐 13 位作者 |
| [40] | `spinbench` | 题名/8 位作者/年份正确，确为 COLM 2025 论文；但把会议论文写成 @article 并把会议名放进 journal 字段，属条目类型错误，应改 @inproceedings。 | 改为 `@inproceedings`，booktitle={The Second Conference on Language Modeling (COLM)}，year=2025，并把会议名从 journal 字段移出 |

## 五、建议修改（P1，11 条）

| 编号 | 键 | 问题 | 建议 |
|---|---|---|---|
| [3] | `reflectivellm` | 题目/会议/年份正确；末位作者应为 Ji-Rong Wen（条目作 Jirong Wen）；缺卷 37、页码 138595–138631 与 DOI。 | 末位作者改为 Wen, Ji-Rong；booktitle 补 “Advances in Neural Information Processing Systems 37”；补 pages=138595--138631 |
| [13] | `marllib` | 题名大小写与官方不符：官方 JMLR 与 arXiv 均作 “Multi-agent”，条目作 “Multi-Agent”；卷 24、期 315、页 1–23、年份均正确。 | 题名大小写改为 “Multi-agent”（与 JMLR 官方一致） |
| [24] | `chathtn25` | 题目/会议（NeuS 2025, PMLR 288）/年份正确；姓氏连字符丢失（Muñoz-Avila 印作 “Muñoz Avila”）；缺页码 446–458。 | 确保姓氏连字符保留（Mu\~noz-Avila），补 pages=446--458 |
| [25] | `gorila` | 题目/前三位作者/arXiv 编号/年份正确；作者表截断（官方 14 人）；实为 ICML 2015 Deep Learning Workshop 论文，未标注出处；@article 承载预印本可商榷。 | 补出 14 位作者或至少标注 workshop 出处（ICML 2015 Deep Learning Workshop） |
| [30] | `hivex` | 题目/作者/arXiv 编号/年份正确，无正式存档出版（另有 ICLR 2025 CCAI workshop 报告）；@article 承载预印本可商榷。 | 类型可改 `@misc`；如需可注明 ICLR 2025 CCAI workshop（非存档） |
| [36] | `cyberbattlesim` | 题目/3 位作者/年份正确；该文实为 IJCAI-21 第 1 届 Adaptive Cyber Defense 研讨会论文，条目未给出研讨会出处；@article 类型不当。 | 改为 `@inproceedings`，booktitle 注明 IJCAI-21 1st International Workshop on Adaptive Cyber Defense |
| [10] | `lshc` | 题目/作者/年份与 arXiv 记录一致，无正式出版记录，按预印本引用符合 .bib 头部政策；@article 承载预印本属可商榷写法。 | 类型可改 `@misc` + eprint 字段（该文无正式出版记录，按 arXiv 引用本身正确） |
| [31] | `coala` | 题目/TMLR/年份正确；TMLR 官方 BibTeX 与条目作者一致（第一作者无须改），可选把第三作者写作 “Narasimhan, Karthik R” 并去掉期刊名后的 “(TMLR)”。 | 无需修改；可选：第三作者写 “Narasimhan, Karthik R”，期刊名去掉 “(TMLR)” |
| [47] | `multiagentbench` | 题名末词官方作 “LLM agents”（条目作 Agents）；缺页码 8580–8622、DOI，booktitle 缺 “(Volume 1: Long Papers)”。 | 题名末词改 “LLM agents”；booktitle 补 “(Volume 1: Long Papers)”；补 pages=8580--8622, doi=10.18653/v1/2025.acl-long.421 |
| [1] | `whenbenchtargets` | 题目/出处正确；唯一实质差异是 Altwairesh 应为官方写法 Al-Twairesh（论文 PDF 亦带连字符），另 Bari 后多一个句点；缺页码 13787–13805、DOI，booktitle 缺 “(Volume 1: Long Papers)”。 | Altwairesh 改为 Al-Twairesh（论文 PDF 亦带连字符）；booktitle 补 “(Volume 1: Long Papers)”；补 pages=13787--13805, doi=10.18653/v1/2024.acl-long.744 |
| [2] | `cicero22` | 题目/期刊/卷期页全部正确；作者表以 et al. 截断（官方含 FAIR 团队署名），缺 DOI。 | 作者截断可接受；如需完整可补 FAIR 团队署名与 doi=10.1126/science.ade9097 |

## 六、仅需补全信息（P2，19 条：官方有页码/DOI/卷号而条目缺）

| 编号 | 键 | 建议补充 |
|---|---|---|
| [6] | `hemac` | volume=413, pages=3290--3296, doi=10.3233/FAIA251197 |
| [8] | `impala` | series=PMLR, volume=80, pages=1407--1416 |
| [9] | `coma` | volume=32, number=1, pages=2974--2982, doi=10.1609/aaai.v32i1.11794 |
| [11] | `l2m2` | pages=99--107, doi=10.24963/ijcai.2025/12, note=Main Track |
| [12] | `mindagent` | pages=3154--3183, doi=10.18653/v1/2024.findings-naacl.200 |
| [15] | `kambhampati24` | series=PMLR, volume=235, pages=22895--22907 |
| [16] | `grf` | volume=34, number=4, pages=4501--4510, doi=10.1609/aaai.v34i04.5878 |
| [17] | `meltingpot` | pages=6187--6199 |
| [22] | `a3c` | series=PMLR, volume=48, pages=1928--1937 |
| [23] | `llmagentsurvey25` | pages=6129--6139, doi=10.1145/3711896.3736570 |
| [27] | `smac` | pages=2186--2188 |
| [29] | `hugginggpt23` | volume=36, pages=38154--38180 |
| [32] | `sutton99` | doi=10.1016/S0004-3702(99)00052-1 |
| [34] | `triantafyllou25` | 可选 arXiv:2410.12539（页码已正确） |
| [35] | `valmeekam23` | volume=36, pages=75993--76005, doi=10.52202/075280-3320 |
| [39] | `capa25` | pages=7247--7264, doi=10.18653/v1/2026.findings-acl.359 |
| [41] | `poac` | 可选 doi=10.48550/arXiv.2112.03809 |
| [42] | `react` | 可选 url=https://openreview.net/forum?id=WE_vluYUL-X |
| [43] | `openfedllm` | doi=10.1145/3637528.3671582 |

## 七、逐条核验结果（47 条）

判据：**内容无误** = 题名/作者/出处/年份匹配且类型恰当（缺页码/DOI 见第六节）；**需小修** = 轻微不一致或类型可商榷；**有实质错误** = 作者张冠李戴、出处或年份错误、类型明确错误；**查无此文** = 权威索引中不存在。
“复核状态”列：**双轮确认** = 第 2 轮对抗复核独立复现第一轮结论；**复核有更正** = 第 2 轮对第一轮的表述提出修正（见第二节）。

| # | 引用键 | 判定 | 类型 | 复核状态 | 核验要点 |
|---|---|---|---|---|---|
| 1 | `whenbenchtargets` | ⚠️ 需小修 | 恰当 | 复核有更正 | 题目/出处正确；唯一实质差异是 Altwairesh 应为官方写法 Al-Twairesh（论文 PDF 亦带连字符），另 Bari 后多一个句点；缺页码 13787–13805、DOI，booktitle 缺 “(Volume 1: Long Papers)”。 |
| 2 | `cicero22` | ⚠️ 需小修 | 恰当 | 双轮确认 | 题目/期刊/卷期页全部正确；作者表以 et al. 截断（官方含 FAIR 团队署名），缺 DOI。 |
| 3 | `reflectivellm` | ⚠️ 需小修 | 恰当 | 双轮确认 | 题目/会议/年份正确；末位作者应为 Ji-Rong Wen（条目作 Jirong Wen）；缺卷 37、页码 138595–138631 与 DOI。 |
| 4 | `benchmarl` | ❗实质错误 | **错误** | 复核有更正 | 作者全错（真实作者 Bettini/Prorok/Moens）；出处错（JMLR 25(217):1–10, 2024，非 ICML 2023）；年份、类型、副标题亦错。 |
| 5 | `llmarena` | ❗实质错误 | 恰当 | 双轮确认 | 作者/会议/年份正确；标题副题错误（官方 “Assessing Capabilities of …”，非 “Evaluating …”）；缺页码 13055–13077、DOI，booktitle 缺卷次。 |
| 6 | `hemac` | ✅ 内容无误 | 恰当 | 复核有更正 | 题目/作者/会议/年份正确（作者连字符写法与预印本一致，非错误）；缺卷 413、页码 3290–3296 与 DOI。 |
| 7 | `smacv2` | ❗实质错误 | 恰当 | 双轮确认 | 第 2 作者错位，第 3 作者 “Robert Faulkner” 在全部官方记录中不存在（应为 Cook、Moalla）；缺 Datasets & Benchmarks track、卷 36、页码 37567–37593。 |
| 8 | `impala` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/会议/年份/前三位作者正确；作者表截断（官方 12 人）；缺 PMLR 卷 80、页码 1407–1416。 |
| 9 | `coma` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/会议/年份/作者全对；缺 volume 32、number 1、页码 2974–2982 与 DOI。 |
| 10 | `lshc` | ⚠️ 需小修 | 可商榷 | 双轮确认 | 题目/作者/年份与 arXiv 记录一致，无正式出版记录，按预印本引用符合 .bib 头部政策；@article 承载预印本属可商榷写法。 |
| 11 | `l2m2` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/作者/会议/年份正确；缺页码 99–107 与 DOI，可补 note=Main Track。 |
| 12 | `mindagent` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/作者/Findings NAACL 2024/年份全部正确；缺页码 3154–3183 与 DOI。 |
| 13 | `marllib` | ⚠️ 需小修 | 恰当 | 复核有更正 | 题名大小写与官方不符：官方 JMLR 与 arXiv 均作 “Multi-agent”，条目作 “Multi-Agent”；卷 24、期 315、页 1–23、年份均正确。 |
| 14 | `lgcmarl` | ❗实质错误 | **错误** | 双轮确认 | 题目/作者/年份正确，但该文已正式发表于 ICRA 2025（pp. 1240–1246），条目仅按 arXiv 引用，类型应为 @inproceedings。 |
| 15 | `kambhampati24` | ✅ 内容无误 | 恰当 | 复核有更正 | 题目/作者/ICML 2024/年份正确；缺 PMLR 卷 235 与页码 22895–22907（官方作者中名更全，属可选）。 |
| 16 | `grf` | ✅ 内容无误 | 恰当 | 复核有更正 | 题目/11 位作者/AAAI 2020 全部正确；缺 volume 34、number 4、页码 4501–4510 与 DOI。 |
| 17 | `meltingpot` | ✅ 内容无误 | 恰当 | 复核有更正 | 题目/10 位作者/ICML 2021/卷 139 正确；缺页码 6187–6199。 |
| 18 | `agentbench` | ❗实质错误 | 恰当 | 双轮确认 | 题目/ICLR 2024/年份正确；作者表漏 Yuxiao Dong 与 Jie Tang（官方 22 人，条目仅 20 人且未标 “and others”，等于谎报作者表完整）。 |
| 19 | `decrypto` | ❗实质错误 | **错误** | 双轮确认 | 已正式发表 ICML 2026（PMLR 306:83284–83323），条目仍按 2025 arXiv 引用，年份错误，类型应为 @inproceedings。 |
| 20 | `ape` | ❗实质错误 | 恰当 | 双轮确认 | 作者/年份/研讨会论文性质正确，但研讨会名错误：EWRL = European Workshop on Reinforcement Learning（第 17 届，2024，图卢兹），非 “Deep Reinforcement Learning Workshop”。 |
| 21 | `gaia` | ❗实质错误 | 恰当 | 复核有更正 | 作者多一人（Craig Swift 仅见 arXiv 版，ICLR 2024 正式版 5 人）；题名大小写与官方不符（官方 “a benchmark”）；ICLR 无页码属正常。 |
| 22 | `a3c` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/会议/年份/前三位作者正确；作者表截断（官方 8 人）；缺 PMLR 卷 48、页码 1928–1937。 |
| 23 | `llmagentsurvey25` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/4 位作者/KDD 2025/年份正确；缺页码 6129–6139 与 DOI。 |
| 24 | `chathtn25` | ⚠️ 需小修 | 恰当 | 双轮确认 | 题目/会议（NeuS 2025, PMLR 288）/年份正确；姓氏连字符丢失（Muñoz-Avila 印作 “Muñoz Avila”）；缺页码 446–458。 |
| 25 | `gorila` | ⚠️ 需小修 | 可商榷 | 双轮确认 | 题目/前三位作者/arXiv 编号/年份正确；作者表截断（官方 14 人）；实为 ICML 2015 Deep Learning Workshop 论文，未标注出处；@article 承载预印本可商榷。 |
| 26 | `rigaki23` | ❗实质错误 | **错误** | 双轮确认 | 作者拼写错误（Lukoš 应为 Lukáš）；已正式发表 ICAART 2024（pp. 774–781），条目按 2023 arXiv 引用，年份与出处均需更新。 |
| 27 | `smac` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/10 位作者/AAMAS 2019/年份全部正确；缺页码 2186–2188（已由 IFAAMAS 官方 PDF 页眉确认）与 DOI 10.65109/lvzz5205。 |
| 28 | `shefin26` | ❗实质错误 | **错误** | 双轮确认 | 题目/作者/年份正确，但该文已正式发表于 AAMAS 2026（官方页码 2347–2355 已确认），条目仅按 arXiv 引用，类型应为 @inproceedings。 |
| 29 | `hugginggpt23` | ✅ 内容无误 | 恰当 | 双轮确认 | 题目/6 位作者/NeurIPS 2023 正确；缺卷 36、页码 38154–38180 与 DOI。 |
| 30 | `hivex` | ⚠️ 需小修 | 可商榷 | 双轮确认 | 题目/作者/arXiv 编号/年份正确，无正式存档出版（另有 ICLR 2025 CCAI workshop 报告）；@article 承载预印本可商榷。 |
| 31 | `coala` | ⚠️ 需小修 | 恰当 | 复核有更正 | 题目/TMLR/年份正确；TMLR 官方 BibTeX 与条目作者一致（第一作者无须改），可选把第三作者写作 “Narasimhan, Karthik R” 并去掉期刊名后的 “(TMLR)”。 |
| 32 | `sutton99` | ✅ 内容无误 | 恰当 | 双轮确认 | 卷 112、期 1–2、页码 181–211、年份全部正确；题名大小写为排版风格差异（花括号保护），非错误；仅缺 DOI。 |
| 33 | `pettingzoo` | ❗实质错误 | 恰当 | 双轮确认 | 第一作者名错误：NeurIPS 官方 PDF 作 “J. K. Terry”，而作者本人的 CITATION.cff（j.k.terry@swarmlabs.com，与论文 PDF 邮箱一致）写明 given name 为 Jordan，条目作 “Justin” 不实；作者表截断（官方 13 人），缺卷 34 与页码 15032–15043。 |
| 34 | `triantafyllou25` | ✅ 内容无误 | 恰当 | 双轮确认 | 题名/4 位作者/ICML 2025 第 42 届/PMLR 267/页码 60072–60098/年份全部吻合，是格式最完整的条目之一。 |
| 35 | `valmeekam23` | ✅ 内容无误 | 恰当 | 双轮确认 | 题名/4 位作者/NeurIPS 2023/年份正确；冒号与破折号之分属官方记录内部不一致（会议录目录用破折号、论文 PDF 与 arXiv 用冒号），不计为错误；缺卷 36、页码 75993–76005、DOI。 |
| 36 | `cyberbattlesim` | ⚠️ 需小修 | 可商榷 | 双轮确认 | 题目/3 位作者/年份正确；该文实为 IJCAI-21 第 1 届 Adaptive Cyber Defense 研讨会论文，条目未给出研讨会出处；@article 类型不当。 |
| 37 | `fedrlsurvey` | ⛔ 查无此文 | 可商榷 | 双轮确认 | 题名、作者、期刊、年份四项在 10 个检索通道（arXiv/OpenAlex 题名与全文/Crossref 题名与 ISSN 限定/Semantic Scholar 精确匹配/IEEE 存缴/Google·Bing 精确串等）中均查无记录，判定为虚构或严重错配。 |
| 38 | `weinberg25` | ❗实质错误 | 恰当 | 双轮确认 | 预印本本身真实（arXiv:2511.15716）；但该文已正式发表于 Discover Artificial Intelligence 6(1):566, 2026，条目应改为期刊版、年份 2026。 |
| 39 | `capa25` | ✅ 内容无误 | 恰当 | 双轮确认 | 题名/17 位作者/Findings of ACL 2026/年份全部正确；缺页码 7247–7264 与 DOI。 |
| 40 | `spinbench` | ❗实质错误 | **错误** | 双轮确认 | 题名/8 位作者/年份正确，确为 COLM 2025 论文；但把会议论文写成 @article 并把会议名放进 journal 字段，属条目类型错误，应改 @inproceedings。 |
| 41 | `poac` | ✅ 内容无误 | 恰当 | 双轮确认 | 题名/8 位作者/年份与 arXiv:2112.03809 一致，无正式出版记录，按预印本引用符合政策。 |
| 42 | `react` | ✅ 内容无误 | 恰当 | 双轮确认 | 题名/7 位作者/ICLR 2023/年份正确（notable top 5% oral）；ICLR 无页码，建议补 OpenReview 链接。 |
| 43 | `openfedllm` | ✅ 内容无误 | 恰当 | 双轮确认 | 题名/9 位作者/KDD 2024/页码 6137–6147/年份全部正确；仅缺 DOI 10.1145/3637528.3671582。 |
| 44 | `defenderbench` | ❗实质错误 | 可商榷 | 双轮确认 | 第 3 作者应为 Michael Albada（条目作 Albadawy）；其余 8 位作者、题名、年份正确；该工作仅有非存档 workshop 海报，按 arXiv 引用符合政策。 |
| 45 | `webarena` | ❗实质错误 | 恰当 | 双轮确认 | 题名/ICLR 2024/年份正确；作者表漏第 8 作者 Tianyue Ou（官方 12 人）。 |
| 46 | `lamarl` | ❗实质错误 | 可商榷 | 双轮确认 | 题目/4 位作者/年份正确；该文已正式发表于 IEEE RA-L 10(7):7476–7483, 2025，条目仅按 arXiv 引用，字段需改为正式期刊信息。 |
| 47 | `multiagentbench` | ⚠️ 需小修 | 恰当 | 复核有更正 | 题名末词官方作 “LLM agents”（条目作 Agents）；缺页码 8580–8622、DOI，booktitle 缺 “(Volume 1: Long Papers)”。 |

## 八、格式规范问题汇总

1. **DOI 全缺**：47 条中 0 条给出 DOI；ACM 参考格式与 AAMAS 审稿习惯通常要求正式出版文献带 DOI。
2. **页码缺失 42 条**，其中 19 条官方记录明确有页码（第六节已列出），本轮又为 [27] 2186–2188、[28] 2347–2355、[33] 15032–15043 找到并确认了官方页码。
3. **条目类型误用**：明确错误 7 条（[4] [14] [19] [26] [28] [40] ＋ [38] 的“期刊版却按预印本”）；可商榷 6 条（[10] [25] [30] [36] [37] [44] [46] 中的预印本/研讨会写法），多为用 `@article` + `journal` 承载 arXiv 预印本，建议改 `@misc` + `eprint`。
4. **booktitle 缺会议录卷次/分卷**：[1] [5] [21] [47] 缺 “(Volume 1: Long Papers)”；[3] 缺 “Advances in NeurIPS 37”；[7] 缺卷 36 与 “Datasets and Benchmarks Track”；[33] 缺卷 34；[11] 缺 “Main Track”；[23] 缺 “V.2”。
5. **作者表用 `and others` 截断**：8 条（[2] [4] [7] [8] [22] [25] [33] [37]）。其中 [4] [7] 的截断掩盖了错误/虚构作者名，风险最高。
6. **题名大小写/措辞细节**：[13] “Multi-agent”、[21] “a benchmark”、[47] “LLM agents”、[5] 副题动词、[4] 副标题，共 5 条与官方字符串不完全一致。
7. **渲染细节**：多条在 PDF 中呈现为 “In Advances in Neural Information Processing Systems (NeurIPS) .” 的句号前空格，属 `ACM-Reference-Format.bst` 在缺页码时的标点行为，补页码后消失。
8. **未引用条目**：`refs.bib` 中的 `tomagent`（Li 等，EMNLP 2023，DOI 10.18653/v1/2023.emnlp-main.13）未被正文引用，不会出现在 PDF 中，建议删除或补引。
9. **正文措辞提示（非参考文献著录错误）**：正文第 143 行称 [1] 为 “Position work”，但 [1] 是带系统实验的 ACL 2024 实证长文（非 position paper），建议改为 “Empirical work / Prior work”。

## 九、修正 BibTeX（可直接粘贴）

```bibtex
@article{benchmarl,
  author  = {Bettini, Matteo and Prorok, Amanda and Moens, Vincent},
  title   = {{BenchMARL}: Benchmarking Multi-Agent Reinforcement Learning},
  journal = {Journal of Machine Learning Research},
  volume  = {25},
  number  = {217},
  pages   = {1--10},
  year    = {2024},
}

@inproceedings{smacv2,
  author    = {Ellis, Benjamin and Cook, Jonathan and Moalla, Skander and Samvelyan, Mikayel and Sun, Mingfei and Mahajan, Anuj and Foerster, Jakob N. and Whiteson, Shimon},
  title     = {{SMACv2}: An Improved Benchmark for Cooperative Multi-Agent Reinforcement Learning},
  booktitle = {Advances in Neural Information Processing Systems 36 (NeurIPS), Datasets and Benchmarks Track},
  pages     = {37567--37593},
  year      = {2023},
}

% [37] 原条目经 10 个检索通道确认查无此文，建议改用可核验的真实综述：
@article{fedrlsurvey,
  author  = {Qi, Jiaju and Zhou, Qihao and Lei, Lei and Zheng, Kan},
  title   = {Federated Reinforcement Learning: Techniques, Applications, and Open Challenges},
  journal = {Intelligence \& Robotics},
  volume  = {1},
  number  = {1},
  pages   = {15--30},
  year    = {2021},
  doi     = {10.20517/ir.2021.02},
}

@inproceedings{decrypto,
  author    = {Lupu, Andrei and Willi, Timon and Foerster, Jakob Nicolaus},
  title     = {The {Decrypto} Benchmark for Multi-Agent Reasoning and Theory of Mind},
  booktitle = {Proceedings of the 43rd International Conference on Machine Learning (ICML)},
  series    = {Proceedings of Machine Learning Research},
  volume    = {306},
  pages     = {83284--83323},
  year      = {2026},
}

@inproceedings{shefin26,
  author    = {Shefin, Risal Shahriar and Gupta, Debashis and Le, Thai and Alqahtani, Sarra},
  title     = {Interpretable Failure Analysis in Multi-Agent Reinforcement Learning Systems},
  booktitle = {Proceedings of the 25th International Conference on Autonomous Agents and Multiagent Systems (AAMAS)},
  pages     = {2347--2355},
  year      = {2026},
  doi       = {10.65109/GWFE6009},
}

@inproceedings{pettingzoo,
  author    = {Terry, Jordan and Black, Benjamin and Grammel, Nathaniel and Jayakumar, Mario and Hari, Ananth and Sullivan, Ryan and Santos, Luis S. and Dieffendahl, Clemens and Horsch, Caroline and Perez-Vicente, Rodrigo and Williams, Niall and Lokesh, Yashas and Ravi, Praveen},
  title     = {{PettingZoo}: {Gym} for Multi-Agent Reinforcement Learning},
  booktitle = {Advances in Neural Information Processing Systems 34 (NeurIPS)},
  pages     = {15032--15043},
  year      = {2021},
}

@inproceedings{rigaki23,
  author    = {Rigaki, Maria and Luk{\'a}{\v{s}}, Ond{\v{r}}ej and Catania, Carlos A. and Garcia, Sebastian},
  title     = {Out of the Cage: How Stochastic Parrots Win in Cyber Security Environments},
  booktitle = {Proceedings of the 16th International Conference on Agents and Artificial Intelligence (ICAART)},
  pages     = {774--781},
  year      = {2024},
  doi       = {10.5220/0012391800003636},
}

@inproceedings{lgcmarl,
  author    = {Jia, Ziqi and Li, Junjie and Qu, Xiaoyang and Wang, Jianzong},
  title     = {Enhancing Multi-Agent Systems via Reinforcement Learning with {LLM}-based Planner and Graph-based Policy},
  booktitle = {2025 IEEE International Conference on Robotics and Automation (ICRA)},
  pages     = {1240--1246},
  year      = {2025},
  doi       = {10.1109/ICRA55743.2025.11127486},
}

@article{lamarl,
  author  = {Zhu, Guobin and Zhou, Rui and Ji, Wenkang and Zhao, Shiyu},
  title   = {{LAMARL}: {LLM}-Aided Multi-Agent Reinforcement Learning for Cooperative Policy Generation},
  journal = {IEEE Robotics and Automation Letters},
  volume  = {10},
  number  = {7},
  pages   = {7476--7483},
  year    = {2025},
  doi     = {10.1109/LRA.2025.3577527},
}

@inproceedings{llmarena,
  author    = {Chen, Junzhe and Hu, Xuming and Liu, Shuodi and Huang, Shiyu and Tu, Wei-Wei and He, Zhaofeng and Wen, Lijie},
  title     = {{LLMArena}: Assessing Capabilities of Large Language Models in Dynamic Multi-Agent Environments},
  booktitle = {Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages     = {13055--13077},
  year      = {2024},
  doi       = {10.18653/v1/2024.acl-long.705},
}

@inproceedings{gaia,
  author    = {Mialon, Gr{\'e}goire and Fourrier, Cl{\'e}mentine and Wolf, Thomas and LeCun, Yann and Scialom, Thomas},
  title     = {{GAIA}: a benchmark for General {AI} Assistants},
  booktitle = {The Twelfth International Conference on Learning Representations (ICLR)},
  year      = {2024},
}

@article{marllib,
  author  = {Hu, Siyi and Zhong, Yifan and Gao, Minquan and Wang, Weixun and Dong, Hao and Liang, Xiaodan and Li, Zhihui and Chang, Xiaojun and Yang, Yaodong},
  title   = {{MARLlib}: A Scalable and Efficient Multi-agent Reinforcement Learning Library},
  journal = {Journal of Machine Learning Research},
  volume  = {24},
  number  = {315},
  pages   = {1--23},
  year    = {2023},
}

@inproceedings{multiagentbench,
  author    = {Zhu, Kunlun and Du, Hongyi and Hong, Zhaochen and Yang, Xiaocheng and Guo, Shuyi and Wang, Zhe and Wang, Zhenhailong and Qian, Cheng and Tang, Xiangru and Ji, Heng and You, Jiaxuan},
  title     = {{MultiAgentBench}: Evaluating the Collaboration and Competition of {LLM} agents},
  booktitle = {Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages     = {8580--8622},
  year      = {2025},
  doi       = {10.18653/v1/2025.acl-long.421},
}

@inproceedings{ape,
  author    = {Maddila, Prasanna and Casellas, Eric and Chabrier, Patrick and Sabbadin, R{\'e}gis and Vinyals, Meritxell},
  title     = {{APE}: An Anti-poaching Multi-Agent Reinforcement Learning Benchmark},
  booktitle = {17th European Workshop on Reinforcement Learning (EWRL)},
  address   = {Toulouse, France},
  year      = {2024},
  note      = {Non-archival},
}

@article{weinberg25,
  author  = {Weinberg, Abraham Itzhak},
  title   = {{MACIE}: Multi-Agent Causal Intelligence Explainer for Collective Behavior Understanding},
  journal = {Discover Artificial Intelligence},
  volume  = {6},
  number  = {1},
  pages   = {566},
  year    = {2026},
  doi     = {10.1007/s44163-026-01543-2},
}

@inproceedings{whenbenchtargets,
  author    = {Alzahrani, Norah A. and Alyahya, Hisham Abdullah and Alnumay, Yazeed and Alrashed, Sultan and Alsubaie, Shaykhah Z. and Almushayqih, Yousef and Mirza, Faisal Abdulrahman and Alotaibi, Nouf M. and Al-Twairesh, Nora and Alowisheq, Areeb and Bari, M Saiful and Khan, Haidar},
  title     = {When Benchmarks are Targets: Revealing the Sensitivity of Large Language Model Leaderboards},
  booktitle = {Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages     = {13787--13805},
  year      = {2024},
  doi       = {10.18653/v1/2024.acl-long.744},
}

```

## 十、核验方法与局限

- **方法与轮次**：
  1. 解析 `main.pdf` 抽取印刷版参考文献表（47 条），用特征标题匹配与 `refs.bib` 建立**一一对应**（无重复键、无遗漏键）；
  2. 第 1 轮：8 个并行核验单元逐条比对题名/作者/出处/年份/类型；
  3. 第 2 轮（对抗式）：另 8 个单元以“证伪前一版”为目标，强制打开一手记录（官方 BibTeX、会议录页、出版社页），并新增核对“条目已有卷期页是否写错”“官方卷期页是否缺失”“arXiv 编号是否对应该文”；
  4. 第 3 轮（定向）：3 个单元只查争议项与新增指控，并对 [37] 与 [4] 从零重新推导；我本人同时下载 ACL 录用版 PDF 逐字核对 [1] 的作者行。
  5. 第 4 轮（盲审）：8 个单元**不给任何既有结论**，各自从一手来源重新推导官方记录并自行把差异分为 must_fix / minor；我把结果与既有分类逐条对差，得到 2 项升级、0 项误报、若干新增元数据。
  6. 第 5 轮（终审）：5 个单元——新数据裁定、对 19 条“干净条目”与 11 条“需小修条目”各做一次 must_fix 红队、正文 13 处引用断言与被引文献摘要的一致性检查。
  7. 我本人的一手复核（贯穿全程）：ACL `.bib` 与录用版 PDF（[1] [47]）、JMLR/PMLR/TMLR 官方页与 BibTeX、NeurIPS 官方 BibTeX 与论文页、IFAAMAS 会议录目录与 PDF（[27] [28]）、Crossref 12 个 DOI、arXiv API 对 12 个预印本的 `journal_ref`/`doi`/`comment` 全扫（用于判定“是否已有正式出版版本”）、以及重复引用/悬空引用的机器检查。
- **结论稳定性**：17 条必须修改项中，13 条经 5 轮全部复现；[18] [33] [40] 由第 4 轮盲审独立升级；[33] 的作者名错误由第 5 轮红队用作者本人的 CITATION.cff 坐实；[38] 的期刊版经 Crossref 复核确认。**先后有 3 条我先前的指控被推翻/降级、1 条降级被再次推翻（[33] 最终仍判为错误）**，均已写入第二节。
- **局限**：
  1. [37] 对 DBLP 的直连被反爬拦截，IEEE Xplore 检索页为动态渲染，但 IEEE 期刊论文均向 Crossref 存缴 DOI，Crossref 的 ISSN 限定检索已覆盖该集合；[37] 的结论基于 10 个通道的一致结果。
  2. OpenReview 的 PDF 与部分 API 端点对自动访问返回 403（Cloudflare），相关结论改以 ICLR/NeurIPS 官方站点、TMLR 官方 BibTeX 与 arXiv 佐证。
  3. OpenAlex 的共享配额在本次核验后期耗尽（HTTP 429），第 5 轮起改以 arXiv/ACL/PMLR/Crossref/出版社页面为准；OpenAlex 曾给出 “Justin K. Terry” 的臆测姓名，已被作者一手 CITATION.cff 推翻，说明第三方索引不宜作为姓名唯一依据。
  4. 官方记录之间偶有不一致（如 [35] 会议录目录用破折号而论文用冒号、[33] 会议录 HTML 作 “J KTerry”），此类情形按“以论文定稿/作者自署为准”处理，不计为条目错误。

---

**附**：逐条机读表见同目录 `reference-audit-2026-10-07.csv`（含判定、复核状态、新增发现、问题描述、权威记录与证据链接）。