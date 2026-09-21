#!/bin/bash
# M8 重训链 v3（09-21 06:45）。与 v1/v2 的差别只在「怎么拿卡」：用 m8_gpu_lib.sh 的预热占位协议（不再裸抢，避免和别的用户的批量任务同时起跑、两败俱伤）。
# 段：末段预训练 pt10_s3（已有成品，跳过）→ 新桥 sft_m8 → CPU 合并 → 偏好训练 dpo_m8。断点续训（最多 6 次）、两道量化闸、关显存预热，同 v1。
source /data/peilincai/CyberPoetTraining/claude_night_20260827/m8_gpu_lib.sh
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python
log(){ echo "[$(date +%m-%d_%H:%M)] M8链：$*" >> $N/logs/seq_watcher.log; }
train_stage(){   # $1 名字  $2 配置  $3 可否续训(yes/no)
  for attempt in 1 2 3 4 5 6; do
    [ -f $N/outputs/$1/adapter_model.safetensors ] && { log "$1 已有成品，跳过"; return 0; }
    card=$(acquire_card); CFG=$2
    if [ "$3" = "yes" ]; then
      ck=$(ls -d $N/outputs/$1/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -n 1)
      if [ -n "$ck" ] && [ -f "$ck/optimizer.pt" ]; then CFG=$N/configs/$1_resume.yaml; grep -v "^resume_from_checkpoint" $2 > $CFG; echo "resume_from_checkpoint: $ck" >> $CFG; fi
    else
      rm -rf $N/outputs/$1
    fi
    log "$1 第 $attempt 次起跑（卡 $card 已占位，配置 $(basename $CFG)）"
    grep -q "^quantization_method: bnb" $CFG || { log "$1 配置里量化方式不是 bnb，停链"; release_all; return 1; }
    LOG=$N/logs/$1_v3try$attempt.log
    cd $R
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY $N/lf_nowarm.py $CFG > $LOG 2>&1 &
    TPID=$!; trap "kill $TPID 2>/dev/null; release_all" TERM INT
    while kill -0 $TPID 2>/dev/null && ! grep -q "trainable params" $LOG 2>/dev/null; do sleep 3; done
    if kill -0 $TPID 2>/dev/null; then
      if ! grep -q "Quantizing model to 4 bit with bitsandbytes" $LOG; then kill $TPID; log "$1 日志里没有 4 位量化那一行 = 量化没生效，停链"; release_all; return 1; fi
      loaded_rearm $card                              # 模型装好：释放占位，再挂一个预热占位接住本段结束的那一刻
    fi
    wait $TPID; rc=$?; trap - TERM INT; log "$1 第 $attempt 次退出 rc=$rc"
    [ $rc -eq 0 ] && [ -f $N/outputs/$1/adapter_model.safetensors ] && return 0
    sleep 10
  done
  log "$1 六次未成，停链"; release_all; return 1
}
PT_START=$(cat $N/m8_pt_start.txt); sed "s#__PT_START__#$PT_START#" $N/configs/pt10_s3.yaml > $N/configs/pt10_s3_resolved.yaml
train_stage pt10_s3 $N/configs/pt10_s3_resolved.yaml yes || exit 1
train_stage sft_m8 $N/configs/sft_m8.yaml yes || exit 1
if [ ! -f $N/outputs/merged_sft_m8/config.json ]; then
  log "合并新桥 → merged_sft_m8（CPU）"
  CUDA_VISIBLE_DEVICES="" $PY $N/rca_20260905/merge_bridge.py $R/models/Qwen3-14B $N/outputs/sft_m8 $N/outputs/merged_sft_m8 > $N/logs/merge_sft_m8.log 2>&1 || { log "合并失败，停链"; release_all; exit 1; }
fi
train_stage dpo_m8 $N/configs/dpo_m8.yaml no || exit 1
log "全链训完：outputs/dpo_m8（逐 9 步存档 + 验证票指标）"
