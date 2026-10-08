# Grid D1开发数据判别线索诊断

来源：`/root/openmd/runs/p0-next-20261002/E3-channel-v3`。仅开发数据，未读取确认输入/真值来调规则。

|字段组|OOF准确率|OOF平衡准确率|AUC|
|---|---:|---:|---:|
|complete|95.16%|95.00%|0.9938|
|candidate_xy_only|96.77%|96.72%|0.9964|
|local_grid_only|83.06%|83.02%|0.8677|
|own_state_only|95.97%|95.83%|0.9922|
|candidate_relative_cell|63.71%|63.59%|0.6701|
|lock_only|67.74%|68.44%|0.7118|
|kind_comm_jam|66.94%|67.29%|0.7178|
|complete_without_explicit_xy|92.74%|92.50%|0.9690|
|complete_without_lock|95.97%|95.83%|0.9964|

当前事件124个，seed聚类87；窗口角色变化0/124。
精确坐标双类重叠：{'all_cells': 52, 'both_class_cells': 1, 'n_overlap_events': 2, 'n_overlap_seeds': 2, 'matched_current_only': {'state': 'insufficient-development-coverage', 'n': 2}}。
首次局部可见时完整当前观测诊断：{'state': 'diagnostic-OOF', 'n': 262, 'seed_clusters': 262, 'accuracy': 0.6984732824427481, 'balanced_accuracy': 0.6926273039675102, 'auc': 0.7713214620431116, 'model': 'fixed quadratic L2 logistic lambda0.1; 4 seed-group folds; no model selection', 'probabilities': 'omitted'}。

固定模型的字段消融用于定位可预测关联，不是因果证明、认证输入删减或正式D1成绩。位置可预测支持空间分布线索；删除显式坐标仍可辨时，网格+自身位置可能恢复它，不能称去除位置信息。首次可见探针可检验8次历史筛选/运动累积是否放大可辨性，但此前动作仍可能影响状态。精确坐标匹配仅开发诊断，需新独立协议和采样才能作为正式测试。
