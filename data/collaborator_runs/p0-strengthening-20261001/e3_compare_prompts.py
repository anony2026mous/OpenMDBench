"""Secondary same-event comparison of fixed original and rule-guided prompts."""
import argparse
from pathlib import Path
import numpy as np
from common import read,write,digest
from e3_classify import auc_matrix


def main():
    p=argparse.ArgumentParser(); p.add_argument('--campaign',type=Path,required=True); a=p.parse_args()
    originals=read(a.campaign/'original-prompt-control/predictions.json')
    refined=read(a.campaign/'classification/predictions.json')
    old={r['id']:r for r in originals}; new={r['id']:r for r in refined}
    if set(old)!=set(new): raise ValueError('Matched prompt comparison requires identical event IDs')
    ids=sorted(old)
    if any(old[k]['seed']!=new[k]['seed'] or old[k]['gold_real']!=new[k]['gold_real'] for k in ids):
        raise ValueError('Event truth/provenance changed')
    if any(r['llm_p_real'] is None for r in originals+refined):
        raise ValueError('Report invalid-response rates before running valid-score paired comparison')
    y=np.array([old[k]['gold_real'] for k in ids],bool)
    clusters=np.array([old[k]['seed'] for k in ids]); seeds=sorted(set(clusters))
    weights=np.random.default_rng(20261001).multinomial(len(seeds),np.ones(len(seeds))/len(seeds),size=20000)
    statistics={}
    count=np.array([sum(clusters==s) for s in seeds])
    for label,lookup in [('original',old),('rule_guided',new)]:
        scores=np.array([lookup[k]['llm_p_real'] for k in ids])
        _,pair,pos,neg=auc_matrix(y,scores,clusters)
        denom=(weights@pos)*(weights@neg); valid=denom>0
        auc_boot=np.einsum('bi,ij,bj->b',weights,pair,weights)[valid]/denom[valid]
        correct=(scores>.5)==y
        wins=np.array([sum(correct&(clusters==s)) for s in seeds])
        acc_boot=(weights@wins)/(weights@count)
        confusion={}
        for gold,label_name in [(False,'feint'),(True,'real')]:
            confusion[label_name]={'n':int(sum(y==gold)),'correct':int(sum(correct&(y==gold)))}
        statistics[label]={'accuracy':float(correct.mean()),'auc':float(pair.sum()/(pos.sum()*neg.sum())),
                            'accuracy_boot':acc_boot,'auc_boot':auc_boot,'confusion':confusion}
    o,n=statistics['original'],statistics['rule_guided']
    result={'n_events':len(ids),'n_seed_clusters':len(seeds),
       'original':{k:o[k] for k in ['accuracy','auc','confusion']},
       'rule_guided':{k:n[k] for k in ['accuracy','auc','confusion']},
       'accuracy_delta':{'mean':n['accuracy']-o['accuracy'],'ci95':np.quantile(n['accuracy_boot']-o['accuracy_boot'],[.025,.975]).tolist()},
       'auc_delta':{'mean':n['auc']-o['auc'],'ci95':np.quantile(n['auc_boot']-o['auc_boot'],[.025,.975]).tolist()},
       'threshold':.5,'bootstrap':'20,000 paired seed-cluster resamples',
       'scope':'Secondary prompt diagnostic; rule-guided geometric instructions are not additional truth/semantic information or proof of D1',
       'source_files':{str(p.relative_to(a.campaign)):digest(p) for p in [a.campaign/'classification/predictions.json',
                                                                       a.campaign/'original-prompt-control/predictions.json']}}
    write(a.campaign/'prompt_comparison.json',result)
    print(result)


if __name__=='__main__': main()
