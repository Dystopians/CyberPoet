#!/bin/bash
# 09-16 复核补充实验·卡 2：实验 A 按训练格式重打分 → 两条干预臂第 1 轮存档（checkpoint-37）各出 198 首面板
cd /data/peilincai/CyberPoetTraining/claude_night_20260827/rca_20260905; export CUDA_VISIBLE_DEVICES=2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python score_pairs_trainfmt.py margins_qwen_trainfmt.jsonl models/Qwen3-14B /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/sft_pt6,/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/sft_pt8,/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/sft_pt9 > score_trainfmt.log 2>&1
echo "[$(date +%H:%M)] 复核实验：训练格式重打分(三桥) exit $?" >> /data/peilincai/CyberPoetTraining/claude_night_20260827/logs/seq_watcher.log
/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python score_pairs_trainfmt.py margins_m7f_trainfmt.jsonl /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt9F_s2 /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/sftF_pt9 > score_trainfmt_m7f.log 2>&1
echo "[$(date +%H:%M)] 复核实验：训练格式重打分(M7F) exit $?" >> /data/peilincai/CyberPoetTraining/claude_night_20260827/logs/seq_watcher.log
cd /data/peilincai/CyberPoetTraining/claude_night_20260827
/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python rca_20260905/gen_panel_seeds.py RCActrl4_e1 /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/dpo_pt9_ctrl4/checkpoint-37 models/Qwen3-14B /data/peilincai/CyberPoetTraining/claude_night_20260827/rca_20260905/RCActrl4_e1_panel_gens.jsonl 911001,911002,911003 > logs/panel_ctrl4_e1.log 2>&1
echo "[$(date +%H:%M)] 复核实验：对照臂第1轮面板 exit $?" >> logs/seq_watcher.log
/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python rca_20260905/gen_panel_seeds.py RCArefbridge_e1 /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/dpo_pt9_refbridge2/checkpoint-37 /data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/merged_sft_pt9 /data/peilincai/CyberPoetTraining/claude_night_20260827/rca_20260905/RCArefbridge_e1_panel_gens.jsonl 911001,911002,911003 > logs/panel_refbridge_e1.log 2>&1
echo "[$(date +%H:%M)] 复核实验：处理臂第1轮面板 exit $?" >> logs/seq_watcher.log
