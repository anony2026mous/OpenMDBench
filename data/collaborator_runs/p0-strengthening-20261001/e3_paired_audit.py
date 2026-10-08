"""Paired-seed comparison of frozen E3 predictions; no threshold/prompt tuning."""
import argparse
from pathlib import Path
import numpy as np
from common import read, write, digest
from e3_classify import auc_matrix


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    rows=read(a.input/'predictions.json')
    if any(r['llm_p_real'] is None for r in rows):
        raise ValueError('This paired AUC comparison requires complete valid scores')
    y=np.array([r['gold_real'] for r in rows],bool)
    c=np.array([r['seed'] for r in rows])
    seeds=sorted(set(c)); rng=np.random.default_rng(20261001)
    weights=rng.multinomial(len(seeds),np.ones(len(seeds))/len(seeds),size=20000)
    estimates={}
    for key in ['rule_p_real','llm_p_real']:
        s=np.array([r[key] for r in rows])
        order,pair,pos,neg=auc_matrix(y,s,c)
        assert order==seeds
        denominator=(weights@pos)*(weights@neg)
        valid=denominator>0
        auc=np.einsum('bi,ij,bj->b',weights,pair,weights)[valid]/denominator[valid]
        counts=np.array([sum(c==seed) for seed in seeds])
        wins=np.array([sum(((s>.5)==y)&(c==seed)) for seed in seeds])
        acc=weights@wins/(weights@counts)
        estimates[key]={'auc':float(pair.sum()/(pos.sum()*neg.sum())),
                        'accuracy':float(((s>.5)==y).mean()),'auc_boot':auc,'accuracy_boot':acc}
    r,l=estimates['rule_p_real'],estimates['llm_p_real']
    answer={'prediction_sha256':digest(a.input/'predictions.json'),'n_events':len(rows),
            'n_seed_clusters':len(seeds),'seeds':[int(s) for s in seeds],'threshold':.5,
            'auc_LLM_minus_rule':{'mean':l['auc']-r['auc'],
                  'ci95':np.quantile(l['auc_boot']-r['auc_boot'],[.025,.975]).tolist()},
            'accuracy_LLM_minus_rule':{'mean':l['accuracy']-r['accuracy'],
                  'ci95':np.quantile(l['accuracy_boot']-r['accuracy_boot'],[.025,.975]).tolist()},
            'comparison':'Paired 20,000 seed-cluster resamples; every event shares model/rule resampling weights',
            'interpretation':'Exploratory ranking comparison; not D1 certification, no fitted threshold or removed events',
            'source_batches':sorted({r['source_batch'] for r in rows}),
            'sources':'Controlled-stimulus result only; source strata remain in corresponding analysis.json; architecture performance scores are not pooled'}
    write(a.output/'paired_audit.json',answer)
    print(answer)


if __name__=='__main__':
    main()
