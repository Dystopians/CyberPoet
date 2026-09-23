# 标记史深度分析（09-21，主人：「你有着浩如烟海的标记历史了，好好分析一下」）。
# 只数可数的东西：每首诗算 24 个可数特征，与主人的票对账。不用任何模型打分；逻辑回归只用来看「哪些可数特征跟着票走」，
# 不做门、不排序上卷。输出 label_history_analysis.json + 控制台表。
import json, re, math, collections, sys
import numpy as np
Q = "/data/peilincai/CyberPoetTraining/claude_night_20260827/quiz_v3/"
V1 = "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference/labels/all_labels.json"

# ---------- 数据装载：统一成 (set, i, kind, A, B, pick, mark)，A/B = {src, who, body} ----------
def picks56(lf):
    d = json.load(open(lf)); return {int(i): v for i, v in d["picks"].items()}, {int(i): v for i, v in d.get("marks", {}).items() if v}
def picks3(lf):
    d = json.load(open(lf)); return {r["i"]: r.get("choice") for r in d["labels"]}, {r["i"]: r.get("remark", "") for r in d["labels"] if r.get("remark")}
SETS = [("v3", "pairs_final.json", picks3), ("v5", "v5_pairs_final.json", picks56), ("v6", "v6_pairs_final.json", picks56),
        ("v7", "v7_pairs_final.json", picks56), ("v7.5", "v75_hh_fixed.json", picks56), ("v8", "v8_pairs_final.json", picks56),
        ("v9", "v9_pairs_final.json", picks56), ("v10b", "v10b_pairs_final.json", picks56), ("v11", "v11_pairs_final.json", picks56), ("v12", "v12_pairs_final.json", picks56),
        ("v13", "v13_pairs_final.json", picks56), ("v14", "v14_pairs_final.json", picks56)]
LF = {"v3": "labels_owner_v3.json", "v5": "labels_owner_v5.json", "v6": "labels_owner_v6.json", "v7": "labels_owner_v7.json", "v7.5": "labels_owner_v75.json",
      "v8": "labels_owner_v8.json", "v9": "labels_owner_v9.json", "v10b": "labels_owner_v10b.json", "v11": "labels_owner_v11.json", "v12": "labels_owner_v12.json", "v13": "labels_owner_v13.json", "v14": "labels_owner_v14.json"}
rows = []
for name, pf, fn in SETS:
    pairs = json.load(open(Q + pf)); picks, marks = fn(Q + LF[name])
    for i, q in enumerate(pairs):
        pk = picks.get(i)
        if pk not in ("A", "B", "X"): continue
        def side(s):
            x = q[s]; return {"src": x["src"], "who": x.get("author") or x.get("model") or "?", "body": x["body"], "title": x.get("title") or q.get("title", "")}
        rows.append({"set": name, "i": i, "kind": q["kind"], "A": side("A"), "B": side("B"), "pick": pk, "mark": marks.get(i, "")})
n_quiz = len(rows)
for x in json.load(open(V1)):
    if x.get("choice") not in ("A", "B", "X"): continue
    rows.append({"set": "v1", "i": x["pk"], "kind": "aa", "A": {"src": "ai", "who": x["ma"], "body": x["ba"], "title": ""},
                 "B": {"src": "ai", "who": x["mb"], "body": x["bb"], "title": ""}, "pick": x["choice"], "mark": ""})
print(f"装入 {len(rows)} 局（测验卷 {n_quiz} + v1 时代 {len(rows)-n_quiz}）：",
      dict(collections.Counter(r["kind"] for r in rows)), "| 都不要", sum(1 for r in rows if r["pick"] == "X"))

# ---------- 可数特征 ----------
PUN = "，。；：、！？"
DECL = ["我们", "你们", "死亡", "如果", "为了", "不能", "孤独", "痛苦", "历史", "永恒", "太阳", "诗人", "头颅", "大地", "歌唱", "上帝", "肉体", "多少", "这么", "她们"]
SIM = ["像", "仿佛", "如同", "宛如", "犹如", "恍若", "好像", "似的"]
ABS = ["时间", "灵魂", "命运", "生命", "记忆", "永恒", "真理", "自由", "孤独", "黑暗", "光明", "存在", "虚无", "沉默", "梦", "死亡", "爱", "痛苦", "世界", "宇宙"]
CLS = re.compile(r"一[个只条种片段座张把颗根块道场阵抹缕丝声句行首朵棵株团粒滴层枚扇面册幅盏束簇座]")
SECT = re.compile(r"(?:^|\n)\s*(?:[0-9]+[\.、．]?|[（(][一二三四五六七八九十][)）]|[一二三四五六七八九十][、.．])\s*(?:\n|$)")
def feats(t, title=""):
    body = t.strip(); L = [l.strip() for l in body.split("\n") if l.strip()]
    z = re.sub(r"\s+", "", body); n = max(1, len(z)); nl = max(1, len(L))
    stanzas = len([b for b in re.split(r"\n\s*\n", body) if b.strip()])
    cnt = collections.Counter(L); rep_max = max(cnt.values()) if cnt else 0
    rep_share = sum(v for v in cnt.values() if v >= 2) / nl
    last = L[-1] if L else ""; first = L[0] if L else ""
    tt = re.sub(r"[《》\s]", "", title)
    f = {
        "chars": n, "lines": nl, "cpl": n / nl, "stanzas": stanzas, "maxline": max(len(re.sub(r"\s", "", l)) for l in L) if L else 0,
        "short_share": sum(1 for l in L if len(re.sub(r"\s", "", l)) <= 4) / nl,
        "punct100": sum(z.count(c) for c in PUN) / n * 100, "qmark": z.count("？") + z.count("?"), "excl": z.count("！") + z.count("!"),
        "ellipsis": z.count("……") + z.count("..."), "dash": z.count("——"),
        "cls100": len(CLS.findall(z)) / n * 100, "sim100": sum(z.count(w) for w in SIM) / n * 100,
        "decl100": sum(z.count(w) for w in DECL) / n * 100, "abs100": sum(z.count(w) for w in ABS) / n * 100,
        "you100": z.count("你") / n * 100, "i100": z.count("我") / n * 100, "de100": z.count("的") / n * 100,
        "rep_max": rep_max, "rep_share": rep_share, "title_echo": (sum(1 for l in L if tt and tt in l) if tt else 0),
        "sect": 1 if SECT.search(body) else 0, "last_len": len(re.sub(r"\s", "", last)), "last_q": 1 if last.endswith(("？", "?")) else 0,
        "last_abs": 1 if any(w in last for w in ABS) else 0, "last_period": 1 if last.endswith(("。", "．")) else 0,
        "ttr": len(set(z)) / n, "latin": len(re.findall(r"[A-Za-z]", z)), "first_len": len(re.sub(r"\s", "", first)),
    }
    return f
FN = None
for r in rows:
    for s in "AB":
        r[s]["f"] = feats(r[s]["body"], r[s]["title"])
FN = list(rows[0]["A"]["f"].keys())
LABEL = {"chars": "字数", "lines": "行数", "cpl": "字/行", "stanzas": "节数", "maxline": "最长行字数", "short_share": "短行(≤4字)占比", "punct100": "标点/百字",
         "qmark": "问号数", "excl": "叹号数", "ellipsis": "省略号数", "dash": "破折号数", "cls100": "「一+量词」/百字", "sim100": "比喻词/百字", "decl100": "陈述大词/百字",
         "abs100": "抽象名词/百字", "you100": "「你」/百字", "i100": "「我」/百字", "de100": "「的」/百字", "rep_max": "同一行最多重复次数", "rep_share": "重复行占比",
         "title_echo": "含题目的行数", "sect": "有分节标号", "last_len": "末行字数", "last_q": "末行问号收尾", "last_abs": "末行含抽象名词", "last_period": "末行句号收尾",
         "ttr": "用字丰富度(异字/总字)", "latin": "拉丁字母数", "first_len": "首行字数"}

def binom2(k, n):
    if n == 0: return 1.0
    logC = lambda n, k: sum(math.log(n-k+i)-math.log(i) for i in range(1, k+1))
    pk = lambda j: math.exp(logC(n, j) + n*math.log(0.5)); obs = pk(k)
    return min(1.0, sum(pk(j) for j in range(n+1) if pk(j) <= obs+1e-12))
def ranksum_p(a, b):
    # Mann–Whitney U 的正态近似（两侧）
    a = np.asarray(a, float); b = np.asarray(b, float); n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0: return 1.0
    allv = np.concatenate([a, b]); order = allv.argsort(); ranks = np.empty(len(allv)); ranks[order] = np.arange(1, len(allv)+1)
    # 并列取平均秩
    uniq, inv, cnt = np.unique(allv, return_inverse=True, return_counts=True)
    csum = np.cumsum(cnt); start = csum - cnt + 1; ranks = ((start + csum) / 2)[inv]
    U = ranks[:n1].sum() - n1*(n1+1)/2; mu = n1*n2/2
    T = sum(c**3 - c for c in cnt); sd = math.sqrt(n1*n2/12 * ((n1+n2+1) - T/((n1+n2)*(n1+n2-1)))) if n1+n2 > 1 else 1
    if sd == 0: return 1.0
    zz = (U - mu) / sd; return math.erfc(abs(zz) / math.sqrt(2))
out = {}

# ---------- 一、人 vs 机：机器味的可数画像（真伪局里的人诗与 AI 诗） ----------
hum = [r[s]["f"] for r in rows if r["kind"] == "ha" for s in "AB" if r[s]["src"] == "human"]
ai = [r[s]["f"] for r in rows if r["kind"] == "ha" for s in "AB" if r[s]["src"] == "ai"]
print(f"\n== 一、人诗 {len(hum)} 首 vs AI 诗 {len(ai)} 首（真伪局），中位数 ==")
sec1 = []
for k in FN:
    a = np.median([f[k] for f in hum]); b = np.median([f[k] for f in ai]); p = ranksum_p([f[k] for f in hum], [f[k] for f in ai])
    sec1.append({"feat": k, "label": LABEL[k], "human_med": float(a), "ai_med": float(b), "p": p})
sec1.sort(key=lambda x: x["p"])
for x in sec1[:14]: print(f"  {x['label']:14s} 人 {x['human_med']:7.2f} | AI {x['ai_med']:7.2f} | p={x['p']:.1e}")
out["human_vs_ai"] = sec1

# ---------- 二、反杀的 AI 诗 vs 没反杀的 AI 诗（真伪局，决定票） ----------
won = [r[s]["f"] for r in rows if r["kind"] == "ha" and r["pick"] in "AB" for s in "AB" if r[s]["src"] == "ai" and r["pick"] == s]
lost = [r[s]["f"] for r in rows if r["kind"] == "ha" and r["pick"] in "AB" for s in "AB" if r[s]["src"] == "ai" and r["pick"] != s]
print(f"\n== 二、反杀的 AI 诗 {len(won)} 首 vs 输给真人的 AI 诗 {len(lost)} 首，中位数 ==")
sec2 = []
for k in FN:
    a = np.median([f[k] for f in won]); b = np.median([f[k] for f in lost]); p = ranksum_p([f[k] for f in won], [f[k] for f in lost])
    sec2.append({"feat": k, "label": LABEL[k], "won_med": float(a), "lost_med": float(b), "p": p})
sec2.sort(key=lambda x: x["p"])
for x in sec2[:12]: print(f"  {x['label']:14s} 反杀 {x['won_med']:7.2f} | 输 {x['lost_med']:7.2f} | p={x['p']:.3f}")
out["ai_won_vs_lost"] = sec2

# ---------- 三、机机局：胜者−败者 配对差（符号检验），以及「都不要」局的画像 ----------
def paired(kind_filter, label):
    res = []
    dec = [r for r in rows if kind_filter(r) and r["pick"] in "AB"]
    for k in FN:
        d = [r[r["pick"]]["f"][k] - r["B" if r["pick"] == "A" else "A"]["f"][k] for r in dec]
        pos = sum(1 for x in d if x > 0); neg = sum(1 for x in d if x < 0)
        res.append({"feat": k, "label": LABEL[k], "n": pos + neg, "winner_higher": pos, "winner_lower": neg, "p": binom2(pos, pos + neg), "median_diff": float(np.median(d)) if d else 0})
    res.sort(key=lambda x: x["p"])
    print(f"\n== {label}（决定票 {len(dec)} 局）：胜者比败者「高」的局数 : 「低」的局数 ==")
    for x in res[:12]: print(f"  {x['label']:14s} {x['winner_higher']:3d} : {x['winner_lower']:3d}  p={x['p']:.3f}  中位差 {x['median_diff']:+.2f}")
    return res
out["aa_paired"] = paired(lambda r: r["kind"] == "aa", "三、机机局（含 v1 时代）")
out["aa_paired_quiz"] = paired(lambda r: r["kind"] == "aa" and r["set"] != "v1", "三b、机机局（只算测验卷 v3–v14）")
out["hh_paired"] = paired(lambda r: r["kind"] == "hh", "四、纯人对（主人的纯口味，无机器混杂）")
out["ha_paired"] = paired(lambda r: r["kind"] == "ha", "五、真伪局（胜者−败者，多数胜者是人）")

# 都不要 vs 决定票（机机局）：两首取均值
bb = [r for r in rows if r["kind"] == "aa" and r["pick"] == "X"]; dec = [r for r in rows if r["kind"] == "aa" and r["pick"] in "AB"]
print(f"\n== 六、机机局「都不要」{len(bb)} 局 vs 决定票 {len(dec)} 局（两首均值的中位数）==")
sec6 = []
for k in FN:
    a = [(r["A"]["f"][k] + r["B"]["f"][k]) / 2 for r in bb]; b = [(r["A"]["f"][k] + r["B"]["f"][k]) / 2 for r in dec]
    sec6.append({"feat": k, "label": LABEL[k], "bothbad_med": float(np.median(a)), "decided_med": float(np.median(b)), "p": ranksum_p(a, b)})
sec6.sort(key=lambda x: x["p"])
for x in sec6[:10]: print(f"  {x['label']:14s} 都不要 {x['bothbad_med']:7.2f} | 决定票 {x['decided_med']:7.2f} | p={x['p']:.3f}")
out["bothbad_vs_decided"] = sec6

# ---------- 七、逐臂画像：各臂 AI 诗的特征中位数 + 被骂率 ----------
print("\n== 七、各臂 AI 诗的可数画像（测验卷里出场 ≥20 首的臂）==")
byarm = collections.defaultdict(list)
for r in rows:
    if r["set"] == "v1": continue
    for s in "AB":
        if r[s]["src"] == "ai": byarm[r[s]["who"]].append(r[s]["f"])
KEYS7 = ["chars", "cpl", "short_share", "cls100", "sim100", "decl100", "abs100", "you100", "rep_share", "sect", "punct100", "ttr"]
print("  臂 | n | " + " | ".join(LABEL[k] for k in KEYS7))
sec7 = {}
for arm, fs in sorted(byarm.items(), key=lambda x: -len(x[1])):
    if len(fs) < 20: continue
    med = {k: float(np.median([f[k] for f in fs])) for k in FN}; sec7[arm] = {"n": len(fs), **med}
    print(f"  {arm:10s} | {len(fs):3d} | " + " | ".join(f"{med[k]:.2f}" for k in KEYS7))
hmed = {k: float(np.median([f[k] for f in hum])) for k in FN}; sec7["human"] = {"n": len(hum), **hmed}
print(f"  {'真人':10s} | {len(hum):3d} | " + " | ".join(f"{hmed[k]:.2f}" for k in KEYS7))
out["by_arm"] = sec7

# ---------- 八、批注词根 × 臂 × 卷 ----------
KW = {"量词": ["量词"], "流水账": ["流水账"], "比喻差": ["比喻"], "幼稚/学生作文": ["幼稚", "小学生", "初中生", "儿歌", "童谣", "作文"], "垃圾/狗屎": ["垃圾", "狗屎", "屎"],
      "语言差": ["语言", "用词", "用语"], "结尾": ["结尾"], "太短太碎": ["太短", "太碎", "零碎", "碎"], "都不错/还行": ["不错", "还行", "还可以", "可以"], "AI味/机器": ["AI", "机器", "train"]}
marks_all = json.load(open(Q + "all_marks.json"))
print(f"\n== 八、批注词根（{len(marks_all)} 条）按卷 ==")
byset = collections.defaultdict(collections.Counter); byarm_kw = collections.defaultdict(collections.Counter)
for m in marks_all:
    st, i, kind, pk, text, who = m[0], m[1], m[2], m[3], m[4], m[5]
    for k, ws in KW.items():
        if any(w in text for w in ws):
            byset[st][k] += 1
            for arm in re.findall(r"AI·([A-Za-z0-9_]+)", who): byarm_kw[arm][k] += 1
sets_order = ["v5", "v6", "v7", "v8", "v9", "v10b", "v11", "v12", "v13", "v14"]
print("  词根 | " + " | ".join(sets_order))
for k in KW: print(f"  {k:10s} | " + " | ".join(str(byset[s][k]) for s in sets_order))
print("  词根 × 臂（批注提到该臂在场的局）:")
for arm, c in sorted(byarm_kw.items(), key=lambda x: -sum(x[1].values())): print(f"    {arm:10s} " + " ".join(f"{k}{v}" for k, v in c.most_common(6)))
out["marks_by_set"] = {s: dict(byset[s]) for s in sets_order}; out["marks_by_arm"] = {a: dict(c) for a, c in byarm_kw.items()}

# ---------- 九、时间线：按卷的反杀率、都不要率、M4 战绩 ----------
print("\n== 九、按卷时间线 ==")
tl = []
for name in ["v3", "v5", "v6", "v7", "v8", "v9", "v10b", "v11", "v12", "v13", "v14"]:
    rs = [r for r in rows if r["set"] == name]
    ha = [r for r in rs if r["kind"] == "ha"]; aa = [r for r in rs if r["kind"] == "aa"]
    up = sum(1 for r in ha if r["pick"] in "AB" and r[r["pick"]]["src"] == "ai"); hd = sum(1 for r in ha if r["pick"] in "AB")
    x = sum(1 for r in aa if r["pick"] == "X"); m4 = sum(1 for r in aa if r["pick"] in "AB" and r[r["pick"]]["who"] == "M4_dpo"); m4n = sum(1 for r in aa if r["pick"] in "AB" and any(r[s]["who"] == "M4_dpo" for s in "AB"))
    tl.append({"set": name, "ha_upsets": up, "ha_decided": hd, "aa_bothbad": x, "aa_total": len(aa), "m4_w": m4, "m4_n": m4n})
    print(f"  {name:5s} 真伪反杀 {up:2d}/{hd:3d}  机机都不要 {x:2d}/{len(aa):3d}  M4 胜 {m4}/{m4n}")
out["timeline"] = tl

# ---------- 十、逻辑回归：哪些可数特征跟着票走（配对差特征，留一卷交叉验证）----------
def fit_lr(X, y, l2=1.0, iters=3000, lr=0.05):
    w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(iters):
        z = X @ w + b; p = 1 / (1 + np.exp(-z)); g = p - y
        w -= lr * (X.T @ g / len(y) + l2 * w / len(y)); b -= lr * g.mean()
    return w, b
def auc(y, s):
    pos = s[y == 1]; neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float("nan")
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())
def lr_block(sel, label):
    dec = [r for r in rows if sel(r) and r["pick"] in "AB"]
    X = []; y = []; sets = []
    for r in dec:
        for a, b, lab in ((r["A"], r["B"], 1 if r["pick"] == "A" else 0),):
            X.append([a["f"][k] - b["f"][k] for k in FN]); y.append(lab); sets.append(r["set"])
        # 对称增广：交换 A/B
        X.append([r["B"]["f"][k] - r["A"]["f"][k] for k in FN]); y.append(1 - y[-1]); sets.append(r["set"])
    X = np.array(X, float); y = np.array(y, float); sets = np.array(sets)
    sd = X.std(0) + 1e-9; Xs = X / sd
    w, b = fit_lr(Xs, y)
    coef = sorted(zip(FN, w), key=lambda x: -abs(x[1]))
    # 留一卷
    aucs = {}
    for s in sorted(set(sets)):
        tr = sets != s; te = sets == s
        if te.sum() < 10 or tr.sum() < 40: continue
        w2, b2 = fit_lr(Xs[tr], y[tr]); aucs[s] = auc(y[te], Xs[te] @ w2 + b2)
    print(f"\n== 十、{label}：逻辑回归（配对差、标准化、留一卷）决定票 {len(dec)} 局 ==")
    print("  留一卷 AUC: " + ", ".join(f"{s} {v:.2f}" for s, v in aucs.items()) + f" | 平均 {np.nanmean(list(aucs.values())):.2f}")
    print("  权重最大的特征（+ = 该项越高越可能被选）: " + "; ".join(f"{LABEL[k]} {v:+.2f}" for k, v in coef[:8]))
    return {"n": len(dec), "auc_by_set": aucs, "coef": [(k, float(v)) for k, v in coef]}
out["lr_hh"] = lr_block(lambda r: r["kind"] == "hh", "纯人对")
out["lr_aa"] = lr_block(lambda r: r["kind"] == "aa", "机机局")
out["lr_ha"] = lr_block(lambda r: r["kind"] == "ha", "真伪局")
json.dump(out, open(Q + "label_history_analysis.json", "w"), ensure_ascii=False, indent=1)
print("\n→ label_history_analysis.json")
