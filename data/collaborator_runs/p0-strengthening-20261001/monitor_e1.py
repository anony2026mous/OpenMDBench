"""Read-only compact telemetry for the authorized queue."""
import argparse
import json
from pathlib import Path
import time
from common import read


def main():
    p=argparse.ArgumentParser(); p.add_argument('--campaign',type=Path,required=True); a=p.parse_args()
    result={'time':time.time()}
    for name in ['progress','status','equivalence_gate','finalization_status']:
        f=a.campaign/f'{name}.json'
        if f.exists():
            body=read(f)
            if name=='status': body={k:body[k] for k in ['state','saturated_families','confirmation_started'] if k in body}
            if name=='equivalence_gate': body={'passed':body['passed']}
            if name=='finalization_status': body={k:body[k] for k in ['state','campaign_state','archive'] if k in body}
            result[name]=body
    progress=result.get('progress',{}); phase=progress.get('phase','calibration-rule')
    logs=list((a.campaign/phase).glob('*/*/*/episode.jsonl')); ticks=[]
    errors=[]; reports=[]
    for path in logs:
        with path.open('rb') as f:
            f.seek(0,2); size=f.tell(); f.seek(max(0,size-32768)); tail=f.read().decode('utf-8',errors='replace')
        last_tick=0
        for line in tail.splitlines():
            try:
                row=json.loads(line); last_tick=max(last_tick,int(row.get('tick',0)))
            except (ValueError,TypeError): continue
        report=path.with_name('report.json')
        if report.exists():
            r=read(report); reports.append(r)
            if r.get('aborted'): errors.append({'path':str(report),'aborted':r['aborted']})
        else: ticks.append(last_tick)
    result.update(logs=len(logs),reports=len(reports),active_logs=len(ticks),
                  active_tick_range=[min(ticks),max(ticks)] if ticks else None,
                  engineering_errors=errors, elapsed_s=time.time()-progress.get('started_at',time.time()))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__': main()
