# 案例 E5-12-9ab3 — LLM 规划器原始输出

## 调用 0（tick 0）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4000, 1500]}, "priority": 0.5},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6000, 1500]}, "priority": 0.5},
    {"task_id": "patrol_uav_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8000, 1500]}, "priority": 0.5},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4000, 0]}, "priority": 0.5},
    {"task_id": "patrol_uav_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6000, 0]}, "priority": 0.5},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [8000, 0]}, "priority": 0.5},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [4000, -1500]}, "priority": 0.5},
    {"task_id": "patrol_uav_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [6000, -1500]}, "priority": 0.5},
    {"task_id": "patrol_uav_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8000, -1500]}, "priority": 0.5},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1500, -500]}, "priority": 0.5},
    {"task_id": "patrol_usv_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2600, -1500]}, "priority": 0.5},
    {"task_id": "patrol_usv_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1400, -2400]}, "priority": 0.5}
  ],
  "reasoning": "No hostile contacts detected in the current situation. All units are holding their patrol positions to maintain sensor coverage and readiness for incoming threats."
}
```

## 调用 1（tick 10）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4130.0, 1622.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6036.0, 1648.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8002.0, 1706.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3909.0, -139.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6123.0, -37.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [7874.0, 84.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3984.0, -1689.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5975.0, -1366.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8072.0, -1343.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1518.0, -511.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2609.0, -1492.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1408.0, -2395.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (dist_zone > 8000m) and approaching stably. Interceptors and sensors are holding position to conserve energy and maintain coverage until threats enter the engagement window."
}
```

## 调用 2（tick 20）

```
{
  "goal_commands": [
    {"task_id": "track_boat01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.9},
    {"task_id": "track_boat02_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.pier.intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_boat04_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-09.intruder.boat-04"}, "priority": 0.7},
    {"task_id": "patrol_uav01_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4258.0, 1772.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6127.0, 1823.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8002.0, 1963.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3735.0, -274.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6152.0, -240.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [7632.0, 120.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_010", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3928.0, -1897.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_011", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5915.0, -1229.0]}, "priority": 0.5},
    {"task_id": "patrol_uav09_012", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8204.0, -1185.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept set to true. The surface threats (boats) are the highest priority but are currently outside the effective engagement window for the USVs (feasible=false for most, or long ETAs). The USVs are tasked to track the closest surface threats to maintain continuous observation and prepare for future engagement. The UAVs are holding position/patrolling as the air threats are far away (dist > 14km) and not yet in the intercept window (prepare=false). This conserves ammunition and maintains situational awareness."
}
```

## 调用 3（tick 30）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 378},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 487},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4403.0, 1904.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6256.0, 1976.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8009.0, 2219.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3525.0, -336.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6182.0, -440.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [7389.0, 150.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3825.0, -2087.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5856.0, -1094.0]}, "priority": 0.5},
    {"task_id": "patrol_uav09_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8337.0, -1025.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-01, boat-02, boat-03) are the primary threats, with high threat scores (0.79-0.82) and relatively short distances to the protected zone (7.8-9.3 km). The USVs are the only units with feasible intercept ETAs for these targets (UAVs have infeasible ETAs for surface targets). USV-02 is assigned to boat-01 (closest, highest threat, feasible ETA 160t), USV-01 to boat-02 (feasible ETA 378t), and USV-03 to boat-03 (feasible ETA
```

## 调用 4（tick 40）

```
{
  "goal_commands": [
    {"task_id": "track_boat_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-01"}, "priority": 0.95},
    {"task_id": "track_boat_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.90},
    {"task_id": "track_boat_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03"}, "priority": 0.85},
    {"task_id": "ambush_fuel_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-fuel-01"}, "priority": 0.80},
    {"task_id": "ambush_comms_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-comms-01"}, "priority": 0.75},
    {"task_id": "ambush_cmd_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-command-01"}, "priority": 0.70},
    {"task_id": "reserve_uav_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [4532.0, 2050.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-04", "position": [3308.0, -371.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-05", "position": [6189.0, -644.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [7144.0, 173.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav_005", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [3760.0, -2299.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav_006", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [5799.0, -957.0], "commit_within_m": 9000}, "priority": 0.60}
  ],
  "reasoning": "No targets currently have can_intercept or prepare_intercept=true. The three surface boats are high-threat (0.78-0.81) but far from the zone (7.7-9.2km) and moving slowly; USVs are assigned to track them to maintain observation. The three air targets are medium-threat (0.28-0.49) and far away (22-29km). UAV-09, UAV-03, and UAV-02 are the closest to their respective air targets and are assigned to ambush at lead intercept points to conserve ammo and position for future engagement. Remaining UAVs are held in reserve to react to any new threats or if the primary ambushers fail."
}
```

## 调用 5（tick 50）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4617.0, 2227.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3103.0, -296.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6219.0, -842.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6897.0, 194.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3556.0, -2379.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5741.0, -823.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1732.0, -652.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2550.0, -1346.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1339.0, -2303.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. The three air targets are far away (dist > 13km) with long ETAs. The surface targets are closer but have low closing speeds and are not yet in the intercept window for the USVs (feasible=false for most, or long feasible_eta). Maintaining the current intercept assignments for the air targets allows the UAVs to close the distance and prepare for engagement. The remaining UAVs and USVs hold position to maintain sensor coverage and readiness."
}
```

## 调用 6（tick 60）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1787.0, -691.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2532.0, -1302.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1315.0, -2275.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4699.0, 2405.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2895.0, -345.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6229.0, -1045.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6653.0, 206.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3513.0, -2587.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5683.0, -687.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. The three air intruders (strike-comms-01, strike-fuel-01, strike-command-01) are approaching but still far from the protected zone (dist_zone > 21km) and outside weapon range. I am assigning the closest available interceptors (uav-09, uav-03, uav-02) to track/intercept these air threats to prepare for engagement as they close. The surface boats (boat-01, boat-02, boat-03) are closer to the zone but moving slowly and are currently outside the effective intercept window for the USVs (feasible=false for most). I am holding the USVs in patrol positions to maintain sensor coverage and prepare for potential engagement if the boats continue their approach. The remaining UAVs are held in patrol to maintain coverage and
```

## 调用 7（tick 70）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.facility.command.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 200},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1844.0, -727.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2512.0, -1260.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1291.0, -2247.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4768.0, 2591.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2677.0, -351.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6238.0, -1248.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6406.0, 214.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3373.0, -2762.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5629.0, -549.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. The air threats (strike-fuel-01, strike-comms-01, strike-command-01) are approaching but still far (dist > 11km, ttr > 75 ticks). UAV-09 is closest to strike-fuel-01 (highest threat 0.52) and is already tasked, so it continues intercept to close the gap. UAV-03 is closest to strike-comms-01 (threat 0.48) and continues its intercept. UAV-02 is closest to strike-command-01 (threat 0.28) and continues its intercept. Surface threats (boats) are slow and far from the zone (dist_zone > 7km), and USVs are holding position to
```

## 调用 8（tick 80）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1900.0, -764.0]}, "priority": 0.8},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2494.0, -1217.0]}, "priority": 0.8},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1267.0, -2219.0]}, "priority": 0.8},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4831.0, 2780.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7992.0, 3492.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2460.0, -341.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6245.0, -1451.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6159.0, 224.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3269.0, -2960.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5573.0, -411.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the closest high-threat air target (threat 0.53, TTR 55.5t). UAV-02 is assigned to intercept strike-comms-01 (threat 0.49, TTR 57.6t) as it is the observer and has prepare_intercept=true. Surface boats (boat-01, 02, 04) are high threat but have feasible=false for all interceptors, meaning they will reach the zone before engagement is possible; USVs are held in patrol to maintain sensor coverage. Remaining
```

## 调用 9（tick 90）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 200},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03"}, "priority": 0.6, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4898.0, 2967.0]}, "priority": 0.3},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7043.0, 2865.0]}, "priority": 0.3},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2255.0, -265.0]}, "priority": 0.3},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5912.0, 223.0]}, "priority": 0.3},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3183.0, -3073.0]}, "priority": 0.3},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5520.0, -273.0]}, "priority": 0.3}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. The three air intruders (strike-fuel-01, strike-comms-01, strike-command-01) are the highest threat level (0.54, 0.49, 0.36) and are approaching. UAV-09 is closest to strike-fuel-01 (range_gap 2852m), so it is assigned to intercept it early to close the gap. UAV-03 is closest to strike-comms-01 (range_gap 4244m) and is assigned to intercept it. UAV-0
```

## 调用 10（tick 100）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-06.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_command_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4953.0, 3155.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7162.0, 3024.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2065.0, -165.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6280.0, -1860.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5668.0, 232.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3006.0, -3022.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5465.0, -138.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2012.0, -841.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1219.0, -2162.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the closest threat to the intercept window (ttr=49.6). UAV-03 is assigned to intercept strike-comms-01 as it also has prepare_intercept=true (ttr
```

## 调用 11（tick 110）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-07.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 180},
    {"task_id": "track_command_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01"}, "priority": 0.6, "deadline": 200},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4996.0, 3348.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7265.0, 3194.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1880.0, -50.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6288.0, -2067.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5422.0, 235.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2825.0, -2887.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5410.0, -1.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2069.0, -879.0]}, "priority": 0.3, "deadline": 200},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1196.0, -2133.0]}, "priority": 0.3, "deadline": 200}
  ],
  "reasoning": "UAV-09 is the only unit with prepare_intercept=true for the high-threat fuel intruder (TTR 45t), so it must intercept immediately. UAV-03 is the closest interceptor to the comms intruder (TTR 73t) and is assigned to intercept it to
```

## 调用 12（tick 120）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2127.0, -916.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2418.0, -1044.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1173.0, -2105.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5029.0, 3544.0]}, "priority": 0.4},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7347.0, 3374.0]}, "priority": 0.4},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1684.0, 51.0]}, "priority": 0.4},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5178.0, 241.0]}, "priority": 0.4},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2642.0, -2757.0]}, "priority": 0.4},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5355.0, 135.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-09 is already tasked with strike-comms-01 which has prepare_intercept=true and is the closest air threat to the zone. UAV-03 is assigned to intercept strike-comms-01 as well (observed by UAV-01, but UAV-03 is closest and has feasible_eta=69t) to ensure coverage if UAV-09 fails or needs to reposition. UAV-05 is assigned to intercept strike-fuel-01 (observed by UAV-05, prepare_intercept=true, feasible_eta=84t). Surface threats (boats) are far from the zone (dist_zone > 7000m) and have low closing speeds; USVs are holding position to maintain sensor coverage. Other UAVs are
```

## 调用 13（tick 130）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "track_boat_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-03.intruder.boat-01"}, "priority": 0.8, "deadline": 150},
    {"task_id": "track_boat_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02"}, "priority": 0.8, "deadline": 150},
    {"task_id": "track_boat_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5056.0, 3742.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7436.0, 3551.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8096.0, 4760.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1494.0, 164.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4933.0, 246.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2452.0, -2635.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5300.0, 270.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the closest high-threat air target (TTR 21t). UAV-05 is assigned to intercept strike-comms-01 (prepare_intercept=true, TTR 45t) to spread the load. USVs are tracking the three surface boats which are high threat but currently outside feasible intercept range for the USVs themselves; UAVs are too far to engage them effectively yet. Remaining UAVs hold position to maintain coverage."
}
```

## 调用 14（tick 140）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 160},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 160},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-02.intruder.boat-01"}, "priority": 0.8, "deadline": 180},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02"}, "priority": 0.8, "deadline": 180},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-03"}, "priority": 0.8, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5090, 3936]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1312, 277]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6262, -2690]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4689, 256]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2260, -2516]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5244, 402]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-comms-01 as it has the shortest time-to-weapon-range (7.5 ticks) and is the closest air threat. UAV-02 is assigned to intercept strike-fuel-01, which it observes directly and is approaching (prepare_intercept=true). UAV-03 continues its intercept of strike-comms-01 as a secondary layer. USVs are tasked to track the three surface boats to maintain sensor coverage and classify them, as they are currently outside effective engagement range for the USVs and the UAVs are prioritized for the faster air threats. Remaining UAVs hold position to conserve ammunition and maintain readiness."
}
```

## 调用 15（tick 150）

```
{
  "goal_commands": [
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 170},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 165},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5113.0, 4133.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8147.0, 5273.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1130.0, 395.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6248.0, -2897.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4442.0, 259.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2050.0, -2433.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5189.0, 537.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2363.0, -913.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1104.0, -2017.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 has can_intercept=true for strike-comms-01 (dist 7947m, inside 8000m range) and is the only unit with this status; assign intercept immediately. UAV-02 has prepare_intercept=true for strike-fuel-01 (range_gap 4136m, ttr 130.8t) and is currently tracking it; assign intercept to maneuver into position. USV-01 has prepare_intercept=true for boat-01 (range_gap 580m, ttr 
```

## 调用 16（tick 160）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 180},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 180},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5136.0, 4329.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [984.0, 562.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6236.0, -3103.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4197.0, 269.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1851.0, -2325.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5135.0, 671.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2356.0, -1064.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2345.0, -870.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1079.0, -1989.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 has can_intercept=true for strike-comms-01 (observed by UAV-08, but UAV-09 is the only unit with can_intercept=true for this target in the graph, implying it has the necessary observation or the graph implies feasibility for it specifically - wait, the rule says 'issue intercept for unit U only against contacts with by=U'. Let's re-read carefully. 'Each contact line shows by <observer_unit> — issue intercept for unit U only against contacts with by=U'. \n\nCorrection: \n- strike-comms-01 is observed_by=defender.uav-08. Only UAV-08 can fire at it? Or does 'observed_by' mean the primary sensor? The rule says '
```

## 调用 17（tick 170）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5152.0, 4529.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [864.0, 745.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3951.0, 276.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1656.0, -2209.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5083.0, 805.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1055.0, -1960.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is in weapon range for both high-threat air targets (fuel, comms) and is assigned to the higher-threat fuel target. UAV-02 and UAV-03 are assigned to the comms target which has prepare_intercept=true and is approaching. UAV-05 is assigned to the fuel target as a secondary interceptor due to prepare_intercept=true. USV-01 and USV-02 are assigned to the surface boats (boat-0
```

## 调用 18（tick 180）

```
{
  "goal_commands": [
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-05.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 10},
    {"task_id": "intercept_comms_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 15},
    {"task_id": "intercept_fuel_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 15},
    {"task_id": "track_boat_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-03.intruder.boat-01"}, "priority": 0.7, "deadline": 60},
    {"task_id": "track_boat_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-09.intruder.boat-02"}, "priority": 0.7, "deadline": 60},
    {"task_id": "track_boat_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03"}, "priority": 0.6, "deadline": 60},
    {"task_id": "reserve_uav_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5184.0, 4724.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-04", "position": [768.0, 941.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [3706.0, 288.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [1472.0, -2077.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav_005", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [5032.0, 939.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-09 has can_intercept=true for
```

## 调用 19（tick 190）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-09.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5194.0, 4922.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [650.0, 1125.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3462.0, 293.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1286.0, -1949.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4980.0, 1071.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1008.0, -1903.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 has can_intercept=true for strike-comms-01, so it engages immediately. UAV-05 has prepare_intercept=true for strike-fuel-01 (highest threat air target) and is closest, so it intercepts now. USV-01 has can_intercept=true for boat-01 (highest threat surface target), so it engages. USV-02 has prepare_intercept=true for boat-02, so it intercepts. UAV-03 is assigned to strike-comms-01 as a secondary interceptor since it is also close and has prepare_intercept=true. Remaining units hold position to conserve ammo and maintain coverage."
}
```

## 调用 20（tick 200）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5153.0, 5117.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8250.0, 6325.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [634.0, 1345.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3215.0, 304.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1101.0, -1822.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4932.0, 1203.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [983.0, -1875.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 and UAV-05 are in intercept range for the two high-threat air targets (strike-comms-01 and strike-fuel-01) and are assigned to engage. USV-01 and USV-02 are assigned to the high-threat surface target boat-01, which is closest to the protected zone and within their sensor/weapon envelope. Other units hold position to maintain coverage and conserve ammunition."
}
```

## 调用 21（tick 210）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 50},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 50},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 50},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5131.0, 5316.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [618.0, 1563.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [2968.0, 296.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [935.0, -1668.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4884.0, 1334.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2643.0, -1244.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 and UAV-05 are in weapon range of high-threat air targets (strike-comms-01 and strike-fuel-01) and are assigned to intercept. UAV-03 is also in range of strike-comms-01 and assigned as a secondary interceptor to ensure engagement. USV-02 and USV-03 are assigned to intercept surface threats (boat-02 and boat-03) which are approaching the protected zone; USV-01 has no ammo and is held for sensor support. Remaining UAVs are held in patrol positions to maintain coverage and conserve ammunition for potential new waves."
}
```

## 调用 22（tick 220）

```
{
  "goal_commands": [
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_boat1_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_boat3_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8278.0, 6808.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6111.0, -4122.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_usv01_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [2702.0, -1280.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5113.0, 5517.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 100},
    {"task_id": "reserve_uav04_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-04", "position": [631.0, 1783.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 100},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [2720.0, 301.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 100},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [764.0, -1518.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 100}
  ],
  "reasoning": "UAV-02 is in range of strike-comms-01 (can_intercept=true) and assigned to engage. UAV-08 is assigned to strike-fuel-01 (prepare_intercept=true, high threat) to maneuver into position. USV-02 and USV-03 are assigned to the closest surface threats (boat-01 and boat-03) which are
```

## 调用 23（tick 230）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8293.0, 7066.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6092.0, -4329.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5096.0, 5717.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 300},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-04", "position": [671.0, 2000.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 300},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [2474.0, 300.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 300},
    {"task_id": "reserve_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [604.0, -1360.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 300},
    {"task_id": "reserve_005", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [4786.0, 1601.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 300},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [2759.0, -1317.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-02 is the only armed unit with can_intercept=true for the high-threat air contact strike-comms-01 (observed by UAV-03, but UAV-02 has line-of-sight and is in range). UAV-03 and UAV-05 are out of ammo and must disengage to conserve resources or reposition. The surface threats (boat-01, boat-03) are the most immediate danger to the protected zone (dist_zone < 8km). USV-02 is assigned to boat-01 (closest, highest threat
```

## 调用 24（tick 240）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.90, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03"}, "priority": 0.85, "deadline": 150},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8314.0, 7323.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6056.0, -4535.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.7},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03"}, "priority": 0.7},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5068.0, 5918.0]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9055.0, 4963.0]}, "priority": 0.4},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [441.0, -1204.0]}, "priority": 0.4}
  ],
  "reasoning": "Three surface intruders (boat-01, boat-02, boat-03) are approaching the protected zone with high threat levels (0.83-0.86). boat-01 and boat-02 are already within sensor range of USVs and have prepare_intercept=true, indicating imminent threat. boat-03 is also approaching with prepare_intercept=true. UAV-04, UAV-06, and UAV-08 are assigned to intercept these three targets respectively, as they are the closest armed units with sufficient ammo. UAV-03 and UAV-05 have 0 ammo and are disengaged. USVs are tasked with tracking to maintain sensor coverage. Remaining UAVs patrol to maintain situational awareness."
}
```

## 调用 25（tick 250）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5130, 6116], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav04_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-04", "position": [670, 2234], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [4688, 1879], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8341, 7576]}, "priority": 0.1},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6028, -4743]}, "priority": 0.1},
    {"task_id": "disengage_usv01_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [2874, -1388]}, "priority": 0.1},
    {"task_id": "disengage_usv03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-03", "position": [873, -1726]}, "priority": 0.1}
  ],
  "reasoning": "Three surface intruders (boat-01, boat-02, boat-03) are approaching the protected zone. boat-01 and boat-02 are within sensor range of USV-02 and UAV-06 respectively, and both have prepare_intercept=true, so immediate intercept is required. boat-03 is observed by UAV-07 and is also approaching; UAV-07 is assigned to intercept it. UAV-03 and UAV-05 have no ammo and are disengaged. USV-01 has no ammo and is disengaged. USV-03 is disengaged to conserve resources as the primary interceptors are already assigned. Remaining armed UAVs (01, 04, 08) are held in reserve to react to new threats or if the primary interceptors fail."
}
```

## 调用 26（tick 260）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5198.0, 6309.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9235.0, 5292.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8318.0, 7827.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5985.0, -4944.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [1994.0, 235.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [164.0, -1342.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4642.0, 2029.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2927.0, -1424.0]}, "priority": 0.5}
  ],
  "reasoning": "boat-01 is the highest threat (0.86) and closest to the zone (5809m). usv-02 has can_intercept=true and is assigned to engage it. boat-02 (0.85) is approaching; uav-04 has prepare_intercept=true and is assigned to intercept. boat-03 (0.82) is approaching; usv-03 is assigned to intercept it. Other units are on patrol to maintain coverage and conserve ammunition."
}
```

## 调用 27（tick 270）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_strike01_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_strike01_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8341.0, 8077.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5919.0, -5116.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2981.0, -1455.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for boat-01 (highest threat, closest to zone), so it engages immediately. UAV-04 and UAV-06 are assigned to boat-02 and boat-03 respectively, as they are the closest armed interceptors to these approaching threats (prepare_intercept=true for boat-02/03 from their perspective or imminent threat). UAV-07 and UAV-08 track the receding boats 04 and 05 to maintain sensor coverage. UAV-01
```

## 调用 28（tick 280）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01"}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5308.0, 6712.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9355.0, 5662.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4553.0, 2327.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "boat-01 (threat 0.87) is the highest priority surface threat, approaching the zone. usv-02 has can_intercept=true and is assigned to engage. uav-04 and uav-07 have prepare_intercept=true and are assigned to intercept to ensure coverage and redundancy. boat-02 (threat 0.85) is also approaching; uav-06 has prepare_intercept=true and is assigned to intercept. usv-01 tracks boat-02 as it is out of range for usv-02. uav-03 tracks boat-03 (ammo 0). uav-05 tracks the air threat (ammo 0). Remaining
```

## 调用 29（tick 290）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8368.0, 8580.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5944.0, -5532.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [3087.0, -1524.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.6}
  ],
  "reasoning": "boat-01 and boat-02 are the highest threats (0.85/0.84) and are approaching the zone. boat-01 is observed by usv-03 (can_intercept=true for usv-02), so usv-02 is assigned to intercept. uav-04 and uav-06 are assigned to intercept boat-01 and boat-02 respectively to provide redundant coverage and engage if USVs fail. boat-04 and boat-05 are receding but still high threat; uav-01 and uav-02 are assigned to intercept them to prevent them from turning back or to engage if they re-approach. uav-03, uav-05, and usv-01 have 0 ammo and are disengaged. usv-03 and uav-07 track boat-01 to maintain sensor coverage."
}
```

## 调用 30（tick 300）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.65, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03"}, "priority": 0.5, "deadline": 120},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1, "deadline": 120},
    {"task_id": "return_002", "goal_type": "return", "parameters": {"unit_id": "defender.uav-05"}, "priority": 0.1, "deadline": 120}
  ],
  "reasoning": "Prioritizing high-threat surface contacts (boat-01, boat-02, boat-04) approaching the protected zone. boat-01 is closest (5485m) and observed by facility.command; assigning nearest armed UAVs (uav-06, uav-04) and USV-02 to intercept. boat-02 (6062m) is observed by uav-07; assigning uav-04 (also close) and uav-07. boat-04 (7492m) is observed by usv-01; assigning uav-08, uav-01, uav-02 to intercept. boat-03 is further out (6922m) and observed
```

## 调用 31（tick 310）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-01"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-03"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-04"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.boat-05"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-04"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.boat-03"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_008", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.boat-04"}, "priority": 0.70, "deadline": 120}
  ],
  "reasoning": "Boats 01, 02, and 03 are the highest threats (0.83-0.86) and are approaching the protected zone. UAV-04 and UAV-06 have prepare_intercept=true for boats 01 and 02 respectively, so they are assigned to intercept immediately. UAV-08 is assigned to intercept boat 03 as it is the next closest threat. USVs are assigned to track these targets to maintain sensor coverage and provide fire control data. Other UAVs are assigned to track remaining contacts to maintain situational awareness and prepare for potential future threats."
}
```

## 调用 32（tick 320）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.command.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5567.0, 7505.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9547.0, 6390.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8367.0, 9153.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5696.0, -6028.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1101.0, -1453.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3245.0, -1630.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2210.0, -255.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat surface intruders (boat-01, boat-02, boat-03) are approaching the protected zone. UAV-04, UAV-06, and UAV-08 are the closest armed interceptors with line-of-sight to their respective targets and are assigned to intercept. Other units are holding position to conserve ammunition and maintain sensor coverage, as the primary threats are being engaged by the dedicated interceptors."
}
```

## 调用 33（tick 330）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_strike01_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01"}, "priority": 0.60, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5622.0, 7708.0]}, "priority": 0.50},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8374.0, 9376.0]}, "priority": 0.50},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5496.0, -6080.0]}, "priority": 0.50},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3294.0, -1668.0]}, "priority": 0.50},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2202.0, -213.0]}, "priority": 0.50},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.50}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone with high threat levels and prepare_intercept=true. UAV-06 is closest to boat-02 and has ammo, so it is assigned to intercept. UAV-04 is closest to boat-03 and has ammo, so it is assigned to intercept. UAV-08 is closest to boat-04 and has ammo, so it is assigned to intercept. UAV-07 is tracking boat-05 which is receding. UAV-02 is tracking the air threat strike-command-01 which is far away. Other units are patrolling or holding position as they have no ammo or are not in a position to engage."
}
```

## 调用 34（tick 340）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5650.0, 7914.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [9492.0, 6759.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [4299.0, 3217.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8376.0, 9618.0]}, "priority": 0.3},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5427.0, -5910.0]}, "priority": 0.3},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.4},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.4},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01"}, "priority": 0.4}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone with high threat levels. UAV-04, UAV-06, and UAV-07 are the closest armed units with line-of-sight to their respective targets and are assigned to intercept. UAV-01, UAV-02, and UAV-08 are held in reserve to react to new threats or if the primary interceptors fail. UAV-03 and UAV-05 have no ammunition and are disengaged to return to anchor. USVs are tasked with tracking to maintain sensor coverage on the intruders and the distant air contact."
}
```

## 调用 35（tick 350）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5673.0, 8116.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [9468.0, 6951.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8389.0, 9857.0]}, "priority": 0.3},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5513.0, -5789.0]}, "priority": 0.3},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [3396.0, -1740.0]}, "priority": 0.3},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2200.0, -129.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04, 06, and 07 are assigned to intercept the three surface intruders (boat-02, boat-03, boat-04) which are currently approaching or receding slowly but have high threat levels and are within or near weapon range. UAV-08 is assigned to intercept the air intruder (strike-command-01) which is approaching and has prepare_intercept=true. UAV-01 and 02 are held in reserve to cover the rear and react to new threats. UAV-03 and 05 are disengaged as they have 0 ammo. USV-01 is disengaged as it has 0 ammo. USV-02 and 03 are patrolling to maintain sensor coverage."
}
```

## 调用 36（tick 360）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 137},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 118},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 255},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 283},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03"}, "priority": 0.6, "deadline": 231},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.6, "deadline": 347},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.6, "deadline": 460},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5690.0, 8316.0]}, "priority": 0.4, "deadline": 320},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9404.0, 7128.0]}, "priority": 0.4, "deadline": 238},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8371.0, 10098.0]}, "priority": 0.2, "deadline": 315},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5674.0, -5707.0]}, "priority": 0.2, "deadline": 256}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-03 and boat-02 respectively, as they are the closest threats with prepare_intercept=true and are within their own observation range. UAV-07 is assigned to boat-04, which is also approaching and observed by the pier facility. UAV-08 is assigned to strike-command-01, which is approaching and observed by the pier facility. USVs are assigned to track the closest threats to maintain sensor coverage. UAV-01 and UAV-02 are on patrol as they are further away and not currently in a position to intercept. UAV-03 and UAV-05 are disengaging as they have no ammunition."
}
```

## 调用 37（tick 370）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8406.0, 10339.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5627.0, -5634.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [3488.0, -1818.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2202.0, -46.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5718.0, 8518.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to the highest threat surface contacts (boat-03 and boat-02) which are approaching the protected zone and have prepare_intercept=true. UAV-07 is assigned to boat-02 as a secondary interceptor to ensure coverage if the primary fails or to engage if it crosses the boundary. UAV-08 and UAV-02 are assigned to the air contact (strike-command-01) which is approaching and has prepare_intercept=true for UAV-02. UAV-03, UAV-05, and USV-01 are disengaged due to 0 ammo. USV-02 and USV-03 are patrolling to maintain sensor coverage. UAV-01 is patrolling as a reserve."
}
```

## 调用 38（tick 380）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5734.0, 8722.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9363.0, 7328.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8417.0, 10581.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5800.0, -5627.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3537.0, -1856.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-02 (highest threat, closest to zone, prepare_intercept=true for UAV-04) to prevent zone entry. UAV-07 intercepts boat-03 (high threat, prepare_intercept=true). UAV-08 intercepts strike-command-01 (air threat, approaching). USV-02 intercepts boat-02 as a secondary layer. UAV-01 and UAV-02 hold position as they are too far to engage current threats effectively. UAV-03 and UAV-05 are disengaged due to 0 ammo. USVs hold position for sensor coverage."
}
```

## 调用 39（tick 390）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01"}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "boat-02 is the highest threat (0.86) and closest to the zone (5253m). usv-02 has can_intercept=true and is assigned to engage. uav-04 is assigned to intercept boat-02 as a secondary armed asset (prepare_intercept=true, approaching). boat-03 (0.83) is approaching; uav-07 is assigned to intercept it (prepare_intercept=true). strike-command-01 (0.65) is approaching fast (ttr=16.5
```

## 调用 40（tick 400）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 180},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-04"}, "priority": 0.6, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5742.0, 9133.0]}, "priority": 0.3},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9340.0, 7698.0]}, "priority": 0.3},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8460.0, 11057.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5968.0, -5275.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-841.0, -379.0]}, "priority": 0.3}
  ],
  "reasoning": "UAV-04 and UAV-07 are closest to the high-threat surface boats (02 and 03) and have prepare_intercept=true, so they are assigned to intercept immediately. USV-02 and USV-03 are also assigned to intercept boats 02 and 03 respectively, as they are within range or preparing to engage. UAV-08 is assigned to the air threat (strike-command-01) which is approaching and has prepare_intercept=true. USV-01 is out of ammo and assigned to track boat-04 to maintain sensor coverage. UAV-03 and UAV-05 are out of ammo and disengaged. Remaining UAVs are on patrol to maintain coverage."
}
```

## 调用 41（tick 410）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 90},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_strike_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8445.0, 11296.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6111.0, -5152.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3680.0, -1974.0]}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2222.0, 60.0]}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with prepare_intercept=true for the highest threat (boat-02, threat 0.88) and is already in range (range_gap=0), so it is assigned to intercept with a salvo to maximize kill probability. UAV-07 is assigned to boat-03 (threat 0.85) as it is the closest armed unit to that target with prepare_intercept=true. UAV-02 is assigned to boat-04 (threat 0.83) as it is the observer and has prepare_intercept=true. UAV-06 is assigned to boat-05 (threat 0.83) as it is the observer and has prepare_intercept=true. UAV-08 is tracking the air threat (strike-command-01) to maintain observation for other units, as it is currently out of range for most interceptors. UAV-
```

## 调用 42（tick 420）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6223.0, -4984.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8442.0, 11535.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3728.0, -2012.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2232.0, 55.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5710.0, 9542.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9364.0, 8089.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "UAV-04 is closest to boat-02 (3695m, prepare=true) and assigned to intercept with salvo for high threat. UAV-07 is closest to boat-03 (6753m, prepare=true) and assigned to intercept. UAV-06 is closest to boat-04 (5442m) and assigned to intercept. UAV-08 is assigned to intercept strike-command-01 (prepare=true, approaching). UAV-05 and UAV-03 have 0 ammo and are disengaged. USVs are on patrol to maintain sensor coverage. UAV-01 and UAV-02 are on patrol as they are too far to effectively engage current threats."
}
```

## 调用 43（tick 430）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5743.0, 9749.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9333.0, 8279.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8446.0, 11772.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6426.0, -4961.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3777.0, -2050.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2248.0, 50.0]}, "priority": 0.4},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04, UAV-07, and UAV-06 are assigned to intercept the three surface intruders (boat-02, boat-03, boat-04) which are currently in the prepare_intercept phase and approaching the protected zone. UAV-08 is assigned to intercept the air intruder (strike-command-01) which is also in the prepare_intercept phase. UAV-01 and UAV-02 are held in patrol as they are too far to effectively engage the immediate threats. UAV-03 and UAV-05 are disengaged due to zero ammunition. USVs are held in patrol to maintain sensor coverage."
}
```

## 调用 44（tick 440）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5716.0, 9955.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9300.0, 8469.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8466.0, 12014.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3819.0, -2092.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2254.0, 75.0]}, "priority": 0.4},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [837.0, -1692.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 is closest to boat-02 (dist 3572m, prepare=true) and assigned to intercept. UAV-06 is closest to boat-03 (dist 4321m, prepare=true) and assigned to intercept. UAV-07 is closest to boat-04 (dist 6691m, prepare=true) and assigned to intercept. UAV-08 is closest to strike-command-01 (dist 9085m, prepare=true) and assigned to intercept. Other UAVs are too far or out of ammo. USVs are holding position to maintain sensor coverage."
}
```

## 调用 45（tick 450）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.65, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8401.0, 12232.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [3863.0, -2132.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5679.0, 10162.0]}, "priority": 0.5}
  ],
  "reasoning": "Prioritizing high-threat surface intruders (boat-02, boat-03) which are closest to the protected zone and have prepare_intercept=true. Assigning USV-03 and USV-02 to boat-02 (highest threat 0.89) and UAV-04, UAV-06, UAV-07 to boat-03 (threat 0.87) to ensure coverage. Assigning UAV-08 and UAV-02 to the air threat (strike-command-01) which is approaching and has prepare_intercept=true. Disengaging UAV-03 and USV-01 due to 0 ammo. Keeping UAV-01 on patrol as a reserve."
}
```

## 调用 46（tick 460）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 90},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5688.0, 10373.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [9207.0, 8838.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8368.0, 12466.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3912.0, -2165.0]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2234.0, 155.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 and UAV-06 are closest to the high-threat surface boats (boat-02, boat-03) which are approaching the zone; assigning them to intercept. UAV-08 is the observer for the air target (strike-command-01) and is within range (prepare_intercept=true), so it must engage. UAV-07 is assigned to the new surface contact (boat-04) observed by UAV-08, as it is approaching and needs coverage. UAV-01 and UAV-02 are held in reserve to cover the rear/air axis. UAV-03 has no ammo and is disengaged. USVs are sensor-only and held in position to maintain observation."
}
```

## 调用 47（tick 470）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 15},
    {"task_id": "intercept_strike01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 20},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.70, "deadline": 60},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5705.0, 10580.0]}, "priority": 0.50},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9229.0, 9028.0]}, "priority": 0.50},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8251.0, 12672.0]}, "priority": 0.40},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-2234.0, -629.0]}, "priority": 0.50},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3962.0, -2193.0]}, "priority": 0.50}
  ],
  "reasoning": "UAV-04 and UAV-07 are assigned to intercept Boat-02 and Boat-03 respectively, as they are the closest surface threats with prepare_intercept=true and are within weapon range. UAV-08 is assigned to intercept Strike-Command-01, which is approaching rapidly and has prepare_intercept=true. USV-02 is tracking Boat-04 to maintain sensor coverage. UAV-01, UAV-02, and UAV-06 are patrolling to maintain situational awareness and readiness. UAV-03 is disengaging due to 0 ammo. USV-01 is patrolling as it has 0 ammo and is a sensor-only unit."
}
```

## 调用 48（tick 480）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5675.0, 10787.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9258.0, 9222.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8190.0, 12897.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4014.0, -2219.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to intercept the air threat (strike-command-01) which has prepare_intercept=true and is approaching; UAV-04 is closest and has a short feasible ETA. USV-02 is assigned to intercept boat-02 (highest threat surface contact, can_intercept=true). UAV-06 and UAV-07 are assigned to intercept boat-03 (can_intercept=true for USV-02, but USV-02 is committed to boat-02; UAV-06/07 are in position to engage boat-03 if it becomes a threat or if USV-02 fails). UAV-01 and UAV-02 are on patrol as they are far from the immediate threats and have no prepare_intercept targets. UAV-03 has 0 ammo and is disengaging. USV-01 has 0 ammo and is on patrol."
}
```

## 调用 49（tick 490）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 50},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 40},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02"}, "priority": 0.5, "deadline": 100},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5680, 10999], "commit_within_m": 9000}, "priority": 0.4, "deadline": 200},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [9194, 9409], "commit_within_m": 9000}, "priority": 0.4, "deadline": 200},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8128, 13125]}, "priority": 0.1, "deadline": 100}
  ],
  "reasoning": "UAV-08 has can_intercept=true for the air threat (strike-command-01) and is the closest armed unit to it, so it engages immediately. UAV-04 is extremely close to boat-02 (2524m, prepare_intercept=true) and is the best candidate to intercept it before it reaches the zone. UAV-07 is close to boat-03 (6474m, prepare_intercept=true) and will intercept it. UAV-06 is assigned to boat-04 (6163m) to cover the fourth threat. USVs are used for tracking to maintain sensor coverage. UAV-01 and UAV-02 are held in reserve as they are far from the immediate threats. UAV-03 has no ammo and is disengaged."
}
```

## 调用 50（tick 500）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.6},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5656.0, 11206.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [9218.0, 9602.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8048.0, 13348.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage immediately with a salvo to maximize kill probability. UAV-06 and UAV-07 are assigned to the two closest surface threats (boat-02 and boat-03) which are approaching the protected zone; they are in range and will engage as they close. UAV-08 is assigned to boat-04, which is approaching and observed by UAV-08 (implied by previous assignment and proximity, though graph shows usv-01 observation, UAV-08 is the closest armed unit to it and was previously tracking it). USVs are used for tracking to maintain sensor coverage. UAV-01 and UAV-02 are held in reserve to react to new threats or if current engagements fail. UAV-03 has no ammo and is disengaged."
}
```

## 调用 51（tick 510）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.command.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.6, "deadline": 60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7937.0, 13560.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is closest, so it engages immediately. UAV-07 and UAV-06 are assigned to the two closest surface threats (boat-02 and boat-03) which have prepare_intercept=true and are approaching the zone. USV-02 and USV-01 engage their respective observed targets (boat-02 and boat-05) to maintain local coverage. UAV-08 and UAV-02 are tasked to intercept the air target as secondary/backup layers since they have prepare_intercept=true and are closer than other reserves. UAV-03 has 0 ammo and is disengaged to conserve resources."
}
```

## 调用 52（tick 520）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7821.0, 13766.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4226.0, -2332.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2180.0, 404.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5742.0, 11619.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9231.0, 9979.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 has can_intercept=true for the high-threat air target (strike-command-01) and is the closest; assigned to intercept with salvo to maximize kill probability. UAV-07 is closest to boat-02 (highest threat surface) and has prepare_intercept=true; assigned to intercept. UAV-06 is closest to boat-03 and has prepare_intercept=true; assigned to intercept. UAV-08 is closest to boat-04 and has prepare_intercept=true; assigned to intercept. UAV-03 has 0 ammo and is disengaged. USVs are sensors only (or low ammo) and are holding position to maintain sensor coverage. UAV-01 and UAV-02 are holding position as reserves since all immediate threats are covered by closer interceptors."
}
```

## 调用 53（tick 530）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.pier.intruder.boat-05"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03"}, "priority": 0.60, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5717.0, 11828.0]}, "priority": 0.50},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9227.0, 10173.0]}, "priority": 0.50},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7731.0, 13982.0]}, "priority": 0.10}
  ],
  "reasoning": "UAV-04 and UAV-08 have can_intercept=true for the high-threat air target (strike-command-01) and are assigned to engage it with assess policy to conserve ammo. UAV-06 and UAV-07 are assigned to the closest surface threats (boat-02 and boat-03) which are approaching the zone and have prepare_intercept=true. USVs are used for tracking as they are sensors only (USV-01 has 0 ammo, USV-02 is tracking boat-03). UAV-01 and UAV-02 are on patrol as they are far from the immediate threats. UAV-03 has 0 ammo and is disengaging."
}
```

## 调用 54（tick 540）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5745.0, 12039.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9204.0, 10367.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7687.0, 14214.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-08 is in range of the high-threat air target (strike-command-01) and assigned to intercept with a salvo to maximize kill probability. USV-02 is in range of the closest surface threat (boat-02) and assigned to intercept. UAV-07 is approaching the air target and assigned to intercept as a secondary threat. UAV-06 is assigned to intercept boat-02 as a backup. UAV-04 and USV-01 have no ammo and are assigned to track nearby threats for sensor coverage. UAV-01 and UAV-02 are on patrol to maintain sensor coverage. UAV-03 has no ammo and is disengaging to return to base."
}
```

## 调用 55（tick 550）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 172},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 223},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 247},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 170},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.7, "deadline": 135},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5736.0, 12251.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9212.0, 10562.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7632.0, 14437.0]}, "priority": 0.4},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1322.0, -2371.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-08 is in range of the high-threat air target (strike-command-01) and is assigned to intercept. UAV-07 is preparing to intercept the same air target as a secondary layer. USV-02 and UAV-06 are assigned to the high-threat surface target (boat-02) which is closest to the zone. USV-01 tracks boat-03 to maintain sensor coverage. UAV-01 and UAV-02 hold position as reserves. UAV-03 and UAV-04 are out of ammo and disengaged to rear anchors."
}
```

## 调用 56（tick 560）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5733.0, 12464.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [9203.0, 10755.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7553.0, 14655.0]}, "priority": 0.1, "deadline": 300},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1351.0, -2531.0]}, "priority": 0.1, "deadline": 300}
  ],
  "reasoning": "UAV-07 is assigned to intercept the air threat (strike-command-01) as it is the highest priority and has prepare_intercept=true with a short feasible_eta. UAV-06 is assigned to intercept boat-02 (highest threat surface contact) which is approaching and has prepare_intercept=true. USV-02 is assigned to intercept boat-03 which is also approaching and has prepare_intercept=true. USV-01 tracks boat-05 as it is a sensor-only unit. UAV-08 tracks boat-02 to maintain sensor coverage while UAV-06 engages. UAV-01 and UAV-02 are held in reserve. UAV-03 and UAV-04 are disengaged as they have 0 ammo."
}
```

## 调用 57（tick 570）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5768.0, 12674.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9211.0, 10943.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7496.0, 14881.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1338.0, -2722.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3458.0, 6001.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with ammo and can_intercept=true for boat-02 (closest to zone, 3669m). UAV-07 has prepare_intercept=true for boat-03 (4510m) and is approaching, so it is assigned to intercept. UAV-06 has prepare_intercept=true for boat-04 (5089m) and is the closest armed unit to it, so it is assigned to intercept. USV-01 has can_intercept=true for boat-05 but has 0 ammo, so it is assigned to track to maintain sensor contact. Other UAVs are on patrol to maintain coverage and conserve ammo."
}
```

## 调用 58（tick 580）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5801.0, 12883.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9163.0, 11139.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7402.0, 15097.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1493.0, -2836.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3403.0, 6151.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4536.0, -2502.0]}, "priority": 0.5}
  ],
  "reasoning": "Three intruders (boat-02, boat-03, boat-04) are approaching the protected zone. boat-02 is closest (3607m) and highest threat (0.90), assigned to uav-06 which is in range and observing it. boat-03 (4384m) is assigned to usv-02 which has can_intercept=true. boat-04 (4963m) is assigned to uav-07 which is in range and observing it. Other units are on patrol to maintain coverage and conserve ammunition."
}
```

## 调用 59（tick 590）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 188},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 168},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.85, "deadline": 416},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1652.0, -2923.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7332.0, 15319.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4589.0, -2526.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5817.0, 13095.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9079.0, 11317.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3349.0, 6303.0]}, "priority": 0.4, "deadline": 100}
  ],
  "reasoning": "Three intruders (boat-03, 04, 05) are approaching the protected zone from the East (bearing ~90-100). UAV-06 is closest to boat-03 (highest threat 0.90) and has prepare_intercept=true, so it is assigned to intercept. UAV-07 is assigned to boat-04 (threat 0.88) as it is the next closest armed unit with a feasible intercept path. USV-02 is assigned to boat-05 (threat 0.86) to cover the third threat, although it is further away. UAV-04 and UAV-03 have 0 ammo and are disengaged to conserve energy/return to base. USV-01 has 0 ammo and is patrolling. Remaining UAVs (01, 02, 08) are patrolling as the primary threats are being handled by the closer units."
}
```

## 调用 60（tick 600）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5877.0, 13306.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8982.0, 11484.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7243.0, 15534.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1810.0, -3025.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3286.0, 6456.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4643.0, -2544.0]}, "priority": 0.5}
  ],
  "reasoning": "Three intruders (boat-03, boat-04, boat-05) are approaching the protected zone from the east/northeast. boat-04 is closest to the zone boundary and is observed by uav-07, which is in position to intercept. boat-05 is observed by uav-06, which is also in position. boat-03 is observed by usv-02, which is the closest armed unit to it. The other UAVs are too far away to be effective interceptors for these specific targets and are holding position to maintain sensor coverage and readiness for potential new threats. usv-01 is out of ammo and holding."
}
```

## 调用 61（tick 610）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5953.0, 13506.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8950.0, 11635.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7166.0, 15769.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1990.0, -3027.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3239.0, 6606.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4694.0, -2569.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, boat-04, boat-05) are currently the highest threats (0.87-0.90) and are within weapon range of their assigned interceptors (uav-07, uav-06, usv-02). The air targets are far away (20km+) with stable approach and no immediate interception window (prepare=false), so interceptors are held in patrol to conserve ammo and maintain positioning. uav-04 and uav-03 are out of ammo and held in position."
}
```

## 调用 62（tick 620）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6024.0, 13706.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9073.0, 11780.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7108.0, 16020.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2157.0, -2902.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3193.0, 6750.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4747.0, -2601.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, boat-04, boat-05) are currently in the immediate vicinity of the protected zone (dist_zone < 5.5km) and are the highest priority threats. boat-03 is assigned to usv-02 (observer), boat-04 to uav-07 (observer), and boat-05 to uav-06 (observer). All other contacts are air targets at >20km distance with no immediate interception window (prepare=false), so remaining units hold position to conserve ammo and maintain sensor coverage."
}
```

## 调用 63（tick 630）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6083.0, 13902.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9209.0, 11886.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7061.0, 16272.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2317.0, -2767.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3140.0, 6887.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4802.0, -2635.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, boat-04, boat-05) are currently within weapon range of their assigned interceptors (uav-07, uav-06, usv-02) and are the highest immediate threats to the protected zone. The air contacts (strike-comms, strike-fuel) are far away (15-28km) with long ETAs and no immediate interception triggers (can_intercept=false, prepare_intercept=false), so the remaining armed UAVs are held in patrol positions to conserve ammunition and maintain situational awareness."
}
```

## 调用 64（tick 640）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6115.0, 14100.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9393.0, 11901.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7015.0, 16525.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2530.0, -2711.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3068.0, 7018.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4856.0, -2672.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, boat-04, boat-05) are currently the highest threats (0.85-0.89) and are closest to the protected zone. boat-03 is approaching and within range of usv-02 (can_intercept=true), so usv-02 is assigned to intercept. boat-04 and boat-05 are receding but still high threat; uav-07 and uav-06 are assigned to intercept them to maintain pressure and prevent re-approach. The air contacts (strike-comms, strike-fuel) are far away (dist > 14km) and have low prepare_intercept flags, so the remaining UAVs are held in patrol positions to conserve ammo and maintain coverage for potential future waves."
}
```

## 调用 65（tick 650）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6143.0, 14298.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9581.0, 11919.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6976.0, 16780.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2729.0, -2633.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2999.0, 7151.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4911.0, -2709.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, boat-04, boat-05) are currently in the immediate vicinity of the protected zone and are the highest priority threats. boat-03 and boat-04 are within weapon range of usv-02 and uav-07 respectively, and are being engaged. boat-05 is approaching and within range of uav-06, so it is being engaged. The air targets are far away (20km+) and not yet in the intercept window, so the remaining UAVs are holding position to maintain coverage and conserve ammunition."
}
```

## 调用 66（tick 660）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6186.0, 14493.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9769.0, 11939.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6922.0, 17035.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2950.0, -2629.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-5624.0, 155.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-3747.0, -340.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2924.0, 7282.0]}, "priority": 0.5}
  ],
  "reasoning": "Immediate threat: boat-04 (threat 0.88) is within range of usv-02 (can_intercept=true). boat-05 (threat 0.86) is approaching and prepare_intercept=true for usv-02, so usv-02 is tasked to intercept both (prioritizing boat-04). boat-03 (threat 0.88) is observed by usv-01 (sensor only) and uav-04 (out of ammo), so usv-01 tracks it. The air threats (strike-comms/fuel) are far away (dist > 14km) with no prepare_intercept flags, so armed UAVs (uav-
```

## 调用 67（tick 670）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.80, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6232.0, 14689.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9951.0, 11970.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6863.0, 17287.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3158.0, -2574.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-5858.0, 226.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2852.0, 7415.0]}, "priority": 0.5, "deadline": 300}
  ],
  "reasoning": "Boats 04 and 05 are the immediate threats (dist_zone < 5km, high threat). USV-02 is the only armed unit in range (USV-01 has 0 ammo). USV-02 is assigned to intercept Boat 04 (closest, approaching) and Boat 05 (just outside range, approaching). USV-01 tracks Boat 03 (receding, low immediate risk) to maintain sensor contact. UAV-07 tracks Boat 04 for redundancy. All other UAVs are on patrol as the air threats are far away (dist_zone > 20km) and no interceptors are currently in a position to engage them effectively without wasting time."
}
```

## 调用 68（tick 680）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat05_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_boat03_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav01_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6292, 14879], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_uav02_005", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [10136, 11999], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_uav03_006", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6803, 17537]}, "priority": 0.2, "deadline": 300},
    {"task_id": "disengage_uav04_007", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3365, -2511]}, "priority": 0.2, "deadline": 300},
    {"task_id": "reserve_uav06_008", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-6088, 307], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_uav07_009", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-4157, -150], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_uav08_010", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [2776, 7543], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300}
  ],
  "reasoning": "USV-02 is the only unit with ammo and close range to the high-threat surface boats (0.88-0.89). It is assigned to intercept boat-04 (can_intercept=true) and boat-05 (prepare_intercept=true). USV-01 (no ammo) tracks boat-03 to maintain sensor coverage. UAVs with ammo are held in reserve to engage if boats penetrate or new air threats emerge, as current air targets are far (20km+). UAVs with 0 ammo are disengaged."
}
```

## 调用 69（tick 690）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05"}, "priority": 0.80, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6326.0, 15076.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10310.0, 12065.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6744.0, 17787.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-6328.0, 356.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4351.0, -33.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2699.0, 7671.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, 04, 05) are the immediate threat, all within 5km of the protected zone. boat-04 and boat-05 are observed by usv-02 (armed, ammo=2) and have can_intercept=true; usv-02 is assigned to intercept boat-04 (closest, highest threat). boat-03 is observed by uav-04 (armed, ammo=0) and is approaching; uav-04 is assigned to intercept it (will maneuver, but cannot fire due to 0 ammo; usv-01 is tracking boat-05 to maintain sensor coverage). The air contacts (strike-comms, strike-fuel) are far away (20km+), with no prepare_intercept flags, so armed UAVs (uav-01, 02, 06, 07, 08) are held in patrol to conserve ammo and maintain positioning for future waves. uav-03 and uav-04 have 0 ammo and are used for tracking/intercept maneuvers only."
}
```

## 调用 70（tick 700）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6383.0, 15272.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10473.0, 12153.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6679.0, 18037.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-6567.0, 407.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4549.0, 70.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5189.0, -2884.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-03, boat-04, boat-05) are currently in the immediate vicinity of the protected zone (dist_zone < 5km) and are the highest priority threats. boat-03 is observed by usv-02 (can_intercept=true) and uav-04 (current target). boat-04 is observed by uav-08 (current target). boat-05 is observed by usv-01 (can_intercept=true) but usv-01 has 0 ammo; uav-04 is already tasked with boat-03. To maximize kill probability and spread fire, usv-02 engages boat-03 (closest, highest threat 0.92). uav-08 continues engaging boat-04. uav-04 continues engaging boat-03 (secondary coverage). The air contacts (strike-comms/fuel) are far away (dist_zone > 20km) and not yet in intercept range (prepare=false), so UAVs are held in patrol positions to conserve ammo and maintain situational awareness."
}
```

## 调用 71（tick 710）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6632.0, 18292.0]}, "priority": 0.2, "deadline": 60},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3918.0, -2172.0]}, "priority": 0.2, "deadline": 60},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [5245.0, -2919.0]}, "priority": 0.2, "deadline": 60},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-6804.0, 475.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-4733.0, 183.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300}
  ],
  "reasoning": "USV-02 is the only unit with ammo and can_intercept=true for the high-threat surface boat-03; assigned to intercept. UAV-02, UAV-01, and UAV-08 are assigned to the three distinct air threats (comms-02, comms-03, comms-04) respectively, as they are the closest interceptors to these targets and have ammo. UAV-03, UAV-04, and USV-01 have 0 ammo and are disengaged to conserve resources/return to anchor. UAV-06 and UAV-07 are held in reserve to react to any new threats or if the primary interceptors fail."
}
```

## 调用 72（tick 720）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-7042.0, 526.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-4922.0, 300.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6557.0, 18535.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4032.0, -1993.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5303.0, -2952.0]}, "priority": 0.4}
  ],
  "reasoning": "USV-02 is the only unit with ammo and can_intercept=true for the high-threat surface boats (0.91, 0.86) currently near the zone; it is tasked to engage them. UAV-02 and UAV-01 are tasked to intercept the air contacts they observe (comms-02 and comms-04 respectively) as they approach, utilizing their ammo. UAV-08 is tasked to intercept comms-02 as a secondary layer since it is closer than UAV-01 to that specific target's approach vector, though UAV-01 is also tasked to cover the other air contact. UAV-06 and UAV-07 are held in reserve near the objective to react to any new threats or if the primary interceptors fail. UAV-03 and UAV-04 are out of ammo and disengaged. USV-01 is a sensor-only unit and is patrolling to maintain observation."
}
```

## 调用 73（tick 730）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "ambush_fuel02_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "ambush_fuel03_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "ambush_comms03_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "ambush_comms02_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6480, 18776]}, "priority": 0.1, "deadline": 60},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5361, -2982]}, "priority": 0.3, "deadline": 60}
  ],
  "reasoning": "Immediate threat: 3 surface boats (03, 04, 05) are within weapon range of USV-02, UAV-08, and UAV-07 respectively. USV-02 is assigned to Boat-03 (highest threat 0.93, closest to zone). UAV-08 and UAV-07 are assigned to Boat-04 and Boat-05 as they are the only armed units observing them (Interface Rule). The air threats (Fuel/Comms) are far away (11-17km) but approaching. UAV-04 and UAV-06 are positioned to ambush the high-threat Fuel wave. UAV-01 and UAV-02 are positioned to ambush the Comms wave. UAV-03 is out of ammo and disengaging. USV-01 is a sensor-only unit and is patrolling to maintain coverage."
}
```

## 调用 74（tick 740）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6427.0, 19027.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4229.0, -1617.0]}, "priority": 0.2},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [5418.0, -3013.0]}, "priority": 0.2}
  ],
  "reasoning": "USV-02 is the only unit with ammo and can_intercept=true for boat-03 (closest to zone, high threat). UAV-02 and UAV-01 are closest to the comms strike group (comms-04 and comms-03) and should begin intercept maneuvers now as they are the primary air threats. UAV-06, 08, and 07 continue tracking their assigned surface/air threats. UAV-03, UAV-04, and USV-01 have 0 ammo and are disengaged to conserve energy/return to base."
}
```

## 调用 75（tick 750）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.70, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6367.0, 19278.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4331.0, -1430.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [5476.0, -3044.0]}, "priority": 0.1}
  ],
  "reasoning": "USV-02 is the only unit with ammo and can_intercept=true for the high-threat surface boat-04 (threat 0.92, dist 2507m). It is assigned to engage. The air threats (comms-03, comms-02, comms-04) are approaching with prepare_intercept=false but closing rapidly (ttr < 120t for UAV-02). UAV-02, UAV-01, UAV-08, UAV-07, and UAV-06 are assigned to intercept the air threats to establish early engagement geometry. UAV-02 is closest to comms-03 (range_gap 2817m). UAV-01 and UAV-08 are assigned to comms-03 and comms-02 respectively to spread coverage. UAV-07 and UAV-06 are assigned to comms-03 as secondary support given their positions. UAV-03, UAV-04, and USV-01 have 0 ammo and are disengaged to conserve energy/return to base."
}
```

## 调用 76（tick 760）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-02"}, "priority": 0.7, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5533.0, -3077.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6314.0, 19527.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4425.0, -1241.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 engages boat-03 (can_intercept=true, highest threat 0.93). UAV-08 engages boat-04 (can_intercept=true, threat 0.91). UAV-02 and UAV-01 engage the closest air threats (comms-03 and comms-04) which are approaching and will enter range soon. UAV-06 and UAV-07 engage the fuel strike wave (fuel-02 and fuel-03) which are further out but high threat. USV-01, UAV-03, and UAV-04 are out of ammo or too far, so they hold position."
}
```

## 调用 77（tick 770）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.6, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.5, "deadline": 180},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1},
    {"task_id": "return_002", "goal_type": "return", "parameters": {"unit_id": "defender.uav-04"}, "priority": 0.1},
    {"task_id": "return_003", "goal_type": "return", "parameters": {"unit_id": "defender.usv-01"}, "priority": 0.1}
  ],
  "reasoning": "Immediate threat: boat-04 is inside weapon range of usv-02 (can_intercept=true) and uav-08 (current target). Assigning both to engage to ensure kill. Strike-comms-03 is the closest air threat to the zone (dist_zone ~19km) and is observed by uav-02 (current target) and facility.pier. Assigning uav-02 to intercept it. Strike-comms-04 is also approaching; uav-01 is assigned to intercept it as it is the closest armed UAV to that bearing. Strike-fuel-02 is the fastest approaching air threat (closing 43m/t); uav-06 and uav-07 are assigned to intercept it to cover the axis. UAV-03, UAV-04, and USV-01 are out of ammo and returning to base."
}
```

## 调用 78（tick 780）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.7, "deadline": 240},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.6, "deadline": 300},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.5, "deadline": 360},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4605.0, -862.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.4}
  ],
  "reasoning": "USV-02 is in range of boat-03 (highest threat surface contact) and must engage immediately. UAV-08 continues tracking boat-04 which is receding but still a threat. UAV-02 is closest to the comms strike wave and assigned to strike-comms-02. UAV-01 assigned to strike-comms-03. UAV-07 and UAV-06 assigned to the fuel strike wave which is approaching faster. UAV-03 and UAV-04 have no ammo and are disengaged to rear anchors. USV-01 tracks boat-05 as it is receding and out of weapon range for the USV."
}
```

## 调用 79（tick 790）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 240},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.6, "deadline": 300},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.6, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4627.0, -652.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for the high-threat surface boats (boat-03, boat-04, boat-05) which are close to the zone boundary. Assigning USV-02 to the highest threat (boat-03) to engage immediately. UAV-08 is already tasked with boat-04 (surface, high threat) and is in position, so maintaining that intercept. The air threats (comms and fuel) are approaching but further out. UAV-02 is closest to the comms wave and has ammo, so assigning it to the fastest comms target (comms-04). UAV-01 is assigned to comms-02. UAV-06 and UAV-07 are assigned to the fuel wave targets they are best positioned for. UAV-03 and UAV-04 have no ammo and are disengaged to rear anchors. USV-01 has no ammo and is tracking the fuel wave for sensor support."
}
```

## 调用 80（tick 800）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04"}, "priority": 0.9, "deadline": 15},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03"}, "priority": 0.9, "deadline": 15},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-5574, 918], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154, 19998]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.5}
  ],
  "reasoning": "USV-02 engages boat-03 (can_intercept=true, highest threat 0.94). UAV-08 and UAV-06 engage boat-04 and boat-03 respectively (can_intercept=true). UAV-04 engages strike-fuel-02 (prepare_intercept=true, high threat 0.64, closest to zone). UAV-02 and UAV-01 engage comms targets (prepare_intercept=false but approaching, maintaining coverage). UAV-07 held in reserve. UAV-03 disengaged (0 ammo). USV-01 tracks fuel-02 (0 ammo, sensor only)."
}
```

## 调用 81（tick 810）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5822.0, -3229.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4743.0, -244.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-5702.0, 1073.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is assigned to intercept boat-03 (highest threat 0.94, can_intercept=true) as it is the only unit with ammo capable of engaging surface targets in range. UAV-08 and UAV-06 continue intercepting boat-04 and boat-03 respectively to maintain pressure on surface threats. UAV-02 is assigned to intercept strike-comms-03 (prepare_intercept logic: approaching, feasible_eta=40t) to engage the air threat before it reaches the zone. UAV-01 is assigned to intercept strike-comms-02 (approaching, feasible_eta=208t but closer than others for that unit) to prepare for engagement. USV-01 and UAV-03/04/07 are out of ammo or too far to engage effectively, so they hold position to maintain sensor coverage."
}
```

## 调用 82（tick 820）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.90, "deadline": 10},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05"}, "priority": 0.85, "deadline": 10},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.80, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02"}, "priority": 0.70, "deadline": 60},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03"}, "priority": 0.60, "deadline": 120},
    {"task_id": "intercept_008", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-04"}, "priority": 0.55, "deadline": 120},
    {"task_id": "intercept_009", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03"}, "priority": 0.50, "deadline": 120},
    {"task_id": "intercept_010", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04"}, "priority": 0.45, "deadline": 120},
    {"task_id": "intercept_011", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.40, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.10},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [5879.0, -3261.0]}, "priority": 0.10}
  ],
  "reasoning": "USV-02 is the only unit with can_inter
```

## 调用 83（tick 830）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6077.0, 16779.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-9393.0, 1024.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6039.0, 1361.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [1957.0, 9268.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5936.0, -3291.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 has can_intercept=true for boat-04 (high threat, close to zone) and is the only unit with ammo in that sector, so it engages. UAV-04 has prepare_intercept=true for strike-fuel-02 (high threat, fast closing) and is the closest armed unit to that axis, so it intercepts. UAV-02 is closest to strike-comms-04 (prepare_intercept=false but feasible_eta is low) and is already tracking a comms target, so it shifts to the higher priority fuel/comms threat. Other units hold position to conserve ammo and maintain coverage."
}
```

## 调用 84（tick 840）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6037.0, 16958.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-9634.0, 1033.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6203.0, 1510.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "USV-02 is in range of boat-04 (can_intercept=true) and must engage immediately to prevent zone entry. UAV-04 is the only unit with prepare_intercept=true for the high-threat fuel-02 (ttr=31t) and must intercept now despite ammo=0 (likely decoy or sensor-only role, but must maneuver to deny entry). UAV-02 is closest to comms-04 (approaching, ttr=247t) and should begin intercept maneuver. USV-01 and UAV-08 track the remaining high-threat boats (04 and 03) to maintain sensor coverage. Other UAVs hold position to conserve energy and maintain sensor posture."
}
```

## 调用 85（tick 850）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4900.0, 163.0]}, "priority": 0.2},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [6054.0, -3346.0]}, "priority": 0.2},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6370.0, 1650.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for the high-threat surface boats (boat-03, boat-04, boat-05) which are receding but close to the zone; assigning it to the highest threat (boat-03) to secure the perimeter. UAV-02, UAV-08, and UAV-06 are assigned to the air threats (strike-comms-04, strike-comms-03, strike-comms-02) respectively, as they are the closest feasible interceptors with ammo. UAV-03, UAV-04, and USV-01 have 0 ammo and are disengaged to conserve resources/return to base. UAV-07 is held in reserve/patrol as it is too far to effectively intercept the current air wave before they potentially reach the zone or before other units engage."
}
```

## 调用 86（tick 860）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6114.0, -3372.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5969.0, 17156.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-10113.0, 1048.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6522.0, 1813.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [1766.0, 9661.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for the high-threat surface boat-03 (dist 2866m, threat 0.95); assigned to intercept with salvo to maximize kill probability. UAV-04 has prepare_intercept=true for strike-fuel-03 (dist 9188m, closing 37.68m/t, threat 0.67); assigned to intercept now to maneuver into position. UAV-02 has prepare_intercept=true for strike-comms-02 (dist 9839m, closing -4.22m/t but prepare flag set); assigned to intercept to maintain pressure. Other units hold position to conserve ammo and maintain sensor coverage, as no other targets are in immediate intercept window."
}
```

## 调用 87（tick 870）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6173.0, -3400.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5922.0, 17330.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-10347.0, 1097.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6684.0, 1966.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [1701.0, 9792.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with ammo and can_intercept=true for the high-threat surface boat-04 (dist 2827m, threat 0.93). Assigning it to intercept. UAV-04 has prepare_intercept=true for the high-threat air target strike-fuel-02 (dist 8175m, threat 0.70, closing fast) and is the closest armed unit to it, so assigning intercept. UAV-02 has prepare_intercept=true for strike-comms-04 (dist 9201m, threat 0.62) and is the closest armed unit to it, so assigning intercept. Other units are either out of ammo (UAV-03, UAV-04, USV-01) or too far to be effective for the current threats, so they are held in patrol to maintain sensor coverage and readiness."
}
```

## 调用 88（tick 880）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5883.0, 17523.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [13097.0, 12897.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4900.0, 776.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_
```

## 调用 89（tick 890）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4936.0, 983.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [6290.0, -3457.0]}, "priority": 0.5, "deadline": 60}
  ],
  "reasoning": "USV-02 engages boat-04 (can_intercept=true, high threat). UAV-02, UAV-01, and UAV-08 are assigned to the three distinct air threats (comms-04, comms-03, comms-02) respectively, as they are the closest armed units to their respective targets and can maneuver into position. UAV-07 and UAV-06 are assigned to the distant fuel threats (fuel-04, fuel-03) to prepare for interception as they approach. UAV-03, UAV-04, and USV-01 are out of ammo and disengaged to conserve resources/return to base."
}
```

## 调用 90（tick 900）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.70, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4978.0, 1189.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [6349.0, -3484.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-11061.0, 1201.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "USV-02 engages boat-04 (can_intercept=true, high threat 0.93) with salvo to conserve future options. UAV-07 intercepts strike-fuel-03 (highest threat 0.72, approaching). UAV-08 and UAV-02 intercept comms-03 and comms-04 respectively to spread coverage of the incoming air wave. UAV-01 intercepts comms-02. UAV-04, UAV-03, and USV-01 are disengaged due to 0 ammo. UAV-06 held in reserve."
}
```

## 调用 91（tick 910）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_comms_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_comms_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03"}, "priority": 0.80, "deadline": 180},
    {"task_id": "intercept_comms_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.75, "deadline": 240},
    {"task_id": "track_boat_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.60},
    {"task_id": "track_boat_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04"}, "priority": 0.60},
    {"task_id": "reserve_uav_006", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-11297.0, 1253.0], "commit_within_m": 9000}, "priority": 0.40},
    {"task_id": "reserve_uav_007", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-7348.0, 2566.0], "commit_within_m": 9000}, "priority": 0.40},
    {"task_id": "disengage_uav_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.10}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the closest threat (strike-fuel-02, dist 7050m, closing fast) and is currently assigned to it; maintain intercept. UAV-02 is closest to strike-comms-04 (dist 9715m, prepare_intercept imminent) and has ammo; assign intercept. UAV-01 and UAV-08 are positioned to intercept the remaining comms threats (strike-comms-03 and strike-comms-02) which are approaching the zone; assign intercept to spread coverage. USVs track the high-threat surface boats (boat-04, boat-05) which are receding but remain a threat. UAV-06 and UAV-07 held as reserves with auto-commit triggers. UAV-03 has 0 ammo and is disengaged."
}
```

## 调用 92（tick 920）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_fuel04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_comms03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 180},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6, "deadline": 300},
    {"task_id": "return_uav03_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1, "deadline": 600}
  ],
  "reasoning": "UAV-06 and UAV-07 are assigned to the fuel intruders (02 and 04) which are approaching from the east/northeast and have the highest threat scores (0.72/0.71) among the air targets, despite being far away; early intercept is necessary to prevent them from reaching the zone. UAV-02, UAV-08, and UAV-01 are assigned to the comms intruders (03, 02, 04) which are currently receding but will likely turn or are part of a coordinated wave; intercepting them now positions the UAVs for engagement if they approach. USVs track the surface boats (04 and 05) which are close to the zone but receding; they are high threat (0.95/0.93) but currently moving away, so tracking is appropriate to maintain observation. UAV-03 has no ammo and is returned to base."
}
```

## 调用 93（tick 930）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.4},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.4}
  ],
  "reasoning": "No targets currently have can_intercept=true. UAV-02 is closest to the highest threat (strike-comms-03) and is assigned to intercept. UAV-08 is assigned to strike-comms-02 (second highest threat) as it is well-positioned. UAV-01 is assigned to strike-comms-04. UAV-07 and UAV-06 are assigned to the approaching fuel strikes (strike-fuel-02 and strike-fuel-04) to prepare for interception as they close. UAV-03 has no ammo and is disengaged. USVs are tracking their respective observed threats to maintain sensor coverage."
}
```

## 调用 94（tick 940）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_fuel03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_comms03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 240},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.6, "deadline": 300},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1, "deadline": 600},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-11909.0, 1634.0], "commit_within_m": 9000}, "priority": 0.4, "deadline": 600}
  ],
  "reasoning": "UAV-08 intercepts strike-fuel-02 (prepare_intercept=true, closest to zone) to prevent boundary crossing. UAV-07 intercepts strike-fuel-03 (high threat, approaching). UAV-02 and UAV-01 engage comms-03 and comms-04 respectively to spread fire discipline across the air threat cluster. USVs track the high-threat surface boats (boat-04/05) which are receding but close to the zone. UAV-03 is disengaged due to 0 ammo. UAV-06 held in reserve."
}
```

## 调用 95（tick 950）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_comms03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.90, "deadline": 60},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.85, "deadline": 60},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-12108, 1764], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154, 19998]}, "priority": 0.10}
  ],
  "reasoning": "No targets currently have can_intercept=true. UAV-07 is assigned to strike-fuel-02 (highest threat 0.76, closest to zone at 9454m, approaching) to prepare for early engagement. UAV-02, UAV-08, and UAV-01 are assigned to the three strike-comms targets (threats 0.71-0.74) which are approaching and will enter range soon; spreading them ensures coverage. USVs track the two high-threat surface boats (0.94, 0.89) which are receding but close to the zone. UAV-06 holds reserve. UAV-03 has 0 ammo and is disengaged."
}
```

## 调用 96（tick 960）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_comms03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_fuel03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_fuel02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "No targets have can_intercept=true. However, strike-fuel-03 and strike-fuel-02 are approaching rapidly (closing > 25 m/t) and are the highest threat (0.77, 0.71). UAV-07 and UAV-06 are assigned to intercept them early to prevent zone entry. UAV-08, UAV-02, and UAV-01 are assigned to the comms intruders (0.69, 0.65, 0.62) which are also approaching but slower. UAV-03 has 0 ammo and is disengaged. USVs track the high-threat fuel intruders to maintain sensor coverage."
}
```

## 调用 97（tick 970）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.6, "deadline": 100},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1, "deadline": 100}
  ],
  "reasoning": "No targets currently have can_intercept=true. The closest threats to the protected zone are the strike-comms group (dist_zone ~10km) and the strike-fuel group (dist_zone ~9km). UAV-08 and UAV-02 are closest to the comms group and are assigned to intercept strike-comms-04 (lowest ETA). UAV-07 and UAV-06 are assigned to intercept strike-comms-02 (highest threat in that group). UAV-01 is assigned to intercept strike-comms-03. The USVs are tracking the nearby fuel targets which are currently outside the UAVs' effective engagement geometry or to maintain sensor coverage. UAV-03 is out of ammo and returning to reserve."
}
```

## 调用 98（tick 980）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_fuel_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_comms_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_comms_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "track_boat_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_fuel_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.8, "deadline": 60},
    {"task_id": "return_uav_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1}
  ],
  "reasoning": "UAV-06 and UAV-07 are assigned to the two fuel intruders which are approaching rapidly (TTR < 300t) and have the highest closing speeds. UAV-08, UAV-02, and UAV-01 are assigned to the three comms intruders to maintain coverage and prepare for engagement as they close. USV-02 tracks the high-threat surface boat-05, while USV-01 tracks the fuel intruders to provide sensor data for the UAVs. UAV-03 is out of ammo and returning to base."
}
```

## 调用 99（tick 990）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 100},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6174.0, 19705.0]}, "priority": 0.5, "deadline": 100}
  ],
  "reasoning": "No targets have can_intercept=true. Prioritizing high-threat targets with prepare_intercept=true or approaching vectors. UAV-08 assigned to strike-comms-03 (highest threat 0.75, approaching, feasible). UAV-02 assigned to strike-comms-04 (threat 0.68, feasible, closest ETA). UAV-07 assigned to strike-comms-02 (threat 0.74, approaching). UAV-06 assigned to strike-fuel-02 (threat 0.74, approaching). USVs tracking nearby contacts for sensor fusion. UAV-03 returning due to 0 ammo. UAV-01 holding position as it is far from the main threat axis and has no feasible intercepts."
}
```

## 调用 100（tick 1000）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.70, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6}
  ],
  "reasoning": "No targets currently have can_intercept=true. However, strike-comms-02 has prepare_intercept=true and is the highest threat (0.79) with the shortest TTR (44.8t) among approaching threats, so uav-08 (closest feasible interceptor) is assigned to intercept it immediately. Other high-threat approaching targets (strike-fuel-02, strike-fuel-03, strike-comms-04, strike-comms-03) are assigned to the nearest available armed UAVs to prepare for interception as they close. uav-03 has 0 ammo and is disengaged. USVs are tasked to track the highest threat surface contact (boat-05) and the primary air threat (strike-comms-02) to maintain sensor coverage."
}
```

## 调用 101（tick 1010）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.95},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.95},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [13692.0, 13107.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-13207.0, 2687.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-8972.0, 3682.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [832.0, 11660.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true. The only prepare_intercept=true target (strike-fuel-04) is observed by USV-02 but has domain_ok=false (air target vs surface unit), making it infeasible for USV-02 to engage. All other targets are far away (dist > 10km) and receding or approaching slowly, with no immediate threat to the protected zone. USV-01 and USV-02 are tasked to track the high-threat surface contact boat-05 (threat 0.92) to maintain sensor coverage. UAVs are holding position to conserve energy and wait for targets to enter intercept range or for new threats to emerge. UAV-03 is disengaging as it has 0 ammo."
}
```

## 调用 102（tick 1020）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_fuel02_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_comms04_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_comms02_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_comms03_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "disengage_uav03_006", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "track_boat05_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6},
    {"task_id": "patrol_usv01_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6994.0, -3867.0]}, "priority": 0.4}
  ],
  "reasoning": "No targets currently have can_intercept=true. However, strike-fuel-03 (threat 0.83) and strike-fuel-02 (threat 0.77) are approaching the protected zone from the East (bearing ~106-113) with ETAs of ~400-410 ticks. UAV-07 and UAV-06 are the closest armed assets to this axis and are assigned to intercept them early to prevent boundary crossing. Strike-comms-04 (threat 0.79) is also approaching (bearing 90-95) and is assigned to UAV-08 which has a feasible intercept window. Strike-comms-02 (threat 0.76) is approaching and observed by USV-02 (prepare_intercept=true), so UAV-02 is assigned to intercept it. Strike-comms-03 (threat 0.72) is assigned to UAV-01. UAV-03 has 0 ammo and is disengaged. USV-02 tracks the high-threat surface boat-05 (threat 0.84) which is close to the zone but receding; USV-01 holds position as a sensor."
}
```

## 调用 103（tick 1030）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 186},
    {"task_id": "intercept_fuel04_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 278},
    {"task_id": "intercept_comms02_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 92},
    {"task_id": "intercept_comms03_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 143},
    {"task_id": "intercept_comms04_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 247},
    {"task_id": "track_boat05_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.9, "deadline": 495},
    {"task_id": "track_fuel03_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.8, "deadline": 254},
    {"task_id": "disengage_uav03_008", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 100}
  ],
  "reasoning": "UAV-07 and UAV-06 are assigned to the high-threat fuel intruders (0.82) which are approaching and have the shortest ETAs to the zone (175t and 528t respectively, though fuel-02 is closer). UAV-08 and UAV-02 are assigned to the comms intruders (0.82/0.79) which are also approaching and have feasible intercept windows. UAV-01 is assigned to comms-04 (0.75) as a secondary threat. USVs are tasked with tracking the high-threat surface boat (0.94) and the fuel-03 intruder to maintain sensor coverage, as they lack the speed/range to intercept effectively. UAV-03 is disengaged as it has 0 ammo."
}
```

## 调用 104（tick 1040）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.7},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-01", "duration": 10}, "priority": 0.2}
  ],
  "reasoning": "UAV-08 is the closest feasible interceptor to the high-threat Comms-04 (threat 0.81, prepare_intercept=true, feasible_eta=93t) and is assigned to intercept. UAV-02 is also feasible for Comms-04 (eta=143t) and is assigned as a secondary interceptor to ensure engagement if UAV-08 fails or is delayed. UAV-07 is assigned to Fuel-02 (threat 0.77, approaching, feasible_eta=181t) to cover the fuel axis. UAV-06 is assigned to Fuel-04 (threat 0.81, approaching, feasible_eta=311t) to cover the other fuel threat. USVs are tasked to track their respective observed contacts to maintain sensor ownership. UAV-03 has 0 ammo and is disengaged. UAV-01 is held as it has no feasible intercept options for the current high-priority targets."
}
```

## 调用 105（tick 1050）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.85, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.7, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14014.0, 13758.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1, "deadline": 100}
  ],
  "reasoning": "No targets have can_intercept=true. UAV-08 is assigned to strike-comms-02 (closest feasible intercept, threat 0.80) and UAV-07 to strike-fuel-04 (highest threat 0.83, approaching). UAV-06 covers strike-fuel-02 (threat 0.79). USVs track their respective contacts to maintain sensor ownership. UAV-01 and UAV-02 hold position as they are too far to engage current threats effectively. UAV-03 is disengaged due to 0 ammo."
}
```

## 调用 106（tick 1060）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.85, "deadline": 200},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.80, "deadline": 250},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14129.0, 13905.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.6}
  ],
  "reasoning": "strike-fuel-02 is the highest threat (0.89) and closest to the zone (4685m), approaching fast. uav-07 is the closest armed interceptor to it (14691m) and is assigned to intercept. strike-comms-02 and strike-comms-03 are also approaching and have prepare_intercept=true; uav-06 and uav-08 are assigned to intercept them respectively to spread the load. uav-01 and uav-02 are holding position as they are far from the immediate threat axis. uav-03 has no ammo and is disengaging. USVs are tracking the nearest contacts to maintain sensor coverage."
}
```

## 调用 107（tick 1070）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 160},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 170},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 280},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "distance": 2500.0}, "priority": 0.6},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.4}
  ],
  "reasoning": "USV-02 is the only unit with prepare_intercept=true for the closest threat (strike-comms-02, TTR 3.9t), so it must engage immediately. UAV-08 is the closest armed interceptor to the high-threat comms-03 (feasible_eta 97t) and should intercept it. UAV-02 is assigned to the only feasible target in its sector (strike-command-04). UAV-07 and UAV-06 are positioned to intercept the fuel tankers (high threat 0.89/0.84) which are approaching from the west. UAV-03 is out of ammo and disengaging. USV-01 tracks the closest fuel tanker to maintain sensor coverage. UAV-01 holds position as it is too far to be effective on current targets."
}
```

## 调用 108（tick 1080）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 1100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.9, "deadline": 1100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.85, "deadline": 1100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-03"}, "priority": 0.8, "deadline": 1100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.75, "deadline": 1100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.6, "deadline": 1100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6, "deadline": 1100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1, "deadline": 1100}
  ],
  "reasoning": "No targets have can_intercept=true. Several high-threat targets have prepare_intercept=true (strike-comms-03, strike-comms-02, strike-comms-04) or are approaching with short TTR (strike-fuel-02, strike-fuel-04). UAV-08 is closest to the comms cluster (feasible_eta ~100t) and is assigned to the highest threat (comms-03). UAV-07 is closest to fuel-02 (TTR 208t) and assigned to it. UAV-06 is assigned to fuel-04 (TTR 421t). UAV-02 is assigned to command-03 (approaching, TTR 83t). UAV-01 is assigned to comms-04. USVs are sensors only (domain_ok=false for intercept) and are tasked to track the closest contacts to maintain observation. UAV-03 has 0 ammo and is disengaged."
}
```

## 调用 109（tick 1090）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 103},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 263},
    {"task_id": "intercept_command04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 171},
    {"task_id": "intercept_fuel04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 249},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_comms04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.5},
    {"task_id": "track_command03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-03"}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true. UAV-07 is assigned to strike-fuel-02 (highest threat 0.91, approaching, feasible_eta 150t). UAV-08 is assigned to strike-comms-02 (threat 0.86, feasible_eta 103t). UAV-01 and UAV-02 are assigned to strike-comms-04 and strike-command-04 respectively to cover the next closest feasible threats. UAV-06 covers strike-fuel-04. UAV-03 has 0 ammo and is disengaged. USVs continue tracking their current targets to maintain sensor coverage."
}
```

## 调用 110（tick 1100）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_command04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-15138.0, 3500.0], "commit_within_m": 9000}, "priority": 0.7},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "track_comms04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6},
    {"task_id": "track_fuel04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.6}
  ],
  "reasoning": "No targets have can_intercept=true. Several high-threat targets have prepare_intercept=true or are approaching with low TTR. UAV-07 is closest to strike-fuel-02 (highest threat, approaching) and assigned to intercept. UAV-08 is closest to strike-comms-02 (high threat, approaching) and assigned to intercept. UAV-02 is closest to strike-comms-04 (high threat, approaching) and assigned to intercept. UAV-01 is closest to strike-command-04 (medium threat, receding but feasible) and assigned to intercept. UAV-06 held as reserve. UAV-03 has 0 ammo and is disengaged. USVs track their respective contacts for sensor fusion."
}
```

## 调用 111（tick 1110）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.95, "deadline": 1150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.9, "deadline": 1150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 1150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.8, "deadline": 1150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6}
  ],
  "reasoning": "UAV-07 and UAV-06 are closest to the high-threat fuel intruders (strike-fuel-03 and strike-fuel-02) which are approaching the zone; intercepting them early prevents boundary breach. UAV-08 intercepts strike-comms-04 which is feasible and approaching. UAV-02 intercepts strike-command-03 which is feasible and approaching. UAV-01 and UAV-03 are far north and have no feasible intercepts for the current close threats; UAV-03 has no ammo so it disengages. USVs track the closest contacts to maintain sensor coverage."
}
```

## 调用 112（tick 1120）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_fuel_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_command_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.70},
    {"task_id": "track_command_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.70},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.50},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14550.0, 14910.0]}, "priority": 0.50},
    {"task_id": "disengage_uav_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.10}
  ],
  "reasoning": "No targets have can_intercept=true. UAV-07 is closest to the high-threat fuel-02 (dist 13.5km, closing) and assigned to intercept. UAV-06 assigned to fuel-04 (fastest closing, ttr 387t). UAV-08 assigned to comms-02 (closest comms threat, ttr 217t). USVs track command targets to maintain sensor coverage. UAV-03 has 0 ammo and is disengaged. Other UAVs hold position as reserve."
}
```

## 调用 113（tick 1130）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_comms03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_cmd03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.5},
    {"task_id": "track_cmd04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.5}
  ],
  "reasoning": "strike-fuel-02 is the highest threat (0.95) and closest to the zone (1733m), with uav-07 having the shortest feasible ETA (128t). uav-06 is assigned to strike-comms-02 (0.92 threat, 3042m) as it is the closest armed unit to that axis. uav-08 and uav-01 are assigned to the remaining high-threat comms targets (0.89 and 0.83) to maintain fire discipline and cover multiple axes. uav-03 is disengaged due to 0 ammo. USVs are tasked to track the command targets to maintain sensor coverage."
}
```

## 调用 114（tick 1140）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14795.0, 15174.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [139.0, 13524.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "strike-fuel-02 is the highest priority threat (dist_zone=1352m, closing=19.49m/t, ttr=252t). It is observed by usv-01. uav-07 is the closest armed interceptor (range_gap=4916m, ttr=252t) and is assigned to intercept. uav-06 is the second closest (range_gap=9073m) and is assigned as a backup to ensure engagement if uav-07 fails or is delayed. usv-01 and usv-02 are sensor-only (or low ammo) and are tasked to track the primary threats to maintain observation for the interceptors. uav-03 has 0 ammo and is disengaged. Other UAVs are holding position as they are too far to engage the immediate threat effectively before it reaches the zone."
}
```

## 调用 115（tick 1150）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14910.0, 15315.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1, "deadline": 120}
  ],
  "reasoning": "UAV-07 is closest to the high-threat fuel-03 (dist 13km, closing 50m/t) and comms-02; assigned to fuel-03 as it is the most imminent threat to the zone (dist_zone 1577m). UAV-06 is assigned to comms-02 (dist 17km, closing 24m/t) to cover the second most dangerous axis. UAV-08 is assigned to comms-04 which has prepare_intercept=true and is approaching. USVs are tracking their respective contacts to maintain sensor ownership. UAV-01 and UAV-02 are holding position as they are too far to engage the current threats effectively. UAV-03 is disengaging due to 0 ammo."
}
```

## 调用 116（tick 1160）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_fuel_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_comms_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_comms_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154, 19998]}, "priority": 0.1},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.5},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true, but several high-threat targets are approaching (strike-fuel-02, strike-comms-02, strike-comms-04). UAV-07 and UAV-06 are closest to the highest threat (fuel-02) and are assigned to intercept. UAV-08, UAV-01, and UAV-02 are assigned to the other approaching comms targets to spread coverage. UAV-03 has no ammo and is disengaged. USVs continue tracking for sensor coverage."
}
```

## 调用 117（tick 1170）

```
{
  "goal_commands": [
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "ambush_uav07_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "standoff_m": 500}, "priority": 0.95},
    {"task_id": "ambush_uav06_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "standoff_m": 500}, "priority": 0.9},
    {"task_id": "ambush_uav08_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.85},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15037.0, 15647.0]}, "priority": 0.5},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.6},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.6}
  ],
  "reasoning": "No targets are currently in the intercept window (can_intercept=false) or preparing to enter (prepare_intercept=false). The high-threat 'fuel' and 'comms' targets are approaching from the north/northwest. UAV-07 and UAV-06 are closest to the 'fuel' threats and are positioned to ambush them before they reach the protected zone. UAV-08 is closest to 'comms-04' and will ambush it. UAV-03 has no ammo and is disengaged. UAV-01 and UAV-02 are too far to be effective against the current wave and are holding position. USVs continue tracking their assigned contacts for sensor fusion."
}
```

## 调用 118（tick 1180）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.99, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.97, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.95, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15162.0, 15779.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8}
  ],
  "reasoning": "UAV-07, UAV-06, and UAV-08 are assigned to the three closest high-threat intruders (fuel-03, fuel-02, comms-02) which are approaching the protected zone. Although can_intercept is false, the targets are within the effective engagement window for these specific units (range_gap < 10km) and are the highest priority threats. UAV-01 and UAV-02 are held in reserve as they are too far to engage the current wave effectively. UAV-03 is disengaged due to 0 ammo. USVs are tasked with tracking to maintain sensor coverage on the remaining contacts."
}
```

## 调用 119（tick 1190）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15266.0, 15925.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6}
  ],
  "reasoning": "UAV-07 and UAV-06 are the closest interceptors to the high-threat comms-02 and comms-03 targets respectively, which are approaching the zone (dist_zone < 1300m). UAV-08 is assigned to comms-04 to cover the third threat. UAV-01 and UAV-02 are too far to intercept effectively (feasible=false) and are held in position. UAV-03 has no ammo and is disengaged. USVs continue tracking to maintain sensor coverage."
}
```

## 调用 120（tick 1200）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15333.0, 16086.0]}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_comms04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6},
    {"task_id": "track_comms02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6}
  ],
  "reasoning": "UAV-07 is closest to the high-threat fuel-03 (dist 12.7km, approaching) and assigned to intercept. UAV-06 is closest to comms-02 (dist 16.9km, stable) and assigned to intercept. UAV-08 is assigned to fuel-02 (dist 15.3km) to cover the third high-threat target. UAV-01 and UAV-02 are held in reserve/patrol as they are far from the immediate threat cluster. UAV-03 has 0 ammo and is disengaged. USVs continue tracking their respective contacts for sensor fusion."
}
```

## 调用 121（tick 1210）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.6}
  ],
  "reasoning": "No targets have can_intercept=true, but several have prepare_intercept=true or are approaching with high threat. UAV-07 is closest to strike-comms-04 (approaching, ttr=107.8) and should intercept now. UAV-06 is closest to strike-fuel-04 (approaching, ttr=272.1). UAV-01 is closest to strike-fuel-02 (approaching, ttr=2066.0 but closing). UAV-02 is closest to strike-command-04 (receding but high threat). UAV-03 has 0 ammo, so disengage. USVs track their observed contacts for sensor coverage."
}
```

## 调用 122（tick 1220）

```
{
  "goal_commands": [
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.95, "deadline": 120},
    {"task_id": "ambush_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "standoff_m": 500}, "priority": 0.9, "deadline": 120},
    {"task_id": "ambush_003", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "standoff_m": 500}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15509.0, 16395.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "All threats are currently receding or far outside weapon range (range_ratio > 1.5). No unit has can_intercept=true. UAV-07 is closest to the threat axis (bearing 101) and assigned to ambush the highest threat (strike-comms-04). UAV-06 and UAV-08 are positioned to ambush the other high-threat contacts (strike-comms-03 and strike-fuel-02) as they approach. USVs continue tracking to maintain sensor coverage. UAV-03 is out of ammo and disengaging. UAV-01 and UAV-02 are too far to be effective for immediate interception and are holding position to conserve fuel/position for potential future waves."
}
```

## 调用 123（tick 1230）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289, 19998], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [15630, 16534], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154, 19998]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.4},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.4}
  ],
  "reasoning": "Three high-threat intruders (comms-02, comms-03, fuel-03) are approaching the protected zone from the south/southwest (bearing ~200). UAV-07, UAV-06, and UAV-08 are the closest armed interceptors with feasible ETAs to reach weapon range before the targets cross the boundary. Assigning them to intercept the respective targets. UAV-01 and UAV-02 are held in reserve at their current positions to react to any new threats or if the primary interceptors fail. UAV-03 has no ammo and is disengaged. USVs are tasked to track the contacts to maintain sensor coverage."
}
```

## 调用 124（tick 1240）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15782.0, 16630.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6}
  ],
  "reasoning": "No targets have can_intercept=true. UAV-07 is closest to the high-threat comms-04 (dist 12910m, receding) and assigned to intercept to close the gap. UAV-06 assigned to fuel-03 (dist 18641m, receding) as the next closest high-threat target. UAV-08 assigned to comms-02 (dist 14642m, receding) to cover the southern axis. UAV-01 and UAV-02 are far from the immediate threat cluster and remain on patrol. UAV-03 has 0 ammo and is disengaged. USVs are sensor-only (domain_ok=false for intercept) and assigned to track the closest contacts to maintain observation."
}
```

## 调用 125（tick 1250）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8094.0, -4728.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1041.0, 3048.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15922.0, 16748.0]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat air contacts (strike-comms-02/03/04) are approaching the protected zone from bearing ~200-214. UAV-07 is closest to strike-comms-04 (dist 13km, closing) and assigned to intercept. UAV-08 is closest to strike-comms-03 (dist 14.6km, closing) and assigned to intercept. UAV-06 is closest to strike-comms-02 (dist 18.2km, receding but still a threat) and assigned to intercept. UAV-03 has 0 ammo and is disengaged. USVs are on patrol to maintain sensor coverage. UAV-01 and UAV-02 are on patrol as reserves."
}
```

## 调用 126（tick 1260）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.95, "deadline": 20},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.85, "deadline": 170},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 260},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.75, "deadline": 320},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1, "deadline": 100},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-02", "duration": 10}, "priority": 0.1, "deadline": 10}
  ],
  "reasoning": "USV-02 is the only unit with feasible intercept capability for the immediate threats (strike-comms-02 and strike-command-02) which are approaching the zone boundary. Assigning USV-02 to the closest threat (strike-comms-02, TTR 17.4t). UAV-07 is the closest armed interceptor to the high-threat strike-fuel-04 (dist 13.8km) and is assigned to intercept it early. UAV-08 and UAV-06 are assigned to the other approaching threats (strike-comms-03 and strike-comms-04) to spread coverage. UAV-01 is assigned to the distant strike-command-02. USV-01 (sensor only) tracks the comms-04 threat. UAV-03 (no ammo) and UAV-02 (distant) are held/disengaged to conserve resources or wait for repositioning."
}
```

## 调用 127（tick 1270）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.85, "deadline": 150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8194.0, -4789.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15909.0, 17108.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19069.0, 4103.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with prepare_intercept=true for strike-comms-04 (TTR 27.4t) and strike-command-02 (TTR 48.5t). It is assigned to the higher threat strike-comms-04. UAV-07 and UAV-08 are the closest armed interceptors to the remaining high-threat contacts (strike-comms-03 and strike-command-02 respectively) and are assigned to intercept them to establish a defensive screen. Other units hold position to conserve energy and maintain sensor coverage."
}
```

## 调用 128（tick 1280）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8244.0, -4819.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [991.0, 3162.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true. strike-command-03 has prepare_intercept=true (ttr=47.3s) and is the highest priority threat; uav-07 is the closest armed interceptor to it (dist 16km, closing 30m/t). strike-comms-04 is approaching (ttr=519s) and uav-08 is well-positioned to intercept it. strike-fuel-04 is receding but uav-06 is assigned to monitor/intercept if it turns. uav-03 has 0 ammo and is disengaged. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 129（tick 1290）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.5},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [15717.0, 17436.0], "commit_within_m": 9000}, "priority": 0.4},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19517.0, 4144.0], "commit_within_m": 9000}, "priority": 0.4},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1}
  ],
  "reasoning": "strike-command-04 has prepare_intercept=true and is the closest high-threat target to the zone (dist_zone=2538m, ttr=47.5t). UAV-07 is the closest armed interceptor to it (dist=22516m, feasible_eta=363t) and is assigned to intercept. strike-comms-04 is the highest threat (0.97) and closest to the zone (dist_zone=693m); UAV-08 is assigned to intercept it. strike-command-02 is approaching (ttr=238.5t) and is assigned to UAV-01. UAV-02 and UAV-06 are held in reserve to cover other axes. UAV-03 has no ammo and is disengaged. USVs continue tracking their assigned targets."
}
```

## 调用 130（tick 1300）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.85, "deadline": 150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.8},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19730, 4203], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154, 19998]}, "priority": 0.1}
  ],
  "reasoning": "strike-comms-04 is the highest threat (0.97) and closest to the zone (842m), with prepare_intercept=true for usv-02. uav-07 is the closest armed interceptor to this target (14km vs 19km for uav-06) and is assigned to intercept. strike-command-04 (0.95) is assigned to uav-08, which is also close and approaching. strike-command-03 (0.91) is assigned to uav-01. usv-02 and usv-01 continue tracking to maintain sensor ownership. uav-06 is held in reserve. uav-03 has 0 ammo and is disengaged."
}
```

## 调用 131（tick 1310）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.7}
  ],
  "reasoning": "No targets have can_intercept=true, but several have prepare_intercept=true or are approaching with high threat. UAV-07 is closest to strike-command-03 (approaching, TTR 325t) and should intercept. UAV-08 is closest to strike-command-04 (approaching, TTR 4641t but closer than others). UAV-06 is closest to strike-fuel-04 (approaching, TTR 1335t). UAV-01 is closest to strike-comms-04 (receding but closest). UAV-03 has 0 ammo, so disengage. USVs track to maintain observation."
}
```

## 调用 132（tick 1320）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 162},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 179},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 307},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 329},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.5}
  ],
  "reasoning": "No targets are currently in the intercept window (can_intercept=false) and none are flagged for early preparation (prepare_intercept=false). However, the threat cluster is approaching from the South/South-West (bearings ~180-220). UAV-07 is the closest armed asset to the threat axis (dist ~14.5km) and is assigned to the highest threat (strike-comms-04). UAV-08 is positioned to the North of the objective and is assigned to strike-command-02 to cover the northern approach. UAV-06 and UAV-01 are assigned to the remaining high-threat contacts (strike-fuel-04 and strike-command-03) to ensure all potential intruders are covered as they close. UAV-03 is out of ammo and disengaged. USVs continue tracking to maintain sensor fusion."
}
```

## 调用 133（tick 1330）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 170},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 230},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 180},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-03"}, "priority": 0.6},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.4},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [15656.0, 17631.0], "commit_within_m": 9000}, "priority": 0.4},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1}
  ],
  "reasoning": "Three high-threat strike-command intruders are approaching from the East (bearing ~100) with ETAs to the protected zone in 320-777m. UAV-07 is closest to the lead threat (strike-command-02) and is assigned to intercept it. UAV-06 is assigned to the second threat (strike-command-03) and UAV-08 to the third (strike-command-04) to spread fire discipline. Sensors (USV-01/02) continue tracking to maintain observation ownership. UAV-01 and UAV-02 are held in reserve at their current positions to react to any new threats or if the primary interceptors fail. UAV-03 is out of ammo and disengaged."
}
```

## 调用 134（tick 1340）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15589.0, 17800.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 4265.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-15395.0, 1849.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-375.0, 14952.0]}, "priority": 0.5}
  ],
  "reasoning": "All contacts are currently receding from the protected zone and are far outside the weapon envelope (range_ratio > 1.3). No targets have can_intercept or prepare_intercept set to true. Interceptors are holding position to conserve energy and maintain coverage. Sensor USVs are tracking the closest contacts to maintain continuous observation and update threat vectors."
}
```

## 调用 135（tick 1350）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8585.0, -4897.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1003.0, 3458.0]}, "priority": 0.5},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15479.0, 17967.0]}, "priority": 0.4}
  ],
  "reasoning": "No targets have can_intercept=true. strike-command-03 is the closest threat (dist_zone=465m) and is approaching; uav-07 is the closest armed interceptor to it, so issue intercept now to maneuver into position. strike-command-04 is also close (317m) and approaching; uav-08 is assigned to intercept it. strike-comms-04 (846m) is approaching and has prepare_intercept=true on usv-02; uav-01 is assigned to intercept it early. strike-command-02 (386m) is receding but still a high threat; uav-06 is assigned to intercept it to maintain coverage. uav-03 has 0 ammo and is returned. USVs are held in position for sensor coverage. uav-02 is held in patrol as it is far from the immediate threat cluster."
}
```

## 调用 136（tick 1360）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-03"}, "priority": 0.7, "deadline": 120}
  ],
  "reasoning": "No targets have can_intercept=true, but strike-command-02 (threat 0.97) is closest to the zone (379m) and approaching. UAV-07 is the closest armed interceptor to this threat (range_gap 6799m) and is assigned to intercept. UAV-08 is assigned to strike-command-04 (threat 0.94, 392m to zone) as the next highest priority. UAV-01 and UAV-02 are assigned to the remaining high-threat contacts (fuel-04 and comms-04) to maintain coverage. UAV-03 has 0 ammo and is disengaged. USVs are tasked to track their respective contacts to maintain sensor ownership."
}
```

## 调用 137（tick 1370）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15235.0, 18294.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 4265.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-15968.0, 1573.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-616.0, 15388.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are either receding or far outside weapon range (range_ratio > 1.2). UAVs are holding position to conserve energy and maintain coverage. USVs are tracking the closest contacts (strike-command-04 and strike-comms-04) to maintain sensor fusion and prepare for potential engagement if they turn or close in."
}
```

## 调用 138（tick 1380）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [15120.0, 18460.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 4265.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-16156.0, 1479.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-689.0, 15542.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8732.0, -4943.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1014.0, 3585.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are far (15-25km) and mostly receding or have long ETAs. UAV-03 is out of ammo and must disengage. Other UAVs are set to reserve to conserve ammo and react if threats close. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 139（tick 1390）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [15052.0, 18645.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 4265.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-16347.0, 1382.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-773.0, 15692.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8781.0, -4959.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1018.0, 3627.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (range_ratio > 1.2) and have prepare_intercept=false. The closest interceptor (uav-07) is still 7km away from weapon range, while the targets are 500-800m from the zone boundary. Immediate interception is infeasible. UAVs are set to reserve to auto-commit if targets enter the 9km threat radius. UAV-03 is disengaged due to 0 ammo. USVs continue patrol for sensor coverage."
}
```

## 调用 140（tick 1400）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14989.0, 18829.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19994.0, 4332.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-16492.0, 1235.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-880.0, 15825.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8833.0, -4970.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1017.0, 3671.0]}, "priority": 0.5}
  ],
  "reasoning": "All contacts are receding (negative closing speed) and far outside weapon range (range_ratio > 1.3). No unit has can_intercept or prepare_intercept true. The threats are moving away from the protected zone. Maintaining current positions to monitor for any change in trajectory or new threats."
}
```

## 调用 141（tick 1410）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.strike-command-04"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.strike-comms-04"}, "priority": 0.85, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14860.0, 18980.0]}, "priority": 0.5},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8885.0, -4980.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1017.0, 3714.0]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat intruders (command, fuel, comms) are approaching the protected zone from the East (bearing ~95-105). UAV-07, UAV-08, and UAV-06 are the closest armed assets to this axis and are assigned to intercept the respective targets to prevent them from crossing the boundary. Although `can_intercept` is currently false, the targets are within 16km and closing, so early maneuvering is required. UAV-01 and UAV-02 are held in reserve to the North. UAV-03 is out of ammo and returning. USVs are holding position for sensor coverage."
}
```

## 调用 142（tick 1420）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14739.0, 19139.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19942.0, 4764.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-16817.0, 976.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1077.0, 16111.0]}, "priority": 0.5}
  ],
  "reasoning": "All intruders are currently receding or stable at distances far exceeding weapon range (10km-25km). No targets have can_intercept=true or prepare_intercept=true. Interceptors are holding position to conserve energy and maintain coverage. Sensors are tracking the highest threat contacts to maintain continuous observation for when they re-approach."
}
```

## 调用 143（tick 1430）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14598.0, 19285.0]}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19938.0, 4988.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-16931.0, 813.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1194.0, 16240.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8991.0, -4995.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1022.0, 3797.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are currently receding from the protected zone (negative closing speed) and are far outside the weapon range of all interceptors (range_ratio > 2.0). No unit has can_intercept=true or prepare_intercept=true. The targets are moving away, so immediate interception is infeasible and would waste maneuvering. Interceptors are holding position to conserve energy and maintain situational awareness. UAV-03 is disengaging as it has 0 ammo. USVs are holding to maintain sensor coverage."
}
```

## 调用 144（tick 1440）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14468.0, 19430.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19877.0, 5200.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17067.0, 664.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-1295.0, 16381.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8}
  ],
  "reasoning": "All targets are far outside weapon range (range_ratio > 2.0) and have prepare_intercept=false. UAVs are positioned as reserves to commit automatically if threats approach the objective. USVs are tracking the closest contacts to maintain sensor coverage and update threat classification."
}
```

## 调用 145（tick 1450）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14427.0, 19622.0]}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19919.0, 5419.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-17213.0, 514.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1399.0, 16520.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9096.0, -5009.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1023.0, 3880.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All contacts are far (16-25km) and mostly receding or stable. UAV-03 has 0 ammo and is disengaged. Other units hold position to conserve energy and maintain sensor coverage until threats enter the intercept window."
}
```

## 调用 146（tick 1460）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14287.0, 19765.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19876.0, 5637.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17351.0, 361.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-1514.0, 16650.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9145.0, -5012.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1024.0, 3920.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are far (16-25km) and mostly receding or stable. UAV-03 is out of ammo and must disengage. Other armed UAVs are held in reserve to conserve ammo and react if threats close in. USVs continue patrolling to maintain sensor coverage."
}
```

## 调用 147（tick 1470）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14236.0, 19953.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19909.0, 5840.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17494.0, 205.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-1625.0, 16784.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9192.0, -5022.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1027.0, 3960.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (16-25km) and currently receding or moving slowly. No unit has can_intercept or prepare_intercept true. UAV-03 has 0 ammo and is disengaged. Other UAVs are set to reserve to conserve ammo and react if threats approach the zone. USVs are patrolling to maintain sensor coverage."
}
```

## 调用 148（tick 1480）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19896.0, 6062.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17570.0, 12.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-1726.0, 16926.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9242.0, -5029.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1020.0, 4000.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (range_ratio > 2.0) and currently receding or moving slowly. No unit has can_intercept or prepare_intercept true. UAV-03 has 0 ammo and is disengaged. Other UAVs are set to reserve to conserve ammo and react if threats approach the objective. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 149（tick 1490）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6237.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17619.0, -192.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-1825.0, 17072.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9292.0, -5038.0]}, "priority": 0.6},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1023.0, 4039.0]}, "priority": 0.6}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All contacts are far (10km+) and mostly receding or stable. UAV-03 has 0 ammo and is disengaged. Other armed UAVs are held in reserve to conserve ammo and react if threats approach the zone. USVs maintain patrol positions for continuous sensor coverage."
}
```

## 调用 150（tick 1500）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.strike-command-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1941.0, 17203.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9342.0, -5043.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1023.0, 4079.0]}, "priority": 0.5}
  ],
  "reasoning": "Two high-threat intruders (strike-command-04 and strike-fuel-04) are approaching the protected zone from the East (bearing ~90-110). UAV-07 and UAV-06 are the closest armed interceptors to the threat axis and have the shortest feasible ETAs (211t and 295t respectively). Although can_intercept is currently false, the targets are closing and will enter the intercept window soon; issuing intercept now allows the UAVs to maneuver into position. Other UAVs are too far or out of position to engage effectively before the targets reach the zone. UAV-03 is out of ammo and is disengaged. USVs are holding position to maintain sensor coverage."
}
```

## 调用 151（tick 1510）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.8},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17794.0, -570.0], "commit_within_m": 9000}, "priority": 0.7},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2034.0, 17351.0], "commit_within_m": 9000}, "priority": 0.7},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_005", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6469.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1}
  ],
  "reasoning": "All three intruders are far outside weapon range (10-25km) and currently receding or stable. No interceptor has can_intercept or prepare_intercept true. USVs are tracking to maintain sensor lock. UAVs are holding in reserve positions to conserve ammo and wait for the threats to approach the protected zone boundary."
}
```

## 调用 152（tick 1520）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6469.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17902.0, -749.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2154.0, 17479.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9441.0, -5049.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1022.0, 4161.0]}, "priority": 0.5}
  ],
  "reasoning": "All contacts are far outside weapon range (10-25km) and have no prepare_intercept flag. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are set to reserve to conserve ammo and react if threats close. USVs continue patrol to maintain sensor coverage."
}
```

## 调用 153（tick 1530）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19986.0, 6556.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18020.0, -923.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2259.0, 17618.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9491.0, -5056.0]}, "priority": 0.3},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1026.0, 4203.0]}, "priority": 0.3}
  ],
  "reasoning": "All three intruders are far outside weapon range (10-25km) and currently receding or moving slowly. No unit has can_intercept or prepare_intercept true. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are held in reserve to conserve ammunition and maintain coverage, while USVs continue sensor tracking."
}
```

## 调用 154（tick 1540）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6581.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18037.0, -1133.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2364.0, 17761.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9541.0, -5065.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1031.0, 4244.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All targets are far (10km+) and mostly receding or stable. UAV-03 has 0 ammo, so it disengages. Other armed UAVs hold reserve positions to react if threats close in. USVs maintain sensor coverage."
}
```

## 调用 155（tick 1550）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6581.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18094.0, -1335.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2469.0, 17904.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9593.0, -5070.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1035.0, 4287.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (10-25km) and have no prepare_intercept flags. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are set to reserve with auto-commit triggers to react if threats close in. USVs maintain sensor coverage."
}
```

## 调用 156（tick 1560）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6581.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18162.0, -1531.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2574.0, 18043.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9644.0, -5077.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1036.0, 4329.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (range_ratio > 2.0) and currently receding or moving slowly. No unit has can_intercept or prepare_intercept true. UAV-03 is out of ammo and must disengage. Other armed UAVs are held in reserve to conserve ammo and position for when threats approach the protected zone. USVs continue patrol to maintain sensor coverage."
}
```

## 调用 157（tick 1570）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19997.0, 6647.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18193.0, -1739.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2688.0, 18176.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9694.0, -5083.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1040.0, 4371.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far from the protected zone (dist_zone > 300m) and currently receding or stable. No interceptor has can_intercept=true or prepare_intercept=true. UAV-03 has 0 ammo and is disengaged. Other UAVs are held in reserve to conserve ammo and react if the intruders turn and approach. USVs continue patrolling to maintain sensor coverage."
}
```

## 调用 158（tick 1580）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6647.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18219.0, -1948.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2775.0, 18327.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9745.0, -5094.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1043.0, 4415.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (17-25km) with ETAs > 400 ticks. No unit has can_intercept or prepare_intercept true. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are set to reserve to conserve ammo and react if threats close. USVs maintain sensor coverage."
}
```

## 调用 159（tick 1590）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18279.0, -2151.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2874.0, 18472.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9792.0, -5103.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1043.0, 4457.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are currently receding or far outside the intercept window (prepare_intercept=false, can_intercept=false, feasible=false). The closest threat (strike-command-04) is 400m from the zone but moving away at 17m/t. No immediate engagement is required. UAVs are held in reserve positions to react if the intruders turn back or new threats appear. USVs maintain sensor coverage."
}
```

## 调用 160（tick 1600）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18338.0, -2351.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2978.0, 18612.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9840.0, -5111.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1047.0, 4499.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (11-25km) and currently receding or stable. No unit has can_intercept or prepare_intercept true. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are held in reserve to conserve ammo and react if the intruders turn and approach the protected zone. USVs continue sensor coverage."
}
```

## 调用 161（tick 1610）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.strike-command-04"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9891.0, -5118.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1048.0, 4542.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-03", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-08", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "Three high-threat intruders are approaching the protected zone from the East/South-East (bearings ~80-110 deg). UAV-07 is closest to the highest threat (strike-command-04) and is assigned to intercept it. UAV-06 is assigned to strike-fuel-04, and UAV-01 to strike-comms-04 to spread the interceptors across distinct targets. Although `can_intercept` is currently false, the targets are closing and will enter the weapon envelope soon; early maneuvering is required to meet them before they cross the boundary. USVs are held in position to maintain sensor coverage. Other UAVs are held as reserves."
}
```

## 调用 162（tick 1620）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-18569.0, -2695.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-3180.0, 18898.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (12km-25km) and mostly receding or stable. USVs are maintaining tracking on the closest contacts to preserve sensor ownership. UAVs are holding position to conserve energy and wait for threats to enter the intercept window. UAV-03 is disengaging as it has 0 ammo."
}
```

## 调用 163（tick 1630）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18621.0, -2897.0], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3275.0, 19044.0], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9997.0, -5124.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1053.0, 4627.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "All three intruders are far outside weapon range (10-25km) and have no prepare_intercept flags. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are set to reserve positions to react if threats close in. USVs continue patrolling to maintain sensor coverage."
}
```

## 调用 164（tick 1640）

```
{
  "goal_commands": [
    {"task_id": "ambush_fuel_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "standoff_m": 500}, "priority": 0.95, "deadline": 300},
    {"task_id": "ambush_comms_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.9, "deadline": 300},
    {"task_id": "ambush_cmd_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "standoff_m": 500}, "priority": 0.85, "deadline": 300},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.7, "deadline": 600},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3387.0, 19182.0], "commit_within_m": 9000}, "priority": 0.7, "deadline": 600},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 300}
  ],
  "reasoning": "All three intruders are far from the protected zone (dist_zone ~500-850m) and currently receding or stable, with no can_intercept or prepare_intercept flags. The UAVs are positioned far away (17-25km). To conserve ammunition and ensure engagement at the optimal moment, I am assigning the three armed UAVs (uav-07, uav-06, uav-01) to 'ambush' the lead intercept points of the three distinct threats. This positions them to fire as the targets approach the zone boundary. uav-02 and uav-08 are held as reserves. uav-03 is disengaged due to 0 ammo. USVs continue tracking for sensor fusion."
}
```

## 调用 165（tick 1650）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.98, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.93, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3461.0, 19343.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10096.0, -5140.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1061.0, 4714.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (18-25km) and receding or slowly approaching. UAV-03 has 0 ammo and is disengaged. UAV-01, 06, 07 are assigned to intercept the three distinct threats (command, comms, fuel) respectively to maintain coverage and prepare for engagement as they close. UAV-02 and 08 are held in reserve. USVs are on patrol for sensor coverage."
}
```

## 调用 166（tick 1660）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1064.0, 4756.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10144.0, -5149.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-03", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-08", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (17-25km) and receding or stable. UAV-07, UAV-06, and UAV-01 are assigned to intercept the three distinct threats to maintain forward positioning and update tracking, despite current infeasibility, to prepare for potential closure. UAV-03 is out of ammo and held. Other units held to conserve energy/position."
}
```

## 调用 167（tick 1670）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_cmd_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3618.0, 19660.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "track_fuel_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.5},
    {"task_id": "track_cmd_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat intruders (fuel, command, comms) are approaching the protected zone from the east/southeast. UAV-07, UAV-06, and UAV-01 are the closest armed interceptors to their respective targets and are assigned to intercept them to prevent zone entry. UAV-02 and UAV-08 are held in reserve to react to any new threats or if the primary interceptors fail. UAV-03 is out of ammo and disengaging. USVs are tracking to maintain sensor coverage."
}
```

## 调用 168（tick 1680）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-18851.0, -3899.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-3698.0, 19815.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (10km+ gap) and have no prepare_intercept flag. UAVs are positioned far away and cannot reach the intercept window before the targets (feasible=false). USVs are the only sensors close enough to track the threats. Maintaining tracking on the USVs is critical for early warning. UAVs hold position to conserve energy and wait for the threats to close or for a new wave to appear."
}
```

## 调用 169（tick 1690）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-18925.0, -4093.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3801.0, 19957.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are far (18-25km) and mostly receding or moving slowly. UAV-03 has 0 ammo and is disengaged. Other UAVs are set to reserve to conserve ammo and react if threats close. USVs are tracking to maintain sensor coverage."
}
```

## 调用 170（tick 1700）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19003.0, -4288.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10342.0, -5162.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1064.0, 4928.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are currently receding from the protected zone (negative closing speed) and are far outside weapon range (range_ratio > 2.5). No unit has can_intercept or prepare_intercept true. UAV-03 is out of ammo and is disengaged. The remaining armed UAVs are held in reserve to conserve ammunition and maintain coverage, while USVs continue to track the contacts to update their trajectories."
}
```

## 调用 171（tick 1710）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19127.0, -4461.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10392.0, -5172.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1069.0, 4971.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (12-21km) and have no prepare_intercept flags. UAVs are positioned as reserves to react if threats approach the zone. USVs continue sensor coverage."
}
```

## 调用 172（tick 1720）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19199.0, -4659.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10441.0, -5176.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1073.0, 5013.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (18-25km) and currently receding or stable. No unit has can_intercept or prepare_intercept true. UAV-03 has 0 ammo and is disengaged. Armed UAVs are held in reserve to conserve ammo and maintain coverage, while USVs continue sensor tracking."
}
```

## 调用 173（tick 1730）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19245.0, -4861.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10490.0, -5183.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1081.0, 5054.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders (strike-command-04, strike-fuel-04, strike-comms-04) are currently receding or at a distance where no interceptor has can_intercept=true or prepare_intercept=true. The closest approach is ~5km, but they are moving away or closing very slowly. To conserve ammunition and avoid premature engagement, all armed UAVs are set to 'reserve' with a 9km commit trigger. UAV-03 is disengaged due to 0 ammo. USVs are patrolling to maintain sensor coverage."
}
```

## 调用 174（tick 1740）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19350.0, -5044.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10540.0, -5191.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1086.0, 5096.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (18-25km) and mostly receding or stable. Interceptors are holding position to conserve energy and maintain coverage until threats enter the intercept window."
}
```

## 调用 175（tick 1750）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.5},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19511.0, -5179.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10592.0, -5199.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1090.0, 5139.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (12-25km) and currently receding or stable with no prepare_intercept flags. Interceptors are positioned as reserves to react if the threat vector changes or they approach the zone. UAV-03 is disengaged due to 0 ammo. USVs maintain sensor coverage."
}
```

## 调用 176（tick 1760）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19618.0, -5360.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10645.0, -5205.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1093.0, 5181.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are currently receding or stable at distances >19km, well outside weapon range (8km) and with no prepare_intercept flags. The closest threat (strike-command-04) is 5.8km from usv-02 but receding from the zone. Interceptors are positioned as reserves to react if the wave turns or new threats appear. UAV-03 is disengaged due to 0 ammo. USVs maintain sensor coverage."
}
```

## 调用 177（tick 1770）

```
{
  "goal_commands": [
    {"task_id": "barrier_uav01_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-01", "axis_deg": 200, "radius_m": 5000}, "priority": 0.9},
    {"task_id": "barrier_uav02_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-02", "axis_deg": 217, "radius_m": 5000}, "priority": 0.9},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154, 19998]}, "priority": 0.5},
    {"task_id": "barrier_uav06_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-06", "axis_deg": 111, "radius_m": 5000}, "priority": 0.9},
    {"task_id": "barrier_uav07_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-07", "axis_deg": 74, "radius_m": 5000}, "priority": 0.9},
    {"task_id": "barrier_uav08_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-08", "axis_deg": 171, "radius_m": 5000}, "priority": 0.9},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10697, -5213]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1099, 5223]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far from the protected zone (450-800m away) and have long ETAs (500+ ticks). No unit has can_intercept or prepare_intercept true. UAV-03 has 0 ammo and is disengaged. The remaining armed UAVs are positioned to form a barrier screen on the threat axes (200, 217, 111, 74, 171 degrees) to intercept threats before they reach the zone. USVs are patrolling to maintain sensor coverage."
}
```

## 调用 178（tick 1780）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19841.0, -5709.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10750.0, -5222.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1099.0, 5266.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are far outside weapon range (12-25km) with no prepare_intercept flags. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are held in reserve to conserve ammo and react if threats close. USVs maintain sensor coverage."
}
```

## 调用 179（tick 1790）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14227.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6154.0, 19998.0]}, "priority": 0.2},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 6767.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19874.0, -5914.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3834.0, 19998.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10803.0, -5230.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1102.0, 5308.0]}, "priority": 0.5}
  ],
  "reasoning": "All contacts are far outside weapon range (12-25km) and mostly receding or stable. No can_intercept or prepare_intercept flags are active. UAV-03 is out of ammo and disengaged. Remaining armed UAVs are held in reserve to conserve ammo and react if threats approach the protected zone. USVs maintain sensor coverage."
}
```

