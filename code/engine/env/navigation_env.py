import numpy as np
import taichi as ti
import taichi.math as tm
import torch
from env.calibrated_vessels import kvlcc2_l64
from env.simulator import Sim2Sea
from gymnasium import spaces
from openmdbench.core.rng import SessionRNG
from openmdbench.domains.surface.actions import (
    heading_to_rudder,
    validate_action_tensor_shape,
    validate_kinematic_actions,
    validate_mmg_actions,
)


@ti.data_oriented
class MaritimeNavigationEnv(Sim2Sea):
    def __init__(self, args):
        if args.max_num != 1 or getattr(args, "controlled_entities_per_env", 1) != 1:
            raise ValueError("Phase 0 supports exactly one controlled USV per environment")
        super().__init__(args)

        self.load_vessel_params(kvlcc2_l64)
        self.args = args
        self.session_rng = SessionRNG(getattr(args, "seed", 0))

        self.max_episode_steps = args.max_episode_steps
        self.ship_radius = args.ship_radius
        self.max_speed = args.max_speed
        self.max_angular_velocity = args.max_angular_velocity
        self.use_mask = args.use_mask

        if self.use_bev:
            self.setup_bev(bev_size=args.bev_size, bev_R=args.bev_R)
            # self.use_bev = True

        self.action_space = spaces.Box(
            low=np.array([0.0, -0.3]), high=np.array([5.0, 0.3]), dtype=np.float32
        )

        self.observation_space = spaces.Dict(
            {
                "bev_map": spaces.Box(
                    low=0, high=256, shape=(args.bev_size, args.bev_size, 3), dtype=np.float32
                ),
                "ship_state": spaces.Box(low=-np.inf, high=np.inf, shape=(8,), dtype=np.float32),
                "goal_info": spaces.Box(low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32),
                "potential_gradient": spaces.Box(low=-1, high=1, shape=(2,), dtype=np.float32),
            }
        )

        self.setup_obstacle_fields()

        # 加载真实地图数据（线段障碍物为全局共享，所有并行环境共用）
        if hasattr(args, "use_real_map") and args.use_real_map:
            from env.map_loader import apply_coordinate_offset, load_map

            map_files = args.map_files if hasattr(args, "map_files") else ["weihai_map.txt"]
            map_data_dir = args.map_data_dir if hasattr(args, "map_data_dir") else "env/map_data"
            combined_polygons = load_map(map_data_dir, map_files)
            offset_polygons, self.map_offset_x, self.map_offset_y = apply_coordinate_offset(
                combined_polygons
            )
            # 直接调用 setup_line_obstacles（绕过有格式 bug 的 setup_line_obstacles_taichi）
            # setup_line_obstacles 内部自动调用 setup_ao_grid_gpu + init_obstacle_grid
            self.setup_line_obstacles(offset_polygons)

        self.setup_task_fields()

        self.setup_reward_fields()

        self.register_features()

        self.register_pairs()

        self.setup_rvo_dynamic_field(rvo_d0=args.rvo_d0)

    def setup_obstacle_fields(self):
        self.max_moving_obstacles = 5
        self.max_waypoints_per_obstacle = 8

        self.moving_obstacle_pos = ti.Vector.field(
            2, dtype=self.ctype, shape=(self.max_env, self.max_moving_obstacles)
        )
        self.moving_obstacle_vel = ti.Vector.field(
            2, dtype=self.ctype, shape=(self.max_env, self.max_moving_obstacles)
        )
        self.moving_obstacle_radius = ti.field(
            dtype=self.ctype, shape=(self.max_env, self.max_moving_obstacles)
        )
        self.moving_obstacle_speed = ti.field(
            dtype=self.ctype, shape=(self.max_env, self.max_moving_obstacles)
        )
        self.moving_obstacle_waypoints = ti.Vector.field(
            2,
            dtype=self.ctype,
            shape=(self.max_env, self.max_moving_obstacles, self.max_waypoints_per_obstacle),
        )
        self.moving_obstacle_waypoint_count = ti.field(
            dtype=ti.i32, shape=(self.max_env, self.max_moving_obstacles)
        )
        self.moving_obstacle_current_waypoint = ti.field(
            dtype=ti.i32, shape=(self.max_env, self.max_moving_obstacles)
        )
        self.moving_obstacle_active = ti.field(
            dtype=ti.i32, shape=(self.max_env, self.max_moving_obstacles)
        )

        self.max_static_obstacles = 8
        self.static_obstacle_pos = ti.Vector.field(
            2, dtype=self.ctype, shape=(self.max_env, self.max_static_obstacles)
        )
        self.static_obstacle_radius = ti.field(
            dtype=self.ctype, shape=(self.max_env, self.max_static_obstacles)
        )
        self.static_obstacle_active = ti.field(
            dtype=ti.i32, shape=(self.max_env, self.max_static_obstacles)
        )

    def setup_task_fields(self):
        self.goal_pos = ti.Vector.field(2, dtype=self.ctype, shape=(self.max_env, self.max_num))

        self.step_count = ti.field(dtype=ti.i32, shape=(self.max_env, self.max_num))
        self.previous_distance_to_goal = ti.field(
            dtype=self.ctype, shape=(self.max_env, self.max_num)
        )

        # 轨迹记录
        self.max_trajectory_length = 2000
        self.trajectory_pos = ti.Vector.field(
            2, dtype=self.ctype, shape=(self.max_env, self.max_num, self.max_trajectory_length)
        )
        self.trajectory_length = ti.field(dtype=ti.i32, shape=(self.max_env, self.max_num))

    def setup_reward_fields(self):
        self.collision_detected = ti.field(dtype=ti.i32, shape=(self.max_env, self.max_num))

        self.potential_gradient = ti.Vector.field(
            2, dtype=self.ctype, shape=(self.max_env, self.max_num)
        )

        self.path_smoothness = ti.field(dtype=self.ctype, shape=(self.max_env, self.max_num))

    @ti.kernel
    def init_obstacles_scenario(self, scenario_type: ti.i32):

        self.moving_obstacle_active.fill(0)
        self.static_obstacle_active.fill(0)
        for env_id in range(self.max_env):
            # self.moving_obstacle_active[env_id, :] = 0
            # self.static_obstacle_active[env_id, :] = 0

            if scenario_type == 0:
                self._init_simple_scenario(env_id)
            elif scenario_type == 1:
                self._init_medium_scenario(env_id)
            elif scenario_type == 2:
                self._init_complex_scenario(env_id)

    @ti.func
    def _init_simple_scenario(self, env_id: ti.i32):
        for i in range(3):
            self.static_obstacle_active[env_id, i] = 1
            self.static_obstacle_pos[env_id, i] = ti.Vector(
                [200.0 + i * 300.0 + ti.random() * 100.0, 200.0 + ti.random() * 600.0]
            )
            self.static_obstacle_radius[env_id, i] = 10.0 + ti.random() * 20.0

        self.moving_obstacle_active[env_id, 0] = 1
        self.moving_obstacle_pos[env_id, 0] = ti.Vector([400.0, 300.0])
        self.moving_obstacle_radius[env_id, 0] = 25.0
        self.moving_obstacle_speed[env_id, 0] = 10.0
        self.moving_obstacle_waypoint_count[env_id, 0] = 4
        self.moving_obstacle_current_waypoint[env_id, 0] = 0

        self.moving_obstacle_waypoints[env_id, 0, 0] = ti.Vector([400.0, 300.0])
        self.moving_obstacle_waypoints[env_id, 0, 1] = ti.Vector([600.0, 300.0])
        self.moving_obstacle_waypoints[env_id, 0, 2] = ti.Vector([600.0, 500.0])
        self.moving_obstacle_waypoints[env_id, 0, 3] = ti.Vector([400.0, 500.0])

    @ti.func
    def _init_medium_scenario(self, env_id: ti.i32):
        for i in range(3):
            self.static_obstacle_active[env_id, i] = 1
            self.static_obstacle_pos[env_id, i] = ti.Vector(
                [550.0 + i * 300.0 + ti.random() * 50.0, 200.0 + ti.random() * 50.0]
            )
            self.static_obstacle_radius[env_id, i] = 10.0 + ti.random() * 5.0

        for i in range(2):
            self.moving_obstacle_active[env_id, i] = 1
            self.moving_obstacle_pos[env_id, i] = ti.Vector([200.0 + i * 250.0, 200.0 + i * 100.0])
            self.moving_obstacle_radius[env_id, i] = 20.0 + ti.random() * 5.0
            self.moving_obstacle_speed[env_id, i] = 2.0 + ti.random() * 5.0
            self.moving_obstacle_waypoint_count[env_id, i] = 6
            self.moving_obstacle_current_waypoint[env_id, i] = 0

            center_x = 200.0 + i * 250.0
            center_y = 200.0 + i * 100.0
            radius = 80.0
            for j in range(6):
                angle = j * 2.0 * tm.pi / 6.0
                self.moving_obstacle_waypoints[env_id, i, j] = ti.Vector(
                    [center_x + radius * tm.cos(angle), center_y + radius * tm.sin(angle)]
                )
        self.moving_obstacle_active[env_id, 2] = 1
        self.moving_obstacle_pos[env_id, 2] = ti.Vector([1500, 600])
        self.moving_obstacle_radius[env_id, 2] = 20.0 + ti.random() * 5.0
        self.moving_obstacle_speed[env_id, 2] = 3.0 + ti.random() * 2.0
        self.moving_obstacle_waypoint_count[env_id, 2] = 6
        self.moving_obstacle_current_waypoint[env_id, 2] = 0

        center_x = 1300
        center_y = 650
        radius = 80.0
        for j in range(6):
            angle = j * 2.0 * tm.pi / 6.0
            self.moving_obstacle_waypoints[env_id, 2, j] = ti.Vector(
                [center_x + radius * tm.cos(angle), center_y + radius * tm.sin(angle)]
            )

    @ti.func
    def _init_complex_scenario(self, env_id: ti.i32):
        for i in range(7):
            self.static_obstacle_active[env_id, i] = 1
            self.static_obstacle_pos[env_id, i] = ti.Vector(
                [100.0 + i * 140.0 + ti.random() * 80.0, 100.0 + ti.random() * 800.0]
            )
            self.static_obstacle_radius[env_id, i] = 20.0 + ti.random() * 30.0

        for i in range(5):
            self.moving_obstacle_active[env_id, i] = 1
            self.moving_obstacle_pos[env_id, i] = ti.Vector(
                [150.0 + i * 200.0, 150.0 + (i % 2) * 400.0]
            )
            self.moving_obstacle_radius[env_id, i] = 15.0 + ti.random() * 20.0
            self.moving_obstacle_speed[env_id, i] = 12.0 + ti.random() * 8.0
            self.moving_obstacle_waypoint_count[env_id, i] = 8
            self.moving_obstacle_current_waypoint[env_id, i] = 0

            for j in range(8):
                angle = j * 2.0 * tm.pi / 8.0
                radius = 100.0 + 50.0 * tm.sin(angle * 2.0)
                center_x = 150.0 + i * 200.0
                center_y = 150.0 + (i % 2) * 400.0
                self.moving_obstacle_waypoints[env_id, i, j] = ti.Vector(
                    [center_x + radius * tm.cos(angle), center_y + radius * tm.sin(angle)]
                )

    def setup_line_obstacles_taichi(self, obstacle_lines_list: list[list[list[float]]]):
        line_segments = []
        for env_obstacles in obstacle_lines_list:
            env_segments = []
            for polygon in env_obstacles:
                for i in range(len(polygon)):
                    start = polygon[i]
                    end = polygon[(i + 1) % len(polygon)]
                    env_segments.append([start, end])
            line_segments.append(env_segments)

        print(line_segments)

        if line_segments:
            self.setup_line_obstacles(line_segments[0])

    @ti.kernel
    def update_moving_obstacles(self):
        dt = self.dt[None]

        # for env_id in range(self.max_env):
        #     for obs_id in range(self.max_moving_obstacles):
        # Struct for parallel computing
        for index in ti.grouped(self.moving_obstacle_pos):
            if self.moving_obstacle_active[index]:
                env_id, obs_id = index[0], index[1]
                current_wp = self.moving_obstacle_current_waypoint[index]
                wp_count = self.moving_obstacle_waypoint_count[index]
                target_pos = self.moving_obstacle_waypoints[env_id, obs_id, current_wp]

                current_pos = self.moving_obstacle_pos[index]
                to_target = target_pos - current_pos
                distance = tm.length(to_target)

                if distance < 10.0:
                    self.moving_obstacle_current_waypoint[index] = (current_wp + 1) % wp_count
                    target_pos = self.moving_obstacle_waypoints[
                        env_id, obs_id, self.moving_obstacle_current_waypoint[index]
                    ]
                    to_target = target_pos - current_pos
                    distance = tm.length(to_target)

                if distance > 1e-4:
                    direction = to_target / distance
                    speed = self.moving_obstacle_speed[index]
                    self.moving_obstacle_pos[index] += direction * speed * dt
                    self.moving_obstacle_vel[index] = direction * speed

    @ti.kernel
    def check_collisions(self):
        self.collision_detected.fill(0)

        for index in ti.grouped(self.x):
            env_id, _agent_id = index[0], index[1]
            # for env_id in range(self.max_env):
            #     for agent_id in range(self.max_num):
            if self.active[index]:
                agent_pos = self.x[index].xy
                agent_radius = self.width[index] / 2.0

                for obs_id in range(self.max_static_obstacles):
                    if self.static_obstacle_active[env_id, obs_id]:
                        obs_pos = self.static_obstacle_pos[env_id, obs_id]
                        obs_radius = self.static_obstacle_radius[env_id, obs_id]

                        if tm.length(agent_pos - obs_pos) < agent_radius + obs_radius:
                            self.collision_detected[index] = 1
                            self.done[index] += 1

                for obs_id in range(self.max_moving_obstacles):
                    if self.moving_obstacle_active[env_id, obs_id]:
                        obs_pos = self.moving_obstacle_pos[env_id, obs_id]
                        obs_radius = self.moving_obstacle_radius[env_id, obs_id]

                        if tm.length(agent_pos - obs_pos) < agent_radius + obs_radius:
                            self.collision_detected[index] = 1
                            self.done[index] += 1

                if (
                    agent_pos.x < agent_radius
                    or agent_pos.x > self.res[0] - agent_radius
                    or agent_pos.y < agent_radius
                    or agent_pos.y > self.res[1] - agent_radius
                ):
                    self.collision_detected[index] = 1
                    self.done[index] += 1

    @ti.kernel
    def calculate_potential_gradients(self):
        for index in ti.grouped(self.x):
            env_id, _agent_id = index[0], index[1]
            if self.active[index]:
                agent_pos = self.x[index].xy
                goal_pos = self.goal_pos[index]

                to_goal = goal_pos - agent_pos
                distance_to_goal = tm.length(to_goal) + 1e-5

                # if distance_to_goal > 0:
                #     attractive_grad = to_goal / distance_to_goal
                # else:
                #     attractive_grad = ti.Vector([0.0, 0.0])
                self.gradient[index] = -to_goal / distance_to_goal

                for obs_id in ti.static(range(self.max_static_obstacles)):
                    if self.static_obstacle_active[env_id, obs_id]:
                        obs_pos = self.static_obstacle_pos[env_id, obs_id]
                        margin = -(
                            (
                                (self.width[index] + self.static_obstacle_radius[env_id, obs_id])
                                / self.res[0]
                            )
                            ** 2
                        )
                        to_obs = (agent_pos - obs_pos) / self.res[0]
                        for coord in ti.static(range(2)):
                            margin += to_obs[coord] ** 2

                        d0 = (self.searchR[None] / self.res[0]) ** 2

                        if margin <= 0.0:
                            self.done[index] += 1
                        elif margin < d0:
                            valLog = tm.log(margin / d0)
                            valLogC = valLog * (margin - d0)
                            relD = 1 - d0 / margin
                            D = -self.coef[None] * (2 * valLogC + (margin - d0) * relD)
                            grad_value = D * 2 * to_obs

                            self.gradient[index] += grad_value
                            self.aa_gradient[index] += grad_value

                    # if distance < influence_radius and distance > 0:
                    #     repulsive_grad += to_obs / (distance * distance + 1e-6)

                for obs_id in ti.static(range(self.max_moving_obstacles)):
                    if self.moving_obstacle_active[env_id, obs_id]:
                        obs_pos = self.moving_obstacle_pos[env_id, obs_id]
                        margin = -(
                            (
                                (self.width[index] + self.moving_obstacle_radius[env_id, obs_id])
                                / self.res[0]
                            )
                            ** 2
                        )
                        to_obs = (agent_pos - obs_pos) / self.res[0]
                        for coord in ti.static(range(2)):
                            margin += to_obs[coord] ** 2

                        d0 = (self.searchR[None] / self.res[0]) ** 2

                        if margin <= 0.0:
                            self.done[index] += 1
                        elif margin < d0:
                            valLog = tm.log(margin / d0)
                            valLogC = valLog * (margin - d0)
                            relD = 1 - d0 / margin
                            D = -self.coef[None] * (2 * valLogC + (margin - d0) * relD)
                            grad_value = D * 2 * to_obs

                            self.gradient[index] += grad_value
                            self.aa_gradient[index] += grad_value

                    # obs_pos = self.moving_obstacle_pos[env_id, obs_id]
                    # to_obs = agent_pos - obs_pos
                    # distance = tm.length(to_obs)
                    # influence_radius = self.moving_obstacle_radius[env_id, obs_id] + 120.0
                    #
                    # if distance < influence_radius and distance > 0:
                    #     repulsive_grad += to_obs / (distance * distance + 1e-6)

    @ti.kernel
    def calculate_path_smoothness(self):
        for env_id in range(self.max_env):
            for agent_id in range(self.max_num):
                if self.active[env_id, agent_id]:
                    traj_len = self.trajectory_length[env_id, agent_id]

                    if traj_len >= 3:
                        p1 = self.trajectory_pos[env_id, agent_id, traj_len - 3]
                        p2 = self.trajectory_pos[env_id, agent_id, traj_len - 2]
                        p3 = self.trajectory_pos[env_id, agent_id, traj_len - 1]

                        v1 = p2 - p1
                        v2 = p3 - p2

                        v1_len = tm.length(v1)
                        v2_len = tm.length(v2)

                        if v1_len > 0 and v2_len > 0:
                            cos_angle = tm.dot(v1, v2) / (v1_len * v2_len)
                            cos_angle = tm.clamp(cos_angle, -1.0, 1.0)
                            angle_change = tm.acos(cos_angle)
                            self.path_smoothness[env_id, agent_id] = angle_change
                            # print(angle_change)
                        else:
                            self.path_smoothness[env_id, agent_id] = 0.0
                    else:
                        self.path_smoothness[env_id, agent_id] = 0.0

    @ti.kernel
    def update_trajectory(self):
        for env_id in range(self.max_env):
            for agent_id in range(self.max_num):
                if self.active[env_id, agent_id]:
                    traj_len = self.trajectory_length[env_id, agent_id]
                    if traj_len < self.max_trajectory_length:
                        self.trajectory_pos[env_id, agent_id, traj_len] = self.x[
                            env_id, agent_id
                        ].xy
                        self.trajectory_length[env_id, agent_id] += 1

    @ti.kernel
    def calculate_rewards(self):
        # for env_id in range(self.max_env):
        #     for agent_id in range(self.max_num):
        for index in ti.grouped(self.x):
            env_id, _agent_id = index[0], index[1]
            if self.active[index]:
                reward = 0.0

                current_pos = self.x[index].xy
                goal_pos = self.goal_pos[index]
                current_distance = tm.length(current_pos - goal_pos)

                distance_improvement = self.previous_distance_to_goal[index] - current_distance
                reward += distance_improvement
                self.previous_distance_to_goal[index] = current_distance

                if current_distance < 50.0:
                    reward += 200.0
                    self.done[index] += 1

                if self.collision_detected[index]:
                    reward -= 500.0
                    self.done[index] += 1

                reward -= 0.1

                # mask reward
                if ti.static(self.use_mask):
                    reward -= self.mask_num[env_id] * 0.1
                # Alternative: penalize aggregate avoidance-gradient magnitude.

                self.step_count[index] += 1

                if self.step_count[index] >= self.max_episode_steps:
                    reward -= 5.0
                    self.done[index] += 1

                self.reward[index] = reward

    @ti.kernel
    def render_obstacles_to_buffer_navigation(self):
        for index in ti.grouped(self.x):
            env_id, agent_id = index[0], index[1]
            if self.active[index]:
                agent_pos = self.x[index].xy

                for obs_id in range(self.max_moving_obstacles):
                    if self.moving_obstacle_active[env_id, obs_id]:
                        obs_pos = self.moving_obstacle_pos[env_id, obs_id]
                        obs_radius = self.moving_obstacle_radius[env_id, obs_id]
                        # obs_radius = ti.max(3, self.moving_obstacle_radius[env_id, obs_id])

                        if tm.length(obs_pos - agent_pos) <= self.bev_radius[None]:
                            rel_pos = (obs_pos - agent_pos) * self.bev_scale + self.bev_size / 2
                            bev_radius = obs_radius * self.bev_scale

                            self._render_circle_to_bev(
                                env_id, agent_id, rel_pos, bev_radius, 0, 0.9
                            )  # 绿色

                for obs_id in range(self.max_static_obstacles):
                    if self.static_obstacle_active[env_id, obs_id]:
                        obs_pos = self.static_obstacle_pos[env_id, obs_id]
                        obs_radius = self.static_obstacle_radius[env_id, obs_id]

                        if tm.length(obs_pos - agent_pos) <= self.bev_radius[None]:
                            rel_pos = (obs_pos - agent_pos) * self.bev_scale + self.bev_size / 2
                            bev_radius = obs_radius * self.bev_scale

                            self._render_circle_to_bev(
                                env_id, agent_id, rel_pos, bev_radius, 0, 0.9
                            )  # 红色

    @ti.func
    def _render_circle_to_bev(
        self,
        env_id: ti.i32,
        agent_id: ti.i32,
        center: tm.vec2,
        radius: ti.f32,
        channel: ti.i32,
        intensity: ti.f32,
    ):
        center_x, center_y = center.x, center.y

        min_x = ti.max(0, ti.cast(center_x - radius, ti.i32))
        max_x = ti.min(self.bev_size - 1, ti.cast(center_x + radius, ti.i32))
        min_y = ti.max(0, ti.cast(center_y - radius, ti.i32))
        max_y = ti.min(self.bev_size - 1, ti.cast(center_y + radius, ti.i32))

        # print('rendering', env_id, agent_id, min_x, max_x, min_y, max_y, channel, intensity)

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                dist_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                if dist_sq <= radius**2:
                    self.bev_buffer[env_id, agent_id, y, x][channel] = intensity

    @ti.kernel
    def clear_gradients(self):
        self.gradient.fill(0.0)
        self.aa_gradient.fill(0.0)
        self.ao_gradient.fill(0.0)

    @ti.func
    def deal_NaN(self, input):
        return ti.select((not (input <= 0 or input > 0)), 0.0, input)

    def _target_heading_actions(self, speeds: np.ndarray, headings_deg: np.ndarray) -> np.ndarray:
        """Translate an RVO target heading into the selected solver's action contract."""
        target_actions = np.stack((speeds, headings_deg), axis=-1)
        if self.solver_type in {"mmg", "nomoto"}:
            current_math_rad = self.psi.to_numpy()
            rudders = np.empty_like(headings_deg, dtype=np.float64)
            for index in np.ndindex(headings_deg.shape):
                rudders[index] = heading_to_rudder(
                    float(headings_deg[index]), float(current_math_rad[index])
                )
            target_actions[..., 1] = rudders
            return validate_mmg_actions(target_actions)
        return validate_kinematic_actions(target_actions, max_speed_mps=self.max_speed)

    def _validate_direct_actions(self, actions: np.ndarray) -> np.ndarray:
        """Reject commands that do not match the selected solver's explicit contract."""
        validate_action_tensor_shape(actions, batch_size=self.max_env, entity_count=self.max_num)
        if self.solver_type in {"mmg", "nomoto"}:
            return validate_mmg_actions(actions)
        return validate_kinematic_actions(actions, max_speed_mps=self.max_speed)

    def step(self, actions: np.ndarray, ii, rl_input=False, grad_out=False):
        # self.done.fill(0)
        ii = ii
        np_reward = np.zeros((self.max_env, 1))
        vels = np.ones((self.max_env, 1)) * 5.0
        if rl_input and self.use_mask:
            rvo_actions = self.compute_RVO_signal()
            des_ang = self.des_ang.to_numpy()
            # print(actions.shape, des_ang.shape)
            rl_ang = des_ang + actions * 2 * np.pi / self._discrete_vels
            rvo_ang = rvo_actions[:, :, -1] * np.pi / 180
            np_reward = -((rl_ang - rvo_ang) ** 2)
            if not ii:
                target_headings = (90.0 - np.degrees(rl_ang)) % 360.0
                real_actions = self._target_heading_actions(rvo_actions[:, :, 0], target_headings)
            else:
                # Taking over, maybe useful in off-policy methods
                real_actions = self._target_heading_actions(
                    rvo_actions[:, :, 0], rvo_actions[:, :, 1]
                )
            # print(real_actions, rl_ang, rvo_ang)
        elif rl_input and not self.use_mask:
            rvo_actions = self.compute_RVO_signal()
            des_ang = self.des_ang.to_numpy()
            rl_ang = des_ang + actions * 2 * np.pi / self._discrete_vels
            target_headings = (90.0 - np.degrees(rl_ang)) % 360.0
            real_actions = self._target_heading_actions(vels, target_headings)
        else:
            real_actions = self._validate_direct_actions(actions)

        # print(real_actions, '\n ---- \n', np_reward, rvo_actions)
        # print(ii, real_actions[0,:,-1])

        self.collision_detected.fill(0)
        self.clear_gradients()
        self.core_step(real_actions)
        self.update_moving_obstacles()
        self.update_trajectory()

        self.check_collisions()
        self.intersection_check_nav()
        self.calculate_potential_gradients()
        self.calculate_path_smoothness()

        # if self.use_ic:
        self.find_ao_neighbour_by_agent()
        self.compute_gradAO()
        # self.feat_encode_kernel()

        self.calculate_rewards()
        self.update_active()
        self.update_target_v()

        # self.step_count += 1

        obs = self.get_observation(grad_out=grad_out)

        # if grad out or numpy out
        if grad_out:
            rewards = self.reward.to_torch(device=self.device)
            dones = (self.done.to_torch(device=self.device) > 0).float()
        else:
            rewards = self.reward.to_numpy()
            dones = np.array(self.done.to_numpy() > 0)

        rewards += np_reward

        # print('rewawrd shape', rewards.shape, dones.shape)
        # print(dones)

        info = {
            "collisions": self.collision_detected.to_torch(device=self.device),
            "distances_to_goal": self.previous_distance_to_goal.to_torch(device=self.device),
            "path_smoothness": self.path_smoothness.to_torch(device=self.device),
        }

        return obs, rewards, dones, info

    def step_real(self, x, y, u, v, ii=None, rl_input=False, grad_out=False):
        #################################
        # For real-ship deployment!!!!

        self.collision_detected.fill(0)
        self.clear_gradients()

        self.insert_x_pos(x, y, u, v)

        # self.core_step(real_actions)

        self.update_moving_obstacles()

        self.update_trajectory()

        self.check_collisions()
        # self.intersection_check_nav()
        self.calculate_potential_gradients()
        self.calculate_path_smoothness()

        # if self.use_ic:
        self.find_ao_neighbour_by_agent()
        self.compute_gradAO()
        # self.feat_encode_kernel()

        self.calculate_rewards()

        # self.update_active()

        # self.step_count += 1

        obs = self.get_observation(grad_out=grad_out)

        if grad_out:
            rewards = self.reward.to_torch(device=self.device)
            dones = (self.done.to_torch(device=self.device) > 0).float()
        else:
            rewards = self.reward.to_numpy()
            dones = np.array(self.done.to_numpy() > 0)

        info = {
            "collisions": self.collision_detected.to_torch(device=self.device),
            "distances_to_goal": self.previous_distance_to_goal.to_torch(device=self.device),
            "path_smoothness": self.path_smoothness.to_torch(device=self.device),
        }

        return obs, rewards, dones, info

    def reset(self, scenario_type: int = 1, seed: int | None = None):
        self.done.fill(0)
        self.reward.fill(0)
        self.step_count.fill(0)
        self.trajectory_length.fill(0)
        self.collision_detected.fill(0)
        self.active.fill(1)

        if seed is not None:
            self.session_rng.reset(seed)
        pi_v = float(np.pi)
        # self.w_vel[None] = 1.0
        self.w_vel[None] = self.session_rng.generator.random() / 2
        self.beta_w[None] = self.session_rng.generator.random() * 2 * pi_v
        print("for winds and waves: ", self.w_vel[None], self.beta_w[None], "\n`````````[")

        poses = np.zeros((self.max_env, self.max_num, 3), dtype=np.float32)
        vels = np.zeros((self.max_env, self.max_num, 3), dtype=np.float32)
        craft_camps = np.zeros((self.max_env, self.max_num), dtype=np.int32)
        widths = np.ones((self.max_env, self.max_num), dtype=np.float32) * 10.0
        angle_lims = np.ones((self.max_env, self.max_num), dtype=np.float32) * 0.5
        max_v = np.ones((self.max_env, self.max_num), dtype=np.float32) * 5

        poses[:, :, 0] = self.session_rng.generator.uniform(30, 150, (self.max_env, self.max_num))
        poses[:, :, 1] = self.session_rng.generator.uniform(10, 50, (self.max_env, self.max_num))
        poses[:, :, 2] = self.session_rng.generator.uniform(
            0, 2 * np.pi, (self.max_env, self.max_num)
        )

        vels[:, :, 0] = self.session_rng.generator.uniform(8, 12, (self.max_env, self.max_num))

        self.core_init(poses, vels, craft_camps, widths, angle_lims, max_v)

        self.init_obstacles_scenario(scenario_type)

        self.set_random_goals()

        # if hasattr(self, 'line_obstacles_config'):
        #     self.setup_line_obstacles_taichi(self.line_obstacles_config)

        self.calculate_potential_gradients()
        self.update_initial_distances()

        self.find_ao_neighbour_by_agent()
        self.compute_gradAO()

        self.update_target_v()

        obs = self.get_observation()

        return obs

    def reset_real(self, scenario_type: int = 1):
        ############################
        # Real ship deployment
        self.done.fill(0)
        self.reward.fill(0)
        self.step_count.fill(0)
        self.trajectory_length.fill(0)
        self.collision_detected.fill(0)
        self.active.fill(1)

        poses = np.zeros((self.max_env, self.max_num, 3), dtype=np.float32)
        vels = np.zeros((self.max_env, self.max_num, 3), dtype=np.float32)
        craft_camps = np.zeros((self.max_env, self.max_num), dtype=np.int32)
        widths = np.ones((self.max_env, self.max_num), dtype=np.float32) * 10.0
        angle_lims = np.ones((self.max_env, self.max_num), dtype=np.float32) * 0.5
        max_v = np.ones((self.max_env, self.max_num), dtype=np.float32) * 5

        poses[:, :, 0] = 50
        poses[:, :, 1] = 20
        poses[:, :, 2] = self.session_rng.generator.uniform(
            0, 2 * np.pi, (self.max_env, self.max_num)
        )

        vels[:, :, 0] = self.session_rng.generator.uniform(8, 12, (self.max_env, self.max_num))

        self.core_init(poses, vels, craft_camps, widths, angle_lims, max_v)

        self.init_obstacles_scenario(scenario_type)

        # 设置目标位置
        self.set_random_goals()

        # if hasattr(self, 'line_obstacles_config'):
        #     self.setup_line_obstacles_taichi(self.line_obstacles_config)

        self.calculate_potential_gradients()
        self.update_initial_distances()

        self.find_ao_neighbour_by_agent()
        self.compute_gradAO()

        self.update_target_v()

        obs = self.get_observation()

        return obs

    @ti.kernel
    def update_active(self):
        for index in ti.grouped(self.done):
            # if done < 1, then active
            self.active[index] = ti.cast(self.done[index] < 1, ti.i32)

    @ti.kernel
    def set_random_goals(self):
        for env_id in range(self.max_env):
            for agent_id in range(self.max_num):
                # self.goal_pos[env_id, agent_id] = ti.Vector([
                #     ti.random() * (self.res[0] - 200) + 100,
                #     ti.random() * (self.res[1] - 200) + 100
                # ])
                self.goal_pos[env_id, agent_id] = ti.Vector(
                    [self.args.target[0], self.args.target[1]]
                )
                print(self.goal_pos[env_id, agent_id])

    @ti.kernel
    def update_initial_distances(self):
        for env_id in range(self.max_env):
            for agent_id in range(self.max_num):
                if self.active[env_id, agent_id]:
                    current_pos = self.x[env_id, agent_id].xy
                    goal_pos = self.goal_pos[env_id, agent_id]
                    self.previous_distance_to_goal[env_id, agent_id] = tm.length(
                        current_pos - goal_pos
                    )

    def get_observation(self, grad_out=False):
        rdn_value = 0.95 + 0.1 * self.session_rng.generator.random() if self.randomization else 1.0

        if self.use_bev:
            self.clear_bev_buffers()
            self.render_obstacles_to_buffer()
            self.render_ships_to_buffer()
            self.render_obstacles_to_buffer_navigation()
            self.finalize_bev_images()
            self.normalize_gradients()

        if grad_out:
            bev_tensor = self.bev_images.to_torch(device=self.device) if self.use_bev else None

            positions = self.x.to_torch(device=self.device)
            velocities = self.v.to_torch(device=self.device) / 5.0
            target_directions = self.target_v.to_torch(device=self.device) / 5.0
            # print(target_directions)
            # headings = self.psi.to_torch(device=self.device)

            goals = self.target.to_torch(device=self.device)

            aa_g = self.aa_gradient.to_torch(device=self.device)
            ao_g = self.ao_gradient.to_torch(device=self.device)
            ff_g = self.gradient.to_torch(device=self.device)

            grads = torch.cat([aa_g[:, 0, :], ao_g[:, 0, :], ff_g[:, 0, :]], dim=-1)
            mask_num = (
                self.mask_num.to_torch(device=self.device).unsqueeze(-1) / self._discrete_vels
            )
            action_mask = self.action_mask.to_torch(device=self.device)
            obs = {
                "bev": bev_tensor,
                "ship_state": torch.cat(
                    [
                        positions[:, 0, :2] / self.res[0],  # x, y
                        velocities[:, 0, :2],  # u, v
                        # headings.unsqueeze(-1),  # psi
                        torch.norm(velocities[:, 0, :2], dim=-1, keepdim=True),  # speed
                        target_directions,
                        torch.norm(goals - positions[:, 0, :2], dim=-1, keepdim=True) / 1000,
                        # Optional normalized episode progress and distance-to-goal.
                    ],
                    dim=-1,
                )
                * rdn_value,
                "helper": torch.cat([grads, mask_num], dim=-1) * rdn_value,
                "mask": action_mask,
            }
        else:
            bev_tensor = self.bev_images.to_numpy() if self.use_bev else None

            positions = self.x.to_numpy()
            velocities = self.v.to_numpy() / 5.0
            target_directions = self.target_v.to_numpy() / 5.0
            # print(target_directions)
            # headings = self.psi.to_torch(device=self.device)

            goals = self.target.to_numpy()
            self.target.to_numpy() / self.res[0]

            aa_g = self.aa_gradient.to_numpy()
            ao_g = self.ao_gradient.to_numpy()
            ff_g = self.gradient.to_numpy()

            grads = np.concatenate([aa_g[:, 0, :], ao_g[:, 0, :], ff_g[:, 0, :]], axis=-1)
            mask_num = np.expand_dims(self.mask_num.to_numpy() / self._discrete_vels, axis=-1)
            action_mask = self.action_mask.to_numpy()

            obs = {
                "bev": bev_tensor,
                "ship_state": np.concatenate(
                    [
                        positions[:, 0, :2] / self.res[0],  # x, y
                        velocities[:, 0, :2],  # u, v
                        # headings.unsqueeze(-1),  # psi
                        np.expand_dims(
                            np.linalg.norm(velocities[:, 0, :2], axis=-1), axis=-1
                        ),  # speed
                        target_directions,
                        # targets,
                        np.expand_dims(
                            np.linalg.norm(goals - positions[:, 0, :2], axis=-1) / 1000, axis=-1
                        ),
                        # Optional normalized episode progress and distance-to-goal.
                    ],
                    axis=-1,
                )
                * rdn_value,
                "helper": np.concatenate([grads, mask_num], axis=-1) * rdn_value,
                "mask": action_mask,
            }

            # print(obs)
        return obs

    def set_line_obstacles_config(self, obstacles_config: list[list[list[float]]]):
        self.line_obstacles_config = obstacles_config

    def render(self):
        pass

    ###################
    # RVO-here

    def setup_rvo_dynamic_field(self, rvo_d0=600, rvo_smooth_factor=0.25, discrete_vels=19):
        self.rvo_step = 0
        self.rvo_searchR = rvo_d0
        self._rvo_epsilon = 1e-6
        # self._discrete_vels = discrete_vels
        # self._discrete_angle = ti.cast(tm.pi / (discrete_vels - 1), self.ctype)
        self._discrete_vels = discrete_vels - 1
        self._discrete_angle = ti.cast(2 * tm.pi / (discrete_vels - 1), self.ctype)
        self._rvo_time_horizon = self.dt[None] * self.substeps_float[None]
        self._rvo_smooth_factor = rvo_smooth_factor
        rvo_overall_root = ti.root.dense(ti.i, self.max_env)
        rr1 = rvo_overall_root.dynamic(ti.j, 512, chunk_size=32)
        rr2 = rvo_overall_root.dynamic(ti.j, 512, chunk_size=32)
        rv1 = rvo_overall_root.dynamic(ti.j, 512, chunk_size=32)
        rr3 = rvo_overall_root.dynamic(ti.j, 512, chunk_size=32)
        cndv = rvo_overall_root.dynamic(ti.j, 64, chunk_size=32)
        self.cone_angle_cos = ti.field(dtype=ti.f32)
        self.rvo_rad = ti.field(dtype=ti.f32)
        self.rvo_pos = ti.Vector.field(2, dtype=ti.f32)
        self.rvo_vel = ti.Vector.field(2, dtype=ti.f32)
        self.candi_vel = ti.Vector.field(2, dtype=ti.f32)

        rr1.place(self.cone_angle_cos)
        rr2.place(self.rvo_pos)
        rr3.place(self.rvo_rad)
        rv1.place(self.rvo_vel)
        cndv.place(self.candi_vel)

        self.rvo_count = ti.field(dtype=ti.i32, shape=(self.max_env,))
        self.rvo_count.fill(0)

        self.candi_vel_count = ti.field(dtype=ti.i32, shape=(self.max_env,))
        self.candi_vel_count.fill(0)

        self.target_v = ti.Vector.field(2, dtype=self.ctype, shape=(self.max_env,))
        self.target_v.fill(0)

        self.action_mask = ti.field(dtype=self.ctype, shape=(self.max_env, self._discrete_vels))
        self.action_mask.fill(1)

        self.mask_num = ti.field(dtype=self.ctype, shape=(self.max_env,))
        self.mask_num.fill(self._discrete_vels)

        self.rvo_signal = ti.field(dtype=self.ctype, shape=(self.max_env, self.max_num, 2))
        self.rvo_signal.fill(0)

    @ti.kernel
    def rvo_initalize(self):
        for i in range(self.max_env):
            self.rvo_vel[i].deactivate()
            self.rvo_pos[i].deactivate()
            self.cone_angle_cos[i].deactivate()
            self.rvo_rad[i].deactivate()
            self.candi_vel[i].deactivate()
        self.rvo_count.fill(0)
        self.candi_vel_count.fill(0)
        self.action_mask.fill(0)
        self.mask_num.fill(self._discrete_vels)  # initial guessing: all velocities masked
        # Utilizing atomic add still causes some order errors, e.x.
        # ray1 ray2 & rvo velocities' mismatch, just use if/else

        for index in ti.grouped(self.moving_obstacle_pos):
            if self.moving_obstacle_active[index]:
                env_id, _obs_id = index[0], index[1]
                neigh_x = self.moving_obstacle_pos[index]
                neigh_v = self.moving_obstacle_vel[index]

                rel_pos = self.x[env_id, 0] - neigh_x
                dist = tm.length(rel_pos)
                # print(dist)
                dist_sq = dist**2
                if dist < self.rvo_searchR:
                    idx = ti.atomic_add(self.rvo_count[env_id], 1)
                    # print(idx)
                    radius_sum = (self.width[env_id, 0] + self.moving_obstacle_radius[index]) * 2.5

                    cone_angle_cos = ti.sqrt(dist_sq - radius_sum**2) / dist

                    self.cone_angle_cos[env_id, idx] = cone_angle_cos
                    self.rvo_pos[env_id, idx] = neigh_x
                    self.rvo_vel[env_id, idx] = neigh_v
                    self.rvo_rad[env_id, idx] = self.moving_obstacle_radius[index]

        for index in ti.grouped(self.static_obstacle_pos):
            if self.static_obstacle_active[index]:
                env_id, _obs_id = index[0], index[1]
                neigh_x = self.static_obstacle_pos[index]
                neigh_v = tm.vec2(0.0, 0.0)

                rel_pos = self.x[env_id, 0] - neigh_x
                dist = tm.length(rel_pos)
                # print(dist)
                dist_sq = dist**2
                if dist < self.rvo_searchR:
                    idx = ti.atomic_add(self.rvo_count[env_id], 1)
                    # print(idx)
                    radius_sum = (self.width[env_id, 0] + self.static_obstacle_radius[index]) * 2.5

                    cone_angle_cos = ti.sqrt(dist_sq - radius_sum**2) / dist

                    self.cone_angle_cos[env_id, idx] = cone_angle_cos
                    self.rvo_pos[env_id, idx] = neigh_x
                    self.rvo_vel[env_id, idx] = neigh_v
                    self.rvo_rad[env_id, idx] = self.static_obstacle_radius[index]

        # for i in range(obs.shape[0]):
        #     neigh_x = ti.Vector([obs[i, 0], obs[i, 1]])
        #     neigh_v = ti.Vector([obs[i, 2], obs[i, 3]])
        #
        #     rel_pos = self.x[0] - neigh_x
        #     dist = tm.length(rel_pos)
        #     # print(dist)
        #     dist_sq = dist ** 2
        #     if dist < self.rvo_searchR:
        #         idx = ti.atomic_add(self.rvo_count[None], 1)
        #         # print(idx)
        #         radius_sum = self.width[0] * 2
        #
        #         cone_angle_cos = ti.sqrt(dist_sq - radius_sum ** 2) / dist
        #
        #         # angle = tm.atan2(rel_pos.y, rel_pos.x)
        #         # half_angle = tm.asin(radius_sum / dist)
        #         # ray1 = tm.vec2(tm.cos(angle - half_angle), tm.sin(angle - half_angle))
        #         # ray2 = tm.vec2(tm.cos(angle + half_angle), tm.sin(angle + half_angle))
        #
        #         self.cone_angle_cos[idx] = cone_angle_cos
        #         self.rvo_pos[idx] = neigh_x
        #         self.rvo_vel[idx] = neigh_v

    @ti.kernel
    def rvo_search(self):
        self.candi_vel_count.fill(0)
        for i in range(self.max_env):
            # v_des = tm.normalize(self.target_v[i])
            # des_ang = tm.atan2(v_des.y, v_des.x) - tm.pi / 2.0
            # if des_ang < -tm.pi:
            #     des_ang += tm.pi * 2.0
            # self.des_ang[i, 0] = des_ang
            self.des_ang[i, 0] = 0.0
        # print(self.v[0])

        # from -180 degrees to 180 degrees uniform sample per 20 degrees
        for index in ti.grouped(ti.ndrange(self.max_env, self._discrete_vels)):
            env_id, angle = index[0], index[1]
            result = 0
            rad = angle * self._discrete_angle
            pos_a = self.x[env_id, 0]
            radius_a = self.width[env_id, 0] * 2.5
            # ignoring * alpha
            vsample = (
                5
                * ti.Vector(
                    [tm.cos(self.des_ang[env_id, 0] + rad), tm.sin(self.des_ang[env_id, 0] + rad)]
                )
                * self.v_max[env_id, 0]
            )
            # print(des_ang, des_ang + rad, vsample, v_des)
            for vo_id in range(self.rvo_count[env_id]):
                # rel_v = vsample - self.rvo_vel[vo_id]
                hybrid_radius = radius_a + self.rvo_rad[env_id, vo_id] * 2.5
                result += self._is_vel_safe_from_circle(
                    pos_a,
                    hybrid_radius,
                    vsample,
                    self.rvo_pos[env_id, vo_id],
                    self.rvo_vel[env_id, vo_id],
                    self.cone_angle_cos[env_id, vo_id],
                )
            for vl_id in range(self.n_ao[env_id]):
                v_id = self.candidate_ao[env_id, vl_id][1]
                v0 = self.obstacle_v[v_id, 0]
                v1 = self.obstacle_v[v_id, 1]
                result += self._is_vel_safe_from_line(pos_a, radius_a, vsample, v0, v1)
            #
            if result == 0:
                vel_idx = ti.atomic_add(self.candi_vel_count[env_id], 1)
                self.action_mask[env_id, angle] = 1.0
                self.mask_num[env_id] -= 1.0
                self.candi_vel[env_id, vel_idx] = vsample / 5

    @ti.kernel
    def rvo_best_vel(self):
        # ti.loop_config(serialize=True)
        for env_id in range(self.max_env):
            ti.Vector([0.0, 0.0])
            gap = 1e5
            best_v = ti.Vector([0.0, 0.0])

            for c_idx in range(self.candi_vel_count[env_id]):
                vel = self.candi_vel[env_id, c_idx]
                # add smooth factor
                # ignoring alpha
                current_gap = tm.length(
                    vel - self.target_v[env_id]
                ) + self._rvo_smooth_factor * tm.length(vel - self.v[env_id, 0])
                # print(best_v, vel, current_gap)
                if current_gap < gap:
                    best_v = vel
                    gap = current_gap

            self.rvo_signal[env_id, 0, 0] = tm.length(best_v)
            self.rvo_signal[env_id, 0, 1] = (
                (tm.atan2(best_v.x, best_v.y) * 180.0 / tm.pi) + 360.0
            ) % 360.0

            # self.new_v[0] = best_v
        # print('new-v', self.new_v[0])

    # @ti.kernel
    # def update_target(self):
    @ti.kernel
    def normalize_gradients(self):
        # pick out Nans/Infs; normalize; reverse directions
        for index in ti.grouped(self.aa_gradient):
            new_grad = tm.vec2(
                self.deal_NaN(self.aa_gradient[index].x), self.deal_NaN(self.aa_gradient[index].y)
            )
            normalized = ti.select(
                tm.length(new_grad) > 1e-5, tm.normalize(new_grad), tm.vec2(0.0, 0.0)
            )
            self.aa_gradient[index] = -normalized
        for index in ti.grouped(self.ao_gradient):
            new_grad = tm.vec2(
                self.deal_NaN(self.ao_gradient[index].x), self.deal_NaN(self.ao_gradient[index].y)
            )
            normalized = ti.select(
                tm.length(new_grad) > 1e-5, tm.normalize(new_grad), tm.vec2(0.0, 0.0)
            )
            self.ao_gradient[index] = -normalized
        for index in ti.grouped(self.gradient):
            new_grad = tm.vec2(
                self.deal_NaN(self.gradient[index].x), self.deal_NaN(self.gradient[index].y)
            )
            normalized = ti.select(
                tm.length(new_grad) > 1e-5, tm.normalize(new_grad), tm.vec2(0.0, 0.0)
            )
            self.gradient[index] = -normalized

    @ti.kernel
    def update_target_v(self):
        for i in range(self.max_env):
            self.target_v[i] = tm.normalize(self.target[i] - self.x[i, 0]) * self.v_max[i, 0]
            # print(tm.normalize(self.target[i] - self.x[i, 0])* self.v_max[i, 0])
            # print(self.target[i] ,self.x[i, 0],self.v_max[i, 0], self.target_v[i])

    def compute_RVO_signal(self):
        self.update_target_v()
        self.rvo_initalize()
        self.rvo_search()
        self.rvo_best_vel()

        rvo_signal = self.rvo_signal.to_numpy()
        return rvo_signal

    def compute_RVO_velocity(self, obs):
        self.update_target_v()
        self.rvo_initalize(obs)
        # self.find_ao_neighbour()
        # self.alpha[None] = 1.0
        self.rvo_step += 1

        if self.rvo_count[None] > 0 or self.n_ao[None] > 0:
            # If having obstacles to avoid, then plan!
            while self.alpha[None] > self.global_alpha_min:
                self.intersection_check_result[None] = 0
                self.intersection_check_rvo()
                self.rvo_search()
                if self.candi_vel_count[None] > 0 and self.intersection_check_result[None] == 0:
                    break
                else:
                    self.alpha[None] *= 0.6

            self.alpha[None] *= self.alpha[None] > self.global_alpha_min
            self.rvo_best_vel()
        else:
            self.new_v[0] = self.v[0]

        self.x[0] += self.new_v[0] * self.dt * self.substeps
        # print(self.v[0], self.new_v[0], self.alpha[None])
        craft_info = self.render_info()
        self.check_activity()
        # else v = v_rel

        return craft_info

    @ti.func
    def _get_time_to_collision(self, p_rel, v_rel, combined_radius):
        """
        [Taichi Func] Time to collide with circle obstacles
        """
        # Inf
        ttc = 1e9

        #  solving a*t^2 + b*t + c = 0
        r_sum_sq = combined_radius * combined_radius
        p_dot_p = p_rel.dot(p_rel)
        v_dot_v = v_rel.dot(v_rel)
        p_dot_v = p_rel.dot(v_rel)

        is_separating = p_dot_v >= 0
        is_overlapping = p_dot_p < r_sum_sq

        # else direct solve
        if not is_separating and not is_overlapping:
            a = v_dot_v
            b = 2 * p_dot_v
            c = p_dot_p - r_sum_sq

            discriminant = b * b - 4 * a * c

            # only real solutions exists, continue
            if discriminant >= 0 and a > self._rvo_epsilon:
                t1 = -1.0
                sqrt_disc = ti.sqrt(discriminant)
                # smaller one
                t1 = (-b - sqrt_disc) / (2 * a)
                # print(ttc)

                if t1 > 0:
                    ttc = t1
                    # print(ttc)

        return ttc

    ##Optional##

    # @ti.func
    # def _is_vel_safe_from_circle(...):
    #     rtn_value = 1
    #     pos_a = pos_a
    #     vel_a = vel_candidate

    #     # VO
    #     p_rel = obs_pos - pos_a
    #     p_rel_len = tm.length(p_rel)
    #     apex = obs_vel

    #     v_rel_apex = vel_a - apex

    #     v_rel_apex_len = v_rel_apex.norm()
    #     if v_rel_apex_len < self._rvo_epsilon:
    #         rtn_value = 0  # safe region
    #     else:
    #         dot_product_normalized = v_rel_apex.dot(p_rel) / (v_rel_apex_len * p_rel_len)
    #         if dot_product_normalized > cone_angle_cos:
    #             # adding time to collide
    #             rtn_value = 1
    #         else:
    #             rtn_value = 0

    #     return rtn_value

    @ti.func
    def _is_vel_safe_from_circle(
        self, pos_a, radius_a, vel_candidate, obs_pos, obs_vel, obs_radius
    ):
        rtn_value = 0

        pos_a = pos_a
        radius_a = radius_a
        obs_radius = obs_radius

        # VO
        p_rel = pos_a - obs_pos
        v_rel = vel_candidate - obs_vel
        combined_radius = radius_a

        # TTC computing
        ttc = self._get_time_to_collision(p_rel, v_rel, combined_radius)

        # print(ttc)
        if ttc < self._rvo_time_horizon:
            rtn_value = 1

        return rtn_value

    @ti.func
    def _is_vel_safe_from_line(self, pos_a, radius_a, vel_candidate, line_start, line_end):
        """
        [Taichi Func] line obstacles
        """
        p = pos_a
        v = vel_candidate
        r = radius_a

        next_pos = p + v * self._rvo_time_horizon

        # minium distance
        v0 = line_start
        v1 = line_end

        obs_vec = v1 - v0
        rel_pos0 = v0 - next_pos
        rel_pos1 = v1 - next_pos

        lensq = obs_vec.dot(obs_vec)
        s = -rel_pos0.dot(obs_vec) / lensq

        dist_sq = 0.0
        if s < 0.0:
            # dist_sq = (next_pos - v0).dot(next_pos - v0)
            dist_sq = rel_pos0.dot(rel_pos0)
        elif s > 1.0:
            dist_sq = (next_pos - v1).dot(next_pos - v1)
            dist_sq = rel_pos1.dot(rel_pos1)
        else:
            vp = ti.Vector([-obs_vec.y, obs_vec.x]) / tm.sqrt(lensq)
            dist = rel_pos0.dot(vp)
            # print('dist:', dist)
            dist_sq = dist**2
            # proj_point = v0 + s * obs_vec
            # dist_sq = (next_pos - proj_point).dot(next_pos - proj_point)

        rtn_value = 0

        if dist_sq < r * r:
            rtn_value = 1
            # print(dist_sq, p, line_start, line_end)

        agentVec = v * self._rvo_time_horizon

        RHS = v0 - p

        LHS = tm.mat2([agentVec[0], -obs_vec[0]], [agentVec[1], -obs_vec[1]])

        if LHS.determinant() > 1e-6:
            # print('xxxxxxxxxxxxxxxx')
            s_vec = LHS.inverse() @ RHS
            # print(LHS.inverse(), RHS, LHS.inverse() @ RHS)
            # print(s)
            s0 = s_vec[0]
            s1 = s_vec[1]
            rtn_value += int(0 <= s0 <= 1 and 0 <= s1 <= 1)

        return rtn_value

    @ti.kernel
    def intersection_check_nav(self):
        # print('IC', self.intersection_check_result[None])
        for i in ti.grouped(self.candidate_ao):
            env_id = self.candidate_ao[i][0]
            v_id = self.candidate_ao[i][1]
            p_id = self.candidate_ao[i][2]
            # print('vid:', v_id)
            # print('pid:', p_id)

            v0 = self.obstacle_v[v_id, 0]
            v1 = self.obstacle_v[v_id, 1]
            p = self.x[env_id, p_id]

            obsVec = v1 - v0
            agentVec = self.movement[env_id, p_id]

            RHS = v0 - p

            LHS = tm.mat2([agentVec[0], -obsVec[0]], [agentVec[1], -obsVec[1]])

            if LHS.determinant() > 1e-6:
                # print('xxxxxxxxxxxxxxxx')
                s = LHS.inverse() @ RHS
                # print(s)
                s0 = s[0]
                s1 = s[1]
                flag = int(0 <= s0 <= 1 and 0 <= s1 <= 1)
                #
                self.done[env_id, p_id] += flag
                self.collision_detected[env_id, p_id] += flag

    ##################
    # Change
    @ti.kernel
    def insert_x_pos(self, x: ti.f32, y: ti.f32, u: ti.f32, v: ti.f32):
        self.x[0, 0][0] = x
        self.x[0, 0][1] = y
        self.v[0, 0][0] = u
        self.v[0, 0][1] = v

    @ti.kernel
    def intersection_check_rvo(self):
        for i in range(self.n_ao[None]):
            v_id = self.candidate_ao[i][0]
            p_id = self.candidate_ao[i][1]
            # print('vid:', v_id)
            # print('pid:', p_id)

            v0 = self.obstacle_v[v_id, 0]
            v1 = self.obstacle_v[v_id, 1]
            p = self.x[p_id]

            obsVec = v1 - v0
            agentVec = self.new_v[p_id] * self.alpha[None] * self._rvo_time_horizon

            RHS = v0 - p

            LHS = tm.mat2([agentVec[0], -obsVec[0]], [agentVec[1], -obsVec[1]])

            if LHS.determinant() > 1e-6:
                # print('xxxxxxxxxxxxxxxx')
                s = LHS.inverse() @ RHS
                # print(s)
                s0 = s[0]
                s1 = s[1]
                self.intersection_check_result[None] += int(0 <= s0 <= 1 and 0 <= s1 <= 1)

    # end
    #############
