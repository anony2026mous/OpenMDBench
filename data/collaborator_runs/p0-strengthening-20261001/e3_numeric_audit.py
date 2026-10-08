"""Untuned continuous numeric-score robustness controls; no primary gate replacement."""
import argparse
from pathlib import Path
import numpy as np
from common import read,write,digest
from e3_classify import metrics


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);a=p.parse_args()
    events={r['id']:r for r in read(a.input/'dataset.json')}
    rows=read(a.input/'predictions.json')
    for r in rows:
        e=events[r['id']]
        v=np.array(e['numeric']['headings'],float).mean(axis=0)
        d=np.array([1,18])-np.array(e['numeric']['positions'][-1],float)
        projection=float(v@d); denominator=float(np.linalg.norm(v)*np.linalg.norm(d))
        cosine=projection/denominator if denominator else 0
        r['continuous_projection']=.5+.5*projection/(1+abs(projection))
        r['continuous_cosine']=.5+.5*float(np.clip(cosine,-1,1))
    answer={'dataset_sha256':digest(a.input/'dataset.json'),
        'controls':{key:metrics(rows,key) for key in ['rule_p_real','continuous_projection','continuous_cosine','llm_p_real']},
        'definitions':{'continuous_projection':'p=.5+.5*projection/(1+abs(projection)); monotone ranking, no fitted scale',
             'continuous_cosine':'p=(1+cos(mean_observed_heading, port_minus_last_position))/2; zero-norm ->.5'},
        'interpretation':'Same numeric observations, no tuned threshold; continuous controls preserve projection-sign decisions. LLM AUC advantage over a binary rule may partly reflect score resolution.',
        'scope':'Post hoc untuned robustness diagnostic; original primary gate, all events and all original responses unchanged'}
    write(a.input/'numeric_robustness.json',answer)
    print({key:{'accuracy':value['accuracy'],'auc':value['auc']} for key,value in answer['controls'].items()})


if __name__=='__main__':main()
