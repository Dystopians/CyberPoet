#!/bin/bash
# 实验 G：复读率随预训练轮数的变化（关重复罚，48 题同种子）。pt6 链 1/3/7 轮；pt9 链 s1(2ep)/s2 0.6ep/s2 3ep/s3。
cd /data/peilincai/CyberPoetTraining/claude_night_20260827
export CUDA_VISIBLE_DEVICES=7
/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python /tmp/claude-1024/-data-peilincai/6164bb8c-752c-48a6-b1de-f02ae5c96bd6/scratchpad/rca/degeneracy.py /data/peilincai/CyberPoetTraining/claude_night_20260827/rca_20260905/degen_epochs.jsonl \
  pt6_e1=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt6_r32/checkpoint-84 pt6_e3=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt6_r32/checkpoint-252 pt6_e7=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt6_r32 \
  pt9_s1=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt9_s1 pt9_s2_e06=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt9_s2/checkpoint-50 pt9_s2=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt9_s2 pt9_s3=/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt9_s3 > logs/degen_epochs.log 2>&1
echo "[$(date +%H:%M)] 轮数复读实验（sft_pt9b 后续）exit $?" >> logs/seq_watcher.log
