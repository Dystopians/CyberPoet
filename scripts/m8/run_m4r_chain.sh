#!/bin/bash
# 实验 1「M4R」链（09-22 19:50，主人「按你说的做」）：
# ① CPU 上把 M4 的桥 sft_pt6 合并成完整权重 merged_sft_pt6（参考=桥的前提）
# ② 等卡（m8_gpu_lib 规则）→ dpo_m4r（与 dpo_m8b 同配置，只换底座）；起跑后核对日志里有量化行
# ③ 存档不按验证损失挑：M4R = 训满 3 轮的末档；M4Rw = 训练奖励差最接近 2.0 的存档
# ④ 面板 198 首 × 三臂：桥本身（M4sft = merged_sft_pt6 不挂 adapter）/ M4R / M4Rw；关重复罚诊断 48 题
# ⑤ 等 quiz_v3/titles_v15.ready → 三臂 v15 候选（M4 的候选另由 run_m4_v15cands.sh 用 bf16 合并版生成）
# ⑥ 数字 + 记忆核验。日志 logs/seq_watcher.log（前缀 M4R链）
source /data/peilincai/CyberPoetTraining/claude_night_20260827/m8_gpu_lib.sh
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python; Q=$N/quiz_v3; B=$N/outputs/merged_sft_pt6
log(){ echo "[$(date +%m-%d_%H:%M)] M4R链：$*" >> $N/logs/seq_watcher.log; }
log "起（此刻空余 $(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | tr -d ' ' | tr '\n' ' ')）"
# ---- ① 合并（CPU）----
if [ ! -f $B/config.json ]; then
  log "合并 sft_pt6 → merged_sft_pt6（CPU）"
  (cd $N && CUDA_VISIBLE_DEVICES= $PY rca_20260905/merge_bridge.py $R/models/Qwen3-14B $N/outputs/sft_pt6 $B > $N/logs/merge_sft_pt6.log 2>&1) || { log "合并失败，见 logs/merge_sft_pt6.log"; exit 1; }
  log "合并完：$(du -sh $B | cut -f1)"
fi
# ---- ② 偏好训练 ----
if [ ! -f $N/outputs/dpo_m4r/trainer_state.json ]; then
  rm -rf $N/outputs/dpo_m4r; card=$(acquire_card); log "dpo_m4r 起跑（卡 $card）"
  cd $R; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY $N/lf_nowarm.py $N/configs/dpo_m4r.yaml > $N/logs/dpo_m4r.log 2>&1 &
  TPID=$!; while kill -0 $TPID 2>/dev/null && ! grep -q "trainable params" $N/logs/dpo_m4r.log 2>/dev/null; do sleep 5; done
  kill -0 $TPID 2>/dev/null && { grep -q "Quantizing model to 4 bit" $N/logs/dpo_m4r.log || { kill $TPID; log "dpo_m4r 没量化，停"; exit 1; }; loaded_rearm $card; }
  wait $TPID; rc=$?; log "dpo_m4r 退出 rc=$rc"; [ $rc -eq 0 ] || { release_all; exit 1; }
fi
# ---- ③ 选存档：末档 + 奖励差≈2 ----
read LAST WORK <<< "$($PY $N/m4r_pick.py $N/outputs/dpo_m4r)"
log "M4R = checkpoint-$LAST（末档）；M4Rw = checkpoint-$WORK（奖励差≈2）"
gen(){ out=$1; shift; for a in 1 2 3; do card=$(acquire_card); log "生成 $(basename $out)（卡 $card）"; GL=$N/logs/m8_gen_$(basename $out .jsonl).log; : > $GL.cur
  (cd $N; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY gen_m8.py $out "$@" --nf4 --bs 32 > $GL.cur 2>&1) & GPID=$!
  while kill -0 $GPID 2>/dev/null && ! grep -q "shards: 100%" $GL.cur 2>/dev/null; do sleep 3; done; kill -0 $GPID 2>/dev/null && loaded_rearm $card
  wait $GPID; rc=$?; cat $GL.cur >> $GL; [ $rc -eq 0 ] && return 0; sleep 10; done; return 1; }
# ---- ④ 面板 + 关重复罚 ----
gen $Q/M4R_panel_gens.jsonl   $B $N/outputs/dpo_m4r/checkpoint-$LAST $Q/m8_titles_panel66.json M4R   || { release_all; exit 1; }
gen $Q/M4Rw_panel_gens.jsonl  $B $N/outputs/dpo_m4r/checkpoint-$WORK $Q/m8_titles_panel66.json M4Rw  || { release_all; exit 1; }
gen $Q/M4sft_panel_gens.jsonl $B none $Q/m8_titles_panel66.json M4sft || { release_all; exit 1; }
gen $N/rca_20260905/degen_m4r.jsonl $B $N/outputs/dpo_m4r/checkpoint-$LAST $Q/m8_titles_degen48.json M4R --seeds 7000 --rp 1.0 || { release_all; exit 1; }
release_all
$PY $N/m8_metrics.py $Q/M4R_panel_gens.jsonl $Q/M4Rw_panel_gens.jsonl $Q/M4sft_panel_gens.jsonl $N/rca_20260905/degen_m4r.jsonl >> $N/logs/m8_metrics.txt 2>&1
log "面板完（数字在 logs/m8_metrics.txt）；等 quiz_v3/titles_v15.ready"
# ---- ⑤ v15 候选 ----
until [ -f $Q/titles_v15.ready ]; do sleep 30; done
gen $Q/v15_cands_M4R.jsonl   $B $N/outputs/dpo_m4r/checkpoint-$LAST $Q/titles_v15.json M4R   || { release_all; exit 1; }
gen $Q/v15_cands_M4Rw.jsonl  $B $N/outputs/dpo_m4r/checkpoint-$WORK $Q/titles_v15.json M4Rw  || { release_all; exit 1; }
gen $Q/v15_cands_M4sft.jsonl $B none $Q/titles_v15.json M4sft || { release_all; exit 1; }
release_all
$PY $N/m8_metrics.py $Q/v15_cands_M4R.jsonl $Q/v15_cands_M4Rw.jsonl $Q/v15_cands_M4sft.jsonl >> $N/logs/m8_metrics.txt 2>&1
$PY $N/check_memorization.py $N/data/pt6_train_full.json $Q/M4R_panel_gens.jsonl $Q/M4Rw_panel_gens.jsonl $Q/M4sft_panel_gens.jsonl $Q/v15_cands_M4R.jsonl $Q/v15_cands_M4Rw.jsonl $Q/v15_cands_M4sft.jsonl >> $N/logs/m8_memcheck.txt 2>&1
log "M4R 链完：三臂候选各 $(wc -l < $Q/v15_cands_M4R.jsonl) 首"
