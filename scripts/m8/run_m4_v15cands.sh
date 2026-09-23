#!/bin/bash
# M4 的 v15 候选（09-22 20:00，实验 1 的尺子臂）：合并后的完整权重 merged_dpo_pt6（bf16 28.4 GB），可跨 2–4 张卡分派；先等 M4R 链跑完再抢卡（两条链不共用占位协议）。派生自 run_m4_merged.sh。
# 每 5 秒扫一次 3/4/5/6 号卡：按空余从大到小取卡，每张留 2.5 GB 余量，累计够 31 GB 就起跑；60 秒后查撞车，撞了就让。gen_m8.py 断点续写。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python; Q=$N/quiz_v3; OUT=$Q/v15_cands_M4.jsonl
log(){ echo "[$(date +%m-%d_%H:%M)] M4v15：$*" >> $N/logs/seq_watcher.log; }
foreign_new(){ local uuid=$(nvidia-smi --query-gpu=uuid --format=csv,noheader -i $1); for p in $(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader | grep "$uuid" | cut -d, -f2 | tr -d ' '); do [ "$(ps -o user= -p $p 2>/dev/null | tr -d ' ')" = "$(whoami)" ] && continue; et=$(ps -o etimes= -p $p 2>/dev/null | tr -d ' '); [ -n "$et" ] && [ "$et" -lt 90 ] && return 0; done; return 1; }
plan(){   # 输出 "卡列表;预算列表" 或空
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | tr -d ' ' | awk -F, '($1>=3&&$1<=6){print $2","$1}' | sort -t, -k1 -nr | awk -F, '{b=int(($1-2560)/1024); if(b<3) next; tot+=b; c=c (c?",":"") $2; m=m (m?",":"") b; if(tot>=31){print c";"m; exit}}'
}
START=$(($(wc -l < $N/logs/seq_watcher.log)+1)); log "等 M4R 链完再起"
until tail -n +$START $N/logs/seq_watcher.log | grep -q "M4R链：M4R 链完"; do sleep 30; done
for attempt in $(seq 1 20); do
  until P=$(plan) && [ -n "$P" ]; do sleep 5; done
  DEV=${P%%;*}; MM=${P##*;}
  log "起跑（卡 $DEV，预算 $MM GiB，第 $attempt 次，已有 $(wc -l < $OUT 2>/dev/null || echo 0) 首）"
  (cd $N && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$DEV $PY gen_m8.py $OUT $N/outputs/merged_dpo_pt6 none $Q/titles_v15.json M4 --bs 8 --maxmem "$MM" >> $N/logs/m8_gen_v15_cands_M4.log 2>&1) &
  PID=$!; sleep 75
  bad=0; for c in ${DEV//,/ }; do foreign_new $c && bad=1; done
  if [ $bad = 1 ]; then kill $PID 2>/dev/null; wait $PID 2>/dev/null; log "与别人同时起跑，我方让"; sleep 90; continue; fi
  wait $PID; n=$(wc -l < $OUT 2>/dev/null || echo 0); log "退出，已有 $n 首"
  [ "$n" -ge 402 ] && { log "M4 候选完（$n 首）"; exit 0; }
  sleep 60
done
log "二十次未成"; exit 1
