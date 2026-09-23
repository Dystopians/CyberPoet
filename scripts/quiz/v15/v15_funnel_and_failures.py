# v15 交付附件（09-22，Codex 评审 C1/C9 + 主人 09-21 「别让我在测验里替你数病」）：
# ① 完整漏斗：每臂 原始候选 → 硬门控（逐条拒因）→ 盲读否决 → 上卷；② 出厂面板与候选的可数体检（循环/字数/短诗/撞顶 + 文本模式占比）；
# ③ 每臂最常见三类失败的原文短摘（≤2 行，标明 AI 生成，只摘不评）。输出 v15_交付附件_漏斗与失败.md。用法：候选齐、门控与装配跑完后执行。
import json, re, collections, os, sys
sys.path.insert(0, '.')
from v15_arms import ARMS
from gate_v15 import clean, gate
CLS = re.compile(r"一[个只条种片段座张把颗根块道场阵抹缕丝声句行首朵棵株团粒滴层枚扇面册幅盏束簇]")
GAN = ["文明", "辉煌", "史诗", "丝绸之路", "阶级", "伟大", "中华", "民族", "真理", "意志"]
JT = ["生活就是", "人生", "勇敢", "美好", "每个人都", "不可或缺", "珍惜", "希望和"]
def lines(t): return [l.strip() for l in t.split("\n") if l.strip()]
def z(t): return re.sub(r"\s+", "", t)
def classes(b):
    L = lines(b); s = z(b); n = max(1, len(s)); out = {}
    out["童谣词"] = (len(re.findall(r"[啊呀哩]|多么|真[好美]", s)) + s.count("！")) / n * 100 >= 0.6
    out["顺序记事"] = len(re.findall(r"然后|于是|接着|后来", s)) >= 2
    out["说理/鸡汤"] = len(re.findall(r"因为|所以|意味着|就是|真理|生活就是", s)) >= 2 or any(w in (L[-1] if L else "") for w in JT)
    out["量词串"] = len(CLS.findall(s)) / n * 100 >= 2.0
    out["宏大词"] = any(w in s for w in GAN)
    out["整行循环"] = bool(L) and max(collections.Counter(L).values()) >= 3
    return out
def excerpt(b, cls):
    L = lines(b)
    if cls == "整行循环":
        c = collections.Counter(L); line = c.most_common(1)[0][0]; return f"「{line[:20]}」×{c[line]}"
    if cls == "量词串":
        for i in range(len(L)):
            seg = "/".join(L[i:i+2])
            if len(CLS.findall(seg)) >= 3: return seg[:44]
        # 没有 2 行 ≥3 的窗口时，取「一+量词」最密的那一行（原先回落到首行，摘出来的是分节号「1」）
        best = max(L, key=lambda l: len(CLS.findall(l)), default="")
        return best[:44]
    if cls == "宏大词":
        for l in L:
            if any(w in l for w in GAN): return l[:30]
    if cls == "童谣词":
        for l in L:
            if re.search(r"[啊呀哩]|多么|真[好美]|！", l): return l[:30]
    if cls == "顺序记事":
        for i, l in enumerate(L):
            if re.search(r"然后|于是|接着|后来", l): return "/".join(L[max(0, i-1):i+1])[:44]
    if cls == "说理/鸡汤":
        for l in reversed(L):
            if re.search(r"因为|所以|意味着|就是|真理|生活就是", l) or any(w in l for w in JT): return l[:30]
    return (L[0] if L else "")[:30]
gated = json.load(open('v15_gen_gated.json')) if os.path.exists('v15_gen_gated.json') else {}
final = json.load(open('v15_pairs_final.json')) if os.path.exists('v15_pairs_final.json') else []
rv = json.load(open('v15_read_verdicts.json')) if os.path.exists('v15_read_verdicts.json') else {"veto": []}
veto = collections.Counter(v[1] for v in rv.get("veto", []))
onq = collections.Counter(p[s]["model"].replace("_dpo", "") for p in final for s in "AB" if p[s]["src"] == "ai")
out = ["# v15 交付附件：候选漏斗与失败短摘（09-22）", "", "只数不评；短摘全是 AI 生成，人诗一字不引。", ""]
out += ["## 一、漏斗（每臂）", "", "| 臂 | 原始候选 | 过硬门控 | 门控拒因（前三） | 盲读否决 | 上卷 |", "|---|---|---|---|---|---|"]
stats = {}
for arm in ARMS:
    f = f"v15_cands_{arm}.jsonl"
    if not os.path.exists(f): continue
    rows = [json.loads(l) for l in open(f, encoding="utf-8")]
    why = collections.Counter(); passed = 0; cl = collections.Counter(); ex = collections.defaultdict(list)
    for r in rows:
        b = clean(r["body"], r["title"]); w = gate(r["title"], b)
        if w: why[re.sub(r"\d+", "", w)] += 1
        else: passed += 1
        for k, v in classes(b).items():
            if v:
                cl[k] += 1
                if len(ex[k]) < 3: ex[k].append(excerpt(b, k))
    stats[arm] = (rows, cl, ex)
    top = "、".join(f"{k} {v}" for k, v in why.most_common(3))
    out.append(f"| {arm} | {len(rows)} | {passed} | {top} | {veto.get(arm, 0)} | {onq.get(arm, 0)} |")
out += ["", "## 二、候选池的可数体检（占比 = 命中该模式的候选 / 原始候选；同一首可命中多类）", "", "| 臂 | " + " | ".join(["童谣词", "顺序记事", "说理/鸡汤", "量词串", "宏大词", "整行循环"]) + " |", "|---|" + "---|" * 6]
for arm, (rows, cl, ex) in stats.items():
    out.append(f"| {arm} | " + " | ".join(f"{cl[k]/max(1,len(rows)):.0%}" for k in ["童谣词", "顺序记事", "说理/鸡汤", "量词串", "宏大词", "整行循环"]) + " |")
out += ["", "语料抽样与桥数据在这六项上的占比见 标记总报告 十一（童谣词 15%、顺序记事 3%、说理 8%、量词串 16%、宏大词 7%）。", ""]
out += ["## 三、每臂最常见三类失败的原文短摘（AI 生成；每类 3 例，≤2 行）", ""]
for arm, (rows, cl, ex) in stats.items():
    out.append(f"### {arm}")
    for k, v in cl.most_common(3):
        out.append(f"- **{k}**（{v}/{len(rows)}）：" + "；".join(f"「{e}」" for e in ex[k]))
    out.append("")
open('v15_交付附件_漏斗与失败.md', 'w', encoding='utf-8').write("\n".join(out))
print("\n".join(out[:14])); print("→ v15_交付附件_漏斗与失败.md")
