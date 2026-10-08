"""End-to-end test for the evaluation framework."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation import CentralSimulationServer, ULHAClient, MetricEngine, EloSystem
from grid_env.agents.rule_agent import RuleAgent
from grid_env.agents.hybrid_agent import HybridAgent

print("=== Test 1: CSS + ULHA single session ===")
css = CentralSimulationServer(output_dir="eval_test_output")

client = ULHAClient(
    css=css, agent_name="rule_v1",
    scenario_id="grid_simple", difficulty="simple", role="blue", seed=42,
)

obs = client.reset()
print(f"Session started: {client.session_id}")
print(f"Briefing: {obs['mission_briefing'][:50]}...")

agent = RuleAgent(role="blue", seed=42)
env = client.get_env()

for step in range(150):
    actions = agent.act(obs, env=env)
    result = client.submit_actions(actions)
    obs = result["observation"]
    if result["done"]:
        break

final = client.close()
print(f"\nFinal result:")
print(f"  Winner: {final['winner']}")
print(f"  Composite: {final['composite_score']:.4f}")
print(f"  Planning:  {final['planning_score']:.4f}")
print(f"  Execution: {final['execution_score']:.4f}")
print(f"  Steps: {final['steps']}")
print(f"  Details: {json.dumps(final['metric_details'], indent=4)}")

print("\n=== Test 2: Trajectory recording ===")
traj_path = css.save_trajectories("test_traj.json")
print(f"Saved to: {traj_path}")
with open(traj_path) as f:
    traj = json.load(f)
print(f"  Episodes: {traj['num_episodes']}")
print(f"  Timesteps: {traj['episodes'][0]['length']}")
ts0 = traj["episodes"][0]["timesteps"][0]
print(f"  Step 0 keys: {list(ts0.keys())}")

print("\n=== Test 3: Elo rating ===")
elo = EloSystem()
elo.register("rule_v1")
elo.register("hybrid_v1")
elo.update("rule_v1", "hybrid_v1", 0.8)
r1 = elo.get_rating("rule_v1")
r2 = elo.get_rating("hybrid_v1")
print(f"  rule_v1:   blue={r1['blue']:.1f}, red={r1['red']:.1f}")
print(f"  hybrid_v1: blue={r2['blue']:.1f}, red={r2['red']:.1f}")

print("\n=== Test 4: Metric engine ===")
engine = MetricEngine()
sample_metrics = {
    "mission_success": True, "steps": 80, "blue_score": 0.8,
    "red_intercepted": 2, "red_detected": 2, "red_combatants_total": 2,
    "rule_violation_rate": 0.0, "civilian_encounters": 1,
    "civilian_intercepted": 0, "ammo_used": 3,
    "adaptation_latencies": [], "instruction_switches": 0,
    "port_penetrations": 0, "blue_units_lost": 0,
}
mr = engine.compute(sample_metrics)
print(f"  Planning:  {mr.planning_score:.4f}")
print(f"  Execution: {mr.execution_score:.4f}")
print(f"  Composite: {mr.composite_score:.4f}")
print(f"  All metrics: {json.dumps(mr.details, indent=4)}")

print("\n=== ALL TESTS PASSED ===")
