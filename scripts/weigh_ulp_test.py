# 判别实验：79.6% 权重零变化，到底是 (A) bf16 舍入地板 还是 (B) BAdam 调度没轮到？
# 判据：若是 (A)，零变化率应随权重量级单调上升（|w| 越大 ULP 越大，固定步长越易被吃掉），
#       且在同一张量内部，未变的权重应系统性地比变了的权重更大。
#       若是 (B)，零变化应按层/张量整块出现，与量级无关。
import json, os, collections
import torch
from safetensors import safe_open

BASE='/data/peilincai/CyberPoetTraining/cyberpoet_v1/models/Qwen3-14B'
FULL='/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt6_fullparam'
idx=lambda d: json.load(open(os.path.join(d,'model.safetensors.index.json')))['weight_map']
bmap,fmap=idx(BASE),idx(FULL)
hs={}
def get(d,mp,k):
    f=mp[k]; key=(d,f)
    if key not in hs: hs[key]=safe_open(os.path.join(d,f),framework='pt',device='cpu')
    return hs[key].get_tensor(k)

# 取若干代表性张量：早/中/晚层的 mlp.down_proj 与 self_attn.q_proj
probes=[f'model.layers.{l}.{m}.weight' for l in (1,10,20,30,39)
        for m in ('mlp.down_proj','self_attn.q_proj')]
print("张量 | 零变化率 | 未变权重中位|w| | 变了的权重中位|w| | 比值")
ratios=[]
for k in probes:
    if k not in bmap: continue
    b=get(BASE,bmap,k).float().flatten()
    f=get(FULL,fmap,k).float().flatten()
    d=f-b
    z=(d==0)
    if z.sum()==0 or (~z).sum()==0: continue
    mz=b[z].abs().median().item(); mn=b[~z].abs().median().item()
    r=mz/max(mn,1e-12); ratios.append(r)
    print(f"{k[13:]:34s} {z.float().mean().item():6.1%} {mz:.5f} {mn:.5f} {r:6.2f}×")
print(f"\n未变/已变 权重量级比值：中位 {sorted(ratios)[len(ratios)//2]:.2f}×")
print("判据：>1 支持 (A) bf16 舍入地板；≈1 支持 (B) 调度未覆盖")

# 补充：非零更新的量级 vs 该处 bf16 ULP
k='model.layers.20.mlp.down_proj.weight'
b=get(BASE,bmap,k).float().flatten(); f=get(FULL,fmap,k).float().flatten(); d=(f-b)
nz=d[d!=0].abs()
ulp=(b[d!=0].abs()*2**-8)          # bf16 8位尾数的相对分辨率
print(f"\n{k[13:]}：非零更新中位 |Δ|={nz.median().item():.3e}，"
      f"该处 bf16 ULP 中位={ulp.median().item():.3e}，比值={nz.median().item()/max(ulp.median().item(),1e-30):.2f}")
print("（若非零更新≈1×ULP，说明存活下来的正是「刚好够一个最小刻度」的那些——铁证）")
