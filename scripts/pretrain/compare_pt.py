"""同题对照：基座 vs 预训练后的模型。同一套提示词、同一组随机种子。
不打分、不排序，只把两边的原文并排存下来。"""
import json, torch, argparse
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8").strip()

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=12)
ap.add_argument("--seed", type=int, default=20260825)
ap.add_argument("--out", default=str(W / "pretrain/compare_pt.jsonl"))
args = ap.parse_args()

tasks = [json.loads(l) for l in open(R / "eval/benchmark/tasks.jsonl")][:args.n]
tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
tok.padding_side = "left"
if tok.pad_token is None: tok.pad_token = tok.eos_token

def build(t):
    user = t["instruction"]
    if t.get("form_constraints"): user += f"\n形式：{t['form_constraints']}"
    if t.get("target_length_chars"): user += f"\n篇幅：约 {t['target_length_chars']} 字。"
    return tok.apply_chat_template(
        [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)

print("加载基座 …", flush=True)
model = AutoModelForCausalLM.from_pretrained(
    R / "models/Qwen3-14B", trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()

def run(tag, m):
    res = {}
    for t in tasks:
        torch.manual_seed(args.seed)
        enc = tok([build(t)], return_tensors="pt").to("cuda:0")
        with torch.no_grad():
            o = m.generate(**enc, max_new_tokens=560, do_sample=True, temperature=0.85,
                           top_p=0.9, repetition_penalty=1.08, pad_token_id=tok.pad_token_id)
        res[t["id"]] = tok.decode(o[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        print(f"  {tag} {t['id']} 完成", flush=True)
    return res

base = run("基座", model)
print("挂上预训练适配器 …", flush=True)
model = PeftModel.from_pretrained(model, str(W / "pretrain/outputs/e1")).eval()
pt = run("预训练", model)

with open(args.out, "w") as f:
    for t in tasks:
        f.write(json.dumps({"id": t["id"], "instruction": t["instruction"],
                            "base": base[t["id"]], "pretrained": pt[t["id"]]},
                           ensure_ascii=False) + "\n")
print("写出", args.out)
