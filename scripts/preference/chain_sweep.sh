#!/usr/bin/env bash
set -uo pipefail
W=/data/peilincai/CyberPoetTraining/claude_parallel_20260825
R=/data/peilincai/CyberPoetTraining/cyberpoet_v1
echo "[$(date +%H:%M)] 等 e4 与 e5 训练结束 …"
while pgrep -f 'configs_M1_e[45]\.yaml' >/dev/null; do sleep 60; done
echo "[$(date +%H:%M)] 训练都结束，开始四方对照生成"
cd "$R"
export HF_HOME="$R/.hf-home" HF_HUB_CACHE="$R/.hf-home/hub" TOKENIZERS_PARALLELISM=false
while true; do
  GPU=$(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits \
        | awk -F', ' '$2<1024 && $3<10 {print $1; exit}')
  [[ -n "${GPU:-}" ]] && break
  sleep 30
done
echo "[$(date +%H:%M)] 用 $GPU 号卡"
CUDA_VISIBLE_DEVICES=$GPU "$R/.env/bin/python" "$W/vocab_probe/gen_epoch_sweep.py"
echo "[$(date +%H:%M)] 生成完成，建 HTML 阅读包"
python3 "$W/vocab_probe/build_html_packet.py"
echo "[$(date +%H:%M)] 全部完成"
