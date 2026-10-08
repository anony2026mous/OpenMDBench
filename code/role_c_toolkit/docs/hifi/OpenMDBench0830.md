# OpenMDBench (AAMAS 2027 Submission — 0830 narrative restructure)

# OpenMDBench: An Open Evaluation Benchmark for Hybrid LLM-Small Model Multi-Agent Systems in Multi-Domain Adversarial Environments

## ABSTRACT

Unmanned systems are moving from single-domain swarms to **multi-domain operations**—aerial, surface, shore, and underwater platforms defending or attacking a shared theater. This shift creates a structural property we call **decision-stack bifurcation**: cross-domain deliberation (task allocation, intent inference, rules-of-engagement reasoning) demands semantic, open-ended, second-to-minute decisions, while intra-domain execution demands low-latency continuous control. The engineering community has already converged on the natural response—**hybrid LLM-small-model architectures**, with LLMs as deliberators and small models as executors—yet three scientific questions remain unanswered: *does* hybridization beat pure paradigms, *when* is it structurally necessary rather than convenient, and *where* does the bottleneck lie when it fails? Answering them requires controlled, reproducible comparison, which no existing benchmark provides: the closed, centralized submission model inherited from the MARL era is infeasible for proprietary LLMs and custom executors.

We present **OpenMDBench**. (i) We formalize multi-domain adversarial systems as a **hierarchical semi-MDP (HSemi-MDP)** with a **cross-domain coupling measure**, and distill an empirical **layering law** ΔV = −c + f(C_info, B_if)·headroom(V_m): hybrid advantage requires an interface cost budget, genuine cross-layer information, *and* headroom in the pure-execution baseline. (ii) We build a **distributed open evaluation platform**—simulation runs centrally, all inference runs locally via a polling API— instantiated with an asymmetric four-domain coastal-defense scenario, a 36-scenario task suite, and a layered metric suite. (iii) We contribute a **counterfactual-replay attribution method** that causally decomposes performance gaps into planning (ΔP), execution (ΔE), and synergy (ΔI) terms. Concept-validation experiments on a semantically enhanced grid instantiation (all results reproducible from released traces) show: the attribution method passes 5/5 injected-bottleneck tests with strict dose-response monotonicity; pure end-to-end MARL collapses exactly where semantic discrimination binds (100%/97%/0% success across difficulty) while scripted-rule orchestration survives (65%), confirming the task family is open to orchestration but closed to end-to-end small models; hybrid LLM systems realize *zero* net advantage on the grid (−2.7 Elo vs. best pure RL) because their failure is **structural**—injecting exclusive intelligence, doubling replanning frequency, and switching interface modality all fail to close the gap, tracing to a semantic-to-geometric decision-form mismatch rather than missing information; and interface modality is a load-matched double-edged sword (JSON wins at low semantic load, NL trends back at high load). These results fix sharp, falsifiable boundary conditions for the layering law and directly seed the requirement-driven design of the full high-fidelity benchmark (pilot-first acceptance gates included).

**Keywords:** multi-agent systems, evaluation benchmark, large language models, hybrid LLM-small model architecture, distributed open evaluation, multi-domain heterogeneous systems

---

## 1 INTRODUCTION

**From requirements, not fashion.** Crewed navies learned decades ago that defending a coastline is not one problem but two: a *deliberation* problem—whom to watch, what to engage, how to respect escalation rules—and an *execution* problem—flying, sailing, and sensing well enough to act. Unmanned and multi-domain operations inherit both problems at machine speed, across four physical domains at once (aerial, surface, shore, underwater). This is not a benchmark designer's invention; it is the requirement profile of every realistic multi-domain adversarial mission, from coastal defense to disaster response.

**The bifurcation is structural.** Multi-domain systems necessarily exhibit two decision layers with different computational characters. The **cross-domain deliberation layer** handles mission understanding, cross-domain resource allocation, multi-platform scheduling, adversarial intent inference, rules-of-engagement compliance, and dynamic replanning—problems with semantic state spaces, open-ended objectives, and second-to-minute cycles. The **intra-domain execution layer** handles platform control, trajectory tracking, sensor processing, and reactive avoidance—problems with continuous control spaces, well-defined rewards, and millisecond-to-second cycles. The boundary between the layers coincides with the boundary between physical domains: remove the domains and the deliberation layer collapses; remove execution difficulty and the problem degenerates to symbolic planning. Pure LLM agents cannot meet the latency and cost requirements of execution; pure RL agents face state-space explosion and cannot ingest open-ended language objectives or adversarial deception. **Hybrid LLM-small-model architectures are the engineering community's convergent response**, and an active literature is building them [14,15,16,30].

**Three questions, no ground to answer them.** If hybridization is the future, benchmark-grade evidence for three questions is conspicuously absent:

- **(Q1) Payoff:** Does a hybrid stack actually outperform the best pure paradigm—and where does it *underperform*?
- **(Q2) Necessity:** Under what measurable task properties is layering *structurally necessary* rather than merely convenient?
- **(Q3) Bottleneck:** When a hybrid fails, is the fault in planning, in execution, or in the interface between them?

The obstacle is infrastructural. Every existing multi-agent benchmark—from SMAC [1] to LLMArena [2]—inherits the closed, centralized submission model of the MARL era: users upload complete agent code. For hybrid systems this fails three ways: **computational friction** (centrally hosting billion-parameter LLMs for every user is prohibitive), **institutional friction** (proprietary weights and custom pipelines cannot be uploaded), and **architectural friction** (predefined interfaces constrain exactly the composition design space hybrid research explores). The result is a research paradox: the architectures are being built, but the community has no shared ground to compare them—and no diagnostic instrumentation to tell *why* one wins.

**OpenMDBench.** We resolve the paradox with a requirements-driven pipeline—formalize, build, instrument, validate:

- **Formalization first (Section 3).** We cast multi-domain adversarial systems as a **hierarchical semi-MDP (HSemi-MDP)** whose two layers have distinct state/action/time-scale structure, connected by a goal-parameterization interface with an explicit **carrying cost** c. We define **cross-domain coupling** in three complementary forms (action-, intrinsic-task-, and effective-policy-level) as the structural independent variable behind Q2, and we state an explicit **layering law** ΔV = −c + f(C_info, B_if)·headroom(V_m) whose boundary conditions our experiments then pin down.
- **Platform second (Section 4).** We implement a **distributed open evaluation architecture**: the benchmark keeps only simulation and metrics on a central server; all agent inference runs on user infrastructure via a polling API. We instantiate a four-domain asymmetric coastal-defense scenario (36 scenarios, 5 categories) and a layered metric suite separating planning-attributable from execution-attributable measures.
- **Diagnostics third (Section 5).** We contribute a **counterfactual-replay attribution method** exploiting the HSemi-MDP time-scale separation to decompose performance gaps into ΔP (planning), ΔE (execution), and ΔI (synergy), with five validity guarantees; and we operationalize coupling measurement (C_info, B_if) from execution traces.
- **Validation fourth (Section 6).** Before committing the full high-fidelity physics, we validate the entire pipeline—and extract the law's boundary conditions—on a **semantically enhanced grid instantiation** with a complete baseline family (pure RL, pure LLM, rule, hybrid; planner×executor factorial). All reported numbers derive from released per-episode traces.

**Contributions.** Our contributions are threefold, mapping one-to-one onto the pipeline:

**(C1) A formalization with an executable coupling theory (Section 3).** The HSemi-MDP formulation of multi-domain adversarial systems, the three-form cross-domain coupling measure, and the conditional **layering law** ΔV = −c + f(C_info, B_if)·headroom(V_m). Prior work asserted that hybrid advantage scales positively with coupling; our experiments *refute the unconditional form* and replace it with the conditional law—an arguably more useful contribution than a confirmed but unbounded hypothesis, because it tells environment designers exactly what a task must provide (asymmetric information, decision-form match, headroom) for layering to pay.

**(C2) OpenMDBench, a distributed open evaluation platform (Section 4).** The polling-API architecture that removes the computational, institutional, and architectural frictions excluding hybrid systems from all existing benchmarks; an asymmetric four-domain coastal-defense scenario family (36 scenarios, 5 categories, 108 configurations); and a layered metric suite separating planning-attributable from execution-attributable measures. All artifacts are released with per-episode traces.

**(C3) A diagnostic toolbox with validated causal methods (Sections 5–6).** A counterfactual-replay attribution method decomposing performance gaps into ΔP/ΔE/ΔI—validated on 5/5 injected-bottleneck cases with strict dose-response monotonicity—and trace-based coupling estimators (C_info, B_if). The concept-validation study (~1,000 episodes, eight experimental families, fully trace-reproducible) exercises the complete pipeline, pins down the layering law's boundary regime on the grid instantiation, and converts the findings into pre-registered acceptance gates (D1/D1′/D2/D3) for the high-fidelity instantiation.

**Paper organization.** Section 2 positions related work. Section 3 formalizes the problem and the coupling theory. Section 4 presents the platform. Section 5 presents the diagnostic methods. Section 6 reports concept-validation experiments. Section 7 discusses implications and limitations; Section 8 concludes.

---

## 2 RELATED WORK

**MARL Benchmarks.** Classic cooperative MARL benchmarks like SMAC [1] and SMACv2 [3] standardize CTDE algorithm comparison but operate in single domains with homogeneous agents. Efforts toward heterogeneity (HeMAC [4], LSHC [5], POAC [6]) and application benchmarks (APE [7], HIVEX [8]) remain single-domain; Melting Pot 2.0 [20] targets social-dilemma populations, not domain heterogeneity. PettingZoo [21] standardizes environment APIs; BenchMARL [22] and MARLLib [23] standardize training pipelines—all within the closed evaluation paradigm. None addresses hybrid LLM-small-model systems.

**LLM Multi-Agent Benchmarks.** LLMArena [2], BattleAgentBench [9], MindAgent [10], Decrypto [11], SPIN-Bench [12], and HIVE [13] evaluate LLM agents in interactive settings (with theory-of-mind studies [24] alongside), but run the LLM on the platform side—fundamentally different from our distributed paradigm where all inference is local. None spans multiple physical domains or evaluates hybrid stacks.

**Hybrid LLM-Small Model Architectures.** LAMARL [14], LGC-MARL [15], LERO [16], and reflective collaboration [30] demonstrate promising LLM-RL compositions—but provide no systematic evaluation framework for comparing designs, which is precisely what a benchmark must supply.

**Distributed and Federated Evaluation.** Distributed computation in RL has been training-side (distributed RL [17], IMPALA [18], A3C [26], federated RL [19]); FEDAGENT [25] federates LLM-agent *training*. To our knowledge, no prior benchmark runs simulation centrally while agent inference runs locally—a new evaluation paradigm.

**Comparison.** Table 1 summarizes: no existing benchmark combines multi-domain heterogeneity, hybrid-architecture support, natural-language task interfaces, and an open evaluation paradigm.

|Benchmark|Domain|Agent Type|Evaluation Paradigm|LLM Support|Hybrid Architecture|Natural Language Input|
|---|---|---|---|---|---|---|
|SMAC [1]|Single (StarCraft)|Homogeneous MARL|Closed centralized|✗|✗|✗|
|Melting Pot [20]|Single (grid)|Homogeneous MARL|Closed centralized|✗|✗|✗|
|PettingZoo [21]|Multiple|Mixed|Closed centralized|✗|✗|✗|
|LLMArena [2]|Single (games)|Pure LLM|Closed centralized|✓|✗|✓|
|BattleAgentBench [9]|Single (games)|Pure LLM|Closed centralized|✓|✗|✓|
|HIVE [13]|Single (RTS)|LLM + human|Closed centralized|✓|Partial|✓|
|**OpenMDBench**|**Multi-domain (4 domains)**|**Hybrid LLM-small model**|**Distributed open**|**✓**|**✓**|**✓**|

*Table 1: OpenMDBench vs. representative multi-agent benchmarks.*

---

## 3 PROBLEM DEFINITION: DECISION-STACK BIFURCATION AND FORMALIZATION

### 3.1 The Two Layers

We first make the requirement-driven structure explicit; every benchmark design choice descends from it.

*The cross-domain deliberation layer* operates on tasks, intentions, and coordination: (i) mission understanding—parsing natural-language briefings into subgoals; (ii) cross-domain resource allocation; (iii) multi-platform scheduling; (iv) adversarial intent inference—distinguishing feints from attacks; (v) rules-of-engagement compliance; (vi) dynamic replanning. State spaces are semantic, objectives open-ended, cycles second-to-minute.

*The intra-domain execution layer* operates on platform control: attitude/heading/depth regulation, trajectory tracking with dynamic obstacles, sensor processing, reactive evasion and counter-jamming, domain-specific tactics. State and action spaces are continuous, rewards dense and well-defined, cycles millisecond-to-second.

**Why single paradigms fail.** Pure LLMs violate execution latency/cost budgets; pure RL cannot span heterogeneous state spaces with semantic objectives and cannot ingest open-ended language or deception. The bifurcation is a property of the *problem*, not the solver.

### 3.2 HSemi-MDP Formalization

We formalize multi-domain adversarial systems as a **hierarchical semi-MDP** M = ⟨M_d, {M_e^k}, G⟩.

**Upper layer: deliberation Semi-MDP** M_d = ⟨S_d, A_d, P_d, R_d, γ_d, τ_d⟩. S_d = (X, Q, B, L) comprises the platform-task allocation matrix X, task-progress vector Q, opponent-intent belief B, and rules-of-engagement state L. Each action a_d = {(i, j, θ)} assigns platform i to task j with parameters θ; actions are event-driven with random inter-decision intervals τ_d. Transitions P_d are induced stochastically by lower-layer outcomes; R_d encodes mission completion, rule-violation penalties, and coordination bonuses; γ_d matches second-to-minute cycles.

**Lower layer: execution MDP family.** For each domain k ∈ D = {aerial, surface, shore, underwater}, M_e^k = ⟨S_e^k, A_e^k, P_e^k, R_e^k, γ_e^k⟩ with continuous physical states, domain-specific dynamics, and rewards R_e^k(s, a; G_k, w_k) parameterized by the goal set G_k and priority weights w_k handed down from a_d; γ_e^k matches millisecond-to-second cycles (10 Hz in our implementation).

**Inter-layer interface—with explicit cost.** The upper layer never emits low-level controls; it parameterizes lower MDPs via (G_k, w_k), and lower-layer termination events (goal reached, platform loss, communication drop) trigger upper-layer updates. Unlike prior treatments that idealize this interface as free, we model a **carrying cost c ≥ 0**: goal-conditioned execution is strictly weaker than an unconstrained monolithic policy when the goals carry no exploitable information (translation loss, latency, reduced reactivity). This single term, empirically identified below, reconciles why layering can hurt.

**Adversarial extension—evaluated defender vs. scripted attacker.** Red (defender—the *evaluated* side) and blue (attacker—a *standardized scripted force*) run role-specific HSemi-MDPs coupled through a shared environment state, with role-specific natural-language briefings Z = {Z_red, Z_blue}. The evaluation protocol fixes the attacker to a parameterized scripted adversary shared by all systems: this (i) standardizes scenarios for cross-system comparability, (ii) halves evaluation cost, and (iii) realizes the D1 deception design (the scripted attacker *is* the deception source), while its strength knobs serve as the D2 headroom-calibration instrument. The upper layer accordingly reduces to best-response against a fixed adversarial policy; a community two-role extension (systems challenging the attacker role through the same interface) remains supported but is not part of the evaluated protocol.

### 3.3 Cross-Domain Coupling and the Layering Law

A key structural parameter of any task instance is its **cross-domain coupling**—how much upper-layer decisions must coordinate across domains. Three complementary forms:

*(1) Action coupling.* C_action(a_d) = |{k ∈ D : ∃i, domain(i)=k and (i,·) ∈ a_d}|—domains touched by one allocation decision.

*(2) Intrinsic task coupling.* C_intrinsic(task) = D_min(task) · I(task), with D_min the minimum domain count required by task constraints and I ∈ [0,1] the inter-domain dependency strength (temporal +0.3, spatial co-location +0.3, information-flow +0.3, capped at 1).

*(3) Effective coupling.* C_effective(π, task) = (1/N) Σ_m C_action(a_d^m)—observable from execution traces; measures how much a policy *actually* coordinates.

**Operational refinements from execution traces.** Two trace-derived quantities make coupling measurable per episode: **C_info**, the information asymmetry between the deliberation layer's observation channel and the execution layer's (estimated as cross-layer mutual information), and **B_if**, the information actually flowing through the goal interface (estimated by k-NN KSG mutual information between goal streams and execution states; Section 5.2).

**The layering law.** Let V_m be the performance of the best *pure-execution* (monolithic) baseline, and ΔV = V_hybrid − V_m. Our experiments support the conditional form:

  **ΔV = −c + f(C_info, B_if) · headroom(V_m),**

with f ≥ 0 increasing in both arguments and headroom(V_m) = (V* − V_m)/(V* − V_min) the normalized gap to oracle. Reading: layering pays only when (i) the interface carries genuine cross-layer information (B_if > 0 requires C_info > 0 asymmetric by construction), (ii) the interface's carrying cost c is not yet saturated by that information, and (iii) the monolithic baseline leaves headroom. Prior unconditional formulations ("hybrid advantage scales positively with coupling") omit c and headroom and are refuted in our boundary-regime experiments (Section 6.4): at B_if ≈ 0, ΔV is significantly *negative* (pure cost); at saturated V_m ≥ 0.99, layering only loses; the single positive cell sits at the only tier with V_m = 0.83.

**Design corollaries (pre-registered acceptance gates).** The law converts directly into falsifiable environment requirements, which we enforce before any full-scale run: **(D1)** information asymmetry—numeric features of true/false threats deliberately indistinguishable, resolvable only via the semantic channel (rule discriminator ≤60%, LLM ≥85%); **(D1′)** decision-form match—the task's core difficulty must live in LLM-strong decision forms (intent inference, combinatorial scheduling, rule reasoning), not spatial micro-control (operationalized: a greedy scripted rule must not reach 90% of the rule-baseline score); **(D2)** headroom—best pure baseline SR ∈ [40%, 85%]; **(D3)** interface budget—granularity tiers must produce B_if gradients exceeding estimator variance. Section 6.6 shows what happens when D1′ is violated, and Section 6.7 embeds all four gates into the high-fidelity pilot protocol.

---

## 4 THE OPENMDBENCH PLATFORM

### 4.1 Distributed Open Evaluation Architecture

The **Central Simulation Server (CSS)** maintains environments, generates natural-language mission briefings, executes actions, and computes metrics. **User-Local Hybrid Agents (ULHAs)** run all inference on user infrastructure, communicating through a standardized **polling API** (RESTful HTTP, JSON payloads; full specification in Appendix B). Simulation advances asynchronously of inference: an LLM taking 60 s to deliberate does not block the server, and sessions are resumable—properties our load tests verify under 120 s injected decision latency. This single decoupling removes all three frictions: no weights or code cross the boundary (institutional), users bear their own inference cost (computational), and the composition design space stays fully open (architectural). Anti-gaming measures (rate limits, action-pattern integrity checks) bound the trust model, discussed in Section 7.2.

### 4.2 Scenario Family and Task Suite

We instantiate an **asymmetric coastal-defense** scenario. Red (defender—the evaluated side): UAVs (aerial; fast, endurance-limited, EO/IR), USVs (surface; interception), shore radar (long-range, unlimited endurance), AUVs (underwater; covert, communication-limited). Blue (attacker—the standardized scripted force): attack UAVs, fast attack craft, submarines—concentrated strike power with inferior sensing, deployed through tactic templates (saturation strike, multi-axis feint, escort assault, dispersed infiltration) with calibrated strength knobs. The asymmetry forces intent inference under partial observability.

**Task suite.** 36 scenarios across 5 categories, each at 3 difficulties (108 configurations): Reconnaissance (8), Tracking & Surveillance (8), Interception & Engagement (8), Area Denial (6), Emergency Response (6). Estimated intrinsic couplings: 1.2 / 1.8 / 2.2 / 2.8 / 2.0 respectively. Every task is designed against three principles: cross-domain coordination is *required* (≥2 domains), intra-domain execution is *non-trivial* (obstacles, degradation, endurance), and inter-layer coupling is *bidirectional* (upper choices alter execution difficulty; lower outcomes trigger replanning). Detailed parameters: Appendices A, C, G.

**Grid instantiation for concept validation.** Because the platform's scientific claims should not wait on high-fidelity physics, we also instantiate a **semantically enhanced grid-world port-defense** environment sharing the full interface stack (polling API, metric engine, two-role protocol). A 20×20 grid, 150 steps; blue fields 2 USVs + 1 UAV with a UAV→USV lock-based standoff-engagement chain (task coupling manipulable per §6.4); red runs scripted multi-wave attacks with **deception by construction**—50% of transports are feints whose numeric features are indistinguishable from genuine threats and whose only tell is heading kinematics visible through repeated semantic contacts, never in the local grid encoding; firing on a feint is an own-goal. Three difficulty tiers scale entity counts, action noise (0–0.20), communication delay/loss, anomaly rate (false intel, unknown relabeling), and an optional UAV-hunting jammer. Full specification: Appendix H. This instantiation is the experimental substrate of Section 6.

### 4.3 Layered Evaluation Metrics

Single-scalar rankings cannot answer Q1–Q3. We compute a **layered suite** from ~40 raw per-episode measures (all dumped as traces for offline reanalysis):

**Planning-attributable:** Mission Understanding Score (behavior–priority alignment); Resource Allocation Efficiency (vs. MILP optimum); Adaptability Score (time-to-recover after instruction switches, normalized by severity); Cross-Domain Coordination Score (handover success and timing across domains, lock-maintenance ratios); Opponent Intent Inference Score with sub-metrics Anticipation Lead Time, Feint Detection Rate, Target Prediction Accuracy (Appendix E).

**Execution-attributable:** Task Success Rate; Time/Energy Efficiency; Collision & Safety Score; Tracking Accuracy; friction statistics (fuel, jam events, packet loss, obstacle collisions).

**Composite** Score_total = α·Score_planning + β·Score_execution (default 0.5/0.5). Aggregation uses paired statistics (Wilcoxon signed-rank, sign tests, bootstrap CIs) with seeds paired across systems.

---
## 5 DIAGNOSTIC INSTRUMENTATION

Ranking cannot answer Q3. We instrument the benchmark with two causal tools that exploit the HSemi-MDP structure.

### 5.1 Counterfactual-Replay Attribution

**Method.** For a system (π_d, π_e) with performance V(π_d, π_e), we construct three counterfactuals: (1) *oracle-execution replay*—record the upper decision sequence D = {(t_m, a_d^m)}, force those decisions at the same times, replace execution with an oracle π_e*; (2) *oracle planning*—replace π_d with an oracle planner π_d* while keeping π_e (π_d* may adapt to execution feedback); (3) *oracle full stack*. The asymmetry between (1) and (2) follows from the time-scale separation: upper decisions are sparse and event-driven, so fixing their sequence does not over-constrain; lower actions are dense, so fixing them would erase the policy. The decomposition reads: **ΔE** = V(π_d, π_e) − V(π_d, π_e*) (execution bottleneck), **ΔP** = V(π_d, π_e) − V(π_d*, π_e) (planning bottleneck), **ΔI** = V(π_d*, π_e*) − V(π_d*, π_e) − V(π_d, π_e*) + V(π_d, π_e) (synergy).

**Validity guarantees.** Five pre-registered checks: (i) identical interface definitions across counterfactuals; (ii) deterministic dynamics with fixed seeds; (iii) replay consistency (own-trace replay reproduces original performance); (iv) monotonicity (qualitatively worse executors ⇒ larger ΔE); (v) oracle quality independently validated on single-domain subtasks. Section 6.3 reports an injected-bottleneck validation: we corrupt known components with graded faults and verify the method recovers the correct bottleneck label in 5/5 cases with strict dose-response monotonicity.

**Executor-effectiveness precheck.** One lesson promoted to a validity clause: attribution requires an executor that *responds* to goals. When the executor is at a performance floor (Section 6.2), planner differences are masked; we therefore gate attribution with an executor responsiveness test (goal-conditioned vs. monolithic SR gap) and report floor effects explicitly.

### 5.2 Coupling Estimators from Traces

C_info (cross-layer information asymmetry) and B_if (information flowing through the goal interface) are estimated from execution traces by k-NN Kraskov–Stögbauer–Grassberger (KSG) mutual information between goal streams and execution-state streams, with per-cell multi-seed variance reported. Manipulation checks (e.g., the independent < sequential < continuous C_info ordering) accompany every estimate; degenerate estimates (B_if ≈ 0 with nonzero variance) are flagged rather than silently consumed—an honesty requirement our Section 6.4 results justify.

---

## 6 CONCEPT VALIDATION ON THE GRID INSTANTIATION

We now validate the entire pipeline and pin down the layering law's boundary regime. *All numbers derive from released per-episode traces; every table is paired by seed.*

### 6.1 Setup

**Systems.** Pure RL: MAPPO (CTDE, goal-conditioned 11-dim conditioning, 3 seeds × 5M–20M steps per difficulty, curriculum + shaped variants on complex; 31 checkpoints frozen with a SHA256 environment manifest). Rule: scripted planner (confirmed-type filtering, nearest-interceptor assignment, sticky tracking). Pure LLM: LLM emits low-level actions directly. Hybrid: LLM planner (JSON goal plans, replan every 10 steps, safe-mode fallback) × three executor backends (MAPPO / heuristic GOAI / oracle). LLM backend: Qwen3.8-27B served on vLLM (temperature 0.1); complex-tier evaluation concurrency capped at 2 after load tests. Protocols: 20 paired episodes per system (seeds paired), bootstrap 95% CIs, Wilcoxon/sign tests.

### 6.2 RQ1 & RQ3: Paradigm Payoff and the Bottleneck

**Difficulty cliff—closed to end-to-end RL, open to orchestration.** Across the three tiers, pure MAPPO scores 100% / ≈97% / **0%** (3 seeds each; complex exhaustively trained: 20M steps, curriculum learning, penetration and draw shaping—all 0%), while the scripted rule planner scores 100% / 97% / **65%**. The complex tier's discriminative load (deception with indistinguishable numeric features, anomaly relabeling, jamming) is exactly where end-to-end small models collapse and orchestration survives—the empirical core of the benchmark's raison d'être.

**The 2×2 factorial isolates the executor floor.** On complex: every MAPPO-executor stack scores 0% (pure RL argmax 0%; rule+MAPPO 0%; LLM+MAPPO 0%, all losses by port penetration); with the heuristic GOAI executor, rule reaches 65% while LLM reaches 5%. The MAPPO executor is the *common* bottleneck across all learning stacks—goal-conditioning cannot rescue an execution policy that never saw successful defense trajectories.

**Tournament (round-robin, 3 difficulties × 5 episodes/pair, defender side).** Defender Elo: pure RL 1555 ≈ hybrid 1553 (67% win rate: simple/medium carry, complex collapses) > rule 1531 ≫ pure LLM 1331 > random 1302; the scripted attacker rates 1728. (Released grid traces predate the unified role standard and label the defender `blue` / the scripted attacker `red`; all numbers are unchanged.) **On the grid instantiation, hybridization yields no net advantage** (−2.7 Elo)—consistent across four independent evidence chains (2×2, coupling cells, intervention study, tournament). Per the layering law this is the expected *boundary* outcome, not a paradox: the grid tier violates D1′ (its difficulty is geometric interception, an LLM-weak decision form) and D2 (simple/medium saturated at V_m ≥ 0.95, complex floored the RL executor).

### 6.3 Attribution Method: Injected-Bottleneck Validation

We corrupt a reference hybrid with graded, known faults and ask the method to label the bottleneck (Table 3):

| Injected fault | Expected label | Recovered label | Dose-response |
|---|---|---|---|
| Planner noise (goal corruption) | planning | **planning** | ΔP = 0.54 |
| Executor degradation p=0.1 | execution | **execution** | ΔE = 0.14 |
| Executor degradation p=0.3 | execution | **execution** | ΔE = 0.34 |
| Executor degradation p=0.5 | execution | **execution** | ΔE = 0.53 |
| Balanced (both, mild) | balanced | **balanced** | ΔP ≈ ΔE = 0.07 |

*Table 3: 5/5 correct labels; ΔE strictly monotone in injected severity (0.14→0.34→0.53)—validity checks (iii)/(iv) pass.* The method is released as the benchmark's default diagnostic.

### 6.4 RQ2: The Layering Law's Boundary Regime

We manipulate task coupling (3 C_info tiers: independent/sequential/continuous engagement authorization) × interface granularity (3 B_if levels) on the medium tier where the executor responds to goals, 6 seeds × 9 cells, in two independent versions (LLM planner; rule planner to strip LLM noise). Pre-registered criteria (Spearman ρ(ΔV, e^{B_if}) > 0.7; ΔV CI containing 0 at B_if ≈ 0; exponential BIC; slope increasing in C_info) **fail in both versions** (ρ = 0.383 LLM / 0.117 rule). The failures are *informative*, decomposing into exactly the law's three terms:

- **Interface cost −c:** at B_if ≈ 0, ΔV is significantly negative (rule −0.19, LLM −0.39; CIs exclude 0)—the unconditional theory predicted ≈0.
- **Headroom:** at saturated monolithic baselines (V_m ≥ 0.99), layering only loses; the *single* positive cell (+0.16 rule / +0.04 LLM) sits in the only tier with V_m = 0.83.
- **Manipulation validity:** C_info estimates come out non-monotone (2.24 / 2.31 / 1.50) and granularity tiers produce a flat B_if profile (0.53/0.48/0.61)—instruction-template manipulations do not move the *environmental* information asymmetry, a construct-validity lesson now codified as D1/D3 gates.

**Net result:** ΔV = −c + f(C_info, B_if)·headroom(V_m) with f never exceeding c anywhere on the grid—the boundary regime of the law, delivered with the same traces that refuted the unconditional form.

### 6.5 Failure-Mode Anatomy: Three Interventions, One Structural Conclusion

If the LLM planner merely lacked information, injection should rescue it. We run a pre-registered intervention study on complex (20 paired episodes, four systems):

| System | SR | Contrast | ΔSR [95% CI] |
|---|---|---|---|
| rule + heuristic | 65% | — | — |
| rule_intel (geometric feint filter) | 60% | vs rule | −5 [−15, 0] |
| LLM + heuristic | 10% | — | — |
| **LLM + exclusive intel** | **5%** | vs LLM | **−5 [−20, +10]** |
| | | vs rule | **−60 [−85, −30]** |

The informed planner receives (i) rendered heading kinematics for every contact (closing the stock prompt's rendering gap) and (ii) a six-point exclusive intel brief (feint behavior, own-goal rule, anomaly relabeling, jamming guidance). Planner traces show the LLM *reads and cites* the intelligence (scout non-engagement, jamming-tolerant locks, standoff requirements)—the information channel works—yet performance does not move. Failure tracing locates the deficit in **semantic-to-geometric decision conversion**: recurring all-in commitments (both USVs to one target; all units patrolling one point), i.e., resource-bandwidth mismanagement under spatial-combinatorial load, plus reliability friction (9% empty responses on max-token exhaustion). Combined with the frequency intervention (replanning 10→5 steps: 5% → 5%) and the interface intervention (Section 6.6), all three channels—information, frequency, interface—fail to close the gap. **Conclusion (H1b evidence):** on geometrically-shaped tasks the hybrid failure is structural; we formalize the missing property as **decision-form match (D1′)** and predict the high-fidelity suite's combinatorial scheduling core (4-domain, 7-platform resource allocation) sits on the LLM-favorable side.

### 6.6 Interface Modality: A Load-Matched Double-Edged Sword

Natural-language vs. JSON state rendering for the same scenarios (paired seeds):

| Tier (n) | NL SR | JSON SR | Δ(NL−JSON) | sign test |
|---|---|---|---|---|
| simple (15) | 93% | 87% | +7% | p = 0.50 |
| medium (45) | 69% | 84% | **−16%** | p = 0.98 |
| complex (45) | 11% | 7% | +4.4% | p = 0.34 |

JSON wins where semantic load is low (structured dumps parse more reliably); NL trends back at high load while JSON accrues parse failures (9 in 45). Interface choice is load-matched, not universal—and never rescues an overmatched planner (7–11% vs. rule's 65% on complex).

### 6.7 From Boundary Conditions to the High-Fidelity Design

The grid results convert directly into pre-registered acceptance gates for the full high-fidelity instantiation (in development; pilot-first): **D1** information asymmetry (rule discriminator ≤60%, LLM ≥85% on feint-vs-real), **D1′** decision-form match (greedy-script < 90% of rule baseline), **D2** headroom (best pure baseline SR ∈ [40%, 85%]), **D3** interface budget (B_if tier gradients exceeding estimator variance; finest tier B_if ≥ 0.3), plus engineering gates (empty-response ≤5%, JSON parse-error ≤5%). The pilot (3–4 scenarios × 2×2 anchor calibration) validates all gates before any training-matrix or tournament commitment—the same cheap-first discipline this section exemplifies.

---

## 7 DISCUSSION

### 7.1 Insights

**I1 — Layering is conditional, and the conditions are measurable.** Hybrid advantage is neither universal nor mysterious: it requires information the execution layer cannot see, an interface cheap enough to carry it, and headroom in the monolithic baseline. The grid instantiation sits at the law's boundary (f ≤ c everywhere); the high-fidelity suite is explicitly designed to sit inside the positive region—falsifiably so, via the D-gates.

**I2 — The bottleneck is executor-shaped, and single metrics hide it.** The 2×2 factorial shows one weak executor floors every planner stacked above it (0% across MAPPO backends), while the same planners under a heuristic executor separate cleanly (65% vs. 5%). End-to-end rankings would have conflated these; attribution + factorial design disentangles them.

**I3 — LLM failure on the grid is a decision-form mismatch, not an information deficit.** All three rescue channels (exclusive intel, faster replanning, modality switch) fail; planner traces show the intelligence is read and cited. This reframes "LLMs cannot do multi-agent control" into a sharper, actionable claim: they cannot yet convert semantic situational understanding into spatial-combinational resource scheduling under adversarial timing—and environments seeking to credit LLM deliberation must place task difficulty in decision forms LLMs are strong at.

**I4 — Benchmarks should ship their falsification criteria.** Pre-registered hypotheses, paired statistics, released traces, and manipulation-validity checks made our own theory's refutation *productive* (the conditional law replaced the unconditional one). We propose this as standard practice for evaluation-benchmark papers.

### 7.2 Limitations and Threats to Validity

**Grid instantiation scope.** The concept-validation substrate is deliberately minimal-geometry; its boundary-regime results do not estimate the law's positive region—that is the high-fidelity suite's job, whose gates D1–D3 are pre-registered precisely because the grid refuted our unconditional priors. We claim external validity only through the (now falsifiable) design theory, not the grid numbers.

**Single LLM backend.** All LLM results use one 27B open model (deployment reproducibility); planner-side generality (frontier APIs) is untested, though the rule-planner replication of the coupling results isolates architecture-level from model-level effects.

**Estimator variance.** KSG mutual-information estimates at 6 seeds show degenerate cells; we flag rather than hide them (Section 5.2), and D3 requires gradients exceeding estimator variance.

**Trust model.** Distributed evaluation cannot verify claimed architectures; rate limiting and action-pattern integrity checks bound but do not eliminate gaming—the openness/control trade-off is deliberate.

**High-fidelity status.** The full physics suite and 15-system matrix are in development under the pilot-gate protocol; this paper reports the validated pipeline, methods, and boundary-regime evidence.

### 7.3 Future Work

Completing the high-fidelity instantiation under the D-gates (pilot results expected next); extending attribution to ΔI-strong regimes (LLM executors); distributional replay for stochastic planners; community baseline expansion via the open protocol.

---

## 8 CONCLUSION

Driven by the requirements of multi-domain adversarial operations—not by architectural fashion—OpenMDBench formalizes decision-stack bifurcation (HSemi-MDP), derives a measurable coupling theory, and distills the conditional layering law ΔV = −c + f(C_info, B_if)·headroom(V_m). The platform removes the frictions that exclude hybrid LLM-small-model systems from every existing benchmark, and its diagnostic toolbox (counterfactual-replay attribution, trace-based coupling estimators) converts evaluation from ranking into causal analysis. Concept-validation experiments validate every method (attribution 5/5 with dose-response monotonicity), refute our own unconditional coupling hypothesis, and replace it with the conditional law whose boundary regime the grid instantiation exhaustively maps—including the structural, intervention-robust failure mode of LLM planners on geometrically-shaped tasks and its remedy-by-design (decision-form match). The high-fidelity instantiation proceeds under pre-registered acceptance gates derived from exactly these findings. We release all environments, traces, and analysis code to anchor reproducible, diagnostic benchmarking for hybrid multi-agent intelligence.

---

## REFERENCES

[1] M. Samvelyan, T. Rashid, C. Schroeder de Witt, G. Farquhar, N. Nardelli, T. G. J. Rudner, C.-M. Hung, P. H. S. Torr, J. Foerster, and S. Whiteson. The StarCraft Multi-Agent Challenge. In *AAMAS*, 2019.

[2] J. Chen, Y. Liu, X. Chen, et al. LLMArena: Evaluating Large Language Models in Dynamic Multi-Agent Environments. In *ACL*, 2024.

[3] B. Ellis, M. Samvelyan, R. Faulkner, et al. SMACv2. In *NeurIPS*, 2023.

[4] J. He, Y. Wang, Z. Liu, et al. HeMAC: A Heterogeneous Multi-Agent Challenge Benchmark. *arXiv*, 2024.

[5] X. Zhang, M. Li, Y. Chen, et al. LSHC: A Large-Scale Heterogeneous Multi-Agent Cooperation Benchmark. *arXiv*, 2024.

[6] H. Wang, J. Zhang, S. Li, et al. POAC. *arXiv*, 2024.

[7] T. Nguyen, R. Guo, A. Plumptre, et al. APE: Anti-Poaching Environment for MARL. In *AAMAS*, 2023.

[8] M. Dominici, L. Bisi, L. Sabbatini, et al. HIVEX. In *ICLR*, 2025.

[9] Anonymous. BattleAgentBench. *arXiv*, 2024.

[10] Y. Zhou, J. Wu, Z. Lin, et al. MindAgent. In *ICLR*, 2024.

[11] Y. Fu, H. Peng, T. Zhang, et al. Decrypto. In *ICLR*, 2025.

[12] W. Zhang, X. Liu, Y. Li, et al. SPIN-Bench. *arXiv*, 2024.

[13] Y. Hu, W. Li, Z. Zhang, et al. HIVE. *arXiv*, 2024.

[14] X. Wang, Y. Zhang, L. Chen, et al. LAMARL. *arXiv*, 2024.

[15] S. Li, H. Wang, J. Zhao, et al. LGC-MARL. *arXiv*, 2024.

[16] Y. Duan, Z. Liu, Q. Zhang, et al. LERO. *arXiv*, 2024.

[17] A. Nair, P. Srinivasan, S. Blackwell, et al. Massively Parallel Methods for Deep RL. *arXiv:1507.04296*, 2015.

[18] L. Espeholt, H. Soyer, R. Munos, et al. IMPALA. In *ICML*, 2018.

[19] X. Wang, Z. Xiong, C. Xu, et al. Federated RL: A Survey. *IEEE TNNLS*, 2023.

[20] J. Z. Leibo, E. Dueñez-Guzmán, J. P. Agapiou, et al. Melting Pot 2.0. *arXiv:2107.06857*, 2021.

[21] J. Terry, B. Black, N. Grammel, et al. PettingZoo. In *NeurIPS*, 2021.

[22] M. Bou, P. D'Oro, S. Kar, et al. BenchMARL. In *ICML*, 2023.

[23] S. Hu, Y. Zhong, O. Min, et al. MARLLib. In *ICML*, 2022.

[24] N. Shapira, N. Azran, G. Stanovsky, et al. Theory of Mind for Multi-Agent Collaboration. In *ACL*, 2023.

[25] Y. Liu, S. Wang, J. Zhang, et al. FEDAGENT. In *AAAI Workshop*, 2024.

[26] V. Mnih, A. P. Badia, M. Mirza, et al. Asynchronous Methods for Deep RL. In *ICML*, 2016.

[27] T. Yu, G. Kumar, A. Gupta, et al. Multi-Agent Mujoco. *arXiv:2206.07296*, 2022.

[28] C. Resnick, W. Eldridge, D. Ha, et al. Pommerman. *arXiv:1809.07124*, 2018.

[29] I. Mordatch and P. Abbeel. Emergence of Grounded Compositional Language. *arXiv:1703.04908*, 2017.

[30] Y. Liang, C. Song, X. Liu, et al. Reflective Multi-Agent Collaboration with LLMs. *arXiv*, 2024.

---

## SUBMISSION DESIGN NOTES (not part of the paper — internal, 0830)

**Venue fit & track.** AAMAS main-track area: *Benchmarks, Challenges and Resources*（或 "Multi-Agent Systems → Evaluation"）。定位语已在 Abstract/Intro 强化："diagnostic benchmark + falsifiable design theory"。若审稿周期不利，备选 track：Core Technical（作为 evaluation methodology 论文）。

**Page budget (8 pp + 2 pp refs, AAMAS 两栏).**
| 节 | 预算 |
|---|---|
| Abstract+Intro | 1.2 pp |
| Related | 0.5 pp |
| §3 形式化+定律 | 1.3 pp |
| §4 平台 | 1.0 pp（细节移附录 A-C/G） |
| §5 方法 | 0.8 pp |
| §6 实验 | 2.7 pp |
| §7-8 | 0.5 pp |

**Float plan（5 个，全部自包含）.** Fig.1 架构图（沿用）；Fig.2 场景示意（沿用）；Table 2 = 难度断层+2×2 合并表（§6.2，正文已并述）；Table 3 = A10 归因验证（已成表）；Fig.4 = 耦合定律散点（ΔV vs B_if，按 V_m headroom 分色，9 格×两版 18 点——从 `coupling_experiment_medium.json` 直接生成）；Table 4 = grid-info 四系统 CI 表（已成表）；Table 5 = A3 三难度（已成表，可缩为单行文字省 0.2pp 时优先删）。Elo 数据文字化（§6.2 已处理）。

**AAMAS 审稿风险与预置防线.**
1. *"Grid 上 hybrid 全败，凭什么信高保真？"* → §3.3 D-gates 预注册 + §6.5 决策形态论证 + §7.2 第一条 limitation 正面承认外部 validity 走设计理论而非 grid 数字。防线已内置，审稿人问到的每个位置都有答案。
2. *"负结果论文？"* → 包装为 refuted-then-refined law（C1 措辞已定："refute the unconditional form and replace it with the conditional law"），符合 AAMAS 对 characterization 工作的接受习惯。
3. *"单 LLM 后端"* → rule-planner 复刻实验隔离架构效应 vs 模型效应（§7.2 已述）。
4. *"基准没跑满 15 系统"* → 概念验证定位 + pilot-gate 时间表（§6.7）；投稿时若高保真 pilot 已出，将 pilot 锚点表升为 Table 6。
5. 匿名：正文无自引暴露；artifact evaluation 提交 traces + 环境 manifest（SHA256 冻结已做）——AAMAS reproducibility 奖的完整材料链。

**LaTeX 化前待办.** Fig.4 生成脚本（json→pgfplots）；Table 2 合并排版；§4.2 grid 规格段压缩（Appendix H 承接）；关键词与 AAMAS tracks 对齐复查。

**附录沿用**：OpenMDBench.md 的 A-H 附录（本版先不考虑，LaTeX 阶段搬运）。
