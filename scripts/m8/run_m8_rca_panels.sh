#!/bin/bash
# M8 桥分布问题归因（09-21 12:12，主人令：先归因修复再出卷）。现象：桥（sft_m8 第 50 步，合并后再量化）面板循环 10.6%、字数中位 164、短于 60 字 13；上一代桥 sft_pt9b 是 2.0% / 236 / 3。
# 单变量对照，全部同一生成脚本、同题（面板 66 题 × 3 种子）、同参（温度 0.9、重复罚 1.08、4 位量化推理）：
#   A = 上一代桥 merged_sft_pt9b 用本次的生成方式跑  → 隔离「量化推理 + 本次生成参数」
#   B = 本次桥第 50 步，adapter 挂在量化底座上（训练时的样子，不合并） → 隔离「合并后再量化」
#   C = 本次桥第 250 步（同上挂法） → 隔离「训练量」
# 用法: run_m8_rca_panels.sh <卡> <A|B|C> ...
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; PY=/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python; Q=$N/quiz_v3; C=$1; shift
cd $N
for k in "$@"; do
  case $k in
    A) base=$N/outputs/merged_sft_pt9b; ad=none; arm=RCA8_A_sft_pt9b_nf4;;
    B) base=models/Qwen3-14B; ad=$N/outputs/sft_m8/checkpoint-50; arm=RCA8_B_ck50_unmerged;;
    C) base=models/Qwen3-14B; ad=$N/outputs/sft_m8/checkpoint-250; arm=RCA8_C_ck250_unmerged;;
    D) base=models/Qwen3-14B; ad=$N/outputs/sft_m8/checkpoint-200; arm=RCA8_D_ck200_unmerged;;
    E) base=models/Qwen3-14B; ad=$N/outputs/pt9_s3; arm=RCA8_E_base_pt9_s3;;          # 上一代桥的预训练底（bf16 训，三段全跑）
    F) base=models/Qwen3-14B; ad=$N/outputs/pt10_s3; arm=RCA8_F_base_pt10_s3;;        # 本次桥的预训练底（pt9_s2 第 50 步 → 量化续训一段）
    G) base=models/Qwen3-14B; ad=$N/outputs/pt9_s2/checkpoint-50; arm=RCA8_G_base_pt9_s2ck50;;
    P72) base=$N/outputs/merged_sft_m8; ad=$N/outputs/dpo_m8/checkpoint-72; arm=RCA8_P72_dpo_on_ck50bridge;;   # 验证票选出的偏好训练存档（建在有问题的桥上）：看偏好训练改不改循环
    oldbase*) base=models/Qwen3-14B; ad=$N/outputs/sft_m8_short_oldbase/checkpoint-${k#oldbase}; arm=RCA8_oldbase_short_ck${k#oldbase};;
    short*) base=models/Qwen3-14B; ad=$N/outputs/sft_m8_short/checkpoint-${k#short}; arm=RCA8_short_ck${k#short};;  # 短程退火桥各档
    ck*) base=models/Qwen3-14B; ad=$N/outputs/sft_m8_cont/checkpoint-${k#ck}; arm=RCA8_cont_ck${k#ck};;   # 续训各档
  esac
  echo "[$(date +%m-%d_%H:%M)] M8归因：起 $arm（卡 $C）" >> $N/logs/m8_checks.log
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$C $PY gen_m8.py $N/rca_20260905/${arm}_panel_gens.jsonl $base $ad $Q/m8_titles_panel66.json $arm --nf4 --bs 32 >> $N/logs/${arm}.log 2>&1
  echo "[$(date +%m-%d_%H:%M)] M8归因：$arm 退出 rc=$? 行数 $(wc -l < $N/rca_20260905/${arm}_panel_gens.jsonl)" >> $N/logs/m8_checks.log
done
