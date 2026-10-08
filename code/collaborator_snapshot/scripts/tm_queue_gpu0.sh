#\!/bin/bash
cd /home/<user>/zrz/test_jidi/openMD/code
PY=/home/<user>/anaconda3/envs/jidi/bin/python
for seed in 42 43 44; do
  CUDA_VISIBLE_DEVICES=0 $PY train_mappo.py --difficulty medium --seed $seed --task_mode independent --save_dir checkpoints/v214 >> logs/mappo_medium_tm-ind_s${seed}_v214.log 2>&1
done
for seed in 42 43 44; do
  CUDA_VISIBLE_DEVICES=0 $PY train_mappo.py --difficulty medium --seed $seed --task_mode independent --no-goals --save_dir checkpoints/v214 >> logs/mappo_medium_tm-ind_mono_s${seed}_v214.log 2>&1
done
for seed in 42 43; do
  CUDA_VISIBLE_DEVICES=0 $PY train_mappo.py --difficulty medium --seed $seed --task_mode sequential --save_dir checkpoints/v214 >> logs/mappo_medium_tm-seq_s${seed}_v214.log 2>&1
done
echo "gpu0 queue done at $(date +%H:%M)" >> logs/auto_chain.log
