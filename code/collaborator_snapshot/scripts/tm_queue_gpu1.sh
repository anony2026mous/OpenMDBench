#\!/bin/bash
cd /home/<user>/zrz/test_jidi/openMD/code
PY=/home/<user>/anaconda3/envs/jidi/bin/python
CUDA_VISIBLE_DEVICES=1 $PY train_mappo.py --difficulty medium --seed 44 --task_mode sequential --save_dir checkpoints/v214 >> logs/mappo_medium_tm-seq_s44_v214.log 2>&1
for seed in 42 43 44; do
  CUDA_VISIBLE_DEVICES=1 $PY train_mappo.py --difficulty medium --seed $seed --task_mode sequential --no-goals --save_dir checkpoints/v214 >> logs/mappo_medium_tm-seq_mono_s${seed}_v214.log 2>&1
done
for seed in 42 43 44; do
  CUDA_VISIBLE_DEVICES=1 $PY train_mappo.py --difficulty medium --seed $seed --task_mode continuous --no-goals --save_dir checkpoints/v214 >> logs/mappo_medium_mono_s${seed}_v214.log 2>&1
done
echo "gpu1 queue done at $(date +%H:%M)" >> logs/auto_chain.log
