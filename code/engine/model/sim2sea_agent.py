import copy

import torch
import torch.nn.functional as F
from einops import rearrange, repeat
from einops.layers.torch import Rearrange
from torch import nn
from torch.distributions import Independent


class GPTConfig:
    """base GPT config, params common to all GPT versions"""

    # embd_pdrop = 0.1
    # resid_pdrop = 0.1
    # attn_pdrop = 0.1
    embd_pdrop = 0.0
    resid_pdrop = 0.0
    attn_pdrop = 0.0

    def __init__(self, state_size, vocab_size, block_size, **kwargs):
        self.vocab_size = vocab_size
        self.block_size = block_size
        self.state_size = state_size
        for k, v in kwargs.items():
            setattr(self, k, v)


# helpers


def pair(t):
    return t if isinstance(t, tuple) else (t, t)


class Swish(nn.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x * torch.sigmoid(x)
        return x


# classes


class PreNorm(nn.Module):
    def __init__(self, dim, fn):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fn = fn

    def forward(self, x, **kwargs):
        return self.fn(self.norm(x), **kwargs)


class FeedForward(nn.Module):
    def __init__(self, dim, hidden_dim, dropout=0.0):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.net(x)


class Attention(nn.Module):
    def __init__(self, dim, heads=8, dim_head=64, dropout=0.0):
        super().__init__()
        inner_dim = dim_head * heads
        project_out = not (heads == 1 and dim_head == dim)

        self.heads = heads
        self.scale = dim_head**-0.5

        self.attend = nn.Softmax(dim=-1)
        self.to_qkv = nn.Linear(dim, inner_dim * 3, bias=False)

        self.to_out = (
            nn.Sequential(nn.Linear(inner_dim, dim), nn.Dropout(dropout))
            if project_out
            else nn.Identity()
        )

    def forward(self, x):
        qkv = self.to_qkv(x).chunk(3, dim=-1)
        q, k, v = map(lambda t: rearrange(t, "b n (h d) -> b h n d", h=self.heads), qkv)

        dots = torch.matmul(q, k.transpose(-1, -2)) * self.scale

        attn = self.attend(dots)

        out = torch.matmul(attn, v)
        out = rearrange(out, "b h n d -> b n (h d)")
        return self.to_out(out)


class G_Attention(nn.Module):
    def __init__(self, dim, heads=8, dim_head=64, dropout=0.0, type="layernorm"):
        super().__init__()
        inner_dim = dim_head * heads
        project_out = not (heads == 1 and dim_head == dim)

        self.heads = heads
        self.scale = dim_head**-0.5
        self.dim_head = dim_head
        self.normal_type = type

        self.attend = nn.Softmax(dim=-1)
        self.to_qkv = nn.Linear(dim, inner_dim * 3, bias=False)
        self.eps = 1e-5

        self.register_norm(self.eps)

        self.to_out = (
            nn.Sequential(nn.Linear(inner_dim, dim), nn.Dropout(dropout))
            if project_out
            else nn.Identity()
        )

    def forward(self, x):
        qkv = self.to_qkv(x).chunk(3, dim=-1)
        q, k, v = map(lambda t: rearrange(t, "b n (h d) -> b h n d", h=self.heads), qkv)

        seq_len = q.size(-2)
        if self.normal_type == "instance":
            k, v = k.transpose(-2, -1), v.transpose(-2, -1)

        k_heads = zip(self.norm_K, (k[:, i, ...] for i in range(self.heads)), strict=False)
        k = torch.stack([norm(value) for norm, value in k_heads], dim=1)
        v_heads = zip(self.norm_V, (v[:, i, ...] for i in range(self.heads)), strict=False)
        v = torch.stack([norm(value) for norm, value in v_heads], dim=1)

        if self.normal_type == "instance":
            k, v = k.transpose(-2, -1), v.transpose(-2, -1)

        scores = torch.matmul(k.transpose(-2, -1), v) / seq_len

        out = torch.matmul(q, scores)
        out = rearrange(out, "b h n d -> b n (h d)")
        return self.to_out(out)

    def register_norm(self, eps):
        if self.normal_type == "instance":
            self.norm_K = self._get_instancenorm(self.dim_head, self.heads, eps=eps, affine=True)
            self.norm_V = self._get_instancenorm(self.dim_head, self.heads, eps=eps, affine=True)
        else:
            self.norm_K = self._get_layernorm(self.dim_head, self.heads, eps=eps)
            self.norm_V = self._get_layernorm(self.dim_head, self.heads, eps=eps)

    @staticmethod
    def _get_layernorm(normalized_dim, n_head, **kwargs):
        return nn.ModuleList(
            [copy.deepcopy(nn.LayerNorm(normalized_dim, **kwargs)) for _ in range(n_head)]
        )

    @staticmethod
    def _get_instancenorm(normalized_dim, n_head, **kwargs):
        return nn.ModuleList(
            [copy.deepcopy(nn.InstanceNorm1d(normalized_dim, **kwargs)) for _ in range(n_head)]
        )


class Transformer(nn.Module):
    def __init__(self, dim, depth, heads, dim_head, mlp_dim, dropout=0.0, att_type="ScaleDot"):
        super().__init__()
        self.layers = nn.ModuleList([])
        self.att_type = att_type
        if self.att_type == "ScaleDot":
            for _ in range(depth):
                self.layers.append(
                    nn.ModuleList(
                        [
                            PreNorm(
                                dim, Attention(dim, heads=heads, dim_head=dim_head, dropout=dropout)
                            ),
                            PreNorm(dim, FeedForward(dim, mlp_dim, dropout=dropout)),
                        ]
                    )
                )
        elif self.att_type == "Galerkin":
            for _ in range(depth):
                self.layers.append(
                    nn.ModuleList(
                        [
                            G_Attention(dim, heads=heads, dim_head=dim_head, dropout=dropout),
                            PreNorm(dim, FeedForward(dim, mlp_dim, dropout=dropout)),
                        ]
                    )
                )
        else:
            for _ in range(depth):
                self.layers.append(
                    nn.ModuleList(
                        [
                            G_Attention(dim, heads=heads, dim_head=dim_head, dropout=dropout),
                            PreNorm(dim, FeedForward(dim, mlp_dim, dropout=dropout)),
                        ]
                    )
                )

    def forward(self, x):
        for attn, ff in self.layers:
            x = attn(x) + x
            x = ff(x) + x
        return x


class MaskAttention(nn.Module):
    def __init__(self, dim, heads=8, dim_head=64, dropout=0.0, max_block=256):
        super().__init__()
        inner_dim = dim_head * heads
        project_out = not (heads == 1 and dim_head == dim)

        self.heads = heads
        self.scale = dim_head**-0.5

        self.register_buffer(
            "mask",
            rearrange(torch.tril(torch.ones(max_block + 1, max_block + 1)), "a b -> 1 1 a b"),
        )

        self.attend = nn.Softmax(dim=-1)
        self.to_qkv = nn.Linear(dim, inner_dim * 3, bias=False)

        self.to_out = (
            nn.Sequential(nn.Linear(inner_dim, dim), nn.Dropout(dropout))
            if project_out
            else nn.Identity()
        )

    def forward(self, x):
        # batch timestep context_dim
        B, T, C = x.size()
        qkv = self.to_qkv(x).chunk(3, dim=-1)
        q, k, v = map(lambda t: rearrange(t, "b n (h d) -> b h n d", h=self.heads), qkv)

        # batch * time * head * dim
        dots = torch.matmul(q, k.transpose(-1, -2)) * self.scale
        # TODO: Check the mask implementation
        # TODO:block should > 3* n_agent + 1
        dots = dots.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))
        attn = self.attend(dots)

        out = torch.matmul(attn, v)
        out = rearrange(out, "b h n d -> b n (h d)")
        return self.to_out(out)


class Masked_G_Attention(nn.Module):
    def __init__(self, dim, heads=8, dim_head=64, dropout=0.0, type="layernorm"):
        super().__init__()
        inner_dim = dim_head * heads
        project_out = not (heads == 1 and dim_head == dim)

        self.heads = heads
        self.scale = dim_head**-0.5
        self.dim_head = dim_head
        self.normal_type = type

        self.attend = nn.Softmax(dim=-1)
        self.to_qkv = nn.Linear(dim, inner_dim * 3, bias=False)
        self.eps = 1e-7

        self.register_norm(self.eps)

        self.to_out = (
            nn.Sequential(nn.Linear(inner_dim, dim), nn.Dropout(dropout))
            if project_out
            else nn.Identity()
        )

    def forward(self, x):
        qkv = self.to_qkv(x).chunk(3, dim=-1)
        q, k, v = map(lambda t: rearrange(t, "b n (h d) -> b h n d", h=self.heads), qkv)

        bsz, n_head, seq_len, d_k = q.shape
        dtype = q.dtype

        # k = k / seq_len

        if self.normal_type == "instance":
            k, v = k.transpose(-2, -1), v.transpose(-2, -1)

        k_heads = zip(self.norm_K, (k[:, i, ...] for i in range(self.heads)), strict=False)
        k = torch.stack([norm(value) for norm, value in k_heads], dim=1)
        v_heads = zip(self.norm_V, (v[:, i, ...] for i in range(self.heads)), strict=False)
        v = torch.stack([norm(value) for norm, value in v_heads], dim=1)

        if self.normal_type == "instance":
            k, v = k.transpose(-2, -1), v.transpose(-2, -1)

        b_q, b_k, b_v = [x.reshape(bsz, n_head, -1, 1, d_k) for x in (q, k, v)]

        b_k_sum = b_k.sum(dim=-2)
        b_k_cumsum = b_k_sum.cumsum(dim=-2).type(dtype)

        scores = torch.einsum("bhund,bhune->bhude", b_k, b_v)
        scores = scores.cumsum(dim=-3).type(dtype) / seq_len

        D_inv = 1.0 / torch.einsum("bhud,bhund->bhun", b_k_cumsum + self.eps, b_q)
        out = torch.einsum("bhund,bhude,bhun->bhune", b_q, scores, D_inv)

        # out = out.reshape(q.shape)
        # out = rearrange(out, 'b h n d -> b n (h d)')

        out = rearrange(out, "b h u n e -> b u (h e n)")

        return self.to_out(out)

    def register_norm(self, eps):
        if self.normal_type == "instance":
            self.norm_K = self._get_instancenorm(self.dim_head, self.heads, eps=eps, affine=True)
            self.norm_V = self._get_instancenorm(self.dim_head, self.heads, eps=eps, affine=True)
        else:
            self.norm_K = self._get_layernorm(self.dim_head, self.heads, eps=eps)
            self.norm_V = self._get_layernorm(self.dim_head, self.heads, eps=eps)

    @staticmethod
    def _get_layernorm(normalized_dim, n_head, **kwargs):
        return nn.ModuleList(
            [copy.deepcopy(nn.LayerNorm(normalized_dim, **kwargs)) for _ in range(n_head)]
        )

    @staticmethod
    def _get_instancenorm(normalized_dim, n_head, **kwargs):
        return nn.ModuleList(
            [copy.deepcopy(nn.InstanceNorm1d(normalized_dim, **kwargs)) for _ in range(n_head)]
        )


class maskedTransformer(nn.Module):
    def __init__(self, dim, depth, heads, dim_head, mlp_dim, dropout=0.0, att_type="ScaleDot"):
        super().__init__()
        self.layers = nn.ModuleList([])
        self.att_type = att_type
        if self.att_type == "ScaleDot":
            for _ in range(depth):
                self.layers.append(
                    nn.ModuleList(
                        [
                            PreNorm(
                                dim,
                                MaskAttention(dim, heads=heads, dim_head=dim_head, dropout=dropout),
                            ),
                            PreNorm(dim, FeedForward(dim, mlp_dim, dropout=dropout)),
                        ]
                    )
                )
        elif self.att_type == "Galerkin":
            for _ in range(depth):
                self.layers.append(
                    nn.ModuleList(
                        [
                            Masked_G_Attention(
                                dim, heads=heads, dim_head=dim_head, dropout=dropout
                            ),
                            PreNorm(dim, FeedForward(dim, mlp_dim, dropout=dropout)),
                        ]
                    )
                )
        else:
            for _ in range(depth):
                self.layers.append(
                    nn.ModuleList(
                        [
                            Masked_G_Attention(
                                dim, heads=heads, dim_head=dim_head, dropout=dropout
                            ),
                            PreNorm(dim, FeedForward(dim, mlp_dim, dropout=dropout)),
                        ]
                    )
                )

    def forward(self, x):
        for attn, ff in self.layers:
            x = attn(x) + x
            x = ff(x) + x
        return x


# class maskedTransformer(nn.Module):
#     def __init__(self, dim, depth, heads, dim_head, mlp_dim, dropout = 0.):
#         super().__init__()
#         self.layers = nn.ModuleList([])
#         for _ in range(depth):
#             self.layers.append(nn.ModuleList([
#                 PreNorm(dim, MaskAttention(...)),
#                 PreNorm(dim, FeedForward(dim, mlp_dim, dropout = dropout))
#             ]))
#     def forward(self, x):
#         for attn, ff in self.layers:
#             x = attn(x) + x
#             x = ff(x) + x
#         return x


class ViT(nn.Module):
    def __init__(
        self,
        *,
        image_size,
        patch_size,
        num_classes,
        dim,
        depth,
        heads,
        mlp_dim,
        pool="cls",
        channels=3,
        dim_head=64,
        dropout=0.0,
        emb_dropout=0.0,
    ):
        super().__init__()
        image_height, image_width = pair(image_size)
        patch_height, patch_width = pair(patch_size)

        assert image_height % patch_height == 0 and image_width % patch_width == 0, (
            "Image dimensions must be divisible by the patch size."
        )

        num_patches = (image_height // patch_height) * (image_width // patch_width)
        patch_dim = channels * patch_height * patch_width
        assert pool in {"cls", "mean"}, (
            "pool type must be either cls (cls token) or mean (mean pooling)"
        )

        self.to_patch_embedding = nn.Sequential(
            Rearrange("b c (h p1) (w p2) -> b (h w) (p1 p2 c)", p1=patch_height, p2=patch_width),
            nn.Linear(patch_dim, dim),
        )

        self.pos_embedding = nn.Parameter(torch.randn(1, num_patches + 1, dim))
        self.cls_token = nn.Parameter(torch.randn(1, 1, dim))
        self.dropout = nn.Dropout(emb_dropout)

        self.transformer = Transformer(dim, depth, heads, dim_head, mlp_dim, dropout)

        self.pool = pool
        self.to_latent = nn.Identity()

        self.mlp_head = nn.Sequential(nn.LayerNorm(dim), nn.Linear(dim, num_classes))

    def forward(self, img):
        x = self.to_patch_embedding(img)
        b, n, _ = x.shape

        cls_tokens = repeat(self.cls_token, "() n d -> b n d", b=b)
        x = torch.cat((cls_tokens, x), dim=1)
        x += self.pos_embedding[:, : (n + 1)]
        x = self.dropout(x)

        x = self.transformer(x)

        x = x.mean(dim=1) if self.pool == "mean" else x[:, 0]

        x = self.to_latent(x)
        return self.mlp_head(x)


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


class TransformerAgent(nn.Module):
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
        self.use_mask = config.use_mask

        self.time_step = self.n_agent
        self.device = config.device
        self.mode = config.mode

        self.use_bev = config.use_bev

        self.embed_dim = config.n_embed
        self.encoder_head = config.n_head
        self.encoder_dim = config.n_embed
        self.encoder_layer = config.n_layer
        # self.mode = config.mode #'oa' 'oar' 'oaro'
        self.encoder = Transformer(
            self.encoder_dim,
            self.encoder_layer,
            self.encoder_head,
            decoder_dim_head,
            self.encoder_dim * 4,
        )  # TODO:dropout, dim_head
        if self.use_bev:
            self.cnn = UltraLightCNN(output_dim=config.n_embed)
            self.embed_to_action = nn.Sequential(
                nn.Linear(self.embed_dim * 2, self.embed_dim),
                Swish(),
                nn.Linear(self.embed_dim, self.action_dim),
            )
        else:
            self.embed_to_action = nn.Sequential(
                nn.Linear(self.embed_dim, self.embed_dim),
                Swish(),
                nn.Linear(self.embed_dim, self.action_dim),
            )

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
        self.to_obs_embed = nn.Sequential(nn.Linear(self.obs_dim, self.embed_dim))

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
        batch_num, n_timestep, _ = obs.shape

        # cal position embedding
        obs_pos_embedding = repeat(
            self.obs_pos_embedding, "b n d -> (b b_repeat) n d", b_repeat=batch_num
        )

        # if mask, should use the specific token to replace the origin input
        # o-observation
        obs_token = self.to_obs_embed(obs)

        # TODO: check weather agent_postion_embeding is neccessary
        obs_token += obs_pos_embedding
        cls_token = repeat(self.cls_token, "b t d -> (b b_repeat) t d", b_repeat=batch_num)

        # if input the current info or the info should as a results, should feed into the network.
        # TODO:[0809] cheak classfication
        tokens_ls = [cls_token, obs_token] if self.cls else [obs_token]

        # tokens_ls = [obs_token]
        tokens = torch.cat(tokens_ls, dim=1)

        # get the patches to be masked for the final reconstruction loss
        # attend with vision transformer [TODO: in CV, mlp head is used to merge infomation]
        encoded_tokens = self.encoder(tokens)

        # get the first token
        first_token = encoded_tokens[:, -1]

        if self.use_bev:
            # [batch, channel, w, h]
            bev = bev.permute(0, 3, 1, 2)
            bev_feature = self.cnn(bev)
            first_token = torch.cat([first_token, bev_feature], dim=-1)

        logits = self.embed_to_action(first_token)

        return logits

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

    def get_mu_prob(self, obs, action, bev, train=True):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            action = rearrange(action, "b t d-> (b t) d")
            if self.use_bev:
                bev = rearrange(bev, "b t w h c -> (b t) w h c")
        # input dim [batch * time * dim]
        obs = obs[:, -self.n_agent :, :].to(device=self.device)

        a = self.forward(obs, bev)

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

    def imitate_action(self, obs, bev):
        re_flag = False
        if len(obs.shape) == 4:
            re_flag = True
            b = obs.shape[0]
            obs = rearrange(obs, "b t c d-> (b t) c d")
            if self.use_bev:
                bev = rearrange(bev, "b t w h c -> (b t) w h c")
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
