#!/bin/bash
# 09-22 凌晨接力链：① 等 M8b 训后流程完 → ② M4 候选（bf16 30 GB，拆到 4+5 两张卡：4 号放 21 GiB、5 号放 8 GiB）→ ③ 消融偏好训练 dpo_m8n（去掉 v1 时代对）→ ④ 按同一规则选存档 → 面板 → 候选 M8n → 复读诊断 → 数字。
source /data/peilincai/CyberPoetTraining/claude_night_20260827/m8_gpu_lib.sh
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python; Q=$N/quiz_v3; B=$N/outputs/merged_sft_m8b
log(){ echo "[$(date +%m-%d_%H:%M)] M8n链：$*" >> $N/logs/seq_watcher.log; }
free_of(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $1 | tr -d ' '; }
START=$(($(wc -l < $N/logs/seq_watcher.log)+1))
until tail -n +$START $N/logs/seq_watcher.log | grep -q "M8训后：训后流程完"; do sleep 20; done
release_all; sleep 3
# ---- ② M4 候选：等 4 号卡 ≥23 GB 且 5 号卡 ≥10 GB（或任一张卡 ≥31 GB 单卡），立即起跑，60 秒后查撞车 ----
OUT=$Q/v14_cands_M4.jsonl
for attempt in $(seq 1 12); do
  while true; do
    c1=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | tr -d ' ' | awk -F, '$2>=31000{print $2","$1}' | sort -t, -k1 -nr | head -n 1 | cut -d, -f2)
    if [ -n "$c1" ]; then DEV=$c1; MM=""; break; fi
    if [ "$(free_of 4)" -ge 23000 ] && [ "$(free_of 5)" -ge 10000 ]; then DEV="4,5"; MM="--maxmem 21,8"; break; fi
    if [ "$(free_of 5)" -ge 23000 ] && [ "$(free_of 4)" -ge 10000 ]; then DEV="5,4"; MM="--maxmem 21,8"; break; fi
    sleep 5
  done
  log "M4 候选起跑（卡 $DEV，bf16，第 $attempt 次，已有 $(wc -l < $OUT 2>/dev/null || echo 0) 首）"
  (cd $N && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$DEV $PY gen_m8.py $OUT models/Qwen3-14B $N/outputs/dpo_pt6 $Q/m8_titles_v14.json M4 --bs 16 $MM >> $N/logs/m8_gen_v14_cands_M4.log 2>&1) &
  P=$!; sleep 60
  bad=0; for c in ${DEV//,/ }; do foreign_new $c && bad=1; done
  if [ $bad = 1 ]; then kill $P 2>/dev/null; wait $P 2>/dev/null; log "M4 候选与别人同时起跑，我方让"; sleep 90; continue; fi
  wait $P; n=$(wc -l < $OUT 2>/dev/null || echo 0); log "M4 候选退出，已有 $n 首"
  [ "$n" -ge 378 ] && break; sleep 60
done
# ---- ③ 消融偏好训练 ----
if [ ! -f $N/outputs/dpo_m8n/trainer_state.json ]; then
  rm -rf $N/outputs/dpo_m8n; card=$(acquire_card); log "dpo_m8n 起跑（卡 $card）"
  cd $R; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY $N/lf_nowarm.py $N/configs/dpo_m8n.yaml > $N/logs/dpo_m8n.log 2>&1 &
  TPID=$!; while kill -0 $TPID 2>/dev/null && ! grep -q "trainable params" $N/logs/dpo_m8n.log 2>/dev/null; do sleep 5; done
  kill -0 $TPID 2>/dev/null && { grep -q "Quantizing model to 4 bit" $N/logs/dpo_m8n.log || { kill $TPID; log "dpo_m8n 没量化，停"; exit 1; }; loaded_rearm $card; }
  wait $TPID; rc=$?; log "dpo_m8n 退出 rc=$rc"; [ $rc -eq 0 ] || exit 1
fi
# ---- ④ 选存档（同一规则）→ 面板 → 候选 ----
DPO_DIR=$N/outputs/dpo_m8n OUT_JSON=$N/m8n_dpo_choice.json $PY $N/m8_select_ckpt.py > $N/logs/m8n_select_ckpt.log 2>&1 || { log "选存档失败"; exit 1; }
gen(){ out=$1; shift; for a in 1 2 3; do card=$(acquire_card); log "生成 $(basename $out)（卡 $card）"; GL=$N/logs/m8_gen_$(basename $out .jsonl).log; : > $GL.cur
  (cd $N; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY gen_m8.py $out "$@" --nf4 --bs 32 > $GL.cur 2>&1) & GPID=$!
  while kill -0 $GPID 2>/dev/null && ! grep -q "shards: 100%" $GL.cur 2>/dev/null; do sleep 3; done; kill -0 $GPID 2>/dev/null && loaded_rearm $card
  wait $GPID; rc=$?; cat $GL.cur >> $GL; [ $rc -eq 0 ] && return 0; sleep 10; done; return 1; }
CH=""; for step in $($PY -c "import json;print(' '.join(str(s) for s in json.load(open('$N/m8n_dpo_choice.json'))['order']))"); do
  P=$N/rca_20260905/M8n_ck${step}_panel_gens.jsonl; gen $P $B $N/outputs/dpo_m8n/checkpoint-$step $Q/m8_titles_panel66.json M8n_ck$step || exit 1
  med=$($PY -c "
import json,re,statistics as st
b=[json.loads(l)['body'] for l in open('$P',encoding='utf-8')]; print(int(st.median(len(re.sub(r'\s+','',x)) for x in b)))")
  log "M8n checkpoint-$step 面板字数中位 $med"; if [ "$med" -ge 120 ] && [ "$med" -le 300 ]; then CH=$step; break; fi
done
[ -z "$CH" ] && { log "M8n 没有一档字数中位在 120–300"; exit 1; }
echo $CH > $N/m8n_dpo_chosen.txt; cp $N/rca_20260905/M8n_ck${CH}_panel_gens.jsonl $Q/M8n_panel_gens.jsonl; log "M8n 选定 checkpoint-$CH"
gen $Q/v14_cands_M8n.jsonl $B $N/outputs/dpo_m8n/checkpoint-$CH $Q/m8_titles_v14.json M8n || exit 1
gen $N/rca_20260905/degen_m8n.jsonl $B $N/outputs/dpo_m8n/checkpoint-$CH $Q/m8_titles_degen48.json M8n --seeds 7000 --rp 1.0 || exit 1
release_all
$PY $N/m8_metrics.py $Q/M8n_panel_gens.jsonl $N/rca_20260905/degen_m8n.jsonl $Q/v14_cands_M8n.jsonl >> $N/logs/m8_metrics.txt 2>&1
python3 $N/check_memorization.py $N/data/pt9_s1.json $Q/M8n_panel_gens.jsonl $Q/v14_cands_M8n.jsonl >> $N/logs/m8_memcheck.txt 2>&1
log "M8n 链完"
