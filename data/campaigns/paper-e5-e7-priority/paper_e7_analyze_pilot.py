"""Read-only E7 pilot analysis; optional detached watcher, no experiment changes."""
from __future__ import annotations
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, q):
    values = sorted(values); x = (len(values) - 1) * q; left = math.floor(x); right = math.ceil(x)
    return values[left] + (values[right] - values[left]) * (x - left)


def bootstrap(values):
    if len(values) < 3: return None
    means = [statistics.fmean(sample) for sample in itertools.product(values, repeat=len(values))]
    return {"mean": statistics.fmean(values), "ci95": [percentile(means,.025),percentile(means,.975)],
            "unit": "seed", "n": len(values), "enumerated_bootstrap_samples": len(means),
            "interpretation": "Exploratory three-seed interval, not confirmatory saturation evidence"}


def analyze(run_dir):
    run_dir = Path(run_dir); plan_path = run_dir / "plan.json"; plan = json.loads(plan_path.read_text())
    state = json.loads((run_dir / "status.json").read_text()); records = []
    for entry in state["completed"]:
        path = Path(entry["result"])
        if not path.exists():
            records.append({"case_id":entry["case_id"],"analysis_valid":False,"missing_result":True});continue
        if entry.get("sha256") and sha(path) != entry["sha256"]: raise ValueError("Case result hash changed")
        r = json.loads(path.read_text())
        if entry.get("reused_E7_preflight_reference"):
            row = {"case_id":entry["case_id"],"seed":r["config"]["seed"],"interval":0,"V":r["V"],
                "analysis_valid":entry["analysis_valid"],"steps":r["steps"],"llm_calls":0,"API_total_tokens":0,
                "goal_bytes":0,"llm_seconds":0,"wall_seconds":r["elapsed_seconds"]}
        else:
            costs=r["costs"]; calls=costs["llm_calls"]; tokens=costs["actual_API_total_tokens"]
            row={"case_id":entry["case_id"],"seed":r["seed"],"interval":r["interval"],"V":r["V"],
                "analysis_valid":r["analysis_valid"],"invalid_reasons":r["invalid_reasons"],"steps":r["steps"],
                "llm_calls":calls,"API_total_tokens":tokens if tokens or not calls else None,
                "goal_bytes":costs["issued_goal_serialized_bytes"],"llm_seconds":costs["request_seconds"],
                "wall_seconds":costs["episode_wall_seconds"]}
            row["planner_fallback_count"]=r.get("agent_stats",{}).get("fallback_count")
            row["goai_rejected"]=r.get("agent_stats",{}).get("goai_rejected")
            row["executor_stats"]=r.get("agent_stats",{}).get("executor")
            row["RL_controller_observation"]=r.get("RL_controller_observation")
        row.update(result_path=str(path),result_sha256=sha(path))
        for label,field in [("calls_per_100_steps","llm_calls"),("tokens_per_100_steps","API_total_tokens"),("goal_bytes_per_100_steps","goal_bytes")]:
            row[label]=100*row[field]/row["steps"] if row.get("steps") and row.get(field) is not None else None
        records.append(row)
    lookup={(r["seed"],r["interval"]):r for r in records if r.get("analysis_valid")}
    expected={(s,k) for s in plan["seeds"] for k in [0,*plan["intervals"]]}
    complete=state["status"]=="complete" and set(lookup)==expected and len(records)==12
    continuity=[]
    for original in plan.get("service_identity_at_launch", []):
        try:
            text=Path('/proc',str(original['pid']),'stat').read_text();fields=text[text.rfind(')')+2:].split()
            matched=fields[19]==str(original['start_ticks'])
        except FileNotFoundError:matched=False
        continuity.append({"pid":original["pid"],"same_process_start":matched})
    if continuity and not all(r["same_process_start"] for r in continuity):complete=False
    summary={"schema":"E7-frequency-pilot-analysis@1","run_status":state["status"],"plan_sha256":sha(plan_path),
        "analyzer_sha256":sha(Path(__file__)),
        "frequency_axis_only":True,"full_teacher_two_axis_scan_completed":False,"records":records,
        "all_preregistered_cases_valid":complete,"model_process_continuity":continuity,"seed_count":len(plan["seeds"]),"group_summary":None,
        "saturation_verdict":"not_available_incomplete_or_invalid_validation",
        "cost_interpretation":"Operational proxies: calls, API tokens and canonical issued-Goal bytes; no claim these are Shannon bits or a fitted analytic f",
        "causal_limitations":["Requested replanning frequency is not proof that every issued goal was accepted",
            "Rejected goals and execution/default behavior may also explain a flat or declining curve",
            "No P0 gate experiments or information-count-axis experiments were run"],
        "E5_human_annotation_or_kappa_computed":False}
    if complete:
        groups=[]
        for interval in plan["intervals"]:
            rows=[lookup[(s,interval)] for s in plan["seeds"]]
            gain=[r["V"]-lookup[(r["seed"],0)]["V"] for r in rows]
            means={k:statistics.fmean(r[k] for r in rows) if all(r[k] is not None for r in rows) else None
                   for k in ["llm_calls","API_total_tokens","goal_bytes","llm_seconds","wall_seconds","calls_per_100_steps","tokens_per_100_steps","goal_bytes_per_100_steps"]}
            groups.append({"interval":interval,"utility":bootstrap([r["V"] for r in rows]),"gain_vs_fixed_RL":bootstrap(gain),"mean_costs":means})
        increments=[]
        for before,after in zip(plan["intervals"],plan["intervals"][1:]):
            values=[lookup[(s,after)]["V"]-lookup[(s,before)]["V"] for s in plan["seeds"]]
            increments.append({"from_interval":before,"to_interval":after,"utility_increment":bootstrap(values)})
        delta=increments[-1]["utility_increment"]["mean"]
        increasing=groups[-1]["mean_costs"]["calls_per_100_steps"]>groups[-2]["mean_costs"]["calls_per_100_steps"]
        verdict=("cost_density_did_not_increase_no_saturation_test" if not increasing else
                 "more_cost_with_mean_utility_degradation_not_a_clean_plateau" if delta<0 else
                 "descriptive_plateau_candidate_not_confirmatory" if delta<=.05 else
                 "no_observed_plateau_at_tested_frequency_levels")
        ceiling=sum(lookup[(s,0)]["V"]==1.0 for s in plan["seeds"])
        if verdict=="descriptive_plateau_candidate_not_confirmatory" and ceiling==len(plan["seeds"]):
            verdict="descriptive_plateau_with_saturated_RL_reference_not_isolated_c_saturation"
        summary.update(group_summary=groups,paired_adjacent_increments=increments,saturation_verdict=verdict,
            teacher_point_estimate_threshold_met=bool(increasing and delta<=.05),
            high_frequency_mean_utility_increment=delta,
            baseline_utility_by_seed={str(s):lookup[(s,0)]["V"] for s in plan["seeds"]},
            fixed_RL_reference_at_native_utility_ceiling_count=ceiling,
            utility_definition="Frozen grid blue_score = 0.6*mission_success + 0.2*red_combatant_elimination_fraction + 0.2*blue_survival_fraction; upper bound 1",
            no_cross_batch_data_merged=True,small_sample_caution="Three seeds cannot establish a universal or precisely located saturation point")
    directory=run_dir/"analysis";directory.mkdir(exist_ok=True)
    (directory/"summary.json").write_text(json.dumps(summary,indent=2)+chr(10))
    fields=["case_id","seed","interval","analysis_valid","V","steps","llm_calls","API_total_tokens","goal_bytes","llm_seconds","wall_seconds","calls_per_100_steps","tokens_per_100_steps","goal_bytes_per_100_steps"]
    with (directory/"per_case.csv").open("w",newline="",encoding="utf-8-sig") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore");writer.writeheader();writer.writerows(records)
    if complete:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(10,4))
        for ax,xkey,ykey,title in [(axes[0],"calls_per_100_steps","utility","Utility versus call density"),
                                   (axes[1],"goal_bytes_per_100_steps","gain_vs_fixed_RL","Gain versus Goal carrier density")]:
            xs=[g["mean_costs"][xkey] for g in groups];ys=[g[ykey]["mean"] for g in groups]
            lo=[y-g[ykey]["ci95"][0] for y,g in zip(ys,groups)];hi=[g[ykey]["ci95"][1]-y for y,g in zip(ys,groups)]
            ax.errorbar(xs,ys,yerr=[lo,hi],marker="o",capsize=3)
            for x,y,g in zip(xs,ys,groups):ax.annotate('k='+str(g['interval']),(x,y),xytext=(4,5),textcoords='offset points')
            ax.set_title(title);ax.set_xlabel(xkey);ax.set_ylabel(ykey);ax.grid(alpha=.2)
        fig.suptitle('E7 frequency-only pilot: 3 seeds; exploratory seed-bootstrap intervals');fig.tight_layout()
        fig.savefig(directory/"frequency_cost_pilot.svg");fig.savefig(directory/"frequency_cost_pilot.png",dpi=170);plt.close(fig)
    return summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run-dir",type=Path,required=True);p.add_argument("--wait",action="store_true")
    args=p.parse_args();started=time.monotonic()
    while args.wait:
        status=json.loads((args.run_dir/"status.json").read_text())
        if status["status"]!="running":break
        if not Path('/proc',str(status['pid'])).exists():break
        if time.monotonic()-started>43200:break
        time.sleep(30)
    result=analyze(args.run_dir);print(json.dumps({"run_status":result["run_status"],"all_cases_valid":result["all_preregistered_cases_valid"],"verdict":result["saturation_verdict"]}))
