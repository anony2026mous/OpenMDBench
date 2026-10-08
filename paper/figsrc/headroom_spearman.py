#!/usr/bin/env python3
"""Headroom trend within the admitted high-fidelity family.

Per admitted scenario: best monolithic baseline composite (max of pure-rule,
pure-RL episode means) vs. each layered stack's withheld-regime gain over it;
Spearman rank correlation between baseline strength and hybrid gain.
Backs the numbers cited in Appendix A. Data: data/hifi_withheld/DATASET_5SEEDS.json
(709 episodes; baselines read no briefing channel, LLM arms filtered to
briefing == "withheld"). Usage: python3 headroom_spearman.py
"""
import json, math, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "hifi_withheld", "DATASET_5SEEDS.json")

def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0]*len(xs); i = 0
    while i < len(order):
        j = i
        while j+1 < len(order) and xs[order[j+1]] == xs[order[i]]: j += 1
        avg = (i+j)/2.0 + 1.0
        for k in range(i, j+1): r[order[k]] = avg
        i = j+1
    return r

def spearman(a, b):
    ra, rb = ranks(a), ranks(b); n = len(a)
    ma, mb = sum(ra)/n, sum(rb)/n
    cov = sum((x-ma)*(y-mb) for x, y in zip(ra, rb))
    va = sum((x-ma)**2 for x in ra); vb = sum((y-mb)**2 for y in rb)
    return cov/(math.sqrt(va)*math.sqrt(vb))

def t_sf(t, df):
    """P(T > t) for Student t via composite Simpson on the density tail."""
    c = math.exp(math.lgamma((df+1)/2.0) - math.lgamma(df/2.0)) / math.sqrt(df*math.pi)
    f = lambda z: c*(1.0+z*z/df)**(-(df+1)/2.0)
    a, b, n = float(t), float(t)+60.0, 6000
    h = (b-a)/n; s = f(a)+f(b)
    for i in range(1, n): s += (4 if i % 2 else 2)*f(a+i*h)
    return s*h/3.0

def p_two_sided(rho, n):
    if n <= 3 or abs(rho) >= 1.0: return float("nan")
    t = abs(rho)*math.sqrt((n-2)/(1.0-rho*rho))
    return 2.0*t_sf(t, n-2)

def main():
    rows = json.load(open(DATA))
    per = defaultdict(lambda: defaultdict(list))
    for r in rows: per[r["scenario"]][r["arm"]].append(r)
    scen = sorted(per)
    base, gain = {}, {"llm-rule": {}, "llm-rl": {}}
    print("%-26s %7s %7s %8s %9s %9s" % ("scenario", "rule", "rl", "best", "dLLM+R", "dLLM+RL"))
    for s in scen:
        d = per[s]
        rule = sum(x["score"] for x in d["rule-rule"])/len(d["rule-rule"])
        rl = sum(x["score"] for x in d["rl"])/len(d["rl"])
        base[s] = max(rule, rl)
        for arm in ("llm-rule", "llm-rl"):
            vals = [x["score"] for x in d[arm] if x["briefing"] == "withheld"]
            gain[arm][s] = sum(vals)/len(vals) - base[s]
        print("%-26s %7.3f %7.3f %8.3f %+9.3f %+9.3f" % (s, rule, rl, base[s], gain["llm-rule"][s], gain["llm-rl"][s]))
    order = sorted(scen, key=lambda s: -base[s])
    rank_of = {s: i+1 for i, s in enumerate(order)}
    losses = [(arm, s) for arm in ("llm-rule", "llm-rl") for s in scen if gain[arm][s] < 0]
    print("\nloss cells (gain < 0): %d of 28" % len(losses))
    for arm, s in sorted(losses, key=lambda x: rank_of[x[1]]):
        print("  %-8s %-26s baseline=%.3f rank=%d/14" % (arm, s, base[s], rank_of[s]))
    top4 = sum(1 for _, s in losses if rank_of[s] <= 4)
    print("losses in the 4 strongest-baseline scenarios: %d/%d" % (top4, len(losses)))
    ie03 = next(s for s in base if s.startswith("IE-03"))
    print("\nSpearman(best baseline, hybrid gain), n=14:")
    for arm in ("llm-rule", "llm-rl"):
        rho = spearman([base[s] for s in scen], [gain[arm][s] for s in scen])
        print("  %-8s rho=%+.3f  p=%.4f" % (arm, rho, p_two_sided(rho, 14)))
    keep = [s for s in scen if s != ie03]
    print("excluding %s (n=13):" % ie03)
    for arm in ("llm-rule", "llm-rl"):
        rho = spearman([base[s] for s in keep], [gain[arm][s] for s in keep])
        print("  %-8s rho=%+.3f  p=%.4f" % (arm, rho, p_two_sided(rho, 13)))

if __name__ == "__main__":
    main()
