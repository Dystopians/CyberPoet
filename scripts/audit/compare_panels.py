"""面板形状对比：quiz_v3/<ARM>_panel_gens.jsonl 若干（同 66 题×3 种子）。"""
import json,re,sys,statistics as st,collections
Q="/data/peilincai/CyberPoetTraining/claude_night_20260827/quiz_v3/"
def n(t): return len(re.sub(r"\s+","",t))
def lines(t): return [l.strip() for l in t.split("\n") if l.strip()]
DECL=["我们","你们","死亡","如果","为了","不能","孤独","痛苦","历史","永恒","太阳","诗人","头颅","大地","歌唱","上帝","肉体","多少","这么","她们"]
SIM=["像","仿佛","如同","宛如","犹如","恍若"]
for arm in sys.argv[1:]:
    rows=[json.loads(l) for l in open(Q+arm+"_panel_gens.jsonl")]
    b=[r["body"] for r in rows]
    ch=[n(x) for x in b]; ln=[len(lines(x)) for x in b]
    cpl=[n(x)/max(1,len(lines(x))) for x in b]
    sui=sum(1 for c in cpl if c<6)/len(b)
    frag=[sum(1 for l in lines(x) if n(l)<=4)/max(1,len(lines(x))) for x in b]
    punct=[len(re.findall(r"[，。；：、！？]",x))/max(1,n(x))*100 for x in b]
    ws=sum(ch); decl=sum(sum(x.count(w) for w in DECL) for x in b)/ws*1e4; sim=sum(sum(x.count(w) for w in SIM) for x in b)/ws*100
    rep=sum(1 for x in b if lines(x) and max(collections.Counter(lines(x)).values())>=2)
    print(f"{arm:14s} n={len(b)} 字数中位 {st.median(ch):4.0f} | 行数 {st.median(ln):3.0f} | 字/行 {st.median(cpl):4.1f} | 碎行率(字/行<6) {sui:5.1%} | 短行占比 {st.mean(frag):.3f} | <60字 {sum(c<60 for c in ch):3d} | 标点/百字 {st.median(punct):4.1f} | 陈述/万 {decl:5.1f} | 比喻/百 {sim:.2f} | 有重复行 {rep}")
