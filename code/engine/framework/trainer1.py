import os
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import wandb
from framework.buffer import Buffer as buffer
from model.sim2sea_agent import TransformerAgent
from torch.nn import functional as F


def setup_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    #  random.seed(seed)
    torch.backends.cudnn.deterministic = True


setup_seed(7)


def trajectory_property():
    return [
        "action",
        "hidden",
        "next_hidden",
        "hidden_q",
        "next_hidden_q",
        "hidden_q_target",
        "next_hidden_q_target",
        "id",
    ]
    # return ["action", "id"]


def compute_advantage(gamma, lmbda, td_delta):
    td_delta = td_delta.detach().numpy()
    advantage_list = []
    advantage = 0.0
    for step_idx in reversed(range(td_delta.shape[-1])):
        delta = td_delta[:, step_idx]
        advantage = gamma * lmbda * advantage + delta
        advantage_list.append(advantage)
    advantage_list.reverse()
    return torch.tensor(advantage_list, dtype=torch.float).T


def weights_init_(m):
    if isinstance(m, nn.Linear):
        torch.nn.init.xavier_uniform_(m.weight, gain=1)
        torch.nn.init.constant_(m.bias, 0)


def update_params(optim, loss, clip=False, param_list=False, retain_graph=False):
    optim.zero_grad()
    loss.backward()
    if clip is not False:
        for i in param_list:
            nn.utils.clip_grad_norm_(i, clip)
    optim.step()


class TPPO:
    def __init__(self, args):
        # env parameters
        self.state_dim = args.obs_space
        self.action_dim = args.action_space
        self.env_num = args.env_num
        self.device = args.device

        # model parameters
        self.n_layer = args.n_layer
        self.n_head = args.n_head
        self.n_embed = args.n_embed
        self.max_seq_len = args.context_len

        # training parameters
        self.actor_lr = args.a_lr
        self.critic_lr = args.c_lr
        self.buffer_size = args.buffer_capacity
        self.batch_size = args.batch_size
        self.gamma = args.gamma
        self.lamda = args.gae_lambda
        self.clip = args.ppo_clip
        self.epoch = args.ppo_epoch
        self.entropy = args.ppo_entropy
        self.grad_norm = args.grad_norm_clip
        self.actor_loss = 0
        self.critic_loss = 0
        self.bev_size = args.bev_size
        self.use_mask = args.use_mask
        self.use_bev = args.use_bev

        # define actor and critic
        args.mode = "actor"
        if args.sigma_type == "share":
            self.actor = TransformerAgent(args).to(self.device)
            print("Fixed Shared Sigmas")
        else:
            raise ValueError("only sigma_type='share' is supported by the legacy trainer")
        args.mode = "critic"
        self.critic = TransformerAgent(args).to(self.device)

        # define for transformer
        self.state = torch.zeros(self.env_num, self.max_seq_len, self.state_dim).to(self.device)
        self.bev = torch.zeros(self.env_num, args.bev_size, args.bev_size, 3).to(self.device)

        # define buffer
        self.memory = buffer(args)

    def reset_optimizer(self):
        self.actor.reset_optimizer()
        self.critic.reset_optimizer()

    def reset_state(self):
        self.state = torch.zeros(self.env_num, self.max_seq_len, self.state_dim).to(self.device)
        self.bev = torch.zeros(self.env_num, self.bev_size, self.bev_size, 3).to(self.device)

    def choose_action(self, state, bev, action_mask, train=True):
        # TODO: [0807]inference by context
        state = torch.FloatTensor(state).unsqueeze(1).to(self.device)
        self.state = torch.cat([self.state, state], dim=1)[:, 1:, :]
        if self.use_bev:
            bev = torch.FloatTensor(bev).squeeze(1).to(self.device)
        if self.use_mask:
            action_mask = torch.FloatTensor(action_mask).to(self.device)

        if train:
            action, _ = self.actor.getVecAction(self.state, bev, action_mask)
        else:
            action, _ = self.actor.getVecAction(self.state, bev, action_mask, train=False)
        return action

    def learn(self):
        # input dim [batch * context_len * dim], batch -> [num_envs * time_steps]
        state, action, reward, done, next_state, bev, bev_next, mask, amask = self.memory.sample(
            self.batch_size
        )
        state = torch.FloatTensor(state).to(self.device)
        action = torch.FloatTensor(action).to(self.device)
        reward = torch.FloatTensor(reward).to(self.device)
        next_state = torch.FloatTensor(next_state).to(self.device)
        done = torch.FloatTensor(done).to(self.device)
        mask = torch.FloatTensor(mask).to(self.device)
        print("traj masks", mask)

        if self.use_bev:
            bev = torch.FloatTensor(bev).to(self.device)
            bev_next = torch.FloatTensor(bev_next).to(self.device)
        if self.use_mask:
            amask = torch.FloatTensor(amask).to(self.device)

        ## ppo update
        td_target = reward + self.gamma * self.critic.getValue(next_state, bev).reshape(
            state.shape[0], state.shape[1]
        ) * (1 - done)  # 20*1
        td_error = td_target - self.critic.getValue(state, bev).reshape(
            state.shape[0], state.shape[1]
        )
        advantage = compute_advantage(self.gamma, self.lamda, td_error.cpu()).to(self.device)

        # [trick] : advantage normalization
        td_lamda_target = (
            advantage * mask
            + self.critic.getValue(state, bev).reshape(state.shape[0], state.shape[1]) * mask
        )
        # advantage = ((advantage - advantage.mean()) / (advantage.std() +1e-5)).detach()

        valid_advantage = advantage[mask == 1]
        if len(valid_advantage) > 0:
            advantage_mean = valid_advantage.mean()
            advantage_std = valid_advantage.std()
            advantage = (((advantage - advantage_mean) / (advantage_std + 1e-5)) * mask).detach()
        else:
            advantage = (advantage * 0).detach()

        old_action_log_prob = self.actor.getActionLogProb(state, action, bev, amask)

        for _ in range(self.epoch):
            # sample new action and new action log prob
            print(_)
            new_action_log_prob = self.actor.getActionLogProb(state, action, bev, amask, train=True)
            # update actor
            ratio = (new_action_log_prob - old_action_log_prob).exp()

            surprise = ratio * advantage
            clipped_surprise = torch.clamp(ratio, 1 - self.clip, 1 + self.clip) * advantage
            actor_loss = -torch.min(surprise, clipped_surprise) * mask

            actor_loss = actor_loss.mean()
            # update critic
            critic_loss = F.mse_loss(
                td_lamda_target.detach(),
                self.critic.getValue(state, bev).reshape(state.shape[0], state.shape[1]) * mask,
            )

            # critic_loss = critic_loss * mask
            # update
            self.actor.optimizer.zero_grad()
            self.critic.optimizer.zero_grad()
            actor_loss.backward()
            critic_loss.backward()
            # trick: clip gradient
            nn.utils.clip_grad_norm_(self.actor.parameters(), self.grad_norm)
            nn.utils.clip_grad_norm_(self.critic.parameters(), self.grad_norm)
            self.actor.optimizer.step()
            self.critic.optimizer.step()

        # the fraction of the training data that triggered the clipped objective
        self.clipfrac = torch.mean(torch.greater(torch.abs(ratio - 1), self.clip).float()).item()
        self.approxkl = torch.mean(-new_action_log_prob + old_action_log_prob).item()

        self.actor_loss = actor_loss.item()
        self.critic_loss = critic_loss.item()

        return actor_loss, critic_loss

    def learn_critic(self):
        # input dim [batch * context_len * dim], batch -> [num_envs * time_steps]
        state, action, reward, done, next_state = self.memory.sample(self.batch_size)
        state = torch.FloatTensor(state).to(self.device)
        reward = torch.FloatTensor(reward).to(self.device)
        next_state = torch.FloatTensor(next_state).to(self.device)
        done = torch.FloatTensor(done).to(self.device)

        ## ppo update
        td_target = reward + self.gamma * self.critic.getValue(next_state).reshape(
            state.shape[0], state.shape[1]
        ) * (1 - done)  # 20*1
        td_error = td_target - self.critic.getValue(state).reshape(state.shape[0], state.shape[1])
        advantage = compute_advantage(self.gamma, self.lamda, td_error.cpu()).to(self.device)
        # [trick] : advantage normalization
        td_lamda_target = advantage + self.critic.getValue(state).reshape(
            state.shape[0], state.shape[1]
        )

        for _ in range(self.epoch):
            # sample new action and new action log prob
            print(_)

            # update critic
            critic_loss = F.mse_loss(
                td_lamda_target.detach(),
                self.critic.getValue(state).reshape(state.shape[0], state.shape[1]),
            )
            # update

            self.critic.optimizer.zero_grad()

            critic_loss.backward()
            # trick: clip gradient

            nn.utils.clip_grad_norm_(self.critic.parameters(), self.grad_norm)

            self.critic.optimizer.step()

        # the fraction of the training data that triggered the clipped objective

        self.critic_loss = critic_loss.item()

        return critic_loss

    def insert_data(self, data):
        for k, v in data.items():
            self.memory.insert(k, v)

    def imitation_train(self, offline_data, iter=7000):
        action_set = offline_data[0]
        state_set = offline_data[1]
        # Optional state normalization precedes tensor conversion.
        # concatenate state list
        # state_ls = np.vstack(state_ls).T
        # convert to tensor
        state_ls = torch.tensor(state_set, dtype=torch.float).to(self.device)
        action = torch.tensor(action_set, dtype=torch.float).to(self.device)

        for _iteration in range(iter):
            self.policy.set_h()
            policy_action_ls = []
            for i in range(len(action_set)):
                state = state_ls[i].view(1, 1, -1).to(self.device)
                next_action, next_action_logprob, _, _, _ = self.policy.sample(state)
                policy_action_ls.append(next_action)
            # concatenate policy action list
            policy_action = torch.cat(policy_action_ls, dim=0).squeeze()
            # cal the loss for action and policy_action
            loss = F.mse_loss(policy_action, action)
            self.imit_loss = loss.detach().cpu().numpy()
            self.policy_optim.zero_grad()
            loss.backward()
            self.policy_optim.step()
            if iter % 1 == 0:
                print("imitation train iter: ", iter, " loss: ", self.imit_loss)
                wandb.log({"imitation_train_loss": self.imit_loss})

        return loss.detach().cpu().numpy()

    def save_critic(self, save_path, episode):
        base_path = os.path.join(save_path, "trained_model")
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        model_critic_path = os.path.join(base_path, "critic_" + str(episode) + ".pth")
        torch.save(self.critic.state_dict(), model_critic_path)

    def save(self, save_path, episode):
        time = datetime.now()
        time_str = time.strftime("%m_%d_%H_%M")
        base_path = os.path.join(save_path, "trained_model")
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        model_actor_path = os.path.join(
            base_path, "actor_" + str(episode) + "_" + time_str + ".pth"
        )
        model_critic_path = os.path.join(
            base_path, "critic_" + str(episode) + "_" + time_str + ".pth"
        )
        torch.save(self.actor.state_dict(), model_actor_path)
        torch.save(self.critic.state_dict(), model_critic_path)

    def load(self, file):
        # load data from file, and map to the correct device
        # self.actor.load_state_dict(torch.load(file, map_location='cuda:0'))
        self.actor.load_state_dict(torch.load(file, map_location=self.device), strict=False)
        self.actor.reset_optimizer()

    def load_v(self, file):
        # load data from file, and map to the correct device
        # self.actor.load_state_dict(torch.load(file, map_location='cuda:0'))
        self.critic.load_state_dict(torch.load(file, map_location=self.device), strict=False)
        self.critic.reset_optimizer()
