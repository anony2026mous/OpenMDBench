import torch
import torch.nn.functional as F
from einops import rearrange, repeat
from torch import nn
from torch.distributions import Independent


def pair(t):
    return t if isinstance(t, tuple) else (t, t)


class Swish(nn.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x * torch.sigmoid(x)
        return x


class UltraLightCNN(nn.Module):
    def __init__(self, input_channels=3, output_dim=256):
        super().__init__()
        self.features = nn.Sequential(
            # Stage 1: 128x128 -> 64x64
            nn.Conv2d(input_channels, 8, kernel_size=3, stride=2, padding=1),  # 只用8个通道
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            # Stage 2: 64x64 -> 32x32
            nn.Conv2d(8, 16, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            # Stage 3: 32x32 -> 16x16
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )

        self.classifier = nn.Linear(32, output_dim)

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)  # [B, 32]
        x = self.classifier(x)
        return x


class MLPAgent(nn.Module):
    def __init__(self, config, decoder_dim_head=64):
        super().__init__()
        # construct encoder
        self.config = config
        self.n_agent = config.context_len  # self.n_agent means the max input block
        self.action_dim = (
            config.action_space if config.mode == "actor" else 1
        )  # since mean and std are concatenated
        self.obs_dim = (
            (config.obs_space + config.action_space) if config.mode == "Q" else config.obs_space
        )
        self.device = config.device
        # self.action_max = config.action_max
        self.action_max_old = config.action_max
        self.action_max_0 = config.action_max_0
        self.action_max_1 = config.action_max_1
        self.action_max = torch.tensor([self.action_max_old] * self.action_dim).to(
            device=self.device
        )
        # Optional: construct a two-dimensional action bound tensor.
        # self.action_max = torch.tensor([1.0, 0.3]).to(device=self.device)
        self.sigma_scaler = torch.tensor([1.0] * self.action_dim).to(device=self.device)
        # self.action_max.requires_grad = True
        self.sigma_min = -6
        self.sigma_max = 0.5

        self.time_step = self.n_agent
        self.device = config.device
        self.mode = config.mode

        self.embed_dim = config.n_embed
        self.encoder_head = config.n_head
        self.encoder_dim = config.n_embed
        self.encoder_layer = config.n_layer
        self.use_bev = config.use_bev
        self.use_mask = config.use_mask
        # self.mode = config.mode #'oa' 'oar' 'oaro'

        # token [TODO: all the same or different?]
        self.cls_token = nn.Parameter(torch.randn(1, 1, self.embed_dim))
        # self.sigma_param = nn.Parameter(torch.ones(self.action_dim)*-2)#.to(self.device)
        self.register_parameter(
            name="sigma_param", param=nn.Parameter(torch.ones(self.action_dim) * -1)
        )
        # Optional: use a fixed two-dimensional sigma parameter.
        # self.sigma_param = nn.Parameter(torch.tensor([-1.0, -1.0]))  # .to(self.device)
        self.cls = config.cls

        # position embeding
        self.obs_pos_embedding = nn.Parameter(torch.randn(1, self.time_step, self.embed_dim))
        self.timestep_embeding = nn.Embedding(self.time_step, self.embed_dim)

        # embed [TODO: is ReLu necessary?]

        # self.obs_to_action = nn.Sequential(
        #     nn.Linear(self.obs_dim, self.embed_dim),
        #     Swish(),
        #     nn.Linear(self.embed_dim, self.embed_dim),
        #     Swish(),
        #     nn.Linear(self.embed_dim, self.action_dim)
        # )

        self.obs_to_embed = nn.Sequential(
            nn.Linear(self.obs_dim, self.embed_dim),
            nn.ReLU(inplace=True),
            nn.Linear(self.embed_dim, self.embed_dim),
        )
        self.cnn = UltraLightCNN(output_dim=config.n_embed)
        self.embed_to_action = nn.Sequential(
            nn.Linear(self.embed_dim * 2, self.embed_dim),
            Swish(),
            nn.Linear(self.embed_dim, self.action_dim),
        )
        # learn parameters
        self.optimizer = self.configure_optimizers()

        self.parameter_number = sum(p.numel() for p in self.parameters())
        print("number of parameters: %e", self.parameter_number)

    def forward(self, obs=None, bev=None, train=False):
        """
        :param obs: [batch * n_agent/n_timestep * dim]
        :param action:
        :param reward:
        :param obs_next:
        :return: o,a,r after reconstruction
        """

        # get the first token
        first_token = obs[:, -1]
        ob_embed = self.obs_to_embed(first_token)
        if self.use_bev:
            if bev is None:
                raise ValueError("BEV input is required when use_bev=True")
            bev = bev.permute(0, 3, 1, 2)
            cn_embed = self.cnn(bev)
        else:
            cn_embed = torch.zeros_like(ob_embed)
        concat = torch.cat([ob_embed, cn_embed], dim=-1)
        action = self.embed_to_action(concat)

        return action

    def reset_optimizer(self):
        self.optimizer = self.configure_optimizers()
        return self.optimizer

    def configure_optimizers(self):
        config = self.config
        # TODO: update optimaizer setting, identify the actor and critic
        # learning rate schedular
        if self.mode == "actor":
            optimizer = torch.optim.AdamW(
                self.parameters(), lr=config.a_lr
            )  # , betas=train_config.betas)
        elif self.mode == "critic":
            optimizer = torch.optim.AdamW(self.parameters(), lr=config.c_lr)
        elif self.mode == "Q":
            optimizer = torch.optim.AdamW(self.parameters(), lr=config.q_lr)

        return optimizer

    def getValue(self, obs, bev):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            if self.use_bev:
                bev = rearrange(bev, "b t w h c -> (b t) w h c")

        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        value = self.forward(obs, bev)
        if re_flag:
            value = rearrange(value, "(b t) 1 -> b t 1", b=b)
        return value

    def getLogit(self, obs, bev):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            if self.use_bev:
                bev = rearrange(bev, "b t w h c -> (b t) w h c")
            # if self.use_mask:
            #     action_mask = rearrange(action_mask, "b t d-> (b t) d")
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        logits = self.forward(obs, bev)

        if re_flag:
            logits = rearrange(logits, "(b t) d -> b t d", b=b)

        return logits

    def getAction(self, obs, train=False):
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        a = self.forward(obs)
        # a = rearrange(a, 'b (s d)-> (b s) d', s=2)
        # mu, sigma = (a[:, 0], a[:, 1]
        mu, sigma = (
            rearrange(a, "b d-> (b d)"),
            repeat(self.sigma_param, "d -> (b d)", b=a.shape[0]),
        )
        # sigma = torch.mul(sigma, self.sigma_scaler)
        # new_mu = torch.tanh(mu)
        # new_mu[0] *= self.action_max_0
        # new_mu[1] *= self.action_max_1
        # mu = new_mu
        mu = torch.mul(torch.tanh(mu), self.action_max)
        # mu = self.action_max * torch.tanh(mu)
        sigma = torch.clamp(sigma, min=self.sigma_min, max=self.sigma_max).exp()
        a_dis = torch.distributions.Normal(mu, sigma)
        a_ = a_dis.sample().detach().cpu().numpy()
        a_log = a_dis.log_prob(a_).detach().cpu().numpy() if train else None
        return a_, a_log

    def getActionLogProb(self, obs, action, bev, amask, train=False, entropy=False):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            action = rearrange(action, "b t d-> (b t) d")
            if self.use_bev:
                bev = rearrange(bev, "b t w h c -> (b t) w h c")
            if self.use_mask:
                amask = rearrange(amask, "b t d-> (b t) d")

        # input dim [batch * context * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        logits = self.forward(obs, bev)

        if self.use_mask:
            masked_logits = logits.masked_fill(amask == 0, -1e9)
            a_dis = torch.distributions.Categorical(logits=masked_logits)
        else:
            a_dis = torch.distributions.Categorical(logits=logits)

        # a_log = a_dis.log_prob(action)
        if train:
            a_log = a_dis.log_prob(action.squeeze(-1))
        else:
            a_log = a_dis.log_prob(action.squeeze(-1)).detach()

        if re_flag:
            a_log = rearrange(a_log, "(b t) -> b t", b=b)

        if entropy:
            return a_log, a_dis.entropy().mean()
        else:
            return a_log

    def getVecAction(self, obs, bev, action_mask, train=True):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            if self.use_bev:
                bev = rearrange(bev, "b t w h c -> (b t) w h c")
            if self.use_mask:
                action_mask = rearrange(action_mask, "b t d-> (b t) d")
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        logits = self.forward(obs, bev)

        # Apply the action mask [web:13][web:16]
        if self.use_mask:
            masked_logits = logits.masked_fill(action_mask == 0, -1e9)
        else:
            masked_logits = logits
        # print('logs ',logits, masked_logits)

        a_dis = torch.distributions.Categorical(logits=masked_logits)

        a_ = a_dis.sample() if train else torch.argmax(masked_logits, dim=-1)

        self.entropy = a_dis.entropy().mean().item()

        # The action is now a single index
        a_ = a_.unsqueeze(-1)  # Add dimension for consistency
        a_log = a_dis.log_prob(a_.squeeze(-1)).detach().cpu().numpy() if train else None

        if re_flag:
            a_ = rearrange(a_, "(b t) d -> b t d", b=b)

        return a_.detach().cpu().numpy(), a_log

    def get_mu_prob(self, obs, action, train=True):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            action = rearrange(action, "b t d-> (b t) d")
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        a = self.forward(obs)

        mu, sigma = a, repeat(self.sigma_param, "d -> b d", b=a.shape[0])
        sigma = torch.clamp(sigma, min=self.sigma_min, max=self.sigma_max).exp()

        mu = torch.mul(torch.tanh(mu), self.action_max)

        a_dis = Independent(torch.distributions.Normal(mu, sigma), 1)

        a_log = a_dis.log_prob(action)

        if re_flag:
            a_log = rearrange(a_log, "(b t) -> b t", b=b)
            mu = rearrange(mu, "(b t) d -> b t d", b=b)

        return mu, a_log

    def imitate_action_batch(self, obs, a_ref, mu_ratio, dist_ratio):
        if len(obs.shape) == 4:
            obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            a_ref = rearrange(a_ref, "b t d-> (b t) d")
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        a = self.forward(obs)
        # a = rearrange(a, 'b (s d)-> (b s) d', s=2)
        # mu, sigma = (a[:, 0], a[:, 1])
        mu, sigma = a, repeat(self.sigma_param, "d -> b d", b=a.shape[0])
        sigma = torch.mul(sigma, self.sigma_scaler)

        mu = torch.mul(torch.tanh(mu), self.action_max)
        sigma = torch.clamp(sigma, min=self.sigma_min, max=self.sigma_max).exp()

        a_dis = Independent(torch.distributions.Normal(mu, sigma), 1)
        a_dis.log_prob(a_ref)

        self.entropy = a_dis.entropy().mean().item()

        loss = F.mse_loss(mu, a_ref).mean() * mu_ratio
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def imitate_action(self, obs):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        a = self.forward(obs)
        # a = rearrange(a, 'b (s d)-> (b s) d', s=2)
        # mu, sigma = (a[:, 0], a[:, 1])
        mu, sigma = a, repeat(self.sigma_param, "d -> b d", b=a.shape[0])
        sigma = torch.clamp(sigma, min=self.sigma_min, max=self.sigma_max).exp()
        # new_mu = torch.tanh(mu)
        # new_mu[0] *= self.action_max_0
        # new_mu[1] *= self.action_max_1
        # mu = new_mu
        mu = torch.mul(torch.tanh(mu), self.action_max)
        # mu = torch.clamp(mu, min=-self.action_max, max=self.action_max)
        # sigma = torch.clamp(sigma, min=self.sigma_min, max=self.sigma_max).exp()
        a_dis = Independent(torch.distributions.Normal(mu, sigma), 1)
        a_ = a_dis.sample()
        self.entropy = a_dis.entropy().mean().item()

        if re_flag:
            a_ = rearrange(a_, "(b t) d -> b t d", b=b)
            mu = rearrange(mu, "(b t) d -> b t d", b=b)

        return a_, mu

    def getActionDistribution(self, obs):
        pass

    def loss(self):
        pass
