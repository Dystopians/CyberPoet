"""M8 代通用生成脚本（面板 / 复读检查 / v14 候选共用）。全部臂同参同提示：HF 模板 enable_thinking=False（与新桥训练逐 token 一致）、
top_p 0.9、max_new_tokens 560；三颗种子同一温度 0.9（09-16 复核：旧做法三颗种子是三种温度，不能当重复）。
可跨多张卡：CUDA_VISIBLE_DEVICES 给几张就按各卡当前空余显存切分（bf16 14B 需约 30 GB，单卡不够时用）。
09-21：M8 一系是真的 4 位量化（nf4）训出来的，推理也用同一套量化参数（--nf4），每个臂都在它训练时的精度下生成；M4 等旧臂训练时是 bf16，照旧 bf16。
用法: gen_m8.py <out.jsonl> <base_dir|rel> <adapter_dir|none> <titles.json> <arm名> [--seeds a,b,c] [--rp 1.08] [--bs 8] [--nf4]
titles.json = [{"id":..,"title":..},...]"""
import sys, json, torch, gc, argparse
import transformers.modeling_utils as mu
mu.caching_allocator_warmup = lambda *a, **k: None
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("base"); ap.add_argument("adapter"); ap.add_argument("titles"); ap.add_argument("arm")
ap.add_argument("--seeds", default="1400001,1400002,1400003"); ap.add_argument("--rp", type=float, default=1.08); ap.add_argument("--bs", type=int, default=8); ap.add_argument("--temp", type=float, default=0.9); ap.add_argument("--nf4", action="store_true")
a = ap.parse_args()
R = Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1')
SYS = (R / 'prompts/poetry_system_v2.txt').read_text(encoding='utf-8').strip()
srcs = json.load(open(a.titles))
tok = AutoTokenizer.from_pretrained(R / 'models/Qwen3-14B', trust_remote_code=True); tok.padding_side = 'left'
if tok.pad_token is None: tok.pad_token = tok.eos_token
basep = a.base if a.base.startswith('/') else str(R / a.base)
ng = torch.cuda.device_count()
if a.nf4:   # 与 LLaMA-Factory 训练时的量化配置逐项相同（quantization.py: nf4 + 双重量化 + 计算/存储 bf16）
    from transformers import BitsAndBytesConfig
    qc = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4", bnb_4bit_quant_storage=torch.bfloat16)
    base = AutoModelForCausalLM.from_pretrained(basep, trust_remote_code=True, torch_dtype=torch.bfloat16, quantization_config=qc, device_map={"": 0}).eval()
elif ng > 1:
    mm = {i: f"{max(1, int((torch.cuda.mem_get_info(i)[0] / 2**30) - 2.5))}GiB" for i in range(ng)}
    print("多卡切分 max_memory:", mm, flush=True)
    base = AutoModelForCausalLM.from_pretrained(basep, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="auto", max_memory=mm).eval()
else:
    base = AutoModelForCausalLM.from_pretrained(basep, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map={"": 0}).eval()
model = PeftModel.from_pretrained(base, a.adapter).eval() if a.adapter != "none" else base
dev0 = next(model.parameters()).device
done = set()
if Path(a.out).exists():
    for l in open(a.out, encoding="utf-8"):
        try: r = json.loads(l); done.add((r["seed"], r["src_id"]))
        except Exception: pass
out = open(a.out, 'a', encoding='utf-8')
for seed in [int(x) for x in a.seeds.split(",")]:
    for i in range(0, len(srcs), a.bs):
        chunk = srcs[i:i + a.bs]
        if all((seed, s["id"]) in done for s in chunk): continue
        texts = [tok.apply_chat_template([{"role": "system", "content": SYS}, {"role": "user", "content": f"以《{s['title']}》为题写一首现代诗。"}],
                                         tokenize=False, add_generation_prompt=True, enable_thinking=False) for s in chunk]
        enc = tok(texts, return_tensors="pt", padding=True).to(dev0)
        torch.manual_seed(seed + i)
        with torch.no_grad():
            o = model.generate(**enc, max_new_tokens=560, do_sample=True, temperature=a.temp, top_p=0.9, repetition_penalty=a.rp, pad_token_id=tok.pad_token_id)
        for s, sq in zip(chunk, o):
            if (seed, s["id"]) in done: continue
            body = tok.decode(sq[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            out.write(json.dumps({"arm": a.arm, "src_id": s["id"], "title": s["title"], "seed": seed, "rp": a.rp, "temp": a.temp, "nf4": a.nf4, "body": body}, ensure_ascii=False) + "\n")
        out.flush()
    print(a.arm, seed, "done", flush=True)
print("完成", flush=True)
