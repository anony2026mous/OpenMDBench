# 案例 E5-07-ec97 — LLM 规划器原始输出

## 调用 0（tick 0）

```
{
  "goal_commands": [
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [3200, 1200]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [3600, 0]}, "priority": 0.5},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1800, -200]}, "priority": 0.5},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2400, 800]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2200, -1400]}, "priority": 0.5},
    {"task_id": "patrol_usv04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1500, 1200]}, "priority": 0.5},
    {"task_id": "patrol_usv05_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [2800, -400]}, "priority": 0.5},
    {"task_id": "patrol_usv06_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [3000, 1400]}, "priority": 0.5},
    {"task_id": "patrol_usv07_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3400, -800]}, "priority": 0.5}
  ],
  "reasoning": "No hostile contacts detected in the current situation report. All units are holding their current positions to maintain sensor coverage and readiness for incoming threats."
}
```

## 调用 1（tick 10）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat01_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "reserve_uav01_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-01", "position": [3309, 1349], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "reserve_uav02_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.uav-02", "position": [3545, 160], "commit_within_m": 9000}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_usv01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1809, -190]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2407, 793]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2212, -1396]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_usv04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1509, 1209]}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "Three intruders (boat-01, boat-02, boat-03) are currently within weapon range of specific USVs (usv-07, usv-05, usv-06 respectively) and have can_intercept=true. I am assigning each USV to intercept its respective closest threat to spread fire and conserve UAV ammo. The UAVs are held in reserve to react to any breakthroughs or new waves, while remaining USVs maintain patrol positions for sensor coverage."
}
```

## 调用 2（tick 20）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.usv-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-03.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.facility.berth.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-06", "target_id": "sensor.contact.defender.usv-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [2402.0, 768.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-07", "position": [3423.0, -771.0]}, "priority": 0.5, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2235.0, -1409.0]}, "priority": 0.4, "deadline": 120},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1489.0, 1228.0]}, "priority": 0.4, "deadline": 120}
  ],
  "reasoning": "UAVs are the primary interceptors due to speed and ammo. UAV-01 targets boat-03 (prepare=true, approaching) to intercept early. UAV-02 targets boat-01 (highest threat, approaching). USV-01 targets boat-01 (can_intercept=true) as a secondary layer. USV-05 targets boat-02 (can_intercept=true). USV-06 targets boat-03 (can_intercept=true). USV-02 and USV-07 are out of ammo and disengaged to conserve energy/avoid collision. USV-03 and USV-04 hold position to maintain sensor coverage."
}
```

## 调用 3（tick 30）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.85, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03"}, "priority": 0.80, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.defender.usv-03.intruder.boat-03"}, "priority": 0.75, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.70, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.65, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.60, "deadline": 120},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02"}, "priority": 0.55, "deadline": 120}
  ],
  "reasoning": "UAV-01 is assigned to intercept boat-01 (highest threat, closest to zone) as it is the only unit with sufficient speed and ammo to engage effectively before the target reaches the boundary. UAV-02 is assigned to intercept boat-03 (prepare_intercept=true) to prevent it from entering the zone. Boat-02 is currently receding from most sensors but approaching the zone from a different axis; multiple USVs are tracking it to maintain continuous observation and prepare for engagement if it turns or if UAVs need to re-task. USV-02 and USV-06/07 have no ammo and are used for tracking only. USV-01, 03, 04, 05 have ammo but are too slow to intercept effectively before the targets reach the zone, so they are used for tracking to maintain sensor coverage."
}
```

## 调用 4（tick 40）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03"}, "priority": 0.7, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-01"}, "priority": 0.4, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-03"}, "priority": 0.3, "deadline": 120},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.2, "deadline": 120}
  ],
  "reasoning": "UAV-01 is assigned to intercept boat-01 (highest threat, closest to zone) as it is the only armed unit with a clear line of sight and sufficient ammo. UAV-02 is assigned to intercept boat-03 (prepare_intercept=true, approaching) to engage it before it reaches the zone. USVs are used for tracking to maintain sensor coverage and update target states, as they are slower and have limited ammo. Boat-02 is being tracked by USV-05 and USV-04 to monitor its approach."
}
```

## 调用 5（tick 50）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-03"}, "priority": 0.5, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [2415, 649]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-06", "position": [2974, 1502]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-07", "position": [3482, -671]}, "priority": 0.2, "deadline": 120}
  ],
  "reasoning": "All three intruders are approaching the protected zone with high threat levels. UAV-01 and UAV-02 are assigned to intercept boat-01 and boat-02 respectively, as they are the closest and most immediate threats. USV-05 is assigned to intercept boat-03, which is slightly further out but still within effective range. USV-01, USV-03, and USV-04 are tasked with tracking their respective targets to maintain situational awareness and provide backup if needed. USV-02, USV-06, and USV-07 have no ammunition and are disengaged to conserve resources and avoid unnecessary risk."
}
```

## 调用 6（tick 60）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1910, 16]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2415, 611]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2386, -1456]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1343, 1335]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2965, 1533]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3507, -640]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are approaching the protected zone. UAV-01 and UAV-02 are the primary interceptors with high speed and ammo; they are assigned to the two closest threats (boat-01 and boat-02) to engage before they cross the boundary. USV-05 is assigned to boat-03 as it is the closest armed sensor to that target and has ammo. Other USVs are held in patrol to maintain sensor coverage and act as reserves, as they are slower and some have no ammo."
}
```

## 调用 7（tick 70）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "reserve_001", "goal_type": "reserve", "parameters": {"unit_id": "defender.usv-01", "position": [1930, 61], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_002", "goal_type": "reserve", "parameters": {"unit_id": "defender.usv-03", "position": [2425, -1472], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "reserve_003", "goal_type": "reserve", "parameters": {"unit_id": "defender.usv-04", "position": [1303, 1357], "commit_within_m": 9000}, "priority": 0.6},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [2421, 571]}, "priority": 0.3},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-06", "position": [2954, 1564]}, "priority": 0.3},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-07", "position": [3529, -606]}, "priority": 0.3}
  ],
  "reasoning": "Three high-threat intruders (boat-01, boat-02, boat-03) are approaching the protected zone. UAV-01 and UAV-02 are assigned to intercept boat-01 and boat-02 respectively, as they are the closest and highest threat. USV-05 is assigned to intercept boat-03, which is slightly further out. USV-01, USV-03, and USV-04 are held in reserve to react to any new threats or if the primary interceptors fail. USV-02, USV-06, and USV-07 have no ammunition and are disengaged to return to their positions to conserve energy and avoid being vulnerable."
}
```

## 调用 8（tick 80）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [1951, 106]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2428, 530]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2465, -1487]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1265, 1381]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2942, 1596]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3552, -573]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are approaching the protected zone (distances 3200-4100m) and are within sensor range of multiple units. UAV-01 and UAV-02 are assigned to intercept boat-01 and boat-02 respectively, as they are the closest threats and the UAVs have the speed to engage effectively. USV-05 is assigned to intercept boat-03, which is the furthest but still a high threat. The other USVs are holding position to maintain sensor coverage and provide backup, as they are slower and may not be able to intercept before the intruders reach the zone. Fire policy is set to 'assess' to conserve ammunition, as the intruders are still at a distance and there is time to evaluate the effect of the first shot."
}
```

## 调用 9（tick 90）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.90, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [3962.0, 2850.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [2555.0, 1474.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2433.0, 487.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1223.0, 1400.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2931.0, 1627.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3574.0, -542.0]}, "priority": 0.5}
  ],
  "reasoning": "Three intruders (boat-01, boat-02, boat-03) are approaching the protected zone. boat-01 is closest (3158m) and highest threat (0.92), assigned to usv-01 which has can_intercept=true and ammo. boat-02 (3511m, threat 0.90) assigned to usv-03 (can_intercept=true, ammo). boat-03 (4024m, threat 0.88) assigned to usv-05 (can_intercept=true, ammo). UAVs and other USVs are on patrol to maintain sensor coverage and reserve positions. Fire policy set to 'assess' to conserve ammunition given the possibility of decoys and multiple waves."
}
```

## 调用 10（tick 100）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 110},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 110},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.90, "deadline": 110},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.6, "deadline": 110},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 110},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1181, 1421]}, "priority": 0.4, "deadline": 110},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2437, 445]}, "priority": 0.4, "deadline": 110},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2922, 1659]}, "priority": 0.4, "deadline": 110},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3594, -511]}, "priority": 0.4, "deadline": 110}
  ],
  "reasoning": "All three intruders are approaching the protected zone (dist_zone 3050-3935m) with high threat (0.90-0.91). UAV-01 and UAV-02 are the primary armed assets with 3 missiles each; they are assigned to intercept boat-01 and boat-02 respectively. USV-05 is assigned to intercept boat-03 as it is the closest armed USV to that target (dist 2453m, can_intercept=true). USV-01 and USV-03 are tracking their respective targets to maintain sensor coverage. USV-02, USV-06, and USV-07 have 0 ammo and are holding position to maintain sensor coverage. USV-04 is holding position as it is too far to effectively engage any target immediately (feasible_eta > 0 for all)."
}
```

## 调用 11（tick 110）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-01"}, "priority": 0.5},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-03"}, "priority": 0.5},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-01"}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are approaching the protected zone with high threat levels (0.91-0.93). UAV-01 and UAV-02 are the primary armed assets with sufficient ammo (3 each) and are assigned to intercept the two closest/most threatening targets (boat-01 and boat-02) using 'assess' fire policy to conserve ammunition. USV-05 is assigned to intercept boat-03 as it is the closest armed USV to that target and has ammo. Other USVs are assigned to track their respective targets to maintain sensor coverage and provide updated data for the interceptors, as they are either out of range or have no ammo (USV-02, USV-06, USV-07)."
}
```

## 调用 12（tick 120）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-01", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4215.0, 3423.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [2133.0, 1928.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2457.0, 362.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1096.0, 1464.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2901.0, 1724.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3636.0, -450.0]}, "priority": 0.5}
  ],
  "reasoning": "All three intruders are approaching the protected zone (distances 2888m, 3242m, 3763m) and are within weapon range of specific USVs. USV-01, USV-03, and USV-05 are assigned to intercept boat-01, boat-02, and boat-03 respectively, as they have the best geometry and ammo. UAVs and other USVs are held in patrol to maintain sensor coverage and reserve capacity, as they are either out of range or have no ammo."
}
```

## 调用 13（tick 130）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.site.shore-radar.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 140},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.usv-04.intruder.boat-03", "fire_policy": "assess"}, "priority": 0.9, "deadline": 140},
    {"task_id": "disengage_usv02_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [2464.0, 323.0]}, "priority": 0.3},
    {"task_id": "disengage_usv06_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-06", "position": [2890.0, 1756.0]}, "priority": 0.3},
    {"task_id": "disengage_usv07_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-07", "position": [3657.0, -416.0]}, "priority": 0.3},
    {"task_id": "patrol_uav01_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [4314.0, 3611.0]}, "priority": 0.5},
    {"task_id": "patrol_uav02_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [1988.0, 2077.0]}, "priority": 0.5},
    {"task_id": "patrol_usv03_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2657.0, -1560.0]}, "priority": 0.5},
    {"task_id": "patrol_usv04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1056.0, 1491.0]}, "priority": 0.5}
  ],
  "reasoning": "Boat-02 (threat 0.93) and Boat-03 (threat 0.91) are the primary active threats. USV-01 and USV-05 are the closest armed units with can_intercept=true for their respective targets and are assigned to engage with 'assess' policy to conserve ammo. USV-02, USV-06, and USV-07 have 0 ammo and are disengaged to return to anchor. UAVs and remaining USVs are held in patrol to maintain sensor coverage and reserve readiness, as they are either out of range or have lower priority than the immediate interceptors."
}
```

## 调用 14（tick 140）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 145},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 145},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 145},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.8, "deadline": 145},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 145},
    {"task_id": "intercept_006", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 145},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [2459.0, 289.0]}, "priority": 0.1},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-06", "position": [2875.0, 1787.0]}, "priority": 0.1},
    {"task_id": "disengage_003", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-07", "position": [3679.0, -384.0]}, "priority": 0.1}
  ],
  "reasoning": "Two high-threat intruders (boat-02, boat-03) are approaching the protected zone. Boat-02 is closer (3044m) and has multiple units with can_intercept=true. Boat-03 is slightly further (3574m) but also has can_intercept=true for several units. I am assigning the closest armed units with can_intercept=true to engage boat-02 (USV-01, USV-03, USV-05) to ensure a kill, and USV-04 to engage boat-03. UAVs are assigned to boat-02 as backup since they are further away but have high speed. USV-02, USV-06, and USV-07 have 0 ammo and are disengaged to conserve resources and avoid wasting time on targets they cannot engage."
}
```

## 调用 15（tick 150）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "intercept_boat03_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-03", "fire_policy": "assess"}, "priority": 0.95, "deadline": 160},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.8, "deadline": 160},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-03"}, "priority": 0.8, "deadline": 160},
    {"task_id": "track_boat03_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-03"}, "priority": 0.8, "deadline": 160},
    {"task_id": "track_boat02_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.8, "deadline": 160},
    {"task_id": "return_001", "goal_type": "return", "parameters": {"unit_id": "defender.usv-02"}, "priority": 0.2, "deadline": 160},
    {"task_id": "return_002", "goal_type": "return", "parameters": {"unit_id": "defender.usv-06"}, "priority": 0.2, "deadline": 160}
  ],
  "reasoning": "Both intruders (boat-02, boat-03) are approaching the protected zone (dist ~3000-3500m) and are observed by multiple sensors. UAVs are the only units with sufficient speed and range to intercept effectively before the boats cross the boundary. Assigning UAV-01 to boat-02 and UAV-02 to boat-03 ensures spread coverage. USVs are used for tracking to maintain sensor fusion and observation continuity, as their speed is too low for effective interception. USV-02 and USV-06 have no ammo and are returned to reserve."
}
```

## 调用 16（tick 160）

```
{
  "goal_commands": [
    {"task_id": "intercept_boat02_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 165},
    {"task_id": "intercept_boat02_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 165},
    {"task_id": "intercept_boat02_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 165},
    {"task_id": "track_boat03_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-03"}, "priority": 0.7, "deadline": 180},
    {"task_id": "track_boat02_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 180},
    {"task_id": "patrol_usv04_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [917, 1525]}, "priority": 0.4, "deadline": 180},
    {"task_id": "hold_usv02_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.2, "deadline": 170},
    {"task_id": "hold_usv06_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.2, "deadline": 170},
    {"task_id": "hold_usv07_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.2, "deadline": 170}
  ],
  "reasoning": "Intruder boat-02 is the primary threat (threat 0.92, approaching, dist_zone 2863m). Multiple USVs (01, 03, 05) have can_intercept=true and are within range; assigning them to intercept with 'assess' policy to conserve ammo while engaging. UAV-02 is tracking boat-03 (secondary threat). UAV-01 tracks boat-02 for sensor support. USV-04 is infeasible for intercept (eta 72t > target ETA), so it holds position. USVs 02, 06, 07 have 0 ammo and cannot fire, so they hold to maintain sensor coverage."
}
```

## 调用 17（tick 170）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.usv-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "sensor.contact.defender.uav-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [891.0, 1545.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2457.0, 177.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2823.0, 1876.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3737.0, -298.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat surface contact (boat-02) is approaching the protected zone (dist_zone=2810m). Multiple units have can_intercept=true. Assigning the closest armed USVs (usv-05, usv-03, usv-01) to intercept immediately to ensure engagement before zone entry. UAVs (uav-01, uav-02) are assigned to intercept as well, providing redundant coverage and leveraging their higher speed for potential repositioning if the primary USVs fail. USV-04 is infeasible for this target (eta > target arrival), so it holds position. USVs with 0 ammo (usv-02, usv-06, usv-07) are held in place to maintain sensor coverage and positioning, as they cannot engage."
}
```

## 调用 18（tick 180）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 180},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 180},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2170.0, 516.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2466.0, 142.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2822.0, -1504.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [858.0, 1564.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3035.0, -1068.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2802.0, 1905.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3744.0, -263.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (intruder.boat-02) is approaching the protected zone (dist_zone=2702m). UAV-01 and UAV-02 are the only armed units with sufficient range and speed to engage it effectively before it crosses the boundary. USVs are either out of range, out of ammo, or too slow to intercept in time, so they are held in position to maintain sensor coverage and act as a secondary screen."
}
```

## 调用 19（tick 190）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2172.0, 560.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2472.0, 107.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2852.0, -1480.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [838.0, 1541.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3046.0, -1108.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2778.0, 1935.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3753.0, -228.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat surface contact (boat-02) is approaching the protected zone (dist_zone=2594m). Both UAVs have can_intercept=false but prepare_intercept=true (UAV-01) or are already tracking it (UAV-02). UAV-01 is assigned to intercept immediately to maneuver into position. UAV-02 continues intercept to maintain pressure and observation. USVs are holding/patrolling to conserve ammo and maintain sensor coverage, as they are slower and the UAVs are the primary interceptors for this threat."
}
```

## 调用 20（tick 200）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2177.0, 606.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2478.0, 73.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2882.0, -1458.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [816.0, 1516.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3051.0, -1148.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2754.0, 1965.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3763.0, -193.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat surface contact (boat-02) is approaching the protected zone (dist_zone=2514m, closing). UAV-01 and UAV-02 are the only armed units with sufficient range and speed to engage effectively; both have prepare_intercept=true. Assigning both to intercept with 'assess' policy to conserve ammo while maintaining pressure. USVs are holding position to maintain sensor coverage and avoid wasting their limited ammo on a target that is already being engaged by faster, more capable interceptors."
}
```

## 调用 21（tick 210）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2179.0, 652.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2484.0, 37.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2910.0, -1433.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [830.0, 1491.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3060.0, -1189.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2729.0, 1995.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3769.0, -157.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat intruder (boat-02) is approaching the protected zone (dist_zone=2432m, closing). Both UAVs have can_intercept=false but prepare_intercept=false; however, they are the only armed units with long range. UAV-01 is closer (4193m) and closing, while UAV-02 is receding. I assign both to intercept to ensure engagement before the boat enters the zone, using 'assess' to conserve ammo. USVs are sensors only (or out of ammo) and are holding position to maintain sensor coverage."
}
```

## 调用 22（tick 220）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-01", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-03", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_004", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-04", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_005", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-05", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_006", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_007", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat surface contact (boat-02) is the only active threat. Both UAVs are assigned to intercept with 'assess' fire policy to conserve ammunition, as the target is currently stable/receding and not yet in the protected zone. USVs are held in position to maintain sensor coverage and provide backup if the UAVs fail to engage or if the target changes course."
}
```

## 调用 23（tick 230）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 100},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2183, 746]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2509, -22]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2957, -1383]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [835, 1444]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3066, -1274]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2680, 2052]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3780, -84]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat target (boat-02) approaching the protected zone (dist_zone=2243m). Both UAVs have prepare_intercept=true and are the only armed units with sufficient range to engage before the target crosses the boundary. USVs are sensors only (or out of ammo) and are holding position to maintain sensor coverage."
}
```

## 调用 24（tick 240）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2187, 789]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2516, -51]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [2984, -1359]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [863, 1461]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3070, -1316]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2652, 2080]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3794, -52]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is approaching the protected zone (dist_zone=2163m). Both UAVs have can_intercept=false but prepare_intercept=false in the graph, however the target is closing and within 8000m range of both UAVs. UAVs are the only armed units with significant range; USVs are sensors only (range 3000m, many have 0 ammo). Assign both UAVs to intercept with 'assess' policy to conserve ammo (3 each) while maintaining sensor coverage via USVs on patrol."
}
```

## 调用 25（tick 250）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-01", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-03", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_004", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-04", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_005", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-05", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_006", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.5},
    {"task_id": "hold_007", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat surface contact (boat-02) is approaching the protected zone (dist_zone=2109m). Both UAVs are assigned to intercept with 'assess' fire policy to conserve ammunition, as the target is not yet in the immediate fire window for the UAVs (can_intercept=false for UAVs, but prepare_intercept logic applies to engage early). USVs are holding to maintain sensor coverage and avoid wasting their limited ammo on a target that the faster UAVs are better positioned to engage before it crosses the boundary."
}
```

## 调用 26（tick 260）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.8}
  ],
  "reasoning": "Single high-threat contact (boat-02) is approaching the protected zone (dist_zone=1974m). Both UAVs are assigned to intercept with 'assess' policy to conserve ammo while ensuring engagement. USVs are assigned to track to maintain continuous sensor coverage and update the interception graph, as they are the primary observers."
}
```

## 调用 27（tick 270）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "Single high-threat surface contact (boat-02) is approaching the protected zone (dist_zone=1875m). Multiple USVs have can_intercept=true and prepare_intercept=true. Assigning USVs 01, 03, 04, and 05 to intercept with 'assess' fire policy to conserve ammo while ensuring engagement. UAVs continue tracking to maintain sensor coverage. USVs 02, 06, and 07 have 0 ammo and are held in place."
}
```

## 调用 28（tick 280）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-03.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.defender.usv-04.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.usv-05.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6523, 1955]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [-81, 3985]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "Single high-threat contact (boat-02) is observed by multiple USVs. USV-01, 03, 04, and 05 have can_intercept=true and ammo; assigning them to intercept with 'assess' policy to conserve ammo while engaging. UAVs are too far (receding, no prepare_intercept) to be effective immediately, so they hold position. USVs with 0 ammo (02, 06, 07) hold."
}
```

## 调用 29（tick 290）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.usv-02.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6728, 1962]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [-238, 4120]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "Single high-threat intruder (boat-02) is approaching the protected zone (dist_zone=1704m). Multiple USVs have can_intercept=true and are in position to engage. UAVs are too far (eta > 100t) to be effective for immediate interception, so they are held in patrol to maintain sensor coverage. USVs with ammo are assigned to intercept with 'assess' policy to conserve ammunition while engaging the threat. USVs with 0 ammo are held."
}
```

## 调用 30（tick 300）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.facility.berth.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.facility.berth.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.facility.berth.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.85, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.facility.berth.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_005", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.facility.berth.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.75, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [6938.0, 1939.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [-396.0, 4253.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2476.0, 2228.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3835.0, 174.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is approaching the protected zone (dist_zone=1622m). USV-02 is closest (221m) and has prepare_intercept=true, so it is assigned to intercept immediately. USV-04 is also approaching (4.48m/t) and has prepare_intercept=true, so it is assigned to intercept as well. USV-03, USV-01, and USV-05 are within range and can_intercept=true, so they are assigned to intercept to ensure engagement. UAVs and USVs with 0 ammo are placed on patrol to maintain sensor coverage and positioning."
}
```

## 调用 31（tick 310）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.usv-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.usv-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.defender.usv-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.usv-07.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [7136.0, 1878.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [-555.0, 4381.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "Single high-threat intruder (boat-02) is approaching the protected zone (dist_zone=1515m, closing). Multiple USVs have can_intercept=true and are within range. Assigning USV-01, 03, 04, and 05 to intercept with 'assess' fire policy to conserve ammo while ensuring engagement. UAVs are too far (domain_ok=false) to engage effectively, so they hold position. USV-02, 06, and 07 have 0 ammo and cannot fire, so they hold."
}
```

## 调用 32（tick 320）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-02", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02"}, "priority": 0.8, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [7326.0, 1777.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [-719.0, 4506.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2254.0, 1127.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3107.0, -1082.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3075.0, -1645.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2424.0, 2268.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3844.0, 252.0]}, "priority": 0.5}
  ],
  "reasoning": "Intruder boat-02 is the only contact, currently 1434m from the protected zone. USV-02 is closest (154m) and has prepare_intercept=true, so it is assigned to intercept immediately. USV-04 is also approaching (3.78m/t) and has prepare_intercept=true, so it is assigned as a secondary interceptor to ensure engagement. Other units are holding position to maintain sensor coverage and readiness for potential new threats."
}
```

## 调用 33（tick 330）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.6, "deadline": 120},
    {"task_id": "disengage_001", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-02", "position": [2513.0, -342.0]}, "priority": 0.2, "deadline": 120},
    {"task_id": "disengage_002", "goal_type": "disengage", "parameters": {"unit_id": "defender.usv-06", "position": [2396.0, 2287.0]}, "priority": 0.2, "deadline": 120}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding but still within the protected zone boundary (1353m). UAV-01 and UAV-02 are the only armed units with sufficient range and ammo; both are assigned to intercept with 'assess' policy to conserve ammunition while maintaining pressure. USVs with ammo (01, 03, 04, 05) are assigned to track to maintain continuous observation and update the interception graph. USVs with 0 ammo (02, 06) are disengaged to conserve energy and avoid cluttering the sensor picture, as they cannot fire."
}
```

## 调用 34（tick 340）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2267, 1215]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2509, -374]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3136, -1009]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1082, 1641]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3072, -1731]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2364, 2303]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3871, 323]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding from the protected zone (dist_zone=1245m, closing negative). UAVs are assigned to intercept to maintain pressure and secure a kill if it turns, using 'assess' to conserve ammo. USVs hold position to maintain sensor coverage and readiness for potential new waves or if the target re-approaches."
}
```

## 调用 35（tick 350）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2275.0, 1257.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2512.0, -407.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3161.0, -981.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1100.0, 1656.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3071.0, -1774.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2339.0, 2329.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3878.0, 361.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (intruder.boat-02) is receding from the protected zone (dist_zone=1218m, closing negative). UAVs are assigned to intercept to maintain pressure and engage if it turns or stops, using 'assess' to conserve ammo. USVs hold position to maintain sensor coverage and readiness."
}
```

## 调用 36（tick 360）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.5, "deadline": 120}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding (closing speed negative) and far from the protected zone (1066m). UAVs are assigned to intercept with 'assess' policy to conserve ammo while maintaining pressure. USVs are assigned to track to maintain continuous sensor coverage and update the contact's state, as they are closer and can provide better tracking data for the UAVs' engagement."
}
```

## 调用 37（tick 370）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2289.0, 1344.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2514.0, -479.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3207.0, -923.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1127.0, 1624.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3065.0, -1864.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2279.0, 2367.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3898.0, 438.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding (closing speed negative) and far from the protected zone (975m). UAVs are the only armed units capable of engaging it; USVs are sensors only. Assigning both UAVs to intercept with 'assess' policy to conserve ammo while maintaining pressure. USVs hold position to maintain sensor coverage."
}
```

## 调用 38（tick 380）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.8}
  ],
  "reasoning": "Single high-threat contact (intruder.boat-02) is receding but remains the primary focus. UAVs are assigned to intercept with 'assess' policy to conserve ammo while maintaining pressure. USVs are tasked to track to maintain continuous sensor coverage and update the interception graph, as they are the primary observers for this contact."
}
```

## 调用 39（tick 390）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2296.0, 1436.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2509.0, -550.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3249.0, -863.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1174.0, 1651.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3057.0, -1951.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2213.0, 2406.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3923.0, 515.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding (closing speed negative) and far from the protected zone (804m). UAVs are assigned to intercept to maintain tracking and readiness, while USVs hold position to conserve energy and maintain sensor coverage. No immediate fire required as target is moving away."
}
```

## 调用 40（tick 400）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.8},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.7},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.7},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.7},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2508.0, -587.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2184.0, 2429.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3934.0, 556.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding but remains close to the protected zone (705m). UAVs are assigned to intercept with 'assess' policy to conserve ammo while maintaining pressure. USVs with sensors are tracking to maintain continuous observation. USVs with 0 ammo are patrolling to maintain sensor coverage."
}
```

## 调用 41（tick 410）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2303, 1529]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2507, -624]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3299, -805]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1216, 1669]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3052, -2038]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2154, 2451]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3944, 594]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding but still within 625m of the protected zone. UAVs are the only armed units capable of engaging it (USVs have 0 ammo or are sensors). Both UAVs are assigned to intercept to ensure a kill, using 'assess' policy to conserve ammo. USVs maintain patrol positions to provide continuous sensor coverage and track the target's movement."
}
```

## 调用 42（tick 420）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.usv-01", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.usv-02", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_003", "goal_type": "track", "parameters": {"unit_id": "defender.usv-03", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_004", "goal_type": "track", "parameters": {"unit_id": "defender.usv-04", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_005", "goal_type": "track", "parameters": {"unit_id": "defender.usv-05", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_006", "goal_type": "track", "parameters": {"unit_id": "defender.usv-06", "target_id": "intruder.boat-02"}, "priority": 0.5},
    {"task_id": "track_007", "goal_type": "track", "parameters": {"unit_id": "defender.usv-07", "target_id": "intruder.boat-02"}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is receding (closing speed negative) and far from the protected zone (543m away, 168+ ticks to boundary). UAVs are maintaining intercept posture to be ready if it turns or if new threats appear. USVs are tracking to maintain continuous sensor coverage and classification, as they are the primary observers. No immediate fire is required as the target is moving away and outside the critical engagement window for the zone defense."
}
```

## 调用 43（tick 430）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2311.0, 1620.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2506.0, -697.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3343.0, -742.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1264.0, 1687.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3043.0, -2126.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2097.0, 2490.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3968.0, 664.0]}, "priority": 0.5}
  ],
  "reasoning": "The single high-threat contact (intruder.boat-02) is observed by the facility berth and is currently receding (closing speed negative) with a distance to the protected zone of 436m. The UAVs (uav-01, uav-02) are the only armed units capable of engaging this target effectively from their current positions and have sufficient ammunition. The USVs are sensor-only or out of ammo (usv-02, usv-06, usv-07 have 0 ammo) and are positioned to maintain surveillance coverage. Since the target is receding, immediate interception by the UAVs is the priority to prevent it from re-approaching or to engage it before it can maneuver into a safer position. The USVs hold their patrol positions to maintain sensor coverage of the area."
}
```

## 调用 44（tick 440）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2312, 1666]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2507, -735]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3368, -714]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1246, 1702]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3040, -2170]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2067, 2513]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3977, 701]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (intruder.boat-02) is receding (closing speed negative) and far from the protected zone (354m). UAVs are assigned to intercept to maintain pressure and prepare for potential re-approach, using 'assess' policy to conserve ammo. USVs are holding position to maintain sensor coverage and readiness, as they are closer to the zone and can react quickly if the threat turns."
}
```

## 调用 45（tick 450）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2314.0, 1713.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2512.0, -774.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3392.0, -684.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1243.0, 1675.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3040.0, -2213.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2038.0, 2539.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3987.0, 738.0]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (intruder.boat-02) is observed by all units. UAVs are the only armed units capable of engaging it (USVs have 0 ammo or are sensors only). Both UAVs are assigned to intercept the target to ensure engagement. USVs are ordered to hold their current positions to maintain sensor coverage and observation of the target."
}
```

## 调用 46（tick 460）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2319, 1758]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2520, -812]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3419, -657]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1241, 1638]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3034, -2255]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [2008, 2566]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [3999, 772]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (intruder.boat-02) is very close to the protected zone (193m) and receding. Both UAVs are assigned to intercept with 'assess' policy to conserve ammo while maintaining pressure. USVs are holding position to maintain sensor coverage and monitor the contact's movement."
}
```

## 调用 47（tick 470）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.95, "deadline": 30},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2320, 1804]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2524, -848]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3441, -629]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1269, 1605]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3032, -2300]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [1983, 2595]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [4009, 806]}, "priority": 0.5}
  ],
  "reasoning": "Single high-threat contact (boat-02) is extremely close to the protected zone (84m) and receding. UAV-02 is in the immediate intercept window (feasible_eta=1t) and is assigned to engage. UAV-01 is assigned as a secondary interceptor to ensure a kill if the first shot fails, given the critical proximity to the zone. USVs are holding position to maintain sensor coverage and monitor for additional waves."
}
```

## 调用 48（tick 480）

```
{
  "goal_commands": [
    {"task_id": "track_001", "goal_type": "track", "parameters": {"unit_id": "defender.uav-01", "target_id": "intruder.boat-02"}, "priority": 0.9, "deadline": 120},
    {"task_id": "track_002", "goal_type": "track", "parameters": {"unit_id": "defender.uav-02", "target_id": "intruder.boat-02"}, "priority": 0.9, "deadline": 120},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-01", "position": [2323.0, 1851.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-02", "position": [2533.0, -884.0]}, "priority": 0.5},
    {"task_id": "patrol_003", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-03", "position": [3467.0, -603.0]}, "priority": 0.5},
    {"task_id": "patrol_004", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-04", "position": [1291.0, 1567.0]}, "priority": 0.5},
    {"task_id": "patrol_005", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-05", "position": [3027.0, -2344.0]}, "priority": 0.5},
    {"task_id": "patrol_006", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-06", "position": [1955.0, 2621.0]}, "priority": 0.5},
    {"task_id": "patrol_007", "goal_type": "patrol", "parameters": {"unit_id": "defender.usv-07", "position": [4020.0, 845.0]}, "priority": 0.5}
  ],
  "reasoning": "The single contact 'intruder.boat-02' is currently at the protected zone boundary (dist_zone=0m) but is receding (closing speed negative) and has a long ETA (200t). The UAVs are outside weapon range (range_ratio > 1.0) and cannot intercept effectively yet. The USVs are in range but the target is moving away. To conserve ammunition and maintain situational awareness, UAVs are tasked to track the target to update its velocity vector, while USVs hold their patrol positions to monitor the area and react if the target turns back or new threats appear."
}
```

## 调用 49（tick 490）

```
{
  "goal_commands": [
    {"task_id": "intercept_001", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-01", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.9, "deadline": 60},
    {"task_id": "intercept_002", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-03", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.8, "deadline": 60},
    {"task_id": "intercept_003", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-05", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.7, "deadline": 60},
    {"task_id": "intercept_004", "goal_type": "intercept", "parameters": {"unit_id": "defender.usv-04", "target_id": "sensor.contact.defender.uav-01.intruder.boat-02", "fire_policy": "assess"}, "priority": 0.6, "deadline": 60},
    {"task_id": "patrol_001", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-01", "position": [9739.0, -764.0]}, "priority": 0.5},
    {"task_id": "patrol_002", "goal_type": "patrol", "parameters": {"unit_id": "defender.uav-02", "position": [-3520.0, 6585.0]}, "priority": 0.5},
    {"task_id": "hold_001", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-02", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_002", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-06", "duration": 10}, "priority": 0.1},
    {"task_id": "hold_003", "goal_type": "hold", "parameters": {"unit_id": "defender.usv-07", "duration": 10}, "priority": 0.1}
  ],
  "reasoning": "Single high-threat contact (boat-02) is at the zone boundary (dist_zone=0m) and receding. Multiple USVs have can_intercept=true. Assigning USV-01, USV-03, USV-05, and USV-04 to intercept with 'assess' policy to conserve ammo while ensuring engagement. UAVs are out of range (feasible=false) and will patrol to maintain sensor coverage. USVs with 0 ammo are held."
}
```

