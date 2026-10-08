"""可复制的 MD-AD-002 V2 双方对抗规则智能体。

示例只使用公开 V2 Session、只读 WorldView 和 ActionBatch DTO。场景编译、实体
spawn、动力学与任务裁决都由通用 V2 管线负责；策略代码不进入场景包，也不被核心
运行时导入。
"""

from __future__ import annotations

import argparse

from openmdbench.policies.rule_v2 import FormalRuleAgentTeamV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2


def run(public_id: str = "MD-AD-002-EASY", *, seed: int = 7, ticks: int = 60) -> None:
    """运行数据配置的突防与防空策略；所有动作经过 V2 Session。"""

    session = create_formal_session_v2(public_id, session_id="example.md-ad-002", seed=seed)
    agents = FormalRuleAgentTeamV2.for_scenario(public_id, seed=seed)
    session.load().start()
    try:
        for index in range(ticks):
            tick = session.world_view.tick
            agents(session)
            receipt = session.step(operation_id=f"tick.{index}", expected_tick=tick)
            decision = agents.last_decision
            if decision is None:
                raise RuntimeError("rule agent did not publish a decision")
            mission = session.world_view.checkpoint().mission_scoring_checkpoint
            print(
                {
                    "tick": receipt.tick,
                    "attack_commands": len(decision.attack_command_ids),
                    "defence_commands": len(decision.defence_command_ids),
                    "fires": decision.fire_action_ids,
                    "result": None if mission is None else mission.get("terminal_result"),
                }
            )
    finally:
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"),
        default="MD-AD-002-EASY",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--ticks", type=int, default=60)
    arguments = parser.parse_args()
    run(arguments.scenario, seed=arguments.seed, ticks=arguments.ticks)
