# Grid D1开发数据判别线索诊断

来源：`/root/openmd/runs/p0-next-20261002/E3-channel-complex`。仅开发数据，未读取确认输入/真值来调规则。

|字段组|OOF准确率|OOF平衡准确率|AUC|
|---|---:|---:|---:|
|complete|94.62%|94.02%|0.9838|
|candidate_xy_only|91.03%|91.53%|0.9779|
|local_grid_only|81.34%|79.96%|0.8544|
|own_state_only|92.34%|92.03%|0.9685|
|candidate_relative_cell|69.50%|69.42%|0.7385|
|lock_only|59.69%|66.81%|0.6440|
|kind_comm_jam|65.67%|70.86%|0.6752|
|complete_without_explicit_xy|91.75%|91.34%|0.9649|
|complete_without_lock|94.50%|93.93%|0.9829|

当前事件836个，seed聚类370；窗口角色变化0/836。
精确坐标双类重叠：{'all_cells': 135, 'both_class_cells': 5, 'n_overlap_events': 23, 'n_overlap_seeds': 20, 'matched_current_only': {'state': 'insufficient-development-coverage', 'n': 23}}。
首次局部可见时完整当前观测诊断：{'state': 'diagnostic-OOF', 'n': 783, 'seed_clusters': 577, 'accuracy': 0.7624521072796935, 'balanced_accuracy': 0.7359850233369236, 'auc': 0.8334615581884393, 'model': 'fixed quadratic L2 logistic lambda0.1; 4 seed-group folds; no model selection', 'probabilities': 'omitted'}。

固定模型的字段消融用于定位可预测关联，不是因果证明、认证输入删减或正式D1成绩。位置可预测支持空间分布线索；删除显式坐标仍可辨时，网格+自身位置可能恢复它，不能称去除位置信息。首次可见探针可检验8次历史筛选/运动累积是否放大可辨性，但此前动作仍可能影响状态。精确坐标匹配仅开发诊断，需新独立协议和采样才能作为正式测试。
