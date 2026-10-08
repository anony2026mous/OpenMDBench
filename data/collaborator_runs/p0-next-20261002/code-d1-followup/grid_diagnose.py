"""Development-only diagnostics. Never rewrites confirmation or gate thresholds."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import numpy as np


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def load_channel(code):
    sys.path.insert(0,str(code))
    spec=importlib.util.spec_from_file_location('diagnostic_channel',code/'channel_experiment.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def accuracy(y,p):
    y=np.asarray(y,bool);p=np.asarray(p,float);correct=(p>.5)==y
    return {'accuracy':float(correct.mean()),'balanced_accuracy':float((correct[y].mean()+correct[~y].mean())/2),
            'auc':float((np.sum(p[y,None]>p[None,~y])+.5*np.sum(p[y,None]==p[None,~y]))/(y.sum()*(~y).sum()))}


def cv(rows,features,c):
    # Fixed exploratory model family. Shared four seed folds across all ablations.
    # No tuning against outer-fold outcomes; this is not the original final model.
    if len(rows)<40 or len({r['seed'] for r in rows})<12:return {'state':'insufficient-development-coverage','n':len(rows)}
    seeds=sorted({r['seed'] for r in rows});random.Random(20261003).shuffle(seeds);fold={s:i%4 for i,s in enumerate(seeds)}
    y=np.array([r['gold_real'] for r in rows],bool);x=np.asarray(features,float);p=np.zeros(len(rows))
    for k in range(4):
        tr=[i for i,r in enumerate(rows) if fold[r['seed']]!=k];te=[i for i,r in enumerate(rows) if fold[r['seed']]==k]
        if len(set(y[tr]))<2:return {'state':'fold-class-insufficient','n':len(rows)}
        model=c.fit(x[tr],y[tr],.1,True);p[te]=c.predict(model,x[te])
    # Point estimates of exploratory OOF scores; no falsely independent event CI.
    return {'state':'diagnostic-OOF','n':len(rows),'seed_clusters':len(seeds),**accuracy(y,p),
            'model':'fixed quadratic L2 logistic lambda0.1; 4 seed-group folds; no model selection',
            'probabilities':p.tolist()}


def analyze(campaign,code,out):
    c=load_channel(code);dev=read(campaign/'development_events.json')
    if not dev:raise ValueError('No development events')
    x=np.asarray([r['local_features'] for r in dev]);assert x.shape[1]==84
    groups={'complete':list(range(84)),'candidate_xy_only':[72,73],
            'local_grid_only':list(range(64)),'own_state_only':list(range(64,69)),
            'candidate_relative_cell':[76,77],'lock_only':[69,70,71,81,82,83],
            'kind_comm_jam':[78,79,80],'complete_without_explicit_xy':[i for i in range(84) if i not in range(72,76)],
            'complete_without_lock':[i for i in range(84) if i not in [69,70,71,81,82,83]]}
    ablations={}
    for name,ix in groups.items():
        ablations[name]=cv(dev,x[:,ix],c);print(json.dumps({'stage':'ablation','tier':campaign.name,'group':name,
                                                       'balanced_accuracy':ablations[name].get('balanced_accuracy')}),flush=True)
    allframes=0;visibleframes=0;first=[];window_role_changes=0;windows=0
    before_history=[];files=[];lookup={}
    selected_ids={r['id'] for r in dev}
    for p in sorted((campaign/'development').glob('seed-*/frames.json')):
        meta=read(p);audit=read(p.with_name('audit.json'))
        if not audit['eligible'] or digest(p)!=audit['frames_sha']:raise ValueError('Development provenance changed')
        files.append({'path':str(p),'sha':digest(p)});contacts={}
        for f in meta['frames']:
            allframes+=1;contacts.setdefault(f['contact'],[]).append(f)
            if c.visible_local(f):visibleframes+=1
        for cid,hist in contacts.items():
            vis=[(j,f) for j,f in enumerate(hist) if c.visible_local(f)]
            if vis:
                j,f=vis[0];first.append({'seed':meta['seed'],'gold_real':f['gold_real'],'local_features':c.current_features(f),'position':f['position'],'tick':f['tick']})
            for i in range(0,len(hist)-7,8):
                w=hist[i:i+8];token=f"{meta['seed']}:{cid}:{[f['tick'] for f in w]}";eid=hashlib.sha256(token.encode()).hexdigest()[:24]
                if eid in selected_ids:
                    windows+=1;changed=len({f['gold_real'] for f in w})>1;window_role_changes+=changed
                    lookup[eid]={'seed':meta['seed'],'ticks':[f['tick'] for f in w],'role_changed':changed,
                                 'first_observed_position':hist[0]['position'],'last_position':w[-1]['position']}
    cells={}
    for r in dev:cells.setdefault(tuple(r['numeric']['positions'][-1]),[]).append(r)
    matched=[r for cell,rs in cells.items() if len({q['gold_real'] for q in rs})==2 for r in rs]
    coordinate_rows=[{'position':list(cell),'feint':sum(not r['gold_real'] for r in rs),'real':sum(r['gold_real'] for r in rs)} for cell,rs in sorted(cells.items())]
    summary={'scope':'exploratory development-only; no confirmation tuning or certification',
        'campaign':str(campaign),'development_events_sha':digest(campaign/'development_events.json'),
        'source_rollouts':len(files),'events':len(dev),'class_counts':{str(v):sum(r['gold_real']==v for r in dev) for v in [False,True]},
        'seed_clusters':len({r['seed'] for r in dev}),'feature_layout':'grid0:64 own64:69 lockpos69:72 xy/dist72:76 relative76:78 kind78 comm79 jam80 locked81 age82 uncertainty83',
        'ablations':ablations,'history_audit':{'matched_original_windows':windows,'role_changed_windows':window_role_changes},
        'visibility_sampling':{'all_public_contact_frames':allframes,'currently_locally_visible_frames':visibleframes,
                              'first_visible_contacts':len(first),'first_visible_current_only':cv(first,[r['local_features'] for r in first],c)},
        'exact_xy_overlap':{'all_cells':len(cells),'both_class_cells':sum(len({r['gold_real'] for r in rs})==2 for rs in cells.values()),
                           'n_overlap_events':len(matched),'n_overlap_seeds':len({r['seed'] for r in matched}),
                           'matched_current_only':cv(matched,[r['local_features'] for r in matched],c)},
        'integrity':'all ablations diagnostic only; complete legitimate baseline retained; same-label cells not deleted from original confirmation'}
    write(out/'summary.json',summary);write(out/'position_class_counts.json',coordinate_rows)
    write(out/'development_window_audit.json',lookup);write(out/'development_provenance.json',files)
    lines=['# Grid D1开发数据判别线索诊断','',f'来源：`{campaign}`。仅开发数据，未读取确认输入/真值来调规则。','',
           '|字段组|OOF准确率|OOF平衡准确率|AUC|','|---|---:|---:|---:|']
    for name,row in ablations.items():
        if 'accuracy' in row:lines.append(f"|{name}|{row['accuracy']:.2%}|{row['balanced_accuracy']:.2%}|{row['auc']:.4f}|")
    overlap={k:v for k,v in summary['exact_xy_overlap'].items() if k!='matched_current_only'}
    overlap['matched_current_only']={k:v for k,v in summary['exact_xy_overlap']['matched_current_only'].items() if k!='probabilities'}
    lines+=['',f'当前事件{len(dev)}个，seed聚类{summary["seed_clusters"]}；窗口角色变化{window_role_changes}/{windows}。',
            f'精确坐标双类重叠：{overlap}。',
            f'首次局部可见时完整当前观测诊断：{summary["visibility_sampling"]["first_visible_current_only"] | {"probabilities": "omitted"} if "probabilities" in summary["visibility_sampling"]["first_visible_current_only"] else summary["visibility_sampling"]["first_visible_current_only"]}。','',
            '固定模型的字段消融用于定位可预测关联，不是因果证明、认证输入删减或正式D1成绩。'
            '位置可预测支持空间分布线索；删除显式坐标仍可辨时，网格+自身位置可能恢复它，不能称去除位置信息。'
            '首次可见探针可检验8次历史筛选/运动累积是否放大可辨性，但此前动作仍可能影响状态。'
            '精确坐标匹配仅开发诊断，需新独立协议和采样才能作为正式测试。']
    out.mkdir(parents=True,exist_ok=True);(out/'Grid_D1_开发线索诊断.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--code',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Existing diagnostic retained; use distinct path')
    analyze(a.campaign,a.code,a.output)
