"""Instrument the unchanged native MAPPO trainer; never edit the environment."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_name(p.name+'.tmp');q.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def wire(source):
    sys.path.insert(0,str(source/'code'))
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    import train_mappo as native
    from grid_env.grid_env import GridEnv,MAX_STEPS
    from grid_env.agents.mappo_agent import MAPPOAgent
    if not Path(native.__file__).resolve().is_relative_to(source.resolve()):raise ValueError('Wrong source imported')
    return native,GridEnv,MAX_STEPS,MAPPOAgent,torch

def evaluate(agent, difficulty, seeds, mode='continuous'):
    """Independent environment seeds, deterministic no-goal actor, no critic."""
    trained=agent.trained
    agent.trained=True
    try:return _evaluate_impl(agent,difficulty,seeds,mode)
    finally:agent.trained=trained

def _evaluate_impl(agent, difficulty, seeds, mode):
    from grid_env.grid_env import GridEnv,MAX_STEPS
    rows=[]
    for seed in seeds:
        env=GridEnv(difficulty=difficulty,seed=seed,task_mode=mode)
        reward=0.;actions_total=0
        while not env.done and env.step_count<MAX_STEPS:
            # act() needs only own IDs here. Avoid an extra global-sensor poll:
            # pure MAPPO reads encode_unit_obs exactly as the native evaluator.
            own={'situational_data':{'friendly_assets':[{'id':u} for u in env.blue_units if env.entities[u].alive]}}
            actions=agent.act(own,env)
            if not actions:raise ValueError('No live actors before terminal; retain engineering failure')
            actions_total+=len(actions)
            env.step(actions,None);reward+=env.compute_reward(role='blue')
        m=env.get_episode_metrics()
        rows.append({'seed':seed,'success':bool(m['mission_success']),'ticks':env.step_count,'reward':reward,
                     'actions':actions_total,'metrics':m})
    return rows

def summary(rows):
    import numpy as np
    return {'n_eval_seeds':len(rows),'success_rate':float(np.mean([r['success'] for r in rows])),
            'mean_reward':float(np.mean([r['reward'] for r in rows])),
            'mean_length':float(np.mean([r['ticks'] for r in rows]))}

def cls(native):
    import numpy as np
    class Instrumented(native.MAPPOTrainer):
        def __init__(self,*args,diagnostic_output=None,**kwargs):
            super().__init__(*args,**kwargs)
            self.diagnostic_output=diagnostic_output;self._signals=[];self._records=[]
            # Passive logger: return EXACT same scalar after original call.
            for env in self.envs:
                original=env.compute_reward
                def logged(role='blue',_fn=original,_env=env):
                    value=_fn(role=role)
                    self._signals.append((value,_env.done))
                    return value
                env.compute_reward=logged
        def collect_rollout(self,buf):
            self._signals=[]
            info=super().collect_rollout(buf)
            raw=[v for v,done in self._signals]
            wins=info['episode_wins']
            self._latest={'step':self.total_timesteps,'n_completed_training_episodes':len(wins),
                 'training_success_rate':float(np.mean(wins)) if wins else None,
                 'raw_reward_mean':float(np.mean(raw)) if raw else None,
                 'raw_reward_nonzero_fraction':float(np.mean(np.asarray(raw)!=0)) if raw else None,
                 'positive_nonterminal_rewards':sum(v>0 and not done for v,done in self._signals),
                 'terminal_rewards':sum(done for v,done in self._signals),
                 'normalized_return_mean':float(np.mean(info['episode_returns'])) if wins else None}
            return info
        def ppo_update(self,buf):
            result=super().ppo_update(buf)
            row={**self._latest,**result,'recorded_at':time.time()}
            self._records.append(row)
            if self.diagnostic_output:
                with (self.diagnostic_output/'training_rollouts.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
                write(self.diagnostic_output/'progress.json',{'state':'training','step':self.total_timesteps,'budget':self.total_steps,'latest':row})
            return result
        def evaluate(self,num_episodes=10):
            rows=evaluate(self.agent,self.difficulty,list(range(23101,23111)),self.task_mode)
            result=summary(rows)
            if self.diagnostic_output:
                write(self.diagnostic_output/f'development/step-{self.total_timesteps:09d}.json',{'step':self.total_timesteps,'rows':rows,'summary':result})
            return result
    return Instrumented

def smoke(a):
    native,GridEnv,_,MAPPOAgent,torch=wire(a.source)
    import numpy as np
    # Two seed-identical rollouts: passive logging must preserve buffers and weights.
    settings=dict(difficulty='complex',seed=22001,total_steps=512,steps_per_rollout=512,num_envs=8,device='cpu',save_dir=str(a.output/'native'))
    x=native.MAPPOTrainer(**settings);bx=native.TeamRollout();ix=x.collect_rollout(bx);ux=x.ppo_update(bx)
    y=cls(native)(**{**settings,'save_dir':str(a.output/'instrumented')});by=native.TeamRollout();iy=y.collect_rollout(by);uy=y.ppo_update(by)
    checks={'actions_equal':bx.f_action==by.f_action,'rewards_equal':bx.team==by.team,
            'observations_equal':np.array_equal(bx.f_obs,by.f_obs),'advantages_equal':np.array_equal(bx.f_adv,by.f_adv),
            'updates_equal':ux==uy,'actor_after_update_equal':all(torch.equal(v,y.agent.actor.state_dict()[k]) for k,v in x.agent.actor.state_dict().items())}
    if not all(checks.values()):raise ValueError('Passive instrumentation altered training')
    y.agent.trained=True
    write(a.output/'smoke.json',{'state':'passed','checks':checks,'rollout_steps':512})
    print(json.dumps({'state':'passed','checks':checks}),flush=True)

def train(a):
    native,GridEnv,_,MAPPOAgent,torch=wire(a.source)
    config=json.loads(a.config.read_text());out=a.output
    out.mkdir(parents=True,exist_ok=True)
    if (out/'config.json').exists():raise ValueError('Existing training attempt retained')
    write(out/'config.json',config);start=time.time()
    try:
        settings=dict(difficulty='complex',seed=config['seed'],total_steps=config['total_steps'],
            steps_per_rollout=4096,num_envs=8,ppo_epochs=4,batch_size=512,lr=config['lr'],
            ent_coef=config['entropy'],gamma=.99,gae_lambda=.95,clip_eps=.2,vf_coef=.5,max_grad_norm=.5,
            eval_interval=100000,save_dir=str(out/'checkpoints'),device='cpu',
            goal_inject_prob=.5,goal_inject_period=20,task_mode='continuous',init_from=config.get('init_from'))
        trainer=cls(native)(**settings,diagnostic_output=out)
        trainer.train()
        # Both final and development-selected best are evaluated; never pick by confirm outcomes.
        results={}
        for tag in ['best','final']:
            path=Path(trainer._ckpt(tag))
            agent=MAPPOAgent(trained=True,checkpoint_path=str(path),device='cpu')
            rows=evaluate(agent,'complex',list(range(24101,24111)))
            write(out/f'confirmation/{tag}.json',{'checkpoint_sha256':sha(path),'rows':rows,'summary':summary(rows)})
            results[tag]=summary(rows)
        write(out/'status.json',{'state':'completed','seconds':time.time()-start,'actual_steps':trainer.total_timesteps,'results':results})
    except Exception as e:
        write(out/'status.json',{'state':'failed-engineering','error':repr(e),'seconds':time.time()-start});raise

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','train'])
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    smoke(a) if a.command=='smoke' else train(a)

if __name__=='__main__':main()
