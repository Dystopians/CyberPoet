"""裸提示实测：不给系统提示词、不给简报结构，只说一句「根据《xxx》写一首现代诗」。
看预训练带来的变化是否依赖提示词格式。"""
import json, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8").strip()
TITLES = ["晚风", "旧站台", "九月", "母亲的手", "空房间", "铁轨旁的野花"]
SEED = 20260825

tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
if tok.pad_token is None: tok.pad_token = tok.eos_token
print("加载基座 …", flush=True)
model = AutoModelForCausalLM.from_pretrained(
    R / "models/Qwen3-14B", trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()

def gen(m, title, with_sys):
    msgs = ([{"role": "system", "content": SYS}] if with_sys else []) + \
           [{"role": "user", "content": f"根据《{title}》写一首现代诗。"}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    enc = tok([text], return_tensors="pt").to("cuda:0")
    torch.manual_seed(SEED)
    with torch.no_grad():
        o = m.generate(**enc, max_new_tokens=560, do_sample=True, temperature=0.85,
                       top_p=0.9, repetition_penalty=1.08, pad_token_id=tok.pad_token_id)
    return tok.decode(o[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()

res = {}
for tag, m in (("base", model),):
    for t in TITLES:
        for ws in (False, True):
            res[(tag, t, ws)] = gen(m, t, ws)
            print(f"  {tag} 《{t}》 {'带系统提示' if ws else '裸提示'} 完成", flush=True)
print("挂上预训练适配器 …", flush=True)
model = PeftModel.from_pretrained(model, str(W / "pretrain/outputs/e1")).eval()
for t in TITLES:
    for ws in (False, True):
        res[("pt", t, ws)] = gen(model, t, ws)
        print(f"  pt 《{t}》 {'带系统提示' if ws else '裸提示'} 完成", flush=True)

out = W / "pretrain/bare_prompt_test.jsonl"
with open(out, "w") as f:
    for t in TITLES:
        for ws in (False, True):
            f.write(json.dumps({"title": t, "with_system": ws,
                                "base": res[("base", t, ws)], "pretrained": res[("pt", t, ws)]},
                               ensure_ascii=False) + "\n")
print("写出", out)
