import numpy as np
import taichi as ti
import taichi.math as tm
from env.MMG_dataclass_f32 import Vessel32
from env.MMG_dataclass_f64 import Vessel64

# ti.init()


@ti.data_oriented
class Sim2Sea_Core:
    def __init__(
        self,
        args,
    ):

        self.manual_calibrated = args.manual_calibrated
        self.device = args.device
        self.stencil_grids = args.stencil_grids
        # for obs_case 3, selecting k nearest agents
        self.nearest_num = args.nearest_num

        self.res = ti.Vector([args.res[0], args.res[1]])
        self.have_wind = args.have_wind

        self.dim = 2

        self.solver_type = args.solver_type
        self.obs_case = args.obs_case
        self.substeps = args.substeps
        self.debug = args.debug

        self.randomization = args.randomization

        self.ra = 6378140.0
        self.rb = 6356755.0

        self.lon_per_degree = 111319.55 / 10.0
        self.lat_per_degree = 110946.30 / 10.0

        self.n_crafts = ti.field(ti.i32, shape=())

        self.control_freq = args.control_freq

        self.max_num = args.max_num
        self.max_env = args.max_env

        self.ctype = ti.f32
        if args.type == "f32":
            self.ctype = ti.f32
        elif args.type == "f64":
            self.ctype = ti.f64

        # If use implicit crowd algorithm
        self.use_ic = args.use_ic
        self.use_bev = args.use_bev

        # self.red_num = ti.field(ti.i32, shape=())
        # self.blue_num = ti.field(ti.i32, shape=())
        self.two_side_num = ti.Vector.field(2, dtype=ti.i32, shape=())
        self.dt = ti.field(self.ctype, shape=())
        self.substeps_float = ti.field(self.ctype, shape=())

        # Numbers of red and blue, blue=0, red=1, used for feature encoding ()
        if self.obs_case == 1:
            self.two_side_num[None] = ti.Vector([args.blue_num, args.red_num])
        # self.red_num[None] = red_num
        # self.blue_num[None] = blue_num

        self.dt[None] = float(1.0 / (args.control_freq * args.substeps))

        # self.substeps_float = ti.field(dtype=self.ctype, shape=())
        self.substeps_float[None] = args.substeps

        self.fl_psi = ti.field(shape=(), dtype=self.ctype)
        self.fl_vel = ti.field(shape=(), dtype=self.ctype)
        self.w_vel = ti.field(shape=(), dtype=self.ctype)
        self.beta_w = ti.field(shape=(), dtype=self.ctype)
        self.reward_correction = ti.field(shape=(), dtype=self.ctype)
        self.target = ti.Vector.field(2, dtype=self.ctype, shape=(self.max_env,))

        self.fl_psi[None] = 0.0
        self.fl_vel[None] = 0.0
        self.w_vel[None] = 0.0
        self.beta_w[None] = 0.0
        self.reward_correction[None] = args.reward_correction
        for i in range(self.max_env):
            self.target[i] = ti.Vector([args.target[0], args.target[1]])

        self.craft_camp = ti.field(dtype=ti.i32)
        ti.root.dense(ti.i, args.max_env).dense(ti.j, args.max_num).place(self.craft_camp)

        if self.use_bev:
            self.setup_bev()
        self.max_surrounding_obstacle = 16
        self.obstacles_in_bev = ti.Vector.field(
            self.max_surrounding_obstacle, dtype=ti.i32, shape=(self.max_env, self.max_num)
        )

        #!!!!!!!!!
        # YOU MUST PUT THESE ROOT AFTER [None]s AND BEFORE ti.dataclass.field!!!
        self.n_env = ti.root.dense(ti.i, self.max_env)
        self.crafts = self.n_env.dense(ti.j, self.max_num)
        # self.crafts = ti.root.dense(ti.j, self.max_num).dense(ti.i, self.max_env)
        # self.obs_root = self.crafts.dense(ti.k, self.max_num + 1)
        obs_num = max(self.max_num - 1, 1)
        if self.obs_case == 1:
            obs_num = self.max_num + 1

        self.obs_root = self.crafts.dense(ti.k, obs_num)
        self.obs = ti.Vector.field(3, dtype=self.ctype)
        self.obs_root.place(self.obs)

        if ti.static(self.solver_type == "mmg"):
            if args.type == "f32":
                self.vessel = Vessel32.field(layout=ti.Layout.AOS)
            else:
                self.vessel = Vessel64.field(layout=ti.Layout.AOS)

        if ti.static(self.solver_type == "mmg"):
            self.x = ti.Vector.field(3, dtype=self.ctype)
            self.movement = ti.Vector.field(3, dtype=self.ctype)
            self.old_x = ti.Vector.field(3, dtype=self.ctype)
            self.v = ti.Vector.field(3, dtype=self.ctype)
            self.nps = ti.field(dtype=self.ctype)
            self.delta = ti.field(dtype=self.ctype)
            self.psi = ti.field(dtype=self.ctype)
            self.width = ti.field(dtype=self.ctype)
            self.reward = ti.field(dtype=self.ctype)
            self.des_ang = ti.field(dtype=self.ctype)
            self.done = ti.field(dtype=ti.i32)
            self.active = ti.field(dtype=ti.i32)
            # self.craft_camp = ti.field(dtype=ti.i32)
            # SoA for x (pairs computation)
            # self.crafts.place(self.craft_camp, self.width)
            # self.crafts.place(self.craft_camp, self.width, self.x)
            # AoS for others (internal computation)
            self.crafts.place(
                self.active,
                self.width,
                self.old_x,
                self.movement,
                self.x,
                self.reward,
                self.des_ang,
                self.vessel,
                self.v,
                self.nps,
                self.delta,
                self.psi,
                self.done,
            )
            # self.crafts.place(self.craft_camp, self.width)
        elif ti.static(self.solver_type == "nomoto"):
            self.x = ti.Vector.field(3, dtype=self.ctype)
            self.movement = ti.Vector.field(3, dtype=self.ctype)
            self.old_x = ti.Vector.field(3, dtype=self.ctype)
            self.v = ti.Vector.field(3, dtype=self.ctype)
            self.width = ti.field(dtype=self.ctype)
            self.reward = ti.field(dtype=self.ctype)
            self.des_ang = ti.field(dtype=self.ctype)
            self.psi = ti.field(dtype=self.ctype)
            self.done = ti.field(dtype=ti.i32)
            self.active = ti.field(dtype=ti.i32)
            self.nomoto_K = ti.field(dtype=self.ctype)
            self.nomoto_T = ti.field(dtype=self.ctype)
            self.delta = ti.field(dtype=self.ctype)
            self.speed_cmd = ti.field(dtype=self.ctype)
            self.crafts.place(
                self.active,
                self.width,
                self.old_x,
                self.movement,
                self.x,
                self.psi,
                self.reward,
                self.des_ang,
                self.done,
                self.v,
                self.nomoto_K,
                self.nomoto_T,
                self.delta,
                self.speed_cmd,
            )
        else:
            self.x = ti.Vector.field(2, dtype=self.ctype)
            self.movement = ti.Vector.field(2, dtype=self.ctype)
            self.old_x = ti.Vector.field(2, dtype=self.ctype)
            self.v = ti.Vector.field(2, dtype=self.ctype)
            self.v_2_change = ti.Vector.field(2, dtype=self.ctype)
            self.v_max = ti.field(dtype=self.ctype)
            self.angular_v = ti.field(dtype=self.ctype)
            self.rot_ang = ti.field(dtype=self.ctype)
            self.angle_limit = ti.field(dtype=self.ctype)
            self.psi = ti.field(dtype=self.ctype)
            self.width = ti.field(dtype=self.ctype)
            self.reward = ti.field(dtype=self.ctype)
            self.des_ang = ti.field(dtype=self.ctype)
            self.done = ti.field(dtype=ti.i32)
            self.active = ti.field(dtype=ti.i32)
            # self.craft_camp = ti.field(dtype=ti.i32)
            self.crafts.place(
                self.active,
                self.old_x,
                self.movement,
                self.x,
                self.reward,
                self.des_ang,
                self.v,
                self.v_2_change,
                self.v_max,
                self.width,
                self.angular_v,
                self.rot_ang,
                self.psi,
                self.angle_limit,
                self.done,
            )

        if self.use_ic:
            self.gradient = ti.Vector.field(2, dtype=self.ctype)
            self.aa_gradient = ti.Vector.field(2, dtype=self.ctype)
            self.ao_gradient = ti.Vector.field(2, dtype=self.ctype)
            self.crafts.place(self.gradient, self.aa_gradient, self.ao_gradient)
        self.min_distance = ti.Vector.field(2, dtype=self.ctype)
        # self.nearest_oppo = ti.field(dtype=self.ctype)
        self.min_distance_pos = ti.Vector.field(2, dtype=ti.i32)
        self.crafts.place(self.min_distance, self.min_distance_pos)

        if self.use_ic:
            # self.max_num = args.max_num

            x_grids = ti.floor(self.res[0] / args.GridR) + 1
            y_grids = ti.floor(self.res[1] / args.GridR) + 1
            self.n_grid = x_grids * y_grids

            self.coef = ti.field(self.ctype, shape=())
            self.coef[None] = args.coef
            self.vel_adj = False

            self.searchR = ti.field(self.ctype, shape=())
            self.searchR[None] = args.searchR

            self.GridR = ti.field(self.ctype, shape=())
            self.GridR[None] = args.GridR

            self.invGridR = ti.field(self.ctype, shape=())
            self.invGridR[None] = 1.0 / args.GridR

            # Max len of hash indexes
            self.hash_num = ti.field(ti.i32, shape=())
            self.hash_num[None] = int(self.n_grid / 2)

            S = self.n_env.dynamic(ti.j, self.max_num, chunk_size=None)
            self.active_agents = ti.field(int)
            S.place(self.active_agents)

        if self.solver_type == "mmg":
            self.params = {
                "rho": ti.field(dtype=self.ctype, shape=()),  # Water density
                "rho_air": ti.field(dtype=self.ctype, shape=()),  # Air density
                "C_b": ti.field(dtype=self.ctype, shape=()),  # Block Coefficient
                "Lpp": ti.field(dtype=self.ctype, shape=()),  # Length over perpendiculars (m)
                "B": ti.field(dtype=self.ctype, shape=()),  # Overall width
                "displ": ti.field(dtype=self.ctype, shape=()),  # Displacement in [m³]
                "w_P0": ti.field(dtype=self.ctype, shape=()),  # Assumed wake fraction coefficient
                "J_int": ti.field(
                    dtype=self.ctype, shape=()
                ),  # Intercept for the calculation of K_T
                "J_slo": ti.field(dtype=self.ctype, shape=()),  # Slope for the calculation of K_T
                "x_G": ti.field(
                    dtype=self.ctype, shape=()
                ),  # X-Coordinate of the center of gravity (m)
                "x_P": ti.field(
                    dtype=self.ctype, shape=()
                ),  # X-Coordinate of the propeller (-0.5*Lpp)
                "D_p": ti.field(dtype=self.ctype, shape=()),  # Diameter of propeller (m)
                "k_0": ti.field(dtype=self.ctype, shape=()),  # Propeller open water coefficients.
                "k_1": ti.field(dtype=self.ctype, shape=()),
                "k_2": ti.field(dtype=self.ctype, shape=()),
                "C_1": ti.field(dtype=self.ctype, shape=()),
                "C_2_plus": ti.field(dtype=self.ctype, shape=()),
                "C_2_minus": ti.field(dtype=self.ctype, shape=()),
                "l_R": ti.field(
                    dtype=self.ctype, shape=()
                ),  # correction of flow straightening factor to yaw-rate
                "gamma_R": ti.field(dtype=self.ctype, shape=()),
                "gamma_R_plus": ti.field(dtype=self.ctype, shape=()),
                # Flow straightening coefficient for positive rudder anglesSDK
                "gamma_R_minus": ti.field(dtype=self.ctype, shape=()),
                # Flow straightening coefficient for negative rudder angles
                "eta": ti.field(
                    dtype=self.ctype, shape=()
                ),  # Ratio of propeller diameter to rudder span
                "kappa": ti.field(
                    dtype=self.ctype, shape=()
                ),  # An experimental constant for expressing "u_R"
                "A_R": ti.field(dtype=self.ctype, shape=()),  # Moveable rudder area
                "epsilon": ti.field(dtype=self.ctype, shape=()),
                # Ratio of wake fraction at propeller and rudder positions
                "f_alpha": ti.field(dtype=self.ctype, shape=()),
                # Rudder lift gradient coefficient (assumed rudder aspect ratio = 2)
                "A_Fw": ti.field(dtype=self.ctype, shape=()),  # Frontal wind area [m²]
                "A_Lw": ti.field(dtype=self.ctype, shape=()),  # Lateral wind area [m²]
                "t_R": ti.field(dtype=self.ctype, shape=()),  # Steering-resistance factor
                "t_P": ti.field(dtype=self.ctype, shape=()),  # Thrust deduction factor
                "x_H_dash": ti.field(dtype=self.ctype, shape=()),
                # Longitudinal coordinate of acting point of the additional lateral force
                "d": ti.field(dtype=self.ctype, shape=()),  # Ship draft (Tiefgang)
                "m_x_dash": ti.field(dtype=self.ctype, shape=()),
                # Non dimensionalized added masses coefficient in x direction
                "m_y_dash": ti.field(dtype=self.ctype, shape=()),
                # Non dimensionalized added masses coefficient in y direction
                "R_0_dash": ti.field(
                    dtype=self.ctype, shape=()
                ),  # frictional resistance coefficient
                "X_vv_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "X_vr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "X_rr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "X_vvvv_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "Y_v_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "Y_r_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "Y_vvv_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "Y_vvr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "Y_vrr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "Y_rrr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "N_v_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "N_r_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "N_vvv_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "N_vvr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "N_vrr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "N_rrr_dash": ti.field(dtype=self.ctype, shape=()),  # Hull derivatives
                "J_z_dash": ti.field(
                    dtype=self.ctype, shape=()
                ),  # Added moment of inertia coefficient
                "a_H": ti.field(dtype=self.ctype, shape=()),  # Rudder force increase factor
                "delta_prop": ti.field(
                    dtype=self.ctype, shape=()
                ),  # Additional propeller parameter
            }

    @ti.kernel
    def set_nomoto_params(self, K: ti.f32, T: ti.f32):
        for index in ti.grouped(self.x):
            self.nomoto_K[index] = K
            self.nomoto_T[index] = T

    @ti.kernel
    def update_water_wind_status(
        self, fl_vel: ti.f32, w_vel: ti.f32, fl_psi: ti.f32, beta_w: ti.f32
    ):
        self.fl_vel[None] = fl_vel
        self.fl_psi[None] = fl_psi
        self.w_vel[None] = w_vel
        self.beta_w[None] = beta_w

    def setup_bev(self, bev_size=224, bev_R=10.0):
        self.bev_size = bev_size
        self.bev_radius = ti.field(dtype=self.ctype, shape=())
        self.bev_radius[None] = bev_R  # can set to searchR

        self.bev_scale = self.bev_size / 2 / self.bev_radius[None]

        # bev map
        self.bev_images = ti.Vector.field(
            3, dtype=ti.f32, shape=(self.max_env, self.max_num, bev_size, bev_size)
        )

        # buffer, including depth
        self.bev_buffer = ti.Vector.field(
            4, dtype=ti.f32, shape=(self.max_env, self.max_num, bev_size, bev_size)
        )

    @ti.func
    def rot_psi(self, psi):
        mat = tm.mat3(
            [tm.cos(psi), -tm.sin(psi), 0.0], [tm.sin(psi), tm.cos(psi), 0.0], [0.0, 0.0, 1.0]
        )
        return mat

    @ti.func
    def rot_psi_2d(self, psi):
        mat = tm.mat2([tm.cos(psi), -tm.sin(psi)], [tm.sin(psi), tm.cos(psi)])
        return mat

    #####################################################################
    # Initializing
    def load_vessel_params(self, dict):
        if self.solver_type == "mmg":
            self.set_params_from_dict(dict)
            self.load_params_to_crafts()
        elif self.solver_type == "nomoto":
            K = 0.185
            T = 100
            for key, value in dict.items():
                if key == "nomoto_K":
                    K = float(value)
                if key == "nomoto_T":
                    T = float(value)
            self.set_nomoto_params(K, T)
        else:
            pass

    def set_params_from_dict(self, dict):
        # print('dict', dict)
        print("=============Loading MMG Params=============")
        print(f"If manual calibrated: {self.manual_calibrated}")
        for key, value in dict.items():
            # print('ini_loading: ', key, value)
            # if hasattr(self.params, key):
            print(key, value)
            self.params[key][None] = value

    @ti.kernel
    def load_params_to_crafts(self):
        # loading to (env, agents)
        if ti.static(self.solver_type == "mmg" and not self.manual_calibrated):
            for index in ti.grouped(self.vessel):
                self.vessel[index].rho = self.params["rho"][None]
                self.vessel[index].rho_air = self.params["rho_air"][None]
                self.vessel[index].C_b = self.params["C_b"][None]
                self.vessel[index].Lpp = self.params["Lpp"][None]
                self.vessel[index].B = self.params["B"][None]
                self.vessel[index].displ = self.params["displ"][None]
                self.vessel[index].w_P0 = self.params["w_P0"][None]
                self.vessel[index].J_int = self.params["J_int"][None]
                self.vessel[index].J_slo = self.params["J_slo"][None]
                self.vessel[index].x_G = self.params["x_G"][None]
                self.vessel[index].x_P = self.params["x_P"][None]
                self.vessel[index].D_p = self.params["D_p"][None]
                self.vessel[index].k_0 = self.params["k_0"][None]
                self.vessel[index].k_1 = self.params["k_1"][None]
                self.vessel[index].k_2 = self.params["k_2"][None]
                self.vessel[index].C_1 = self.params["C_1"][None]
                self.vessel[index].C_2_plus = self.params["C_2_plus"][None]
                self.vessel[index].C_2_minus = self.params["C_2_minus"][None]
                self.vessel[index].l_R = self.params["l_R"][None]
                self.vessel[index].gamma_R_plus = self.params["gamma_R_plus"][None]
                self.vessel[index].gamma_R_minus = self.params["gamma_R_minus"][None]
                self.vessel[index].eta = self.params["eta"][None]
                self.vessel[index].kappa = self.params["kappa"][None]
                self.vessel[index].A_R = self.params["A_R"][None]
                # self.vessel[index].A_R_Ld_em = self.params['A_R_Ld_em'][None]
                self.vessel[index].epsilon = self.params["epsilon"][None]
                self.vessel[index].f_alpha = self.params["f_alpha"][None]
                self.vessel[index].A_Fw = self.params["A_Fw"][None]
                self.vessel[index].A_Lw = self.params["A_Lw"][None]
                self.vessel[index].t_R = self.params["t_R"][None]
                self.vessel[index].t_P = self.params["t_P"][None]
                self.vessel[index].x_H_dash = self.params["x_H_dash"][None]
                self.vessel[index].d = self.params["d"][None]
                self.vessel[index].m_x_dash = self.params["m_x_dash"][None]
                self.vessel[index].m_y_dash = self.params["m_y_dash"][None]
                self.vessel[index].R_0_dash = self.params["R_0_dash"][None]
                self.vessel[index].X_vv_dash = self.params["X_vv_dash"][None]
                self.vessel[index].X_vr_dash = self.params["X_vr_dash"][None]
                self.vessel[index].X_rr_dash = self.params["X_rr_dash"][None]
                self.vessel[index].X_vvvv_dash = self.params["X_vvvv_dash"][None]
                self.vessel[index].Y_v_dash = self.params["Y_v_dash"][None]
                self.vessel[index].Y_r_dash = self.params["Y_r_dash"][None]
                self.vessel[index].Y_vvv_dash = self.params["Y_vvv_dash"][None]
                self.vessel[index].Y_vvr_dash = self.params["Y_vvr_dash"][None]
                self.vessel[index].Y_vrr_dash = self.params["Y_vrr_dash"][None]
                self.vessel[index].Y_rrr_dash = self.params["Y_rrr_dash"][None]
                self.vessel[index].N_v_dash = self.params["N_v_dash"][None]
                self.vessel[index].N_r_dash = self.params["N_r_dash"][None]
                self.vessel[index].N_vvv_dash = self.params["N_vvv_dash"][None]
                self.vessel[index].N_vvr_dash = self.params["N_vvr_dash"][None]
                self.vessel[index].N_vrr_dash = self.params["N_vrr_dash"][None]
                self.vessel[index].N_rrr_dash = self.params["N_rrr_dash"][None]
                self.vessel[index].J_z_dash = self.params["J_z_dash"][None]
                self.vessel[index].a_H = self.params["a_H"][None]
                self.vessel[index].delta_prop = self.params["delta_prop"][None]
                # Added masses and moment of inertia
                m_x = self.vessel[index].m_x_dash * (
                    0.5
                    * self.vessel[index].rho
                    * (self.vessel[index].Lpp ** 2)
                    * self.vessel[index].d
                )
                m_y = self.vessel[index].m_y_dash * (
                    0.5
                    * self.vessel[index].rho
                    * (self.vessel[index].Lpp ** 2)
                    * self.vessel[index].d
                )
                J_z = self.vessel[index].J_z_dash * (
                    0.5
                    * self.vessel[index].rho
                    * (self.vessel[index].Lpp ** 4)
                    * self.vessel[index].d
                )
                m = self.vessel[index].displ * self.vessel[index].rho
                I_zG = m * (0.25 * self.vessel[index].Lpp) ** 2

                # Mass matrices
                M_RB = ti.Matrix(
                    [
                        [m, 0.0, 0.0],
                        [0.0, m, m * self.vessel[index].x_G],
                        [0.0, m * self.vessel[index].x_G, I_zG],
                    ]
                )

                M_A = ti.Matrix(
                    [
                        [m_x, 0.0, 0.0],
                        [0.0, m_y, 0.0],
                        [0.0, 0.0, J_z + (self.vessel[index].x_G ** 2) * m],
                    ]
                )

                # Compute the inverse of the combined mass matrix
                self.vessel[index].M_inv = (M_RB + M_A).inverse()
                self.vessel[index].M_A = M_A
                self.vessel[index].m = m
                self.vessel[index].m_x = m_x
                self.vessel[index].m_y = m_y

        elif ti.static(self.solver_type == "mmg" and self.manual_calibrated):
            for index in ti.grouped(self.vessel):
                self.vessel[index].rho = self.params["rho"][None]
                self.vessel[index].rho_air = self.params["rho_air"][None]
                self.vessel[index].C_b = self.params["C_b"][None]
                self.vessel[index].Lpp = self.params["Lpp"][None]
                self.vessel[index].B = self.params["B"][None]
                self.vessel[index].displ = self.params["displ"][None]
                self.vessel[index].w_P0 = self.params["w_P0"][None]
                self.vessel[index].J_int = self.params["J_int"][None]
                self.vessel[index].J_slo = self.params["J_slo"][None]
                self.vessel[index].x_G = self.params["x_G"][None]
                self.vessel[index].x_P = self.params["x_P"][None]
                self.vessel[index].D_p = self.params["D_p"][None]
                self.vessel[index].l_R = self.params["l_R"][None]
                self.vessel[index].gamma_R = self.params["gamma_R"][None]
                self.vessel[index].eta = self.params["eta"][None]
                self.vessel[index].kappa = self.params["kappa"][None]
                self.vessel[index].A_R = self.params["A_R"][None]
                self.vessel[index].epsilon = self.params["epsilon"][None]
                self.vessel[index].f_alpha = self.params["f_alpha"][None]
                self.vessel[index].A_Fw = self.params["A_Fw"][None]
                self.vessel[index].A_Lw = self.params["A_Lw"][None]
                self.vessel[index].t_R = self.params["t_R"][None]
                self.vessel[index].t_P = self.params["t_P"][None]
                self.vessel[index].x_H_dash = self.params["x_H_dash"][None]
                self.vessel[index].d = self.params["d"][None]
                self.vessel[index].m_x_dash = self.params["m_x_dash"][None]
                self.vessel[index].m_y_dash = self.params["m_y_dash"][None]
                self.vessel[index].R_0_dash = self.params["R_0_dash"][None]
                self.vessel[index].X_vv_dash = self.params["X_vv_dash"][None]
                self.vessel[index].X_vr_dash = self.params["X_vr_dash"][None]
                self.vessel[index].X_rr_dash = self.params["X_rr_dash"][None]
                self.vessel[index].X_vvvv_dash = self.params["X_vvvv_dash"][None]
                self.vessel[index].Y_v_dash = self.params["Y_v_dash"][None]
                self.vessel[index].Y_r_dash = self.params["Y_r_dash"][None]
                self.vessel[index].Y_vvv_dash = self.params["Y_vvv_dash"][None]
                self.vessel[index].Y_vvr_dash = self.params["Y_vvr_dash"][None]
                self.vessel[index].Y_vrr_dash = self.params["Y_vrr_dash"][None]
                self.vessel[index].Y_rrr_dash = self.params["Y_rrr_dash"][None]
                self.vessel[index].N_v_dash = self.params["N_v_dash"][None]
                self.vessel[index].N_r_dash = self.params["N_r_dash"][None]
                self.vessel[index].N_vvv_dash = self.params["N_vvv_dash"][None]
                self.vessel[index].N_vvr_dash = self.params["N_vvr_dash"][None]
                self.vessel[index].N_vrr_dash = self.params["N_vrr_dash"][None]
                self.vessel[index].N_rrr_dash = self.params["N_rrr_dash"][None]
                self.vessel[index].J_z_dash = self.params["J_z_dash"][None]
                self.vessel[index].a_H = self.params["a_H"][None]
                self.vessel[index].delta_prop = self.params["delta_prop"][None]
                # Added masses and moment of inertia
                m_x = self.vessel[index].m_x_dash * (
                    0.5
                    * self.vessel[index].rho
                    * (self.vessel[index].Lpp ** 2)
                    * self.vessel[index].d
                )
                m_y = self.vessel[index].m_y_dash * (
                    0.5
                    * self.vessel[index].rho
                    * (self.vessel[index].Lpp ** 2)
                    * self.vessel[index].d
                )
                J_z = self.vessel[index].J_z_dash * (
                    0.5
                    * self.vessel[index].rho
                    * (self.vessel[index].Lpp ** 4)
                    * self.vessel[index].d
                )
                m = self.vessel[index].displ * self.vessel[index].rho
                I_zG = m * (0.25 * self.vessel[index].Lpp) ** 2

                # Mass matrices
                M_RB = ti.Matrix(
                    [
                        [m, 0.0, 0.0],
                        [0.0, m, m * self.vessel[index].x_G],
                        [0.0, m * self.vessel[index].x_G, I_zG],
                    ]
                )

                M_A = ti.Matrix(
                    [
                        [m_x, 0.0, 0.0],
                        [0.0, m_y, 0.0],
                        [0.0, 0.0, J_z + (self.vessel[index].x_G ** 2) * m],
                    ]
                )

                # Compute the inverse of the combined mass matrix
                self.vessel[index].M_inv = (M_RB + M_A).inverse()
                self.vessel[index].M_A = M_A
                self.vessel[index].m = m
                self.vessel[index].m_x = m_x
                self.vessel[index].m_y = m_y
        else:
            pass

            # self.crafts[i].vessel = craft

    @ti.func
    def _C_RB(self, m, x_G, r):
        C_RB = ti.Matrix([[0.0, -m * r, -m * x_G * r], [m * r, 0.0, 0.0], [m * x_G * r, 0.0, 0.0]])
        return C_RB

    @ti.func
    def _C_A(self, m_x, m_y, u, v_m):
        C_A = ti.Matrix([[0.0, 0.0, -m_y * v_m], [0.0, 0.0, m_x * u], [0.0, 0.0, 0.0]])
        return C_A

    @ti.func
    def limit_angle(self, ang_in):
        return ang_in % (2 * tm.pi)

    @ti.kernel
    def init_env_ti(
        self,
        poses: ti.types.ndarray(),
        vels: ti.types.ndarray(),
        craft_camp: ti.types.ndarray(),
        width: ti.types.ndarray(),
        angle_lim: ti.types.ndarray(),
        max_v: ti.types.ndarray(),
    ):
        self.active.fill(1)
        if ti.static(self.solver_type == "mmg" or self.solver_type == "nomoto"):
            for i in range(self.max_env):
                for j in range(self.max_num):
                    index = [i, j]

                    self.x[index][0] = poses[i, j, 0]
                    self.x[index][1] = poses[i, j, 1]
                    self.x[index][2] = poses[i, j, 2]

                    self.psi[index] = poses[i, j, 2]

                    self.v[index][0] = vels[i, j, 0]
                    self.v[index][1] = vels[i, j, 1]
                    self.v[index][2] = vels[i, j, 2]

                    self.craft_camp[index] = craft_camp[i, j]
                    self.width[i, j] = width[i, j]

        else:
            for i in range(self.max_env):
                for j in range(self.max_num):
                    index = [i, j]

                    self.x[index][0] = poses[i, j, 0]
                    self.x[index][1] = poses[i, j, 1]
                    # self.x[index][2] = poses[i, j, 2]

                    self.psi[index] = poses[i, j, 2]

                    self.v[index][0] = vels[i, j, 0]
                    self.v[index][1] = vels[i, j, 1]
                    # self.v[index][2] = vels[i, j, 2]

                    self.craft_camp[index] = craft_camp[i, j]
                    self.width[index] = width[i, j]
                    self.angle_limit[index] = angle_lim[i, j]
                    self.v_max[index] = max_v[i, j]

    def core_init(self, poses, vels, craft_camps, widths, angle_lims, max_v):
        self.poses = poses
        self.vels = vels
        self.craft_camps = craft_camps
        self.widths = widths
        self.angle_lims = angle_lims
        self.max_v = max_v

        self.init_env_ti(poses, vels, craft_camps, widths, angle_lims, max_v)
        # craft_info = self.render_info()
        # return craft_info

    def core_reset(self):
        self.init_env_ti(
            self.poses, self.vels, self.craft_camps, self.widths, self.angle_lims, self.max_v
        )
        # craft_info = self.render_info()
        # return craft_info

    def core_step(self, control_signal, type="RK"):
        # print(1)
        if ti.static(self.solver_type == "mmg"):
            self.translate_action_mmg(control_signal)
            for _step in range(self.substeps):
                # time.sleep(0.1)
                if ti.static(type == "Euler"):
                    self.full_step()
                else:
                    self.full_step_rk()
                # print(step)

        elif ti.static(self.solver_type == "nomoto"):
            self.translate_action_nomoto(control_signal)
            self.movement.fill(0.0)
            for _step in range(self.substeps):
                self.step_nomoto()

        else:
            self.translate_action_kinematic(control_signal)
            self.movement.fill(0.0)
            for _step in range(self.substeps):
                self.step_kinematic()

        # craft_info = self.render_info()
        # return craft_info

    @ti.kernel
    def step_kinematic(self):
        disturb, disturb2 = 0.0, 0.0
        if ti.static(self.randomization):
            disturb = tm.vec2(
                self.w_vel[None] * tm.sin(self.beta_w[None]),
                self.w_vel[None] * tm.cos(self.beta_w[None]),
            )
            disturb2 = 0.1 * tm.vec2(ti.random(ti.f32) - 0.5, ti.random(ti.f32) - 0.5)
        for index in ti.grouped(self.v):
            # Semi-implicit euler
            if self.active[index]:
                self.v[index] += self.v_2_change[index]
                movement = (
                    self.v[index] + disturb * (0.8 + 0.2 * ti.random(ti.f32)) + disturb2
                ) * self.dt[None]
                self.x[index] += movement
                self.movement[index] += movement

    @ti.kernel
    def step_nomoto(self):
        disturb, disturb2 = 0.0, 0.0
        if ti.static(self.randomization):
            disturb = tm.vec2(
                self.w_vel[None] * tm.sin(self.beta_w[None]),
                self.w_vel[None] * tm.cos(self.beta_w[None]),
            )
            disturb2 = 0.1 * tm.vec2(ti.random(ti.f32) - 0.5, ti.random(ti.f32) - 0.5)
        for index in ti.grouped(self.x):
            if self.active[index]:
                u = self.speed_cmd[index]
                u += disturb * (0.8 + 0.2 * ti.random(ti.f32)) + disturb2
                r = self.v[index][2]
                # Nomoto: T * r_dot + r = K * delta  =>  r_dot = (K*delta - r)/T

                r_dot = (self.nomoto_K[index] * self.delta[index] - r) / ti.max(
                    self.nomoto_T[index], 1e-6
                )

                rot_mat = self.rot_psi(self.psi[index])

                self.v[index][0] = u
                self.v[index][1] = 0.0
                self.v[index][2] = r
                old_eta_dot = rot_mat @ self.v[index]

                r_new = r + r_dot * self.dt[None]
                self.v[index][2] = r_new

                eta_dot_new = rot_mat @ self.v[index]
                new_eta = self.x[index] + 0.5 * (old_eta_dot + eta_dot_new) * self.dt[None]
                new_eta[2] = self.limit_angle(new_eta[2])
                self.psi[index] = new_eta[2]
                self.x[index] = new_eta

    @ti.func
    def _C_X_wind(self, g_w, cx=0.9):
        return -cx * tm.cos(g_w)

    @ti.func
    def _C_Y_wind(self, g_w, cy=0.95):
        return cy * tm.sin(g_w)

    @ti.func
    def _C_N_wind(self, g_w, cn=0.2):
        return cn * tm.sin(2 * g_w)

    def render_info(self):
        np_x = np.ndarray((self.max_env, self.max_num, 3), dtype=np.float64)
        np_v = np.ndarray((self.max_env, self.max_num, 3), dtype=np.float64)
        np_rot_ang = np.ndarray(
            (
                self.max_env,
                self.max_num,
            ),
            dtype=np.float64,
        )
        self.get_render_info(np_x, np_v, np_rot_ang)

        craft_data = {
            "position": np_x.tolist(),
            "velocity": np_v.tolist(),
            "rotation_ang": np_rot_ang.tolist(),
        }

        return craft_data

    @ti.kernel
    def get_render_info(
        self, x: ti.types.ndarray(), v: ti.types.ndarray(), rot_ang: ti.types.ndarray()
    ):
        for index in ti.grouped(self.x):
            i = index[0]
            j = index[1]

            for k in ti.static(range(3)):
                x[i, j, k] = self.x[index][k]
                v[i, j, k] = self.v[index][k]
                rot_ang[i, j] = self.psi[index]

    @ti.kernel
    def translate_action_mmg(self, signal: ti.types.ndarray()):
        for j in range(self.max_num):
            for i in range(self.max_env):
                # print(i)
                index = [i, j]

                self.nps[index] = signal[i, j, 0]
                self.delta[index] = signal[i, j, 1]
        # print(signal[0,0,0], 'time', self.nps[0,0])

        # print(self.delta[0,0])

    @ti.kernel
    def translate_action_nomoto(self, signal: ti.types.ndarray()):
        for index in ti.grouped(self.x):
            i = index[0]
            j = index[1]
            self.speed_cmd[index] = signal[i, j, 0]
            self.delta[index] = signal[i, j, 1]

    @ti.kernel
    def translate_action_kinematic(self, signal: ti.types.ndarray()):
        for index in ti.grouped(self.x):
            # maximum velocity: 42Kn-21m/s, acceleration duration: 28s
            # maximum acceleration assumption (linear): 2.8m/s^2
            j = index[1]
            i = index[0]

            current_psi = (tm.atan2(self.v[index].x, (self.v[index].y + 1e-6)) + 2 * tm.pi) % (
                2 * tm.pi
            )

            desired_v = tm.max(signal[i, j, 0], 1e-4)
            # changed_ang = signal[i, j, 1]
            new_ang = signal[i, j, 1] * tm.pi / 180.0
            # counter-clockwise rot_psi_2d
            changed_ang = current_psi - new_ang
            # print(new_ang,changed_ang,current_psi)

            rot_mat = self.rot_psi_2d(changed_ang)
            new_v = ti.select(
                tm.length(self.v[index]) > 1e-5,
                rot_mat @ tm.normalize(self.v[index]) * desired_v,
                rot_mat @ tm.vec2(0.0, 1.0) * desired_v,
            )

            # new_v = rot_mat @ tm.normalize(self.v[index]) * desired_v
            full_v_2_change = new_v - self.v[index]
            length = tm.length(full_v_2_change) / self.substeps_float[None]

            # optimized
            absolute = tm.min(length, self.dt[None] * 0.3)
            normalized_change = ti.select(
                length > 1e-5, tm.normalize(full_v_2_change), tm.vec2(0.0, 0.0)
            )
            self.v_2_change[index] = normalized_change * absolute

            # #If < 1m/s^2 * dt
            # if length < self.dt[None]:
            #     self.v_2_change[index] = (new_v - self.v[index]) / self.substeps_float[None]
            # else:
            # Alternative: normalize the capped velocity change.

    @ti.kernel
    def full_step(self):
        vc = 0
        bc = 0
        if ti.static(self.randomization):
            disturb = tm.vec2(
                self.w_vel[None] * tm.sin(self.beta_w[None]),
                self.w_vel[None] * tm.cos(self.beta_w[None]),
            )
            disturb2 = 0.1 * tm.vec2(ti.random(ti.f32) - 0.5, ti.random(ti.f32) - 0.5)
            db = disturb * (0.8 + ti.random(dtype=ti.f32) * 0.2) + disturb2
            vc = tm.length(db)
            bc = tm.atan2(db.y, db.x)
        for index in ti.grouped(self.x):
            if self.active[index]:
                rot_mat = self.rot_psi(self.psi[index])
                # print('rot_mat', rot_mat)

                old_eta_dot = rot_mat @ self.v[index]

                uvr_dot = self.mmg_dyn_step_optimized(
                    self.v[index],
                    self.vessel[index],
                    self.dt[None],
                    self.nps[index],
                    self.delta[index],
                    self.psi[index],
                    bc,
                    vc,
                    self.w_vel[None],
                    self.beta_w[None],
                )
                self.v[index] += uvr_dot * self.dt[None]

                # Find new eta_dot via rotation
                eta_dot_new = rot_mat @ self.v[index]
                # eta_dot_new = self.v[index] @ rot_mat

                # Update position in earth fixed coordinate system
                new_eta = self.x[index] + 0.5 * (old_eta_dot + eta_dot_new) * self.dt[None]
                # print(new_eta)

                # Correct for overshooting heading angles
                new_eta[2] = self.limit_angle(new_eta[2])
                self.psi[index] = new_eta[2]

                self.x[index] = new_eta
            # print(self.x[0,0], self.v[0,0])

    @ti.kernel
    def full_step_rk(self):
        vc = 0
        bc = 0
        if ti.static(self.randomization):
            disturb = tm.vec2(
                self.w_vel[None] * tm.sin(self.beta_w[None]),
                self.w_vel[None] * tm.cos(self.beta_w[None]),
            )
            disturb2 = 0.1 * tm.vec2(ti.random(ti.f32) - 0.5, ti.random(ti.f32) - 0.5)
            db = disturb * (0.8 + ti.random(dtype=ti.f32) * 0.2) + disturb2
            vc = tm.length(db)
            bc = tm.atan2(db.y, db.x)
        for j in range(self.max_num):
            for i in range(self.max_env):
                # print(i)
                index = [i, j]
                if self.active[index]:
                    #########################################
                    # (Runge-Kutta)RK4Initialize
                    #########################################
                    orig_pos = self.x[index]
                    orig_vel = self.v[index]
                    orig_psi = self.psi[index]
                    orig_rot_mat = self.rot_psi(orig_psi)

                    # for slopes
                    k = (
                        ti.Vector.zero(self.ctype, 3),
                        ti.Vector.zero(self.ctype, 3),
                        ti.Vector.zero(self.ctype, 3),
                        ti.Vector.zero(self.ctype, 3),
                    )

                    #########################################
                    # -------- 1st ---------
                    tmp_vel_k1 = orig_vel
                    k[0] = self.mmg_dyn_step_optimized(
                        tmp_vel_k1,
                        self.vessel[index],
                        self.dt[None],
                        self.nps[index],
                        self.delta[index],
                        orig_psi,
                        # self.fl_psi[None],
                        # self.fl_vel[None],
                        bc,
                        vc,
                        self.w_vel[None],
                        self.beta_w[None],
                    )

                    # -------- 2nd ---------
                    tmp_vel_k2 = orig_vel + 0.5 * self.dt[None] * k[0]
                    orig_pos + 0.5 * self.dt[None] * (orig_rot_mat @ orig_vel)
                    tmp_psi_k2 = orig_psi + 0.5 * self.dt[None] * orig_vel[2]

                    k[1] = self.mmg_dyn_step_optimized(
                        tmp_vel_k2,
                        self.vessel[index],
                        self.dt[None],
                        self.nps[index],
                        self.delta[index],
                        tmp_psi_k2,
                        bc,
                        vc,
                        self.w_vel[None],
                        self.beta_w[None],
                    )

                    # -------- 3rd ---------
                    tmp_vel_k3 = orig_vel + 0.5 * self.dt[None] * k[1]
                    orig_pos + 0.5 * self.dt[None] * (self.rot_psi(tmp_psi_k2) @ tmp_vel_k2)
                    tmp_psi_k3 = orig_psi + 0.5 * self.dt[None] * tmp_vel_k2[2]

                    k[2] = self.mmg_dyn_step_optimized(
                        tmp_vel_k3,
                        self.vessel[index],
                        self.dt[None],
                        self.nps[index],
                        self.delta[index],
                        tmp_psi_k3,
                        bc,
                        vc,
                        self.w_vel[None],
                        self.beta_w[None],
                    )

                    # -------- 4th ---------
                    tmp_vel_k4 = orig_vel + self.dt[None] * k[2]
                    orig_pos + self.dt[None] * (self.rot_psi(tmp_psi_k3) @ tmp_vel_k3)
                    tmp_psi_k4 = orig_psi + self.dt[None] * tmp_vel_k3[2]

                    k[3] = self.mmg_dyn_step_optimized(
                        tmp_vel_k4,
                        self.vessel[index],
                        self.dt[None],
                        self.nps[index],
                        self.delta[index],
                        tmp_psi_k4,
                        bc,
                        vc,
                        self.w_vel[None],
                        self.beta_w[None],
                    )

                    #########################################
                    # RK4
                    #########################################

                    vel_increment = (k[0] + 2 * k[1] + 2 * k[2] + k[3]) * (self.dt[None] / 6.0)

                    old_eta_dot = orig_rot_mat @ orig_vel

                    new_vel = orig_vel + vel_increment

                    pos_increment = (
                        old_eta_dot
                        + 2 * (self.rot_psi(tmp_psi_k2) @ tmp_vel_k2)
                        + 2 * (self.rot_psi(tmp_psi_k3) @ tmp_vel_k3)
                        + (self.rot_psi(tmp_psi_k4) @ tmp_vel_k4)
                    ) * (self.dt[None] / 6.0)

                    # v & x update
                    self.v[index] = new_vel
                    self.x[index] = orig_pos + pos_increment
                    self.movement[index] = pos_increment

                    self.psi[index] = self.x[index][2]
                    two_pi = 2 * tm.pi
                    floored = tm.floor(self.psi[index] / two_pi)
                    self.psi[index] = self.psi[index] - two_pi * floored

                    # neg psi
                    if self.psi[index] < 0:
                        self.psi[index] += two_pi

                    self.x[index][2] = self.psi[index]
                    # self.psi[index] = self.x[index][2]
                    # x = tm.fmod

    @ti.func
    def mmg_dyn_step_optimized(self, x, vessel, dt, nps, delta, psi, fl_psi, fl_vel, w_vel, beta_w):
        # pos
        # print(f'delta = {delta}, cosdelta = {tm.cos(delta)}')
        u = x[0]
        v_m = x[1]
        r = x[2]

        # fl_vel_condi = ti.select()
        u_c = fl_vel * tm.cos(fl_psi - psi - tm.pi)
        v_c = fl_vel * tm.sin(fl_psi - psi - tm.pi)
        # relative velocity
        u_r = u - u_c
        v_r = v_m - v_c
        u_pure = u
        v_pure = v_m

        u = u_r
        v_m = v_r

        # total velocity U
        U = tm.sqrt(u**2 + v_m**2)

        # if not zero
        U_flag = U != 0
        beta = ti.select(U_flag, tm.atan2(-v_m, u), 0.0)
        v_dash = ti.select(U_flag, v_m / U, 0.0)
        r_dash = ti.select(U_flag, r * vessel.Lpp / U, 0.0)

        # Propeller and rudder calculations (based on mmg_dynamics)
        beta_P = beta - (vessel.x_P / vessel.Lpp) * r_dash

        w_P = 0.0
        if ti.static(self.manual_calibrated):
            w_P = vessel.w_P0 * tm.exp(-4.0 * beta_P**2)
        else:
            C_2 = ti.select(beta_P >= 0, vessel.C_2_plus, vessel.C_2_minus)
            tmp = 1 - tm.exp(-vessel.C_1 * ti.abs(beta_P)) * (C_2 - 1)
            w_P = 1 - (1 - vessel.w_P0) * (1 + tmp)

        # J = (1 - w_P) * u / (nps * vessel.D_p) * ti.cast((nps != 0), self.ctype)
        J = ti.select(nps != 0, (1 - w_P) * u / (nps * vessel.D_p), 0.0)

        K_T = 0.0
        if ti.static(self.manual_calibrated):
            K_T = vessel.J_slo * J + vessel.J_int
        else:
            K_T = ti.select(
                vessel.k_0 != 0.0,
                vessel.k_0 + vessel.k_1 * J + vessel.k_2 * (J**2),
                vessel.J_slo * J + vessel.J_int,
            )

        beta_R = beta - vessel.l_R * r_dash

        gamma_R = ti.select(beta_R < 0.0, vessel.gamma_R_minus, vessel.gamma_R_plus)

        v_R = U * gamma_R * beta_R

        u_R = ti.select(
            J != 0.0,
            u
            * (1 - w_P)
            * vessel.epsilon
            * tm.sqrt(
                vessel.eta
                * (1.0 + vessel.kappa * (tm.sqrt(1.0 + 8.0 * K_T / (tm.pi * (J**2))) - 1)) ** 2
                + (1 - vessel.eta)
            ),
            0.0,
        )

        U_R = tm.sqrt(u_R**2 + v_R**2)
        alpha_R = delta - tm.atan2(v_R, u_R)
        F_N = 0.5 * vessel.A_R * vessel.rho * vessel.f_alpha * (U_R**2) * tm.sin(alpha_R)
        # print(f'p.aAR{vessel.A_R}, FN: {F_N}')

        # Forces on hull and rudder
        F_C = 0.5 * vessel.rho * vessel.Lpp * vessel.d * (U**2)
        X_H = F_C * (
            -vessel.R_0_dash
            + vessel.X_vv_dash * (v_dash**2)
            + vessel.X_vr_dash * v_dash * r_dash
            + vessel.X_rr_dash * (r_dash**2)
            + vessel.X_vvvv_dash * (v_dash**4)
        )
        X_R = -(1 - vessel.t_R) * F_N * tm.sin(delta)
        X_P = (1 - vessel.t_P) * vessel.rho * K_T * (nps**2) * (vessel.D_p**4)

        # Lateral and yaw forces
        Y_H = F_C * (
            vessel.Y_v_dash * v_dash
            + vessel.Y_r_dash * r_dash
            + vessel.Y_vvv_dash * (v_dash**3)
            + vessel.Y_vvr_dash * (v_dash**2) * r_dash
            + vessel.Y_vrr_dash * v_dash * (r_dash**2)
            + vessel.Y_rrr_dash * (r_dash**3)
        )
        Y_R = -(1 + vessel.a_H) * F_N * tm.cos(delta)

        N_H = (
            F_C
            * vessel.Lpp
            * (
                vessel.N_v_dash * v_dash
                + vessel.N_r_dash * r_dash
                + vessel.N_vvv_dash * (v_dash**3)
                + vessel.N_vvr_dash * (v_dash**2) * r_dash
                + vessel.N_vrr_dash * v_dash * (r_dash**2)
                + vessel.N_rrr_dash * (r_dash**3)
            )
        )
        rudder_moment_arm = -0.5 * vessel.Lpp + vessel.a_H * vessel.x_H_dash * vessel.Lpp
        N_R = -rudder_moment_arm * F_N * tm.cos(delta)

        # # External forces (e.g. wind) / currently ignoring
        X_W = Y_W = N_W = 0.0
        if ti.static(self.have_wind):
            u_w = w_vel * tm.cos(beta_w - psi)
            v_w = w_vel * tm.sin(beta_w - psi)

            u_rw = u - u_w
            v_rw = v_m - v_w

            V_rw_sq = u_rw**2 + v_rw**2
            g_rw = -tm.atan2(v_rw, u_rw)

            # Wind forces (assuming wind force coefficients are defined)
            X_W = 0.5 * vessel.rho_air * V_rw_sq * self._C_X_wind(g_rw) * vessel.A_Fw
            Y_W = 0.5 * vessel.rho_air * V_rw_sq * self._C_Y_wind(g_rw) * vessel.A_Lw
            N_W = 0.5 * vessel.rho_air * V_rw_sq * self._C_N_wind(g_rw) * vessel.A_Lw * vessel.Lpp
        else:
            X_W = Y_W = N_W = 0.0

        # Total forces and moments
        FX = X_H + X_R + X_P + X_W
        FY = Y_H + Y_R + Y_W
        FN = N_H + N_R + N_W

        F = ti.Vector([FX, FY, FN])

        M_inv = vessel.M_inv
        m = vessel.m
        m_x = vessel.m_x
        m_y = vessel.m_y
        M_A = vessel.M_A

        # Acceleration calculation (neglecting Coriolis terms)
        result = ti.select(
            fl_vel != 0.0,
            M_inv
            @ (
                F
                - self._C_RB(m, vessel.x_G, r) @ ti.Vector([u_pure, v_pure, r])
                - self._C_A(m_x, m_y, u, v_m) @ ti.Vector([u_r, v_r, r])
                + M_A @ ti.Vector([v_c * r, -u_c * r, 0.0])
            ),
            M_inv
            @ (
                F
                - (
                    (self._C_RB(m, vessel.x_G, r) + self._C_A(m_x, m_y, u, v_m))
                    @ ti.Vector([u, v_m, r])
                )
            ),
        )

        # State update
        return result
