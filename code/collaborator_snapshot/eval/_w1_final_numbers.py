"""Final numbers dump for the paper document: arm means, seen/unseen split, stable counts."""
from __future__ import annotations

import statistics as st

import _w1_common as c

llm = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)
decl = c.collect(c.SNAP, "*.json", briefing="declared", strict_arms=True,
                 provenance="legacy-ok")

D4 = {"IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
      "IE-05-MULTI-AXIS"}


def three_part(by, sc, h, o):
    hs = {k: st.mean(v) for k, v in by.get((sc, h), {}).items() if v}
    os_ = {k: st.mean(v) for k, v in by.get((sc, o), {}).items() if v}
    ha, oa = c.vals(by, sc, h), c.vals(by, sc, o)
    if len(ha) < 2 or len(oa) < 2:
        return None
    mh, mo = st.mean(ha), st.mean(oa)
    mean_ok = mh > mo
    seed_ok = len(hs) >= 2 and len(os_) >= 2 and min(hs.values()) > max(os_.values())
    order = sorted(hs)
    split_ok = mean_ok
    if len(order) >= 4:
        a1, a2 = order[:len(order) // 2], order[len(order) // 2:]
        split_ok = (st.mean([hs[x] for x in a1]) > mo
                    and st.mean([hs[x] for x in a2]) > mo)
    return mean_ok and seed_ok and split_ok


# merged view for the verdicts
from collections import defaultdict
main: dict = defaultdict(lambda: defaultdict(list))
for k, v in llm.items():
    for sd, s in v.items():
        main[k][sd].extend(s)
for a in c.BASE_ARMS:
    for sc in c.IE:
        for sd, s in base.get((sc, a), {}).items():
            main[(sc, a)][sd].extend(s)

print("=== ARM SUMMARY (4 seeds) ===")
for a in c.ARMS:
    src = llm if a in c.LLM_ARMS else base
    allv = [x for sc in c.IE for x in c.vals(src, sc, a)]
    stc = counter = 0
    if a in c.LLM_ARMS:
        for sc in c.IE:
            for o in c.BASE_ARMS:
                r = three_part(main, sc, a, o)
                if r is True:
                    stc += 1
                elif r is False and st.mean(c.vals(main, sc, a) or [0]) < st.mean(
                        c.vals(main, sc, o) or [0]):
                    counter += 1
    w_rr = sum(1 for sc in c.IE if c.vals(src, sc, a) and c.vals(base, sc, "rule-rule")
               and st.mean(c.vals(src, sc, a)) > st.mean(c.vals(base, sc, "rule-rule")))
    w_rl = sum(1 for sc in c.IE if c.vals(src, sc, a) and c.vals(base, sc, "rl")
               and st.mean(c.vals(src, sc, a)) > st.mean(c.vals(base, sc, "rl")))
    print(f"  {c.LABEL[a]:<12} mean={st.mean(allv):.4f} sd={st.pstdev(allv):.4f} "
          f"n={len(allv):>3} STABLE={stc:>2} beats_rr={w_rr:>2}/14 beats_rl={w_rl:>2}/14")

print("\n=== SEEN (llm-rl 训练过的 4 场景) vs UNSEEN (10) ===")
for a in c.ARMS:
    src = llm if a in c.LLM_ARMS else base
    s = [x for sc in D4 for x in c.vals(src, sc, a)]
    u = [x for sc in c.IE if sc not in D4 for x in c.vals(src, sc, a)]
    print(f"  {c.LABEL[a]:<12} seen={st.mean(s):.4f}(n={len(s):>2})  "
          f"unseen={st.mean(u):.4f}(n={len(u):>2})  gap={st.mean(s) - st.mean(u):+.4f}")

print("\n=== UNSEEN-ONLY MEANS (clean of llm-rl training overlap) ===")
for a in c.ARMS:
    src = llm if a in c.LLM_ARMS else base
    u = [x for sc in c.IE if sc not in D4 for x in c.vals(src, sc, a)]
    print(f"  {c.LABEL[a]:<12} {st.mean(u):.4f}  n={len(u)}")

print("\n=== DECLARED vs WITHHELD (4 seeds) ===")
for a in c.LLM_ARMS:
    w = [x for sc in c.IE for x in c.vals(llm, sc, a)]
    d = [x for sc in c.IE for x in c.vals(decl, sc, a)]
    better = sum(1 for sc in c.IE if c.vals(llm, sc, a) and c.vals(decl, sc, a)
                 and st.mean(c.vals(llm, sc, a)) > st.mean(c.vals(decl, sc, a)))
    tot = sum(1 for sc in c.IE if c.vals(llm, sc, a) and c.vals(decl, sc, a))
    print(f"  {c.LABEL[a]:<12} withheld={st.mean(w):.4f} declared={st.mean(d):.4f} "
          f"delta={st.mean(w) - st.mean(d):+.4f} better={better}/{tot}")

print("\n=== STABLE LISTS ===")
for a in c.LLM_ARMS:
    wins = []
    for sc in c.IE:
        for o in c.BASE_ARMS:
            if three_part(main, sc, a, o) is True:
                wins.append((sc, o, st.mean(c.vals(main, sc, a)) - st.mean(c.vals(main, sc, o))))
    print(f"  {c.LABEL[a]}: {len(wins)} 条 / {len({w[0] for w in wins})} 场景")
    for sc, o, d in wins:
        print(f"     {sc:<28} > {c.LABEL[o]:<10} {d:+.3f}")

print("\n=== COUNTEREXAMPLES (hybrid arms only) ===")
for sc in c.IE:
    for h in c.LLM_ARMS:
        for o in c.BASE_ARMS:
            r = three_part(main, sc, h, o)
            if r is False:
                mh = st.mean(c.vals(main, sc, h))
                mo = st.mean(c.vals(main, sc, o))
                if mh < mo:
                    print(f"  {sc:<28} {c.LABEL[h]:<10} < {c.LABEL[o]:<10} {mh - mo:+.3f}")
