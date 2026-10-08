"""公平性审计取证：ROE/平民惩罚、传感器噪声口径、能量是否真的会耗尽。"""
import re

import yaml

BASE = "/root/source_codes_linux/source_codes/scenarios/formal"
for name in ("md_int_006_saturation_roe", "md_ad_002_easy", "md_int_003_easy"):
    data = yaml.safe_load(open(f"{BASE}/{name}/scenario.yaml", encoding="utf-8"))
    scen = data["scenario"]
    print(f"=== {name} ===")
    print("  roe_rules:", scen["world"].get("roe_rules"))
    scoring = scen.get("scoring") or {}
    for metric in scoring.get("metrics", ()):
        print("  score:", metric.get("id"), "selector=", metric.get("selector"),
              "weight=", metric.get("weight"))
    for rule in scen.get("mission_rules", ()):
        cond = rule.get("condition", {})
        print("  mission_rule:", rule.get("id"), "sel=", cond.get("selector"),
              "params=", cond.get("parameters"))
    text = open(f"{BASE}/{name}/scenario.yaml", encoding="utf-8").read()
    print("  'civilian' 出现次数:", text.count("civilian"))

print()
print("=== 传感器版本与噪声字段（AD-002 vs INT-003）===")
cat = open("/root/source_codes_linux/source_codes/catalog/v2/md_ad_002.yaml",
           encoding="utf-8").read()
for match in re.finditer(r"id: (sensor\.[\w.-]+)\n\s+version: ([\d.]+)[\s\S]{0,400}?content: \{(.*?)\}", cat):
    sid, ver, content = match.groups()
    noise = "range_noise_fraction" in content or "bearing_noise_deg" in content
    print(f"  {sid}@{ver} noise_fields={noise}")
