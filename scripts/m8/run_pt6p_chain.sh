#!/bin/bash
# 实验 2「pt6+散文」链（09-22 20:30，主人「按你说的做」）：M4 的配方一字不改，只把 pt9 的 301 篇散文加进预训练。
# 段：pt6p_r32（7 轮，bf16 LoRA，约 5 小时）→ pt6p_anneal（1 轮）→ sft_pt6p（sft_v3，2 轮）→ dpo_pt6p（dpo_v1，参考=裸底座，3 轮）→ 面板 198（bf16 推理）。
# 与 M4 当年唯一的差别是数据集 cyberpoet_pt6p_full（pt6 6169 篇 + 散文 301 篇 = 291 万字）。配置里量化键已删（当年从未生效）。
# 拿卡：先等 M4 的 v15 候选跑完（两条链不共用占位协议）；bf16 LoRA 要 ≥34 GB，占到卡后核对「空余 + 占位持有」≥ 34000 MiB，不够就放掉再等。
# 日志前缀 pt6p链。断点：预训练段 save_only_model，没有优化器，失败重来；其余段同。
source /data/peilincai/CyberPoetTraining/claude_night_20260827/m8_gpu_lib.sh
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python; Q=$N/quiz_v3
NEED=34000
log(){ echo "[$(date +%m-%d_%H:%M)] pt6p链：$*" >> $N/logs/seq_watcher.log; }
held_on(){   # $1 卡：我方 gpu_sniper 在这张卡上持有的显存（MiB）
  local uuid=$(nvidia-smi --query-gpu=uuid --format=csv,noheader -i $1) t=0
  for row in $(nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader,nounits | tr -d ' ' | grep "$uuid"); do
    pid=$(echo $row | cut -d, -f2); mem=$(echo $row | cut -d, -f3)
    ps -o args= -p $pid 2>/dev/null | grep -q 'gpu_sniper.py' && t=$((t+mem))
  done; echo $t
}
acquire_big(){   # 输出卡号：占到的卡「空余+持有」≥ NEED 才算
  while true; do
    card=$(acquire_card)
    f=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $card | tr -d ' '); h=$(held_on $card)
    if [ $((f+h)) -ge $NEED ]; then echo $card; return; fi
    log "占到卡 $card 但只有 $((f+h)) MiB（空余 $f + 持有 $h）< $NEED，放掉再等"; release_all; sleep 300
  done
}
train_stage(){   # $1 名字(=输出目录名)  $2 配置
  for attempt in 1 2 3 4; do
    [ -f $N/outputs/$1/adapter_model.safetensors ] && { log "$1 已有成品，跳过"; return 0; }
    rm -rf $N/outputs/$1; card=$(acquire_big)
    log "$1 第 $attempt 次起跑（卡 $card）"
    LOG=$N/logs/$1_try$attempt.log; cd $R
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY $N/lf_nowarm.py $2 > $LOG 2>&1 &
    TPID=$!; trap "kill $TPID 2>/dev/null; release_all" TERM INT
    while kill -0 $TPID 2>/dev/null && ! grep -q "trainable params" $LOG 2>/dev/null; do sleep 3; done
    if kill -0 $TPID 2>/dev/null; then
      if grep -q "Quantizing model to 4 bit" $LOG; then kill $TPID; log "$1 日志里出现了量化 = 配方不对（M4 是 bf16），停链"; release_all; return 1; fi
      loaded_rearm $card
    fi
    wait $TPID; rc=$?; trap - TERM INT; log "$1 第 $attempt 次退出 rc=$rc"
    [ $rc -eq 0 ] && [ -f $N/outputs/$1/adapter_model.safetensors ] && return 0
    sleep 60
  done
  log "$1 四次未成，停链"; release_all; return 1
}
START=$(($(wc -l < $N/logs/seq_watcher.log)+1)); log "起：等 M4 的 v15 候选跑完再抢卡（bf16 LoRA 要 ≥34 GB）"
until tail -n +$START $N/logs/seq_watcher.log | grep -q "M4v15：M4 候选完"; do sleep 60; done
train_stage pt6p_r32    $N/configs/pt6p_full.yaml   || exit 1
train_stage pt6p_anneal $N/configs/pt6p_anneal.yaml || exit 1
train_stage sft_pt6p    $N/configs/sft_pt6p.yaml    || exit 1
train_stage dpo_pt6p    $N/configs/dpo_pt6p.yaml    || exit 1
# ---- 面板（bf16 推理，与 M4 同法：底座 + adapter）----
for a in 1 2 3; do card=$(acquire_big); log "面板 M4P（卡 $card）"; GL=$N/logs/m8_gen_M4P_panel_gens.log; : > $GL.cur
  (cd $N; PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY gen_m8.py $Q/M4P_panel_gens.jsonl models/Qwen3-14B $N/outputs/dpo_pt6p $Q/m8_titles_panel66.json M4P --bs 16 > $GL.cur 2>&1) & GPID=$!
  while kill -0 $GPID 2>/dev/null && ! grep -q "shards: 100%" $GL.cur 2>/dev/null; do sleep 3; done; kill -0 $GPID 2>/dev/null && loaded_rearm $card
  wait $GPID; rc=$?; cat $GL.cur >> $GL; [ $rc -eq 0 ] && break; sleep 30; done
release_all
$PY $N/m8_metrics.py $Q/M4P_panel_gens.jsonl >> $N/logs/m8_metrics.txt 2>&1
$PY $N/check_memorization.py $N/data/pt6p_train_full.json $Q/M4P_panel_gens.jsonl >> $N/logs/m8_memcheck.txt 2>&1
log "pt6p 链完：outputs/dpo_pt6p + quiz_v3/M4P_panel_gens.jsonl（数字在 logs/m8_metrics.txt）"
