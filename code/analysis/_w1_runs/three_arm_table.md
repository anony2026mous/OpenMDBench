```
====================================================================================================================================
三臂对照（防守方视角；overall 越高越好）
====================================================================================================================================
rule       overall=0.532 term=1.00 fac=0.10 depth=0.22 leak=0.58 exch=0.55 ammo=1.00 surf=1.00 | depth_mean=7209.8 intercept=0.58 release=0.42
hybrid_r1  overall=0.630 term=1.00 fac=0.13 depth=0.73 leak=0.58 exch=0.42 ammo=1.00 surf=1.00 | depth_mean=10085.8 intercept=0.42 release=0.42
pure_r1    overall=0.527 term=1.00 fac=0.10 depth=0.22 leak=0.58 exch=0.50 ammo=1.00 surf=1.00 | depth_mean=6571.0 intercept=0.58 release=0.42
hybrid     overall=0.130 term=0.00 fac=0.00 depth=0.10 leak=0.50 exch=0.17 ammo=0.89 surf=0.00 | depth_mean=3428.7 intercept=0.33 release=0.50

------------------------------------------------------------------------------------------------------------------------------------
layer               rule   hybrid_r1     pure_r1      hybrid
------------------------------------------------------------------------------------------------------------------------------------
terminal           1.000       1.000       1.000       0.000   (w=0.2)
facilities         0.100       0.133       0.100       0.000   (w=0.25)
depth              0.220       0.733       0.220       0.095   (w=0.2)
leak               0.583       0.583       0.583       0.500   (w=0.1)
exchange           0.545       0.417       0.500       0.167   (w=0.1)
ammo               1.000       1.000       1.000       0.889   (w=0.05)
surface            1.000       1.000       1.000       0.000   (w=0.1)
------------------------------------------------------------------------------------------------------------------------------------
OVERALL            0.532       0.630       0.527       0.130

====================================================================================================================================
原始证据
====================================================================================================================================
metric                            rule         hybrid_r1           pure_r1            hybrid
------------------------------------------------------------------------------------------------------------------------------------
ticks_run                         1800              1800              1800               719
aborted                           None              None              None              None
terminal              defender_success  defender_success  defender_success  attacker_success
terminal_tick                     1799              1799              1799               718
consistent                        True              True              True              True
executed_fires                      59                45                41                34
shots_blue                          24                18                18                 9
shots_red                           35                27                23                25
uav_lost_blue                        7                 5                 8                 6
uav_lost_red                         7                 5                 7                 4
usv_lost_blue                        0                 3                 0                 2
usv_lost_red                         5                 5                 5                 0
intercept_rate                  0.5833            0.4167            0.5833            0.3333
depth_mean_m                    7209.8           10085.8            6571.0            3428.7
depth_median_m                   228.7            9306.7             228.7            3807.9
release_rate                    0.4167            0.4167            0.4167               0.5
leak_rate                         0.75            0.5833              0.75               0.5
facility_survival                  0.1            0.1333               0.1               0.0
facilities_destroyed                 3                 3                 3                 4
defender_kills                      12                10                12                 4
attacker_kills                      11                12                12                12
def_shots_per_kill                 2.0               1.8               1.5              2.25
llm_calls                         None              None              None              None
fallback_count                    None                 0              None                 0
parse_failures                     n/a               n/a               n/a               n/a
elapsed_s                       499.51           3283.19           2026.93           1820.32
```
