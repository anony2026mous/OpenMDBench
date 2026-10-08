"""Display same-event prompt contrast and strong numeric ranking control."""
import argparse
from pathlib import Path
import numpy as np
from common import read


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);a=p.parse_args()
    refined=read(a.campaign/'classification/predictions.json')
    original={r['id']:r for r in read(a.campaign/'original-prompt-control/predictions.json')}
    events={r['id']:r for r in read(a.campaign/'classification/dataset.json')}
    gold=np.array([r['gold_real'] for r in refined],bool)
    scores={name:[] for name in ['Binary kinematic rule','Continuous projection','LLM original prompt','LLM rule-guided prompt']}
    for r in refined:
        e=events[r['id']];v=np.array(e['numeric']['headings'],float).mean(axis=0)
        d=np.array([1,18])-np.array(e['numeric']['positions'][-1],float);projection=float(v@d)
        scores['Binary kinematic rule'].append(r['rule_p_real'])
        scores['Continuous projection'].append(.5+.5*projection/(1+abs(projection)))
        scores['LLM original prompt'].append(original[r['id']]['llm_p_real'])
        scores['LLM rule-guided prompt'].append(r['llm_p_real'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10.5,4))
    for label,s in scores.items():
        s=np.array(s); thresholds=[float('inf'),*sorted(set(s),reverse=True),-float('inf')]
        fpr=[float(np.mean(s[~gold]>=t)) for t in thresholds]
        tpr=[float(np.mean(s[gold]>=t)) for t in thresholds]
        axes[0].plot(fpr,tpr,label=label,linestyle='--' if label=='Binary kinematic rule' else '-')
    axes[0].plot([0,1],[0,1],':',color='grey')
    axes[0].set(xlabel='False-positive rate',ylabel='True-positive rate',title='Same 400 held-out events: ROC',xlim=(0,1),ylim=(0,1.02))
    axes[0].legend(fontsize=8,loc='lower right')
    pair=read(a.campaign/'prompt_comparison.json')
    x=np.arange(2);width=.35
    for offset,(key,label) in enumerate([('original','Original prompt'),('rule_guided','Rule-guided prompt')]):
        vals=[pair[key]['confusion'][c]['correct']/pair[key]['confusion'][c]['n'] for c in ['feint','real']]
        bars=axes[1].bar(x+(offset-.5)*width,vals,width,label=label)
        axes[1].bar_label(bars,labels=[f'{v:.1%}' for v in vals],padding=3,fontsize=9)
    axes[1].set(xticks=x,xticklabels=['Feint (n=200)','Real (n=200)'],ylabel='Correctly classified fraction',
                title='Paired prompt diagnostic; threshold=0.5',ylim=(0,1.18))
    axes[1].legend(fontsize=8,loc='lower left')
    fig.tight_layout();fig.savefig(a.campaign/'prompt_and_numeric_controls.png',dpi=180);fig.savefig(a.campaign/'prompt_and_numeric_controls.svg')


if __name__=='__main__':main()
