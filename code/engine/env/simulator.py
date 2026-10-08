import numpy as np

# from env.vessel_sim_agent_parallel import *
# from env.vessel_sim_env_parallel import *
import taichi as ti
import taichi.math as tm
import torch
from env.vessel_sim import Sim2Sea_Core


@ti.data_oriented
class Sim2Sea(Sim2Sea_Core):
    ###############################
    # MMG, Nomoto, and kinematic vessel solvers are implemented by Sim2Sea_Core.
    # this is used for managing various features encoding.
    ###############################
    # Structure: BEV Feature -- Agent-Agent Feature -- Agent-Obstacle Feature -- Functions
    ###############################
    # Initialization & reset: A-A pairs & feat encoding cases; O occupied hash grids
    # Simulation loop: insert actions --> core_step --> update A-O neighbours
    # --> A-A grad & feat & dones --> A-O grad & feat & dones --> BEV feat

    ###########################################
    # BEV Here!
    ###########################################
    @ti.kernel
    def clear_bev_buffers(self):
        for index, i, y, x in self.bev_buffer:
            # default -- white, default distance -- 1000 (making it far enough)
            self.bev_buffer[index, i, y, x] = ti.Vector([0.1, 0.1, 0.1, 1000.0])

    @ti.kernel
    def render_ships_to_buffer(self):
        for Id in ti.grouped(self.x):
            index, i = Id[0], Id[1]
            if self.active[index, i] == 1:
                center_x = self.x[Id][0]
                center_y = self.x[Id][1]

                for j in range(self.max_num):
                    if (
                        self.active[index, j] == 1
                        and tm.length(self.x[Id] - self.x[index, j]) <= self.bev_radius[None]
                    ):
                        rel_x = (
                            self.x[index, j][0] - center_x
                        ) * self.bev_scale + self.bev_size / 2
                        rel_y = (
                            self.x[index, j][1] - center_y
                        ) * self.bev_scale + self.bev_size / 2
                        ship_radius = ti.max(3.0, self.width[index, j] * self.bev_scale)

                        # bounding box
                        min_x = ti.max(0, ti.cast(rel_x - ship_radius, ti.i32))
                        max_x = ti.min(self.bev_size - 1, ti.cast(rel_x + ship_radius, ti.i32))
                        min_y = ti.max(0, ti.cast(rel_y - ship_radius, ti.i32))
                        max_y = ti.min(self.bev_size - 1, ti.cast(rel_y + ship_radius, ti.i32))

                        # colors
                        color = ti.Vector([0.0, 0.0, 0.0, 0.0])
                        if j == i:
                            color = ti.Vector([0.1, 0.9, 0.1, 0.5])  # self green
                        elif self.craft_camp[index, j] == 0:
                            color = ti.Vector([0.1, 0.1, 0.9, 1.0])  # 0 - blue
                        else:
                            color = ti.Vector([0.9, 0.1, 0.1, 1.0])  # 1 - red

                        # check pixels in bounding box
                        for y in range(min_y, max_y + 1):
                            for x in range(min_x, max_x + 1):
                                # pixel 2 ship position
                                dist_sq = (x - rel_x) ** 2 + (y - rel_y) ** 2

                                # if pixel in ship and nearer
                                if (
                                    dist_sq <= ship_radius**2
                                    and color[3] < self.bev_buffer[index, i, y, x][3]
                                ):
                                    self.bev_buffer[index, i, y, x] = color

    @ti.kernel
    def render_obstacles_to_buffer(self):
        for Id in ti.grouped(self.x):
            index, i = Id[0], Id[1]
            if self.active[index, i] == 1:
                center_x = self.x[Id][0]
                center_y = self.x[Id][1]

                for j in ti.static(range(self.max_surrounding_obstacle)):
                    k = self.obstacles_in_bev[Id][j]
                    if self.obstacles_in_bev[Id][j] != -1:
                        # vertices
                        v0 = self.obstacle_v[k, 0]
                        v1 = self.obstacle_v[k, 1]

                        # coord to pixel coords
                        p0x = (v0[0] - center_x) * self.bev_scale + self.bev_size / 2
                        p0y = (v0[1] - center_y) * self.bev_scale + self.bev_size / 2
                        p1x = (v1[0] - center_x) * self.bev_scale + self.bev_size / 2
                        p1y = (v1[1] - center_y) * self.bev_scale + self.bev_size / 2

                        # bounding box
                        min_x = ti.max(0, ti.cast(ti.min(p0x, p1x) - 2, ti.i32))
                        max_x = ti.min(self.bev_size - 1, ti.cast(ti.max(p0x, p1x) + 2, ti.i32))
                        min_y = ti.max(0, ti.cast(ti.min(p0y, p1y) - 2, ti.i32))
                        max_y = ti.min(self.bev_size - 1, ti.cast(ti.max(p0y, p1y) + 2, ti.i32))

                        color = ti.Vector([0.9, 0.3, 0.3, 2.5])
                        # print('line obs coords', min_x, min_y, max_x, max_y)
                        # pixels in bounding box
                        for y in range(min_y, max_y + 1):
                            for x in range(min_x, max_x + 1):
                                # dist from point to line
                                dist = self.return_distance(
                                    ti.Vector([p0x, p0y]), ti.Vector([p1x, p1y]), ti.Vector([x, y])
                                )

                                if dist <= 1:
                                    self.bev_buffer[index, i, y, x] = color
                                    # if index==0:
                                    # Debug: print distance, environment ID, and pixel color.

    @ti.kernel
    def finalize_bev_images(self):
        for index, i, y, x in self.bev_buffer:
            # buffer 2 image
            self.bev_images[index, i, y, x] = ti.Vector(
                [
                    self.bev_buffer[index, i, y, x][0],
                    self.bev_buffer[index, i, y, x][1],
                    self.bev_buffer[index, i, y, x][2],
                ]
            )

            # if self.bev_buffer[index, i, y, x][2] == 0.3 and index==0:
            # Debug: print line-obstacle pixel color.

            # Debug only: inspect non-empty BEV-buffer pixels.
            #     if index == 0:
            #         print(y, x)

    def generate_bev_images(self, merge=False, out_type="BHWC"):
        self.clear_bev_buffers()

        self.render_ships_to_buffer()
        self.render_obstacles_to_buffer()

        self.finalize_bev_images()

        # to torch tensors
        bev_tensor = self.bev_images.to_torch(device=self.device)

        # Rearrange to (B, C, H, W); channels first
        if out_type == "BHWC":
            if merge:
                batch_size = self.max_env * self.max_num
                bev_tensor = bev_tensor.reshape(batch_size, self.bev_size, self.bev_size, 3)
        elif out_type == "BCHW":
            if merge:
                batch_size = self.max_env * self.max_num
                bev_tensor = bev_tensor.reshape(batch_size, self.bev_size, self.bev_size, 3)
                bev_tensor = bev_tensor.permute(0, 3, 1, 2)
            else:
                bev_tensor = bev_tensor.permute(0, 1, 4, 2, 3)

        return bev_tensor

    #####################################################
    # Agent-Agent, not necessary for single agent env
    #####################################################

    def register_features(self):
        # query_pair saves the [n_teammate, n_opponent];
        # query_mat saves the id of each agent and another agent's <position> in obs feature
        self.obs_query_mat = ti.field(shape=(self.max_num, self.max_num), dtype=ti.i32)
        self.obs_query_pair = ti.field(shape=(self.max_num, 2), dtype=ti.i32)

        self.obs_turns_kernel()

    def register_pairs(self):
        self.pair_root = ti.root.dynamic(ti.i, int(self.max_env * (self.max_num**2)), chunk_size=32)
        self.collision_pair = ti.Vector.field(6, dtype=ti.i32)

        # Red/blue pairs represent opposing vessels; white pairs avoid collisions.
        # white pair means white and other ships avoid collisions between each other.

        self.pair_root.place(self.collision_pair)

        self.n_pair = ti.field(dtype=ti.i32, shape=())
        self.n_pair[None] = 0

        self.register_pairs_kernel()
        self.obs_turns_kernel()

    @ti.kernel
    # Register used only once
    def register_pairs_kernel(self):
        for index in range(self.max_env):
            for i in range(self.max_num):
                self.min_distance_pos[index, i] = ti.Vector(
                    [self.two_side_num[None][self.craft_camp[index, i]] - 1, self.max_num]
                )
                for j in range(self.max_num):
                    if j > i:
                        new_pair = ti.atomic_add(self.n_pair[None], 1)
                        # If same flag, 0 means teammate; else 1 means opponent.
                        flag = ti.select(
                            self.craft_camp[index, i] == self.craft_camp[index, j], 0, 1
                        )
                        # j's <position> in i's obs feature; and i's in j's
                        m = self.obs_query_mat[i, j]
                        n = self.obs_query_mat[j, i]

                        self.collision_pair[new_pair] = ti.Vector([index, i, j, flag, m, n])

    @ti.kernel
    def obs_turns_kernel(self):
        for i in range(self.max_num):
            for j in range(self.max_num):
                # Sequential!
                if ti.static(self.obs_case == 1):
                    if i != j:
                        # If same camp, no need to add
                        flag = ti.select(self.craft_camp[0, i] == self.craft_camp[0, j], 0, 1)
                        # Blue opponents follow teammates and the nearest teammate.
                        # [teammates, nearest_team, oppos, nearest_oppo]
                        number_to_add = self.two_side_num[None][self.craft_camp[0, i]]
                        number_to_add = number_to_add * flag

                        self.obs_query_mat[i, j] = self.obs_query_pair[i, flag] + number_to_add

                        self.obs_query_pair[i, flag] += 1
                else:
                    if i > j:
                        self.obs_query_mat[i, j] = j
                    elif i < j:
                        self.obs_query_mat[i, j] = j - 1

    def other_vessel_feat_encode(self):
        self.feat_encode_kernel()
        vessel_obs_tensor = self.obs.to_torch(device=self.device)
        if self.obs_case == 3:
            vessel_obs_tensor = self.select_nearest_k_torch(vessel_obs_tensor, k=self.nearest_num)

        return vessel_obs_tensor

    @ti.kernel
    def feat_encode_kernel(self):
        # gradAA implemented here!
        for p in range(self.n_pair[None]):
            vector = self.collision_pair[p]
            # print(vector)
            index, i, j, flag, m, n = (
                vector[0],
                vector[1],
                vector[2],
                vector[3],
                vector[4],
                vector[5],
            )

            x_1, x_2 = ti.Vector([0.0, 0.0]), ti.Vector([0.0, 0.0])
            if ti.static(self.solver_type == "mmg"):
                x_1 = ti.Vector([self.x[index, i][0], self.x[index, i][1]])
                x_2 = ti.Vector([self.x[index, j][0], self.x[index, j][1]])
            else:
                x_1, x_2 = self.x[index, i], self.x[index, j]

            if ti.static(self.use_ic):
                # IC grad
                margin = -((self.width[index, i] + self.width[index, j]) ** 2)
                ab, velr = ti.Vector([0.0, 0.0]), ti.Vector([0.0, 0.0])
                for coord in ti.static(range(2)):
                    ab[coord] = x_1[coord] - x_2[coord]
                    margin += ab[coord] ** 2

                d0 = self.searchR[None]

                if ti.static(self.vel_adj):
                    lvelr = tm.dot(velr, velr) * 1.0
                    d0 += lvelr

                if ti.static(self.debug) and margin <= 0.0:
                    print("Checked during gradAA: invalid margin", margin, "between", index, i, j)
                    self.done[index, i] += 1
                    self.done[index, j] += 1

                if margin < d0:
                    valLog = tm.log(margin / d0)
                    valLogC = valLog * (margin - d0)
                    relD = 1 - d0 / margin
                    D = -self.coef[None] * (2 * valLogC + (margin - d0) * relD)
                    grad_value = D * 2 * ab

                    self.gradient[index, i] += grad_value
                    self.gradient[index, j] -= grad_value

                    self.aa_gradient[index, i] += grad_value
                    self.aa_gradient[index, j] -= grad_value

            # Feat obs
            # distance, angle_a, angle_b = self.get_relative_position(x_1, x_2)
            # print(self.obs[index, i, 0])

            # IF case==0, only compute grad!
            if ti.static(self.obs_case == 1):
                # Feat obs
                distance, angle_a, angle_b = self.get_relative_position(x_1, x_2)
                # print(self.obs[index, i, 0])

                self.obs[index, i, m] = ti.Vector([distance, angle_a, self.psi[index, j]])
                self.obs[index, j, n] = ti.Vector([distance, angle_b, self.psi[index, i]])

                old_dist_1 = ti.atomic_min(self.min_distance[index, i][flag], distance)
                need_update_1 = ti.cast(distance < old_dist_1, ti.i32)
                self.obs[index, i, self.min_distance_pos[index, i][flag]] = ti.select(
                    need_update_1,
                    ti.Vector([distance, angle_a, self.psi[index, j]]),
                    self.obs[index, i, self.min_distance_pos[index, i][flag]],
                )

                old_dist_2 = ti.atomic_min(self.min_distance[index, j][flag], distance)
                need_update_2 = ti.cast(distance < old_dist_2, ti.i32)
                self.obs[index, j, self.min_distance_pos[index, j][flag]] = ti.select(
                    need_update_2,
                    ti.Vector([distance, angle_b, self.psi[index, i]]),
                    self.obs[index, j, self.min_distance_pos[index, j][flag]],
                )

            if ti.static(self.obs_case == 2 or self.obs_case == 3):
                # Feat obs
                distance, angle_a, angle_b = self.get_relative_position(x_1, x_2)
                # print(self.obs[index, i, 0])

                self.obs[index, i, m] = ti.Vector([distance, angle_a, self.psi[index, j]])
                self.obs[index, j, n] = ti.Vector([distance, angle_b, self.psi[index, i]])

    def select_nearest_k_torch(self, x_in, k=3):
        # x shape: (M, n, n-1, 3)
        _, sorted_idx = torch.sort(x_in[..., 0], dim=2)
        nearest_k_idx = sorted_idx[:, :, :k]

        M, n, _, _ = x_in.shape
        batch_idx = torch.arange(M, device=x_in.device).view(-1, 1, 1).expand(-1, n, k)
        agent_idx = torch.arange(n, device=x_in.device).view(1, -1, 1).expand(M, -1, k)
        return x_in[batch_idx, agent_idx, nearest_k_idx, :]

    ###########################################
    # Agent - Obstacles, supporting single agent & multi-agents
    ###########################################

    def setup_line_obstacles(self, input_list):
        """
        preprocess it in python scope
        Input of the vertices should be like:
        [[[x1, y1],
          [x2, y2],
          ```
          ], ```
          ]

        """
        array_list = []
        array_num = len(input_list)
        for i in range(array_num):
            sliced_array = input_list[i]
            node_num = len(sliced_array)
            for j in range(node_num):
                if j != node_num - 1:
                    array_list.append([sliced_array[j], sliced_array[j + 1]])
                else:
                    array_list.append([sliced_array[j], sliced_array[0]])

        self.n_obstacles = ti.field(ti.i32, shape=())
        vertice_num = len(array_list)
        self.n_obstacles[None] = vertice_num
        print(self.n_obstacles[None])

        # Batch-write obstacles via NumPy to avoid slow per-line Taichi writes.
        np_dtype = np.float32 if self.ctype == ti.f32 else np.float64
        # obstacle_arr shape: (vertice_num, 2, 2)
        #   obstacle_arr[k, 0, :] = [start_x, start_y]
        #   obstacle_arr[k, 1, :] = [end_x, end_y]
        if vertice_num > 0:
            obstacle_arr = np.array(array_list, dtype=np_dtype)
        else:
            obstacle_arr = np.zeros((vertice_num, self.dim, self.dim), dtype=np_dtype)
        self.start_np = obstacle_arr[:, 0, :].copy()
        self.end_np = obstacle_arr[:, 1, :].copy()
        # These two numpy arrays are for rendering in taichi gui

        self.obstacle_v = ti.Vector.field(self.dim, dtype=self.ctype)
        ti.root.dense(ti.ij, (vertice_num, self.dim)).place(self.obstacle_v)
        self.obstacle_v.from_numpy(obstacle_arr)
        # the cell in obstacle_v should be a vector of the coordinate of vertices,
        # shape of it should be [n_lines, 2-dim]

        self.start_np /= self.res[0]
        self.end_np /= self.res[0]

        self.setup_ao_grid_gpu()

        self.init_obstacle_grid()

    def setup_ao_grid_gpu(self):
        # Whenever add agents, reset grid
        # ao means agent-obstacle
        self.n_ao = ti.field(dtype=ti.i32, shape=(self.max_env,))
        # self.ao_gridCount = ti.field(dtype=ti.i32)
        # self.ao_grid = ti.field(dtype=ti.i32)

        self.maxAOPair = 8 * self.n_obstacles[None]

        self.candidate_ao = ti.Vector.field(3, dtype=ti.i32)
        ti.root.dense(ti.i, self.max_env).dynamic(ti.j, self.maxAOPair).place(self.candidate_ao)

        # Hash grids for ao
        # self.occupied_indexes = ti.field(ti.i32)

        self.ao_gridCount = ti.field(dtype=ti.i32, shape=(self.hash_num[None],))
        self.ao_grid = ti.field(dtype=ti.i32, shape=(self.hash_num[None], self.n_obstacles[None]))
        self.ao_gridCount.fill(0)
        self.ao_grid.fill(-1)

    @ti.kernel
    def init_obstacle_grid(self):
        # Test each grid midpoint between the line endpoints.
        # The grid is occupied within searchR plus half a grid length.
        # by the obstacle
        valid_distance = self.searchR[None] + 0.7 * self.GridR[None]
        # print('valid_dis', valid_distance)
        for i in range(self.n_obstacles[None]):
            # i is the index of the lines
            v0 = self.obstacle_v[i, 0]
            v1 = self.obstacle_v[i, 1]
            indexV0 = ti.cast(v0 * self.invGridR[None], ti.i32)
            indexV1 = ti.cast(v1 * self.invGridR[None], ti.i32)

            v0x, v0y = indexV0[0], indexV0[1]
            v1x, v1y = indexV1[0], indexV1[1]

            x_min = ti.min(v0x, v1x)
            y_min = ti.min(v0y, v1y)

            x_max = ti.max(v0x, v1x)
            y_max = ti.max(v0y, v1y)

            # print("iiiii", i, indexV0, indexV1)

            for m in range(x_min - 1, x_max + 2):
                for n in range(y_min - 1, y_max + 2):
                    vmx = (ti.cast(m, self.ctype) + 0.5) * self.GridR[None]
                    vmy = (ti.cast(n, self.ctype) + 0.5) * self.GridR[None]

                    indexM = ti.Vector([m, n])

                    middle_point = ti.Vector([vmx, vmy])
                    distance = self.return_distance(v0, v1, middle_point)
                    # print('ith_dis', i, distance)

                    if distance < valid_distance:
                        hash_index = self.get_cell_hash(indexM)
                        old = ti.atomic_add(self.ao_gridCount[hash_index], 1)
                        # print('count', i, self.ao_gridCount[hash_index])
                        self.ao_grid[hash_index, old] = i
                        # self.occupied_indexes[k].append(hash_index)

    @ti.kernel
    def init_ao_grid(self):
        self.ao_grid.fill(-1)
        self.ao_gridCount.fill(0)

    # We suppose the agents in the environments are always fewer than line obstacles
    # So we suggest to search candidate collison pairs by searching near the agents

    @ti.kernel
    def find_ao_neighbour_by_agent(self):
        self.n_ao.fill(0)
        self.obstacles_in_bev.fill(-1)
        for i in ti.grouped(self.x):
            env_id, p_id = i[0], i[1]
            indexV = ti.cast(self.x[i].xy * self.invGridR[None], ti.i32)
            # print('indexV', indexV, 'envid', env_id, 'p_id', p_id)
            cumulated_obs_count = 0
            for offset in ti.static(ti.grouped(self.stencil_range())):
                hash_index_v = self.get_cell_hash(indexV + offset)
                # print(f'{indexV + offset}, {hash_index_v}')
                k = 0

                while k < self.ao_gridCount[hash_index_v]:
                    v_id = self.ao_grid[hash_index_v, k]
                    count = 0
                    # for s in range(self.n_ao[None]):
                    for s in ti.static(range(self.max_surrounding_obstacle)):
                        flag = ti.select((v_id == self.obstacles_in_bev[i][s]), 1, 0)
                        count += flag
                        # print('finding',flag, count, v_id)

                    # count == 0, means no duplicate obstacles
                    if count == 0:
                        new_pair = ti.atomic_add(self.n_ao[env_id], 1)
                        self.candidate_ao[env_id, new_pair] = ti.Vector([env_id, v_id, p_id])
                        self.obstacles_in_bev[i][cumulated_obs_count] = v_id
                        # self.registed_ob[new_pair] = v_id
                        cumulated_obs_count += 1
                        #################################
                        # Once tested, no need to print 'exceed'
                        # if cumulated_obs_count > self.max_surrounding_obstacle:
                        #     print('ao_grid exceeding self.max_surrounding_obstacle')
                        cumulated_obs_count = ti.min(
                            cumulated_obs_count, (self.max_surrounding_obstacle - 1)
                        )
                    k += 1

            # if ti.static(self.use_bev):
            #     self.obstacles_in_bev[i] = max_obs_tempora

    @ti.kernel
    def compute_gradAO(self):
        for i in ti.grouped(self.candidate_ao):
            # index: env_id
            index = self.candidate_ao[i][0]
            v_id = self.candidate_ao[i][1]
            p_id = self.candidate_ao[i][2]
            # print('vid:', v_id)
            # print('pid:', p_id)

            v0 = self.obstacle_v[v_id, 0]
            v1 = self.obstacle_v[v_id, 1]
            p = self.x[index, p_id].xy
            radsq = self.width[index, p_id] ** 2

            obsVec = v1 - v0
            relpos0 = v0 - p
            relpos1 = v1 - p

            lensq = obsVec.dot(obsVec)
            if lensq < 0.1:
                print("small lensq:", lensq)
            s = -relpos0.dot(obsVec) / lensq

            d0 = self.searchR[None]
            if ti.static(self.vel_adj):
                vel_add = tm.dot(self.v[index, p_id], self.v[index, p_id])
                d0 += vel_add

            if s < 0.0:
                dsitsq0 = relpos0.dot(relpos0)
                if dsitsq0 < radsq + d0:
                    E, D = self.clog(dsitsq0 - radsq, d0)
                    value = D * 2 * relpos0
                    self.gradient[index, p_id] -= value
                    self.ao_gradient[index, p_id] -= value
            elif s > 1.0:
                dsitsq1 = relpos1.dot(relpos1)
                if dsitsq1 < radsq + d0:
                    E, D = self.clog(dsitsq1 - radsq, d0)
                    value = D * 2 * relpos1
                    self.gradient[index, p_id] -= value
                    self.ao_gradient[index, p_id] -= value
            else:
                v = ti.Vector([-obsVec.y, obsVec.x]) / tm.sqrt(lensq)
                dist = relpos0.dot(v)
                # print('dist:', dist)
                distsq = dist**2
                if distsq < radsq + d0:
                    E, D = self.clog(distsq - radsq, d0)
                    # print("D:", D)
                    value = D * 2 * v
                    self.gradient[index, p_id] -= value
                    self.ao_gradient[index, p_id] -= value

    @ti.kernel
    def intersection_check(self):
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
                # Add done here

    #######################################
    # Functions
    #######################################

    @ti.func
    def return_projection_point(self, v0, v1, p):
        # normal point to outer:
        # for example: start(0,0) end (3,0), normal:[0, 1]
        # projection is weighted, for example ,if in line, 0<projection<1
        d = v1 - v0
        # v = ti.Vector([-d.y, d.x]) / tm.length(d)
        projection = (p - v0).dot(d) / (d.dot(d) + 1e-5)
        return d, projection

    @ti.func
    def return_distance(self, v0, v1, p):
        d = v1 - v0
        if ti.static(self.debug) and d.dot(d) < 0.1:
            print("small dodtd", d.dot(d), v0, v1)
        # v = ti.Vector([-d.y, d.x]) / tm.length(d)
        projection = (p - v0).dot(d) / (d.dot(d) + 1e-5)
        p_point = v0 + projection * d
        return tm.length(p - p_point)

    @ti.func
    def get_cell_hash(self, a):
        p1 = 73856093 * a.x
        p2 = 19349663 * a.y

        return ((p1 ^ p2) % self.hash_num[None] + self.hash_num[None]) % self.hash_num[None]

    @ti.func
    def stencil_range(self):
        # return ti.ndrange(*((-self.stencil_grids, self.stencil_grids + 1) * self.dim))
        return ti.ndrange(*((self.stencil_grids * 2 + 1,) * self.dim))

    @ti.kernel
    def init_grad(self):
        # Given x and v, calculate E
        # for i in range(self.n_crafts[None]):
        for Id in ti.grouped(self.active_agents):
            i = self.active_agents[Id]
            Id[0]
            # print(Id, i)

            XX = 0.0
            for j in ti.static(ti.ndrange(self.dim)):
                self.gradient[i][j] = -self.v[i][j] / self.dt[None]
                XX += (-self.v[i][j] / self.dt[None]) ** 2

            XX / (2.0 * self.dt[None] * self.dt[None])
            # self.prev_global_E[env_id] += dE

    @ti.func
    def get_relative_position(self, x_a, x_b):
        rel_vector = x_a - x_b
        distance = tm.length(rel_vector)
        angle_b = tm.atan2(rel_vector[1], rel_vector[0])
        angle_a = tm.atan2(-rel_vector[1], -rel_vector[0])

        return distance, angle_a, angle_b

    @ti.func
    def clog(self, d, d0):
        if ti.static(self.debug) and d < 0:
            print("invalid d", d)
        valLog = tm.log(d / d0)
        valLogC = valLog * (d - d0)
        relD = (d - d0) / d

        D = -self.coef[None] * (2 * valLogC + (d - d0) * relD)
        E = -valLogC * (d - d0) * self.coef[None]

        return E, D

    @ti.func
    def clog_E(self, d, d0):
        valLog = tm.log(d / d0)
        valLogC = valLog * (d - d0)

        E = -valLogC * (d - d0) * self.coef[None]

        return E

    ##########################################
    # Encoding other vessels' features
    ##########################################

    @ti.kernel
    def store_old_x(self):
        for i in ti.grouped(self.x):
            self.old_x[i] = self.x[i]
            self.reward[i] = 0.0
            self.min_distance[i].fill(1000.0)
        if ti.static(self.obs_case != -1):
            self.gradient.fill(0.0)
            self.aa_gradient.fill(0.0)
            self.ao_gradient.fill(0.0)

    def init_env_test(self, poses, vels, craft_camps, widths, angel_lims):
        self.core_init(poses, vels, craft_camps, widths, angel_lims)
        self.register_features()
        self.register_pairs()

    def reset_env_test(self):
        self.core_reset()
        self.find_ao_neighbour_by_agent()
        self.feat_encode_kernel()
        obs_tensor = self.obs.to_torch(device=self.device)
        bevs = self.generate_bev_images() if self.use_bev else None
        return obs_tensor, bevs

    def step_env_test(self, actions):
        self.store_old_x()
        self.core_step(actions)
        # print(self.obs[0, 0, 0])
        self.find_ao_neighbour_by_agent()
        self.feat_encode_kernel()
        self.intersection_check()
        # self.format_reward_done_kernel()

        obs_tensor = self.obs.to_torch(device=self.device)
        bevs = self.generate_bev_images() if self.use_bev else None
        # print(obs_tensor.shape)
        reward_tensor = self.reward.to_torch(device=self.device)
        # print(reward_tensor.shape)
        done = None

        return obs_tensor, bevs, reward_tensor, done, None
