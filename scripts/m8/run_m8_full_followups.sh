#!/bin/bash
# 全长对照的后续（09-21 16:50）：① 等 5 号卡上 X4 面板跑完 → 在 5 号卡起 F2（旧数据）；② F1/F3 每出一个存档（500、800、末档）就出面板；F2 出 600、1242 面板。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; R=/data/peilincai/CyberPoetTraining/cyberpoet_v1
until grep -q "RCA8_X4_v5c_ck300 退出" $N/logs/m8_checks.log; do sleep 20; done
echo "[$(date +%m-%d_%H:%M)] M8归因：F2 旧数据（卡 5）起跑" >> $N/logs/m8_checks.log
(cd $R && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=5 nohup .env/bin/python $N/lf_nowarm.py $N/configs/sft_m8_full_v4data.yaml > $N/logs/sft_m8_full_v4data.log 2>&1 &)
panel_when(){   # $1 run dir  $2 step  $3 tag prefix  $4 card
  until [ -f $N/outputs/$1/checkpoint-$2/adapter_model.safetensors ]; do sleep 30; done
  sleep 10; $N/run_m8_rca_panels.sh $4 ${3}_$2
}
# 面板卡：用 6 号卡（对方任务在跑时空余 6 GB 不够；等它空出 ≥16 GB 再跑）
wait_free(){ until [ "$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $1 | tr -d ' ')" -ge 16000 ]; do sleep 30; done; }
for job in "sft_m8_full_oldbase 500 F1" "sft_m8_full_oldboth 500 F3" "sft_m8_full_oldbase 800 F1" "sft_m8_full_oldboth 800 F3" "sft_m8_full_oldbase 1084 F1" "sft_m8_full_oldboth 1242 F3" "sft_m8_full_v4data 600 F2" "sft_m8_full_v4data 1242 F2"; do
  read -r d s t <<< "$job"
  until [ -f $N/outputs/$d/checkpoint-$s/adapter_model.safetensors ]; do sleep 30; done
  sleep 10; wait_free 6; $N/run_m8_rca_panels.sh 6 ${t}_$s
done
