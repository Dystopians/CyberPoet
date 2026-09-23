# v15 hh（09-22，为 v16「标准局」备料）：24 对 / 6 家各 8 出场——陆忆敏（累计 9/14）、杨炼（10/12）、昌耀（正向显著）+ 张枣、多多、商禽。
# 目的：让主人在纯人对里再评一批真人诗，赢的诗做下一卷 AI 对强真人诗的「标准局」。派生自 v12。
# 边多重集：完全图 K6 每边 1 对 = 15 对，再补 9 条边到每家 8 出场。名篇不再规避（主人 08-31 裁决）。
# 纪律：登记表+v9金标互查、名诗黑名单（v7#62 事故后 hh 侧也过）、
#   池内10字窗近重复清理、篇幅比≤1.6、bucket 优先同域、侧位配平。
import json, re, random, collections, sys
sys.path.insert(0, '.')
from v5_lib import norm, chars, bucket
from fix_v75 import FAMOUS
# 盲态否决（通读裁定 2026-08-30）：正文自报作者 / 点名密友诗人+自引作品，作者身份等于明牌
BLIND_VETO = {("商禽","苍鹭"), ("昌耀","古本尖乔①——鲁沙尔镇的民间节日"), ("商禽","豆腐汤丸")}   # v15 通读裁定：题词引卞之琳名句+点名安格尔/华苓（明牌）；题名带注号①与组诗副题行；「她作」疑似吞字

import glob
POOL_AUTHORS = ("陆忆敏","杨炼","昌耀","张枣","多多","商禽")
pool = collections.defaultdict(list)
_seen = set()
for r in (json.loads(l) for l in open('../corpus_clean/base_fixed/all.jsonl')):
    if r.get("author") in POOL_AUTHORS:
        k = norm(r["text"])
        if k in _seen: continue
        _seen.add(k); pool[r["author"]].append({"title": r.get("title",""), "body": r["text"]})
for fp in glob.glob('../corpus_clean/poets_v2/*.jsonl'):
    for r in (json.loads(l) for l in open(fp)):
        if r.get("author") in POOL_AUTHORS:
            k = norm(r["body"])
            if k in _seen: continue
            _seen.add(k); pool[r["author"]].append({"title": r.get("title",""), "body": r["body"]})
for a in list(pool):
    pool[a] = [p for p in pool[a] if p["title"] and not re.search(r"[A-Za-z]", p["title"]) and 60 <= chars(p["body"]) <= 340 and len(re.findall(r"[A-Za-z]", p["body"])) < 3]   # 题名含拉丁字母也剔（沿第十二卷）
used = set(json.load(open('used_bodies.json')))
# v9 ha 金标也算占用（防跨题型撞车）
v9src = json.load(open('v15_sources_proposed.json'))
for p in v9src["ha"]: used.add(norm(p["body"]))
V9_AA_TITLES = {p["title"] for p in v9src["aa"]}          # 跨题型同题互斥（v8 事故）
V9_HA_TITLES = {p["title"] for p in v9src["ha"]}

import itertools
POETS = ["陆忆敏","杨炼","昌耀","张枣","多多","商禽"]
EDGES = list(itertools.combinations(POETS, 2))            # 15 条
EDGES += [("陆忆敏","杨炼"),("陆忆敏","昌耀"),("陆忆敏","张枣"),("杨炼","多多"),("杨炼","商禽"),
          ("昌耀","多多"),("昌耀","商禽"),("张枣","多多"),("张枣","商禽")]   # +9 → 每家 8
assert len(EDGES) == 24
deg = collections.Counter(a for e in EDGES for a in e)
assert all(v == 8 for v in deg.values()), deg

def fgrams(t):
    s = norm(t); return {s[i:i+10] for i in range(max(len(s)-9, 1))}
used_g = set()
for b in used: used_g |= {b[i:i+10] for i in range(max(len(b)-9, 1))}

for a in deg:
    kept, gs = [], set()
    for p in pool.get(a, []):
        if (a, p["title"]) in BLIND_VETO or p["title"] in V9_AA_TITLES or p["title"] in V9_HA_TITLES: continue
        g = fgrams(p["body"])
        if g & gs or g & used_g: continue
        gs |= g; kept.append(p)
    pool[a] = kept
print("可用池:", {a: len(pool[a]) for a in deg})

# 定序改用标题哈希（不用 shuffle）：黑名单增删只影响被剔那首，不再全池级联重排
import hashlib
for a in deg:
    pool[a].sort(key=lambda p: hashlib.sha256((a + p["title"]).encode()).hexdigest())
rng = random.Random(150015)
taken = collections.defaultdict(set)
sel_g, sel_titles = set(), set()

def pick_pair(a, b):
    best = None
    for i, pa in enumerate(pool[a]):
        if i in taken[a] or pa["title"] in sel_titles: continue
        ga = fgrams(pa["body"])
        if ga & sel_g: continue
        ca = chars(pa["body"]); ba = bucket(pa["body"])
        for j, pb in enumerate(pool[b]):
            if j in taken[b] or pb["title"] in sel_titles or pb["title"] == pa["title"]: continue
            cb = chars(pb["body"])
            r = max(ca, cb) / min(ca, cb)
            if r > 1.6: continue
            gb = fgrams(pb["body"])
            if gb & sel_g or gb & ga: continue
            bb = bucket(pb["body"])
            score = (0 if (ba and ba == bb) else 1, r)
            if best is None or score < best[0]: best = (score, i, j)
        if best and best[0][0] == 0 and best[0][1] < 1.15: break
    if best is None: return None
    _, i, j = best
    taken[a].add(i); taken[b].add(j)
    pa, pb = pool[a][i], pool[b][j]
    for p in (pa, pb):
        sel_g.update(fgrams(p["body"])); sel_titles.add(p["title"])
    return pa, pb

pairs, fails = [], []
for a, b in EDGES:
    got = pick_pair(a, b)
    if got is None: fails.append(f"{a}-{b}"); continue
    pa, pb = got
    pairs.append(((a, pa), (b, pb)))
if fails: print("!! 配不出:", fails)

rng.shuffle(pairs)
# 逐诗人侧位配平：贪心翻边，最小化每位诗人 |A−B| 之和（防位置偏差混入诗人级统计）
def imbalance():
    c = collections.Counter()
    for k, ((a, _), (b, _)) in enumerate(pairs):
        A, B = (b, a) if flip[k] else (a, b)
        c[A] += 1; c[B] -= 1
    return sum(abs(v) for v in c.values())
best_flip, best_imb = None, 10**9
for restart in range(200):
    r2 = random.Random(150015 + restart)
    flip = [r2.random() < 0.5 for _ in range(len(pairs))]
    improved = True
    while improved:
        improved = False
        for k in range(len(pairs)):
            before = imbalance(); flip[k] = not flip[k]
            if imbalance() < before: improved = True
            else: flip[k] = not flip[k]
    if imbalance() < best_imb: best_imb, best_flip = imbalance(), list(flip)
    if best_imb == 0: break
flip = best_flip
print("配平后失衡度:", imbalance())
out = []
for k, ((a, pa), (b, pb)) in enumerate(pairs):
    L, R = ((b, pb), (a, pa)) if flip[k] else ((a, pa), (b, pb))
    out.append({"kind": "hh",
        "A": {"src": "human", "author": L[0], "title": L[1]["title"], "body": L[1]["body"].strip()},
        "B": {"src": "human", "author": R[0], "title": R[1]["title"], "body": R[1]["body"].strip()}})
side = collections.Counter()
for p in out:
    side[p["A"]["author"] + "_A"] += 1
json.dump(out, open('v15_hh_pairs.json', 'w'), ensure_ascii=False, indent=1)
print(f"OK: {len(out)} 对 → v15_hh_pairs.json")
print("A侧分布:", dict(side))
print("出场核对:", dict(collections.Counter(p[s]["author"] for p in out for s in "AB")))
