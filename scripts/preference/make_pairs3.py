"""把第三批生成整理成配对。遵守 docs/07 的六条规则。

A 部分：模型轮转对打，同一首诗在同一题里只用一次。
B 部分：同模型多次采样拆成互不相交的配对——DPO 真正要吃的数据。
"""
import argparse, collections, hashlib, itertools, json, random, re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default="/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference")
ap.add_argument("--b-model", default="cons", help="B 部分所用模型（须与生成时一致）")
ap.add_argument("--out", default="pairs3.json")
a = ap.parse_args()

W = Path(a.dir)
rng = random.Random(20260826)
norm = lambda t: re.sub(r"\s+", "", t)
gid = lambda src, pk, m, s, b: hashlib.sha256(f"{src}|{pk}|{m}|{s}|{b}".encode()).hexdigest()[:16]


def grams(t):
    f = re.sub(r"[^一-鿿]", "", t)
    return {f[i:i + 4] for i in range(max(0, len(f) - 3))}


def near_dup(x, y, thr=0.8):
    p, q = grams(x), grams(y)
    return bool(p and q) and len(p & q) / len(p | q) >= thr


pairs, used_bodies = [], set()

# ── A 部分：选基础模型 ──
A = [json.loads(l) for l in (W / "batch3_A.jsonl").open(encoding="utf-8") if l.strip()]
by = collections.defaultdict(dict)
prompts = {}
for r in A:
    by[r["prompt_key"]][r["model"]] = r["body"]
    prompts[r["prompt_key"]] = r["prompt"]
# 规则 4：model 字段只放真模型
MODELS = ["base", "pt2", "pt_sft", "cons"]
ROT = [(("base", "cons"), ("pt2", "pt_sft")),
       (("base", "pt2"), ("cons", "pt_sft")),
       (("base", "pt_sft"), ("cons", "pt2"))]
for i, pk in enumerate(sorted(by)):
    have = by[pk]
    seen_in_prompt = set()          # 规则 2：一条生成一批里只用一次
    for m1, m2 in ROT[i % 3]:
        if m1 not in have or m2 not in have:
            continue
        b1, b2 = have[m1], have[m2]
        k1, k2 = norm(b1), norm(b2)
        if k1 in seen_in_prompt or k2 in seen_in_prompt:
            continue
        if len(k1) < 20 or len(k2) < 20:
            continue
        if near_dup(b1, b2):        # 规则 3
            continue
        x = {"gen_id": gid("b3A", pk, m1, 0, b1), "model": m1, "body": b1}
        y = {"gen_id": gid("b3A", pk, m2, 0, b2), "model": m2, "body": b2}
        if rng.random() < .5:
            x, y = y, x
        pairs.append({"prompt_key": f"A:{pk}", "prompt": prompts[pk], "A": x, "B": y})
        seen_in_prompt |= {k1, k2}

# ── B 部分：同模型采样 ──
bf = W / "batch3_B.jsonl"
if bf.exists():
    B = [json.loads(l) for l in bf.open(encoding="utf-8") if l.strip()]
    grp = collections.defaultdict(list)
    for r in B:
        grp[r["prompt_key"]].append(r)
    for pk, rs in grp.items():
        seen, uniq = set(), []
        for r in rs:                                # 规则 1：按 (题目, 去空白正文) 去重
            k = norm(r["body"])
            if k in seen or len(k) < 20:
                continue
            seen.add(k); uniq.append(r)
        rng.shuffle(uniq)
        used = set()
        for x, y in itertools.combinations(uniq, 2):
            if x["seed"] in used or y["seed"] in used:
                continue
            if near_dup(x["body"], y["body"]):
                continue
            m = a.b_model
            p = {"gen_id": gid("b3B", pk, m, x["seed"], x["body"]), "model": m, "body": x["body"]}
            q = {"gen_id": gid("b3B", pk, m, y["seed"], y["body"]), "model": m, "body": y["body"]}
            if rng.random() < .5:
                p, q = q, p
            pairs.append({"prompt_key": f"B:{pk}", "prompt": x["prompt"], "A": p, "B": q})
            used |= {x["seed"], y["seed"]}

rng.shuffle(pairs)
json.dump(pairs, (W / a.out).open("w", encoding="utf-8"), ensure_ascii=False, indent=1)
nA = sum(1 for p in pairs if p["prompt_key"].startswith("A:"))
print(f"共 {len(pairs)} 对：A 部分（选模型）{nA} 对，B 部分（同模型采样）{len(pairs) - nA} 对")
c = collections.Counter(tuple(sorted((p["A"]["model"], p["B"]["model"]))) for p in pairs)
for k, v in c.most_common():
    print(f"  {k[0]} vs {k[1]}: {v}")
# 自检：同一 gen_id 不得出现两次
ids = [p[s]["gen_id"] for p in pairs for s in ("A", "B")]
dup = [k for k, v in collections.Counter(ids).items() if v > 1]
print(f"重复使用的生成: {len(dup)}（应为 0）")
