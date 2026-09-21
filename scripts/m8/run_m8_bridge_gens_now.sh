#!/bin/bash
# 桥（M8sft）的三份生成与偏好训练并行先跑（09-21 11:50）：面板 198 首、v14 候选 372 首、关重复罚复读诊断 48 首。
# 文件名与训后流程相同、可续写——训后流程轮到这几步时发现已齐会直接跳过。卡 3 此刻空余 21 GB（对方任务在跑，起不了新的），批 48 让我方占到约 18 GB：
# 对方这一个跑完后空余仍 <24000，它的下一个会按自己的规则等；不和它同时装载。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; PY=/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python; B=$N/outputs/merged_sft_m8; Q=$N/quiz_v3; C=${1:-3}
log(){ echo "[$(date +%m-%d_%H:%M)] M8并行：$*" >> $N/logs/m8_checks.log; }
cd $N
for job in "$Q/M8sft_panel_gens.jsonl $Q/m8_titles_panel66.json" "$Q/v14_cands_M8sft.jsonl $Q/m8_titles_v14.json" "$N/rca_20260905/degen_m8sft.jsonl $Q/m8_titles_degen48.json --seeds 7000 --rp 1.0"; do
  set -- $job; out=$1; titles=$2; shift 2
  log "起 $(basename $out)（卡 $C）"
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$C $PY gen_m8.py $out $B none $titles M8sft "$@" --nf4 --bs 48 >> $N/logs/m8_gen_$(basename $out .jsonl).log 2>&1
  log "$(basename $out) 退出 rc=$? 行数 $(wc -l < $out)"
done
