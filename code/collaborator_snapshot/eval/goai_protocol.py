"""GOAI 目标协议（V2 迁移版）—— 从 grid_env/goai.py 移植，去掉全部 grid 环境依赖。

协议语义与原版一致（paper §3.2.1 / Appendix I）：
- Goal Command (I.1): task_id / goal_type(7) / parameters / priority / constraints / deadline
- Status Report (I.2): task_id / status(6) / progress / eta / anomaly(8) / confidence / reported_at
- 状态机 (I.3): pending → executing → completed | failed | infeasible | timeout
- 协商：不可行目标不允许原样重发；broker 拒绝同签名重提交
- 安全模式 (I.5): T_DECISION_MAX 步内无新目标 → 执行层原地待命并停火，上报 comm_loss

本模块是纯协议层：不 import openmdbench，任何 planner/executor 组合都通过它交换。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 协议常量（Appendix I.4；V2 中 1 tick ≈ 1 仿真秒，语义同 grid 的 1 step）
# ---------------------------------------------------------------------------

T_DECISION_MAX = 30      # 无新目标进入安全模式的步数阈值
T_STATUS_PERIOD = 5      # 周期性状态上报间隔（tick）
T_COMM_TIMEOUT = 15      # 通信丢失判定阈值（tick）
T_OBS_STALE = 2          # 观测最大可接受年龄（tick）
N_MAX_GOALS = 8          # 单平台最大并发目标数
PRIORITY_EPSILON = 0.01  # 抢占所需的最小优先级差

GOAL_TYPES = (
    # 基础 7 型（原论文 Appendix I.1 口径，保持不变）
    "waypoint", "patrol", "track", "intercept", "hold", "return", "loiter",
    # 扩展战术原语（B 线新增，下层直接支持，规则组/LLM 组共用）
    "barrier",   # 屏障：在保护区外侧按方位扇面布防并扫掠（parameters: axis_deg, radius_m, arc_deg）
    "ambush",    # 伏击：按目标速度推算的提前交点占位，等目标进杀伤区（target_id, standoff_m）
    "reserve",   # 预备：驻留后方锚点，威胁进入 commit_within_m 时自动前出接战（position, commit_within_m）
    "disengage",  # 脱离：脱离当前任务返回锚点（position 可选）
)
STATUS_STATES = ("pending", "executing", "completed", "failed", "infeasible", "timeout")
ANOMALY_TYPES = (
    "none", "fuel_low", "obstacle_blocked", "sensor_degraded",
    "comm_loss", "target_lost", "platform_damaged", "constraint_violation",
)

TASK_ID_PATTERN = re.compile(r"^[a-z_]+_[0-9]{3}$")


# ---------------------------------------------------------------------------
# 消息
# ---------------------------------------------------------------------------

@dataclass
class GoalCommand:
    """上层→下层目标命令（Appendix I.1）。

    parameters 常用键：
    - unit_id: 执行该目标的己方实体 id
    - position: [x, y] 或 [x, y, z]，米制（V2 为连续坐标）
    - target_id: 接触/目标 contact_id
    - speed_mps: 期望巡航速度（可选）
    - duration: hold 持续时间（tick）
    """

    task_id: str
    goal_type: str
    parameters: dict = field(default_factory=dict)
    priority: float = 0.5
    constraints: List[dict] = field(default_factory=list)  # {type, value}
    deadline: Optional[float] = None  # 自下发起的 tick 数
    issued_at: int = 0                # 由 broker 自动填写

    def __post_init__(self):
        # 归一化 position：LLM 可能输出 "(x, y)" / "x, y" 字符串或 list
        pos = (self.parameters or {}).get("position")
        if pos is not None and not isinstance(pos, (list, tuple)):
            nums = re.findall(r"-?\d+(?:\.\d+)?", str(pos))
            if len(nums) >= 2:
                values = [float(nums[0]), float(nums[1])]
                if len(nums) >= 3:
                    values.append(float(nums[2]))
                self.parameters["position"] = values
        elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
            try:
                self.parameters["position"] = [float(pos[0]), float(pos[1]), float(pos[2])] \
                    if len(pos) >= 3 else [float(pos[0]), float(pos[1])]
            except (TypeError, ValueError):
                self.parameters.pop("position", None)

    @property
    def unit_id(self) -> Optional[str]:
        return self.parameters.get("unit_id")

    def constraint(self, ctype: str) -> Optional[object]:
        for c in self.constraints:
            if c.get("type") == ctype:
                return c.get("value")
        return None

    def to_granularity(self, level: str) -> "GoalCommand":
        """目标粒度三档裁剪（对应 interface_requirements.md §2.2 / B_if 归因操纵）。

        - weak: 仅保留 unit_id (goal_type 隐含或保留最小参数)
        - medium: unit_id + target_id
        - strong: 完整参数 (含 position, speed, pattern, constraints 等)
        """
        lvl = str(level).lower()
        if lvl == "weak":
            params = {"unit_id": self.unit_id} if self.unit_id else {}
            return GoalCommand(
                task_id=self.task_id, goal_type=self.goal_type,
                parameters=params, priority=self.priority,
                deadline=self.deadline, issued_at=self.issued_at
            )
        elif lvl == "medium":
            params = {}
            if self.unit_id:
                params["unit_id"] = self.unit_id
            if "target_id" in self.parameters:
                params["target_id"] = self.parameters["target_id"]
            return GoalCommand(
                task_id=self.task_id, goal_type=self.goal_type,
                parameters=params, priority=self.priority,
                deadline=self.deadline, issued_at=self.issued_at
            )
        return self

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "goal_type": self.goal_type,
            "parameters": self.parameters,
            "priority": self.priority,
            "constraints": self.constraints,
            "deadline": self.deadline,
            "issued_at": self.issued_at,
        }

    @staticmethod
    def from_dict(d: dict) -> "GoalCommand":
        return GoalCommand(
            task_id=str(d.get("task_id", "goal_000")),
            goal_type=str(d.get("goal_type", "hold")),
            parameters=dict(d.get("parameters") or {}),
            priority=float(d.get("priority", 0.5)),
            constraints=list(d.get("constraints") or []),
            deadline=(float(d["deadline"]) if d.get("deadline") is not None else None),
        )


@dataclass
class StatusReport:
    """下层→上层状态报告（Appendix I.2）。"""

    task_id: str
    status: str          # one of STATUS_STATES
    progress: float      # [0, 1]
    eta: Optional[float] = None
    anomaly: str = "none"
    anomaly_detail: str = ""
    confidence: float = 1.0
    reported_at: int = 0
    unit_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "unit_id": self.unit_id,
            "status": self.status,
            "progress": round(self.progress, 3),
            "eta": self.eta,
            "anomaly": self.anomaly,
            "anomaly_detail": self.anomaly_detail,
            "confidence": self.confidence,
            "reported_at": self.reported_at,
        }


# ---------------------------------------------------------------------------
# 单目标执行状态（Appendix I.3）
# ---------------------------------------------------------------------------

@dataclass
class GoalExecutionState:
    command: GoalCommand
    status: str = "pending"
    start_tick: Optional[int] = None
    last_progress: float = 0.0
    initial_dist: Optional[float] = None
    hold_until: Optional[int] = None
    loiter_phase: int = 0

    @property
    def terminal(self) -> bool:
        return self.status in (
            "completed", "failed", "infeasible", "timeout", "superseded",
        )


# ---------------------------------------------------------------------------
# Broker —— 上下层消息总线 + 不可行协商
# ---------------------------------------------------------------------------

def _goal_signature(cmd: GoalCommand) -> Tuple:
    params = cmd.parameters
    pos = params.get("position")
    if isinstance(pos, (list, tuple)):
        pos = tuple(float(v) for v in pos)
    key_params = (params.get("unit_id"), pos, params.get("target_id"),
                  params.get("pattern"))
    return (cmd.goal_type,) + key_params


class GOAIBroker:
    """进程内消息总线：规划层提交目标，执行层上报状态。

    - submit_goals(): 不可行目标的同签名重发被拒绝（协商规则 §3.2.1）；
      每个规划周期提交的是该单位的完整目标集，未出现的旧目标被 supersede。
    """

    def __init__(self):
        self.active: Dict[str, GoalExecutionState] = {}
        self.reports: List[StatusReport] = []
        self.infeasible_signatures: Dict[Tuple, str] = {}
        self.stats = {"goals_accepted": 0, "goals_rejected": 0}

    def submit_goals(self, commands: List[GoalCommand], step: int,
                     per_unit_limit: int = N_MAX_GOALS) -> dict:
        accepted, rejected = [], []
        resub_units = {c.unit_id for c in commands
                       if c.unit_id is not None and c.goal_type in GOAL_TYPES}
        for tid, s in list(self.active.items()):
            if (not s.terminal and s.command.unit_id in resub_units
                    and tid not in {c.task_id for c in commands}):
                s.status = "superseded"

        for cmd in commands:
            if cmd.goal_type not in GOAL_TYPES:
                rejected.append({"task_id": cmd.task_id,
                                 "reason": f"invalid goal_type {cmd.goal_type!r}"})
                continue
            sig = _goal_signature(cmd)
            if sig in self.infeasible_signatures:
                rejected.append({
                    "task_id": cmd.task_id,
                    "reason": ("negotiation_violation: goal identical to "
                               f"infeasible {self.infeasible_signatures[sig]}; "
                               "modify parameters before reissuing"),
                })
                continue
            unit = cmd.unit_id
            n_unit = sum(1 for s in self.active.values()
                         if not s.terminal and s.command.unit_id == unit)
            if unit is not None and n_unit >= per_unit_limit:
                rejected.append({"task_id": cmd.task_id,
                                 "reason": f"unit {unit} at N_max_goals={per_unit_limit}"})
                continue
            cmd.issued_at = step
            self.active[cmd.task_id] = GoalExecutionState(command=cmd)
            accepted.append(cmd.task_id)
        self.stats["goals_accepted"] += len(accepted)
        self.stats["goals_rejected"] += len(rejected)
        return {"accepted": accepted, "rejected": rejected}

    def post_report(self, report: StatusReport):
        self.reports.append(report)
        state = self.active.get(report.task_id)
        if state is not None:
            state.status = report.status
            state.last_progress = report.progress
            if report.status == "infeasible":
                self.infeasible_signatures[
                    _goal_signature(state.command)] = report.task_id

    def poll_reports(self) -> List[StatusReport]:
        out, self.reports = self.reports, []
        return out

    def prune_terminal(self):
        self.active = {tid: s for tid, s in self.active.items() if not s.terminal}

