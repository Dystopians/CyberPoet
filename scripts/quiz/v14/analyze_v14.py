# v14 结果码解码分析：M8vsM4（重训臂对现役）/ M8vsM8sft（修正后的偏好训练对它自己的桥）+ 分臂图灵率 +
# DPO 金标行 + 反杀裱框候选 + 批注辑录。用法: python3 analyze_v14.py <码或文件>
import json, sys, base64, math, collections, re
from v5_lib import tags, norm
from v14_arms import LEAD_B
# 分点检测（与 panel.py SECT2 同式；不 import panel——它顶层会吃 argv 当 jsonl 跑面板）
SECT2 = re.compile(r"(?:^|\n)\s*(?:[0-9]+[\.、．]?|[（(][一二三四五六七八九十][)）]|[一二三四五六七八九十][、.])\s*(?:\n|$)")

def binom2(k, n):
    if n == 0: return 1.0
    logC = lambda n, k: sum(math.log(n-k+i)-math.log(i) for i in range(1, k+1))
    pk = lambda j: math.exp(logC(n, j) + n*math.log(0.5))
    obs = pk(k)
    return min(1.0, sum(pk(j) for j in range(n+1) if pk(j) <= obs+1e-12))

arg = sys.argv[1]
try: raw = open(arg).read().strip()
except (FileNotFoundError, OSError): raw = arg.strip()
d = json.loads(base64.b64decode(raw).decode("utf-8"))
assert d.get("v") == 14, f"结果码版本 {d.get('v')} != 14"
picks = {int(i): v for i, v in d["picks"].items()}
marks = {int(i): v for i, v in d.get("marks", {}).items() if v}
pairs = json.load(open('v14_pairs_final.json'))
print(f"署名: {d.get('nick','')} | 表态 {len(picks)}/{len(pairs)}，弃权 {sum(1 for v in picks.values() if v=='X')}，批注 {len(marks)} 条\n")

# ---- 1) aa 臂间主判 ----
duel = collections.defaultdict(lambda: [0, 0])   # (armX, armY) 有序 -> [X胜, 总]
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "aa" or pk not in "AB": continue
    ma, mb = q["A"]["model"], q["B"]["model"]
    x, y = sorted([ma, mb])
    win_x = (pk == "A" and ma == x) or (pk == "B" and mb == x)
    duel[(x, y)][0] += int(win_x); duel[(x, y)][1] += 1
print("aa 臂间对决（M8 对 M4 / M8 对 M8sft；预登记见下；45–55% 记均衡，决定票 <30 只记不判）:")
for (x, y), (wx, n) in sorted(duel.items()):
    print(f"  {x} {wx} : {n-wx} {y}   p={binom2(wx,n):.3f}" + ("  **" if binom2(wx,n) < 0.05 else ""))

# ---- 1b) 预登记对账（v14 制卷记录，作答前锁定）----
def duel_stat(lead, other):
    w = n = 0
    for i, pk in picks.items():
        q = pairs[i]
        if q["kind"] != "aa" or pk not in "AB": continue
        ms = {q["A"]["model"], q["B"]["model"]}
        if ms != {lead + "_dpo", other + "_dpo"}: continue
        n += 1
        if q[pk]["model"] == lead + "_dpo": w += 1
    return w, n
print("\n预登记对账（判决只认票；预测只用于事后归因）:")
for lead, other, cond, label in (("M8","M4",lambda r: r>0.55,"预登记：M8 对现役 >55%（低于 45% 记负，45–55% 记均衡；36 局里若一半弃权，决定票约 18，检验力不足，只记不判）"),
                                 (LEAD_B,"M8sft",lambda r: r>0.55,"预登记：修正后的偏好训练对自己的桥 >55%（同上口径）")):
    w, n = duel_stat(lead, other)
    r = w / n if n else 0
    verdict = "无票" if not n else ("均衡（45–55%）" if 0.45 <= r <= 0.55 else ("命中" if cond(r) else ("记负（<45%）" if r < 0.45 else "未命中")))
    if n and n < 30: verdict += f"——决定票 {n} <30，只记不判"
    print(f"  {lead}vs{other}: {w}/{n} = {r:.0%}  {label} → {verdict}")

# ---- 2) 分臂图灵率 ----
print("\nha 分臂（AI 得票 = 反杀原作，硬通货）:")
byarm = collections.defaultdict(lambda: [0, 0])
upsets = []
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "ha" or pk not in "AB": continue
    ai = "A" if q["A"]["src"] == "ai" else "B"
    m = q[ai]["model"]
    byarm[m][1] += 1
    if pk == ai:
        byarm[m][0] += 1
        upsets.append((i, m, q[("B" if ai == "A" else "A")]["author"], q.get("title", "")))
for m, (w, n) in sorted(byarm.items()):
    print(f"  {m}: 反杀 {w}/{n} = {w/n:.0%}")
if upsets:
    print("  反杀清单（裱框候选，逐首过目后挂 首批过关诗.html）:")
    for i, m, a, t in upsets: print(f"    [{i}] {m} 胜 {a}《{t}》")

# ---- 3) 信号复验（第三次：无装置 p=0.044、长句行 p=0.011 的跨卷续记）----
DIMS = [("device","有装置","无装置"),("linelen","长句行","短句行"),("punct","满标点","无标点"),
        ("density","密","疏"),("ending","悬置","落地"),("simile","有喻","无喻"),
        ("register","口语","书面"),("abstract","抽象","具象"),("person","有你","无你"),("heat","热","冷")]
print("\n十维（全卷题池）:")
for k, L, R in DIMS:
    l = r = 0
    for i, pk in picks.items():
        if pk not in "AB": continue
        q = pairs[i]
        ta, tb = tags(q["A"]["body"]), tags(q["B"]["body"])
        if not ta[k] or not tb[k] or ta[k] == tb[k]: continue
        if (ta if pk == "A" else tb)[k] == L: l += 1
        else: r += 1
    p = binom2(l, l+r)
    print(f"  {k:9s} {L}{l:3d} : {r:<3d}{R}  p={p:.3f}" + ("  **" if p < 0.05 else ""))

# ---- 4) hh 新诗人票 ----
print("\n诗人级判定（本卷无真人互殴局，仅供口径一致）:")
poet = collections.defaultdict(lambda: [0, 0])
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "hh" or pk not in "AB": continue
    for s in "AB":
        a = q[s].get("author")
        if not a: continue
        poet[a][1] += 1
        if pk == s: poet[a][0] += 1
for a, (w, n) in sorted(poet.items(), key=lambda x: -(abs(x[1][0]/max(x[1][1],1)-.5)*math.sqrt(x[1][1]))):
    p = binom2(w, n)
    print(f"  {a:12s} {w:2d}/{n:2d} = {w/max(n,1):4.0%}  p={p:.3f}" + ("  **" if p < 0.05 and n >= 6 else ""))

# ---- 5) DPO 金标行（沿 v6 规则：ha 决票产 chosen/rejected；弃分点反向对加权 2.0）----
rows = []
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "ha" or pk not in "AB": continue
    win, lose = q[pk], q[("B" if pk == "A" else "A")]
    instr = f"以《{q.get('title','无题')}》为题写一首现代诗。"
    w = 2.0 if (SECT2.search(lose["body"]) and not SECT2.search(win["body"])) else 1.0
    rows.append({"instruction": instr, "chosen": win["body"].strip(), "rejected": lose["body"].strip(),
                 "weight": w, "src": f"v14[{i}]", "chosen_src": win["src"]})
json.dump(rows, open('dpo_rows_owner_v14.json', 'w'), ensure_ascii=False, indent=1)
print(f"\nDPO 金标行: {len(rows)} 条 → dpo_rows_owner_v14.json（加权 2.0 的 {sum(1 for r in rows if r['weight']>1)} 条）")

# ---- 6) 批注辑录 ----
if marks:
    print("\n批注辑录:")
    for i in sorted(marks):
        q = pairs[i]; pk = picks.get(i, "—")
        def who(s): return s.get("author") or ("AI·" + s.get("model", "?"))
        sel = {"A": who(q["A"]), "B": who(q["B"]), "X": "都不要"}.get(pk, "—")
        print(f"  [{i}] {q['kind']} {who(q['A'])} vs {who(q['B'])} 选{pk}({sel}): {marks[i]}")
