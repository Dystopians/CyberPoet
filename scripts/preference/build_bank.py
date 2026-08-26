"""把项目里所有已经生成过的诗收拢成一个池子，作为将来做偏好标注（DPO）的原料。
只读，不改动任何现有文件。每条记录都带来源，方便追溯。"""
import json, re, glob, hashlib
from pathlib import Path

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
OUT = W / "preference/bank.jsonl"
rows = []

def add(prompt_key, prompt_text, model, body, source, seed=None):
    body = (body or "").strip()
    if len(body) < 20: return
    rows.append({"gen_id": hashlib.sha256(f"{source}|{prompt_key}|{model}|{seed}|{body}".encode()).hexdigest()[:16],
                 "prompt_key": prompt_key, "prompt": prompt_text, "model": model,
                 "seed": seed, "body": body, "source": source})

# 1) 我做的同题对照（基座 vs 预训练）
p = W / "pretrain/compare_pt.jsonl"
if p.exists():
    for l in open(p):
        d = json.loads(l)
        add(d["id"], d["instruction"], "base", d["base"], "compare_pt", 20260825)
        add(d["id"], d["instruction"], "pretrain_e1", d["pretrained"], "compare_pt", 20260825)

# 2) 裸提示实测
p = W / "pretrain/bare_prompt_test.jsonl"
if p.exists():
    for l in open(p):
        d = json.loads(l)
        k = f"title:{d['title']}:{'sys' if d['with_system'] else 'bare'}"
        add(k, f"根据《{d['title']}》写一首现代诗。", "base", d["base"], "bare_prompt", 20260825)
        add(k, f"根据《{d['title']}》写一首现代诗。", "pretrain_e1", d["pretrained"], "bare_prompt", 20260825)

# 3) v1/v2 的正式评测输出（基座 36 + 候选 36，各两轮）
tasks = {json.loads(l)["id"]: json.loads(l)["instruction"] for l in open(R / "eval/benchmark/tasks.jsonl")}
for run in glob.glob(str(R / "eval/runs/*/outputs/*")):
    cond = Path(run).name; tag = Path(run).parent.parent.name
    for f in glob.glob(run + "/*.txt"):
        tid = Path(f).stem
        model = "base" if cond == "baseline" else ("sft_v1" if "041942" in tag else "sft_v2")
        add(tid, tasks.get(tid, ""), model, open(f).read(), f"eval:{tag}")

# 4) v3 的形式探针（基座 / v1best / v2best / v2late）
p = R / "v3/reports/phase1_ckpt_probe/generations.jsonl"
if p.exists():
    base_dir = p.parent
    probes = {}
    for pf in ("v3/probes/literary_12.jsonl", "v3/probes/form_8.jsonl", "v3/probes/form_20.jsonl"):
        q = R / pf
        if q.exists():
            for l in open(q):
                d = json.loads(l)
                probes[d.get("id") or d.get("pid")] = d.get("instruction") or d.get("scene") or ""
    for l in open(p):
        d = json.loads(l)
        bf = base_dir / d["body_file"]
        if bf.exists():
            add(d["probe_id"], probes.get(d["probe_id"], ""), d["condition"],
                bf.read_text(encoding="utf-8"), "phase1_probe", d.get("seed"))

# 5) v3 target 生成的候选（同一题目多次采样，天然成对）
for f, tag in ((W / "data/targets_shard_tail.jsonl", "v3_tail"),
               (R / "v3/data/targets_shard_head.jsonl", "v3_head"),
               (R / "v3/data/targets_r1_superseded.jsonl", "v3_r1")):
    if not Path(f).exists(): continue
    for l in open(f):
        d = json.loads(l)
        body = d.get("body") or d.get("best_draft")
        sp = d.get("spec", {})
        add(d["pid"], f"{sp.get('scene','')}｜{sp.get('treatment','')}", f"base_sampled_{d['status']}", body, tag)

# 去重按「同一题目下的正文」，不按 gen_id——同一首诗从两个文件读进来，
# 元数据不同但正文相同，按 gen_id 去重会漏网（2026-08-25 实测漏了 36 条）。
import re as _re
seen, uniq = set(), []
for r in rows:
    key = (r["prompt_key"], _re.sub(r"\s+", "", r["body"]))
    if key in seen: continue
    seen.add(key); uniq.append(r)
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w") as f:
    for r in uniq: f.write(json.dumps(r, ensure_ascii=False) + "\n")

import collections
print(f"入池 {len(uniq)} 条生成")
print("按来源:", dict(collections.Counter(r["source"].split(":")[0] for r in uniq)))
print("按模型:", dict(collections.Counter(r["model"] for r in uniq)))
keys = collections.Counter(r["prompt_key"] for r in uniq)
pairable = {k: c for k, c in keys.items() if c >= 2}
print(f"可配对的题目 {len(pairable)} 个，理论可出 {sum(c*(c-1)//2 for c in pairable.values())} 对")
