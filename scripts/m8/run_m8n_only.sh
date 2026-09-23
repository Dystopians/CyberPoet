#!/bin/bash
# 09-22 03:40：M8n 消融臂单独接力（run_m8n_chain.sh 的 ③④ 段；①② 已由别的脚本完成，v14 已交付，本臂不补进 v14）。
# ③ 等一张卡（m8_gpu_lib 的规则：空余 ≥23900 先占位再装载；[21000,23900) 直接起）→ 消融偏好训练 dpo_m8n（与 dpo_m8b 只差数据：去掉 v1 时代 183 对，剩 174 对）
# ④ 按同一规则选存档（验证损失最低、并列取早、面板字数中位 120–300）→ 面板 198 → v14 题表候选 378 → 关重复罚诊断 48 → 数字与记忆核验。
source /data/peilincai/CyberPoetTraining/claude_night_20260827/m8_gpu_lib.sh
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python; Q=$N/quiz_v3; B=$N/outputs/merged_sft_m8b
log(){ echo "[$(date +%m-%d_%H:%M)] M8n链：$*" >> $N/logs/seq_watcher.log; }
log "起（等卡；此刻空余 $(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | tr -d ' ' | tr '\n' ' ')）"
# ---- ③ 消融偏好训练 ----
if [ ! -f $N/outputs/dpo_m8n/trainer_state.json ]; then
  rm -rf $N/outputs/dpo_m8n; card=$(acquire_card); log "dpo_m8n 起跑（卡 $card）"
  cd $R; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY $N/lf_nowarm.py $N/configs/dpo_m8n.yaml > $N/logs/dpo_m8n.log 2>&1 &
  TPID=$!; while kill -0 $TPID 2>/dev/null && ! grep -q "trainable params" $N/logs/dpo_m8n.log 2>/dev/null; do sleep 5; done
  kill -0 $TPID 2>/dev/null && { grep -q "Quantizing model to 4 bit" $N/logs/dpo_m8n.log || { kill $TPID; log "dpo_m8n 没量化，停"; exit 1; }; loaded_rearm $card; }
  wait $TPID; rc=$?; log "dpo_m8n 退出 rc=$rc"; [ $rc -eq 0 ] || { release_all; exit 1; }
fi
# ---- ④ 选存档（同一规则）→ 面板 → 候选 ----
DPO_DIR=$N/outputs/dpo_m8n OUT_JSON=$N/m8n_dpo_choice.json $PY $N/m8_select_ckpt.py > $N/logs/m8n_select_ckpt.log 2>&1 || { log "选存档失败"; release_all; exit 1; }
gen(){ out=$1; shift; for a in 1 2 3; do card=$(acquire_card); log "生成 $(basename $out)（卡 $card）"; GL=$N/logs/m8_gen_$(basename $out .jsonl).log; : > $GL.cur
  (cd $N; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY gen_m8.py $out "$@" --nf4 --bs 32 > $GL.cur 2>&1) & GPID=$!
  while kill -0 $GPID 2>/dev/null && ! grep -q "shards: 100%" $GL.cur 2>/dev/null; do sleep 3; done; kill -0 $GPID 2>/dev/null && loaded_rearm $card
  wait $GPID; rc=$?; cat $GL.cur >> $GL; [ $rc -eq 0 ] && return 0; sleep 10; done; return 1; }
CH=""; for step in $($PY -c "import json;print(' '.join(str(s) for s in json.load(open('$N/m8n_dpo_choice.json'))['order']))"); do
  P=$N/rca_20260905/M8n_ck${step}_panel_gens.jsonl; gen $P $B $N/outputs/dpo_m8n/checkpoint-$step $Q/m8_titles_panel66.json M8n_ck$step || { release_all; exit 1; }
  med=$($PY -c "
import json,re,statistics as st
b=[json.loads(l)['body'] for l in open('$P',encoding='utf-8')]; print(int(st.median(len(re.sub(r'\s+','',x)) for x in b)))")
  log "M8n checkpoint-$step 面板字数中位 $med"; if [ "$med" -ge 120 ] && [ "$med" -le 300 ]; then CH=$step; break; fi
done
[ -z "$CH" ] && { log "M8n 没有一档字数中位在 120–300"; release_all; exit 1; }
echo $CH > $N/m8n_dpo_chosen.txt; cp $N/rca_20260905/M8n_ck${CH}_panel_gens.jsonl $Q/M8n_panel_gens.jsonl; log "M8n 选定 checkpoint-$CH"
gen $Q/v14_cands_M8n.jsonl $B $N/outputs/dpo_m8n/checkpoint-$CH $Q/m8_titles_v14.json M8n || { release_all; exit 1; }
gen $N/rca_20260905/degen_m8n.jsonl $B $N/outputs/dpo_m8n/checkpoint-$CH $Q/m8_titles_degen48.json M8n --seeds 7000 --rp 1.0 || { release_all; exit 1; }
release_all
$PY $N/m8_metrics.py $Q/M8n_panel_gens.jsonl $N/rca_20260905/degen_m8n.jsonl $Q/v14_cands_M8n.jsonl >> $N/logs/m8_metrics.txt 2>&1
$PY $N/check_memorization.py $N/data/pt9_s1.json $Q/M8n_panel_gens.jsonl $Q/v14_cands_M8n.jsonl >> $N/logs/m8_memcheck.txt 2>&1
log "M8n 链完：quiz_v3/v14_cands_M8n.jsonl（$(wc -l < $Q/v14_cands_M8n.jsonl) 首）"
