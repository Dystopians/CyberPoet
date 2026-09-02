"""权重差分自检（强制流程，STATE 规矩）：python3 check_weight_diff.py <基座目录> <checkpoint目录>
抽 4 个张量 + 输出头三件，报零变化率与 ‖Δ‖/‖W‖；任一层零变化率 >50% 判为「训练未发生」，退出码 2。"""
import json, os, sys, torch
from safetensors import safe_open
BASE, CK = sys.argv[1], sys.argv[2]
# 第 3 个参数可选：只抽查这些层（逗号分隔）。BAdam 升序轮转下，中途 checkpoint 只能查已轮到的层：
#   已轮到层数 ≈ 优化步数 / badam_switch_interval（v10 事故：第 50 步查 20/30/39 层误判熔断）。
LAYERS = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [3, 20, 30, 39]
def tensor(d, key):
    idx = os.path.join(d, 'model.safetensors.index.json')
    if os.path.exists(idx):
        m = json.load(open(idx))['weight_map']; f = m[key]
    else:
        f = 'model.safetensors'
    with safe_open(os.path.join(d, f), framework='pt', device='cpu') as h:
        return h.get_tensor(key)
bad = False
KIND = ['self_attn.q_proj', 'mlp.down_proj', 'mlp.gate_proj', 'self_attn.o_proj']
for j, L in enumerate(LAYERS):
    k = f'model.layers.{L}.{KIND[j % 4]}.weight'
    b = tensor(BASE, k).float(); f = tensor(CK, k).float()
    zr = (b == f).float().mean().item(); rel = (f - b).norm().item() / (b.norm().item() or 1e-12)
    # 判据（09-02 修正）：M5F 式签名 = 零变化率 >70% 且 ‖Δ‖/‖W‖ <5e-4。单看零变化率会把「只轮到一次的后层」误判（实测 66%/1.1e-3 仍是坏配置的 10 倍）
    dead = zr > 0.7 and rel < 5e-4
    flag = ' !! 未训签名' if dead else (' （轮到次数少）' if zr > 0.5 else '')
    bad |= dead
    print(f'{k}: 零变化率 {zr:.1%}  ‖Δ‖/‖W‖ {rel:.2e}{flag}')
for k in ['lm_head.weight', 'model.embed_tokens.weight', 'model.norm.weight']:
    b = tensor(BASE, k); f = tensor(CK, k)
    print(f'{k}: 逐比特相同 = {bool((b == f).all())}')
print('（输出头三件在 BAdam layer 模式下预期冻结，仅记录不判）')
print('结论:', '训练未发生（熔断）' if bad else '权重在动，通过')
sys.exit(2 if bad else 0)
