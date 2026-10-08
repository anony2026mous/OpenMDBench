"""Render ROC from frozen E10 CSV outputs; does not change predictions."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args()
    target=a.batch/'reports/r01/E10_Grid_ROC.png'
    if target.exists():raise ValueError('Existing figure retained')
    fig,axes=plt.subplots(1,2,figsize=(9,4),constrained_layout=True)
    for ax,tier in zip(axes,['medium','complex']):
        for key,label in [('grid_p_real','Grid plane only'),('llm_p_real','LLM briefing (reused)')]:
            with (a.batch/f'analysis/a01/{tier}/ROC_{key}.csv').open() as f:rows=list(csv.DictReader(f))
            ax.plot([float(r['fpr']) for r in rows],[float(r['tpr']) for r in rows],label=label)
        ax.plot([0,1],[0,1],'--',color='gray',linewidth=1)
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='False positive rate',ylabel='True positive rate',title=tier.capitalize())
        ax.legend(loc='lower right',fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('E10: retrospective controlled-stimulus comparison')
    fig.savefig(target,dpi=180);plt.close(fig)


if __name__=='__main__':main()
