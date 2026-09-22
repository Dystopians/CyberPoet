# 全量合并：v3/v5/v6/v7/v7.5 五卷可逐对复原的标注 → 统一表
#   1) 十维两口径合并（纯人对 vs 含机对）——检验「人机反转」
#   2) 诗人两口径战绩（对真人 hh / 对 AI 的人侧 ha）
#   3) 质感分卷统计（v7 为 ha/aa 样本外）
# 输出 merged_labels_stats.json + 控制台表
import json, math, collections, sys
from v5_lib import tags

def binom2(k, n):
    if n == 0: return 1.0
    logC = lambda n, k: sum(math.log(n-k+i)-math.log(i) for i in range(1, k+1))
    pk = lambda j: math.exp(logC(n, j) + n*math.log(0.5))
    obs = pk(k)
    return min(1.0, sum(pk(j) for j in range(n+1) if pk(j) <= obs+1e-12))

def picks56(lf):
    d = json.load(open(lf)); return {int(i): v for i, v in d["picks"].items() if v in "AB"}
def picks3(lf):
    d = json.load(open(lf)); return {r["i"]: r["choice"] for r in d["labels"] if r.get("choice") in "AB"}

SETS = [("v3", "pairs_final.json", picks3("labels_owner_v3.json")),
        ("v5", "v5_pairs_final.json", picks56("labels_owner_v5.json")),
        ("v6", "v6_pairs_final.json", picks56("labels_owner_v6.json")),
        ("v7", "v7_pairs_final.json", picks56("labels_owner_v7.json")),
        ("v7.5", "v75_hh_fixed.json", picks56("labels_owner_v75.json")),
        ("v8", "v8_pairs_final.json", picks56("labels_owner_v8.json")),
        ("v9", "v9_pairs_final.json", picks56("labels_owner_v9.json")),
        ("v10b", "v10b_pairs_final.json", picks56("labels_owner_v10b.json")),
        ("v11", "v11_pairs_final.json", picks56("labels_owner_v11.json"))]

DIMS = [("device","有装置","无装置"),("linelen","长句行","短句行"),("punct","满标点","无标点"),
        ("density","密","疏"),("ending","悬置","落地"),("simile","有喻","无喻"),
        ("register","口语","书面"),("abstract","抽象","具象"),("person","有你","无你"),("heat","热","冷")]

dim_h = collections.defaultdict(lambda: [0, 0])   # 纯人对
dim_m = collections.defaultdict(lambda: [0, 0])   # 含机对
poet_hh = collections.defaultdict(lambda: [0, 0]) # 对真人
poet_ha = collections.defaultdict(lambda: [0, 0]) # 人侧对 AI
tex = collections.defaultdict(lambda: [0, 0])     # 卷 -> 质感命中
sys.path.insert(0, '.')
import texture_retrodict as T

for name, pf, picks in SETS:
    pairs = json.load(open(pf))
    for i, pk in picks.items():
        q = pairs[i]
        hh = q["A"].get("src", "human") == "human" and q["B"].get("src", "human") == "human"
        ta, tb = tags(q["A"]["body"]), tags(q["B"]["body"])
        tgt = dim_h if hh else dim_m
        for k, L, R in DIMS:
            if not ta[k] or not tb[k] or ta[k] == tb[k]: continue
            if (ta if pk == "A" else tb)[k] == L: tgt[k][0] += 1
            else: tgt[k][1] += 1
        # 诗人两口径
        if hh:
            for s in "AB":
                a = q[s].get("author")
                if not a: continue
                poet_hh[a][1] += 1
                if pk == s: poet_hh[a][0] += 1
        elif q["kind"] == "ha":
            hu = "A" if q["A"].get("src") == "human" else "B"
            a = q[hu].get("author")
            if a:
                poet_ha[a][1] += 1
                if pk == hu: poet_ha[a][0] += 1
        # 质感
        xa, xb = T.texture(q["A"]["body"]), T.texture(q["B"]["body"])
        if xa is not None and xb is not None and abs(xa-xb) > 1e-9:
            key = name + ("/hh" if hh else "/机")
            tex[key][1] += 1
            tex[key][0] += int(("A" if xa > xb else "B") == pk)

print("== 十维两口径（纯人对 | 含机对）==")
for k, L, R in DIMS:
    h, m = dim_h[k], dim_m[k]
    ph, pm = binom2(h[0], sum(h)), binom2(m[0], sum(m))
    print(f"{k:9s} 纯人 {L}{h[0]:3d}:{h[1]:<3d} p={ph:.3f}{' **' if ph<0.05 else '   '} | 含机 {L}{m[0]:3d}:{m[1]:<3d} p={pm:.3f}{' **' if pm<0.05 else ''}")

print("\n== 诗人两口径（对真人 | 人侧对AI）出场合计≥8 ==")
allp = set(poet_hh) | set(poet_ha)
rows = []
for a in allp:
    h, m = poet_hh[a], poet_ha[a]
    if h[1] + m[1] < 8: continue
    rows.append((a, h, m))
rows.sort(key=lambda r: -(r[1][0]/max(r[1][1],1) if r[1][1]>=6 else 0.5))
for a, h, m in rows:
    ph = binom2(h[0], h[1]) if h[1] else 1
    pm = binom2(m[0], m[1]) if m[1] else 1
    print(f"{a:8s} 对真人 {h[0]:2d}/{h[1]:<2d} p={ph:.3f}{' **' if ph<0.05 and h[1]>=6 else '   '} | 对AI人侧 {m[0]:2d}/{m[1]:<2d} p={pm:.3f}{' **' if pm<0.05 and m[1]>=6 else ''}")

print("\n== 质感分卷（v7 为 ha/aa 样本外）==")
tot = [0, 0]
for k in sorted(tex):
    h, n = tex[k]; tot[0] += h; tot[1] += n
    print(f"{k:8s} {h}/{n} = {h/n:.0%}  p={binom2(h,n):.4f}")
print(f"全部     {tot[0]}/{tot[1]} = {tot[0]/tot[1]:.0%}  p={binom2(tot[0],tot[1]):.6f}")

json.dump({"dim_h": dim_h, "dim_m": dim_m, "poet_hh": poet_hh, "poet_ha": poet_ha,
           "tex": tex}, open("merged_labels_stats.json", "w"), ensure_ascii=False, indent=1)
print("\n→ merged_labels_stats.json")
