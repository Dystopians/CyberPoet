#!/bin/bash
# 续训各档面板（归因用）：存档一出来就出 198 首面板，顺序 400 → 550 → 700 → 850 → 1000 → 1084；卡由参数给。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; C=$1; shift
for s in "$@"; do
  until [ -f $N/outputs/sft_m8_cont/checkpoint-$s/adapter_model.safetensors ]; do sleep 30; done
  sleep 20
  $N/run_m8_rca_panels.sh $C ck$s
done
