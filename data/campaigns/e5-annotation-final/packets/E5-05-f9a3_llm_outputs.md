# 案例 E5-05-f9a3 — LLM 规划器原始输出

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
  "reasoning": "No hostile contacts detected in the current situation report. All units are holding their patrol positions to maintain sensor coverage and readiness for incoming threats."
}
```

## 调用 1（tick 10）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4132.0, 1621.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6036.0, 1649.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8003.0, 1707.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3902.0, -117.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6125.0, -38.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [7874.0, 84.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3992.0, -1692.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5975.0, -1365.0]}, "priority": 0.3},
    {"task_id": "patrol_uav_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8072.0, -1344.0]}, "priority": 0.3},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1518.0, -511.0]}, "priority": 0.3},
    {"task_id": "patrol_usv_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2609.0, -1492.0]}, "priority": 0.3},
    {"task_id": "patrol_usv_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1408.0, -2395.0]}, "priority": 0.3}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (15km-30km) and stable. Maintaining current positions to conserve ammunition and wait for threats to enter engagement range."
}
```

## 调用 2（tick 20）

```
{
  "goal_commands": [
    {"task_id": "ambush_fuel_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-fuel-01", "standoff_m": 1000}, "priority": 0.9, "deadline": 100},
    {"task_id": "ambush_comms_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-comms-01", "standoff_m": 1000}, "priority": 0.8, "deadline": 150},
    {"task_id": "ambush_command_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.strike-command-01", "standoff_m": 1000}, "priority": 0.7, "deadline": 200},
    {"task_id": "barrier_boat_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.usv-02", "axis_deg": 105, "radius_m": 5000}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4260, 1770]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6158, 1805]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3712, -229]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6153, -240]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3976, -1913]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5914, -1229]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1566, -542]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_usv_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1402, -2378]}, "priority": 0.5, "deadline": 300}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. Air targets are far (14-25km) with long ETAs, so I assign the closest UAVs (09, 03, 06) to ambush positions to save ammo and maneuver time. Surface boats are closer (5-7km) but USVs are too slow to intercept before they reach the zone (feasible=false for most). I position USV-02 as a barrier on the threat axis to monitor and potentially engage if they slow down, while keeping other USVs in patrol to maintain sensor
```

## 调用 3（tick 30）

```
{
  "goal_commands": [
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4400.0, 1907.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6274.0, 1964.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7988.0, 2216.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3518.0, -334.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6182.0, -441.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [7387.0, 147.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [4003.0, -2136.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5854.0, -1091.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8340.0, -1031.0]}, "priority": 0.5},
    {"task_id": "patrol_010", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1620.0, -579.0]}, "priority": 0.5},
    {"task_id": "patrol_011", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2580.0, -1430.0]}, "priority": 0.5},
    {"task_id": "patrol_012", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1383.0, -2357.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (dist_zone > 7km) and closing slowly. Interceptors and sensors hold position to conserve energy and maintain coverage until threats enter the engagement window."
}
```

## 调用 4（tick 40）

```
{
  "goal_commands": [
    {"task_id": "ambush_fuel_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-fuel-01", "standoff_m": 500}, "priority": 0.9, "deadline": 120},
    {"task_id": "ambush_comms_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-comms-01", "standoff_m": 500}, "priority": 0.8, "deadline": 120},
    {"task_id": "ambush_cmd_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-command-01", "standoff_m": 500}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1676.0, -617.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2564.0, -1389.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1361.0, -2332.0]}, "priority": 0.5},
    {"task_id": "hold_uav01_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-01", "duration": 10}, "priority": 0.3},
    {"task_id": "hold_uav04_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-04", "duration": 10}, "priority": 0.3},
    {"task_id": "hold_uav05_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-05", "duration": 10}, "priority": 0.3},
    {"task_id": "hold_uav06_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-06", "duration": 10}, "priority": 0.3},
    {"task_id": "hold_uav07_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-07", "duration": 10}, "priority": 0.3},
    {"task_id": "hold_uav08_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-08", "duration": 10}, "priority": 0.3}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. Air targets are far (14-24km) with long ETAs. Surface boats are closer but also far from the zone (7-9km) and moving slowly. Assigning closest UAVs to ambush the highest threat air targets (fuel, comms, command) to position for future engagement. Holding other UAVs to conserve energy and maintain coverage. USVs continue patrol to maintain sensor coverage on surface threats."
}
```

## 调用 5（tick 50）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1732.0, -656.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2547.0, -1349.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1339.0, -2305.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4639.0, 2219.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3121.0, -467.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6162.0, -845.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6896.0, 152.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3915.0, -2540.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5738.0, -818.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. The three air targets (strike-fuel-01, strike-comms-01, strike-command-01) are the highest threat (0.47-0.48) and are approaching. I am maintaining the intercept assignments from the previous tick for UAV-09, UAV-03, and UAV-02 to keep them maneuvering toward the expected intercept points. The surface boats are slower and further out, and the USVs are holding position to maintain sensor coverage. The remaining UAVs are holding position to conserve energy and maintain a defensive screen."
}
```

## 调用 6（tick 60）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4730.0, 2392.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6638.0, 2430.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2929.0, -553.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6180.0, -1048.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6650.0, 158.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3966.0, -2755.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5681.0, -679.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1786.0, -695.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1316.0, -2277.0]}, "priority": 0.5}
  ],
  "reasoning": "Maintaining current intercept assignments for the three air threats (strike-fuel-01, strike-comms-01, strike-command-01) as they are the primary high-threat contacts with feasible interception windows. No unit has can_intercept=true or prepare_intercept=true yet, so no new intercepts are triggered. Surface threats (boats) are far from the protected zone and have low closing speeds; USVs are holding position to maintain sensor coverage. All other UAVs are patrolling to maintain situational awareness and readiness for new threats."
}
```

## 调用 7（tick 70）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_command_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4827.0, 2565.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6756.0, 2589.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2729.0, -642.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6183.0, -1251.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6404.0, 160.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3960.0, -2974.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5626.0, -540.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1842.0, -734.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1293.0, -2249.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. The air threats (strike-fuel, strike-comms, strike-command) are far away (dist_zone > 20km) with long ETAs. The surface threats (boats) are closer but moving slowly and are currently outside the effective engagement window for the USVs (feasible=false for most, or long ETAs). I am maintaining the current intercept assignments for the air threats to keep them in the kill box as they approach, and tracking the command boat. The other UAVs are holding position to conserve energy and maintain sensor coverage until the threats enter the intercept window."
}
```

## 调用 8（tick 80）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "barrier_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.usv-01", "axis_deg": 109, "radius_m": 2000}, "priority": 0.7, "deadline": 120},
    {"task_id": "barrier_002", "goal_type": "barrier", "parameters": {"unit_id": "defender.usv-02", "axis_deg": 106, "radius_m": 2000}, "priority": 0.7, "deadline": 120},
    {"task_id": "barrier_003", "goal_type": "barrier", "parameters": {"unit_id": "defender.usv-03", "axis_deg": 91, "radius_m": 2000}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4915.0, 2742.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6887.0, 2739.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2534.0, -707.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6186.0, -1457.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6158.0, 170.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3832.0, -3154.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5572.0, -403.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. The air threats (strike-fuel-01, strike-comms-01, strike-command-01) are far away (dist_zone > 20km) with long ETAs. The surface threats (boat-01, boat-02, boat-03) are closer (dist_zone ~7-9km) but moving slowly (closing ~5-15 m/t) and are outside the USV sensor range (
```

## 调用 9（tick 90）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1954.0, -810.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2472.0, -1181.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1246.0, -2193.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4980.0, 2929.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7019.0, 2887.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2322.0, -670.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6198.0, -1662.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5911.0, 176.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3642.0, -3248.0]}, "priority": 0.5},
    {"task_id": "patrol_010", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5519.0, -264.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. The air threats (strike-fuel-01, strike-comms-01, strike-command-01) are far from the protected zone (dist_zone > 19km) and have long ETAs. The surface threats (boat-01, boat-02, boat-03) are closer but also have long ETAs (100-200+ ticks) and are currently outside the effective intercept window for the USVs (feasible=false for most). Maintaining the current intercept assignments for the closest air threats (uav-09 on fuel-01, uav-03 on comms-01) allows them to close the distance and prepare for engagement. Other units hold position to conserve energy and maintain sensor coverage."
}
```

## 调用 10（tick 100）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5039.0, 3117.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7143.0, 3042.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2115.0, -688.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6211.0, -1867.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5665.0, 180.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3475.0, -3195.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5464.0, -128.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2011.0, -847.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2454.0, -1139.0]}, "priority": 0.5},
    {"task_id": "patrol_010", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1223.0, -2164.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 and UAV-03 are assigned to intercept the two highest-threat air targets (strike-fuel-01 and strike-comms-01) which have prepare_intercept=true and are approaching the protected zone. The remaining UAVs and USVs are held in patrol positions to maintain sensor coverage and readiness for potential new threats or to support the interceptors if needed. The surface threats (boats) are currently outside the effective engagement range of the USVs and are being monitored."
}
```

## 调用 11（tick 110）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-08.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 160},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5110.0, 3302.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7254.0, 3207.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1898.0, -714.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6210.0, -2075.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5420.0, 185.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3319.0, -3030.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5409.0, 7.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2067.0, -885.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2434.0, -1097.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1200.0, -2136.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 and UAV-03 are assigned to intercept the two air targets (strike-fuel-01 and strike-comms-01) which have prepare_intercept=true and are the closest threats to the protected zone. The remaining UAVs and USVs are holding their patrol positions to maintain sensor coverage and readiness for the surface threats (boats) and the distant command aircraft, which are currently outside the immediate intercept window."
}
```

## 调用 12（tick 120）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "track_boat_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_boat_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.pier.intruder.boat-03"}, "priority": 0.75, "deadline": 120},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5169.0, 3491.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7353.0, 3380.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1679.0, -690.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6204.0, -2283.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5176.0, 197.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3146.0, -2881.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5353.0, 141.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the closest high-threat air target to the zone. UAV-03 is assigned to intercept strike-comms-01 as it has prepare_intercept=true and is the closest high-threat air target to the zone. USVs are assigned to track the three surface
```

## 调用 13（tick 130）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 150},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5215.0, 3684.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7455.0, 3549.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8057.0, 4755.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1475.0, -603.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4931.0, 209.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2988.0, -2718.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5299.0, 275.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2391.0, -1014.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1154.0, -2080.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 and UAV-05 are assigned to intercept the high-threat fuel intruder (strike-fuel-01) which has prepare_intercept=true and is closing rapidly. USV-01 is assigned to intercept the high-threat surface boat-01 which also has prepare_intercept=true. Other units hold position to maintain sensor coverage and reserve readiness."
}
```

## 调用 14（tick 140）

```
{
  "goal_commands": [
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.facility.pier.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 160},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 170},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5270.0, 3874.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7512.0, 3736.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8080.0, 5011.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1267.0, -609.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2768.0, -2665.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5240.0, 412.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2236.0, -1001.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2371.0, -972.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1132.0, -2051.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-comms-01 as it has prepare_intercept=true and the shortest feasible ETA (15t). UAV-05 is assigned to intercept strike-fuel-01 which also has prepare_intercept=true and a short feasible ETA (60t). UAV-06 continues tracking boat-01 as it is the closest surface threat and already engaged. Other units hold position to maintain sensor coverage and reserve ammunition for potential new threats or if the current intercepts fail."
}
```

## 调用 15（tick 150）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 160},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 160},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 160},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 160},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8105.0, 5264.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1050.0, -630.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4442.0, 220.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2771.0, -2461.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2292.0, -1039.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2352.0, -929.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1111.0, -2022.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is at the edge of weapon range for strike-comms-01 (range_gap=45m, prepare=true) and is the closest interceptor to this high-threat air target, so it is assigned to intercept immediately. UAV-02 is also assigned to strike-comms-01 as a secondary interceptor to ensure engagement if UAV-09 fails or is delayed, given the target's high threat level and proximity to the intercept window. UAV-05 is assigned to strike-fuel-01, which has prepare=true and is approaching the intercept window. UAV-08 is assigned to boat-01, the closest surface threat with prepare=true, to prevent it from entering the protected zone. UAV-01 is assigned to boat-02, the next closest surface threat. Other UAVs
```

## 调用 16（tick 160）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 180},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 180},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.7, "deadline": 180},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.7, "deadline": 180},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03"}, "priority": 0.7, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5351.0, 4265.0]}, "priority": 0.5, "deadline": 180},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [839.0, -633.0]}, "priority": 0.5, "deadline": 180},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4197.0, 228.0]}, "priority": 0.5, "deadline": 180},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2601.0, -2316.0]}, "priority": 0.5, "deadline": 180},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5123.0, 681.0]}, "priority": 0.5, "deadline": 180}
  ],
  "reasoning": "UAV-09 has can_intercept=true for strike-comms-01, so it engages immediately. UAV-02 and UAV-03 have prepare_intercept=true for strike-comms-01 (range_gap < 1.5km, TTR < 30t), so they maneuver to intercept now to ensure coverage if UAV-09 misses or is delayed. UAV-05 has prepare_intercept=true for strike-fuel-01 (range_gap 1.5km, TTR 38t), so it intercepts that target. The surface boats (boat-01/02/03) are high threat (0
```

## 调用 17（tick 170）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 170},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 170},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 170},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 170},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 170},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 170},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [661.0, -710.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2438.0, -2374.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5065.0, 815.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2406.0, -1114.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2313.0, -845.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1069.0, -1964.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 has can_intercept=true for strike-comms-01 (dist 6799m, inside 8000m range) and is assigned to engage. UAV-02 and UAV-03 have prepare_intercept=true for strike-comms-01 (range_gap < 1000m, ttr < 30t) and are assigned to intercept to ensure coverage. UAV-05 has prepare_intercept=true for strike-fuel-01 (range_gap 1030m, ttr 18.9t) and is assigned to intercept. UAV-01 is assigned to intercept strike-comms-01 as a secondary layer. UAV-06 is assigned to intercept
```

## 调用 18（tick 180）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 180},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 180},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8184.0, 6030.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [550.0, -532.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2317.0, -2183.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5011.0, 950.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2463.0, -1152.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2293.0, -802.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1047.0, -1934.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 has can_intercept=true for both air threats; assigned to strike-fuel-01 (higher threat 0.63). UAV-02 and UAV-01 assigned to strike-comms-01 (prepare_intercept=true, high closing speed). UAV-05 assigned to strike-fuel-01 (prepare_intercept=true) to provide backup/coverage. UAV-06 continues tracking boat-01 (prepare_intercept=true, high threat 0.84). Remaining units hold position to conserve ammo and maintain sensor coverage."
}
```

## 调用 19（tick 190）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5444.0, 4857.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8200.0, 6284.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [424.0, -565.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4955.0, 1085.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2276.0, -759.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1025.0, -1905.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "USV-01 has can_intercept=true for boat-01 (closest surface threat, dist 2960m), so it engages immediately. UAV-02 and UAV-05 have prepare_intercept=true for strike-comms-01 and strike-fuel-01 respectively (range gaps 5m and 155m, TTR < 4 ticks), so they are assigned to intercept these high-threat air targets now to prevent them from reaching the protected zone. UAV-06 and UAV-07 are assigned to track boat-02 and boat-03 to maintain sensor coverage on the remaining surface threats. Other units hold position to conserve ammunition and maintain situational awareness."
}
```

## 调用 20（tick 200）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 50},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-08.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 50},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 50},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5446.0, 5058.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8237.0, 6540.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [576.0, -436.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3216.0, 258.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1986.0, -1884.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1003.0, -1875.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 and UAV-05 are in weapon range of high-threat air targets (strike-comms-01 and strike-fuel-01) and must engage immediately. USV-01 is in range of boat-01 (high threat, close to zone) and must engage. USV-02 is assigned to boat-02 (prepare_intercept=true) to prevent it from entering the zone. UAV-08 is assigned to intercept strike-comms-01 as a secondary threat since it has prepare_intercept=true. Remaining units hold position to conserve ammo and maintain coverage."
}
```

## 调用 21（tick 210）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5421.0, 5256.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8253.0, 6796.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [574.0, -221.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2623.0, -1246.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2256.0, -677.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [981.0, -1845.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 and UAV-05 have can_intercept=true for the high-threat air targets (strike-comms-01 and strike-fuel-01 respectively) and are assigned to engage. UAV-06 and UAV-07 are assigned to the surface threats (boat-01 and boat-02) which are closer to the protected zone and have high threat levels. UAV-08 is assigned to track/intercept strike-fuel-01 as a secondary option if UAV-05 fails. Other units are held in patrol positions to maintain coverage and readiness for new threats."
}
```

## 调用 22（tick 220）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 165},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 174},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 394},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 316},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 247},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 298},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 286},
    {"task_id": "intercept_008", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-07.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.65, "deadline": 238},
    {"task_id": "intercept_009", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.6, "deadline": 326},
    {"task_id": "intercept_010", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.5, "deadline": 516},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1}
  ],
  "reasoning": "UAV-02 and UAV-05 are in immediate intercept range (can_intercept=true) for the two highest-threat air targets (strike-comms and strike-fuel) and are assigned to engage. USV-02 and USV-01 are assigned to the closest surface threat (boat-01) which is approaching the zone; USV-02 is closer and has ammo, while USV-01 is already tracking
```

## 调用 23（tick 230）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8305.0, 7305.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5936.0, -4349.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_008", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60}
  ],
  "reasoning": "UAV-02 and UAV-08 have can_intercept=true for strike-comms-01 (observed by UAV-06, but UAV-02/08 are in range and can engage). UAV-01 and UAV-06 are also assigned to strike-comms-01 as it is the highest threat (0.64) and closest to the zone. UAV-04 and UAV-07 are assigned to strike
```

## 调用 24（tick 240）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8329.0, 7560.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5872.0, -4545.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [2766.0, -1337.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5263.0, 5830.0]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [675.0, 409.0]}, "priority": 0.4},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1799.0, -1740.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-02 intercepts strike-comms-01 (can_intercept=true). UAV-06 and USV-02 engage boat-01 (prepare_intercept=true, high threat). UAV-08 engages boat-02 (prepare_intercept=true). USV-03 engages boat-03 (prepare_intercept=true). UAV-03, UAV-05, and USV-01 are disengaged due to 0 ammo. Remaining UAVs hold patrol to conserve ammo and maintain sensor coverage."
}
```

## 调用 25（tick 250）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5290.0, 6034.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [495.0, 506.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8360.0, 7811.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5860.0, -4754.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-08 and UAV-06 assigned to intercept boat-01 (highest threat, prepare_intercept=true, closest to zone). UAV-02 assigned to intercept boat-05 (prepare_intercept=true). UAV-07 assigned to intercept boat-02 (prepare_intercept=true). USVs tracking their respective contacts for sensor fusion. UAV-01 and UAV-04 patrolling to maintain coverage. UAV-03 and UAV-05 disengaging due to 0 ammo."
}
```

## 调用 26（tick 260）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.pier.intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.pier.intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5308.0, 6238.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8272.0, 4863.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8402.0, 8055.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5817.0, -4958.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1490.0, -1455.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "boat-01 and boat-02 are the highest threats (0.85/0.84) and are approaching the protected zone. boat-01 is observed by usv-02 (can_intercept=true) and uav-06 (prepare_intercept=true); boat-02 is observed by uav-08 and uav-04 (both prepare_intercept=true). Assigning usv-02 to boat-01 and uav-06/uav-08/uav-04 to boat-01/boat-02 respectively to engage before they cross the boundary. boat-03 is further out (dist_zone=7300m) and observed by facility.pier; usv
```

## 调用 27（tick 270）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-01.intruder.boat-05"}, "priority": 0.70, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5328.0, 6442.0]}, "priority": 0.50},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8272.0, 4863.0]}, "priority": 0.50},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8448.0, 8297.0]}, "priority": 0.30},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5756.0, -5161.0]}, "priority": 0.30},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4858.0, 1356.0]}, "priority": 0.50},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2927.0, -1443.0]}, "priority": 0.40},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [858.0, -1696.0]}, "priority": 0.40}
  ],
  "reasoning": "USV-02 has can_intercept=true for boat-01 (highest threat 0.86, closest to zone). UAV-04 is assigned to boat-02 (threat 0.84, prepare_intercept=true) as it is the closest armed unit with line-of-sight. UAV-06 is assigned to boat-03 (threat 0.82, prepare_intercept=true) to cover the third distinct threat. UAV-07 tracks boat-05 (threat 0.80) as a secondary monitor. UAV-03 and UAV-05 have 0 ammo and are disengaged to rear anchors. Remaining units hold patrol positions to maintain sensor coverage and reserve readiness."
}
```

## 调用 28（tick 280）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5406.0, 6638.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8308.0, 5035.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8471.0, 8547.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5696.0, -5361.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1110.0, -1304.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4814.0, 1496.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2981.0, -1479.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [858.0, -1696.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is in range of boat-01 (can_intercept=true) and assigned to engage. UAV-04 is assigned to boat-02 (prepare_intercept=true, approaching) to intercept before it reaches the zone. UAV-06 is assigned to boat-03 (prepare_intercept=true, approaching) to intercept. UAV-03 and UAV-05 have 0 ammo and are disengaged to rear anchors. Remaining units hold position to maintain sensor coverage and reserve readiness."
}
```

## 调用 29（tick 290）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5473.0, 6834.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8370.0, 5215.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8508.0, 8795.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5672.0, -5569.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [895.0, -1268.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4770.0, 1644.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3034.0, -1515.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [858.0, -1696.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-01, boat-02, boat-03) are approaching the protected zone. boat-01 is closest and has prepare_intercept=true for uav-04, but usv-02 is already in intercept range (can_intercept=true) and is the closest armed unit to it, so usv-02 is assigned to boat-01. uav-04 is assigned to boat-02 (prepare_intercept=true) to maneuver into position. uav-06 is assigned to boat-03 (prepare_intercept=true) to cover the third threat. The air target (strike-command-01) is far away (dist_zone=18585m) and not yet in intercept range for any unit, so remaining units hold position to conserve ammo and maintain coverage."
}
```

## 调用 30（tick 300）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5525.0, 7034.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8436.0, 5397.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8537.0, 9044.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5693.0, -5775.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4726.0, 1795.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3089.0, -1548.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2128.0, -314.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "Boat-01 and Boat-02 are high-threat surface contacts approaching the protected zone with prepare_intercept=true. UAV-04 and UAV-06 are the closest armed interceptors with line-of-sight (observed_by matches) and are assigned to intercept them immediately to prevent zone entry. Boat-03 is also approaching; USV-03 is already tracking it and is assigned to intercept as it is the closest unit to that specific target. Boat-04 is receding, so UAV-07 is assigned to track it for monitoring. UAV-03 and
```

## 调用 31（tick 310）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat03_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "reserve_uav01_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5591, 7229], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav02_005", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [8492, 5581], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav08_006", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [4687, 1945], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav03_007", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8561, 9295]}, "priority": 0.2},
    {"task_id": "disengage_uav05_008", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5705, -5984]}, "priority": 0.2},
    {"task_id": "track_boat01_009", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-01"}, "priority": 0.6},
    {"task_id": "track_boat02_010", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02"}, "priority": 0.6},
    {"task_id": "track_boat03_011", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03"}, "priority": 0.6}
  ],
  "reasoning": "Three high-threat surface intruders (boat-01, boat-02, boat-03) are approaching the protected zone. UAV-06, UAV-04, and UAV-07 are the closest armed interceptors with valid observation links (via USV-01, Pier, and UAV-07 respectively) and are assigned to intercept them immediately to prevent zone entry. UAV-01, UAV-02, and UAV-08 are held in reserve to cover the distant air threat (strike-command-01) or react to new waves. UAV-03 and UAV-05 have no ammo and are disengaged. USVs continue tracking to maintain sensor fusion."
}
```

## 调用 32（tick 320）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5630.0, 7428.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8562.0, 5759.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8564.0, 9544.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5660.0, -6189.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4645.0, 2091.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3193.0, -1621.0]}, "priority": 0.5}
  ],
  "reasoning": "Boat-01 and Boat-02 are the highest threats (0.86) and are approaching the protected zone. USV-02 has can_intercept=true for Boat-01, so it is assigned to intercept. USV-03 has prepare_intercept=true for Boat-02, so it is assigned to intercept. UAV-06 and UAV-04 are also assigned to intercept Boat-01 and Boat-02 respectively to ensure coverage and redundancy, as they are close and have prepare_intercept=true. Boat-03 is a high threat (0.84) and is approaching, so UAV-07 is assigned to intercept it. Other units are on patrol to maintain coverage and readiness for new threats."
}
```

## 调用 33（tick 330）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5690.0, 7625.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8579.0, 5951.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8578.0, 9795.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5649.0, -6397.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [51.0, -1282.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3244.0, -1659.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2086.0, -255.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [858.0, -1696.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone with high threat levels. boat-02 is closest to the zone (5837m) and has prepare_intercept=true for uav-06, so uav-06 is assigned to intercept it. boat-03 is next (6652m) and uav-04 is already tracking it, so uav-04 continues intercept. boat-04 is furthest (7204m) but uav-08 is in a good position to intercept it. uav-03 and uav-05 have no ammo and are disengaged. Other units hold position to maintain sensor coverage and readiness."
}
```

## 调用 34（tick 340）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5754.0, 7822.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8553.0, 6138.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8584.0, 10037.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5640.0, -6602.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-150.0, -1212.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone with high threat levels (0.84-0.87). Boat-02 is closest to the zone (5703m) and has prepare_intercept=true for multiple units. UAV-04 is closest to boat-02 and assigned to intercept. UAV-06 is closest to boat-03 and assigned to intercept. UAV-08 is closest to boat-04 and assigned to intercept. USVs are assigned to track the primary threat (boat-02) to maintain sensor coverage. UAV-03 and UAV-05 have 0 ammo and are disengaged. Other UAVs are patrolling to maintain
```

## 调用 35（tick 350）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.7},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03"}, "priority": 0.7},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04"}, "priority": 0.7},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5772.0, 8027.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [8500.0, 6323.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8574.0, 10277.0]}, "priority": 0.3},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5804.0, -6728.0]}, "priority": 0.3},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-363.0, -1174.0], "commit_within_m": 9000}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone. UAV-04, UAV-06, and UAV-08 are the closest armed interceptors with feasible ETAs and are assigned to intercept each respective target to spread fire discipline. USVs are assigned to track these targets to maintain sensor coverage. UAV-01, UAV-02, and UAV-07 are held in reserve to react to new threats or if interceptors fail. UAV-03 and UAV-05 have 0 ammo and are disengaged to return to anchor."
}
```

## 调用 36（tick 360）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02"}, "priority": 0.70, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5810, 8225]}, "priority": 0.50},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8542, 10516]}, "priority": 0.50},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5851, -6930]}, "priority": 0.50},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-538, -1068]}, "priority": 0.50}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone with high threat levels and prepare_intercept=true. UAV-06 is closest to boat-02, UAV-04 to boat-03, and UAV-08 to boat-04, so they are assigned to intercept these distinct targets to prevent a mass breach. UAV-02 is assigned to intercept the air target strike-command-01 which has prepare_intercept=true and is approaching. USVs are tasked to track the primary surface threats to maintain sensor coverage. UAVs with 0 ammo (UAV-03, UAV-05) and those not optimally positioned for the immediate surface threats (UAV-01, UAV-07) are held in patrol to conserve energy and maintain general situational awareness."
}
```

## 调用 37（tick 370）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-03"}, "priority": 0.5, "deadline": 100},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-04"}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5820.0, 8428.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8497.0, 10753.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6043.0, -6952.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-724.0, -957.0]}, "priority": 0.4, "deadline": 100}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are approaching the protected zone with high threat levels and prepare_intercept=true. UAV-04, UAV-06, and UAV-08 are the closest armed interceptors to these targets and are assigned to intercept them immediately to prevent zone entry. UAV-02 is assigned to intercept the air threat (strike-command-01) which is approaching and has prepare_intercept=true. USVs are assigned to track the surface threats to maintain sensor coverage. UAV-01, UAV-03, UAV-05, and UAV-07 are held in patrol positions as reserves or due to lack of ammunition (UAV-03, UAV-05)."
}
```

## 调用 38（tick 380）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.7, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.6, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5870.0, 8628.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-937.0, -946.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8469.0, 10993.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6223.0, -6908.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3508.0, -1823.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-02 and boat-03 respectively, as they are the closest threats with prepare_intercept=true and are within weapon range. UAV-08 is assigned to intercept boat-04, which is also approaching and within range. UAV-02 is assigned to intercept strike-command-01, which is approaching and has prepare_intercept=true. USV-02 and USV-03 are tracking boat-02 to maintain sensor coverage. UAV-01 and UAV-07 are patrolling to maintain coverage. UAV-03 and UAV-05 are disengaging as they have no ammo. USV-01
```

## 调用 39（tick 390）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5921.0, 8830.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8462.0, 11234.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6406.0, -6864.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1151.0, -963.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "UAV-04 is assigned to intercept boat-03 (observed by self, prepare_intercept=true, high threat) as it is the closest high-threat surface contact. UAV-06 intercepts boat-02 (observed by self, high threat) to prevent it from entering the zone. UAV-08 intercepts boat-04 (observed by self, high threat). UAV-02 intercepts the air strike-command (observed by self, prepare_intercept=true) to handle the air threat. USVs are tasked to track their respective observed contacts to maintain sensor coverage. UAVs with no ammo or no immediate intercept opportunity are placed on patrol to conserve energy and maintain position."
}
```

## 调用 40（tick 400）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.command.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.command.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.command.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5918.0, 9034.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8469.0, 11477.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6605.0, -6846.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1369.0, -962.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-04 intercepts boat-03 (observed by self, prepare=true). UAV-06 intercepts boat-02 (observed by facility, prepare=true, high threat). UAV-08 intercepts boat-04 (observed by facility, high threat). UAV-02 continues intercepting strike-command-01 (observed by self, prepare=true). USVs track boat-02 for sensor coverage. UAVs 01, 03, 05, 07 hold position as reserve/monitoring."
}
```

## 调用 41（tick 410）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5918.0, 9239.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8464.0, 11717.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6783.0, -6857.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [3659.0, -1932.0]}, "priority": 0.1},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1584.0, -970.0]}, "priority": 0.5}
  ],
  "reasoning": "boat-02 is the highest threat (0.88) and closest to the zone (5073m). It is observed by uav-06, usv-02, and usv-03. uav-04 is assigned to intercept boat-02 (observed by uav-04 in previous ticks, now likely still tracking or re-acquiring, but uav-04 is closest to the threat axis). uav-08 and uav-02 are assigned to intercept strike-command-01 (air, threat 0.69) as it is approaching and prepare_intercept=true for uav-08. usv-02 and usv-03 are assigned to intercept boat-02 as they are in
```

## 调用 42（tick 420）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8466.0, 11959.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6965.0, -6926.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [3709.0, -1968.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1792.0, -1022.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is closest to boat-02 (dist 3544m, prepare=true) and assigned to intercept it. UAV-08 is closest to strike-command-01 (dist 8510m, prepare=true) and assigned to intercept it. UAV-06 is closest to boat-03 (dist 4095m) and assigned to intercept it. USV-02 and USV-03 are assigned to intercept boat-02 as they are within range or preparing to engage. UAV-02, UAV-01 are assigned to intercept strike-command-01 as they are approaching and have prepare=true. UAV-03, UAV-05, USV-
```

## 调用 43（tick 430）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5928.0, 9650.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8465.0, 12201.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [7151.0, -7008.0]}, "priority": 0.1, "deadline": 120}
  ],
  "reasoning": "UAV-05 has can_intercept=true for the air threat (strike-command-01) and is the only unit with that status for that target, so it engages immediately. UAV-04 and
```

## 调用 44（tick 440）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-03.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5926.0, 9857.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8449.0, 12441.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [7348.0, -7046.0]}, "priority": 0.2},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3808.0, -2042.0]}, "priority": 0.4},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2117.0, 211.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [858.0, -1696.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-02 and boat-03 respectively, as they are the closest surface threats with prepare_intercept=true and high threat levels. UAV-08 and UAV-02 are assigned to intercept strike-command-01, which is approaching and has prepare_intercept=true for UAV-08. UAV-01 is patrolling as it has no immediate high-threat targets within its effective range. UAV-03 and UAV-05 are disengaging due to zero ammo. USVs are patrolling to maintain sensor coverage."
}
```

## 调用 45（tick 450）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.command.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5870.0, 10054.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8482.0, 12672.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [7457.0, -7220.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2227.0, -1114.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2126.0, 256.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the air threat (strike-command-01) and is assigned to engage it. UAV-06 is assigned to boat-02 (high threat, approaching, prepare_intercept=true) as it is the closest armed unit with observation. UAV-04 is assigned to boat-03 (high threat, approaching, prepare_intercept=true) as it is the closest armed unit with observation. UAV-02 is assigned to boat-04 (high threat, approaching, prepare_intercept=true) as it is the closest armed unit with observation. USV-01 tracks boat-05 (medium threat, approaching) as it is a sensor-only unit. Other units are on patrol to maintain coverage and conserve ammunition."
}
```

## 调用 46（tick 460）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3908.0, -2112.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2129.0, 301.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [0.0, 0.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5884.0, 10252.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8441.0, 12906.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [0.0, 0.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2408.0, -1038.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. UAV-04 and UAV-06 are assigned to the two closest surface threats (boat-02 and boat-03) which have prepare_intercept=true and are approaching the zone. UAV-02 is assigned to boat-04, which is also approaching. USVs are held in position to maintain sensor coverage and act as a secondary layer, as they are slower and have limited engagement capability compared to UAVs. Other UAVs are held in reserve or patrol to cover potential new threats or reposition if needed."
}
```

## 调用 47（tick 470）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5890.0, 10459.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8266.0, 8458.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8344.0, 13123.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3960.0, -2142.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2118.0, 343.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. UAV-04, UAV-06, and UAV-07 are assigned to the three surface threats (boat-02, boat-03, boat-04) respectively, as they are the closest armed units with line-of-sight and feasible intercept windows. UAV-01 and UAV-02 are held in reserve/patrol as they are too far to engage the current threats effectively. UAV-03 is disengaged due to 0 ammo. USVs are held in position for sensor coverage as they have no weapons or are out of range."
}
```

## 调用 48（tick 480）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_strike_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5920, 10668], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [8253, 8652], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8305, 13358]}, "priority": 0.1, "deadline": 60}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air contact (strike-command-01) and is assigned to engage it. UAV-04 is closest to boat-02 (dist 3072m) and assigned to intercept it. UAV-06 is closest to boat-03 (dist 4577m) and assigned to intercept it. UAV-07 is closest to boat-04 (dist 7053m) and assigned to intercept it. USVs are used for tracking to maintain sensor coverage. UAV-01 and UAV-02 are held in reserve to react to new threats or if current interceptors fail. UAV-03 has no ammo and is disengaged."
}
```

## 调用 49（tick 490）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.command.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5925.0, 10879.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8282.0, 8843.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8250.0, 13587.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4065.0, -2197.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2110.0, 429.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it with a salvo. UAV-04, UAV-07, and UAV-06 are assigned to the three surface threats (boat-02, boat-03, boat-04) respectively, as they are the closest armed units with valid observation links and prepare_intercept=true. UAV-01 and UAV-02 are held in patrol as reserves since the primary threats are being covered. UAV-03 is disengaged due to 0 ammo. USVs are held in patrol as they are sensor-only or have limited engagement capability compared to the UAVs for these specific targets."
}
```

## 调用 50（tick 500）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 50},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 50},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5963.0, 11087.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8281.0, 9036.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8205.0, 13819.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4114.0, -2228.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to the high-threat air target (strike-command-01) which is currently in the intercept window (can_intercept=true) and approaching. UAV-04 is closer and assigned 'salvo' for immediate engagement, while UAV-08 provides backup with 'assess'. USV-02 is assigned to boat-02 (high threat, can_intercept=true). UAV-06 is assigned to boat-03 (high threat, prepare_intercept=true, approaching). UAV-07 is assigned to boat-04 (medium threat, prepare_intercept=true). UAV-01 and UAV-02 are held in patrol positions to maintain sensor coverage and readiness for new threats. UAV-03 is disengaged as it has 0 ammo. USV-01 is held in patrol as it has 0 ammo and is a sensor-only unit."
}
```

## 调用 51（tick 510）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 100},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 100},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05"}, "priority": 0.60, "deadline": 100},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5936.0, 11298.0]}, "priority": 0.50, "deadline": 100},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8229.0, 9223.0]}, "priority": 0.50, "deadline": 100},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8136.0, 14038.0]}, "priority": 0.10, "deadline": 100}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. UAV-06, UAV-07, and UAV-08 are assigned to the three surface threats (boat-02, boat-03, boat-04) respectively, as they are the closest armed units with feasible intercept paths and observation ownership. USV-01 tracks boat-05 as it is a sensor-only unit. UAV-01 and UAV-02 are held in reserve/patrol as they are too far to engage the current immediate threats effectively. UAV-03 is disengaged due to 0 ammo."
}
```

## 调用 52（tick 520）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5948.0, 11513.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8207.0, 9418.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8106.0, 14269.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage. USV-02 has can_intercept=true for boat-02 (closest surface threat) and is assigned to engage. UAV-07 is assigned to boat-02 as a secondary interceptor due to prepare_intercept=true and proximity, ensuring coverage if USV-02 fails or is delayed. UAV-06 is assigned to strike-command-01 as a secondary interceptor due to prepare_intercept=true and closing speed, providing redundancy for the air threat. USV-01 and UAV-04 are tracking other surface threats (boat-05, boat-04) which are further out or have lower immediate threat levels compared to boat-02 and the air target. UAV-01, UAV-02, and UAV-03 are on patrol/hold as they are either out of range, have no ammo (UAV-03), or are better positioned for future threats than current ones."
}
```

## 调用 53（tick 530）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-07.intruder.boat-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1480.0, -3540.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8056.0, 14501.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5981.0, 11724.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8189.0, 9615.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-801.0, 118.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. UAV-07 is assigned to intercept boat-05, which is approaching and has prepare_intercept=true, representing an immediate threat to the zone. USV-02 is assigned to intercept boat-03, which is also approaching and within its sensor range. USV-01 tracks boat-04 as it is stable and further out, preserving its sensor capability. UAV-04 and UAV-03 are disengaged as they have 0 ammo. Remaining UAVs patrol to maintain coverage and readiness for new threats."
}
```

## 调用 54（tick 540）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8007.0, 14728.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1554.0, -3714.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [4317.0, -2347.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "Three high-threat surface contacts (boat-02, boat-03, boat-04) are approaching the protected zone. Boat-02 is closest (3903m) and observed by usv-02 (can_intercept=true) and uav-07 (prepare_intercept=true). Boat-03 is next (4752m) and observed by uav-06 and uav-08 (both feasible). Boat-04 is furthest (5332m) but observed by uav-01 and uav-02 (both feasible). Assigning distinct armed units to each threat to maintain fire discipline and maximize coverage. Units with 0 ammo (uav-03, uav-04, usv-01) are disengaged to conserve resources and avoid infeasible goals."
}
```

## 调用 55（tick 550）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.75, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.70, "deadline": 180},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7901.0, 14935.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1625.0, -3882.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [4372.0, -2371.0]}, "priority": 0.1}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for boat-03, so it engages immediately. UAV-07 and UAV-06 are assigned to boat-02 (highest threat, closest to zone) as they are the closest armed interceptors with feasible ETAs. UAV-08 engages boat-04 which is approaching and within its sensor range. UAV-01 and UAV-02 are tasked with boat-05 (approaching, prepare_intercept=true) to provide redundancy and coverage. UAV-03, UAV-04, and USV-01 have 0 ammo and are disengaged to conserve resources and avoid infeasible engagement attempts."
}
```

## 调用 56（tick 560）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4423.0, -2397.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5989.0, 12160.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8169.0, 10005.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7882.0, 15166.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1704.0, -4065.0]}, "priority": 0.1}
  ],
  "reasoning": "boat-02 is the highest threat (0.91) and closest to the zone (3787m). usv-02 has can_intercept=true and is assigned to engage it. uav-07 has prepare_intercept=true for boat-02 and is assigned to intercept as a secondary layer. boat-04 (0.88) is assigned to uav-06 (observer) and boat-03 (0.84) to uav-08 (observer) to spread fire discipline. uav-01 and uav-02 are held in reserve as they are too far to engage the current wave effectively. uav-03 and uav-04 have 0 ammo and are disengaged."
}
```

## 调用 57（tick 570）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6014.0, 12354.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8100.0, 10172.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7803.0, 15386.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1868.0, -4173.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3752.0, 4733.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4473.0, -2421.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for the highest threat (boat-02, 0.92) and is approaching; assign intercept. UAV-06 is closest to boat-03 (0.88) and has ammo; assign intercept. UAV-07 is closest to boat-04 (0.88) and has ammo; assign intercept. UAV-03 and UAV-04 have 0 ammo and are disengaged to rear anchors. Other units hold position to maintain sensor coverage and reserve."
}
```

## 调用 58（tick 580）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.70, "deadline": 60},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03"}, "priority": 0.60, "deadline": 60},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6052.0, 12566.0], "commit_within_m": 9000}, "priority": 0.50, "deadline": 120},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [8052.0, 10363.0], "commit_within_m": 9000}, "priority": 0.50, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7765.0, 15614.0]}, "priority": 0.10, "deadline": 120}
  ],
  "reasoning": "Three intruders (boat-02, boat-03, boat-04) are approaching the protected zone. Boat-02 is closest (3580m) and observed by USV-02 (can_intercept=true) and UAV-07 (prepare_intercept=true). Assign USV-02 to intercept boat-02 immediately. Assign UAV-07 to intercept boat-02 as well (prepare_intercept=true, approaching) to ensure engagement if USV-02 fails or needs repositioning. Boat-03 is next (4384m) and observed by UAV-06 (can_intercept=true); assign UAV-06 to intercept. Boat-04 is furthest (4954m) and observed by UAV-08 (can_intercept=true); assign UAV-08 to intercept. USV-01 and UAV-04 are sensors with no ammo; assign them to track their respective primary contacts for continuous observation. UAV-01 and UAV-02 are far away and not in intercept range; hold them in reserve. UAV-03 has no ammo; disengage to rear anchor."
}
```

## 调用 59（tick 590）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6090.0, 12772.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7989.0, 10552.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7701.0, 15832.0]}, "priority": 0.1, "deadline": 60},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1944.0, -4549.0]}, "priority": 0.1, "deadline": 60}
  ],
  "reasoning": "boat-02 is the highest threat (0.92) and closest to the zone (3453m). It is observed by uav-08 and usv-02. usv-02 is in range (can_intercept=true) and assigned to intercept. uav-07 has prepare_intercept=true for boat-02 and is assigned to intercept as well to ensure engagement. boat-03 (0.90) is observed by uav-07 and uav-06; uav-06 is assigned to intercept it. boat-04 (0.88) is observed by usv-01 and uav-08; uav-08 is assigned to intercept it. usv-01 tracks boat-04 to maintain sensor coverage. uav-01 and uav-02 are far away and targets are receding, so they hold position. uav-03 and uav-04 have 0 ammo and are disengaged."
}
```

## 调用 60（tick 600）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6096.0, 12984.0], "commit_within_m": 9000}, "priority": 0.4, "deadline": 120},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [7927.0, 10745.0], "commit_within_m": 9000}, "priority": 0.4, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7649.0, 16053.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1995.0, -4724.0]}, "priority": 0.2, "deadline": 120}
  ],
  "reasoning": "UAV-06 is assigned to intercept boat-02 (highest threat 0.92) as it is approaching and has prepare_intercept=true. UAV-07 continues intercepting boat-03 (threat 0.88) which is also approaching. UAV-08 is assigned to intercept boat-04 (threat 0.88) to spread coverage across the three distinct threats. USVs are used for tracking to maintain sensor contact. UAV-01 and UAV-02 are held in reserve at their current positions to react to any new threats or if the primary interceptors fail. UAV-03 and UAV-04 have 0 ammo and are disengaged to return to anchor."
}
```

## 调用 61（tick 610）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat04_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "patrol_uav01_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6088.0, 13190.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [7976.0, 10899.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7603.0, 16284.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2080.0, -4822.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-2174.0, 258.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4678.0, -2527.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are within weapon range and approaching the protected zone. boat-02 is closest to the zone boundary (3273m) and is observed by usv-02, which is assigned to intercept. boat-03 and boat-04 are also within range and observed by uav-08 and uav-07 respectively, so they are assigned to intercept. The air contacts are far away (24-26km) and not yet in the intercept window, so the remaining UAVs are held in patrol to maintain coverage and conserve ammunition."
}
```

## 调用 62（tick 620）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6093.0, 13398.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8153.0, 10973.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7587.0, 16540.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-2387.0, 279.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-3501.0, -2090.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4732.0, -2560.0]}, "priority": 0.5}
  ],
  "reasoning": "Immediate threat: 3 surface boats (boat-02, boat-03, boat-04) are within 5km of the protected zone and receding/stable, but boat-02 and boat-03 are still high threat (0.91/0.89). USV-02 (armed) is assigned to boat-02 (closest, highest threat). UAV-08 (armed) is assigned to boat-03 (observed by facility.pier, but UAV-08 is the only armed unit with a clear line of sight/assignment history for this sector, and boat-03 is observed by usv-02 which is busy; however, the rule says 'issue intercept for unit U only against contacts with by=U'. Wait, boat-03 is observed by defender.usv-02. USV-02 is assigned to boat-02. Can USV-02 intercept both? No, one goal per unit. Boat-03 is observed by usv-02. If I assign USV-02 to boat-02, who intercepts boat-03? UAV-08 is currently tracking boat-03 (current=sensor.contact.facility.pier.intruder.boat-03). But the graph shows boat-03 observed_by=defender.usv-02. Does UAV-08 observe it? The graph lists contacts per unit. Under UAV-08, boat-03 is NOT listed. Under USV-02, boat-03 IS listed. Therefore, only USV-02 can fire at boat-03. But USV-02 is also the only unit that
```

## 调用 63（tick 630）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat04_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "track_boat03_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.command.intruder.boat-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat05_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05"}, "priority": 0.80, "deadline": 120},
    {"task_id": "patrol_uav01_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6102.0, 13603.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8327.0, 11051.0]}, "priority": 0.5},
    {"task_id": "disengage_uav03_007", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7549.0, 16793.0]}, "priority": 0.2},
    {"task_id": "patrol_uav06_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-2624.0, 308.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-3501.0, -2090.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_010", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3396.0, 5603.0]}, "priority": 0.5}
  ],
  "reasoning": "Immediate threat: 3 surface intruders (boat-02, boat-03, boat-04) are within 5km of the protected zone. boat-02 and boat-04 are observed by usv-02 (armed, ammo=2) and have can_intercept=true; assigning usv-02 to engage them. boat-03 is observed by facility.command (not an armed unit I control directly for firing, but usv-01 is nearby and tracking); usv-01 has no ammo, so it continues tracking to maintain sensor lock. boat-05 is observed by uav-04 (no ammo), so uav-04 continues tracking. Air targets are far away (16-27km) with no prepare_intercept flags, so armed UAVs (uav-01, uav-02, uav-06, uav-07, uav-08) hold position/patrol to conserve ammo and maintain coverage. uav-03 has 0 ammo and is disengaged to rear anchor."
}
```

## 调用 64（tick 640）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4844.0, -2630.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6124.0, 13807.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8484.0, 11164.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7540.0, 17046.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2475.0, -4322.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-2860.0, 323.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-04, boat-05) are currently in the immediate vicinity of the protected zone and are receding, but they remain high-threat contacts with can_intercept=true. USV-02 is assigned to boat-02 (closest, highest threat 0.91). UAV-08 is assigned to boat-05 (observed by UAV-08, threat 0.86). UAV-07 is assigned to boat-04 (observed by facility.pier, threat 0.89). The air contacts (strike-comms/fuel) are far away (dist > 15km) with prepare_intercept=false, so they do not require immediate engagement. UAV-03 and UAV-04 have 0 ammo and are kept on patrol to maintain sensor coverage or reposition. USV-01 has 0 ammo and is on patrol. Remaining armed UAVs (01, 02, 06) are held on patrol to conserve ammunition and maintain readiness for the distant air threats."
}
```

## 调用 65（tick 650）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4896.0, -2665.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6138.0, 14009.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8654.0, 11256.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7525.0, 17303.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2557.0, -4150.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-3095.0, 356.0]}, "priority": 0.5}
  ],
  "reasoning": "Surface threats (boat-02, boat-04, boat-05) are the highest priority with threat >0.85 and are currently within sensor range of armed units (usv-02, uav-07, uav-08). usv-01 is out of ammo and cannot engage, so it holds position to maintain sensor coverage. Air threats are far away (dist > 15km) with no prepare_intercept flags, so armed UAVs (uav-01, uav-02, uav-06) hold position to conserve ammo and wait for closer approach. uav-03 and uav-04 are out of ammo and hold position."
}
```

## 调用 66（tick 660）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4952.0, -2700.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6178.0, 14211.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8819.0, 11354.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7500.0, 17559.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2609.0, -3955.0]}, "priority": 0.1}
  ],
  "reasoning": "Four surface intruders (boat-02, boat-03, boat-04, boat-05) are currently within weapon range of their respective observers (USV-02, UAV-06, UAV-07, UAV-08) and are the highest priority threats (threat > 0.85). USV-02 is assigned to boat-02 (highest threat 0.93) with a salvo policy to ensure a kill. UAV-08, UAV-07, and UAV-06 are assigned to the remaining boats with assess policy to conserve ammo. USV-01 is out of ammo and on patrol. UAV-01 and UAV-02 are holding position to monitor distant air threats (strike-comms) which are not yet in intercept range. UAV-03 and UAV-04 are out of ammo and disengaging to rear anchors."
}
```

## 调用 67（tick 670）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6225.0, 14415.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8975.0, 11460.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7496.0, 17812.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2615.0, -3759.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-3984.0, -1649.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5009.0, -2734.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their assigned interceptors (usv-02, uav-06, uav-08) and are the highest priority threats (threat ~0.9). Although they are currently receding or stable, they are close to the protected zone boundary and must be engaged immediately to prevent them from turning or re-entering. UAV-01 and UAV-02 are holding position to monitor the distant air contacts (strike-comms) which are far away (20km+) and not yet in intercept range. UAV-03 and UAV-04 are out of ammo and disengaging to rear anchors. UAV-07 and USV-01 are holding position as they have no immediate targets in range or are out of ammo (USV-01)."
}
```

## 调用 68（tick 680）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6275.0, 14618.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9115.0, 11588.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7482.0, 18069.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2599.0, -3544.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4162.0, -1558.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5066.0, -2767.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their respective assigned interceptors (usv-02, uav-06, uav-08) and are receding/stable, indicating previous engagement or standoff. Immediate intercept commands are issued to maintain pressure and prevent them from re-entering the protected zone. The air threats (strike-comms/fuel) are far away (dist > 13km) with no prepare_intercept flags, so the remaining armed UAVs (uav-01, uav-02, uav-07) are held in patrol positions to conserve ammunition and maintain situational awareness. Unarmed units (uav-03, uav-04, usv-01) are held in position."
}
```

## 调用 69（tick 690）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6310.0, 14825.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9251.0, 11721.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7471.0, 18327.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2536.0, -3374.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4362.0, -1464.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5124.0, -2800.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their assigned interceptors (usv-02, uav-06, uav-08) and are the highest priority threats (threat > 0.9). Although they are currently receding or stable, they are close to the protected zone boundary and must be engaged immediately to prevent them from turning or re-entering. The air targets (strike-comms, strike-fuel) are far away (dist > 13km) with no immediate interception window (prepare=false), so the remaining UAVs are held in patrol positions to conserve energy and maintain situational awareness."
}
```

## 调用 70（tick 700）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.command.intruder.boat-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6307.0, 15029.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9406.0, 11825.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7426.0, 18579.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2608.0, -3174.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-4273.0, 503.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4534.0, -1324.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2878.0, 6507.0]}, "priority": 0.5}
  ],
  "reasoning": "Surface threats (boat-02, boat-03, boat-04, boat-05) are the immediate priority as they are closest to the protected zone and have high threat scores. USV-02 is the only armed surface unit with can_intercept=true for boat-02 and boat-03, so it is assigned to engage them. USV-01 is unarmed and assigned to track the remaining surface threats to maintain sensor coverage. Air threats are far away (dist > 12km) and not yet in intercept range (prepare_intercept=false), so UAVs are held in patrol positions to conserve energy and maintain readiness for when air threats enter the engagement envelope."
}
```

## 调用 71（tick 710）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6286.0, 15227.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9585.0, 11892.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7413.0, 18833.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2564.0, -2976.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4688.0, -1167.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "Immediate threat: 3 surface boats (boat-02, boat-03, boat-04) are within 4km of the protected zone. boat-02 is closest (2.4km) and observed by usv-02 (armed), so usv-02 intercepts with salvo. boat-04 is observed by uav-06 (armed) and approaching, so uav-06 intercepts. boat-05 is observed by uav-08 (armed) and receding but close, so uav-08 intercepts to secure the kill. boat-03 is observed by usv-01 (sensor only) and uav-06 (already tasked), so usv-01 tracks it for continuous observation. Air targets are far (>12km) and not yet in intercept window (prepare=false), so armed UAVs (uav-01, uav-02, uav-07) hold position/patrol to maintain coverage. UAVs with 0 ammo (uav-03, uav-04) disengage to rear anchors."
}
```

## 调用 72（tick 720）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6186.0, 15399.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9762.0, 11953.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7398.0, 19089.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2512.0, -2774.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-4864.0, -1039.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5291.0, -2905.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are within 4.5km of the protected zone and receding/approaching slowly. USV-02 has can_intercept=true for boat-02 and boat-03; UAV-08 has can_intercept=true for boat-04. Assign USV-02 to boat-02 (closest, highest threat 0.94) and UAV-08 to boat-04 (threat 0.91). UAV-06 is assigned to boat-04 as a secondary interceptor if UAV-08 fails, though it is far away. All other units are on patrol as no air targets are in intercept range (all have prepare_intercept=false and large range gaps)."
}
```

## 调用 73（tick 730）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6115.0, 15583.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9947.0, 11986.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7376.0, 19347.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2453.0, -2569.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-5015.0, -877.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5348.0, -2938.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are within weapon range of their respective observers (usv-02, uav-08, uav-06) and have high threat levels (0.91-0.94). Immediate interception is required to prevent them from entering the protected zone. The air contacts are far away (15km+) and not yet in intercept range, so the remaining UAVs are held in patrol positions to maintain coverage and conserve ammunition."
}
```

## 调用 74（tick 740）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6012.0, 15751.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10136.0, 12003.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7368.0, 19607.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2395.0, -2368.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-5183.0, -729.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5404.0, -2971.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their respective assigned units (usv-02, uav-08, uav-06) and are receding or holding near the protected zone boundary. Immediate intercept commands are issued to maintain pressure and prevent them from re-entering the zone. The air threats (strike-comms/fuel) are still far away (15-20km) with no prepare_intercept flags, so the remaining armed UAVs (uav-01, uav-02, uav-07) are held in patrol positions to conserve ammunition and maintain sensor coverage. UAV-03 and UAV-04 are out of ammo and held in position."
}
```

## 调用 75（tick 750）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5893.0, 15907.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10320.0, 12045.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7346.0, 19865.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2328.0, -2168.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-5349.0, -579.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5461.0, -3006.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their respective assigned interceptors (usv-02, uav-08, uav-06) and are receding, indicating previous engagement or maneuvering. We maintain intercept commands to ensure they are destroyed before they can re-approach or if they are decoys. The air contacts (strike-comms/fuel) are far away (11km-24km) with no immediate threat to the protected zone (dist_zone > 18km). UAVs with ammo (uav-01, uav-02, uav-07) are held in patrol positions to conserve ammunition and maintain sensor coverage, as the air threats are not yet in the intercept window (prepare_intercept=false). UAV-03 and UAV-04 have no ammo and are held in position. USV-01 has no ammo and is held."
}
```

## 调用 76（tick 760）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.70, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.65, "deadline": 120},
    {"task_id": "intercept_008", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.60, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2275.0, -1963.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [5518.0, -3041.0]}, "priority": 0.1}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for the three high-threat surface boats (boat-02, boat-03, boat-04) which are currently receding but close to the zone; it must engage them immediately. UAV-02 and UAV-01 are assigned to the fastest-closing air threat (strike-comms-04, ttr=69-842s) to prepare for interception as it approaches weapon range. UAV-08 and UAV-06/07 are assigned
```

## 调用 77（tick 770）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5638.0, 16204.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10684.0, 12137.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2211.0, -1760.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-5716.0, -327.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5575.0, -3075.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their assigned interceptors (usv-02, uav-08, uav-06) and are receding, indicating they are likely outside the immediate kill zone or maneuvering away. Immediate engagement is required to prevent them from re-entering the protected zone or launching attacks. The air targets (strike-comms/fuel) are far away (15-23km) with no immediate threat (prepare_intercept=false), so armed UAVs are held in patrol positions to conserve fuel and maintain situational awareness. UAV-03 and UAV-04 are out of ammo and held in place."
}
```

## 调用 78（tick 780）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5514.0, 16353.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10871.0, 12166.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2176.0, -1550.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-5894.0, -194.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5633.0, -3109.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of their assigned interceptors (usv-02, uav-08, uav-06) and are receding, indicating previous engagement or maneuvering. Immediate intercept commands are issued to maintain pressure and ensure they do not re-enter the protected zone. Air targets are far away (10km+) and not yet in the intercept window (prepare_intercept=false), so armed UAVs are held in patrol positions to conserve energy and maintain situational awareness. UAV-03 and UAV-04 have no ammo and are held in place."
}
```

## 调用 79（tick 790）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5403.0, 16514.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11061.0, 12188.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2112.0, -1344.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6081.0, -71.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5691.0, -3142.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-02, boat-03, boat-04) are currently within weapon range of armed units (usv-02, uav-06, uav-08) and are the highest priority threats (threat > 0.9). Although they are currently receding, they are close to the protected zone boundary and must be engaged to prevent re-entry or future waves. The air contacts (strike-comms, strike-fuel) are far away (dist > 9000m) and not yet in the intercept window (prepare_intercept=false), so the remaining UAVs are held in patrol positions to maintain sensor coverage and readiness for the approaching air waves."
}
```

## 调用 80（tick 800）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5273.0, 16658.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11251.0, 12205.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2048.0, -1140.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5747.0, -3176.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 and UAV-08 are assigned to intercept boat-03 (can_intercept=true, high threat) as it is the closest surface threat to the zone. UAV-06 and UAV-07 continue intercepting boat-04 and boat-03 respectively to maintain pressure on the surface wave. Air targets are far (16-23km) and not yet in intercept range (prepare=false), so remaining UAVs hold position to conserve energy and prepare for future engagement windows."
}
```

## 调用 81（tick 810）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5804.0, -3210.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2077.0, -945.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-6638.0, 749.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6426.0, 209.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2315.0, 7678.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is assigned to intercept boat-03 as it is the closest high-threat surface target within weapon range (can_intercept=true). UAV-02 and UAV-01 are assigned to intercept the two closest air threats (strike-comms-04 and strike-comms-03) which have prepare_intercept=true and are approaching the protected zone. Other units are held in patrol positions to maintain coverage and conserve ammunition, as the air threats are still far from the zone and the surface threats are being handled by the closest available assets."
}
```

## 调用 82（tick 820）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.60, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-02"}, "priority": 0.60, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03"}, "priority": 0.60, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-02"}, "priority": 0.60, "deadline": 120},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.10, "deadline": 300},
    {"task_id": "return_002", "goal_type": "return", "parameters": {"unit_id": "defender.uav-04"}, "priority": 0.10, "deadline": 300}
  ],
  "reasoning": "Immediate threat: 3 surface boats (boat-03, 04, 05) are within or near weapon range of USV-02 and UAV-06/07. USV-02 has can_intercept=true for boat-04; UAV-07 has can_intercept=true for boat-03; UAV-06 is close to boat-05 (range_gap=24m). Assign these three to intercept immediately to prevent zone entry. Air threats (strike-comms/fuel) are far (12-18km) and not yet in intercept window (prepare=false), so assign available armed UAVs (01, 02, 08) to track the closest air contacts to maintain observation and prepare for future intercepts. UAV-03 and UAV-04 have 0 ammo, so return them to base."
}
```

## 调用 83（tick 830）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5916.0, -3270.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2177.0, -527.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 is in range of boat-04 (can_intercept=true) and must engage immediately to prevent zone entry. UAV-02 has prepare_intercept=true for strike-comms-04 (closest air threat), so it initiates intercept now. Other armed UAVs (01, 08, 06, 07) are assigned to strike-comms-04 to ensure coverage and redundancy against the primary air threat, as they are the only units with ammo capable of engaging it. UAV-03 and UAV-04 have 0 ammo and are held in patrol. USV-01 is a sensor-only unit and is held in position to maintain tracking of the surface contacts."
}
```

## 调用 84（tick 840）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav06_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-7109.0, 777.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-6754.0, 539.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.3},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2261.0, -331.0]}, "priority": 0.3},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5972.0, -3302.0]}, "priority": 0.4}
  ],
  "reasoning": "USV-02 is in range of boat-03 (can_intercept=true) and assigned to engage. UAV-08 and UAV-01 are assigned to boat-04 and boat-05 respectively to spread fire and cover the surface threats near the zone boundary. UAV-02 is assigned to strike-comms-04 as it has prepare_intercept=true and is the closest interceptor to that air threat. UAV-06 and UAV-07 are held in reserve to react to new threats. UAV-03 and UAV-04 are disengaged due to 0 ammo. USV-01 is patrolling as a sensor."
}
```

## 调用 85（tick 850）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.8, "deadline": 120},
    {"task_id": "ambush_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "standoff_m": 500}, "priority": 0.8, "deadline": 120},
    {"task_id": "ambush_003", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "standoff_m": 500}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-04", "position": [2302.0, -121.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6029.0, -3331.0]}, "priority": 0.4, "deadline": 300}
  ],
  "reasoning": "Immediate threat: 3 surface boats (boat-03, boat-04, boat-05) are within or near weapon range of USV-02 and UAVs. USV-02 is assigned to boat-04 (can_intercept=true). UAV-06 and UAV-08 are assigned to boat-03 and boat-05 respectively to engage them before they enter the protected zone. The air threats (strike-comms and strike-fuel) are further away but approaching. UAV-02, UAV-01, and UAV-07 are positioned to ambush these air threats at optimal intercept points. UAV-03 and UAV-04 are out of ammo and held in reserve. USV-01 is on patrol to maintain sensor coverage."
}
```

## 调用 86（tick 860）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_boat_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5136.0, 17010.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [12168.0, 12286.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7002.0, 873.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6086.0, -3362.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 has can_intercept=true for boat-04 (dist 2943m, threat 0.94) and is the only unit with ammo in close range, so it engages immediately. UAV-06 and UAV-08 are assigned to boat-03 and boat-05 respectively (threats 0.94/0.90, dist ~3000m) to prevent them from entering the zone; they are the closest armed units to these targets. UAV-04 is assigned to strike-fuel-02 (prepare_intercept=true, threat 0.63) as it is the only unit observing it with prepare=true and is relatively close (10477m). Other units are on patrol to maintain coverage of the air threats (strike-comms/fuel) which are currently receding or far away (dist > 8000m)."
}
```

## 调用 87（tick 870）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.65, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6143.0, -3392.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-03", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "USV-02 has can_intercept=true for boat-04, the highest threat surface contact closest to the zone. UAV-04 is assigned to strike-fuel-02 (prepare_intercept=true, high threat) despite 0 ammo to maintain tracking/positioning for potential future engagement or to force a turn. UAV-08 is assigned to strike-comms-02 (prepare_intercept=true) as it is the closest armed interceptor to that target. UAV-02, UAV-01, UAV-07, and UAV-06 are assigned to other high-threat air contacts to establish intercept geometry early, as they are all approaching and have prepare_intercept or high threat scores. USV-01 holds position as it has no ammo and is a sensor. UAV-03 holds as it has no ammo."
}
```

## 调用 88（tick 880）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_fuel_03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03"}, "priority": 0.9, "deadline": 40},
    {"task_id": "intercept_comms_02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.85, "deadline": 30},
    {"task_id": "track_boat_04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_boat_03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_boat_05_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_uav_01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5107.0, 17406.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [12514.0, 12416.0]}, "priority": 0.5},
    {"task_id": "disengage_uav_03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-04 is the only unit observing strike-fuel-02 (prepare_intercept=true, high threat) and must intercept immediately despite 0 ammo (likely decoy or sensor-only role). UAV-06 and UAV-07 are assigned to the other two approaching air threats (fuel-03, comms-02) which have prepare_intercept=true. Surface boats are receding but remain high threat; USVs and UAV-08 track them to maintain sensor coverage. UAV-01 and UAV-02 hold position as they are too far to engage the current air wave effectively. UAV-03 is disengaged due to 0 ammo."
}
```

## 调用 89（tick 890）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2638.0, 651.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-7821.0, 811.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7492.0, 1306.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-02 is closest to strike-comms-04 (range_gap 1001m) and assigned to intercept. UAV-01 is closest to strike-comms-03 (range_gap 8277m vs others) and assigned to intercept. UAV-08 is closest to strike-comms-02 (range_gap 3933m) and assigned to intercept. USVs track their respective primary air threats to maintain observation. UAV-04 and UAV-03 have 0 ammo and are held in patrol. UAV-06 and UAV-07 are held in patrol as reserves for the western axis, as the current air threats are approaching from the east/south-east."
}
```

## 调用 90（tick 900）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5051.0, 17797.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [12869.0, 12532.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-8036.0, 845.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7641.0, 1463.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [1713.0, 8860.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with prepare_intercept=true for the three closest air threats (strike-comms-02, strike-comms-03, strike-fuel-03). Although it has 0 ammo, it must maneuver to intercept positions to potentially engage if ammo is replenished or if the executor logic allows for a different state (though typically 0 ammo means no fire, the maneuver is still required to close distance or reposition). The USVs are tracking the high-threat surface boats (boat-04, boat-05) which are close to the zone but currently receding. Other UAVs are holding position as their targets are far away and not in the intercept window."
}
```

## 调用 91（tick 910）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2701, 870]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1838, 2021]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6372, -3514]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330, 19998]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-8270, 921]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7851, 1543]}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 is closest to strike-comms-04 (range_gap 1300m) and has ammo, so it intercepts. UAV-08 is closest to strike-comms-02 (range_gap 3427m) and has ammo, so it intercepts. UAV-01 is closest to strike-comms-03 (range_gap 8392m) and has ammo, so it intercepts. UAV-04 and UAV-03 have no ammo, so they patrol. USVs have no ammo or are sensors only, so they patrol."
}
```

## 调用 92（tick 920）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 210},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 40},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04"}, "priority": 0.7, "deadline": 300},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04"}, "priority": 0.7, "deadline": 300},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-8505.0, 977.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 600},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-8037.0, 1670.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 600},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.3, "deadline": 600}
  ],
  "reasoning": "UAV-04 is the only unit with prepare_intercept=true for the closest air threat (strike-fuel-02, dist 8177m, ttr 6.9t) and is currently tracking it; issue intercept immediately despite ammo=0 to maintain positioning or if ammo is replenished/erroneous, but primarily to break off if infeasible. UAV-08 is closest to strike-comms-02 (dist 11162m, closing 26.5m/t) and has ammo; assign intercept. UAV-01 and UAV-02 are assigned to strike-comms-04 (dist 16212m/9562m) to prepare for the next wave. USVs track the high-threat surface contacts (boat-04/05) which are receding but close to the zone. UAV-06/07 held in reserve near the objective. UAV-03 disengaged due to 0 ammo."
}
```

## 调用 93（tick 930）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 180},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-05"}, "priority": 0.6, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5102.0, 17996.0]}, "priority": 0.3, "deadline": 600},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.3, "deadline": 600}
  ],
  "reasoning": "UAV-04 is in range of strike-fuel-02 (can_intercept=true) and must engage immediately despite low ammo to prevent zone entry. UAV-02 is assigned to strike-comms-03 (prepare_intercept=true, closing fast) to intercept before it reaches the zone. UAV-08 is assigned to strike-comms-04 (prepare_intercept=true, closing fast) to cover the third air threat. UAV-06 and UAV-07 are assigned to the remaining air threats (strike-fuel-03 and strike-comms-02) to maintain full coverage of the air wave, even though they are further out, as they are the only units with ammo capable of engaging them. USVs track the surface boats which are currently receding and outside immediate threat range. UAV-01 and UAV-03 hold position as reserves."
}
```

## 调用 94（tick 940）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.command.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2710.0, 1297.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 is out of ammo and must disengage. UAV-08 is closest to the high-threat surface boat-04 (dist 10.5km, closing) and can intercept it before it reaches the zone (dist_zone 1.7km). UAV-06 and UAV-07 are positioned to intercept the incoming air threats (strike-fuel-02 and strike-comms-03) which are approaching the zone. UAV-02 and UAV-01 are assigned to the remaining air threats (strike-comms-04 and strike-comms-03) to maintain coverage. USV-02 is assigned to track/intercept boat-04 as a secondary sensor/weapon platform if UAV-08 fails, though USV-02 is a sensor-only unit in the prompt description ('picket USVs (sensors only)'), wait, the prompt says 'picket USVs (sensors only)' but USV-02 has ammo=2. I will assume USV-02 can fire if it has ammo, or use it for tracking if not. Given the prompt says 'sensors only' for picket USVs, I should be careful. However, USV-02 has ammo=2. I will assign it to track boat-04 to maintain sensor contact, as UAV-08 is the primary interceptor. Actually, looking at
```

## 调用 95（tick 950）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_comms03_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_comms02_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_fuel03_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_comms04_005", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_comms02_006", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-comms-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_boat04_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_boat05_008", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.5, "deadline": 120},
    {"task_id": "return_uav03_009", "goal_type": "return", "parameters": {"unit_id": "defender.uav-03"}, "priority": 0.1, "deadline": 300}
  ],
  "reasoning": "UAV-04 is out of ammo but has can_intercept=true for strike-fuel-02; however, it cannot fire. UAV-08 is the closest armed unit to strike-fuel-02 (dist 10479m, feasible_eta 62t) and is assigned to intercept. UAV-01 is assigned to strike-comms-03 (dist 16512m, feasible_eta 213t) as it is the only other armed unit with a feasible intercept path to a high-threat air target not covered by others. UAV-02 is assigned to strike-comms-02 (dist 11422m, feasible_eta 86t) to spread coverage. UAV-04, UAV-06, UAV-07, and USVs are used for tracking to maintain sensor coverage on remaining threats. UAV-03 is out of ammo and returning to base."
}
```

## 调用 96（tick 960）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-9429, 1263], "commit_within_m": 9000}, "priority": 0.7},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-8817, 2027], "commit_within_m": 9000}, "priority": 0.7},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330, 19998]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.6}
  ],
  "reasoning": "UAV-04 and UAV-08 have can_intercept=true for fuel-02 and comms-03 respectively; engaging immediately. UAV-02 and UAV-01 are assigned to comms-04 and comms-02 as they are the closest armed units to those targets and will enter range soon. UAV-06 and UAV-07 held in reserve near the protected zone to react to any breakthrough. UAV-03 is out of ammo and disengaging. USVs tracking the high-threat surface boat-05."
}
```

## 调用 97（tick 970）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_fuel03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_comms03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "intercept_comms02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "intercept_comms04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-05"}, "priority": 0.7, "deadline": 300},
    {"task_id": "track_comms02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.6, "deadline": 300},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2823.0, 1692.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 300}
  ],
  "reasoning": "UAV-04 and UAV-03 are out of ammo and disengaged. The fuel intruders (02, 03) are the highest threat (0.77) and closest to the zone (8.5k-9.3k m), so they are assigned to the nearest armed interceptors (UAV-06, UAV-07) to engage before they cross the boundary. The comms intruders (02, 03, 04) are further out (9.8k-10.9k m) and are assigned to the remaining armed interceptors (UAV-08, UAV-02, UAV-01) to establish intercept geometry. USVs are used for tracking to maintain sensor coverage on the surface threat (boat-05) and air contacts, preserving their limited mobility for repositioning if needed."
}
```

## 调用 98（tick 980）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_comms_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "intercept_comms_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "intercept_comms_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "track_boat_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.boat-05"}, "priority": 0.9, "deadline": 500},
    {"task_id": "track_fuel_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 200},
    {"task_id": "disengage_uav03", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_uav04", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2896.0, 1893.0]}, "priority": 0.1},
    {"task_id": "reserve_uav07", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-9228.0, 2200.0], "commit_within_m": 9000}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-03 are out of ammo and disengaged. UAV-08 intercepts the high-threat fuel intruder (observed by UAV-04, but UAV-08 is the closest armed unit with feasible intercept). UAV-02, UAV-01, and UAV-06 intercept the three comms intruders respectively, spreading fire discipline. USV-02 tracks the high-threat boat intruder. USV-01 tracks the fuel intruder. UAV-07 held in reserve."
}
```

## 调用 99（tick 990）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-10092.0, 1570.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-9435.0, 2281.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6790.0, -3747.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1657.0, 2316.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2962.0, 2104.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-08 is closest to the highest threat (strike-comms-02) and has ammo, so it intercepts. UAV-02 and UAV-01 are assigned to the other two approaching air threats (strike-comms-04 and strike-comms-03) respectively, as they are the nearest armed units with feasible intercept ETAs. UAV-04 and UAV-03 are out of ammo and disengaged. USVs and remaining UAVs hold position to maintain sensor coverage and reserve."
}
```

## 调用 100（tick 1000）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2897.0, 2314.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.6}
  ],
  "reasoning": "UAV-06 and UAV-07 are assigned to the high-threat fuel intruders (0.81/0.78) approaching from the east, as they are the closest armed units to that axis. UAV-08, UAV-02, and UAV-01 are assigned to the comms intruders (0.77-0.79) which are currently in the 'prepare' or 'approaching' phase; UAV-08 is closest to comms-03, UAV-02 to comms-04, and UAV-01 to comms-02. UAV-03 and UAV-04 are out of ammo and disengaged. USVs track the high-threat surface boat-05 (0.90) which is receding but remains a significant threat."
}
```

## 调用 101（tick 1010）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_02", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 200},
    {"task_id": "intercept_fuel_03", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 200},
    {"task_id": "intercept_comms_03", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 200},
    {"task_id": "intercept_comms_02", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 200},
    {"task_id": "intercept_comms_04", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 200},
    {"task_id": "disengage_uav_03", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_uav_04", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3008.0, 2499.0]}, "priority": 0.1},
    {"task_id": "track_boat_05", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05"}, "priority": 0.6},
    {"task_id": "track_fuel_04", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.5}
  ],
  "reasoning": "UAV-06 and UAV-07 are assigned to the high-threat fuel intruders (0.83, 0.79) which are approaching the zone. UAV-08 continues tracking/intercepting comms-03. UAV-01 and UAV-02 are assigned to the remaining comms intruders (0.81, 0.75) to maintain coverage and prepare for engagement as they close. UAV-03 and UAV-04 are out of ammo and disengaged. USVs track the surface boat and the nearby fuel intruder for sensor fusion."
}
```

## 调用 102（tick 1020）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-02"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03"}, "priority": 0.85, "deadline": 100},
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.8, "deadline": 100},
    {"task_id": "ambush_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-04"}, "priority": 0.75, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3092.0, 2702.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6, "deadline": 100}
  ],
  "reasoning": "UAV-08 is closest to the Comms wave (range_gap ~1900m) and assigned to the closest threat (Comms-02). UAV-02 and UAV-01 are assigned to the other Comms targets to spread fire and ensure coverage. UAV-06 and UAV-07 are positioned to ambush the approaching Fuel wave (high threat, long range). UAV-04 and UAV-03 are out of ammo and disengaged. USVs track the high-threat surface boat-05."
}
```

## 调用 103（tick 1030）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.command.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5221.0, 19151.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3085.0, 2917.0]}, "priority": 0.2},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7006.0, -3891.0]}, "priority": 0.4},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1538.0, 2436.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-08 is the only armed unit with can_intercept=true for the high-threat comms-03 (dist 9816m, closing). UAV-06 and UAV-07 are assigned to the highest threat fuel-02 (dist ~16km, approaching) to prepare for engagement as it closes. UAV-02 is assigned to comms-02 (dist 12647m, approaching) as the next priority. UAV-01 is on patrol as it is too far to engage current threats effectively. UAV-03 and UAV-04 are out of ammo and disengaging to rear anchors. USVs are holding position for sensor coverage."
}
```

## 调用 104（tick 1040）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5258.0, 19335.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3172.0, 3115.0]}, "priority": 0.2},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.6}
  ],
  "reasoning": "UAV-04 and UAV-03 are out of ammo; disengaging them to conserve resources and avoid infeasible intercepts. UAV-08 is closest to the high-threat Comms-02 (can_intercept=true) and assigned to intercept. UAV-06 and UAV-07 are assigned to the approaching Fuel threats (Fuel-03 and Fuel-02) which are closing on the zone. UAV-02 is assigned to Comms-04 to maintain coverage on the second Comms threat. USVs are tasked with tracking to maintain sensor fusion on the primary threats."
}
```

## 调用 105（tick 1050）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5285.0, 19536.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3304.0, 3282.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7108.0, -3965.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1487.0, 2505.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 is assigned to intercept strike-comms-02, which is approaching and within feasible range (46t). UAV-06 and UAV-07 are assigned to intercept strike-fuel-02 and strike-fuel-03 respectively, as they are high-threat targets approaching the zone. UAV-02 is assigned to intercept strike-command-04, which is feasible and approaching. UAV-01, UAV-03, UAV-04, USV-01, and USV-02 are on patrol or hold as they are either out of range, out of ammo, or not the primary interceptors for the current high-priority threats."
}
```

## 调用 106（tick 1060）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 60},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 60},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.5, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5301.0, 19738.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-04 is out of ammo but has can_intercept=true on Comms-02/03; UAV-08 is the closest armed unit to Comms-02 (feasible_eta=47t) and is assigned to intercept it. UAV-02 is assigned to Command-02 (closest feasible target for it). UAV-06 and UAV-07 are assigned to Fuel-02 and Fuel-03 respectively, as they are the closest armed units to these high-threat targets. UAV-04, USV-01, and USV-02 are assigned to track their respective closest contacts to maintain sensor coverage. UAV-01 and UAV-03 are on patrol as they are far from the immediate threat axis and have no feasible intercepts."
}
```

## 调用 107（tick 1070）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5312.0, 19939.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3722.0, 3371.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7211.0, -4043.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1445.0, 2582.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 is the only armed unit with can_intercept=true for the high-threat comms-03 (dist 9952m, closing). Assigning it to intercept. UAV-06 and UAV-07 are positioned to intercept the approaching fuel-02 and fuel-03 threats (dist ~15km, closing fast) before they reach the zone. UAV-02 is assigned to intercept command-04 (dist 13km, feasible). UAV-01, UAV-03, UAV-04, USV-01, and USV-02 are out of range or out of ammo, so they hold position to maintain sensor coverage and readiness."
}
```

## 调用 108（tick 1080）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.command.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.command.intruder.strike-comms-02"}, "priority": 0.7, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.6, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.3},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14074.0, 13009.0]}, "priority": 0.3},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3933.0, 3424.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-08 is the only armed unit with can_intercept=true for the comms cluster (comms-04 is closest to zone and approaching). UAV-06 and UAV-07 are assigned to the high-threat fuel cluster (fuel-02 and fuel-03) which is approaching rapidly from the west; although can_intercept is false, they are the closest armed units and need to maneuver into position. USVs track the comms and fuel clusters to maintain sensor coverage. UAV-01 and UAV-02 hold position as they are too far to engage the immediate threats. UAV-03 and UAV-04 are out of ammo and disengaged."
}
```

## 调用 109（tick 1090）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 200},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4149.0, 3389.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7316.0, -4116.0]}, "priority": 0.3, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1403.0, 2658.0]}, "priority": 0.3, "deadline": 100}
  ],
  "reasoning": "UAV-08 is the only armed unit observing the high-threat comms-02 (threat 0.89) which is approaching the zone (dist 4731m). Assigning intercept. UAV-06 and UAV-07 are assigned to the two highest-threat fuel targets (0.91, 0.90) which are approaching from the east (bearing ~105-107) and have the shortest time-to-weapon-range among the remaining threats. UAV-02 is assigned to the command target (0.74) which is receding but still a threat. UAV-04 and UAV-03 are out of ammo and disengaged. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 110（tick 1100）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_fuel_03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_comms_02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "patrol_uav_01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14230.0, 13110.0]}, "priority": 0.5},
    {"task_id": "disengage_uav_03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.2},
    {"task_id": "disengage_uav_04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4357.0, 3430.0]}, "priority": 0.2},
    {"task_id": "patrol_usv_01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7369.0, -4152.0]}, "priority": 0.4},
    {"task_id": "patrol_usv_02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1378.0, 2693.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-06 and UAV-07 are assigned to the two highest-threat fuel targets (0.91, 0.85) which are approaching the zone from the East (bearing ~105). UAV-08 is assigned to the Comms-02 target (0.89) which is also approaching. UAV-04 and UAV-03 are out of ammo and disengaging. UAV-01 and UAV-02 are holding position as they are too far to engage the current high-priority threats effectively before they reach the zone, and the targets they see are either receding or have lower threat levels than the fuel targets."
}
```

## 调用 111（tick 1110）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4567.0, 3412.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7422.0, -4187.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1356.0, 2730.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-06 and UAV-07 are assigned to the two highest-threat fuel intruders (0.92) which are approaching and have the shortest time-to-weapon-range (TTR ~130-160t). UAV-08 is assigned to Comms-02 (0.90) which is receding but close to the zone; UAV-01 is assigned to the same target as a secondary/backup since it is also in range and has ammo. UAV-02 is assigned to Command-04 (0.74) to maintain coverage on the command element. UAV-03 and UAV-04 have 0 ammo and are disengaged to conserve resources/return to base. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 112（tick 1120）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1125},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 1130},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 1130},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 1140},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4779.0, 3358.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7475.0, -4223.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1331.0, 2764.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for a high-threat target (strike-comms-04) and is assigned to engage it immediately. UAV-06 and UAV-07 are assigned to the two highest-threat approaching targets (strike-fuel-02 and strike-fuel-03) which are closing on the protected zone; although can_intercept is currently false, they are the closest feasible interceptors and need to maneuver into position. UAV-02 is assigned to strike-command-04 as it is the only unit with a feasible intercept path for that target. UAV-01, UAV-03, and UAV-04 are held in patrol/loiter positions as they are either out of ammo (UAV-03, UAV-04) or too far from the immediate threat axis to be effective interceptors (UAV-01). USVs are held in position for sensor coverage."
}
```

## 调用 113（tick 1130）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 1150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 1150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 1150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02"}, "priority": 0.7, "deadline": 1150},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 1150},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4995.0, 3346.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.4, "deadline": 1150}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for a target (strike-comms-04) and is assigned to engage it. UAV-06 and UAV-07 are assigned to the highest threat approaching targets (strike-fuel-02 and strike-fuel-03) which are closing fast and will soon be in range; intercepting now allows them to maneuver into position. UAV-02 is assigned to strike-command-04 which is feasible and approaching. USVs are used for tracking as they are sensors only (or have low ammo/role). UAV-04 and UAV-03 have 0 ammo and are disengaged to conserve resources or return to base. UAV-01 is on patrol as it is far from the immediate threat axis and has no feasible intercepts."
}
```

## 调用 114（tick 1140）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [5211.0, 3333.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14810.0, 13549.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-06, 07, and 08 are assigned to intercept the three highest-threat incoming targets (strike-fuel-02, strike-comms-02, strike-fuel-03) which are approaching the protected zone from the east/north-east. UAV-04 and UAV-03 have 0 ammo and are disengaged to conserve resources and avoid infeasible intercept goals. USVs are tasked with tracking to maintain sensor coverage on the remaining contacts. UAV-01 and 02 are on patrol as they are too far to engage the current immediate threats effectively."
}
```

## 调用 115（tick 1150）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [5411.0, 3267.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "UAV-06 and UAV-07 are the closest armed units to the high-threat fuel intruders (02 and 03) which are approaching the zone; assigning them to intercept. UAV-08 is assigned to intercept comms-04 which is within its feasible range. UAV-01 and UAV-02 are assigned to intercept the same high-threat fuel intruders as secondary coverage since they are also approaching and the primary interceptors may need backup or may be out of position. UAV-03 and UAV-04 have 0 ammo and are disengaged to conserve resources and avoid infeasible goals. USVs are tracking their respective observed contacts to maintain sensor coverage."
}
```

## 调用 116（tick 1160）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.98, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [5614.0, 3198.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [7680.0, -4365.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.3},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15069.0, 13818.0]}, "priority": 0.3}
  ],
  "reasoning": "UAV-06 and UAV-07 are the only units with ammo and feasible ETAs to engage the high-threat fuel intruders (strike-fuel-02 and strike-fuel-03) before they reach the protected zone. UAV-08 is assigned to strike-comms-02 as it is the closest interceptor to that target and has ammo. UAV-03, UAV-04, and USV-01 are out of ammo and disengaged to conserve resources or return to base. USV-02 tracks the comms intruder it observes. UAV-01 and UAV-02 hold position as they are too far to engage the current high-priority threats effectively."
}
```

## 调用 117（tick 1170）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5314.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15192.0, 13956.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [5830.0, 3181.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.6}
  ],
  "reasoning": "UAV-06, 07, and 08 are the only armed units with feasible intercept paths to the high-threat fuel/comms intruders (strike-fuel-02, strike-fuel-03, strike-comms-02) which are approaching the protected zone. UAV-04 has 0 ammo and is disengaged despite can_intercept=true for command intruders, as it cannot fire. UAV-03 has 0 ammo and is disengaged. UAV-01 and 02 are on patrol as their targets are receding and far away. USVs are tracking their respective contacts for sensor fusion."
}
```

## 调用 118（tick 1180）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7330.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [6028.0, 3268.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "UAV-06 and UAV-07 are closest to the high-threat fuel intruders (strike-fuel-02/03) which are approaching the zone (dist_zone < 500m) and have prepare_intercept signals via closing speed. UAV-08 and UAV-01 are assigned to strike-comms-03 (high threat, receding but close). UAV-02 assigned to strike-fuel-04. UAV-03 and UAV-04 have 0 ammo and are disengaged to rear anchors. USVs continue tracking for sensor fusion."
}
```

