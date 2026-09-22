# 臂级累计账（09-21 起有脚本；此前 arm_ledger_v5_v10b.json 是手算的）：v5–v11 全部机机局与真伪局逐对复原。
# 输出 arm_ledger_v5_v11.json：arm_aa（AI 对 AI 胜/场）、arm_ha（反杀/场）、pair（逐对矩阵，键按字母序，值=[前者胜, 决定票]）、
# both_bad（每对决的都不要数）、ha_both_bad（真伪题里连真人一起都不要的数）。用法: python3 arm_ledger.py
import json, math, collections
def binom2(k, n):
    if n == 0: return 1.0
    logC = lambda n, k: sum(math.log(n-k+i)-math.log(i) for i in range(1, k+1))
    pk = lambda j: math.exp(logC(n, j) + n*math.log(0.5)); obs = pk(k)
    return min(1.0, sum(pk(j) for j in range(n+1) if pk(j) <= obs+1e-12))
def picks56(lf):
    d = json.load(open(lf)); return {int(i): v for i, v in d["picks"].items()}
SETS = [("v5", "v5_pairs_final.json", "labels_owner_v5.json"), ("v6", "v6_pairs_final.json", "labels_owner_v6.json"),
        ("v7", "v7_pairs_final.json", "labels_owner_v7.json"), ("v8", "v8_pairs_final.json", "labels_owner_v8.json"),
        ("v9", "v9_pairs_final.json", "labels_owner_v9.json"), ("v10b", "v10b_pairs_final.json", "labels_owner_v10b.json"),
        ("v11", "v11_pairs_final.json", "labels_owner_v11.json")]
aa = collections.defaultdict(lambda: [0, 0]); ha = collections.defaultdict(lambda: [0, 0]); pair = collections.defaultdict(lambda: [0, 0])
bb = collections.Counter(); habb = collections.Counter(); per_set = {}
for name, pf, lf in SETS:
    pairs = json.load(open(pf)); picks = picks56(lf); s_aa = collections.defaultdict(lambda: [0, 0]); s_bb = 0; s_n = 0
    for i, q in enumerate(pairs):
        pk = picks.get(i)
        if q["kind"] == "aa":
            ma, mb = q["A"]["model"], q["B"]["model"]; key = "|".join(sorted([ma, mb])); s_n += 1
            if pk == "X": bb[key] += 1; s_bb += 1; continue
            if pk not in ("A", "B"): continue
            w, l = (ma, mb) if pk == "A" else (mb, ma)
            aa[w][0] += 1; aa[w][1] += 1; aa[l][1] += 1; s_aa[w][0] += 1; s_aa[w][1] += 1; s_aa[l][1] += 1
            pair[key][1] += 1
            if w == key.split("|")[0]: pair[key][0] += 1
        elif q["kind"] == "ha":
            s = "A" if q["A"]["src"] == "ai" else "B"; m = q[s]["model"]
            if pk == "X": habb[m] += 1; continue
            if pk not in ("A", "B"): continue
            ha[m][1] += 1
            if pk == s: ha[m][0] += 1
    per_set[name] = {"aa_by_arm": dict(s_aa), "aa_both_bad": s_bb, "aa_total": s_n}
out = {"arm_aa": dict(aa), "arm_ha": dict(ha), "pair": dict(pair), "both_bad": dict(bb), "ha_both_bad": dict(habb), "per_set": per_set}
json.dump(out, open("arm_ledger_v5_v11.json", "w"), ensure_ascii=False, indent=1)
print("臂 | AI对AI 胜/场 | 胜率 | p | 反杀/场 | 图灵率 | 真伪题都不要")
for m, (w, n) in sorted(aa.items(), key=lambda x: -x[1][0] / max(1, x[1][1])):
    hw, hn = ha.get(m, [0, 0]); print(f"{m:10s} | {w}/{n} | {w/max(1,n):.0%} | {binom2(w,n):.3f} | {hw}/{hn} | {hw/max(1,hn):.0%} | {habb.get(m,0)}")
print("\n逐对（前者胜:后者胜，都不要）:")
for k, (w, n) in sorted(pair.items()):
    a, b = k.split("|"); print(f"  {a} {w}:{n-w} {b}  p={binom2(w,n):.3f}  都不要 {bb.get(k,0)}")
