# 口味可学性探针 · 第一步（10-01）：把主人投过票的每一首诗过一遍裸底座 Qwen3-14B（nf4），取三层隐状态的平均向量 + 每字平均损失。
# 只做特征提取，不打分。输出 taste_probe_emb.npz（keys: bodies, L_last, L_m8, L_m16, nll）。用法：CUDA_VISIBLE_DEVICES=卡 python taste_probe_embed.py
import json, sys, numpy as np, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
Q = "/data/peilincai/CyberPoetTraining/claude_night_20260827/quiz_v3/"; R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
V1 = "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference/labels/all_labels.json"
SETS = ["pairs_final.json", "v5_pairs_final.json", "v6_pairs_final.json", "v7_pairs_final.json", "v75_hh_fixed.json", "v8_pairs_final.json", "v9_pairs_final.json",
        "v10b_pairs_final.json", "v11_pairs_final.json", "v12_pairs_final.json", "v13_pairs_final.json", "v14_pairs_final.json", "v15_pairs_final.json", "v16_pairs_final.json"]
bodies = []
for f in SETS:
    for q in json.load(open(Q + f)):
        for s in "AB": bodies.append(q[s]["body"].strip())
for x in json.load(open(V1)):
    bodies += [x["ba"].strip(), x["bb"].strip()]
bodies = sorted(set(bodies), key=len); print("诗数", len(bodies), flush=True)   # 按长度排，减少补齐（第一次 16 条一批把 5 GB 的 float32 logits 撞爆了）
tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True); tok.padding_side = "right"
m = AutoModelForCausalLM.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True, device_map={"": 0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)).eval()
out = {"L_last": [], "L_m8": [], "L_m16": [], "nll": []}
BS = 4
with torch.no_grad():
    for k in range(0, len(bodies), BS):
        chunk = bodies[k:k+BS]
        enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=600).to(0)
        o = m(**enc, output_hidden_states=True)
        mask = enc["attention_mask"].unsqueeze(-1).to(torch.float32)
        for name, li in (("L_last", -1), ("L_m8", -8), ("L_m16", -16)):
            h = o.hidden_states[li].to(torch.float32); v = (h * mask).sum(1) / mask.sum(1)
            out[name].append(v.cpu().numpy().astype(np.float16))
        logits = o.logits[:, :-1]; tgt = enc["input_ids"][:, 1:]; am = enc["attention_mask"][:, 1:].to(torch.float32)
        lp = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)).to(torch.float32), tgt.reshape(-1), reduction="none").view(tgt.shape)
        out["nll"].append(((lp * am).sum(1) / am.sum(1)).cpu().numpy())
        if k % 320 == 0: print(k, flush=True)
np.savez(Q + "taste_probe_emb.npz", bodies=np.array(bodies, dtype=object), **{k: np.concatenate(v) for k, v in out.items()})
print("saved", flush=True)
