#!/usr/bin/env bash
# 等前面两个作业结束 → 合并草稿 → 切分 → 抢一张空卡直接开训
set -uo pipefail
W=/data/peilincai/CyberPoetTraining/claude_parallel_20260825
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1

echo "[$(date +%H:%M)] 等草稿生成完成 …"
while true; do
  n=$(wc -l < "$W/sft_repair/flat_drafts.jsonl" 2>/dev/null || echo 0)
  [[ "$n" -ge 818 ]] && { echo "[$(date +%H:%M)] 草稿 $n 条，齐了"; break; }
  pgrep -f regen_flat_drafts.py >/dev/null || { echo "[$(date +%H:%M)] 草稿进程已退出，当前 $n 条，就用这些"; break; }
  sleep 30
done

echo "[$(date +%H:%M)] 把新草稿并进数据集 …"
python3 "$W/sft_repair/repair_sft_v2.py" || exit 1
python3 "$W/sft_repair/make_splits.py"  || exit 1

echo "[$(date +%H:%M)] 等 3 轮预训练结束 …"
while true; do
  [[ -f "$W/pretrain/outputs/e3/adapter_model.safetensors" ]] && \
    ! pgrep -f "pt_qwen3_14b_qlora_e3.yaml" >/dev/null && { echo "[$(date +%H:%M)] 预训练完成"; break; }
  sleep 30
done

# 抢卡：不排队，看到空的立刻用
echo "[$(date +%H:%M)] 找空卡 …"
while true; do
  GPU=$(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits \
        | awk -F', ' '$2 < 1024 && $3 < 10 {print $1; exit}')
  [[ -n "${GPU:-}" ]] && break
  sleep 20
done
echo "[$(date +%H:%M)] 占用 $GPU 号卡开训"

cd "$R"
export HF_HOME="$R/.hf-home" HF_HUB_CACHE="$R/.hf-home/hub" TOKENIZERS_PARALLELISM=false
export WANDB_ENTITY="karamazovaniki-university-of-southern-california"
export WANDB_PROJECT="cyberpoet-modern-poetry" WANDB_DIR="$W/sft_repair"
export WANDB_MODE=online WANDB_LOG_MODEL=false WANDB_CONSOLE=off WANDB_DISABLE_CODE=true WANDB_WATCH=false
export WANDB_RUN_GROUP="cyberpoet-repaired-sft"
export WANDB_RUN_ID="cyberpoet-pt-then-sft-$(date -u +%Y%m%dT%H%M%SZ)-$(cut -c1-8 /proc/sys/kernel/random/uuid)"
export WANDB_NAME="$WANDB_RUN_ID" WANDB_TAGS="repaired-sft,on-pretrain,claude-parallel"
export CUDA_VISIBLE_DEVICES=$GPU
echo "W&B: $WANDB_RUN_ID"
exec "$R/.env/bin/llamafactory-cli" train "$W/sft_repair/configs_sft_fixed.yaml"
