"""预热占位（09-21）。背景：这台机器上另一位用户的批量评测脚本钉着每张卡，卡上空余 ≥24 GB 就起下一个任务（每个 30–70 分钟），
任务之间只隔几秒。06:22 / 06:26 两次：我方训练进程装载要 30–60 秒，对方同时起跑，两边一起申请显存，我方溢出（换个先后就是对方溢出）。
做法：提前在目标卡上建好 CUDA 上下文（约 0.4 GB），每 0.1 秒查一次空余；对方任务一结束（空余 ≥ need_free）立刻占 hold GiB——
之后对方脚本查到空余 <24 GB 会按它自己的规则排队等，不会被撞死；我方训练在占位保护下装载，装好后释放占位。
多张卡各挂一个，先占到的写 claim 文件，其余自动退出。最长占 max_hold 秒，绝不长期空占。
用法: CUDA_VISIBLE_DEVICES=<卡> gpu_sniper.py <卡号> <need_free_MiB> <hold_GiB> <claim_file> <release_file> <max_hold_s>"""
import sys, os, time, torch
card, need, claim, rel, max_hold = sys.argv[1], int(sys.argv[2]), sys.argv[4], sys.argv[5], int(sys.argv[6])
AUTO = sys.argv[3] == "auto"; hold_gib = None if AUTO else float(sys.argv[3])
KEEP_FREE = 23400   # auto：占到「空余刚好低于对方起跑线 24000」为止——空卡上约占 24 GiB，有常驻服务的 6 号卡上约占 6 GiB，对方任务同卡在跑时只占几 GiB；给我方下一段留 23 GB
torch.cuda.init(); torch.zeros(1, device="cuda")
print(f"[{time.strftime('%H:%M:%S')}] 卡 {card} 预热完成，等空余 ≥{need} MiB", flush=True)
while True:
    if os.path.exists(claim): print("别的卡已占到，退出", flush=True); sys.exit(0)
    if os.path.exists(rel): print("未占到即被释放（我方任务已直接起跑），退出", flush=True); sys.exit(0)
    free = torch.cuda.mem_get_info()[0] // 2**20
    if free >= need:
        if AUTO: hold_gib = max(0.25, (free - KEEP_FREE) / 1024)
        try:
            x = torch.empty(int(hold_gib * 2**30), dtype=torch.uint8, device="cuda")
        except Exception as e:
            print("占位申请失败，继续等:", str(e)[:80], flush=True); time.sleep(1); continue
        try:
            fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, card.encode()); os.close(fd)
        except FileExistsError:
            print("同时占到，让给先到的，退出", flush=True); sys.exit(0)
        print(f"[{time.strftime('%H:%M:%S')}] 卡 {card} 空余 {free} MiB → 已占 {hold_gib:.1f} GiB", flush=True)
        break
    time.sleep(0.1)
t0 = time.time()
while time.time() - t0 < max_hold and not os.path.exists(rel): time.sleep(0.5)
print(f"[{time.strftime('%H:%M:%S')}] 释放", "（标记）" if os.path.exists(rel) else "（到时）", flush=True)
