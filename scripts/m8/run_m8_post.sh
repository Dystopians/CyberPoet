#!/bin/bash
# M8 训后流程（09-21）：等训练链全链训完 → 按训前写死的规则选偏好训练存档 → 面板验字数中位 → 出厂检生成 → v14 候选（M8、M8桥）。
# M8 一系是 4 位量化训出来的，生成也按同一套量化参数（--nf4）；M4 是 bf16 训的，候选另跑（需约 29 GB，见 run_m8_m4cands.sh）。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; R=/data/peilincai/CyberPoetTraining/cyberpoet_v1; PY=$R/.env/bin/python
log(){ echo "[$(date +%m-%d_%H:%M)] M8训后：$*" >> $N/logs/seq_watcher.log; }
wait_card(){   # $1 需求 MiB：挑空余最多且够用的卡，20 秒后复查
  while true; do
    best=""; bestfree=0
    while IFS=, read -r idx used total; do
      free=$((total-used)); if [ $free -ge $1 ] && [ $free -gt $bestfree ]; then best=$idx; bestfree=$free; fi
    done < <(nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits | tr -d ' ')
    if [ -n "$best" ]; then sleep 20
      used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $best | tr -d ' '); total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i $best | tr -d ' ')
      [ $((total-used)) -ge $1 ] && { echo $best; return; }
    fi
    sleep 60
  done
}
gen(){   # $1 输出  $2 底座  $3 adapter|none  $4 题表  $5 臂名  其余原样传给 gen_m8.py；断了重起自动续
  out=$1; shift
  for attempt in 1 2 3 4 5; do
    card=$(wait_card 20000)
    log "生成 $(basename $out)（卡 $card，第 $attempt 次）"
    cd $N && PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$card $PY gen_m8.py $out "$@" --nf4 --bs 32 >> $N/logs/m8_gen_$(basename $out .jsonl).log 2>&1 && return 0
    sleep 60
  done
  log "生成 $(basename $out) 五次未成"; return 1
}
START=$(($(wc -l < $N/logs/seq_watcher.log)+1))   # 只看本脚本起跑之后的新日志行（之前有一条「人工停链」旧记录）
while ! tail -n +$START $N/logs/seq_watcher.log | grep -q "M8链：全链训完"; do
  tail -n +$START $N/logs/seq_watcher.log | grep -q "M8链：.*停链" && { log "训练链已停，训后流程退出"; exit 1; }
  sleep 120
done
B=$N/outputs/merged_sft_m8; Q=$N/quiz_v3
# ---- P1 选存档（验证损失最低；差 <0.01 取更早）→ 面板验字数中位 120–300，不合格向更早一档退 ----
$PY $N/m8_select_ckpt.py > $N/logs/m8_select_ckpt.log 2>&1 || { log "选存档脚本失败"; exit 1; }
CHOSEN=""
for step in $($PY -c "import json;print(' '.join(str(s) for s in json.load(open('$N/m8_dpo_choice.json'))['order']))"); do
  P=$N/rca_20260905/M8_ck${step}_panel_gens.jsonl
  gen $P $B $N/outputs/dpo_m8/checkpoint-$step $Q/m8_titles_panel66.json M8_ck$step || exit 1
  med=$($PY - <<EOF
import json,re,statistics as st
b=[json.loads(l)["body"] for l in open("$P",encoding="utf-8")]
print(int(st.median(len(re.sub(r"\s+","",x)) for x in b)))
EOF
)
  log "checkpoint-$step 面板字数中位 $med"
  if [ "$med" -ge 120 ] && [ "$med" -le 300 ]; then CHOSEN=$step; break; fi
done
[ -z "$CHOSEN" ] && { log "没有一档的字数中位落在 120–300，停下等人看"; exit 1; }
echo $CHOSEN > $N/m8_dpo_chosen.txt; cp $N/rca_20260905/M8_ck${CHOSEN}_panel_gens.jsonl $Q/M8_panel_gens.jsonl
log "选定 checkpoint-$CHOSEN"
# ---- P1b 工作点补丁（训前写死，训练计划第五节第 3 条）：选中的存档训练奖励差 <1.0 时，另取奖励差最接近 2.0 的存档叫 M8w ----
M8W=$($PY -c "
import json
t=json.load(open('$N/m8_dpo_choice.json'))['table']; ch=int('$CHOSEN')
m={r['step']:r['train_margin_last3'] for r in t}
print('' if m[ch]>=1.0 else min(m,key=lambda s:abs(m[s]-2.0)))")
if [ -n "$M8W" ] && [ "$M8W" != "$CHOSEN" ]; then
  echo $M8W > $N/m8w_step.txt; log "选中的存档奖励差 <1.0 → 加工作点臂 M8w = checkpoint-$M8W"
  gen $Q/M8w_panel_gens.jsonl $B $N/outputs/dpo_m8/checkpoint-$M8W $Q/m8_titles_panel66.json M8w || exit 1
  gen $Q/v14_cands_M8w.jsonl  $B $N/outputs/dpo_m8/checkpoint-$M8W $Q/m8_titles_v14.json M8w || exit 1
else
  log "选中的存档奖励差 ≥1.0，不设 M8w"
fi
# ---- P2 桥的面板 + 两臂 v14 候选 + 关重复罚的复读诊断（48 题，题面不在桥数据 v5 里）----
gen $Q/M8sft_panel_gens.jsonl $B none $Q/m8_titles_panel66.json M8sft || exit 1
gen $Q/v14_cands_M8.jsonl    $B $N/outputs/dpo_m8/checkpoint-$CHOSEN $Q/m8_titles_v14.json M8 || exit 1
gen $Q/v14_cands_M8sft.jsonl $B none $Q/m8_titles_v14.json M8sft || exit 1
gen $N/rca_20260905/degen_m8.jsonl    $B $N/outputs/dpo_m8/checkpoint-$CHOSEN $Q/m8_titles_degen48.json M8    --seeds 7000 --rp 1.0 || exit 1
gen $N/rca_20260905/degen_m8sft.jsonl $B none $Q/m8_titles_degen48.json M8sft --seeds 7000 --rp 1.0 || exit 1
# ---- P3 合并再量化丢了多少（桥：训练时的样子 对 偏好训练的起点）----
card=$(wait_card 16000); cd $N && CUDA_VISIBLE_DEVICES=$card $PY m8_sftdev_nll.py $N/rca_20260905/m8_sftdev_nll.json "bridge_as_trained=models/Qwen3-14B:$N/outputs/sft_m8" "bridge_merged_requant=$B" > $N/logs/m8_sftdev_nll.log 2>&1
# ---- P4 数字 ----
$PY $N/m8_metrics.py $Q/M8sft_panel_gens.jsonl $Q/M8_panel_gens.jsonl $N/rca_20260905/degen_m8sft.jsonl $N/rca_20260905/degen_m8.jsonl $Q/v14_cands_M8.jsonl $Q/v14_cands_M8sft.jsonl > $N/logs/m8_metrics.txt 2>&1
python3 $N/check_memorization.py $N/data/pt9_s1.json $Q/M8_panel_gens.jsonl $Q/M8sft_panel_gens.jsonl $Q/v14_cands_M8.jsonl $Q/v14_cands_M8sft.jsonl > $N/logs/m8_memcheck.txt 2>&1
log "训后流程完：数字在 logs/m8_metrics.txt、logs/m8_memcheck.txt；候选在 quiz_v3/v14_cands_M8*.jsonl"
