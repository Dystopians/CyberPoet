"""从样本池里挑出值得标注的配对：优先跨模型、同题目，两首都不太短。"""
import json, re, random, collections, itertools, argparse
from pathlib import Path
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference")

ap = argparse.ArgumentParser()
ap.add_argument("--max-per-prompt", type=int, default=2)
ap.add_argument("--limit", type=int, default=300)
ap.add_argument("--models", default="", help="只保留涉及这些模型的配对，逗号分隔")
ap.add_argument("--out", default=str(W / "pairs.json"))
a = ap.parse_args()

rows = [json.loads(l) for l in open(W / "bank.jsonl")]
keep = set(a.models.split(",")) if a.models else None
by_prompt = collections.defaultdict(list)
for r in rows: by_prompt[r["prompt_key"]].append(r)

rng = random.Random(20260825)
pairs = []
used = set()          # 一首诗只进一对，避免同一首反复出现在标注页里
def grams(t):
    f = re.sub(r"[^\u4e00-\u9fff]", "", t)
    return {f[i:i+4] for i in range(max(0, len(f) - 3))}
def near_dup(x, y, thr=0.8):
    a, b = grams(x["body"]), grams(y["body"])
    return bool(a and b) and len(a & b) / len(a | b) >= thr

for k, group in by_prompt.items():
    cands = [(x, y) for x, y in itertools.combinations(group, 2) if x["model"] != y["model"]]
    if keep: cands = [p for p in cands if keep & {p[0]["model"], p[1]["model"]}]
    rng.shuffle(cands)
    picked_here = 0
    for x, y in cands:
        if picked_here >= a.max_per_prompt: break
        if x["gen_id"] in used or y["gen_id"] in used: continue
        if near_dup(x, y): continue        # 两首几乎一样，让人选没有意义
        used.add(x["gen_id"]); used.add(y["gen_id"]); picked_here += 1
        if rng.random() < .5: x, y = y, x          # 左右随机，标注时看不出谁是谁
        pairs.append({"prompt_key": k, "prompt": x["prompt"],
                      "A": {"gen_id": x["gen_id"], "model": x["model"], "body": x["body"]},
                      "B": {"gen_id": y["gen_id"], "model": y["model"], "body": y["body"]}})
rng.shuffle(pairs)
pairs = pairs[:a.limit]
json.dump(pairs, open(a.out, "w"), ensure_ascii=False, indent=1)
c = collections.Counter(tuple(sorted((p["A"]["model"], p["B"]["model"]))) for p in pairs)
print(f"出了 {len(pairs)} 对，覆盖 {len({p['prompt_key'] for p in pairs})} 个题目")
for k, v in c.most_common(8): print(f"  {k[0]} vs {k[1]}: {v} 对")
