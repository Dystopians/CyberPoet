"""把第二批生成整理成配对。
A 部分：四个模型轮转对打，同一首诗在同一题里只用一次。
B 部分：同模型 4 次采样拆成 2 对不相交的配对。
"""
import json, random, re, hashlib, collections, itertools
from pathlib import Path
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference")
rng = random.Random(20260826)
norm = lambda t: re.sub(r"\s+", "", t)
gid = lambda src, pk, m, s, b: hashlib.sha256(f"{src}|{pk}|{m}|{s}|{b}".encode()).hexdigest()[:16]

def grams(t):
    f = re.sub(r"[^一-鿿]", "", t)
    return {f[i:i+4] for i in range(max(0, len(f) - 3))}
def near_dup(x, y, thr=0.8):
    a, b = grams(x), grams(y)
    return bool(a and b) and len(a & b) / len(a | b) >= thr

pairs = []

# ---- A 部分 ----
A = [json.loads(l) for l in open(W / "batch2_A.jsonl")]
bank = [json.loads(l) for l in open(W / "bank.jsonl")]
by = collections.defaultdict(dict)
for r in A: by[r["prompt_key"]][r["model"]] = r["body"]
for r in bank:                     # 从既有池子里补 base 与 sft_v2
    if r["model"] in ("base", "sft_v2") and r["prompt_key"] in by and r["source"].startswith("eval"):
        by[r["prompt_key"]].setdefault(r["model"], r["body"])
ROT = [(("base","sft_v2"),("pt2","pt_sft")), (("base","pt2"),("sft_v2","pt_sft")), (("base","pt_sft"),("sft_v2","pt2"))]
prompts_A = {r["prompt_key"]: r["prompt"] for r in A}
for i, pk in enumerate(sorted(by)):
    have = by[pk]
    for m1, m2 in ROT[i % 3]:
        if m1 not in have or m2 not in have: continue
        if near_dup(have[m1], have[m2]): continue
        x = {"gen_id": gid("b2A", pk, m1, 0, have[m1]), "model": m1, "body": have[m1]}
        y = {"gen_id": gid("b2A", pk, m2, 0, have[m2]), "model": m2, "body": have[m2]}
        if rng.random() < .5: x, y = y, x
        pairs.append({"prompt_key": f"A:{pk}", "prompt": prompts_A[pk], "A": x, "B": y})

# ---- B 部分 ----
B = [json.loads(l) for l in open(W / "batch2_B.jsonl")]
grp = collections.defaultdict(list)
for r in B: grp[r["prompt_key"]].append(r)
for pk, rs in grp.items():
    seen, uniq = set(), []
    for r in rs:                                   # 同题内先去重
        k = norm(r["body"])
        if k in seen or len(k) < 20: continue
        seen.add(k); uniq.append(r)
    rng.shuffle(uniq)
    used = set()
    for x, y in itertools.combinations(uniq, 2):
        if x["seed"] in used or y["seed"] in used: continue
        if near_dup(x["body"], y["body"]): continue
        a = {"gen_id": gid("b2B", pk, "pt_sft", x["seed"], x["body"]), "model": "pt_sft", "body": x["body"]}
        b = {"gen_id": gid("b2B", pk, "pt_sft", y["seed"], y["body"]), "model": "pt_sft", "body": y["body"]}
        if rng.random() < .5: a, b = b, a
        pairs.append({"prompt_key": f"B:{pk}", "prompt": x["prompt"], "A": a, "B": b})
        used.add(x["seed"]); used.add(y["seed"])

rng.shuffle(pairs)
json.dump(pairs, open(W / "pairs2.json", "w"), ensure_ascii=False, indent=1)
nA = sum(1 for p in pairs if p["prompt_key"].startswith("A:"))
print(f"共 {len(pairs)} 对：A 部分（选模型）{nA} 对，B 部分（同模型采样）{len(pairs)-nA} 对")
c = collections.Counter(tuple(sorted((p["A"]["model"], p["B"]["model"]))) for p in pairs)
for k, v in c.most_common(): print(f"  {k[0]} vs {k[1]}: {v}")
