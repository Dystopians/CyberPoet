# v16 结果码解码分析（09-25，实验 2「pt6+散文」）：头条 = 同卷对 M4；一对决 M4PvsM4；
# DPO 金标行 + 批注辑录。用法: python3 analyze_v16.py <码或文件>
import json, sys, base64, math, collections, re
from v5_lib import tags, norm
from v16_arms import LEAD_B, DUEL_C, MAIN
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
assert d.get("v") == 16, f"结果码版本 {d.get('v')} != 16"
picks = {int(i): v for i, v in d["picks"].items()}
marks = {int(i): v for i, v in d.get("marks", {}).items() if v}
pairs = json.load(open('v16_pairs_final.json'))
print(f"署名: {d.get('nick','')} | 表态 {len(picks)}/{len(pairs)}，弃权 {sum(1 for v in picks.values() if v=='X')}，批注 {len(marks)} 条\n")

# ---- 0) 头条：同卷对 M4（09-22 v14 解盲：M4 权重未变而其同卷都不要率 5%→50%，都不要率只能同卷对着 M4 读）----
print("头条：同卷对 M4（M4 是尺子；决定票 = 你选了一边的局）:")
def duel_stat(lead, other):
    w = n = x = 0
    for i, pk in picks.items():
        q = pairs[i]
        if q["kind"] != "aa" or pk not in "ABX": continue
        ms = {q["A"]["model"], q["B"]["model"]}
        if ms != {lead + "_dpo", other + "_dpo"}: continue
        if pk == "X": x += 1; continue
        n += 1
        if q[pk]["model"] == lead + "_dpo": w += 1
    return w, n, x
for lead, other, what in ((MAIN, "M4", "多读了散文 对 现役"),):
    w, n, x = duel_stat(lead, other)
    print(f"  {lead} 对 {other}（{what}）：{lead} {w} : {n - w} {other}，都不要 {x}/{n + x}" + (f"，p={binom2(w, n):.3f}" if n else ""))
X = collections.defaultdict(lambda: {"ha": [0, 0]})
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "ha" or pk not in "ABX": continue
    for s_ in "AB":
        if q[s_]["src"] == "ai": c = X[q[s_]["model"]]["ha"]; c[1] += 1; c[0] += int(pk == "X")
print("  真伪题都不要（连真人一起）：" + "；".join(f"{m} {c['ha'][0]}/{c['ha'][1]}" for m, c in sorted(X.items())))
print("  对强真人诗（标准局）：本卷无；本卷 hh 24 局选出的真人诗做下一卷标准局。\n")

# ---- 1) aa 臂间主判 ----
duel = collections.defaultdict(lambda: [0, 0])   # (armX, armY) 有序 -> [X胜, 总]
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "aa" or pk not in "AB": continue
    ma, mb = q["A"]["model"], q["B"]["model"]
    x, y = sorted([ma, mb])
    win_x = (pk == "A" and ma == x) or (pk == "B" and mb == x)
    duel[(x, y)][0] += int(win_x); duel[(x, y)][1] += 1
print("aa 臂间对决（M4P 对 M4；预登记见下；45–55% 记均衡，决定票 <30 只记不判）:")
for (x, y), (wx, n) in sorted(duel.items()):
    print(f"  {x} {wx} : {n-wx} {y}   p={binom2(wx,n):.3f}" + ("  **" if binom2(wx,n) < 0.05 else ""))

# ---- 1b) 预登记对账（v16 制卷记录，作答前锁定）----
print("\n预登记对账（判决只认票；n<30 只记不判；45–55% 记均衡）:")
PRE = ((MAIN, "M4", None, "不预测——这是本卷的问题。读法：≤45% 散文把诗写坏了；≥55% 散文反而有益；45–55% 散文无关，病因不在语料"),)
for lead, other, cond, label in PRE:
    w, n, _ = duel_stat(lead, other)
    r = w / n if n else 0
    if not n: verdict = "无票"
    elif cond is None: verdict = "已记录（不预测）"
    elif 0.45 <= r <= 0.55: verdict = "均衡（45–55%）"
    elif cond(r): verdict = "命中"
    else: verdict = "记负（<45%）" if r < 0.45 else "未命中"
    if n and n < 30: verdict += f"——决定票 {n} <30，只记不判"
    print(f"  {lead}vs{other}: {w}/{n} = {r:.0%}  {label} → {verdict}")

# ---- 2) 分臂图灵率 ----
print("\nha 分臂（附注：AI 得票局数。09-21 起不叫硬通货——赢的多半是主人本来就不选的真人写法，见 owner-absolute-level 记录）:")
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
    print(f"  {m}: AI 得票 {w}/{n} = {w/n:.0%}")
if upsets:
    print("  AI 得票局（只列不裱框；过关诗册 09-21 起停更）:")
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
print("\n诗人级判定（hh 24 局，六家各 8 出场；赢的诗 = 下一卷标准局候选）:")
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
std = []
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "hh" or pk not in "AB": continue
    win, lose = q[pk], q["B" if pk == "A" else "A"]
    std.append({"i": i, "author": win["author"], "title": win["title"], "beat": f"{lose['author']}《{lose['title']}》", "mark": marks.get(i, "")})
json.dump(std, open('v16_hh_winners.json', 'w'), ensure_ascii=False, indent=1)
print(f"  你选中的真人诗 {len(std)} 首 → v16_hh_winners.json（下一卷标准局的候选）；都不要 {sum(1 for i, pk in picks.items() if pairs[i]['kind'] == 'hh' and pk == 'X')} 局")
for r in std: print(f"    [{r['i']}] {r['author']}《{r['title']}》 胜 {r['beat']}" + (f"  批注：{r['mark']}" if r['mark'] else ""))

# ---- 5) DPO 金标行（沿 v6 规则：ha 决票产 chosen/rejected；弃分点反向对加权 2.0）----
rows = []
for i, pk in picks.items():
    q = pairs[i]
    if q["kind"] != "ha" or pk not in "AB": continue
    win, lose = q[pk], q[("B" if pk == "A" else "A")]
    instr = f"以《{q.get('title','无题')}》为题写一首现代诗。"
    w = 2.0 if (SECT2.search(lose["body"]) and not SECT2.search(win["body"])) else 1.0
    rows.append({"instruction": instr, "chosen": win["body"].strip(), "rejected": lose["body"].strip(),
                 "weight": w, "src": f"v16[{i}]", "chosen_src": win["src"]})
json.dump(rows, open('dpo_rows_owner_v16.json', 'w'), ensure_ascii=False, indent=1)
print(f"\nDPO 金标行: {len(rows)} 条 → dpo_rows_owner_v16.json（加权 2.0 的 {sum(1 for r in rows if r['weight']>1)} 条）")

# ---- 6) 批注辑录 ----
if marks:
    print("\n批注辑录:")
    for i in sorted(marks):
        q = pairs[i]; pk = picks.get(i, "—")
        def who(s): return s.get("author") or ("AI·" + s.get("model", "?"))
        sel = {"A": who(q["A"]), "B": who(q["B"]), "X": "都不要"}.get(pk, "—")
        print(f"  [{i}] {q['kind']} {who(q['A'])} vs {who(q['B'])} 选{pk}({sel}): {marks[i]}")
