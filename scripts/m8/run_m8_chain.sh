#!/bin/bash
# M8 重训链（09-21）：见缝插针占卡。每段起跑前找一张「空余显存 ≥ 需求」的卡（任何卡都行），20 秒后复查再占；
# 训练段死了从最近存档续训（最多 6 次）。关掉 transformers 显存预热（lf_nowarm.py），加载峰值 9.6 GB。
# 段：S1 末段预训练 pt10_s3 → S2 新桥 sft_m8（干净开发集早停）→ S3 合并成完整权重（CPU）→ S4 偏好训练 dpo_m8（参考=桥，留验证票）
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python
log(){ echo "[$(date +%m-%d_%H:%M)] M8链：$*" >> $N/logs/seq_watcher.log; }
wait_card(){
  while true; do
    best=""; bestfree=0
    while IFS=, read -r idx used total; do
      free=$((total-used)); if [ $free -ge $1 ] && [ $free -gt $bestfree ]; then best=$idx; bestfree=$free; fi
    done < <(nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits | tr -d ' ')
    if [ -n "$best" ]; then
      sleep 20
      used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $best | tr -d ' '); total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i $best | tr -d ' ')
      if [ $((total-used)) -ge $1 ]; then echo $best; return; fi
    fi
    sleep 60
  done
}
train_stage(){   # $1 名字  $2 配置  $3 需求MiB  $4 可否续训(yes/no)
  for attempt in 1 2 3 4 5 6; do
    [ -f $N/outputs/$1/adapter_model.safetensors ] && { log "$1 已有成品，跳过"; return 0; }
    card=$(wait_card $3); CFG=$2
    if [ "$4" = "yes" ]; then
      ck=$(ls -d $N/outputs/$1/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -n 1)
      if [ -n "$ck" ] && [ -f "$ck/optimizer.pt" ]; then CFG=$N/configs/$1_resume.yaml; grep -v "^resume_from_checkpoint" $2 > $CFG; echo "resume_from_checkpoint: $ck" >> $CFG; fi
    else
      rm -rf $N/outputs/$1
    fi
    log "$1 第 $attempt 次起跑（卡 $card，配置 $(basename $CFG)）"
    grep -q "^quantization_method: bnb" $CFG || { log "$1 配置里量化方式不是 bnb（写成别的库不报错、直接不量化），停链"; return 1; }
    LOG=$N/logs/$1_try$attempt.log
    cd $R
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY $N/lf_nowarm.py $CFG > $LOG 2>&1 &
    TPID=$!; trap "kill $TPID 2>/dev/null" TERM INT
    # 量化是否真的生效：等到模型装完（日志出现 trainable params）或进程退出，再查 4 位量化那行在不在
    while kill -0 $TPID 2>/dev/null && ! grep -q "trainable params" $LOG 2>/dev/null; do sleep 10; done
    if kill -0 $TPID 2>/dev/null && ! grep -q "Quantizing model to 4 bit with bitsandbytes" $LOG; then kill $TPID; log "$1 日志里没有 4 位量化那一行 = 量化没生效，停链"; return 1; fi
    wait $TPID; rc=$?; trap - TERM INT; log "$1 第 $attempt 次退出 rc=$rc"
    [ $rc -eq 0 ] && [ -f $N/outputs/$1/adapter_model.safetensors ] && return 0
    sleep 120
  done
  log "$1 六次未成，停链"; return 1
}
# ---- S1 ----
while [ ! -f $N/m8_pt_start.txt ]; do sleep 30; done
PT_START=$(cat $N/m8_pt_start.txt); [ -f "$PT_START/adapter_model.safetensors" ] || { log "起点 $PT_START 无 adapter，停链"; exit 1; }
sed "s#__PT_START__#$PT_START#" $N/configs/pt10_s3.yaml > $N/configs/pt10_s3_resolved.yaml
log "预训练起点 = $PT_START"
train_stage pt10_s3 $N/configs/pt10_s3_resolved.yaml 19000 yes || exit 1
# ---- S2 ----
train_stage sft_m8 $N/configs/sft_m8.yaml 19000 yes || exit 1
# ---- S3 ----
if [ ! -f $N/outputs/merged_sft_m8/config.json ]; then
  log "合并新桥 → merged_sft_m8（CPU）"
  CUDA_VISIBLE_DEVICES="" $PY $N/rca_20260905/merge_bridge.py $R/models/Qwen3-14B $N/outputs/sft_m8 $N/outputs/merged_sft_m8 > $N/logs/merge_sft_m8.log 2>&1 || { log "合并失败，停链"; exit 1; }
fi
# ---- S4 ----
train_stage dpo_m8 $N/configs/dpo_m8.yaml 17000 no || exit 1
log "全链训完：outputs/dpo_m8（逐 9 步存档 + 验证票指标）"
