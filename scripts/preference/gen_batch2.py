"""生成第二批标注任务。
A 部分：四个模型同题对打，用来选基础模型。
B 部分：选定模型自己的多次采样（同题不同种子）——DPO 真正要吃的配对。
"""
import argparse, json, torch, time
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8").strip()
ADAPTERS = {
    "pt2":    str(W / "pretrain/outputs/e8/checkpoint-398"),
    "pt_sft": str(W / "sft_repair/outputs/pt_then_sft/checkpoint-710"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--part", choices=("A", "B"), required=True)
ap.add_argument("--n", type=int, default=12)
ap.add_argument("--samples", type=int, default=4)
ap.add_argument("--batch", type=int, default=4)
ap.add_argument("--out", required=True)
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
tok.padding_side = "left"
if tok.pad_token is None: tok.pad_token = tok.eos_token
print("加载基座 …", flush=True)
base = AutoModelForCausalLM.from_pretrained(
    R / "models/Qwen3-14B", trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()

def ptext(instruction, form=None):
    u = instruction + (f"\n形式：{form}" if form else "")
    return tok.apply_chat_template([{"role": "system", "content": SYS}, {"role": "user", "content": u}],
                                   tokenize=False, add_generation_prompt=True, enable_thinking=False)

def gen(model, texts, seed):
    enc = tok(texts, return_tensors="pt", padding=True).to("cuda:0")
    torch.manual_seed(seed)
    with torch.no_grad():
        o = model.generate(**enc, max_new_tokens=560, do_sample=True, temperature=0.9,
                           top_p=0.92, repetition_penalty=1.08, pad_token_id=tok.pad_token_id)
    return [tok.decode(s[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip() for s in o]

out = open(a.out, "w"); t0 = time.time()
if a.part == "A":
    tasks = [json.loads(l) for l in open(R / "eval/benchmark/tasks.jsonl")][:a.n]
    model = None
    for tag, path in ADAPTERS.items():
        if model is None:
            model = PeftModel.from_pretrained(base, path, adapter_name=tag)
        else:
            model.load_adapter(path, adapter_name=tag)
        model.set_adapter(tag); model.eval()
        for i in range(0, len(tasks), a.batch):
            chunk = tasks[i:i + a.batch]
            for t, body in zip(chunk, gen(model, [ptext(t["instruction"], t.get("form_constraints")) for t in chunk], 20260825)):
                out.write(json.dumps({"part": "A", "prompt_key": t["id"], "prompt": t["instruction"],
                                      "model": tag, "seed": 20260825, "body": body}, ensure_ascii=False) + "\n")
            out.flush(); print(f"  A/{tag} {min(i + a.batch, len(tasks))}/{len(tasks)}  {(time.time()-t0)/60:.1f}分", flush=True)
else:
    scen = [json.loads(l) for l in open(R / "v3/data/scenarios_100.jsonl")][:a.n]
    model = PeftModel.from_pretrained(base, ADAPTERS["pt_sft"], adapter_name="pt_sft").eval()
    for i, s in enumerate(scen):
        instr = f"写一首现代诗：{s.get('scene') or s.get('text')}。{s.get('treatment', '')}".strip()
        for k in range(0, a.samples, a.batch):
            seed = 771003 + i * 100 + k
            for j, body in enumerate(gen(model, [ptext(instr)] * min(a.batch, a.samples - k), seed)):
                out.write(json.dumps({"part": "B", "prompt_key": f"sc{i:03d}", "prompt": instr,
                                      "model": "pt_sft", "seed": seed + j, "body": body}, ensure_ascii=False) + "\n")
        out.flush(); print(f"  B {i+1}/{len(scen)}  {(time.time()-t0)/60:.1f}分", flush=True)
out.close(); print("完成", flush=True)
