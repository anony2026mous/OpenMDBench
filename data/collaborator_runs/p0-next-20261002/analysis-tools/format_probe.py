"""JSON-schema engineering diagnostic. Preserves original confirmation/errors.

Same stimuli: this is NOT a fresh independent confirmation or new D1 admission.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import requests

SCHEMA={'type':'object','properties':{'label':{'type':'string','enum':['real','feint']},'p_real':{'type':'number','minimum':0,'maximum':1}},'required':['label','p_real'],'additionalProperties':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--code',type=Path,required=True);p.add_argument('--full',action='store_true');a=p.parse_args()
    sys.path.insert(0,str(a.code));from common import read,write,digest
    import e3_classify
    from e3_classify_v2 import SYSTEM_V2
    rows=read(a.campaign/'classification/dataset.json');primary=read(a.campaign/'classification/predictions.json');out=a.output;out.mkdir(parents=True,exist_ok=False)
    if not a.full:
        # Engineering strata, never correctness/gold-selected.
        failed=sorted([r['id'] for r in primary if r.get('error')]);valid=sorted([r['id'] for r in primary if not r.get('error')]);ids=set(failed[:8]+valid[:8]);rows=[r for r in rows if r['id'] in ids]
    protocol={'kind':'paired-format-engineering-diagnostic-not-independent-confirmation','n':len(rows),'source_dataset_sha':digest(a.campaign/'classification/dataset.json'),
        'same_system_prompt':True,'same_user_prompts':True,'same_model_temperature_max_tokens':True,'only_change':'response_format json_schema',
        'D1_thresholds_unchanged':[.6,.85],'source_numeric_control_preserved':True,'selection':'all400' if a.full else 'first8 parse failures+first8 parse successes by ID; never by correctness',
        'script_sha':digest(Path(__file__)),'schema':SCHEMA,'original_failed_attempts_retained':True}
    write(out/'protocol.json',protocol)
    def call(item):
        i,row=item;base=f'http://127.0.0.1:{8101+i%2}/v1'
        payload={'model':'Qwen3.8-27B','temperature':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},
          'messages':[{'role':'system','content':SYSTEM_V2},{'role':'user','content':row['prompt']}],
          'response_format':{'type':'json_schema','json_schema':{'name':'contact_role','strict':True,'schema':SCHEMA}}}
        record={'id':row['id'],'seed':row['seed'],'gold_real':row['gold_real'],'p_real':None,'endpoint':base,'request':payload};start=time.time()
        try:
            response=requests.post(base+'/chat/completions',json=payload,timeout=120);record['HTTP_status']=response.status_code;record['raw_text']=response.text
            response.raise_for_status();data=response.json();record['raw_response']=data
            text=data['choices'][0]['message'].get('content') or '';label=json.loads(text);prob=float(label['p_real'])
            if data['model']!='Qwen3.8-27B' or not np.isfinite(prob) or not 0<=prob<=1 or label['label'] not in ['feint','real'] or (prob>.5)!=(label['label']=='real'):raise ValueError('Invalid label/probability schema')
            record['p_real']=prob
        except Exception as err:record['error']=f'{type(err).__name__}: {err}'
        record['elapsed_seconds']=time.time()-start;write(out/'responses'/f"{row['id']}.json",record);return record
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(call,enumerate(rows)))
    summary={'kind':protocol['kind'],'n':len(results),'errors':sum(r['p_real'] is None for r in results),'engineering_error_rate':sum(r['p_real'] is None for r in results)/len(results),'not_independent_confirm':True}
    if a.full:summary['metrics']=e3_classify.metrics(results,'p_real')
    write(out/'results.json',results);write(out/'summary.json',summary);print(json.dumps(summary))


if __name__=='__main__':main()
