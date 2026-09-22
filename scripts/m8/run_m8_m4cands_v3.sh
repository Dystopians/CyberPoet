#!/bin/bash
# v14 的 M4 候选 v3（09-21 22:00，新题表 126 题）：M4 是 bf16 训的，照旧 bf16 推理（约 30 GB），单卡。
# 每 5 秒查一次，任一张卡空余 ≥31 GB 立即起跑（对方脚本 60 秒一查，我方先到）；起跑 60 秒后复查同卡有没有新冒出来的别人进程，有则让（停、等 90 秒再来）。
# 生成参数与 M8 两臂逐项相同（同题表、同三颗种子、温度 0.9、top_p 0.9、重复罚 1.08、上限 560）。gen_m8.py 断点续写，失败重来不丢已生成的。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python
log(){ echo "[$(date +%m-%d_%H:%M)] M8训后：$*" >> $N/logs/seq_watcher.log; }
foreign_new(){ local uuid=$(nvidia-smi --query-gpu=uuid --format=csv,noheader -i $1); for p in $(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader | grep "$uuid" | cut -d, -f2 | tr -d ' '); do [ "$(ps -o user= -p $p 2>/dev/null | tr -d ' ')" = "$(whoami)" ] && continue; et=$(ps -o etimes= -p $p 2>/dev/null | tr -d ' '); [ -n "$et" ] && [ "$et" -lt 90 ] && return 0; done; return 1; }
OUT=$N/quiz_v3/v14_cands_M4.jsonl
for attempt in $(seq 1 12); do
  until c=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | tr -d ' ' | awk -F, '$2>=31000{print $2","$1}' | sort -t, -k1 -nr | head -n 1 | cut -d, -f2) && [ -n "$c" ]; do sleep 5; done
  log "M4 候选起跑（卡 $c，bf16，第 $attempt 次，已有 $(wc -l < $OUT 2>/dev/null || echo 0) 首）"
  (cd $N && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$c $PY gen_m8.py $OUT models/Qwen3-14B $N/outputs/dpo_pt6 $N/quiz_v3/m8_titles_v14.json M4 --bs 16 >> $N/logs/m8_gen_v14_cands_M4.log 2>&1) &
  P=$!; sleep 60
  if foreign_new $c; then kill $P 2>/dev/null; wait $P 2>/dev/null; log "M4 候选与别人同时起跑，我方让"; sleep 90; continue; fi
  wait $P; rc=$?
  n=$(wc -l < $OUT 2>/dev/null || echo 0); log "M4 候选退出 rc=$rc，已有 $n 首"
  [ "$n" -ge 378 ] && { log "M4 候选完：quiz_v3/v14_cands_M4.jsonl（$n 首）"; exit 0; }
  sleep 60
done
log "M4 候选十二次未成"; exit 1
