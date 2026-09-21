"""M8 出厂检数字（CPU）：任意生成 jsonl（每行含 body，可含 arm/rp/seed）逐文件逐 rp 报形状与复读。
口径与归因报告附录 E/F/G 相同：循环 = 同一行出现 ≥3 次；严口径 = 重复行占全部行 ≥50%；碎行 = 字/行 <6；撞顶 = ≥555 token。
只报数，不做门（出卷门槛只有一条：198 首面板、rp=1.08、循环 >5% 不出卷）。
用法: python3 m8_metrics.py a.jsonl [b.jsonl ...]"""
import json, re, sys, statistics as st, collections
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained('/data/peilincai/CyberPoetTraining/cyberpoet_v1/models/Qwen3-14B', trust_remote_code=True)
n = lambda t: len(re.sub(r"\s+", "", t))
lines = lambda t: [l.strip() for l in t.split("\n") if l.strip()]
DECL = ["我们","你们","死亡","如果","为了","不能","孤独","痛苦","历史","永恒","太阳","诗人","头颅","大地","歌唱","上帝","肉体","多少","这么","她们"]
SIM = ["像","仿佛","如同","宛如","犹如","恍若"]
def wilson(k, m, z=1.96):
    if m == 0: return (0, 0)
    p = k / m; d = 1 + z*z/m; c = p + z*z/(2*m); h = z*((p*(1-p)/m + z*z/(4*m*m))**0.5)
    return ((c-h)/d, (c+h)/d)
for f in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    groups = collections.defaultdict(list)
    for r in rows: groups[(r.get("arm", "?"), r.get("rp", "?"))].append(r["body"])
    for (arm, rp), b in sorted(groups.items(), key=str):
        ch = [n(x) for x in b]; ln = [len(lines(x)) for x in b]; cpl = [n(x)/max(1, len(lines(x))) for x in b]
        loop = sum(1 for x in b if lines(x) and max(collections.Counter(lines(x)).values()) >= 3)
        strict = 0
        for x in b:
            L = lines(x); c = collections.Counter(L)
            if L and sum(v for v in c.values() if v >= 2) / len(L) >= 0.5: strict += 1
        rep = sum(1 for x in b if lines(x) and max(collections.Counter(lines(x)).values()) >= 2)
        cap = sum(1 for x in b if len(tok(x, add_special_tokens=False)["input_ids"]) >= 555)
        punct = [len(re.findall(r"[，。；：、！？]", x))/max(1, n(x))*100 for x in b]
        ws = max(1, sum(ch)); decl = sum(sum(x.count(w) for w in DECL) for x in b)/ws*1e4; sim = sum(sum(x.count(w) for w in SIM) for x in b)/ws*100
        lo, hi = wilson(loop, len(b))
        print(f"{f.split('/')[-1]} | {arm} rp={rp} n={len(b)} | 字数中位 {st.median(ch):.0f}（四分位 {st.quantiles(ch, n=4)[0]:.0f}–{st.quantiles(ch, n=4)[2]:.0f}）| 行数 {st.median(ln):.0f} | 字/行 {st.median(cpl):.1f} | 碎行率 {sum(c < 6 for c in cpl)/len(b):.1%} | <60字 {sum(c < 60 for c in ch)} | 循环 {loop}（{loop/len(b):.1%}，区间 {lo:.0%}–{hi:.0%}）| 严口径 {strict} | 有重复行 {rep} | 撞顶 {cap}（{cap/len(b):.1%}）| 标点/百字 {st.median(punct):.1f} | 陈述/万 {decl:.1f} | 比喻/百 {sim:.2f}")
