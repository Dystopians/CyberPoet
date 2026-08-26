"""训练旁路采样：盯着 checkpoint 目录，每出一个就生成几首诗，连同可数指标打到 wandb。
不碰训练进程本身——训练照常跑，这个进程只读 checkpoint。
两种模式：--mode watch 边训边采，--mode backfill 把已有的 checkpoint 补齐。
"""
import argparse, json, re, time, os, sys, glob, collections, statistics
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import wandb

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
SYS = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8").strip()

def cliche(t, pat):
    n = len(re.sub(r"[^一-鿿]", "", t))
    return len(re.findall(pat, t)) / max(1, n) * 100

def stats_of(text):
    lines = [x for x in text.strip().splitlines() if x.strip()]
    chars = sum(len(re.sub(r"\s", "", x)) for x in lines)
    return len(lines), chars, chars / max(1, len(lines))

def build_overlap_index(n=10):
    D = Path("/data/peilincai/CyberPoet_poetry_dataset_v0.3.0/repository/poetry_dataset/splits")
    corpus, index = [], collections.defaultdict(list)
    for split in ("train", "validation", "test"):
        for l in open(D / f"{split}.jsonl"):
            corpus.append(re.sub(r"\s", "", json.loads(l)["text"]))
    for i, txt in enumerate(corpus):
        for j in range(len(txt) - n + 1):
            index[txt[j:j + n]].append((i, j))
    return corpus, index, n

def max_overlap(gen, corpus, index, n):
    g = re.sub(r"\s", "", gen); best = 0
    for j in range(len(g) - n + 1):
        for (i, k) in index.get(g[j:j + n], []):
            txt = corpus[i]; m = n
            while j + m < len(g) and k + m < len(txt) and g[j + m] == txt[k + m]: m += 1
            best = max(best, m)
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True, help="训练的 output_dir")
    ap.add_argument("--run-name", required=True, help="wandb run 名（会自动加 -samples 后缀）")
    ap.add_argument("--mode", choices=("watch", "backfill"), default="backfill")
    ap.add_argument("--n-prompts", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--poll", type=int, default=60)
    ap.add_argument("--timeout-min", type=int, default=240)
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(R / "eval/benchmark/tasks.jsonl")][:args.n_prompts]
    tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    print("加载基座 …", flush=True)
    base = AutoModelForCausalLM.from_pretrained(
        R / "models/Qwen3-14B", trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()
    print("建逐字重合索引 …", flush=True)
    corpus, index, N = build_overlap_index()

    run = wandb.init(project="cyberpoet-modern-poetry",
                     entity="karamazovaniki-university-of-southern-california",
                     name=f"{args.run_name}-samples", group="cyberpoet-samples",
                     tags=["samples", "sidecar"], reinit=True)
    table = wandb.Table(columns=["step", "题目", "诗", "行数", "字数", "每行字数", "逐字重合"])

    def gen(model, task):
        user = task["instruction"]
        if task.get("form_constraints"): user += f"\n形式：{task['form_constraints']}"
        text = tok.apply_chat_template(
            [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False)
        enc = tok([text], return_tensors="pt").to("cuda:0")
        torch.manual_seed(args.seed)
        with torch.no_grad():
            o = model.generate(**enc, max_new_tokens=560, do_sample=True, temperature=0.85,
                               top_p=0.9, repetition_penalty=1.08, pad_token_id=tok.pad_token_id)
        return tok.decode(o[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    done, model, t0 = set(), None, time.time()
    while True:
        cks = sorted(glob.glob(f"{args.output_dir}/checkpoint-*"),
                     key=lambda p: int(p.rsplit("-", 1)[1]))
        todo = [c for c in cks if c not in done]
        for ck in todo:
            step = int(ck.rsplit("-", 1)[1])
            if not Path(ck, "adapter_model.safetensors").exists():
                continue
            print(f"[{step}] 采样 …", flush=True)
            name = f"s{step}"
            if model is None:
                model = PeftModel.from_pretrained(base, ck, adapter_name=name)
            else:
                model.load_adapter(ck, adapter_name=name)
            model.set_adapter(name)
            model.eval()
            rows, cl, sim, lns, cpl, ovs = [], [], [], [], [], []
            for t in tasks:
                body = gen(model, t)
                L, C, PL = stats_of(body); ov = max_overlap(body, corpus, index, N)
                table.add_data(step, t["instruction"][:40], body, L, C, round(PL, 1), ov)
                cl.append(cliche(body, r"某种|某个|某一")); sim.append(cliche(body, r"像|仿佛|如同|宛如|似的"))
                lns.append(L); cpl.append(PL); ovs.append(ov)
            wandb.log({"step_": step,
                       "套话密度_某种某个_每百字": statistics.mean(cl),
                       "比喻密度_每百字": statistics.mean(sim),
                       "行数_中位": statistics.median(lns),
                       "每行字数_中位": statistics.median(cpl),
                       "逐字重合_最大": max(ovs)}, step=step)
            done.add(ck)
            print(f"[{step}] 完成：套话 {statistics.mean(cl):.2f}/百字，重合 {max(ovs)} 字", flush=True)
        if args.mode == "backfill" and not todo:
            break
        if (time.time() - t0) / 60 > args.timeout_min:
            print("超时退出", flush=True); break
        if args.mode == "watch":
            time.sleep(args.poll)
        else:
            break
    wandb.log({"样本": table})
    run.finish()
    print("结束", flush=True)

if __name__ == "__main__":
    main()
