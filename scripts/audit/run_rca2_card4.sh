#!/bin/bash
# 09-16 复核补充实验·卡 4：参考=桥、学习率 4 倍、5 轮的剂量实验，逐轮存档出 198 首面板
cd /data/peilincai/CyberPoetTraining/cyberpoet_v1; export CUDA_VISIBLE_DEVICES=4 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
./.env/bin/llamafactory-cli train /data/peilincai/CyberPoetTraining/claude_night_20260827/configs/dpo_pt9_refbridge2_dose.yaml > /data/peilincai/CyberPoetTraining/claude_night_20260827/logs/dpo_pt9_refbridge2_dose.log 2>&1
echo "[$(date +%H:%M)] 复核实验：剂量重训 exit $?" >> /data/peilincai/CyberPoetTraining/claude_night_20260827/logs/seq_watcher.log
cd /data/peilincai/CyberPoetTraining/claude_night_20260827
for ck in $(ls -d outputs/dpo_pt9_refbridge2_dose/checkpoint-* | sort -t- -k2 -n); do
  tag=$(basename $ck)
  /data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python rca_20260905/gen_panel_seeds.py RCAdose_$tag /data/peilincai/CyberPoetTraining/claude_night_20260827/$ck /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/merged_sft_pt9 /data/peilincai/CyberPoetTraining/claude_night_20260827/rca_20260905/RCAdose_${tag}_panel_gens.jsonl 911001,911002,911003 > logs/panel_dose_$tag.log 2>&1
  echo "[$(date +%H:%M)] 复核实验：剂量臂 $tag 面板 exit $?" >> logs/seq_watcher.log
done
