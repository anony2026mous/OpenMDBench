"""E14 bounded parallel MAPPO diagnostic campaign; all raw attempts retained."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SEEDS=[22001,22002,22003]
CONFIGS={'default_extended':{'lr':3e-4,'entropy':.01,'total_steps':10000000},
         'medium_curriculum':{'lr':3e-4,'entropy':.01,'total_steps':5000000},
         'lr_half':{'lr':1.5e-4,'entropy':.01,'total_steps':5000000},
         'lr_double_entropy_double':{'lr':6e-4,'entropy':.02,'total_steps':5000000}}

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.tmp');q.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)

def freeze(a):
    files=list((a.source/'code/grid_env').rglob('*.py'))+[a.source/'code/train_mappo.py',a.medium]
    files += [p for p in Path(__file__).parent.rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']]
    return {str(p):sha(p) for p in sorted(set(files))}

def verify(frozen):
    for p,d in frozen.items():
        if sha(p)!=d:raise ValueError('Frozen source changed: '+p)

def audit(a,out):
    sys.path.insert(0,str(Path(__file__).parent))
    from e14_worker import wire,evaluate,summary
    native,GridEnv,MAX_STEPS,MAPPOAgent,torch=wire(a.source)
    import grid_env.grid_env as envcode
    import inspect
    histories=[]
    # Exact historical log locations are missing: inspect source-owned checkpoints only.
    for p in (a.source/'code').rglob('*'):
        if p.is_file() and ('mappo' in p.name.lower() or 'train' in p.name.lower()) and p.suffix in ['.log','.json','.csv','.pt','.pth']:
            histories.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
    weights=torch.load(a.medium,map_location='cpu',weights_only=False)
    meta={k:v for k,v in weights.items() if 'state_dict' not in k}
    structure={'grid_size':envcode.GRID_SIZE,'episode_horizon':MAX_STEPS,
               'difficulty_config':envcode.DIFFICULTY_CONFIG,
               'reward_source':inspect.getsource(GridEnv.compute_reward),
               'epsilon_schedule':'not applicable to native MAPPO: stochastic categorical actions + entropy regularization, NOT legacy PureRLAgent epsilon',
               'historical_logs_found':histories,'historical_complex_checkpoint_available':False,
               'historical_convergence_verdict':'unknown; no complete old complex training curve or tested checkpoint supplied',
               'old20M_statement':'prior manuscript mentions20M and curriculum; text is not an available training trajectory or checkpoint',
               'medium_checkpoint':{'path':str(a.medium),'sha256':sha(a.medium),'metadata':meta},
               'retrain_scope':'current frozen Grid source, native trainer; does not silently replace original paper experiment',
               'sparse_reward_only':False,'no_engine_or_scene_changes':True}
    write(out/'analysis/a00/source_and_training_audit.json',structure)
    # Validate available warm start in EACH existing difficulty, no new training.
    result={}
    agent=MAPPOAgent(trained=True,checkpoint_path=str(a.medium),device='cpu')
    for tier in ['simple','medium','complex']:
        rows=evaluate(agent,tier,list(range(25101,25111)))
        write(out/f'raw/preflight/medium_transfer_{tier}.json',{'rows':rows,'summary':summary(rows)})
        result[tier]=summary(rows)
    write(out/'analysis/a00/medium_transfer.json',result)
    return structure,result

def job(a,name,seed):
    out=a.output/f'raw/training/{name}/seed-{seed}'
    conf={**CONFIGS[name],'name':name,'seed':seed,'goal_inject_prob':.5,'task_mode':'continuous',
          'device':'cpu','source':str(a.source),'diagnostic_training_seeds':SEEDS,
          'development_eval_seeds':list(range(23101,23111)),'confirmation_eval_seeds':list(range(24101,24111)),
          'cpu_threads':1,'steps_per_rollout':4096,'num_envs':8,'ppo_epochs':4,'batch_size':512,
          'gamma':.99,'gae_lambda':.95,'clip_eps':.2,'vf_coef':.5,'max_grad_norm':.5,
          'warm_start_kind':'weights-only, fresh Adam and reward-normalizer; NOT optimizer-resume'}
    if name=='medium_curriculum':conf['init_from']=str(a.medium)
    p=a.output/f'manifest/configs/{name}_seed-{seed}.json'
    write(p,conf);out.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,'-B','-u',str(Path(__file__).with_name('e14_worker.py')),'train','--source',str(a.source),'--output',str(out),'--config',str(p)]
    with (out/'stdout.log').open('a') as f:
        try:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=86400).returncode
        except subprocess.TimeoutExpired:return {'name':name,'seed':seed,'state':'wall-timeout-24h','output':str(out)}
    return {'name':name,'seed':seed,'exit_code':code,'output':str(out),'state':'completed' if code==0 else 'failed-engineering'}

def analyze(out):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    results=[];curves=[]
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for name in CONFIGS:
        seed_rows=[]
        for seed in SEEDS:
            folder=out/f'raw/training/{name}/seed-{seed}'
            if not (folder/'status.json').exists() or read(folder/'status.json')['state']!='completed':continue
            final=read(folder/'status.json');best=read(folder/'confirmation/best.json')
            final_cf=read(folder/'confirmation/final.json')
            roll=[json.loads(s) for s in (folder/'training_rollouts.jsonl').read_text().splitlines()]
            window=roll[-max(1,int(np.ceil(.1*len(roll)))):]
            den=sum(x['n_completed_training_episodes'] for x in window)
            tail=sum((x['training_success_rate'] or 0)*x['n_completed_training_episodes'] for x in window)/den if den else None
            sr=best['summary']['success_rate']
            seed_rows.append({'training_seed':seed,'development_selected_best_confirmation_SR':sr,
                             'final_confirmation_SR':final_cf['summary']['success_rate'],'tail10pct_training_SR':tail,
                             'tail_training_episodes':den,'steps':final['actual_steps']})
            history=sorted((folder/'development').glob('step-*.json'))
            h=[read(p) for p in history]
            curves.append({'name':name,'seed':seed,'development_curve':[{'step':x['step'],**x['summary']} for x in h]})
            label=f'{name}/s{seed}'
            axs[0,0].plot([r['step'] for r in h],[r['summary']['success_rate'] for r in h],label=label)
            axs[0,1].plot([r['step'] for r in h],[r['summary']['mean_reward'] for r in h])
            stride=max(1,len(roll)//200);thin=roll[::stride]
            axs[1,0].plot([r['step'] for r in thin],[r['value_loss'] for r in thin])
            axs[1,1].plot([r['step'] for r in thin],[r['entropy'] for r in thin])
        if seed_rows:
            x=np.array([r['development_selected_best_confirmation_SR'] for r in seed_rows])
            rng=np.random.default_rng(20261003);boot=x[rng.integers(0,len(x),size=(20000,len(x)))].mean(1)
            results.append({'configuration':name,'completed_training_seeds':len(seed_rows),'mean_confirm_SR':float(x.mean()),
                            'training_seed_bootstrap_ci95':np.quantile(boot,[.025,.975]).tolist(),'seed_rows':seed_rows,
                            'diagnostic_over20pct':float(x.mean())>.2,'not_formal10_training_seed_proof':True})
    for ax,title in zip(axs.flat,['Development SR (NOT held-out confirm)','Development raw reward','Value loss','Action entropy']):ax.set(title=title,xlabel='Environment steps')
    if curves:axs[0,0].legend(fontsize=5)
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(out/f'analysis/a01/training_curves.{ext}',dpi=180)
    plt.close(fig)
    conclusion='diagnostic-improvement-found-notify-main-author-before-any-replacement' if any(r['diagnostic_over20pct'] for r in results) else 'no-improvement-at-tested-budget-NOT-proof-of-unlearnability'
    summary={'configurations':results,'curves':curves,'conclusion':conclusion,'no_original_data_replaced':True,
             'CI_unit':'independent training seed n=3 per configuration; eval seeds reused within this diagnostic batch; not30 independent trained agents',
             'structural_simplification':'not run: requires separate permission to change frozen scenario parameters'}
    write(out/'analysis/a01/summary.json',summary)
    return summary

def report_initial(out,audit_info,transfer):
    lines=['# E14 Grid complex 基线诊断：启动与训练资产核查','',
      '依据2026-10-03 14:39 v9清单§3。旧complex完整训练日志和原论文0% checkpoint在当前远程工程中未找到，因此无法复核旧曲线收敛、最后10%窗口或原checkpoint0%。',
      '按清单缺失日志的兜底要求进入当前冻结源码的独立诊断重训，不将缺失材料推断为训练失败或任务不可学。', '',
      '## 当前可验证事实','',
      '原MAPPO使用Categorical随机动作与熵正则，没有ε调度；不要把旧轻量PureRLAgent类的epsilon当成MAPPO探索参数。',
      '原环境reward同时包含终局、检测、截获、跟踪、漏防、伤亡、误击与碰撞等增量信号，并非只有终局稀疏奖励。各难度均为20×20地图、150步上限；复杂层叠加波次、噪声、异常、丢包和UAV追击。',
      '现有medium/s42 checkpoint元数据宣称开发SR=1，但没有完整训练历史。本次先在10个新seed上核查其当前simple/medium/complex表现，不冒称复现历史100/97/0。','',
      '|当前难度|可用medium权重迁移SR（10seed）|','|---|---:|']
    for k,v in transfer.items():lines.append(f"|{k}|{v['success_rate']:.1%}|")
    lines += ['', '## 诊断预算与冻结方案','',
      '4配置×3训练seed（22001–22003）共12次独立训练：默认延长10M步；medium权重课程5M；lr减半5M；lr翻倍且entropy翻倍5M。后两配置构成两组超参扫描。',
      '10M是当前源码默认5M预算的×2，不等于旧论文20M训练的×2。本次不能用于声称已把旧20M试验延长到40M。全部记录完整超参和版本。',
      '开发评估10seed23101–23110选择best；独立确认10seed24101–24110评价预先定义best及final，不按确认结果再选择权重；最终跨训练seed统计单位n=3。',
      '保留源码默认goal注入训练概率0.5，确认时纯actor无外部goal；这与纯RL推理模式一致，但不是另一个no-goals训练协议。',
      'CPU-only PyTorch；12个单线程子进程并行，不改变GPU模型环境，不抢占4张vLLM GPU、不升级依赖。每训练任务24小时墙钟保护，超时和失败保留。',
      '被动记录原reward返回值、训练rollout成功率、loss、entropy；日志不改变reward或RNG，512步原/插桩训练缓冲及更新逐项一致冒烟通过后才启动。',
      '任何改善都如实报告，未经主理人确认不替换原主表或重跑六臂/tournament；全部仍近0只能说明受测配置/预算下未改善，不能证明数学意义“genuinely不可学”。',
      '清单简化complex建议涉及冻结场景参数改动，当前不执行；需额外授权后另冻版本及明确与原场景的对照。', '',
      '结果目录：manifest（协议/源哈希/configs）、raw/preflight（迁移核查）、raw/training（每配置每seed独立日志/权重/开发/确认）、analysis/a00（资产/结构）、analysis/a01（最终曲线/统计）、reports/r00（本启动报告）、reports/r01（最终报告）。']
    dest=out/'reports/r00/E14训练资产核查与启动报告_v1.md';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('\n'.join(lines)+'\n')

def run(a):
    out=a.output;start=time.time()
    import fcntl
    with (out/'logs/run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        frozen=freeze(a)
        protocol={'protocol':'E14-current-Grid-diagnostic-p01','source':str(a.source),'source_sha256':frozen,
          'configurations':CONFIGS,'training_seeds':SEEDS,'workers':a.workers,
          'stats':'20000 training-seed bootstrap, n3 per setting; per-checkpoint10 independent eval seeds; no prior-batch pooling',
          'confirm_selection':'best fixed by development SR only plus final, no confirm-based choice',
          'original_complex_assets':'missing, diagnostic retrain not exact historical reproduction',
          'budget_origin':'native default5M; extension10M not historical20M doubled',
          'rule_for_improvement':'mean best held-out SR>20pct is diagnostic trigger; any successes reported; no silent data replacement',
          'boundary_rule':'failure at finite budgets is not proof of task unlearnability',
          'scenario_change':'none; simplified-complex intervention deferred pending explicit engine/scenario permission',
          'task_mode':'continuous','environment_and_reward_unchanged':True}
        write(out/'manifest/protocol.json',protocol)
        try:
            write(out/'status.json',{'state':'running','phase':'asset-audit','started_at':start})
            info,transfer=audit(a,out)
            cmd=[sys.executable,'-B',str(Path(__file__).with_name('e14_worker.py')),'smoke','--source',str(a.source),'--output',str(out/'raw/smoke')]
            with (out/'logs/smoke.log').open('w') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300).returncode
            if code:raise ValueError('Training instrumentation smoke failed; no campaign launched')
            verify(frozen);report_initial(out,info,transfer)
            jobs=[(n,s) for n in CONFIGS for s in SEEDS];records=[]
            write(out/'status.json',{'state':'running','phase':'diagnostic-training','done':0,'total':len(jobs),'workers':a.workers,'started_at':start})
            with ThreadPoolExecutor(max_workers=a.workers) as pool:
                futures={pool.submit(job,a,n,s):(n,s) for n,s in jobs}
                for future in as_completed(futures):
                    n,s=futures[future]
                    try:r=future.result()
                    except Exception as e:r={'name':n,'seed':s,'state':'failed-engineering','error':repr(e)}
                    records.append(r);write(out/'logs/job_records.json',records)
                    write(out/'status.json',{'state':'running','phase':'diagnostic-training','done':len(records),'total':len(jobs),
                      'errors':sum(r['state']!='completed' for r in records),'started_at':start,'updated_at':time.time()})
            results=analyze(out);verify(frozen)
            dest=out/'reports/r01';dest.mkdir(parents=True,exist_ok=True)
            lines=['# E14 Grid complex诊断结果','',json.dumps(results['configurations'],ensure_ascii=False,indent=2),'',
                   '判定：'+results['conclusion'], '原始论文数据未替换。旧complex训练轨迹/权重缺失，当前诊断不能认证旧0%来源；有限失败不能证明不可学。',
                   '完整配置、逐rollout曲线与原reward记录、开发选模及确认轨迹见raw和manifest；所有任务错误见logs/job_records.json。']
            (dest/'E14最终诊断报告_v1.md').write_text('\n'.join(lines)+'\n')
            write(out/'status.json',{'state':'completed' if all(r['state']=='completed' for r in records) else 'completed-with-engineering-failures',
              'source_unchanged':True,'elapsed_seconds':time.time()-start,'summary':results['conclusion'],'done':len(records),'total':len(jobs)})
        except Exception as e:
            write(out/'status.json',{'state':'failed-engineering','error':repr(e),'elapsed_seconds':time.time()-start});raise

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['launch','run','analyze'])
    p.add_argument('--source',type=Path,required=True);p.add_argument('--medium',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=12)
    a=p.parse_args()
    if a.command=='analyze':print(json.dumps(analyze(a.output),ensure_ascii=False));return
    if a.command=='launch':
        if a.output.exists():raise ValueError('Existing batch retained')
        (a.output/'logs').mkdir(parents=True)
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(a.output/'logs/mpl'))
        cmd=[sys.executable,'-B','-u',str(Path(__file__)),'run','--source',str(a.source),'--medium',str(a.medium),'--output',str(a.output),'--workers',str(a.workers)]
        with (a.output/'logs/supervisor.log').open('a') as f:proc=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        write(a.output/'logs/launch.json',{'pid':proc.pid,'started_at':time.time(),'command':cmd});print(json.dumps({'pid':proc.pid,'output':str(a.output)}));return
    run(a)

if __name__=='__main__':main()
