#!/bin/bash
# v14 的 M4 候选（09-21，v2）：M4 是 bf16 训的，照旧 bf16 推理，要约 30 GB——6 号卡放 24 GiB 权重，其余（约 3.5 GiB）切到第二张卡。
# 生成参数与 M8 两臂逐项相同（同题表、同三颗种子、温度 0.9、top_p 0.9、重复罚 1.08、上限 560）。
# 拿卡走预热占位协议（m8_gpu_lib.sh），只认 6 号卡（别的卡连对方不在时也放不下 25 GiB）。
# M4 自己装到 8 GB 以上才释放占位——这样 6 号卡的空余始终低于对方脚本的起跑线（24 GB），装载的一两分钟里不会有人同时挤进来。
source /data/peilincai/CyberPoetTraining/claude_night_20260827/m8_gpu_lib.sh
unset SNIPE_NEED; declare -A SNIPE_NEED=( [6]=25000 )
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python
log(){ echo "[$(date +%m-%d_%H:%M)] M8训后：$*" >> $N/logs/seq_watcher.log; }
START=$(($(wc -l < $N/logs/seq_watcher.log)+1))
[ "$1" = "now" ] || while ! tail -n +$START $N/logs/seq_watcher.log | grep -q "M8训后：训后流程完"; do sleep 15; done
second_card(){   # 第二张卡：除 6 号外空余最多、且 ≥8000 MiB 的
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | tr -d ' ' | awk -F, '$1!=6 && $2>=8000{print $2","$1}' | sort -t, -k1 -nr | head -n 1 | cut -d, -f2
}
for attempt in 1 2 3 4 5 6; do
  until c2=$(second_card) && [ -n "$c2" ]; do sleep 60; done
  card=$(acquire_card)
  log "M4 候选起跑（卡 $card + 卡 $c2，bf16，第 $attempt 次）"
  ML=$N/logs/m8_gen_v14_cands_M4.log
  cd $N; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card,$c2 $PY gen_m8.py $N/quiz_v3/v14_cands_M4.jsonl models/Qwen3-14B $N/outputs/dpo_pt6 $N/quiz_v3/m8_titles_v14.json M4 --bs 8 --maxmem "24,6" >> $ML 2>&1 &
  MPID=$!
  # M4 进程在 6 号卡上占到 8000 MiB 以上 → 释放占位并重新挂一个预热占位（接住 M4 结束的那一刻，护住后续收尾）
  while kill -0 $MPID 2>/dev/null; do
    m=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits -i $card | tr -d ' ' | awk -F, -v p=$MPID '$1==p{print $2}')
    [ -n "$m" ] && [ "$m" -ge 8000 ] && break; sleep 2
  done
  kill -0 $MPID 2>/dev/null && { n=$(cat $SNIPE_DIR/current); touch $SNIPE_DIR/$n.release; }
  wait $MPID && { log "M4 候选完：quiz_v3/v14_cands_M4.jsonl"; release_all; exit 0; }
  log "M4 候选第 $attempt 次退出，稍后续跑"; sleep 30
done
log "M4 候选六次未成"; release_all; exit 1
