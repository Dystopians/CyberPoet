#!/bin/bash
# v14 的 M4 候选（09-21）：M4 是 bf16 训的，照旧 bf16 推理，要约 29 GB——单卡不够就切到两张卡（gen_m8.py 按各卡空余自动切）。
# 等 M8 训后流程跑完再起（6 号卡那时才腾得出来）；生成参数与 M8 两臂逐项相同（同题表、同三颗种子、温度 0.9、top_p 0.9、重复罚 1.08、上限 560）。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python
log(){ echo "[$(date +%m-%d_%H:%M)] M8训后：$*" >> $N/logs/seq_watcher.log; }
START=$(($(wc -l < $N/logs/seq_watcher.log)+1))
[ "$1" = "now" ] || while ! tail -n +$START $N/logs/seq_watcher.log | grep -q "M8训后：训后流程完"; do sleep 120; done
pick(){   # 输出 "A" 或 "A,B"：单卡空余 ≥31 GB 用单卡；否则最空的两张卡合计（各留 2.5 GB）≥30 GB 且第二张 ≥6 GB
  mapfile -t rows < <(nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits | tr -d ' ' | awk -F, '{print $3-$2","$1}' | sort -t, -k1 -nr)
  fa=${rows[0]%%,*}; a=${rows[0]##*,}; fb=${rows[1]%%,*}; b=${rows[1]##*,}
  if [ $fa -ge 31000 ]; then echo $a; return 0; fi
  if [ $((fa-2560+fb-2560)) -ge 30000 ] && [ $fb -ge 6000 ]; then echo "$a,$b"; return 0; fi
  return 1
}
for attempt in 1 2 3 4 5 6; do
  until cards=$(pick); do sleep 120; done
  sleep 20; cards2=$(pick) || continue; [ "$cards" = "$cards2" ] || continue
  log "M4 候选起跑（卡 $cards，bf16，第 $attempt 次）"
  cd $N && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$cards $PY gen_m8.py $N/quiz_v3/v14_cands_M4.jsonl models/Qwen3-14B $N/outputs/dpo_pt6 $N/quiz_v3/m8_titles_v14.json M4 --bs 8 >> $N/logs/m8_gen_v14_cands_M4.log 2>&1 && { log "M4 候选完：quiz_v3/v14_cands_M4.jsonl"; exit 0; }
  log "M4 候选第 $attempt 次退出，稍后续跑"; sleep 120
done
log "M4 候选六次未成"; exit 1
