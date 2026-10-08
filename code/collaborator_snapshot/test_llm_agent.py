"""Quick test: Pure LLM agent with real Qwen3.5 API."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# LLM config: read from the environment (see code/.env.example).
# Never hardcode credentials here - this file is tracked by git.
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:8000/v1")
os.environ.setdefault("OPENAI_API_KEY", "EMPTY")
os.environ.setdefault("LLM_DEFAULT_MODEL", "Qwen3.5-122B-A10B-FP8")

from grid_env.grid_env import GridEnv
from grid_env.agents.pure_llm_agent import PureLLMAgent

env = GridEnv(difficulty="simple", seed=42)
obs = env._get_observation()

agent = PureLLMAgent(role="blue", seed=42)
print(f"LLM model: {agent.llm.model}")
print(f"LLM base_url: {agent.llm.base_url}")
print("Calling Qwen3.5-122B for action decision...")

actions = agent.act(obs, env=env)
print(f"\nActions: {actions}")
print(f"LLM calls: {agent.call_count}")
print(f"Fallbacks: {agent.fallback_count}")
print(f"LLM stats: {agent.llm.get_stats()}")
