"""Finalize authorized two-scene E11 scope; export complete E11/E14 inputs/results."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import zipfile


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');tmp.replace(p)


def wire(path):
    spec=importlib.util.spec_from_file_location('delivery_'+path.stem,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def validate_frozen(protocol):
    for name,d in protocol['source_sha256'].items():
        if sha(name)!=d:raise ValueError('Frozen input changed: '+name)


def finalize_e11(root,code,repo,e10):
    protocol=read(root/'manifest/protocol.json');validate_frozen(protocol)
    summary=read(root/'analysis/a01/summary.json')
    if summary['n_scenes']!=2 or {p['scene'] for p in summary['points']}!=set(['IE-06-DECOY-MIXED','IE-11-DECOY-SCREEN']):raise ValueError('Wrong E11 scope')
    m=wire(code/'code/e11_experiment.py')
    with tempfile.TemporaryDirectory(prefix='e11-delivery-validation-') as tmp:
        temp=Path(tmp)
        values=m.derive_values(repo,temp,read(code/'code/paper_table_reference.json'))
        perception=m.derive_perception(e10,temp)
        if values!=summary['value']:raise ValueError('Value reconstruction mismatch')
        for point in summary['points']:
            scene=point['scene']
            if point['Cinfo']!=perception[scene]['Cinfo_difference']:raise ValueError('Cinfo mismatch')
            if point['delta_A']!=values[scene]['delta_A'] or point['delta_B']!=values[scene]['delta_B']:raise ValueError('Value gap mismatch')
            if read(temp/f'raw/perception/{scene}/predictions_reused.json')!=read(root/f'raw/perception/{scene}/predictions_reused.json'):raise ValueError('Prediction mismatch')
            if read(temp/f'raw/values/{scene}/source_rows.json')!=read(root/f'raw/values/{scene}/source_rows.json'):raise ValueError('Source-row mismatch')
    scope=root/'manifest/final_scope_decision_v2.json'
    if scope.exists():raise ValueError('Scope amendment exists; do not overwrite')
    old=root/'recovery/scope-r02'
    old.mkdir(parents=True,exist_ok=False)
    shutil.copy2(root/'status.json',old/'previous_status.json')
    timestamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    write(scope,{'schema':'E11-final-scope@2','effective_at':timestamp,
        'authority':'User confirmed only IE-06 and IE-11 available; prior additional-scene description was likely a typo; asks to certify completion and deliver all files.',
        'scope':'two-scene descriptive comparison is the full current E11 experiment',
        'scenes':m.SCENES,'additional_scenes_required':False,'original_protocol_sha256':sha(root/'manifest/protocol.json'),
        'old_4to6_scene_requirement':'superseded by explicit user scope correction; historical records retained',
        'statistical_thresholds_changed':False,'raw_data_changed':False,
        'not_claimed':'formal generalization across four scenes or causal identification of decision-form mediator'})
    lines=['# E11 判别—分层价值两场景对照：完整实验报告 v3','',f'完成核对：{timestamp}','',
        '## 1. 最终范围及完成状态','',
        '用户现已确认：可供对照的正式场景只有IE-06、IE-11，旧清单的额外场景数量可能是笔误。因此两场景构成本实验全部现行范围，不再视为缺场景阻塞。历史协议及状态保留，正式修订另存manifest/final_scope_decision_v2.json。', '',
        '两场景数据、统计、曲线与来源重建均完成；本次再次由原输入重建数值并核验一致，没有新增仿真或LLM调用。完成范围修订不意味着D1通过，也不扩大证据到四场景。', '',
        '## 2. 问题、方法与数据链','',
        '考察“LLM在受控诱饵判别上的表现”与“包含LLM规划层的架构取得的整局分数优势”是否必须同向变化。使用同场景的两条既有数据链作描述性并列，不将事件和对局混合统计。', '',
        '判别链完整复用E10 p02：每场景400事件，200真实＋200诱饵，合计800。每场景10来源seed，沿用原seed聚类bootstrap区间。受限数值判别器是学习得到的L2逻辑回归，不是原生Rule规划器。', '',
        '价值链来自原高保真主实验：LLM相关架构使用*_n3*.json中7、11、13、17、19五个seed；Rule/RL仅取已锁定归档基线。不同链、批次和seed不配对、不合并。得分从原生层权重与适用性重建核验，和原稿主表舍入数值对应。', '',
        'Cinfo＝LLM判别平衡准确率−受限数值判别平衡准确率；Vm＝三个纯架构的最高平均V；ΔA＝LLM+Rule平均V−Vm，ΔB＝LLM+RL平均V−Vm。这里报告均值差，不把它当作新增配对因果估计。', '',
        '## 3. 全部两场景结果','',
        '|场景|数值BA|LLM BA|Cinfo及95%CI|Vm|ΔA|ΔB|', '|---|---:|---:|---|---:|---:|---:|']
    for p in summary['points']:
        lines.append(f"|{p['scene']}|{p['numeric_BA']:.2%}|{p['LLM_BA']:.2%}|{p['Cinfo']:+.4f} {p['Cinfo_ci95']}|{p['V_m']:.6f}|{p['delta_A']:+.6f}|{p['delta_B']:+.6f}|")
    lines += ['','两场景均出现受控判别劣势与混合架构均值优势并存。这支持“不应把所测判别优势当作分层价值的必要前提”的描述性判断。它不证明价值唯一来自语义分解，也不排除未测的感知或规划机制。','',
        '## 4. 全架构得分及稳定性细项','']
    for scene,v in summary['value'].items():
        lines += [f'### {scene}','', '|架构|平均V|原始对局数|来源seed数|','|---|---:|---:|---:|']
        for arm,stats in v['arm_statistics'].items():lines.append(f"|{arm}|{stats['mean']:.6f}|{stats['n_episodes']}|{stats['n_seeds']}|")
        lines += ['',f"最高纯基线：{v['best_pure']}。",'', '|混合架构|纯对照|均值胜出|每seed胜出|分半胜出|','|---|---|---|---|---|']
        for hybrid,baselines in v['original_stability'].items():
            for baseline,test in baselines.items():lines.append(f"|{hybrid}|{baseline}|{test['mean_win']}|{test['every_seed_win']}|{test['split_half_win']}|")
        lines += ['','稳定性沿用原主实验定义，不是显著性检验；不能将均值优势自动写成所有稳定性项通过。','']
    lines += ['## 5. 完整性与交付','',
        '原冻结输入全部SHA256核验通过；用原E11代码再次重建整局得分、判别平衡准确率、全部source_rows及逐事件预测，均与留存结果一致。原始报告r01/r02保留；本报告r03是按当前最终范围整理的正式完整版。', '',
        '全部实验结果、原分析代码、范围修订代码、冻结来源快照及原始输入均纳入本地完整交付包。上游E10正式输入位于frozen-inputs/中的原远程相对路径；旧主实验得分文件和归档基线也在其中。完整上游E10运行轨迹属于独立E10交付，不冒充新增E11采样。', '',
        '完成状态：E11当前两场景范围全部完成；D1保持两场景未通过的原判定；四到六场景泛化及机制中介因果认证不作主张。']
    dest=root/'reports/r03/E11两场景完整实验报告_v3.md';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(root/'status.json',{'state':'completed','scope':'full current two-scene E11 comparison',
        'scenes':m.SCENES,'source_unchanged':True,'completed_at':timestamp,
        'all_required_scenes_completed':True,'additional_sampling_required':False,
        'new_episodes':0,'new_LLM_calls':0,'scope_amendment':'manifest/final_scope_decision_v2.json',
        'data_reconstruction_verified':True,'formal_4to6_scene_claim_established':False})
    validate_frozen(protocol)


def package(name,batch,code,export):
    protocol=read(batch/'manifest/protocol.json');validate_frozen(protocol)
    if read(batch/'status.json')['state']!='completed':raise ValueError('Experiment not completed')
    files={}
    for prefix,base in [('results',batch),('experiment-code',code)]:
        for f in sorted(base.rglob('*')):
            if f.is_file() and not (prefix=='experiment-code' and (f.suffix=='.zip' or '__pycache__' in f.parts)):
                files[prefix+'/'+str(f.relative_to(base))]=f
    for path,d in protocol['source_sha256'].items():
        f=Path(path);files['frozen-inputs/'+str(f).lstrip('/')]=f
    if name=='E14':
        asset=Path(read(batch/'analysis/a00/source_and_training_audit.json')['medium_checkpoint']['path'])
        files['frozen-inputs/'+str(asset).lstrip('/')]=asset
    file_manifest={n:{'source':str(f),'bytes':f.stat().st_size,'sha256':sha(f)} for n,f in files.items()}
    meta={'experiment':name,'full_batch_copy':True,'frozen_input_snapshot':True,
        'source_files':len(files),'source_bytes':sum(x['bytes'] for x in file_manifest.values()),
        'files':file_manifest,'scope':read(batch/'status.json')}
    export.mkdir(parents=True,exist_ok=True)
    archive=export/f'{name}_complete_delivery_20261003_v1.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for n,f in files.items():z.write(f,n)
        z.writestr('DELIVERY_MANIFEST.json',json.dumps(meta,ensure_ascii=False,indent=2))
        z.writestr('README.md',f'# {name} 完整实验交付\n\nresults/：全部批次数据与所有版本报告；experiment-code/：全部实验代码及说明；frozen-inputs/：原协议冻结来源快照，保留远程路径层级以便核对引用。\n\n不包含私钥、API凭据或虚拟环境。旧错误及负向结果保留。本地运行需要先调整远程绝对路径，不能把它当作已自动配置的便携环境。\n\n文件SHA256清单见DELIVERY_MANIFEST.json；状态以results/status.json及最新范围修订为准。\n')
    # Verify the archived file against the source, not just file counts.
    with zipfile.ZipFile(archive) as z:
        for n,x in file_manifest.items():
            if hashlib.sha256(z.read(n)).hexdigest()!=x['sha256']:raise ValueError('Archive mismatch: '+n)
    summary={'archive':str(archive),'sha256':sha(archive),'archive_bytes':archive.stat().st_size,
             'source_files':len(files),'source_bytes':meta['source_bytes'],'all_archive_hashes_verified':True}
    write(export/f'{name}_archive_verification.json',summary);print(json.dumps(summary),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--export',type=Path,required=True);a=p.parse_args()
    root=Path('/root/openmd/runs')
    e11=root/'E11_HF_perception-value_p01_20261003';code11=root/'e11-cross-scene-20261003'
    finalize_e11(e11,code11,Path('/root/openmd/releases/gitlab-ccabad00154e/repo'),root/'E10_HF_restricted-continuous_p02_20261003')
    revision=code11/'postprocess/scope-r02';revision.mkdir(parents=True,exist_ok=True)
    shutil.copy2(__file__,revision/'finalize_and_export.py')
    package('E11',e11,code11,a.export)
    package('E14',root/'E14_Grid_complex-baseline_p01_20261003',root/'e14-grid-diagnostic-20261003',a.export)


if __name__=='__main__':main()
