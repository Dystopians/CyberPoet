# 全参尸检：逐权重比对 pt6_fullparam vs 基座 Qwen3-14B
# 检验三个假设：
#   H1 精度地板：pure_bf16 + LR1e-5 → 更新量小于 bf16 分辨率被舍入 → 大比例权重零变化
#   H2 BAdam 不均：layer/ascending/interval=2 → 各层更新量severely 不均
#   H3 更新偏置：存活的更新集中在高频方向（lm_head/embed 与 MLP 下投影）
import json, glob, os, sys, collections
import torch
from safetensors import safe_open

BASE = '/data/peilincai/CyberPoetTraining/cyberpoet_v1/models/Qwen3-14B'
FULL = '/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/pt6_fullparam'

def index_of(d):
    idx = os.path.join(d, 'model.safetensors.index.json')
    m = json.load(open(idx))['weight_map']
    return m

bmap, fmap = index_of(BASE), index_of(FULL)
keys = sorted(set(bmap) & set(fmap))
print(f"共同权重张量: {len(keys)}（基座独有 {len(set(bmap)-set(fmap))}，全参独有 {len(set(fmap)-set(bmap))}）")

bh, fh = {}, {}
def get(d, mp, hs, k):
    f = mp[k]
    if f not in hs: hs[f] = safe_open(os.path.join(d, f), framework='pt', device='cpu')
    return hs[f].get_tensor(k)

per_layer = collections.defaultdict(lambda: {"n":0, "zero":0, "rel":0.0, "cnt":0})
tot_n = tot_zero = 0
rows = []
for i, k in enumerate(keys):
    b = get(BASE, bmap, bh, k).float()
    f = get(FULL, fmap, fh, k).float()
    if b.shape != f.shape:
        print("!! 形状不同", k, b.shape, f.shape); continue
    d = (f - b)
    n = d.numel()
    zero = int((d == 0).sum())
    bn = b.norm().item() or 1e-12
    rel = d.norm().item() / bn
    tot_n += n; tot_zero += zero
    # 层号
    lay = -1
    if '.layers.' in k:
        lay = int(k.split('.layers.')[1].split('.')[0])
    L = per_layer[lay]
    L["n"] += n; L["zero"] += zero; L["rel"] += rel; L["cnt"] += 1
    rows.append((k, n, zero/n, rel))
    if i % 60 == 0: print(f"  ...{i}/{len(keys)}", flush=True)

print(f"\n=== H1 精度地板 ===")
print(f"全模型参数 {tot_n:,}，其中**完全零变化** {tot_zero:,} = {tot_zero/tot_n:.2%}")

print(f"\n=== H2 逐层更新量（rel = ||Δ||/||W||，按层平均）===")
lays = sorted([l for l in per_layer if l >= 0])
vals = [(l, per_layer[l]["rel"]/per_layer[l]["cnt"], per_layer[l]["zero"]/per_layer[l]["n"]) for l in lays]
for l, r, z in vals[:4] + [("...", 0, 0)] + vals[len(vals)//2-1:len(vals)//2+1] + [("...", 0, 0)] + vals[-4:]:
    if l == "...": print("   ...")
    else: print(f"  层{l:2d}  rel={r:.3e}  零变化={z:.1%}")
rs = [v[1] for v in vals]
print(f"  层间 rel: min={min(rs):.3e} max={max(rs):.3e} 极差={max(rs)/max(min(rs),1e-12):.1f}×")

print(f"\n=== H3 更新最集中/最稀薄的张量 ===")
rows.sort(key=lambda x: -x[3])
for k, n, z, r in rows[:6]: print(f"  强 {k:52s} rel={r:.3e} 零={z:.1%}")
for k, n, z, r in rows[-4:]: print(f"  弱 {k:52s} rel={r:.3e} 零={z:.1%}")
nonlayer = [(k,z,r) for k,n,z,r in rows if '.layers.' not in k]
print("\n  非层张量（embed/lm_head/norm）:")
for k,z,r in nonlayer: print(f"    {k:44s} rel={r:.3e} 零={z:.1%}")
json.dump({"tot_n":tot_n,"tot_zero":tot_zero,
           "per_layer":{str(l):{"rel":per_layer[l]["rel"]/per_layer[l]["cnt"],
                                "zero":per_layer[l]["zero"]/per_layer[l]["n"]} for l in lays}},
          open('全参尸检_raw.json','w'), indent=1)
print("\n→ 全参尸检_raw.json")
