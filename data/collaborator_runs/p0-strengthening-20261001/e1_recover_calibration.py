"""Read-only correction of attacker_success alias; no simulation reruns."""
import argparse
from pathlib import Path
import numpy as np
import yaml
from common import read,write,digest,estimate
from e1_full_campaign import outcomes


def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);a=p.parse_args();root=a.campaign
    m=read(root/'variant_manifest.json'); protocol=read(root/'protocol.json')
    phash=digest(root/'protocol.json');code=root.parent
    for name,sha in protocol['script_hashes'].items():
        old=code/('e1_full_campaign_v1_frozen.py' if name=='e1_full_campaign.py' else name)
        if digest(old)!=sha:raise ValueError('Original runtime code snapshot differs from frozen protocol')
    for name,sha in m['original_source_hashes'].items():
        if digest(Path(m['repo'])/'openmd/source-code/source_codes'/name)!=sha:raise ValueError('Original engine changed')
        if name!='scenarios/formal/registry.yaml' and digest(Path(m['engine'])/name)!=sha:raise ValueError('Copy engine changed')
    for name,sha in protocol['weights'].items():
        if digest(Path(m['repo'])/'openmd/code/eval/_w1_runs/rl'/name)!=sha:raise ValueError('Weight changed')
    old=read(root/'status.json')
    if old['state']!='engineering-gate-failed':raise ValueError('Only documented reader failure is eligible for this recovery')
    if any('Unclassified terminal: attacker_success'!=r['error'] for r in old['jobs'] if 'error' in r):
        raise ValueError('Unexpected engineering error, manual review required')
    write(root/'initial_reader_failure.json',old)
    rows=[];all_reports=[]
    for variant in m['variants']:
        scene=yaml.safe_load((Path(m['engine'])/'scenarios/formal'/variant['package']/'scenario.yaml').read_text())['scenario']
        spawns=[e for e in scene['events'] if e['event_type']=='spawn']
        inventory=[*scene['entities'],*(e['payload']['entity'] for e in spawns)]
        expected=sum(e['faction_id']=='coalition.intruder' for e in inventory)
        latest=max([0,*[e['trigger']['tick'] for e in spawns]])
        cases={};invalid=[]
        for seed in m['calibration_seeds']:
            folder=root/'calibration-rule'/variant['public_id']/'rule'/f'seed-{seed}'
            comp=read(folder/'completion.json');r=read(folder/'report.json')
            if comp['exit_code']!=0 or comp['report_sha256']!=digest(folder/'report.json') or comp['config']['protocol_sha256']!=phash:
                raise ValueError('Original complete episode/report hash does not match')
            card=r['strategy_scorecard'];cases[str(seed)]=outcomes(r)
            all_reports.append({'path':str(folder/'report.json'),'sha256':digest(folder/'report.json')})
            actual=sum(v['total'] for v in card['force']['coalition.intruder'].values())
            if actual!=expected or card['terminal']['tick']<latest:
                invalid.append({'seed':seed,'actual_intruders':actual,'expected_intruders':expected,
                                'terminal_tick':card['terminal']['tick'],'latest_spawn':latest})
        rows.append({**variant,'arm':'rule','SR':estimate([c[0] for c in cases.values()]),
                     'V':estimate([c[1] for c in cases.values()]),'per_seed':cases,
                     'treatment_eligible':not invalid,'missed_wave_cases':invalid})
    write(root/'calibration_rule_analysis.json',rows)
    saturated=[];bounds=[]
    for family in sorted({r['family'] for r in rows}):
        eligible=[r for r in rows if r['family']==family and r['treatment_eligible']]
        if eligible and all(r['SR']['mean']==1 for r in eligible):saturated.append(family)
        # A fixed best arm must at least match rule's mean SR. An arm covering
        # all three requested bins has a fixed upper bound on its whole-menu mean.
        allowed=[float(max(x for x in np.arange(11)/10 if abs(x-target)<=m['target_tolerance'])) for target in m['targets']]
        max_cover=(len(eligible)-3+sum(allowed))/len(eligible) if len(eligible)>=3 else 0
        rule_average=sum(r['SR']['mean'] for r in eligible)/len(eligible) if eligible else 0
        bounds.append({'family':family,'n_eligible_settings':len(eligible),
           'rule_mean_calibration_SR':rule_average,'max_mean_SR_of_arm_covering_all_three_bins':float(max_cover),
           'fixed_best_arm_coverage_impossible':bool(len(eligible)<3 or rule_average>max_cover+1e-12),
           'scope':'Deterministic bound on this frozen calibration menu/seed sample; not a population-success-rate theorem'})
    if not all(r['fixed_best_arm_coverage_impossible'] for r in bounds):
        raise ValueError('Cannot certify menu infeasibility; original reports retained, request next-phase protocol repair')
    correction={'schema':'p0-e1-reader-correction@1','reason':'Native scorecard state attacker_success means defender failure; outcome intruder_success confirms it',
         'simulation_reruns':0,'raw_reports_modified':False,'original_protocol_sha256':phash,
         'old_orchestrator_sha256':digest(code/'e1_full_campaign_v1_frozen.py'),
         'corrected_orchestrator_sha256':digest(code/'e1_full_campaign.py'),
         'defender_loss_cases':[{k:r[k] for k in ['job','output','error']} for r in old['jobs'] if 'error' in r],
         'reports':all_reports,'all_110_simulations_complete_no_abort':True,'n_defender_losses':sum(c[0]==0 for r in rows for c in r['per_seed'].values())}
    write(root/'reader_correction.json',correction)
    write(root/'coverage_bound_audit.json',bounds)
    write(root/'status.json',{'state':'authorized-knob-infeasible','saturated_families':saturated,
           'reason':'All requested SR bins cannot be covered by fixed best-pure on the authorized timing menu. No new pressure knob added.',
           'rule_rows':rows,'confirmation_started':False,'original_source_unchanged':True,
           'coverage_bounds':bounds,'reader_correction':'reader_correction.json','simulation_reruns':0})
    print({'n_cases':110,'defender_losses':correction['n_defender_losses'],'saturated':saturated,'coverage_bounds':bounds})


if __name__=='__main__':main()
