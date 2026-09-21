"""M8 桥在干净开发集（sft_dev_v5，200 首，从未进过任何训练集）上的每 token 损失，只算回答部分。
用途：量「合并后再量化」这一步丢了多少——(a) nf4 底座 + adapter（训练时的样子） 对 (b) 合并成完整权重后再 nf4（偏好训练的起点/参考模型）。
提示串 = HF 模板 enable_thinking=False（与训练模板 qwen3 + enable_thinking:false 逐 token 一致，出厂检第 1 项）。
用法: m8_sftdev_nll.py <out.json> name=base_dir[:adapter_dir] ...   （全部按 nf4 加载；加 --bf16 则按 bf16）"""
import sys, json, torch, gc
import transformers.modeling_utils as mu
mu.caching_allocator_warmup = lambda *a, **k: None
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
R = Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1'); N = Path('/data/peilincai/CyberPoetTraining/claude_night_20260827')
args = [a for a in sys.argv[1:] if not a.startswith("--")]; BF16 = "--bf16" in sys.argv
OUT = args[0]; SPECS = args[1:]
dev = json.load(open(N / 'data/sft_dev_v5.json'))
tok = AutoTokenizer.from_pretrained(R / 'models/Qwen3-14B', trust_remote_code=True)
qc = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4", bnb_4bit_quant_storage=torch.bfloat16)
res = json.load(open(OUT)) if Path(OUT).exists() else {}
for spec in SPECS:
    name, _, rest = spec.partition("="); basep, _, adap = rest.partition(":")
    basep = basep if basep.startswith('/') else str(R / basep)
    kw = dict(trust_remote_code=True, torch_dtype=torch.bfloat16, device_map={"": 0})
    if not BF16: kw["quantization_config"] = qc
    base = AutoModelForCausalLM.from_pretrained(basep, **kw).eval()
    model = PeftModel.from_pretrained(base, adap).eval() if adap else base
    per_sample = []; tot_nll = 0.0; tot_tok = 0
    for r in dev:
        msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["instruction"] + (("\n" + r["input"]) if r.get("input") else "")}]
        p = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        pi = tok(p, add_special_tokens=False)["input_ids"]; ri = tok(r["output"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
        ids = torch.tensor([(pi + ri)[:2048]], device="cuda:0")
        with torch.no_grad(): lg = model(ids).logits[0, :-1].float()
        tgt = ids[0, 1:]; nll = torch.nn.functional.cross_entropy(lg, tgt, reduction="none")[len(pi) - 1:]
        per_sample.append(nll.mean().item()); tot_nll += nll.sum().item(); tot_tok += nll.numel()
    res[name] = {"per_sample_mean": sum(per_sample) / len(per_sample), "token_weighted": tot_nll / tot_tok, "n": len(per_sample), "tokens": tot_tok, "precision": "bf16" if BF16 else "nf4", "base": basep, "adapter": adap}
    print(name, json.dumps(res[name], ensure_ascii=False), flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    del model, base; gc.collect(); torch.cuda.empty_cache()
