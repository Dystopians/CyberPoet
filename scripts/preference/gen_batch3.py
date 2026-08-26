"""生成第三批标注任务。

相对第二批的变化：加入 `cons`（预训练2轮 + 纯约束回放 SFT）。
加它的理由是可数的：实测 120 配对单元显示「预训练2轮」除结尾外指令服从接近基座，
而修复微调把它打坏（禁词 120/120 → 73/120）；`cons` 只补约束、不引入任何
基座自采样的创作 target，用来验证「能不能只补形式而不动文学」。

A 部分：模型同题对打，用来选 DPO 的基础模型。
B 部分：选定模型自己的多次采样（同题不同种子）——DPO 真正要吃的配对。
"""
import argparse, json, time
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8-sig").strip()
ADAPTERS = {
    "pt2":    str(W / "pretrain/outputs/e8/checkpoint-398"),
    "pt_sft": str(W / "sft_repair/outputs/pt_then_sft/checkpoint-710"),
    "cons":   str(R / "v3/outputs/cons/checkpoint-150"),
    "cons7":  str(R / "v3/outputs/cons7/checkpoint-150"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--part", choices=("A", "B"), required=True)
ap.add_argument("--n", type=int, default=12)
ap.add_argument("--samples", type=int, default=4)
ap.add_argument("--batch", type=int, default=4)
ap.add_argument("--model", default="cons", help="B 部分用哪个模型")
ap.add_argument("--out", required=True)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
tok.padding_side = "left"
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
print("加载基座 …", flush=True)
base = AutoModelForCausalLM.from_pretrained(
    R / "models/Qwen3-14B", trust_remote_code=True, torch_dtype=torch.bfloat16,
    device_map="cuda:0").eval()


def ptext(instruction, form=None):
    u = instruction + (f"\n形式：{form}" if form else "")
    return tok.apply_chat_template(
        [{"role": "system", "content": SYS}, {"role": "user", "content": u}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)


def gen(model, texts, seed):
    enc = tok(texts, return_tensors="pt", padding=True).to("cuda:0")
    torch.manual_seed(seed)
    with torch.no_grad():
        o = model.generate(**enc, max_new_tokens=560, do_sample=True, temperature=0.9,
                           top_p=0.92, repetition_penalty=1.08, pad_token_id=tok.pad_token_id)
    return [tok.decode(s[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip() for s in o]


tasks = [json.loads(l) for l in open(R / "eval/benchmark/tasks.jsonl")][:a.n]
out = open(a.out, "w", encoding="utf-8")
t0 = time.time()

if a.part == "A":
    model = None
    # 基座（不挂 adapter）
    texts = [ptext(t["instruction"], t.get("form_constraints")) for t in tasks]
    for i in range(0, len(texts), a.batch):
        for t, b in zip(tasks[i:i + a.batch], gen(base, texts[i:i + a.batch], 20260826 + i)):
            out.write(json.dumps({"prompt_key": t["id"], "prompt": t["instruction"],
                                  "model": "base", "seed": 20260826 + i, "body": b},
                                 ensure_ascii=False) + "\n")
        out.flush(); print(f"base {min(i + a.batch, len(texts))}/{len(texts)}  {(time.time()-t0)/60:.1f}分", flush=True)
    for tag, path in ADAPTERS.items():
        if model is None:
            model = PeftModel.from_pretrained(base, path, adapter_name=tag)
        else:
            model.load_adapter(path, adapter_name=tag)
        model.set_adapter(tag); model.eval()
        for i in range(0, len(texts), a.batch):
            for t, b in zip(tasks[i:i + a.batch], gen(model, texts[i:i + a.batch], 20260826 + i)):
                out.write(json.dumps({"prompt_key": t["id"], "prompt": t["instruction"],
                                      "model": tag, "seed": 20260826 + i, "body": b},
                                     ensure_ascii=False) + "\n")
            out.flush(); print(f"{tag} {min(i + a.batch, len(texts))}/{len(texts)}  {(time.time()-t0)/60:.1f}分", flush=True)
else:
    model = PeftModel.from_pretrained(base, ADAPTERS[a.model], adapter_name=a.model).eval()
    texts = [ptext(t["instruction"], t.get("form_constraints")) for t in tasks]
    for s in range(a.samples):
        seed = 771003 + s * 9173
        for i in range(0, len(texts), a.batch):
            for t, b in zip(tasks[i:i + a.batch], gen(model, texts[i:i + a.batch], seed + i)):
                out.write(json.dumps({"prompt_key": t["id"], "prompt": t["instruction"],
                                      "model": a.model, "seed": seed + i, "body": b},
                                     ensure_ascii=False) + "\n")
            out.flush()
        print(f"采样 {s+1}/{a.samples}  {(time.time()-t0)/60:.1f}分", flush=True)
out.close()
print("完成", a.out)
