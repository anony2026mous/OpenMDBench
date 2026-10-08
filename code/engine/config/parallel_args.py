class NavigationEnvArgs:
    def __init__(self) -> None:
        # Args for testing parallel computing
        self.device = "cpu"
        self.res = (2000, 2000)
        self.control_freq = 1
        # Phase 0 intentionally exposes one controlled USV per environment.  The
        # environment axis remains independently batchable via max_env.
        self.max_num = 1
        self.controlled_entities_per_env = 1
        self.max_env = 16
        self.substeps = 10
        self.type = "f32"
        self.solver_type = "mmg"

        self.randomization = False
        self.seed = 0

        self.max_episode_steps = 750
        self.ship_radius = 10.0
        self.max_speed = 20.0
        self.max_angular_velocity = 0.5

        self.use_bev = False
        self.bev_size = 128
        self.bev_R = 512

        self.use_ic = True
        self.coef = 0.1
        self.searchR = 150.0
        self.GridR = 50.0

        self.stencil_grids = 2
        self.nearest_num = 5
        self.have_wind = False
        self.manual_calibrated = False
        self.obs_case = 0
        self.debug = False
        self.reward_correction = 1.0
        self.target = [1400, 580]
        self.red_num = 0
        self.blue_num = 1
        self.vel_adj = True

        self.rvo_d0 = 1000
        self.use_mask = False

        # 地图配置
        self.use_real_map = True
        self.map_origin_lonlat = [122.0, 37.4]
        self.map_scale = 50.0
        self.map_files = ["weihai_map.txt"]
        self.map_data_dir = "env/map_data"
