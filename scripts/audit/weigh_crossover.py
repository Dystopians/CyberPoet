# 决定性检验：舍入地板机制能不能做出**定量预言**并被数据证实。
# 机制推导：
#   每层可训练步数 = 574 步 /(40 层 × switch_interval 2) ≈ 7.2 轮 × 2 步 ≈ 14 步
#   Adam 单步位移上界 ≈ lr = 1e-5；14 步随机游走累积 ≈ sqrt(14)×1e-5 ≈ 3.7e-5
#   bf16 ULP(|w|) = |w| × 2^-8
#   → 舍入临界点：|w|* = 3.7e-5 × 256 ≈ 9.5e-3
# 预言：零变化率应在 |w| ≈ 1e-2 附近发生急剧转折——
#      |w| 远小于它的几乎全变，|w| 远大于它的几乎全不变。
# 这是机制的硬预言；若数据不呈现这个转折，机制就是错的。
import json, os
import torch
from safetensors import safe_open

BASE='/data/peilincai/CyberPoetTraining/cyberpoet_v1/models/Qwen3-14B'
FULL='/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt6_fullparam'
idx=lambda d: json.load(open(os.path.join(d,'model.safetensors.index.json')))['weight_map']
bmap,fmap=idx(BASE),idx(FULL); hs={}
def get(d,mp,k):
    f=mp[k]; key=(d,f)
    if key not in hs: hs[key]=safe_open(os.path.join(d,f),framework='pt',device='cpu')
    return hs[key].get_tensor(k)

PRED = 9.5e-3
for k in ('model.layers.20.mlp.down_proj.weight','model.layers.10.self_attn.q_proj.weight'):
    b=get(BASE,bmap,k).float().flatten(); f=get(FULL,fmap,k).float().flatten()
    d=(f-b); aw=b.abs()
    print(f"\n=== {k[13:]} ===")
    print(f"{'|w| 区间':>18} {'参数数':>12} {'零变化率':>9}   预言")
    edges=[0,1e-3,2e-3,4e-3,6e-3,8e-3,1.2e-2,1.6e-2,2.4e-2,4e-2,1e9]
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=(aw>=lo)&(aw<hi)
        if m.sum()<1000: continue
        z=(d[m]==0).float().mean().item()
        mid=(lo+hi)/2
        pred="应几乎全变" if hi<=PRED/1.5 else ("应几乎不变" if lo>=PRED*1.5 else "← 转折区")
        bar='█'*int(z*30)
        print(f"{lo:8.1e}–{hi:<8.1e} {int(m.sum()):12,d} {z:8.1%}  {bar:<30} {pred}")
    # 定量核验：低区与高区的零变化率
    lowm=aw<PRED/2; highm=aw>PRED*2
    zl=(d[lowm]==0).float().mean().item(); zh=(d[highm]==0).float().mean().item()
    print(f"  低区(|w|<{PRED/2:.1e}) 零变化 {zl:.1%}  |  高区(|w|>{PRED*2:.1e}) 零变化 {zh:.1%}  |  落差 {zh-zl:+.1%}")
    # 反证：若与量级无关（调度假说），两区应相同
    print(f"  判据：机制预言落差应 >40%；调度假说预言落差 ≈0%")
