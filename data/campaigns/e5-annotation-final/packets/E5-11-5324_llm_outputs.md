# 案例 E5-11-5324 — LLM 规划器原始输出

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
    {"task_id": "ambush_boat01_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "standoff_m": 1000}, "priority": 0.95, "deadline": 100},
    {"task_id": "ambush_boat02_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "standoff_m": 1000}, "priority": 0.95, "deadline": 100},
    {"task_id": "ambush_boat03_003", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-03", "standoff_m": 1000}, "priority": 0.95, "deadline": 100},
    {"task_id": "track_boat01_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.8, "deadline": 100},
    {"task_id": "track_boat02_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02"}, "priority": 0.8, "deadline": 100},
    {"task_id": "track_boat03_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-03"}, "priority": 0.8, "deadline": 100},
    {"task_id": "patrol_uav01_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4132.0, 1621.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_uav02_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [6036.0, 1648.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_uav04_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3902.0, -119.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_uav05_010", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6124.0, -37.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_uav07_011", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3997.0, -1693.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_uav08_012", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5976.0, -1366.0]}, "priority": 0.5, "deadline": 100}
  ],
  "reasoning": "Three high-threat surface intruders (boats 01-03) are approaching the protected zone. UAVs 09, 06
```

## 调用 2（tick 20）

```
{
  "goal_commands": [
    {"task_id": "barrier_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-01", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_002", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-02", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_003", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-03", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_004", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-04", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_005", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-05", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_006", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-06", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_007", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-07", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_008", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-08", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_009", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-09", "axis_deg": 105, "radius_m": 8000}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1566.0, -542.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2599.0, -1467.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1402.0, -2378.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are far (dist_zone > 7km) and closing slowly. UAVs are positioned to form a barrier on the threat axis (105 deg) to intercept incoming boats and aircraft before they reach the protected zone. USVs hold position to maintain sensor coverage."
}
```

## 调用 3（tick 30）

```
{
  "goal_commands": [
    {"task_id": "barrier_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-01", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_002", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-02", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_003", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-03", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_004", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-04", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_005", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-05", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_006", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-06", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_007", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-07", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_008", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-08", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_009", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-09", "axis_deg": 105, "radius_m": 6000}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1620.0, -579.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2585.0, -1429.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1385.0, -2356.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are far (dist_zone > 7km) and closing slowly. Establishing a barrier screen on the threat axis (105 deg) with all interceptors to intercept threats before they reach the protected zone boundary. USVs maintain sensor coverage."
}
```

## 调用 4（tick 40）

```
{
  "goal_commands": [
    {"task_id": "barrier_001", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-01", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_002", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-02", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_003", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-03", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_004", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-04", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_005", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-05", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_006", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-06", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_007", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-07", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_008", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-08", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "barrier_009", "goal_type": "barrier", "parameters": {"unit_id": "defender.uav-09", "axis_deg": 105, "radius_m": 5000}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1677.0, -616.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2569.0, -1387.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1364.0, -2330.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are far (dist_zone > 7km) and closing slowly. Establishing a barrier screen on the threat axis (105 deg) with all UAVs to detect and engage early. USVs hold position to maintain sensor coverage."
}
```

## 调用 5（tick 50）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_boat_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 150},
    {"task_id": "intercept_boat_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4507.0, 2282.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3301.0, -748.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6903.0, 189.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3650.0, -2492.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5739.0, -821.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8569.0, -682.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1733.0, -654.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2555.0, -1344.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1343.0, -2301.0]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat surface intruders (boats 01-03) are approaching the protected zone. UAV-05, UAV-03, and UAV-02 are assigned to intercept them respectively, as they are the closest armed units to their targets and have feasible interception windows. The air targets are currently far away (dist > 12km) with no immediate threat (prepare_intercept=false), so remaining UAVs hold position to conserve energy and maintain coverage."
}
```

## 调用 6（tick 60）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4624.0, 2441.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3113.0, -858.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6656.0, 214.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3587.0, -2709.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5681.0, -685.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8709.0, -525.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1791.0, -691.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2536.0, -1303.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1319.0, -2273.0]}, "priority": 0.5}
  ],
  "reasoning": "Three surface intruders (boat-01, boat-02, boat-03) are the highest threats (0.78-0.81) and are closest to the protected zone. UAV-05, UAV-03, and UAV-02 are already assigned to them and are the closest interceptors to their respective targets. The air targets (strike-comms, strike-fuel, strike-command) are much further away (20km+) and have lower threat levels (0.32-0.48) with no prepare_intercept flags, so they do not require immediate engagement. Remaining UAVs and USVs are held in patrol to maintain sensor coverage and readiness for the air wave or additional surface threats."
}
```

## 调用 7（tick 70）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4731.0, 2607.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2970.0, -1022.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6411.0, 242.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3610.0, -2929.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5622.0, -549.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8842.0, -363.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1849.0, -728.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2515.0, -1262.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1295.0, -2245.0]}, "priority": 0.5}
  ],
  "reasoning": "Maintaining intercept assignments for the three surface intruders (boat-01, boat-02, boat-03) which are the highest threat (0.79-0.83) and closest to the protected zone. Although can_intercept is currently false, the targets are approaching and the assigned UAVs are the closest observers. Other UAVs are held in patrol to conserve ammunition and maintain coverage against the distant air threats (strike-comms, strike-fuel, strike-command) which have low threat levels and long ETAs."
}
```

## 调用 8（tick 80）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4832.0, 2778.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2785.0, -1135.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [6164.0, 253.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3621.0, -3152.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5565.0, -413.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-09", "position": [8974.0, -201.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1905.0, -765.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2496.0, -1220.0]}, "priority": 0.5},
    {"task_id": "patrol_009", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1272.0, -2217.0]}, "priority": 0.5}
  ],
  "reasoning": "Maintaining intercept assignments for the three surface intruders (boat-01, boat-02, boat-03) which are the closest threats to the protected zone. Although can_intercept is currently false, the targets are approaching and the assigned UAVs are the closest observers. Other UAVs are holding position to conserve ammunition and maintain coverage of the air threats (strike-comms, strike-fuel, strike-command) which are currently far away (dist > 12km) and not yet in the intercept window."
}
```

## 调用 9（tick 90）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4940.0, 2942.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2606.0, -1236.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5918.0, 264.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3457.0, -3261.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5509.0, -275.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1963.0, -801.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2476.0, -1178.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1250.0, -2189.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it is the closest air threat (dist 10858m, ttr 64t) and observed by UAV-09. The surface boats (boat-01, boat-02, boat-03) are high-threat (0.80-0.83) and approaching the zone; UAV-05, UAV-03, and UAV-02 continue their intercepts as they are the designated observers and closest interceptors. Other UAVs and USVs hold position to maintain sensor coverage and reserve readiness, as no other targets are within immediate intercept range or observed by them."
}
```

## 调用 10（tick 100）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-07.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2400.0, -1289.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5671.0, 280.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3259.0, -3372.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5454.0, -139.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2020.0, -838.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2456.0, -1136.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1227.0, -2162.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the closest high-threat air target. UAV-01 is assigned to intercept strike-comms-01 as it also has prepare_intercept=true and is the next highest threat. The surface boats (boat-01, boat-02, boat-03) are high-threat (0.78-0.83) and are being tracked by their respective assigned UAVs (UAV-05, UAV-03, UAV-02) which
```

## 调用 11（tick 110）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 130},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 130},
    {"task_id": "track_boat01_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.85, "deadline": 130},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02"}, "priority": 0.85, "deadline": 130},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-03"}, "priority": 0.85, "deadline": 130},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2187.0, -1303.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5425.0, 303.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [3042.0, -3350.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5398.0, -5.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2077.0, -876.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2435.0, -1095.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1203.0, -2136.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the highest threat air target. UAV-02 is assigned to intercept strike-comms-01 as it also has prepare_intercept=true. The surface boats (boat-01, boat-02, boat-03) are high threat but currently outside the effective intercept window for the assigned UAVs (can_intercept=false, prepare_intercept=false), so they are being tracked to maintain observation and prepare
```

## 调用 12（tick 120）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "track_boat01_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5193.0, 3479.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1968.0, -1304.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [5180.0, 327.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2840.0, -3242.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2135.0, -913.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2414.0, -1054.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1178.0, -2109.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-09 is assigned to intercept strike-fuel-01 as it has prepare_intercept=true and is the closest high-threat air target. UAV-08 is assigned to intercept strike-comms-01 (observed by
```

## 调用 13（tick 130）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-08.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-09.intruder.boat-02"}, "priority": 0.8, "deadline": 150},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.command.intruder.boat-01"}, "priority": 0.8, "deadline": 150},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.command.intruder.boat-03"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4934.0, 347.0]}, "priority": 0.5, "deadline": 150},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2655.0, -3111.0]}, "priority": 0.5, "deadline": 150},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5287.0, 262.0]}, "priority": 0.5, "deadline": 150},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2191.0, -950.0]}, "priority": 0.5, "deadline": 150},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2392.0, -1012.0]}, "priority": 0.5, "deadline": 150},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1153.0, -2081.0]}, "priority": 0.5, "deadline": 150}
  ],
  "reasoning": "UAV-09 and UAV-02 are assigned to intercept strike-comms-01 as it has prepare_intercept=true and is the closest air threat to the zone. UAV-05 is assigned to intercept strike-fuel-01 which also has prepare_intercept=true. UAV-03, UAV-01, and UAV-04 are tracking the surface boats to maintain sensor coverage and prepare for engagement if they breach the zone
```

## 调用 14（tick 140）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.usv-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 160},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 170},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1569.0, -1124.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4689.0, 371.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2446.0, -3026.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5232.0, 395.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2250.0, -987.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2371.0, -970.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1128.0, -2054.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is closest to strike-comms-01 (prepare=true, ttr=10.7) and assigned to intercept. UAV-05 is closest to strike-fuel-01 (prepare=true, ttr=44.3) and assigned to intercept. UAV-02 is closest to boat-01 (prepare=true, ttr=37.8) and assigned to intercept. UAV-03 is closest to boat-02 (ttr=85.1) and assigned to intercept. UAV-01 is closest to boat-
```

## 调用 15（tick 150）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 152},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-07.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 193},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 226},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 276},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 373},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1381.0, -1024.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4443.0, 395.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2231.0, -2949.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5177.0, 528.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2308.0, -1023.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2350.0, -927.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1103.0, -2027.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is assigned to strike-comms-01 as it is the closest threat to weapon range (range_gap 84m, prepare_intercept=true). UAV-05 is assigned to strike-fuel-01 (range_gap 1717m, prepare_intercept=true). The surface boats are high-threat (0.81-0.84) and approaching the zone; UAV-02, UAV-03, and UAV-01 are assigned to intercept boat-01, boat-02, and boat-03 respectively to prevent them from
```

## 调用 16（tick 160）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 180},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 180},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-09.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5390.0, 4247.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1233.0, -865.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [4197.0, 420.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [2021.0, -2879.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5122.0, 660.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2366.0, -1059.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2330.0, -885.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1078.0, -1999.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 has can_intercept=true for strike-comms-01, so it engages immediately. UAV-05 has prepare_intercept=true for strike-fuel-01 (range_gap=1200m, ttr=23t), so it begins intercept now. UAV-02 and UAV-03 both have prepare_intercept=true for strike-comms-01 (range_gap ~1500m, ttr ~26-33t); assigning them provides redundancy for this high-threat air target. Surface boats are far from the protected zone (dist_zone > 6700m) and have low closing
```

## 调用 17（tick 170）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-08.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 170},
    {"task_id": "intercept_strike_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 170},
    {"task_id": "intercept_boat_01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 170},
    {"task_id": "intercept_boat_02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 170},
    {"task_id": "intercept_boat_03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 170},
    {"task_id": "patrol_uav_04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [1099.0, -691.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3950.0, 439.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1796.0, -2838.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5069.0, 794.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2424.0, -1095.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2309.0, -842.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1053.0, -1972.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 is the only unit with can_intercept=true for the high-threat strike-fuel-01 (threat 0.60) and is assigned to engage it. UAV-02 is assigned to strike-comms-01 (threat 0.55) as it has prepare_intercept=true and is
```

## 调用 18（tick 180）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-09", "target_id": "sensor.contact.defender.uav-09.intruder.strike-fuel-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 180},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 180},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-06.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5456.0, 4643.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [952.0, -532.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3703.0, 454.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1581.0, -2768.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [5017.0, 927.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2484.0, -1130.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2291.0, -799.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1029.0, -1944.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-09 has can_intercept=true for strike-fuel-01 (observed by self), so it engages immediately with a salvo to maximize kill probability on the highest-threat air target. UAV-02 and UAV-03 are assigned to intercept strike-comms-01 (observed by UAV-06, but UAV-02/03 are closest and have prepare_intercept=true) to cover the second air threat. UAV-05 is assigned to intercept strike-fuel-01 (observed by USV-02, but UAV-05 is closest and has prepare_intercept=true) to cover the third air threat. Remaining UAVs
```

## 调用 19（tick 190）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat1_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_boat2_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_boat3_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 180},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5494.0, 4839.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [842.0, -342.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [3457.0, 473.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [1385.0, -2654.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4964.0, 1060.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2271.0, -756.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [1004.0, -1916.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-05 is in weapon range of strike-fuel-01 (can_intercept=true) and engages it. UAV-02 is assigned to strike-comms-01 (prepare_intercept=true, ttr=4.1) to intercept before it enters range. USV-01 engages boat-01 (can_intercept=true, high threat 0.85
```

## 调用 20（tick 200）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-03.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_008", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-03.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "UAV-02 and UAV-05 have can_intercept=true for strike-comms-01 and strike-fuel-01 respectively, so they are assigned to intercept immediately. UAV-03, UAV-01, and UAV-08 have prepare_intercept=true for strike-comms-01, so they are assigned to intercept to maneuver into position. UAV-04, UAV
```

## 调用 21（tick 210）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.65, "deadline": 180},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.6, "deadline": 180},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6278.0, -4113.0]}, "priority": 0.5, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2655.0, -1241.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2243.0, -666.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [954.0, -1860.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-02 and UAV-03 are assigned to the high-threat 'strike-comms-01' which is currently in the intercept window (can_intercept=true) and approaching the zone. UAV-08 and UAV-01 are tasked with 'strike-fuel-01' (high threat, approaching). The remaining UAVs (04, 06, 07) are assigned to the lower-threat 'strike-command-01' to maintain coverage. UAV-05 is disengaged as it has 0 ammo.
```

## 调用 22（tick 220）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6246.0, -4317.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [972.0, 292.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [2719.0, 521.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [844.0, -2237.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2713.0, -1277.0]}, "priority": 0.3, "deadline": 100},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2229.0, -621.0]}, "priority": 0.3, "deadline": 100},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [930.0, -1832.0]}, "priority": 0.3, "deadline": 100}
  ],
  "reasoning": "UAV-02 is in range of strike-comms-01 (can_intercept=true) and is assigned to engage. UAV-08 is assigned to strike-fuel-01 (prepare_intercept=true, high threat) to intercept before it reaches the zone. UAV-01 and UAV-03 are assigned to strike-comms-01 as secondary interceptors to ensure kill probability and cover the high-threat air target. UAV-05 has 0 ammo and is disengaging. Other units hold position to maintain sensor coverage and reserve readiness."
}
```

## 调用 23（tick 230）

```
{
  "goal_commands": [
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.facility.pier.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.command.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [5468.0, 5446.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav03_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-03", "position": [7877.0, 7053.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6195.0, -4517.0]}, "priority": 0.1},
    {"task_id": "track_boat01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-02.intruder.boat-01"}, "priority": 0.5},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.command.intruder.boat-03"}, "priority": 0.5}
  ],
  "reasoning": "UAV-02 is assigned to intercept strike-comms-01 as it is the only unit with can_intercept=true for this high-threat air target. UAV-08, 06, 07, and 04 are assigned to intercept the four surface boats (boat-02, boat-01, boat-03, boat-04) respectively, as they are the closest armed units to these high-threat surface contacts and can engage them before they reach the protected zone. UAV-01 and UAV-03 are held in reserve to cover the air threat if UAV-02 fails or to
```

## 调用 24（tick 240）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_008", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_009", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6242.0, -4717.0]}, "priority": 0.1, "deadline": 120}
  ],
  "reasoning": "UAV-02 and UAV-08 have can_intercept=true for strike-comms-01; UAV-01 has prepare_intercept=true and is assigned as backup. Surface threats boat-01 and boat-02 are high priority; UAV-06, UAV-04, UAV-07, USV-02, and USV-03 are assigned to boat-01 (closest to zone), while UAV-03 is assigned to boat-02. UAV-05 has 0 ammo and is disengaged."
}
```

## 调用 25（tick 250）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 90},
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "standoff_m": 500}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [499, 572]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [467, -1683]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7877, 7053]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6256, -4924]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.6},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01"}, "priority": 0.6}
  ],
  "reasoning": "UAV-08 and UAV-06 are closest to boat-02 and boat-01 respectively, which are approaching the zone (prepare_intercept=true). UAV-01 is assigned to boat-04 (prepare_intercept=true) as it is the closest armed unit to that contact. UAV-02 is assigned to ambush the air target strike-command-01 to conserve ammo and position for a high-probability kill. USVs are tracking the primary surface threats to maintain sensor coverage. UAV-05 is disengaging due to 0 ammo."
}
```

## 调用 26（tick 260）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.pier.intruder.boat-01"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-01"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "ambush_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 300},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7890, 7278]}, "priority": 0.2, "deadline": 600},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6188, -5117]}, "priority": 0.2, "deadline": 600},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [840, -1722]}, "priority": 0.4, "deadline": 600}
  ],
  "reasoning": "Immediate threat: boat-01 and boat-02 are approaching the protected zone (dist < 6km) and have can_intercept=true for USVs. USV-01 and USV-
```

## 调用 27（tick 270）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 90},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-01"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-01"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-04"}, "priority": 0.60, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-command-01"}, "priority": 0.50, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7928.0, 7527.0]}, "priority": 0.10, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6105.0, -5312.0]}, "priority": 0.10, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.boat-01"}, "priority": 0.40, "deadline": 120}
  ],
  "reasoning": "UAV-08 and UAV-04 are assigned to intercept boat-02 and boat-01 respectively, as they have prepare_intercept=true and are closest to the protected zone. UAV-06 is assigned to intercept boat-03, which is approaching and has prepare_intercept=true. USVs are tracking boat-01 to maintain sensor coverage. UAV-01 and UAV-02 are tracking boat-04 and strike-command-01 respectively, as they are further away and not immediate threats. UAV-03 and UAV-05 are disengaging due to zero ammo."
}
```

## 调用 28（tick 280）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5600, 6024]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [8955, 5970]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7918, 7777]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6064, -5477]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-135, -1493]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3045, -1487]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2149, -355]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808, -1686]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04, UAV-06, and UAV-08 are assigned to intercept boat-02, boat-03, and boat-01 respectively, as they are the closest armed units to these high-threat surface contacts which are approaching the protected zone. UAV-01, UAV-02, and UAV-07 are held in patrol positions to monitor the distant air threat (strike-command-01) and provide backup. UAV-03 and UAV-05 are disengaged due to zero ammunition. USVs are held in position to maintain sensor coverage."
}
```

## 调用 29（tick 290）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-03.intruder.boat-01"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-01.intruder.boat-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.8, "deadline": 200},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.8, "deadline": 200},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-03.intruder.boat-04"}, "priority": 0.7, "deadline": 150},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7950.0, 8025.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5951.0, -5651.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3099.0, -1522.0]}, "priority": 0.6},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2138.0, -310.0]}, "priority": 0.6},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.6}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-01 and boat-02 respectively, as they have prepare_intercept=true and are closest to the protected zone. UAV-08 is assigned to boat-03 to maintain coverage. UAV-01 and UAV-02 are tasked with the air threat strike-command-01, which is approaching but still far. UAV-07 is assigned to boat-04 to monitor its receding movement. UAV-03 and UAV-05 are disengaged due to zero ammunition. USVs are holding position to maintain sensor coverage."
}
```

## 调用 30（tick 300）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-05"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "intruder.strike-command-01"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "intruder.boat-03"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.boat-01"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.4, "deadline": 120},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-01"}, "priority": 0.4, "deadline": 120},
    {"task_id": "track_008", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-01"}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "Boat-01 and Boat-02 are the highest threat surface contacts with prepare_intercept=true and are approaching the protected zone. UAV-04 and UAV-06 are the closest armed interceptors to these targets and are assigned to intercept them immediately. Boat-03 is also a high threat; UAV-08 is assigned to intercept it. Other armed units (UAV-01, UAV-02) are tracking other surface contacts (Boat-04, Boat-05) to maintain observation. Sensor-only units (UAV-03, UAV-05, UAV-07, USVs) are tracking the primary threats to provide continuous sensor data, as they cannot fire."
}
```

## 调用 31（tick 310）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5752.0, 6625.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9069.0, 6332.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8034.0, 8510.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5843.0, -6058.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-719.0, -1335.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3206.0, -1592.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2124.0, -221.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04, UAV-06, and UAV-08 are assigned to intercept the three surface intruders (boat-02, boat-02, boat-01) which are currently approaching the protected zone and have prepare_intercept=true. UAV-04 is closest to boat-02 and boat-01, while UAV-06 and UAV-08 provide coverage for the other contacts. UAV-03 and UAV-05 have no ammunition and are disengaged to conserve resources. Other units are holding position to maintain sensor coverage and readiness for new threats."
}
```

## 调用 32（tick 320）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3258.0, -1629.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2117.0, -176.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8074.0, 8753.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5663.0, -6166.0]}, "priority": 0.1},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-920.0, -1420.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to intercept boat-02 and boat-01 respectively, as they are the closest threats with prepare_intercept=true and are within weapon range. UAV-06 is assigned to intercept boat-01 as a secondary threat. UAV-02 is assigned to intercept boat-04, which is approaching. UAV-01 is assigned to intercept strike-command-01, which is approaching but further away. USVs are patrolling to maintain sensor coverage. UAV-03 and UAV-05 are disengaging due to zero ammo. UAV-07 is patrolling as a reserve."
}
```

## 调用 33（tick 330）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5841.0, 6830.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8090.0, 8999.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5472.0, -6229.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1102.0, -1544.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3309.0, -1668.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2106.0, -131.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-01 and boat-02 respectively, as they have prepare_intercept=true and are the closest threats to the protected zone. UAV-08 is assigned to intercept boat-01 as well, providing redundancy. UAV-02 is assigned to intercept boat-04, which is also approaching. Other units are on patrol to maintain coverage and readiness."
}
```

## 调用 34（tick 340）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-05.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5912.0, 7013.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8118.0, 9246.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5298.0, -6342.0]}, "priority": 0.1},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1267.0, -1660.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3360.0, -1707.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2101.0, -90.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.5}
  ],
  "reasoning": "boat-01 and boat-02 are the highest threat (0.87/0.86) and are approaching the zone (dist ~5-6km). boat-01 has prepare_intercept=true for uav-04, so uav-04 is assigned to intercept it immediately. boat-02 has prepare_intercept=true for uav-04 as well, but uav-04 is committed to boat-01; uav-06 is assigned to boat-02 (closest armed unit with line of sight). uav-08 is assigned to boat-01 as a secondary interceptor to ensure kill probability if uav-04 fails or is delayed. uav-02 is assigned to boat-04 (threat 0.81) which is also approaching. uav-03 and uav-05 have 0 ammo and are disengaged to rear anchors. Remaining units hold position to maintain sensor coverage."
}
```

## 调用 35（tick 350）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-05", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8131.0, 9491.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5206.0, -6528.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03"}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-06 are closest to boat-01 and boat-02 respectively, which are approaching the zone (prepare_intercept=true). UAV-08 is assigned to boat-03 (receding but high threat) to maintain coverage. UAV-02 and UAV-01 are assigned to boat-04 and boat-05 (receding) to monitor and prepare for potential re-approach. UAV-03 and UAV-05 have 0 ammo and are disengaged to rear anchors. USVs are used for tracking to maintain sensor coverage on the primary threats."
}
```

## 调用 36（tick 360）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-05", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-1702.0, -1642.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8149.0, 9738.0]}, "priority": 0.3},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5075.0, -6696.0]}, "priority": 0.3},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3464.0, -1779.0]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2086.0, -1.0]}, "priority": 0.4},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 and UAV-06 are in immediate intercept range of the highest threat surface contacts (boat-01, boat-02) which are approaching the protected zone; UAV-04 uses salvo to maximize kill probability on the closest threat. UAV-08, UAV-02, and UAV-01 are assigned to intercept the remaining surface threats (boat-03, boat-04, boat-05) to prevent a 3+ intruder breach. UAV-07 is held in reserve near the objective. UAV-03 and UAV-05 have no ammunition and are disengaged. USVs are held in position to maintain sensor coverage."
}
```

## 调用 37（tick 370）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "intruder.boat-01"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "intruder.boat-02"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.strike-command-01"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6111.0, 7610.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9188.0, 7465.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8158.0, 9984.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4926.0, -6851.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-1897.0, -1739.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3515.0, -1818.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to intercept boat-01 and boat-02 respectively, as they are the closest threats with prepare_intercept=true and are approaching the protected zone. UAV-08 is assigned to intercept strike-command-01, which has prepare_intercept=true and is approaching. USV-02 and USV-03 are assigned to intercept boat-01 as they have can_intercept=true and are in position to engage. UAV-01 and UAV-02 are on patrol as their targets are receding or far away. UAV-03 and UAV-05 are disengaging due to 0 ammo. UAV-07 and USV-01 are on patrol as they are not in a position to engage the current threats effectively."
}
```

## 调用 38（tick 380）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.facility.command.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6165.0, 7815.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9252.0, 7642.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8169.0, 10233.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4890.0, -7060.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2020.0, -1891.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3569.0, -1854.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-06 are closest to the high-threat surface boats (boat-01, boat-02) which are approaching the zone; issuing intercept to engage before they cross. USV-02 and USV-03 are also in range of boat-01 and boat-02 respectively, providing layered defense. UAV-08 is assigned to the air threat (strike-command-01) as it is the closest armed unit to that target. UAV-03 and UAV-05 have no ammo and are disengaged. Remaining units hold position to maintain coverage."
}
```

## 调用 39（tick 390）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6212.0, 8021.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9316.0, 7819.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8175.0, 10482.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4815.0, -7261.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2221.0, -1962.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3620.0, -1892.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is closest to boat-01 (dist 3115m) and has prepare_intercept=true, so it is assigned to intercept. UAV-08 is the observer for strike-command-01 and has prepare_intercept=true (ttr 39.1), so it is assigned to intercept. USV-02 is currently tracking strike-command-01 and has can_intercept=true for boat-01 and boat-02, but since UAV-04 is closer to boat-01, USV-02 continues to track the air threat. USV-03 has prepare_intercept=true for boat-01 and is assigned to intercept as a secondary layer. UAV-06 is also close to boat-01 and assigned to intercept. UAV-01 and UAV-02 are far from the immediate threats and are placed
```

## 调用 40（tick 400）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6257.0, 8229.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9362.0, 8001.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8155.0, 10729.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4731.0, -7457.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2419.0, -2057.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3673.0, -1928.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2057.0, 178.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is assigned to intercept boat-01 (threat 0.88, prepare_intercept=true, closest to zone) with a salvo to ensure kill. UAV-08 is assigned to intercept strike-command-01 (threat 0.69, prepare_intercept=true, fast closing) to engage the air threat early. UAV-06 is assigned to intercept boat-02 (threat 0.86, prepare_intercept=true) to cover the second surface threat. Other units hold position to conserve ammo and maintain sensor coverage, as no other targets have prepare_intercept=true or are immediately critical."
}
```

## 调用 41（tick 410）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-01.intruder.boat-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6278.0, 8442.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9397.0, 8183.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8140.0, 10975.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4615.0, -7635.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2636.0, -2046.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-04 and UAV-06 are assigned to the two highest-threat surface intruders (boat-01 and boat-02) which are approaching the protected zone and have prepare_intercept=true. UAV-08 is assigned to the air strike-command which is approaching and has prepare_intercept=true. USV-02 and USV-03 are assigned to intercept boat-02 and boat-01 respectively, as they are in range and can engage. USV-01 is tracking boat-03 as it is a sensor-only unit. UAV-01, UAV-02, and UAV-07 are patrolling to maintain coverage. UAV-
```

## 调用 42（tick 420）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3776.0, -2003.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6272.0, 8656.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9443.0, 8366.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8140.0, 11219.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4515.0, -7827.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-2859.0, -2046.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 and USV-03 have can_intercept=true for boat-02 and boat-01 respectively, so they engage immediately. UAV-04 is closest to boat-01 (2776m) and has prepare_intercept=true, so it intercepts to support the USVs. UAV-08 is closest to the air threat (8607m) with prepare_intercept=true, so it intercepts the strike-command. UAV-06 is assigned to boat-02 as a secondary interceptor since it is within range and approaching. Other units hold position to conserve ammo and maintain coverage."
}
```

## 调用 43（tick 430）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 30},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02"}, "priority": 0.60, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02"}, "priority": 0.55, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6289.0, 8867.0]}, "priority": 0.40},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9516.0, 8542.0]}, "priority": 0.40},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8142.0, 11467.0]}, "priority": 0.30},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4406.0, -8016.0]}, "priority": 0.30}
  ],
  "reasoning": "Intruder boat-01 is the highest threat (0.90) and closest to the zone (4279m). It is observed by multiple units. usv-02 and usv-03 have can_intercept=true and are assigned to engage. uav-04 and uav-06 have prepare_intercept=true and are assigned to intercept to ensure coverage. Intruder strike-command-01 is approaching (ttr=12.6) and uav-08 is very close to weapon range (range_gap=339m), so it is assigned to intercept. Intruder boat-02 is receding/stable and further out; usv-01 (sensor) and uav-07 (armed but further) are assigned to
```

## 调用 44（tick 440）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6293.0, 9081.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9561.0, 8727.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [8169.0, 11713.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4200.0, -8054.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-3256.0, -2194.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3873.0, -2084.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the air threat (strike-command-01) and is assigned to engage it. UAV-04 and UAV-06 are assigned to the two surface threats (boat-01 and boat-02) which are approaching the protected zone and have prepare_intercept=true; they are the closest armed units to these targets. USV-02 is assigned to boat-03, which is approaching and within its sensor range, to maintain tracking and prepare for engagement if it becomes a threat. Other units are held in patrol to conserve ammunition and maintain coverage."
}
```

## 调用 45（tick 450）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6293.0, 9294.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9649.0, 8897.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8157.0, 11960.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4120.0, -8246.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [3925.0, -2121.0]}, "priority": 0.4},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [808.0, -1686.0]}, "priority": 0.4}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the air threat (strike-command-01) and is assigned to engage it. UAV-04 and UAV-06 are assigned to the two closest high-threat surface intruders (boat-01 and boat-02) which are within their weapon range and approaching the protected zone. UAV-07 is assigned to boat-04, which is also within range and approaching. USV-02 is assigned to boat-03, which is approaching and will soon be in range. UAV-01 and UAV-02 are held in reserve/patrol as they are too far to engage the current threats effectively. UAV-03 and UAV-05 are out of ammo and disengaged. USV-01 and USV-03 are held in position to maintain sensor coverage."
}
```

## 调用 46（tick 460）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6308.0, 9505.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9677.0, 9082.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8171.0, 12204.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [769.0, -2749.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4044.0, -8449.0]}, "priority": 0.2, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. UAV-06 and UAV-07 are assigned to intercept the two highest-threat surface targets (boat-01 and boat-02) which are approaching the protected zone and have prepare_intercept=true. USVs are used for tracking as they are sensors only (or have no ammo/low speed). UAV-03, UAV-04, and UAV-05 are disengaged/returned as they
```

## 调用 47（tick 470）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6324.0, 9716.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9705.0, 9268.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8163.0, 12451.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [3962.0, -8635.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-3862.0, -2342.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4022.0, -2200.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01), so it is assigned to intercept immediately. UAV-06 is assigned to boat-02 (threat 0.88) as it is the closest armed unit to that target and has prepare_intercept=true. USV-03 is assigned to boat-01 (threat 0.86) as it is the closest unit with can_intercept=true for that target. USV-02 is assigned to track/intercept strike-command-01 as a secondary sensor/engagement platform since it is close and has can_intercept=true. UAV-04 is assigned to boat-04 (threat 0.85) as it is the closest armed unit to that target. UAV-01, UAV-02, and UAV-07 are held in patrol positions to cover
```

## 调用 48（tick 480）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-05.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_boat04_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_boat05_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.70, "deadline": 60},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8146.0, 12695.0]}, "priority": 0.1},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [3914.0, -8834.0]}, "priority": 0.1},
    {"task_id": "disengage_usv01_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [4072.0, -2236.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. USV-02 is assigned to boat-01 (highest threat surface, can_intercept=true). UAV-06 is assigned to boat-02 (prepare_intercept=true, approaching). UAV-02 is assigned to boat-04 (prepare_intercept=true, approaching). UAV-04 is assigned to boat-03 (approaching, observed by UAV-04). UAV-07 is assigned to boat-05 (approaching, observed by UAV-07). UAV-03, UAV-05, and USV-01 have 0 ammo and are disengaged to conserve resources and avoid infeasible intercept goals."
}
```

## 调用 49（tick 490）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6296.0, 10132.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9823.0, 9627.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8100.0, 12940.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it. UAV-04 and UAV-06 are assigned to the two closest surface threats (boat-02 and boat-01) which are approaching the protected zone and have prepare_intercept=true. USV-02 and USV-01 are assigned to boat-01 and boat-04 respectively, as they are within sensor range and can provide close-in defense or tracking. UAV-07 and UAV-05 are assigned to track boat-03 and strike-command-01 respectively to maintain situational awareness. UAV-01 and UAV-02 are on patrol as they are too far to engage current threats effectively. UAV-03 has no ammo and is disengaging to return to base."
}
```

## 调用 50（tick 500）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6295.0, 10342.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [9892.0, 9809.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [8052.0, 13185.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4150.0, -9189.0]}, "priority": 0.2, "deadline": 120}
  ],
  "reasoning": "UAV-04 and UAV-08 are the only units with can_intercept=true for the high-threat air target (strike-command-01); both are assigned to engage it with 'assess' policy to conserve ammo. USV-02 has can_intercept=true for boat-02 and is assigned to engage it. USV-01, UAV-07, and UAV-06 are assigned to track their respective closest surface threats (boat-04, boat-01, boat-01) as they are approaching but not yet in intercept range for the specific observer or are being handled by others. UAV-01 and UAV-02 are on patrol as their targets are receding or far away. UAV-03 and UAV-05 have 0 ammo and are disengaged to rear anchors."
}
```

## 调用 51（tick 510）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "UAV-04 and UAV-08 are in intercept range for the high-threat air target (strike-command-01) and are assigned to engage it. USV-02 is in range for boat-02 and is assigned to intercept. Other units are assigned to track the closest high-threat surface targets (boat-01, boat-04, boat-03) to maintain sensor coverage and prepare for future engagement opportunities, as they are currently outside effective weapon range or the units are unarmed."
}
```

## 调用 52（tick 520）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6267.0, 10750.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10054.0, 10156.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7953.0, 13674.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4433.0, -9459.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4271.0, -2378.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to the air threat (strike-command-01) as both have can_intercept=true and are within range. UAV-06 and USV-02 are assigned to boat-01 (highest threat surface contact, can_intercept=true for USV-02, prepare_intercept=true for UAV-06). UAV-07 is assigned to boat-02 (prepare_intercept=true). Remaining units are on patrol to maintain coverage and conserve ammunition."
}
```

## 调用 53（tick 530）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 200},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 200},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7925.0, 13922.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4535.0, -9626.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [4324.0, -2414.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 have can_intercept=true for the high-threat air target (strike-command-01) and are assigned to engage it. UAV-06 and USV-02 are assigned to the high-threat surface target boat-01 (can_intercept=true for USV-02, prepare_intercept=true for UAV-06). UAV-07 is assigned to boat-02 (prepare_intercept=true). UAV-01 and UAV-02 are assigned to the air target as secondary interceptors to ensure coverage. UAV-03, UAV-05, and USV-01 have 0 ammo and are disengaged to conserve resources and avoid infeasible goals."
}
```

## 调用 54（tick 540）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6277.0, 11172.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10105.0, 10531.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7889.0, 14167.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4466.0, -9830.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4084.0, 4089.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is currently assigned to it; issuing intercept with salvo to maximize kill probability. UAV-06 and UAV-07 are assigned to the two closest high-threat surface targets (boat-01 and boat-02) which are approaching the zone; they have prepare_intercept=true or are in range. USV-02 is assigned to boat-03 which is approaching and within its sensor range, though it is a sensor-only unit (wait, USV-02 has ammo=2, so it is armed? The prompt says 'picket USVs (sensors only)' but the graph shows ammo=2 for usv-02. I will assume it can fire if ammo>0, or if it's strictly sensors only, I
```

## 调用 55（tick 550）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6290.0, 11384.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10155.0, 10716.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7860.0, 14412.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4407.0, -10037.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4431.0, -2480.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to the high-threat air target (strike-command-01) which is currently in the intercept window (can_intercept=true) and approaching. USV-02 and UAV-06 are assigned to the highest-threat surface target (boat-01) which is also in the intercept window. UAV-07 is assigned to boat-02, which is approaching and has prepare_intercept=true. Other units are holding position or patrolling as they are either out of range, out of ammo, or not currently assigned to a high-priority target."
}
```

## 调用 56（tick 560）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7841.0, 14659.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4374.0, -10251.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [4484.0, -2515.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 are in intercept range for the high-threat air command boat (can_intercept=true) and are assigned to engage it. USV-02 and UAV-06 are assigned to the high-threat surface boat-01 (can_intercept=true for USV-02, close range for UAV-06). UAV-07 is assigned to boat-02 (close range). UAV-01 and UAV-02 are assigned to boat-04 (prepare_intercept=true for UAV-08, but UAV-01/02 are closer to the threat axis). UAV-03, UAV-05, and USV-01 have 0 ammo and are disengaged to conserve resources and avoid infeasible goals."
}
```

## 调用 57（tick 570）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_boat04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-07.intruder.boat-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_boat05_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [6284.0, 11807.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [10215.0, 11094.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7816.0, 14904.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4341.0, -10452.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [4040.0, 4228.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat air target (strike-command-01) and is assigned to engage it with a salvo. UAV-06 and UAV-07 are assigned to the two highest-threat surface targets (boat-01 and boat-02) which are approaching the protected zone and have prepare_intercept=true. USV-02 is assigned to
```

## 调用 58（tick 580）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7792.0, 15150.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4325.0, -10661.0]}, "priority": 0.2},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4586.0, -2587.0]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6278.0, 12018.0]}, "priority": 0.3},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10214.0, 11286.0]}, "priority": 0.3}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to the high-threat air target (strike-command-01) which is currently in the intercept window (can_intercept=true) and approaching. UAV-06 and UAV-07 are assigned to the two closest high-threat surface targets (boat-01 and boat-02) which are approaching the protected zone. USV-02 is assigned to boat-01 as a secondary sensor/interceptor. UAV-03 and UAV-05 are out of ammo and disengaged. USV-01 is out of ammo and patrolling. UAV-01 and UAV-02 are patrolling as reserves."
}
```

## 调用 59（tick 590）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_strike_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_strike_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_boat_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_boat_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6271.0, 12229.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10227.0, 11479.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7770.0, 15393.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "disengage_uav_005", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4332.0, -10879.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6385.0, -2088.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "Strike-command-01 is the highest priority threat (air, threat 0.83, can_intercept=true for UAV-04, UAV-06, UAV-08). Assigning all three armed interceptors to engage it immediately to ensure destruction before it reaches the zone. Surface boats (boat-01, boat-02) are high threat but currently receding or stable; USVs are tracking them to maintain sensor lock. UAV-03 and UAV-05 are out of ammo and disengaging. Other UAVs are holding position to conserve fuel/position for potential new waves."
}
```

## 调用 60（tick 600）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6268.0, 12440.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10222.0, 11672.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7739.0, 15637.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4360.0, -11092.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6595.0, -2118.0]}, "priority": 0.5}
  ],
  "reasoning": "Strike-command-01 is the highest threat (0.88) and is approaching. UAV-04 is in range (can_intercept=true) and assigned to engage with a salvo to maximize kill probability. UAV-06 and UAV-08 are also in range and assigned to intercept the same target to ensure destruction, as it is the primary threat. Boat-01 is the closest surface threat (dist_zone=2768m) and is observed by USV-02, which is assigned to intercept it. USV-01 is assigned to intercept Boat-04, which is also in range. Other UAVs are holding position as they are out of range or have no ammo."
}
```

## 调用 61（tick 610）

```
{
  "goal_commands": [
    {"task_id": "intercept_strike_command_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 100},
    {"task_id": "intercept_strike_command_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_strike_command_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_boat_02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "track_boat_01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-05.intruder.boat-01"}, "priority": 0.7, "deadline": 100},
    {"task_id": "patrol_uav_01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6240.0, 12644.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_uav_02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10319.0, 11822.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_uav_03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7732.0, 15888.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "disengage_uav_05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4332.0, -11300.0]}, "priority": 0.4, "deadline": 100},
    {"task_id": "patrol_uav_07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-6811.0, -2101.0]}, "priority": 0.5, "deadline": 100}
  ],
  "reasoning": "Strike-command-01 is the highest threat (0.88) and is approaching the protected zone (dist 4831m). UAV-04, UAV-06, and UAV-08 all have can_intercept=true for this target. I am assigning all three to engage it to ensure a kill, as it is the primary threat to the zone boundary. UAV-04 is closest and gets 'salvo' for maximum immediate effect. The surface boats (boat-01, boat-02, boat-03, boat-04, boat-05) are also high threat but are currently receding or stable at distances >2.5km from the zone center. USV-02 is assigned to intercept boat-02 (approaching, threat 0.92) as it is the closest armed
```

## 调用 62（tick 620）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04"}, "priority": 0.80, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-01"}, "priority": 0.80, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6229.0, 12846.0]}, "priority": 0.50},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10457.0, 11955.0]}, "priority": 0.50},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7697.0, 16144.0]}, "priority": 0.50},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4251.0, -11492.0]}, "priority": 0.50},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7033.0, -2057.0]}, "priority": 0.50}
  ],
  "reasoning": "Strike-command-01 is the highest threat (0.90) and is currently within weapon range of UAV-04, UAV-06, and UAV-08 (can_intercept=true). UAV-04 is assigned to fire a salvo to maximize kill probability on this high-value target. UAV-06 and UAV-08 are assigned to intercept with an 'assess' policy to conserve ammunition while maintaining pressure. The surface boats (boat-01, boat-04) are receding and have lower threat levels; USVs are assigned to track them to maintain sensor coverage. Other UAVs are on patrol to monitor the remaining distant contacts (comms/fuel) which are not yet in the intercept window."
}
```

## 调用 63（tick 630）

```
{
  "goal_commands": [
    {"task_id": "intercept_command_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_command_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_command_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_uav_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6225.0, 13052.0]}, "priority": 0.5},
    {"task_id": "patrol_uav_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10597.0, 12084.0]}, "priority": 0.5},
    {"task_id": "disengage_uav_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7629.0, 16388.0]}, "priority": 0.2},
    {"task_id": "disengage_uav_005", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4126.0, -11653.0]}, "priority": 0.2},
    {"task_id": "patrol_uav_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7252.0, -1995.0]}, "priority": 0.5},
    {"task_id": "patrol_usv_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4853.0, -2759.0]}, "priority": 0.5}
  ],
  "reasoning": "Strike-command-01 is the highest threat (0.91) and is currently within intercept range of UAV-04, UAV-06, and UAV-08. UAV-04 is assigned to fire a salvo to maximize kill probability on this critical target. UAV-06 and UAV-08 are also assigned to intercept to provide backup and ensure engagement if the first shot fails. Boat-01 is the closest surface threat to the protected zone (2479m) and is within range of USV-02, which is assigned to intercept it. Other UAVs are held in patrol or disengaged to conserve ammunition and maintain sensor coverage, as the other threats are either far away or receding."
}
```

## 调用 64（tick 640）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6164.0, 13242.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10785.0, 12106.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7564.0, 16632.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3984.0, -11810.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-3429.0, -68.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-7435.0, -1864.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4910.0, -2791.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 are assigned to intercept the high-threat strike-command-01 which is currently in the intercept window (can_intercept=true) and approaching the protected zone. UAV-04 is closer and has a better angle, so it is prioritized with a salvo policy to maximize kill probability. UAV-08 provides backup. USV-02 is assigned to intercept boat-01, the closest surface threat to the zone. Other units are on patrol to maintain coverage and monitor the remaining contacts, which are currently receding or far away."
}
```

## 调用 65（tick 650）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.pier.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-3656.0, -37.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [3875.0, -11991.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7504.0, 16876.0]}, "priority": 0.5, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [4967.0, -2825.0]}, "priority": 0.4, "deadline": 300},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6086.0, 13422.0]}, "priority": 0.3, "deadline": 300},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [10971.0, 12162.0]}, "priority": 0.3, "deadline": 300}
  ],
  "reasoning": "Strike-command-01 is the highest threat (0.89) and is approaching the protected zone (dist 3030m). UAV-04 is in immediate range (can_intercept=true) and assigned to fire a salvo to maximize kill probability. UAV-07 is also in range (prepare_intercept=true) and assigned to intercept with assess policy to conserve ammo. UAV-08 is in range but receding; assigned to intercept as a backup. Boat-01 is a high threat (0.93) near the zone; USV-02 is assigned to intercept it. UAV-06, UAV-05, and UAV-03 have 0 ammo and are disengaged to rear anchors. USV-01 has 0 ammo and is patrolling to maintain sensor coverage. UAV-01 and UAV-02 are patrolling to maintain coverage of the northern sector where other threats are approaching."
}
```

## 调用 66（tick 660）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-01.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5998.0, 13601.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11147.0, 12231.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7424.0, 17114.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3787.0, -12177.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-3884.0, -7.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5025.0, -2858.0]}, "priority": 0.5}
  ],
  "reasoning": "strike-command-01 is the highest threat (0.91) and is currently within weapon range of uav-04, uav-08, and uav-06 (though uav-06 has no ammo). uav-04 is assigned to intercept with a salvo to maximize kill probability on this high-value target. uav-08 and uav-07 are also assigned to intercept the same target to ensure coverage and redundancy, as it is the primary threat. usv-02 is assigned to intercept boat-02 (threat 0.92) which is within its range and observed by uav-08 (but usv-02 is the only armed surface unit nearby with ammo). Other units are on patrol to maintain sensor coverage and readiness for emerging threats."
}
```

## 调用 67（tick 670）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-07.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-07.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5876.0, 13757.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11330.0, 12287.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7367.0, 17357.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3630.0, -12316.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-4115.0, 17.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5080.0, -2894.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3709m, receding). Assigning it with 'salvo' to maximize kill probability before it escapes. UAV-07 is preparing intercept (prepare_intercept=true) and is closer to the zone, so it is assigned to intercept the same target as a secondary/backup. USV-02 is assigned to intercept boat-01 (can_intercept=true, high threat 0.94, closest to zone). UAV-08 is assigned to intercept boat-02 (can_intercept=true, high threat 0.91). Other units are on patrol or hold as they are out of range or have no ammo (UAV-03, 05, 06, USV-01)."
}
```

## 调用 68（tick 680）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5763.0, 13918.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11513.0, 12340.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7287.0, 17595.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3482.0, -12459.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-4341.0, 59.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5137.0, -2928.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3883m, receding). It is assigned to engage with a salvo to maximize kill probability. UAV-08 and UAV-07 are also assigned to intercept the same target as they have can_intercept/prepare_intercept flags and are closer than other units, providing redundancy against this high-value target. USV-02 is assigned to intercept boat-01 (can_intercept=true, threat 0.95) and boat-03 (can_intercept=true, threat 0.91) as it is the only armed surface unit in range. Other UAVs are out of range or have no ammo (UAV-03, 05, 06) and are held in patrol to maintain sensor coverage."
}
```

## 调用 69（tick 690）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5668.0, 14089.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11705.0, 12362.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7233.0, 17841.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3370.0, -12632.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-4574.0, 74.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5195.0, -2961.0]}, "priority": 0.5}
  ],
  "reasoning": "strike-command-01 is the highest threat (0.95) and is currently inside the weapon envelope of uav-04 (can_intercept=true). uav-07 is also in a prepare_intercept state (range_gap 792m, closing fast) and should engage immediately. uav-08 is already assigned to this target and can_intercept=true, so it continues. usv-02 is assigned to boat-03 (can_intercept=true, threat 0.91) which is approaching the zone. Other units are out of range or out of ammo (uav-03, 05, 06) and are held in patrol to maintain sensor coverage."
}
```

## 调用 70（tick 700）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 10},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 30},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 30},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5562.0, 14258.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [11892.0, 12405.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [7175.0, 18082.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [3225.0, -12784.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-4805.0, 90.0]}, "priority": 0.1}
  ],
  "reasoning": "strike-command-01 is the highest threat (0.94) and is currently inside the weapon envelope of uav-04, uav-08, and uav-06 (though uav-06 has no ammo). uav-04 is closest and has ammo, so it is assigned a salvo for immediate engagement. uav-08 and uav-07 (which is preparing to intercept) are also assigned to engage the same high-value target to ensure a kill, as it is the primary threat to the protected zone. The surface boats (boat-01, boat-02) are also high threat and within range of the USVs; usv-02 and usv-01 are assigned to intercept them respectively. Other UAVs are either out of range, have no ammo, or are assigned to patrol/disengage to conserve resources for the immediate threats."
}
```

## 调用 71（tick 710）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.facility.pier.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.80, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5433.0, 14399.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [12080.0, 12395.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7093.0, 18319.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3075.0, -12926.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-5040.0, 102.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04, UAV-07, and UAV-08 are all within weapon range of the high-threat strike-command-01 (dist < 8000m, can_intercept=true). UAV-04 is closest (4036m) and assigned a salvo for immediate engagement. UAV-07 and UAV-08 are also in range and assigned to intercept with assess policy to conserve ammo if the first shot is effective. USV-02 and USV-01 are assigned to the closest surface threats (boat-01 and boat-05) which are within their 3000m range. Other UAVs are out of range of the primary threat or have no ammo, so they are held in patrol."
}
```

## 调用 72（tick 720）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5291.0, 14526.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [12272.0, 12395.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [7041.0, 18566.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [2958.0, -13105.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-5269.0, 135.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3282.0, 6248.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-07 are assigned to intercept the high-threat strike-command-01 which is currently in the intercept window (can_intercept=true) and approaching the protected zone. UAV-08 is held in patrol to conserve ammunition and maintain sensor coverage, as the target is already being engaged by two other units. USV-02 and USV-01 are assigned to intercept the surface threats boat-03 and boat-05 respectively, which are also in the intercept window. Other UAVs are held in patrol to maintain sensor coverage and conserve ammunition for potential future threats."
}
```

## 调用 73（tick 730）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5175.0, 14676.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6984.0, 18812.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [2846.0, -13286.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-5500.0, 195.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3225.0, 6375.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5407.0, -3090.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-07 are assigned to intercept the high-threat strike-command-01 (threat 0.97) which is currently within weapon range (can_intercept=true) and approaching the protected zone. UAV-02 is assigned to intercept strike-comms-04 (threat 0.48) as it has prepare_intercept=true and is the closest threat to the intercept window among the remaining air targets. USV-02 is assigned to intercept boat-03 (threat 0.91) which is within range and stable. Other units are on patrol to maintain coverage and conserve ammunition."
}
```

## 调用 74（tick 740）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.98, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.90, "deadline": 30},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.85, "deadline": 60},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03"}, "priority": 0.65, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-5733.0, 241.0]}, "priority": 0.50, "deadline": 60},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6905.0, 19049.0]}, "priority": 0.50, "deadline": 60},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2736.0, -13455.0]}, "priority": 0.50, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [5029.0, 14804.0]}, "priority": 0.40, "deadline": 120}
  ],
  "reasoning": "UAV-04 and UAV-07 are assigned to intercept the high-threat strike-command-01 which is currently in range (can_intercept=true) and approaching the protected zone. UAV-04 uses a salvo policy for immediate engagement, while UAV-07 uses assess to conserve ammo. USV-02 intercepts boat-04, which is in range and threatening the zone. USV-01 tracks boat-05 as it is receding and out of immediate firing range for the USV. UAV-02 and UAV-08 track the comms intruders which are approaching but not yet in intercept range. UAV-06, UAV-03, and UAV-05 are disengaged as they have 0 ammo and are not in a position to engage the primary threats effectively."
}
```

## 调用 75（tick 750）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4887.0, 14933.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6851.0, 19296.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [2595.0, -13615.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-5944.0, 345.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-8435.0, -1304.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [3110.0, 6626.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5503.0, -3143.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (dist 4304m, can_intercept=true) and must fire immediately to prevent zone entry. USV-02 is in range of boat-04 (dist 2344m, can_intercept=true) and should engage to prevent surface intrusion. UAV-02 has prepare_intercept=true for strike-comms-03 (dist 9832m, closing fast) and should begin intercept maneuvering now. Other units are out of range or have no ammo, so they hold position to maintain sensor coverage."
}
```

## 调用 76（tick 760）

```
{
  "goal_commands": [
    {"task_id": "intercept_cmd_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 50},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4734.0, 15047.0]}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6809.0, 19549.0]}, "priority": 0.2},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2532.0, -13819.0]}, "priority": 0.2},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-6169.0, 427.0]}, "priority": 0.2},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-8623.0, -1210.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [3059.0, 6753.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5560.0, -3179.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3918m, closing fast). It is assigned to intercept with a salvo to maximize kill probability. UAV-02 is assigned to intercept strike-comms-04 which has prepare_intercept=true and is closing rapidly (ttr 39t). USV-02 is assigned to intercept boat-03 which is within range and can_intercept=true. UAV-07 and UAV-08 are held in reserve to cover the protected zone against other threats. UAV-03, UAV-05, and UAV-06 have 0 ammo and are disengaged. UAV-01 and USV-01 are patrolling to maintain sensor coverage."
}
```

## 调用 77（tick 770）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4574.0, 15152.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6745.0, 19793.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [2453.0, -14018.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-6380.0, 537.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-8832.0, -1112.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [2997.0, 6876.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5618.0, -3213.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only armed unit with can_intercept=true for the high-threat strike-command-01 (dist 3924m, threat 0.98); assigned with salvo to maximize kill probability. USV-02 has can_intercept=true for boat-02 (dist 2388m, threat 0.93) and is the only unit with ammo capable of engaging surface targets; assigned with assess to conserve ammo. UAV-02 is assigned to continue intercepting strike-comms-04 (dist 9220m, threat 0.50) as it is the closest air threat to weapon range (range_gap 1220m) and maintains pressure on the air wave. Other units are out of range or out of ammo; maintaining patrol positions to preserve sensor coverage and readiness for future waves."
}
```

## 调用 78（tick 780）

```
{
  "goal_commands": [
    {"task_id": "intercept_command_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [4419.0, 15261.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-9045.0, -1028.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [2941.0, 7003.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.30},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2387.0, -14221.0]}, "priority": 0.30},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-6598.0, 622.0]}, "priority": 0.30},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5674.0, -3250.0]}, "priority": 0.40}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (can_intercept=true) and is assigned to engage with a salvo to neutralize the primary threat. UAV-02 is assigned to intercept strike-comms-04 (prepare_intercept=true) to prevent it from entering the zone. USV-02 is assigned to intercept boat-03 (can_intercept=true) to handle the surface threat. UAV-01, UAV-07, and UAV-08 are held in reserve to react to emerging threats. UAV-03, UAV-05, and UAV-06 are disengaged due to zero ammunition. USV-01 is patrolling to maintain sensor coverage."
}
```

## 调用 79（tick 790）

```
{
  "goal_commands": [
    {"task_id": "intercept_command_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 30},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [4277, 15384], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-9222, -890], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [2882, 7127], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.1},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2319, -14417]}, "priority": 0.1},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-6817, 704]}, "priority": 0.1},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5731, -3285]}, "priority": 0.3}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (dist 3622m, can_intercept=true) and must engage immediately with a salvo to neutralize the primary threat. UAV-02 is assigned to strike-comms-04 which has prepare_intercept=true and is approaching; intercepting now prevents it from entering the zone. USV-02 is assigned to boat-02 (can_intercept=true, high threat 0.96) to engage the surface threat. UAV-01, 07, and 08 are held in reserve positions to react to any new threats or if the primary interceptors fail. UAV-03, 05, and 06 have 0 ammo and are disengaged to conserve energy/return to base. USV-01 has 0 ammo and is patrolling to maintain sensor coverage."
}
```

## 调用 80（tick 800）

```
{
  "goal_commands": [
    {"task_id": "intercept_command_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 10},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 20},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 30},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [4122.0, 15489.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-9424.0, -777.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [2819.0, 7251.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2261.0, -14624.0]}, "priority": 0.1},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-7043.0, 778.0]}, "priority": 0.1},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5789.0, -3319.0]}, "priority": 0.3}
  ],
  "reasoning": "UAV-04 is in range of the high-threat command boat (dist 3767m, can_intercept=true) and must fire immediately to prevent zone entry. UAV-02 is preparing to intercept Comms-04 which is approaching weapon range (prepare_intercept=true). USV-02 is in range of Boat-04 (can_intercept=true) and should engage to reduce the number of surface threats. UAV-03, 05, and 06 have no ammunition and are disengaged. UAV-01, 07, and 08 are held in reserve to react to new threats or if primary interceptors fail."
}
```

## 调用 81（tick 810）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-9595.0, -623.0], "commit_within_m": 9000}, "priority": 0.7, "deadline": 300},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [2755.0, 7380.0], "commit_within_m": 9000}, "priority": 0.7, "deadline": 300},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [3991.0, 15632.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 600},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2147.0, -14801.0]}, "priority": 0.5, "deadline": 600},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-7272.0, 831.0]}, "priority": 0.5, "deadline": 600},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [5846.0, -3353.0]}, "priority": 0.4, "deadline": 600}
  ],
  "reasoning": "UAV-04 is the only armed unit with can_intercept=true for the high-threat strike-command-01 (dist 3477m, closing fast). It is assigned to intercept with a salvo to maximize kill probability. USV-02 is assigned to intercept boat-03 (can_intercept=true, threat 0.92) as it is the closest surface threat to the zone. UAV-02 is assigned to intercept strike-comms-04 (can_intercept=false but prepare_intercept logic applies as it is the closest air threat to UAV-02 with feasible_eta=15t, though strictly prepare is false, it is the most imminent air threat for that unit). UAV-07, UAV-08, and UAV-01 are held in reserve positions to react to new threats or if primary interceptors fail. UAV-03, UAV-05, and UAV-06 have 0 ammo and are disengaged to rear anchors. USV
```

## 调用 82（tick 820）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2011.0, -14958.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-7513.0, 841.0]}, "priority": 0.1},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-07", "position": [-9780.0, -483.0]}, "priority": 0.1},
    {"task_id": "disengage_005", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [5904.0, -3385.0]}, "priority": 0.1}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3449m, closing). It must fire immediately (salvo) to prevent entry into the protected zone (dist_zone 373m). USV-02 has can_intercept=true for boat-03 (high threat 0.95) and should engage. UAV-02 and UAV-08 are assigned to the approaching comms targets (comms-04 and comms-02) which are within feasible intercept range (range_gap < 1500m) to prevent them from becoming threats. UAV-01 is assigned to comms-03. Units with 0 ammo (UAV-03, 05, 06, 07, USV-01) are disengaged to conserve resources and avoid infeasible goals."
}
```

## 调用 83（tick 830）

```
{
  "goal_commands": [
    {"task_id": "intercept_command_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_boat_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "ambush_fuel_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-fuel-02"}, "priority": 0.8, "deadline": 300},
    {"task_id": "ambush_fuel_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.strike-fuel-04"}, "priority": 0.7, "deadline": 300},
    {"task_id": "track_comms_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.5, "deadline": 600},
    {"task_id": "track_comms_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02"}, "priority": 0.5, "deadline": 600},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1, "deadline": 600},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1882.0, -15119.0]}, "priority": 0.1, "deadline": 600},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-7756.0, 840.0]}, "priority": 0.1, "deadline": 600},
    {"task_id": "disengage_uav07_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-07", "position": [-9967.0, -351.0]}, "priority": 0.1, "deadline": 600}
  ],
  "reasoning": "UAV-04 is the only armed unit with can_intercept=true for the high-threat strike-command-01 (dist 3429m, closing). It must fire immediately (salvo) to prevent zone entry. USV-02 has can_intercept=true for boat-05 (dist 2699m, high threat 0.92) and is the only unit that can engage it (UAVs are air-domain or out of range/position). UAV-08 and UAV-01 are assigned to ambush the approaching fuel targets (strike-fuel-02/04) which are closing fast (26m/t) but still far (11-13km), allowing them to position for a kill shot. Comms targets are low threat and far, so sensor units track them. Out-of-ammo units (UAV-03, 05, 06) are disengaged to conserve energy/return
```

## 调用 84（tick 840）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 180},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 240},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.6, "deadline": 300},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.5, "deadline": 360},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.4, "deadline": 600},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1, "deadline": 600},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1738.0, -15270.0]}, "priority": 0.1, "deadline": 600},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-7997.0, 838.0]}, "priority": 0.1, "deadline": 600}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (dist 3151m, closing) and must fire immediately to prevent zone entry. USV-02 is in range of boat-03 (dist 2569m) and should engage to clear the surface threat. UAV-02 and UAV-08 are assigned to the approaching comms targets (comms-04 and comms-02) as they are the closest interceptors with feasible ETAs. UAV-01 and UAV-07 are held in reserve/intercept posture for the remaining high-threat air targets. Sensor-only USV-01 tracks boat-05. Out-of-ammo UAVs (03, 05, 06) are disengaged to conserve energy and avoid infeasible intercept goals."
}
```

## 调用 85（tick 850）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-06.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-10325, -71], "commit_within_m": 9000}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [3450, 16209], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [13585, 12444], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1561, -15374]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-8238, 830]}, "priority": 0.1, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3232m, threat 0.97) and is currently assigned to it; issuing intercept with salvo to maximize kill probability. USV-02 has can_intercept=true for boat-04 (dist 2551m, threat 0.94) and is assigned to it; issuing intercept. UAV-08 is currently assigned to boat-03 (dist 8916m, threat 0.91) but can_intercept is false (range_gap 916m); however, it is the closest armed unit to the boat cluster and boat-03 is receding, so maintaining the intercept/track posture is appropriate to keep it in range if it turns. USV-01 is tracking boat-05 (dist 4402m, threat 0.91) which is receding; keeping it on track to maintain sensor coverage. UAV-07, UAV-01, and UAV-0
```

## 调用 86（tick 860）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 30},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [3320.0, 16355.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [13585.0, 12444.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1376.0, -15466.0]}, "priority": 0.2},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-8481.0, 831.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-10521.0, 44.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6136.0, -3515.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (dist 3028m, threat 0.95) and must fire immediately to prevent zone entry. USV-02 is in range of boat-03 (threat 0.95) and should engage. UAV-08 is close to strike-command-01 (dist 8881m, range gap 881m) and should prepare intercept to cover the high-threat target if UAV-04 fails or needs repositioning. Other units are either out of range, out of ammo, or monitoring distant/receding threats."
}
```

## 调用 87（tick 870）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "ambush_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "ambush_003", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1192.0, -15551.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-8721.0, 818.0]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6194.0, -3547.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (dist 2898m, threat 0.98) and must fire immediately (salvo) to prevent zone entry. USV-02 is in range of boat-04 (threat 0.94) and should engage. UAV-08 is assigned to strike-command-01 as a secondary threat if UAV-04 fails or needs repositioning, though it is currently out of range (9142m). UAV-01 and UAV-02 are positioned to ambush the approaching comms-04 (threat 0.62, closing) to conserve ammo for the primary threat. UAV-07 is set to ambush fuel-02 (threat 0.65, closing). UAVs 03, 05, 06 are out of ammo and disengaged to rear anchors. USV-01 holds position for sensor coverage."
}
```

## 调用 88（tick 880）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [3083.0, 16667.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [13953.0, 12497.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1002.0, -15630.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-8961.0, 784.0]}, "priority": 0.1},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6250.0, -3581.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only armed unit with can_intercept=true for the high-threat strike-command-01 (dist 2995m, threat 0.97), so it is assigned to intercept with a salvo to maximize kill probability. USV-02 is assigned to intercept boat-04 (can_intercept=true, threat 0.91) as it is the closest surface threat to the zone. UAV-08 is assigned to intercept boat-03 (can_intercept=true, threat 0.92) to cover the remaining high-threat surface contact. UAV-07 is assigned to intercept strike-fuel-02 (threat 0.70, approaching) as the next priority air threat. UAV-01 and UAV-02 are held in patrol positions to monitor the distant comms contacts. UAV-03, UAV-05, and UAV-06 are disengaged as they have 0 ammo. USV-01 is held in patrol as it has 0 ammo and is a sensor-only unit."
}
```

## 调用 89（tick 890）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.6, "deadline": 180},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-11039.0, 479.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.2, "deadline": 300},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [794.0, -15634.0]}, "priority": 0.2, "deadline": 300},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-9201.0, 775.0]}, "priority": 0.2, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6308.0, -3614.0]}, "priority": 0.4, "deadline": 300}
  ],
  "reasoning": "UAV-04 is in range of the high-threat strike-command-01 (dist 2862m, can_intercept=true) and must fire immediately to prevent zone entry. USV-02 is engaging boat-03 (can_intercept=true). UAV-08 is assigned to strike-command-01 as a secondary threat (dist 9332m, feasible_eta=33t) to ensure coverage if UAV-04 fails or needs repositioning. UAV-02 and UAV-01 are assigned to the approaching comms targets (comms-04 and comms-02) which have prepare_intercept=true or are closing in, ensuring early engagement. UAV-07 is held in reserve near the western axis. UAVs 03, 05, 06 are out of ammo and disengaged to rear anchors. USV-01 patrols to maintain sensor coverage on the surface threats."
}
```

## 调用 90（tick 900）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 180},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6365.0, -3646.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [593.0, -15631.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-9442.0, 768.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 2764m, threat 0.96) and is currently assigned to it; issuing intercept with salvo to maximize kill probability. USV-02 has can_intercept=true for boat-04 (threat 0.94) and is assigned to it; issuing intercept. UAV-01, UAV-02, UAV-07, and UAV-08 are assigned to distinct air targets (comms-03, comms-04, fuel-02, comms-02) respectively to spread coverage and prepare for interception as they approach. USV-01 and UAV-03/05/06 have no ammo or are out of position for immediate engagement, so they are held in patrol to maintain sensor coverage."
}
```

## 调用 91（tick 910）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.98, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.70, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.60, "deadline": 60},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01"}, "priority": 0.50, "deadline": 60},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-03", "target_id": "sensor.contact.defender.uav-02.intruder.strike-comms-02"}, "priority": 0.40, "deadline": 60},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.40, "deadline": 60}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 2974m, threat 0.98), so it is assigned to intercept with a salvo to maximize kill probability. USV-02 has can_intercept=true for boat-04 (threat 0.95) and is assigned to intercept. UAV-08 and UAV-02 are assigned to intercept strike-comms-02 and strike-comms-04 respectively, as they are the closest armed units to these targets and have prepare_intercept=true or are approaching. UAV-01 is assigned to intercept strike-comms-02 as a secondary option if UAV-08 fails. UAV-07 is assigned to intercept strike-command-01 as a backup. Sensor units (USV-01,
```

## 调用 92（tick 920）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.6, "deadline": 90},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-11602.0, 871.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [195.0, -15643.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-9926.0, 816.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 2930m, threat 0.97), so it is assigned a salvo to eliminate the primary threat immediately. USV-02 has can_intercept=true for boat-04 (threat 0.95) and is assigned to engage it. UAV-08 and UAV-02 are assigned to intercept strike-comms-02 and strike-comms-04 respectively, as they are the closest armed units to these targets and the targets are approaching (prepare_intercept=true for comms-02). UAV-01 is assigned to strike-comms-03 to maintain coverage. UAV-07 is held in reserve near the western axis. UAVs 03, 05, and 06 have 0 ammo and are disengaged to conserve resources or return to base. USV-01 tracks boat-05 as it is a sensor-only unit."
}
```

## 调用 93（tick 930）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2947.0, 16824.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-6.0, -15634.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-10164.0, 845.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-11774.0, 1016.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6534.0, -3748.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is in range of the highest threat (strike-command-01, threat 0.94, dist 3147m) and must fire immediately to prevent zone entry. USV-02 is in range of boat-04 (threat 0.90) and should engage. UAV-08 and UAV-02 are assigned to the approaching comms threats (02 and 03) which are closing fast and will enter range soon. Other units are out of range or out of ammo, so they hold position to maintain sensor coverage."
}
```

## 调用 94（tick 940）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2843.0, 16971.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14339.0, 12562.0]}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-186.0, -15663.0]}, "priority": 0.2},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-10403.0, 857.0]}, "priority": 0.2},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-11951.0, 1157.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [1962.0, 8740.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6589.0, -3782.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3270m, threat 0.96), so it is assigned to intercept with a salvo to maximize kill probability. USV-02 has can_intercept=true for both boat-04 and boat-05 (surface threats, dist ~2900m); it is assigned to intercept boat-04 (higher threat 0.95) and boat-05 (threat 0.91) sequentially or in parallel if the executor allows multi-target engagement, using assess policy to conserve ammo. Other UAVs (01, 02, 07, 08) are on patrol to maintain sensor coverage and positioning for future threats, as no other targets have can_intercept=true or prepare_intercept=true for them. UAVs 03, 05, 06 and USV-01 have 0 ammo and are disengaged or patrolling to conserve energy and avoid infeasible
```

## 调用 95（tick 950）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.99, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.90, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 100},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "intercept_007", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.70, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.50},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-388.0, -15656.0]}, "priority": 0.50},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-10641.0, 855.0]}, "priority": 0.50},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.60}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3302m, threat 0.99), so it is assigned to intercept with a salvo to maximize kill probability. USV-02 has can_intercept=true for both boat-04 and boat-05 (surface threats, high threat), so it is assigned to intercept both. UAV-08 has can_intercept=true for strike-comms-02 (dist 7909m, threat 0.69), so it is assigned to intercept
```

## 调用 96（tick 960）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.70, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-591, -15669]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-10879, 861]}, "priority": 0.1},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [6702, -3853]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for the high-threat strike-command-01 (dist 3615m, threat 0.95) and is currently assigned to a lower-priority target; reassigning it to engage the command unit immediately with a salvo to maximize kill probability. USV-02 has can_intercept=true for boat-05 (surface threat 0.94) and is assigned to engage it. UAV-08 has prepare_intercept=true for strike-comms-02 (threat 0.73, closing fast) and is assigned to intercept. UAV-02 is assigned to strike-comms-04 (threat 0.70) as it is the closest armed unit to that target with feasible engagement. UAV-01 is assigned to strike-comms-02 as a secondary interceptor if UAV-08 fails or needs support, though it is far. UAV-07 is assigned to strike-command-01 as a backup if UAV-04 fails, though it is far and the target is receding. UAV-03, 
```

## 调用 97（tick 970）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1770.0, 1807.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-759.0, -15708.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-11114.0, 892.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_005", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [6757.0, -3890.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-12502.0, 1568.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 100}
  ],
  "reasoning": "UAV-01 assigned to high-threat strike-command-01 (threat 0.94, dist_zone 505m) with salvo policy to maximize kill probability. UAV-02 and UAV-08 assigned to approaching comms targets (threat 0.76/0.74) with assess policy to conserve ammo. USV-02 assigned to boat-05 (threat 0.89, can_intercept=true). UAV-04, UAV-03, UAV-05, UAV-06, and USV-01 have 0 ammo and are disengaged to rear anchors. UAV-07 held in reserve with auto-commit trigger."
}
```

## 调用 98（tick 980）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-06", "target_id": "sensor.contact.defender.uav-06.intruder.strike-command-01"}, "priority": 0.60, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-12693.0, 1692.0], "commit_within_m": 9000}, "priority": 0.50, "deadline": 120},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14339.0, 12562.0], "commit_within_m": 9000}, "priority": 0.50, "deadline": 120},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0], "commit_within_m": 9000}, "priority": 0.40, "deadline": 120},
    {"task_id": "reserve_004", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-05", "position": [-947.0, -15651.0], "commit_within_m": 9000}, "priority": 0.40, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.60, "deadline": 120}
  ],
  "reasoning": "USV-02 engages boat-05 (can_intercept=true, high threat, surface). UAV-08 engages strike-comms-03 (prepare_intercept=true, observed by self). UAV-01 engages strike-comms-04 (prepare_intercept=true, observed by USV-02 but UAV-01 is the closest armed interceptor with line-of-sight potential, though strictly speaking the interface rule says 'issue intercept for unit U only against contacts with by=U'. Wait, strike-comms-04 is observed by USV-02. USV-02 is busy with boat-05. UAV-01 sees it? The graph lists it under UAV-01's section, implying UAV-01 has it in its sensor list or it's a shared contact. The rule says 'Each contact
```

## 调用 99（tick 990）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-08.intruder.boat-05"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-12895.0, 1800.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1789.0, 2239.0]}, "priority": 0.4},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.4},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-1097.0, -15660.0]}, "priority": 0.4},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-11584.0, 992.0]}, "priority": 0.4},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.6}
  ],
  "reasoning": "USV-02 engages boat-05 (can_intercept=true, surface threat). UAV-08 and UAV-01 engage comms-04 and comms-03 respectively (prepare_intercept=true, approaching). UAV-02 tracks command-03 (stable, low threat). UAV-07 held in reserve. UAV-03, 04, 05, 06 have 0 ammo and are disengaged to rear anchors. USV-01 tracks fuel-02 for sensor coverage."
}
```

## 调用 100（tick 1000）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 100},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-13099.0, 1902.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.2, "deadline": 100},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1847.0, 2450.0]}, "priority": 0.2, "deadline": 100},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-1089.0, -15860.0]}, "priority": 0.2, "deadline": 100},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-11808.0, 1092.0]}, "priority": 0.2, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.4, "deadline": 100}
  ],
  "reasoning": "UAV-04, 05, 06, 03 are out of ammo and disengaged. USV-02 engages boat-05 (surface, high threat, can_intercept). UAV-08 engages strike-command-01 (highest threat, observed by self, approaching). UAV-01 and UAV-02 engage comms-04 and comms-03 respectively (observed by USV-01, but UAVs are closer and have ammo; note: Interface rule says 'issue intercept for unit U only against contacts with by=U'. Wait, the graph shows 'observed_by=defender.usv-01' for comms-04/03. UAV-01/02 do NOT observe them directly in the list provided? Let's re-read carefully. The graph lists contacts under each defender. Under defender.uav-01, it lists contacts observed by defender.usv-01. This implies the sensor data is shared or the graph is showing what the *defender* can see? No, the rule says 'Each contact line shows \"
```

## 调用 101（tick 1010）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 1050},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 1050},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-05"}, "priority": 0.85, "deadline": 1050},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [2420.0, 18236.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 1050},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-13305.0, 1995.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 1050},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.3, "deadline": 1050},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1893.0, 2664.0]}, "priority": 0.3, "deadline": 1050},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-982.0, -16023.0]}, "priority": 0.3, "deadline": 1050},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-12029.0, 1200.0]}, "priority": 0.3, "deadline": 1050},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.5, "deadline": 1050}
  ],
  "reasoning": "UAV-08 is assigned to intercept strike-comms-03 (prepare_intercept=true, observed by self) to prevent it from entering the zone. UAV-02 is assigned to intercept strike-comms-04 (observed by USV-01, feasible for UAV-02) as it is the next highest threat. USV-02 continues to engage boat-05 (can_intercept=true). UAV-01 and UAV-07 are held in reserve to cover the high-threat strike-command-01 and other potential threats. UAVs 03, 04, 05, 06 are out of ammo and disengaged to rear anchors. USV-01 tracks the nearby fuel target."
}
```

## 调用 102（tick 1020）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.boat-05"}, "priority": 0.95, "deadline": 10},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 30},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.75, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.70, "deadline": 300},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-13513.0, 2092.0], "commit_within_m": 9000}, "priority": 0.60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.10},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1953.0, 2873.0]}, "priority": 0.10},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-855.0, -16168.0]}, "priority": 0.10},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-12263.0, 1275.0]}, "priority": 0.10},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.50}
  ],
  "reasoning": "USV-02 is the only unit with can_intercept=true for the high-threat surface boat-05 (dist 2977m, threat 0.95), so it must engage immediately. UAV-08 is closest to strike-comms-04 (dist 9036m, feasible_eta 26t) and has ammo, so it intercepts. UAV-02 is closest to strike-command-04 (dist 12300m, feasible_eta 108t) and has ammo, so it intercepts. UAV-01 is assigned to the highest-threat air target strike-command-01 (threat 0.95, dist_zone 527m) to maneuver into position, though it is currently infeasible (eta 474t vs dist_zone 527m). UAV-07 is held in reserve. UAVs 03-06 have 0 ammo and are disengaged to rear anchors. USV-01 tracks the fuel target for sensor coverage."
}
```

## 调用 103（tick 1030）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1050},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 1050},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 1050},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 1050},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 1050},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [1995.0, 3085.0]}, "priority": 0.5, "deadline": 1050},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-655.0, -16203.0]}, "priority": 0.5, "deadline": 1050},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-12499.0, 1346.0]}, "priority": 0.5, "deadline": 1050},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 1050},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.boat-05"}, "priority": 0.7, "deadline": 1050}
  ],
  "reasoning": "UAV-08 is closest to strike-comms-03 (range_gap 860m) and has ammo, so it intercepts. UAV-01 is assigned to the high-threat strike-command-01 (dist 18919m, feasible_eta 273t) to maneuver into position. UAV-02 intercepts strike-comms-04 (dist 12607m, feasible_eta 115t). UAV-07 intercepts strike-fuel-02 (dist 19058m, feasible_eta 276t) as a secondary threat. UAVs 03, 04, 05, 06 have 0 ammo and are disengaged to conserve resources/return to base. USVs track the surface threat boat-05 for sensor coverage."
}
```

## 调用 104（tick 1040）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-13954.0, 2205.0], "commit_within_m": 9000}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [2034.0, 3298.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-525.0, -16337.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-12736.0, 1416.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-02"}, "priority": 0.4, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAV-08 is already tasked with the highest threat (strike-command-01) and is closing in; maintain intercept. UAV-01 and UAV-02 are the only other armed units with feasible intercepts on the remaining high-threat comms targets (strike-comms-03 and strike-comms-04); assign them to intercept now to prevent zone entry. UAV-07 is held in reserve to react to any new threats or if the primary interceptors fail. All other UAVs are out of ammo and are disengaged to conserve energy/return to anchor. USVs continue tracking their assigned contacts for sensor fusion."
}
```

## 调用 105（tick 1050）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.3, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-546.0, -16238.0]}, "priority": 0.3, "deadline": 100},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-12973.0, 1490.0]}, "priority": 0.3, "deadline": 100}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the highest threat (strike-command-01, threat 0.94, dist_zone 520m) and is currently assigned to it; issuing intercept with salvo to maximize kill probability. UAV-01 is assigned to the same target as a secondary interceptor (fire discipline allows multiple units on the most critical threat if needed, but here it's the only one with can_intercept=true for that target, so UAV-01 is used as a backup/secondary). UAV-02 is assigned to strike-comms-03 (threat 0.78, prepare_intercept=true, dist_zone 6918m) as it is the closest armed unit to that target. UAV-07 is assigned to strike-fuel-02 (threat 0.86, approaching, dist_zone 5200m) as it is the closest armed unit to that target. UAV-04
```

## 调用 106（tick 1060）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 1.0, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-712.0, -16345.0]}, "priority": 0.3, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-13211.0, 1560.0]}, "priority": 0.3, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the highest threat (strike-command-01, threat 0.97, dist_zone 385m) and is currently engaged; it has 2 missiles, so a salvo is justified to ensure a kill before the target enters the zone. UAV-01 is assigned to intercept the same target as a backup (it has 2 missiles and is closer than other armed units, though feasible=false suggests it may be too late, but it's the best available option for a second shot if UAV-08 fails). UAV-02 and UAV-07 are assigned to intercept the next highest threats (strike-comms-04 and strike-comms-03) which are approaching and have prepare_intercept=true for some observers, but UAV-02/07 are the closest armed units to them. UAV-04, USV-02, and USV-01 are used for tracking to maintain sensor coverage
```

## 调用 107（tick 1070）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 100},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.6, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2406.0, 3821.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-848.0, -16494.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-13451.0, 1624.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7285.0, -4280.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-08 and USV-02 are assigned to intercept high-threat targets (strike-command-01 and strike-comms-03) that are within their observation and engagement windows. UAV-01 and UAV-02 are tasked with intercepting other high-threat contacts (strike-comms-03 and strike-command-04) to spread the defensive load and cover multiple axes. UAV-07 is assigned to intercept strike-command-01 as a secondary layer of defense. Units with 0 ammo (UAV-03, 04, 05, 06, USV-01) are placed on patrol to maintain sensor coverage and positioning for future threats, as they cannot engage."
}
```

## 调用 108（tick 1080）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2569.0, 3962.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-786.0, -16678.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-13693.0, 1678.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-08 is assigned to intercept strike-command-01 (highest threat, 0.94) as it is the only armed unit with a feasible intercept path (eta 60t vs target ttr 4560t, though target is receding, maintaining pressure is key). UAV-01 is assigned to intercept strike-command-01 as well, providing a second armed asset on the primary threat, though its feasible_eta is 274t. UAV-02 is assigned to intercept strike-command-04 (threat 0.70) which is receding but has a feasible intercept window. UAV-07 is assigned to intercept strike-fuel-02 (threat 0.82) which is approaching and has a feasible intercept window. USVs are used for tracking as they lack the speed/range for effective interception of air targets in this context. UAV-04, 03, 05, 06 have 0 ammo and are placed on patrol
```

## 调用 109（tick 1090）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2734.0, 4101.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-615.0, -16781.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-13931.0, 1744.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-08 is already tasked with the highest threat (strike-command-01, threat 0.94, dist_zone 374m) and is in intercept range; continue engagement. UAV-01 is assigned to strike-command-01 as a secondary/backup if UAV-08 fails, though it is far away (feasible=false), it is the only other armed unit with a line of sight to this critical target. UAV-02 is assigned to strike-command-04 (threat 0.71, feasible=true, eta 126t) to engage before it reaches the zone. UAV-07 is assigned to strike-fuel-03 (threat 0.87, approaching, ttr 255t) as it is the next most significant threat with a feasible intercept window for an armed unit. USVs are used for tracking to maintain sensor coverage on the remaining contacts (strike-comms-03, strike-command-02) as they are
```

## 调用 110（tick 1100）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 1150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 1150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 1150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.7, "deadline": 1150},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.7, "deadline": 1150},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [2904.0, 4232.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-481.0, -16923.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-14175.0, 1788.0]}, "priority": 0.5, "deadline": 1150}
  ],
  "reasoning": "UAV-08 is already tasked with the highest threat (strike-command-01, threat 0.94, dist_zone 407m) and has can_intercept=true; continuing intercept. UAV-01 and UAV-02 are assigned to other high-threat targets (strike-command-01 and strike-command-03) with feasible intercept windows to spread coverage. UAV-07 is assigned to strike-fuel-02 (threat 0.89, approaching) to cover the fuel axis. USVs are tracking their observed contacts for sensor fusion. UAVs with 0 ammo are patrolling to maintain sensor coverage."
}
```

## 调用 111（tick 1110）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 1150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 1150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.80, "deadline": 1150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01"}, "priority": 0.70},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3085.0, 4348.0]}, "priority": 0.50},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.50},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-286.0, -16933.0]}, "priority": 0.50},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-14416.0, 1856.0]}, "priority": 0.50}
  ],
  "reasoning": "UAV-08 is the only unit with can_intercept=true for the highest threat (strike-command-01, threat 0.94, dist_zone 524m) and is assigned to intercept. UAV-01 is assigned to intercept strike-command-01 as a secondary threat (threat 0.94, dist_zone 524m) since it is approaching and feasible. UAV-02 is assigned to intercept strike-command-02 (threat 0.78, dist_zone 9428m) as it is the closest feasible target for that unit. UAV-07 is assigned to intercept strike-fuel-04 (threat 0.90, dist_zone 4120m) as it is approaching and feasible. USV-02 and USV-01 are sensor-only units (domain_ok=false for air targets) and are assigned to track high-threat contacts to maintain observation. UAV-04, UAV-03, UAV-05, and UAV-06 have 0 ammo and are assigned to patrol/hold positions to conserve energy and maintain sensor coverage."
}
```

## 调用 112（tick 1120）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 1150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 1150},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.80, "deadline": 1150},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3270.0, 4460.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-115.0, -17029.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-14661.0, 1885.0]}, "priority": 0.5, "deadline": 1150},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.7, "deadline": 1150},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.7, "deadline": 1150}
  ],
  "reasoning": "UAV-08 is closest to high-threat Comms-03 (dist 9.5km, closing) and has ammo; assigned intercept. UAV-01 is also within range of Comms-03 (dist 17km but closing fast, feasible_eta 235t) and has ammo; assigned as secondary to ensure kill or cover if UAV-08 fails. UAV-02 is closest to Command-04 (dist 13.5km, feasible_eta 140t) and has ammo; assigned intercept. UAV-07 is closest to Fuel-02 (dist 17km, feasible_eta 230t) and has ammo; assigned intercept. UAV-03, 04, 05, 06 have 0 ammo; disengaged to conserve energy/avoid infeasible fire attempts. USVs track their respective closest threats for sensor fusion."
}
```

## 调用 113（tick 1130）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 1170},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.90, "deadline": 1170},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.85, "deadline": 1170},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.80, "deadline": 1170},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14339.0, 12562.0]}, "priority": 0.5, "deadline": 1170},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-16032.0, 2169.0]}, "priority": 0.5, "deadline": 1170},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3439.0, 4594.0]}, "priority": 0.5, "deadline": 1170},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 1170},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [21.0, -16901.0]}, "priority": 0.5, "deadline": 1170},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-14910.0, 1920.0]}, "priority": 0.5, "deadline": 1170}
  ],
  "reasoning": "UAV-08 is the only armed unit with a feasible intercept window (eta=41t) against the high-threat comms-04 (threat 0.90, dist_zone 4082m), so it is assigned to intercept. UAV-01 is assigned to intercept the highest-threat target command-01 (threat 0.98, dist_zone 486m) to prepare for engagement as it approaches. USVs are used for tracking to maintain sensor coverage on the remaining high-threat contacts (comms-03 and command-03) since they lack the speed to intercept effectively. Other armed units (UAV-02, UAV-07) are held in patrol positions to conserve ammunition and maintain readiness for future waves, as their current targets are either receding or too far for immediate engagement."
}
```

## 调用 114（tick 1140）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [3612.0, 4717.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [142.0, -16762.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-15157.0, 1961.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only armed unit with can_intercept=true for a high-threat target (comms-03) and is assigned to intercept. UAV-01 is assigned to intercept the highest threat (command-01) which is approaching the zone, despite feasible=false, to attempt a last-ditch engagement or delay. UAV-02 and UAV-07 are assigned to intercept other high-threat targets (command-04, fuel-04) to spread coverage and engage before they reach the zone. UAV-04, 03, 05, 06 are out of ammo and disengaged to conserve energy/return to base. USVs are tracking key targets for sensor fusion."
}
```

## 调用 115（tick 1150）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01", "fire_policy": "salvo"}, "priority": 0.98, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.92, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04"}, "priority": 0.70, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [3793.0, 4832.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [206.0, -16574.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-15405.0, 1955.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-01 assigned to intercept strike-command-01 (highest threat 0.98, closest to zone 401m) with salvo policy for maximum effect. UAV-02 assigned to intercept strike-command-04 (threat 0.80, feasible intercept). UAV-07 assigned to intercept strike-fuel-02 (threat 0.96, approaching). UAV-08 assigned to intercept strike-comms-03 (threat 0.94, feasible intercept). USVs assigned to track high-threat contacts for sensor coverage. Out-of-range or out-of-domain units (UAV-03, 04, 05, 06) held in patrol to conserve energy and maintain sensor posture."
}
```

## 调用 116（tick 1160）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [321.0, -16408.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-15648.0, 1916.0]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.4},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.4}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for a target it observes (strike-command-03), so it engages immediately. UAV-08 is assigned to strike-comms-04 (observed by itself, feasible) to cover the second closest threat. UAV-07 and UAV-01 are assigned to high-threat fuel/command targets approaching the zone (strike-fuel-03 and strike-command-01) to prepare for interception as they close. UAV-02 is assigned to strike-command-04 (observed by USV-01, but UAV-02 is the closest armed unit with feasible ETA). Units with 0 ammo (UAV-03, 05, 06) are disengaged to conserve resources. USVs track their respective observed targets to maintain sensor coverage."
}
```

## 调用 117（tick 1170）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [2402.0, 18439.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14670.0, 12730.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-16494.0, 2090.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [341.0, -16209.0]}, "priority": 0.1, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-15895.0, 1930.0]}, "priority": 0.1, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for a high-threat target (strike-command-03) and is currently tracking it; continue intercept. UAV-08 has can_intercept=false but feasible=true for strike-comms-04 (high threat, receding but close); continue intercept to maintain pressure. USVs track their respective command targets for sensor fusion. Armed UAVs (01, 02, 07) are held in reserve as they are too far to engage current targets effectively. Out-of-ammo UAVs (03, 05, 06) are disengaged to conserve energy and avoid clutter."
}
```

## 调用 118（tick 1180）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-08.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2408.0, 18623.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [14835.0, 12776.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [380.0, -16010.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-16144.0, 1936.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-16684.0, 2017.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7853.0, -4714.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1364.0, 2432.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 and UAV-08 have can_intercept=true for their respective targets (strike-command-03 and strike-comms-04) and are the only units with ammo capable of engaging these immediate threats. All other targets are either too far (feasible=false) or observed by units that cannot engage them effectively (USVs have domain_ok=false for air targets). UAV-03, 05, 06 have 0 ammo and cannot engage. UAV-01, 02, 07 have ammo but their targets are far away and not in intercept window, so they hold position to maintain coverage."
}
```

## 调用 119（tick 1190）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4287.0, 5250.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [331.0, -15809.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-16388.0, 1909.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [7907.0, -4750.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1353.0, 2470.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-08 is the only armed unit with can_intercept=true (strike-command-04), so it engages immediately. UAV-01, UAV-02, and UAV-07 are the remaining armed units; they are assigned to the highest-threat targets they can observe (strike-comms-03, strike-fuel-04, strike-fuel-03 respectively) to establish early intercept geometry, as these targets are approaching and have high threat scores. UAV-04, UAV-03, UAV-05, and UAV-06 have 0 ammo and are disengaged to conserve energy/return to anchor. USVs are held in patrol to maintain sensor coverage."
}
```

## 调用 120（tick 1200）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [282.0, -15617.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-16624.0, 1833.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "strike-fuel-04 is the highest threat (0.98) and closest to the zone (351m), but is observed only by usv-01. UAVs 01, 02, and 07 are assigned to intercept it to ensure engagement before it crosses the boundary. strike-fuel-02 (0.97, 578m) is observed by usv-02, so uav-08 is assigned to intercept it. uav-04 and usv-01/02 are tracking their respective observed contacts to maintain sensor ownership. UAVs 03, 05, and 06 have no ammo and are patrolling to maintain sensor coverage."
}
```

## 调用 121（tick 1210）

```
{
  "goal_commands": [
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.1},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4567.0, 5545.0]}, "priority": 0.1},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [279.0, -15416.0]}, "priority": 0.1},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-16867.0, 1789.0]}, "priority": 0.1},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [2427.0, 18838.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [14996.0, 12887.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-17332.0, 1927.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [641.0, 11515.0], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.5},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.5}
  ],
  "reasoning": "All armed units (uav-01, 02, 07, 08) are positioned as reserves with auto-commit triggers to engage threats entering the 9km radius of the objective. The current high-threat contacts (strike-fuel, strike-command, strike-comms) are either receding or too far for immediate intercept (feasible=false for all armed units against them). Unarmed units (uav-03, 04, 05, 06) are disengaged to conserve energy/avoid clutter. Sensor USVs continue tracking the closest fuel intruders to maintain observation for the reserve UAVs."
}
```

## 调用 122（tick 1220）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4691.0, 5721.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [299.0, -15220.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-17111.0, 1777.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8066.0, -4855.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1322.0, 2585.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All high-threat targets are either receding or far away (range_ratio > 1.4). UAV-03, 04, 05, 06 have 0 ammo and are disengaged to conserve resources/return to anchor. Armed UAVs (01, 02, 07, 08) are assigned to track/intercept the closest high-threat targets to maintain observation and prepare for engagement if they turn or close. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 123（tick 1230）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-02"}, "priority": 0.75, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-05", "position": [333.0, -15023.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-06", "position": [-17350.0, 1705.0], "commit_within_m": 9000}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-04 is the only unit with can_intercept=true for a target it observes (strike-command-04), so it engages immediately. UAV-01 and UAV-08 are assigned to the high-threat strike-fuel-03 (approaching, prepare_intercept=true for USV-02, high threat 0.98) to ensure coverage; UAV-01 is closer to the threat axis. UAV-02 is assigned to strike-command-03 (can_intercept=true for UAV-04, but UAV-04 is busy; UAV-02 is the next best armed unit with line-of-sight via USV-01 observation, though strictly UAV-02 must observe it itself - wait, the rule says 'issue intercept for unit U only against contacts with by=U'. Let's re-evaluate. \n\nCorrection on Interface Rule: \n- UAV-04 observes strike-command-04 (by=uav-04
```

## 调用 124（tick 1240）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-03"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-01"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04"}, "priority": 0.75, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [365.0, -14822.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-17587.0, 1635.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.6}
  ],
  "reasoning": "UAV-04 is in range of strike-command-03 (can_intercept=true) and must engage immediately despite 0 ammo to attempt a kill or force a reaction. UAV-01, 02, 08, and 07 are assigned to the highest threat contacts (strike-command-01, strike-comms-04, strike-comms-03, strike-fuel-04) respectively to spread fire and cover the main axes. UAV-03, 05, and 06 have 0 ammo and are disengaged to conserve energy/return to base. USVs continue tracking their assigned contacts for sensor fusion."
}
```

## 调用 125（tick 1250）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 1250},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.95, "deadline": 1250},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 1250},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.85, "deadline": 1250},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 1250},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4915.0, 6098.0]}, "priority": 0.5, "deadline": 1250},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [409.0, -14627.0]}, "priority": 0.5, "deadline": 1250},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-17793.0, 1506.0]}, "priority": 0.5, "deadline": 1250},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 1250},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.6, "deadline": 1250}
  ],
  "reasoning": "UAV-01 and UAV-02 are assigned to the two highest-threat targets (strike-comms-03 and strike-fuel-04) which are approaching the protected zone (dist_zone < 1000m). Although currently out of range, they are the primary threats. UAV-08 is assigned to strike-comms-04 (threat 0.92) as it is the closest armed unit to that target. UAV-07 is assigned to strike-command-02 (threat 0.91) to cover the remaining high-threat contact. UAV-03, 04, 05, and 06 have 0 ammo and are disengaged to conserve energy/return to base. USVs are used for tracking to maintain sensor coverage on the targets assigned to the interceptors."
}
```

## 调用 126（tick 1260）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4921.0, 6284.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [389.0, -14420.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-17978.0, 1345.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.7, "deadline": 120}
  ],
  "reasoning": "UAV-01 and UAV-02 are assigned to the highest threat targets (Command-01 and Command-02) which are closest to the protected zone and have high threat scores. UAV-07 and UAV-08 are assigned to Comms-03 and Comms-04 respectively to spread the interceptors across distinct threats. UAV-03, UAV-04, UAV-05, and UAV-06 have 0 ammo and are disengaged to conserve resources and avoid infeasible goals. USV-01 and USV-02 are tracking their respective targets to maintain sensor coverage."
}
```

## 调用 127（tick 1270）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01"}, "priority": 0.80, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4967, 6482]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [330, -14219]}, "priority": 0.1},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-18183, 1211]}, "priority": 0.1},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.5}
  ],
  "reasoning": "UAV-01 and UAV-08 assigned to strike-comms-03 (highest threat, closest to zone) as it is observed by UAV-04 (which is out of ammo). UAV-02 assigned to strike-command-02 (observed by USV-02, prepare_intercept=true). UAV-07 assigned to strike-command-01 (observed by UAV-04, high threat). UAV-03, 04, 05, 06 have 0 ammo and are disengaged to conserve energy/return to anchor. USVs continue tracking for sensor coverage."
}
```

## 调用 128（tick 1280）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [284.0, -14014.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-18401.0, 1100.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-01, 02, 07, and 08 are the only armed units. They are assigned to the four highest-threat contacts (fuel-04, command-02, comms-03, comms-04) to establish early intercept geometry, as all are currently outside weapon range but approaching. UAV-04 and USVs are out of ammo or have limited range, so they are tasked with tracking to maintain sensor coverage on the immediate threats. Unarmed UAVs are held in patrol to conserve energy and maintain position."
}
```

## 调用 129（tick 1290）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-01", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4982.0, 6882.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [307.0, -13805.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-18590.0, 951.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "UAV-01 is assigned to the highest threat (strike-comms-04, threat 0.98) which is closest to the zone (684m) and observed by UAV-04 (UAV-01 is the closest armed unit to that axis). UAV-02 is assigned to strike-command-04 (threat 0.94) which is observed by USV-02 and is approaching. UAV-08 is assigned to strike-comms-03 (threat 0.95) to cover the second highest threat. UAV-07 is assigned to strike-command-01 (threat 0.94) which is very close to the zone (348m) but receding; UAV-07 is the closest armed unit to that axis. USV-02 and USV-01 are used for tracking to maintain sensor coverage on the remaining threats. UAV-04, UAV-03, UAV-05, and UAV-
```

## 调用 130（tick 1300）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.95, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [5027.0, 7077.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [317.0, -13594.0]}, "priority": 0.5, "deadline": 100},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-18799.0, 828.0]}, "priority": 0.5, "deadline": 100}
  ],
  "reasoning": "All targets are currently receding or far outside weapon range (range_ratio > 1.0). No unit has can_intercept=true. The highest threat (strike-fuel-04) is approaching but still far (dist_zone=624m, but closing speed is low and it is receding relative to some sensors, or approaching slowly). Since no immediate intercept is feasible or required by the 'prepare_intercept' flag (all false), I am holding armed units in position to maintain coverage and tracking sensors on the primary threats to update their vectors. UAV-04 is out of ammo, so it holds position. USVs track the primary threats to maintain sensor fusion."
}
```

## 调用 131（tick 1310）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04"}, "priority": 0.8},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16331.0, 14060.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [5060.0, 7276.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [338.0, -13385.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19002.0, 692.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19183.0, 1557.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-69.0, 12925.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. Most targets are receding or far away (dist > 10km). UAVs 03-06 have 0 ammo. UAVs 01, 02, 07, 08 have ammo but are far from the closest threats (strike-command-04, strike-command-03) which are near the USVs. USVs are tracking the closest contacts to maintain sensor coverage. Holding positions for UAVs is appropriate as no immediate intercept is feasible or required."
}
```

## 调用 132（tick 1320）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4937.0, 7428.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [309.0, -13173.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19222.0, 600.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8566.0, -5204.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1246.0, 2991.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true. Several high-threat targets (strike-command-03, strike-command-04, strike-fuel-04, strike-comms-03) are approaching the protected zone (dist_zone < 1500m) and are within feasible intercept range for specific armed UAVs (uav-01, uav-02, uav-07, uav-08). I am assigning these armed units to intercept their respective closest/feasible targets to prevent zone entry. Units with 0 ammo (uav-03, 04, 05, 06) are disengaged to conserve energy/return to anchor. USVs are holding position as sensors."
}
```

## 调用 133（tick 1330）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.95, "deadline": 50},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04"}, "priority": 0.6},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16465.0, 14204.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [264.0, -12965.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19415.0, 457.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19580.0, 1459.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-215.0, 13215.0]}, "priority": 0.5}
  ],
  "reasoning": "strike-comms-04 is the only contact with prepare_intercept=true and is approaching the zone (dist 866m, ttr 36.9t). defender.usv-02 is the only unit with ammo and domain_ok=false for the others, but it is the closest to this target (3346m) and can engage if it enters range. Other targets are receding or far away, so sensors track them while armed UAVs hold position to conserve ammo."
}
```

## 调用 134（tick 1340）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367, 19998]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16532, 14361]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [193, -12766]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19621, 339]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19786, 1436]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-289, 13361]}, "priority": 0.5}
  ],
  "reasoning": "strike-comms-03 is the only contact with prepare_intercept=true (TTR 26.6t, approaching). It is observed by usv-01, usv-02, and uav-04. usv-01 and usv-02 are sensors (no ammo), so they must track to maintain observation. uav-04 has 0 ammo, so it also tracks to maintain observation. No armed unit (uav-01, uav-02, uav-07, uav-08) currently observes this contact, so no intercept can be issued yet. All other contacts are receding or have very long TTRs and no prepare_intercept flag, so armed units hold position to conserve ammo and wait for new threats or observation updates."
}
```

## 调用 135（tick 1350）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4924, 7821]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [133, -12558]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19819, 207]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8710, -5311]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1236, 3100]}, "priority": 0.4}
  ],
  "reasoning": "strike-comms-04 is the only contact with prepare_intercept=true (TTR 56.6t) and is closest to the zone (746m). Assigning uav-01 (closest armed unit, 20km away) to intercept it now to maneuver into position. Other high-threat contacts (command-04, comms-03, fuel-04) are approaching but further out; assigning remaining armed UAVs (uav-02, uav-07, uav-08) to intercept them to establish early engagement geometry. UAVs with 0 ammo are disengaged to conserve energy/return to anchor. USVs hold position to maintain sensor coverage."
}
```

## 调用 136（tick 1360）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-command-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16557.0, 14543.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4928.0, 8024.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [60.0, -12358.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 56.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 1398.0]}, "priority": 0.5}
  ],
  "reasoning": "USV-02 has prepare_intercept=true for strike-comms-03 (TTR 51t) and is the only unit with ammo in that sector, so it must engage immediately. UAV-08 has prepare_intercept=true for strike-command-03 (TTR 55t) and is the closest armed UAV to that threat, so it is assigned to intercept. USV-01 tracks the fuel intruder to maintain sensor coverage. Other units hold position to conserve energy and maintain sector coverage, as no other immediate intercept triggers are active."
}
```

## 调用 137（tick 1370）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-command-01"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16678.0, 14672.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4858.0, 8207.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [-57.0, -12181.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 56.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 1398.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-450.0, 13657.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are either receding, stable, or approaching too slowly to warrant immediate intercept maneuvering given the large range gaps (1000m+). Sensors (USVs) are tasked to track the closest threats to maintain observation. Interceptors hold position to conserve energy and maintain coverage, ready to react if any threat enters the intercept window."
}
```

## 调用 138（tick 1380）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [16757.0, 14846.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 1398.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-526.0, 13793.0], "commit_within_m": 9000}, "priority": 0.9, "deadline": 120},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4841.0, 8407.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-92.0, -11977.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 56.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8851.0, -5420.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1230.0, 3224.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept=true. All threats are far (dist_zone > 300m but range_gap > 1000m for most, or receding). UAVs 03-06 have 0 ammo and are disengaged to conserve energy/return to anchor. Armed UAVs (01, 02, 07, 08) are placed in reserve mode to react automatically if threats close within 9000m. USVs continue patrol for sensor coverage."
}
```

## 调用 139（tick 1390）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.85, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [8900.0, -5451.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1226.0, 3266.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-03", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-04", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-05", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_004", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-06", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "No targets have can_intercept=true. However, strike-comms-03 has prepare_intercept=true (ttr=32.5s) and is the closest threat to the zone (dist_zone=853m). I am assigning the closest armed interceptor (uav-01) to intercept it immediately to maneuver into position. I am also assigning other armed interceptors (uav-02, uav-07, uav-08) to the other high-threat contacts (strike-fuel-04, strike-comms-04, strike-command-02) to begin early maneuvering, as they are all approaching and will soon enter the intercept window. Unarmed UAVs are holding to conserve energy and maintain sensor coverage."
}
```

## 调用 140（tick 1400）

```
{
  "goal_commands": [
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [2367, 19998], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [16800, 15218], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4857, 8517]}, "priority": 0.5},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [-49, -11601]}, "priority": 0.5},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 56]}, "priority": 0.5},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998, 1116], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-695, 14089], "commit_within_m": 9000}, "priority": 0.8},
    {"task_id": "track_usv01_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6},
    {"task_id": "track_usv02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-command-02"}, "priority": 0.6}
  ],
  "reasoning": "No targets have can_intercept or prepare_intercept true. All threats are either receding or far away (dist_zone > 600m, range_gap > 1000m). UAVs with ammo (01, 02, 07, 08) are placed in reserve to react if threats approach. UAVs without ammo (03, 04, 05, 06) are disengaged to conserve energy/return to anchor. USVs continue tracking their assigned contacts for sensor fusion."
}
```

## 调用 141（tick 1410）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4899, 8376]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [103, -11466]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19874, 102]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.6}
  ],
  "reasoning": "Three high-threat intruders are approaching the protected zone. UAV-01 and UAV-02 are the closest armed units to the primary threats (comms-04 and fuel-04) and are assigned to intercept them. UAV-07 is assigned to intercept comms-03, which is observed by UAV-04 (sensor) and is the third distinct threat. UAV-08 is assigned to track/intercept comms-04 as a secondary layer or reserve if the primary interceptors fail, though it is further away. Units with 0 ammo (UAV-03, 04, 05, 06) are disengaged to conserve energy or return to base. USVs are tasked with tracking to maintain sensor coverage on the threats."
}
```

## 调用 142（tick 1420）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367, 19998]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16753, 15607]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4770, 8416]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [285, -11366]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19798, -83]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998, 891]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-936, 14339]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (dist > 9000m) and receding or stable. USVs are tracking the closest contacts to maintain sensor ownership. UAVs are holding position to conserve energy and maintain coverage, as no immediate engagement is feasible or required."
}
```

## 调用 143（tick 1430）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16707.0, 15802.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4778.0, 8354.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [483.0, -11309.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19954.0, 30.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1047.0, 14468.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9090.0, -5530.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1259.0, 3429.0]}, "priority": 0.5}
  ],
  "reasoning": "All contacts are far from the protected zone (dist_zone ~650m) and are currently receding or stable. No targets have can_intercept=true or prepare_intercept=true. Interceptors are holding position to conserve energy and maintain coverage until threats approach the intercept window."
}
```

## 调用 144（tick 1440）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4744.0, 8235.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [685.0, -11261.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19980.0, 234.0]}, "priority": 0.5},
    {"task_id": "disengage_005", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "disengage_006", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-01", "position": [9138.0, -5546.0]}, "priority": 0.5},
    {"task_id": "disengage_007", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [1262.0, 3469.0]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat intruders are approaching the protected zone. UAV-01, UAV-02, and UAV-08 are the only armed units with feasible intercept paths (or closest to feasible) and are assigned to the three distinct targets to maximize kill probability and spread fire. All other units are unarmed (ammo=0) or sensors (USVs) and are disengaged to return to anchor positions to conserve energy and avoid cluttering the airspace."
}
```

## 调用 145（tick 1450）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04"}, "priority": 0.8},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.7},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.7},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 370]}, "priority": 0.5}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. All threats are far (10km+) and mostly receding or stable. UAV-04 and UAV-05 are closest to the threat cluster but have 0 ammo, so they are tasked with tracking to maintain sensor coverage. Armed UAVs (01, 02, 07, 08) are tasked with intercept maneuvers to close the distance and prepare for engagement as the threats approach or if they turn. UAV-03 and UAV-06 are out of position and out of ammo, so they are disengaged to return to rear anchors. USVs are tasked with tracking to maintain sensor fusion."
}
```

## 调用 146（tick 1460）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.8},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16419.0, 16330.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4986.0, 8419.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [1039.0, -11070.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19949.0, 594.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1382.0, 14839.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (dist > 10km) and mostly receding or stable. Interceptors are holding position to conserve energy and maintain coverage. Sensors are tracking the closest contacts to maintain continuous observation."
}
```

## 调用 147（tick 1470）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4906.0, 8348.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [1243.0, -11039.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 761.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1499.0, 14965.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9288.0, -5596.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1275.0, 3596.0]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat intruders (strike-fuel-04, strike-comms-03, strike-comms-04) are approaching the protected zone with ETAs of ~525t, ~502t, and ~498t respectively. All are currently outside weapon range (range_ratio > 2.0) and no unit has can_intercept=true. However, strike-fuel-04 is the closest to the zone (dist_zone=484m) and approaching at 16.87m/t, making it the highest priority. I am assigning the three armed UAVs (uav-01, uav-02, uav-07) to intercept the three distinct threats to spread fire discipline and maximize coverage. uav-01 is closest to strike-fuel-04's approach vector, uav-02 to strike-comms-03, and uav-07 to strike-comms-04. All other units are unarmed or out of position, so they are held on patrol to maintain sensor coverage and readiness."
}
```

## 调用 148（tick 1480）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04"}, "priority": 0.7},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.7},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [1448.0, -11073.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 761.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true, but strike-comms-03 is approaching (ttr=78t) and strike-fuel-04 is approaching (ttr=173t). UAV-01 and UAV-02 are the closest armed units to these threats respectively, so they are assigned to intercept to maneuver into position. UAV-07 and UAV-08 are assigned to intercept the remaining threat (strike-comms-04) and reinforce strike-comms-03 coverage. Sensor units (UAV-04, USV-01, USV-02) are tasked to track the threats to maintain observation for the armed units. Out-of-range or out-of-domain units (UAV-03, 05, 06) are held in patrol to conserve energy and maintain situational awareness."
}
```

## 调用 149（tick 1490）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-05", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04"}, "priority": 0.6, "deadline": 100},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6, "deadline": 100},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998, 891], "commit_within_m": 9000}, "priority": 0.5, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.2, "deadline": 100},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 761]}, "priority": 0.2, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1291, 3680]}, "priority": 0.4, "deadline": 100}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (range_ratio > 1.2) and feasible=false for all interceptors. UAV-01, UAV-02, and UAV-08 are the only armed units with ammo. They are assigned to intercept the three distinct threats (strike-fuel-04, strike-comms-04, strike-comms-03) to maneuver into position early, as per the rule to start intercept maneuvering when threats are approaching, even if can_intercept is false, to prepare for the eventual engagement window. UAV-04, UAV-05, and USV-01 are tracking their respective observed targets to maintain sensor contact. UAV-07 is held in reserve. UAV-03 and UAV-06 have 0 ammo and are disengaged to rear anchors. USV-02 is patrolling its current position as it is a sensor-only unit (domain_ok=false for air targets) and cannot engage."
}
```

## 调用 150（tick 1500）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 150},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 150},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 150},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4469.0, 8125.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [1827.0, -10936.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19982.0, 874.0]}, "priority": 0.5},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-1887.0, 15320.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.7}
  ],
  "reasoning": "Three high-threat intruders are approaching the protected zone. UAV-01, UAV-02, and UAV-07 are the only armed units with sufficient range and positioning to engage them before they cross the boundary. UAV-04 and UAV-05 are out of ammo and currently tracking targets, so they are disengaged to conserve energy or reposition. UAV-03, UAV-06 are also out of ammo. UAV-08 is held in reserve. USVs continue tracking to maintain sensor coverage."
}
```

## 调用 151（tick 1510）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16340.0, 16529.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4387.0, 8272.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [2026.0, -10878.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 900.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-1990.0, 15467.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are currently receding from the protected zone and are far outside the effective intercept window (can_intercept=false, prepare_intercept=false). The USVs are the primary sensors tracking these contacts. The UAVs are holding position to conserve energy and maintain coverage, ready to engage if the intruders turn back or if new threats appear. No immediate interception is required as the threats are moving away."
}
```

## 调用 152（tick 1520）

```
{
  "goal_commands": [
    {"task_id": "intercept_fuel_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_comms_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_comms_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "track_fuel_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04"}, "priority": 0.7},
    {"task_id": "track_comms_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.6},
    {"task_id": "track_comms_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.6},
    {"task_id": "reserve_uav_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0], "commit_within_m": 9000}, "priority": 0.5},
    {"task_id": "disengage_uav_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.4},
    {"task_id": "disengage_uav_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2233.0, -10900.0]}, "priority": 0.4},
    {"task_id": "disengage_uav_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19954.0, 1006.0]}, "priority": 0.4}
  ],
  "reasoning": "Three high-threat intruders (fuel-04, comms-04, comms-03) are approaching the protected zone. UAV-01, UAV-02, and UAV-08 are the only armed units with feasible intercept paths (feasible_eta < target ETA to zone). Assigning them to distinct targets to maximize kill probability. UAV-04 and USVs are tracking to maintain sensor coverage. UAV-07 held in reserve. Out-of-ammo units (UAV-03, 05, 06) disengaged to conserve energy and avoid clutter."
}
```

## 调用 153（tick 1530）

```
{
  "goal_commands": [
    {"task_id": "track_fuel_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9},
    {"task_id": "track_comms_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-04.intruder.strike-comms-03"}, "priority": 0.8},
    {"task_id": "track_comms_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.7},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [16214.0, 16899.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav07_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_uav08_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2209.0, 15726.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "hold_uav03_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-03", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_uav05_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-05", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_uav06_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-06", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "All three intruders are currently receding from the protected zone and are far outside weapon range (range_ratio > 1.2). No unit has can_intercept or prepare_intercept set to true. To conserve ammunition and maintain situational awareness, sensors (USVs and UAV-04) are tasked to track the contacts. Armed UAVs are held in reserve positions to react if the intruders turn back or new threats emerge. Unarmed UAVs are held in place."
}
```

## 调用 154（tick 1540）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4548.0, 8199.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2627.0, -10779.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19940.0, 1314.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9646.0, -5702.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1322.0, 3893.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are extremely close to the protected zone (dist_zone < 900m) and are high-threat (0.89-0.97). No unit currently has can_intercept=true, but the threats are imminent. I am committing all four armed UAVs (uav-01, uav-02, uav-07, uav-08) to intercept the highest threat (strike-comms-03) to maximize the probability of a kill before it enters the zone. The other two intruders are also critical, but I am prioritizing the highest threat first; if the first wave is not stopped, the remaining missiles will be needed for the others. Unarmed UAVs are disengaged to conserve energy or return to base. USVs are holding position to maintain sensor coverage."
}
```

## 调用 155（tick 1550）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4615.0, 8314.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [2837.0, -10770.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19876.0, 1510.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9697.0, -5717.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1326.0, 3933.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (dist > 9km) and receding or approaching slowly. UAV-03, 04, 05, 06 have 0 ammo and are disengaged to hold positions. Armed UAVs (01, 02, 07, 08) are assigned to intercept the closest threats to maintain forward presence and prepare for engagement as targets close. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 156（tick 1560）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16140.0, 17481.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3044.0, -10750.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19863.0, 1737.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-2563.0, 16100.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (dist_zone > 500m) and mostly receding or approaching slowly. USVs are tracking the closest contacts to maintain sensor ownership. UAVs are holding position to conserve energy and wait for threats to enter the intercept window, as firing now would be ineffective or waste ammunition on targets that are not yet in range."
}
```

## 调用 157（tick 1570）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 300},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-05.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 300},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4545, 8299]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3245, -10709]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19993, 1918]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-2669, 16237]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9804, -5749]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1336, 4012]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (dist > 9km) and mostly receding or stable. UAV-01, 02, and 07 have ammo and are closest to the threat axis (bearing ~180-220). Assigning them to intercept the three distinct threats to prepare for engagement as they approach. Other units are out of ammo or too far, so they hold position to maintain sensor coverage."
}
```

## 调用 158（tick 1580）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4505.0, 8390.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [3454.0, -10729.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 1920.0]}, "priority": 0.5},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-2779.0, 16381.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.8}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. All targets are far outside weapon range (range_ratio > 1.2) and feasible=false for all interceptors, meaning they will reach the zone before any interceptor can engage. UAV-03, 04, 05, 06 have 0 ammo and are useless for engagement, so they are disengaged to rear anchors. UAV-01 and UAV-02 have ammo and are closest to the threat axis (bearing ~188-224), so they are tasked to intercept the highest threat (strike-fuel-04) and second highest (strike-comms-04) respectively to position for future engagement. UAV-07 and UAV-08 are held in reserve. USVs track the closest contacts to maintain sensor coverage."
}
```

## 调用 159（tick 1590）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [16087.0, 17682.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4402.0, 8490.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3655.0, -10700.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19978.0, 2010.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-2919.0, 16492.0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9904.0, -5767.0]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1351.0, 4095.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All contacts are either receding or have ETAs far in the future (400+ ticks) and are outside weapon range. Interceptors are holding position to conserve energy and maintain coverage. Sensors continue tracking."
}
```

## 调用 160（tick 1600）

```
{
  "goal_commands": [
    {"task_id": "ambush_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.95, "deadline": 100},
    {"task_id": "ambush_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.95, "deadline": 100},
    {"task_id": "ambush_003", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.95, "deadline": 100},
    {"task_id": "ambush_004", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 500}, "priority": 0.95, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4307, 8389]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [3855, -10654]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19972, 2227]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9949, -5783]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1358, 4136]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are currently receding from the protected zone (negative closing speed) and are far outside weapon range (range_ratio > 1.2). No unit has can_intercept or prepare_intercept true. The highest threat (strike-comms-04) is the primary target. I am positioning the four armed UAVs (uav-01, uav-02, uav-07, uav-08) to ambush the lead threat at its expected intercept point, ensuring we have multiple shooters ready when it turns or approaches. Unarmed units are holding position to maintain sensor coverage."
}
```

## 调用 161（tick 1610）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [9997.0, -5805.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1355.0, 4176.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are approaching the protected zone with high threat levels (0.91-0.95). strike-fuel-04 is the closest to the zone (508m) and has the highest closing speed (18.86 m/t), making it the most immediate threat. Although can_intercept is false for all, the targets are within the 'prepare' phase logic (approaching, high threat). I am assigning all four armed UAVs (uav-01, uav-02, uav-07, uav-08) to intercept strike-fuel-04 to ensure a kill before it breaches the zone, as it is the primary threat. The other two targets (comms-04 and comms-03) are slightly further out (682m and 771m) and will be engaged if fuel-04 is neutralized or if they become the closest threat in subsequent ticks. USVs are holding position to maintain sensor coverage."
}
```

## 调用 162（tick 1620）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4492, 8434]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4244, -10531]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 2245]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "All targets are far outside weapon range (range_ratio > 1.2) and no unit has can_intercept=true. However, strike-fuel-04 is the highest threat (0.97) and closest to the zone (600m). I am assigning all armed UAVs (01, 02, 07, 08) to intercept it to ensure coverage as it approaches. Unarmed UAVs (03, 04, 05, 06) are holding position to maintain sensor coverage. USVs are tracking the primary threat to provide continuous observation."
}
```

## 调用 163（tick 1630）

```
{
  "goal_commands": [
    {"task_id": "track_fuel_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9},
    {"task_id": "track_fuel_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15807.0, 18329.0]}, "priority": 0.5},
    {"task_id": "patrol_uav03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_uav04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4591.0, 8384.0]}, "priority": 0.5},
    {"task_id": "patrol_uav05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4441.0, -10486.0]}, "priority": 0.5},
    {"task_id": "patrol_uav06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2245.0]}, "priority": 0.5},
    {"task_id": "patrol_uav07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 891.0]}, "priority": 0.5},
    {"task_id": "patrol_uav08_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-3283.0, 16983.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders (strike-comms-03, strike-comms-04, strike-fuel-04) are currently receding or stable at distances >9km from the protected zone, with no interceptor having can_intercept=true or prepare_intercept=true. The closest interceptor (uav-04) is 9.8km away from the nearest target, well outside the 8km weapon range. Since the threats are moving away or holding position, immediate interception is not feasible or necessary. Sensors (usv-01, usv-02) are tasked to track the primary threat (strike-fuel-04) to maintain continuous observation. All UAVs are holding position to conserve energy and maintain coverage, ready to engage if the intruders turn and approach the protected zone."
}
```

## 调用 164（tick 1640）

```
{
  "goal_commands": [
    {"task_id": "ambush_comms03_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "standoff_m": 1000}, "priority": 0.95, "deadline": 300},
    {"task_id": "ambush_fuel04_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "standoff_m": 1000}, "priority": 0.95, "deadline": 300},
    {"task_id": "ambush_comms04_001", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "standoff_m": 1000}, "priority": 0.95, "deadline": 300},
    {"task_id": "ambush_comms03_002", "goal_type": "ambush", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "standoff_m": 1000}, "priority": 0.95, "deadline": 300},
    {"task_id": "disengage_uav03_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_uav04_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4586, 8201]}, "priority": 0.5},
    {"task_id": "disengage_uav05_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4636, -10426]}, "priority": 0.5},
    {"task_id": "disengage_uav06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19988, 2359]}, "priority": 0.5},
    {"task_id": "track_comms03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8},
    {"task_id": "track_comms04_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8}
  ],
  "reasoning": "All three high-threat intruders are approaching the protected zone (dist_zone < 1km) but are currently outside the weapon range of all armed interceptors (range_gap > 1km). Direct intercept is infeasible. I am deploying the four armed UAVs (uav-01, uav-02, uav-07, uav-08) to ambush positions along the threat axes to engage as soon as the targets enter weapon range. UAV-01 and UAV-08 cover the highest threat (comms-03), while UAV-02 covers fuel-04 and UAV-07 covers comms-04. Unarmed UAVs are disengaging to conserve energy or return to base. USVs are tracking to maintain sensor coverage."
}
```

## 调用 165（tick 1650）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4767.0, 8229.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [4801.0, -10306.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2380.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10210.0, -5871.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1355.0, 4338.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (dist > 9000m) and receding or stable. Armed UAVs (01, 02, 07, 08) are assigned to intercept the closest threats to maintain forward positioning and prepare for engagement as they approach. Unarmed units (03, 04, 05, 06, USVs) are held in patrol to maintain sensor coverage and positioning."
}
```

## 调用 166（tick 1660）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4856.0, 8116.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [4976.0, -10199.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2380.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10263.0, -5890.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1353.0, 4381.0]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. All threats are far (dist > 9km) and receding or stable. UAV-03, 04, 05, 06 have 0 ammo and are disengaged to conserve energy/position. Armed UAVs (01, 02, 07, 08) are assigned to intercept the closest high-threat contacts (comms-04, fuel-04, comms-03) to maintain forward positioning and readiness, using 'assess' fire policy to conserve ammo. USVs hold position for sensor coverage."
}
```

## 调用 167（tick 1670）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4746, 7972]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5152, -10095]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 2380]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.6},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03"}, "priority": 0.6}
  ],
  "reasoning": "No targets currently have can_intercept=true or prepare_intercept=true. All targets are far (10km-25km) and receding or stable. UAV-01, 02, 07, 08 have ammo and are assigned to intercept the closest threats to maintain positioning. UAV-03, 04, 05, 06 have 0 ammo and are on patrol to maintain sensor coverage. USVs are tracking their respective contacts."
}
```

## 调用 168（tick 1680）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15602.0, 18788.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4792.0, 8051.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5328.0, -9991.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2380.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19975.0, 496.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-3830.0, 17654.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far from the protected zone (dist_zone > 600m) and most are receding or stable. Interceptors are holding position to conserve fuel and maintain coverage. Sensors are tracking the closest contacts to maintain continuous observation."
}
```

## 调用 169（tick 1690）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4804.0, 7975.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5532.0, -9963.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2380.0]}, "priority": 0.5},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 460.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-3941.0, 17786.0], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.7},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.7}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (10km+) and receding or slowly approaching. UAV-01 and UAV-02 are the closest armed units to the threat axis (bearing ~190-220) and are assigned to intercept the highest threat contacts (strike-comms-04 and strike-fuel-04) to maneuver into position early. UAV-03, 04, 05, 06 have 0 ammo and are disengaged to rear anchors. UAV-07 and 08 are held as reserves with auto-commit triggers. USVs track their respective contacts for continuous sensor coverage."
}
```

## 调用 170（tick 1700）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4929.0, 7975.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [5726.0, -9901.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19947.0, 2556.0]}, "priority": 0.5},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.8}
  ],
  "reasoning": "All three intruders are approaching the protected zone (dist_zone < 1000m) with high threat levels. No unit currently has can_intercept=true, but the closest armed units (uav-01, uav-02, uav-07, uav-08) are assigned to intercept the highest threat (strike-comms-03) to establish a defensive screen. Units with 0 ammo are disengaged to conserve resources. Sensor USVs are tasked to track the primary threat to maintain observation for the interceptors."
}
```

## 调用 171（tick 1710）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03"}, "priority": 0.9},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.9},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15435.0, 19356.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [5008.0, 8130.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [5933.0, -9887.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19955.0, 2772.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, 460.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-4183.0, 18028.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (dist > 9000m) and mostly receding or approaching slowly. Interceptors are holding position to conserve ammo and wait for targets to enter the intercept window. Sensors continue tracking the closest threats to maintain situational awareness."
}
```

## 调用 172（tick 1720）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4998, 8090]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6137, -9855]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 2827]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10564, -5992]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1380, 4630]}, "priority": 0.5}
  ],
  "reasoning": "Three high-threat intruders (strike-comms-04, strike-fuel-04, strike-comms-03) are approaching the protected zone with ETAs of ~3800, ~960, and ~1700 ticks respectively. Although `can_intercept` is currently false for all, the threats are significant and approaching. UAV-01, UAV-02, and UAV-07 are the only armed units with sufficient ammo (2 each) and reasonable positioning to engage. UAV-01 is closest to strike-comms-04, UAV-02 is closest to strike-fuel-04, and UAV-07 is closest to strike-comms-03. Unarmed UAVs (03, 04, 05, 06) are disengaged to conserve energy or reposition, as they cannot fire. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 173（tick 1730）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 300},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.85, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 300},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-08", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.75, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4868.0, 8145.0]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6323.0, -9775.0]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19923.0, 2977.0]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10612.0, -6004.0]}, "priority": 0.4},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1393.0, 4667.0]}, "priority": 0.4}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (dist_zone < 1000m but range_gap > 1000m for most, or receding). UAV-03, 04, 05, 06 have 0 ammo and are disengaged to conserve energy/position. Armed UAVs (01, 02, 07, 08) are assigned to intercept the closest/approaching threats (comms-03, fuel-04, comms-04) to prepare for engagement as they close. USVs are on patrol to maintain sensor coverage."
}
```

## 调用 174（tick 1740）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 100},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-04", "position": [4688.0, 8220.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6500.0, -9673.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2975.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-4543.0, 18408.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10659.0, -6024.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1402.0, 4708.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All targets are far (range_ratio > 1.2) and feasible=false for all interceptors, meaning they will reach the zone before any interceptor can engage. UAV-04 and USV-01 are out of ammo. UAV-01, UAV-02, and UAV-07 have ammo and are closest to the threat axis (bearing ~190-220). Assigning them to intercept the highest threat (strike-fuel-04) and next highest (strike-comms-04, strike-comms-03) to maneuver into position as early as possible, even though current engagement is infeasible, to prepare for future engagement windows. Other units hold position to conserve energy and maintain sensor coverage."
}
```

## 调用 175（tick 1750）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 90},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 450},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-07", "position": [-19980, 43], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-08", "position": [-4659, 18537], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.2},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [6698, -9628]}, "priority": 0.2},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19998, 2975]}, "priority": 0.2},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 is closest to the threat cluster (range_gap ~1.5km) and is assigned to intercept strike-comms-03 which it observes directly. UAV-01 and UAV-02 are assigned to intercept the other two high-threat contacts they observe (strike-comms-04 and strike-fuel-04 respectively) to spread fire discipline and cover the approaching wave. UAV-07 and UAV-08 are held as reserves with auto-commit triggers to react to any new threats or if the primary interceptors fail. UAV-03, 05, and 06 have no ammunition and are disengaged to return to anchor. USVs continue tracking their respective contacts to maintain sensor coverage."
}
```

## 调用 176（tick 1760）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.95, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.strike-comms-04"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15376.0, 19562.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [6896.0, -9574.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19998.0, 2975.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, -33.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-4788.0, 18656.0]}, "priority": 0.5}
  ],
  "reasoning": "UAV-04 has prepare_intercept=true for strike-comms-03 (TTR 57t) and is the only unit with a feasible intercept window (34t), so it is assigned to intercept immediately. USV-02 and USV-01 are tracking the other two intruders to maintain sensor coverage. All other UAVs are holding position as they are too far away to engage the current threats effectively."
}
```

## 调用 177（tick 1770）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.7, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1430.0, 4835.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10794.0, -6071.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-03", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-05", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-06", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_004", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-07", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_005", "goal_type": "hold", "parameters": {"unit_id": "defender.uav-08", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "No targets have can_intercept=true. strike-comms-04 is the closest approaching threat (dist_zone=864m, closing=18m/t). uav-01 and uav-02 are assigned to intercept it to prepare for engagement. uav-04 is assigned to intercept strike-fuel-04 (dist_zone=584m, closing=18m/t) as it is the closest to the zone. Other units are held or patrolling as they are out of range or have no ammo."
}
```

## 调用 178（tick 1780）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 300},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04", "fire_policy": "assess"}, "priority": 0.9, "deadline": 300},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-07", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-04", "fire_policy": "assess"}, "priority": 0.8, "deadline": 300},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-03", "position": [6707, 19998]}, "priority": 0.5},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-04", "position": [4480, 8073]}, "priority": 0.5},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-05", "position": [7309, -9508]}, "priority": 0.5},
    {"task_id": "disengage_004", "goal_type": "disengage", "parameters": {"unit_id": "defender.uav-06", "position": [-19753, 3050]}, "priority": 0.5},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10831, -6086]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [1432, 4878]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are far (10km-25km) and receding or stable. UAV-03, 04, 05, 06 have 0 ammo and are disengaged to conserve energy/return to base. UAV-01, 02, 07 have ammo and are positioned to intercept the closest threats (comms-03, fuel-04, comms-04) respectively, maintaining spread. USVs are on patrol for sensor coverage."
}
```

## 调用 179（tick 1790）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-04", "target_id": "sensor.contact.defender.uav-04.intruder.strike-comms-03"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.strike-fuel-04"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [2367.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [15291.0, 19740.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-03", "position": [6707.0, 19998.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-05", "position": [7498.0, -9443.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-06", "position": [-19853.0, 2934.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-07", "position": [-19998.0, -33.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-08", "position": [-5154.0, 19029.0]}, "priority": 0.5},
    {"task_id": "patrol_008", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [10880.0, -6099.0]}, "priority": 0.5}
  ],
  "reasoning": "No targets have can_intercept=true or prepare_intercept=true. All threats are either receding or far outside weapon range (range_ratio > 1.18). UAV-04 and USV-02 are the primary sensors observing the closest contacts (strike-comms-03 and strike-fuel-04 respectively) and should continue tracking to maintain situational awareness. Other units are holding position to conserve energy and maintain coverage, as no immediate engagement is feasible or required."
}
```

