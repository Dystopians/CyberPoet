# M8 占卡公共函数（09-21 06:40）。被 run_m8_chain3.sh / run_m8_post.sh source。
# 背景见 gpu_sniper.py：另一位用户的批量脚本钉着每张卡，空余 ≥24000 MiB（nvidia-smi 的 free）就起下一个任务，不够就每 60 秒再查。
# 协议：① 预热占位进程先挂在候选卡上（只占约 0.45 GB），卡一空出来就瞬间占到「空余刚好低于 24000」为止（空卡约 24 GiB，6 号卡约 6 GiB）→ 对方按自己的规则排队，不会被撞死；
#       ② 占到后等 20 秒，确认这张卡上没有新冒出来的别人进程（万一同时起跑，我方让：释放、重来）；
#       ③ 我方任务在占位保护下装载，装好后释放占位，并立刻再挂一个预热占位，等我方任务结束的那一刻接住这张卡（护住段间空档）；
#       ④ 每个占位最长 20 分钟自动退出。
N=/data/peilincai/CyberPoetTraining/claude_night_20260827; PYV=/data/peilincai/CyberPoetTraining/cyberpoet_v1/.env/bin/python
SNIPE_DIR=$N/logs/snipe; mkdir -p $SNIPE_DIR
# 候选卡与触发线（MiB，torch 口径的空余）：6 号卡（常驻服务 18.8 GB）与 3 号卡（07:40 起无常驻任务）。
# 5 号卡不用：那张卡常驻服务占 22.7 GB，对方任务装载瞬间冲到过 47.2 GB（06:34 实测只剩 1.3 GB），我方哪怕 0.5 GB 的预热上下文都可能成为压垮它的那一根；4 号卡更贴线。
declare -A SNIPE_NEED=( [4]=23900 [3]=23900 [6]=23900 [7]=23900 [1]=23900 [2]=23900 [0]=23900 )   # 09-21 21:40：4 号卡刚空出 25 GB（F2 已停）；09-22 20:35 加 7 号卡（常驻 26.8 GB，空 21.7 GB 落在直接起跑带）
DIRECT_NEED=21000                      # 空余在 [21000, 23900) 之间：对方起不来（<24000），我方够用（每段 ≤17 GB，留 4 GB 余量）→ 不必占位，直接起跑
snipe_seq(){ n=$(cat $SNIPE_DIR/seq 2>/dev/null || echo 0); n=$((n+1)); echo $n > $SNIPE_DIR/seq; echo $n; }
snipe_alive(){ pgrep -f "gpu_snipe[r].py [0-9]+ [0-9]+ [a-z0-9.]+ $SNIPE_DIR/$1.claim" >/dev/null; }
snipe_launch(){   # $1 序号  其余=卡列表
  local n=$1; shift; rm -f $SNIPE_DIR/$n.claim $SNIPE_DIR/$n.release
  for c in "$@"; do
    CUDA_VISIBLE_DEVICES=$c nohup $PYV $N/gpu_sniper.py $c ${SNIPE_NEED[$c]} auto $SNIPE_DIR/$n.claim $SNIPE_DIR/$n.release 1200 >> $SNIPE_DIR/$n.card$c.log 2>&1 &
  done
  echo $n > $SNIPE_DIR/current
}
foreign_new(){    # $1 卡：这张卡上有没有最近 90 秒内起来的别人进程
  local uuid=$(nvidia-smi --query-gpu=uuid --format=csv,noheader -i $1)
  for p in $(nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv,noheader | grep "$uuid" | cut -d, -f2 | tr -d ' '); do
    [ "$(ps -o user= -p $p 2>/dev/null | tr -d ' ')" = "$(whoami)" ] && continue
    et=$(ps -o etimes= -p $p 2>/dev/null | tr -d ' '); [ -n "$et" ] && [ "$et" -lt 90 ] && return 0
  done
  return 1
}
acquire_card(){   # 输出卡号。已有占位（上一段留下的）就直接用；否则在候选卡上挂预热占位，等到为止
  while true; do
    n=$(cat $SNIPE_DIR/current 2>/dev/null || echo 0)
    if ! { [ -f $SNIPE_DIR/$n.claim ] && snipe_alive $n; }; then
      if ! snipe_alive $n || [ -f $SNIPE_DIR/$n.release ]; then n=$(snipe_seq); snipe_launch $n "${!SNIPE_NEED[@]}"; fi
      for i in $(seq 1 15); do [ -f $SNIPE_DIR/$n.claim ] && break; sleep 1; done    # 先给占位 15 秒：能占到就用占到的卡，占不到才看直接起跑带
      while [ ! -f $SNIPE_DIR/$n.claim ]; do
        snipe_alive $n || break
        for c in "${!SNIPE_NEED[@]}"; do      # 直接起跑带：卡上还有第三方的小任务时，空余到不了占位线，但对方同样起不来
          f=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $c | tr -d ' ')
          if [ "$f" -ge $DIRECT_NEED ] && [ "$f" -lt ${SNIPE_NEED[$c]} ]; then sleep 3
            f=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $c | tr -d ' ')
            if [ "$f" -ge $DIRECT_NEED ] && [ "$f" -lt ${SNIPE_NEED[$c]} ] && [ ! -f $SNIPE_DIR/$n.claim ]; then echo $c; return; fi
          fi
        done
        sleep 1
      done
      [ -f $SNIPE_DIR/$n.claim ] || continue
      sleep 20
    fi
    card=$(cat $SNIPE_DIR/$n.claim)
    if foreign_new $card; then touch $SNIPE_DIR/$n.release; sleep 5; continue; fi   # 同时起跑了：我方让
    snipe_alive $n || continue
    echo $card; return
  done
}
loaded_rearm(){   # $1 卡：我方任务已装好 → 释放当前占位，并再挂一个预热占位，等我方任务结束时接住这张卡
  n=$(cat $SNIPE_DIR/current 2>/dev/null || echo 0); touch $SNIPE_DIR/$n.release; sleep 2
  n=$(snipe_seq); snipe_launch $n $1
}
release_all(){ for f in $SNIPE_DIR/*.claim; do [ -e "$f" ] && touch ${f%.claim}.release; done; n=$(cat $SNIPE_DIR/current 2>/dev/null || echo 0); touch $SNIPE_DIR/$n.release; pkill -f "gpu_snipe[r][.]py [0-9]+ [0-9]+ [a-z0-9.]+ $SNIPE_DIR/" 2>/dev/null; true; }   # 模式带上数字参数：只打占位进程本身，不误伤命令行里恰好带这个文件名的别的 shell（07:14 误杀过训后流程）
