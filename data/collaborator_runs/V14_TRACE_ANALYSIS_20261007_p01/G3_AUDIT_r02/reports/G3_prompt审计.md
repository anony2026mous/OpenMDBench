# G3 no-intelligence prompt审计材料

方法：对冻结场景timeline、历史谓词审计脚本及当前ROE实现逐项对照；区分配置事实、历史注释、现行实现和实际请求记录。当前declared分支已经修复分类缺陷，不能把它重建为旧错误提示词。

K1：`real air package ... declared NON-THREAT`。A true armed package was falsely designated non-threatening by substring matching. 来源类别：historical code-comment excerpt, not verbatim archived request。

K2：`do NOT intercept or fire at it`。Suppresses correct engagement; not an independent second diagnosed bug. 来源类别：second component of the same failure。

K3：`spawn_tick / count / axis / behavior`。Makes the briefing channel different from no-intel. Do not claim it independently caused losses. 来源类别：privileged future information, not necessarily a misleading directive。

行为文本命中非威胁关键词、但label自身未命中的候选波次详见analysis/result.json；候选不自动等于实测错误指令。K1/K2是同一根因的两个组件，不凑成两项独立因果发现。

最新论文tab:nointel架构对应：LLM+RL +0.000、LLM+Rule +0.021、Pure LLM −0.085。已从新资料包CSV与JSON逐行一致性核验后，使用原统计脚本按场景等权重算；未在异批、异seed数比较上虚构配对CI。精确值：{"llm-rule": {"withheld": 0.773727142857143, "withheld_n": 70, "declared": 0.7526922845804987, "declared_n": 82, "scenarios_withheld_better": 9, "scenarios_compared": 14, "delta": 0.021034858276644197}, "llm-rl": {"withheld": 0.78271, "withheld_n": 70, "declared": 0.7824966666666666, "declared_n": 49, "scenarios_withheld_better": 8, "scenarios_compared": 14, "delta": 0.00021333333333339866}, "pure-llm": {"withheld": 0.4309771428571428, "withheld_n": 70, "declared": 0.5160571428571429, "declared_n": 40, "scenarios_withheld_better": 4, "scenarios_compared": 14, "delta": -0.0850800000000001}}

尚缺：legacy实际请求原文及对应批次。没有编辑论文稿件。现有证据支持“识别出误导性内容与信息不对等”，不支持“逐条指令的独立因果效应已被隔离”。
