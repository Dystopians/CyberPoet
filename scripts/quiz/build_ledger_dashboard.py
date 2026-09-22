# 总表看板（09-21，主人：「总表直观展示给我」）：把 arm_ledger_v5_v11.json、merged_labels_stats.json、label_history_analysis.json
# 画成一页 HTML（无外部库，内联 SVG/CSS；不含任何诗句正文）。输出 主人标记总表_20260921.html
import json, math, html
Q = "/data/peilincai/CyberPoetTraining/claude_night_20260827/quiz_v3/"
L = json.load(open(Q + "arm_ledger_v5_v11.json")); S = json.load(open(Q + "merged_labels_stats.json")); A = json.load(open(Q + "label_history_analysis.json"))
def binom2(k, n):
    if n == 0: return 1.0
    logC = lambda n, k: sum(math.log(n-k+i)-math.log(i) for i in range(1, k+1))
    pk = lambda j: math.exp(logC(n, j) + n*math.log(0.5)); obs = pk(k)
    return min(1.0, sum(pk(j) for j in range(n+1) if pk(j) <= obs+1e-12))
RECIPE = {"M4_dpo": "pt6 语料 + 旧偏好数据（现役）", "M3_dpo": "修复语料 pt5", "M6b_dpo": "pt8 语料 LoRA + 旧偏好数据", "M6_dpo": "pt8 语料 + 真人金标偏好数据",
          "dpo_full": "早期全参 DPO", "M2_dpo": "损坏语料 pt3", "M5_dpo": "M4 桥 + 真人金标偏好数据", "M5F_dpo": "坏配置全参（作废）", "M7F_dpo": "修正版全参 + 旧偏好数据"}
NAME = lambda m: m.replace("_dpo", "")
def bar(pct, color, w=160, h=12, text=""):
    pct = max(0, min(100, pct))
    return f'<span class="bar" style="width:{w}px"><span style="width:{pct:.0f}%;background:{color}"></span></span><span class="bt">{html.escape(text)}</span>'
def pstr(p): return ("<b>" + ("<0.001" if p < 0.001 else f"{p:.3f}") + "</b>") if p < 0.05 else ("<0.001" if p < 0.001 else f"{p:.3f}")
# ---- 1 臂级 ----
arms = sorted(L["arm_aa"].items(), key=lambda x: -x[1][0] / max(1, x[1][1]))
rows1 = ""
for m, (w, n) in arms:
    hw, hn = L["arm_ha"].get(m, [0, 0]); r = w / max(1, n); hr = hw / max(1, hn); p = binom2(w, n)
    rows1 += f"<tr><td><b>{NAME(m)}</b><div class='sub'>{RECIPE.get(m, '')}</div></td><td>{bar(r*100, 'var(--c1)', text=f'{w}/{n} = {r:.0%}')}</td><td>{pstr(p)}</td><td>{bar(hr*100, 'var(--c2)', text=f'{hw}/{hn} = {hr:.0%}')}</td><td>{L['ha_both_bad'].get(m, 0)}</td></tr>"
# ---- 2 逐对 ----
rows2 = ""
for k, (w, n) in sorted(L["pair"].items(), key=lambda x: -x[1][1]):
    a, b = k.split("|"); bb = L["both_bad"].get(k, 0); p = binom2(w, n)
    lead = NAME(a) if w >= n - w else NAME(b); lw = max(w, n - w); ll = min(w, n - w)
    rows2 += f"<tr><td>{NAME(a)} 对 {NAME(b)}</td><td>{bar(lw/max(1,n)*100, 'var(--c1)', text=f'{lead} {lw} : {ll}')}</td><td>{pstr(p)}</td><td>{bar(bb/max(1,n+bb)*100, 'var(--c3)', text=f'{bb}（{bb/max(1,n+bb):.0%}）')}</td></tr>"
# ---- 3 时间线 SVG ----
tl = A["timeline"]; W, H, ml, mb = 640, 220, 40, 30
def svg_line(vals, color, label):
    pts = []
    for i, v in enumerate(vals):
        x = ml + i * (W - ml - 10) / (len(vals) - 1); y = H - mb - (v or 0) * (H - mb - 20)
        pts.append((x, y))
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"/><text x="{x:.1f}" y="{y-7:.1f}" text-anchor="middle" font-size="10" fill="{color}">{vals[i]*100:.0f}%</text>' for i, (x, y) in enumerate(pts))
    return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>{dots}'
up = [t["ha_upsets"] / max(1, t["ha_decided"]) for t in tl]; bbr = [t["aa_bothbad"] / max(1, t["aa_total"]) for t in tl]
m4 = [t["m4_w"] / t["m4_n"] if t["m4_n"] else None for t in tl]
xs = "".join(f'<text x="{ml + i*(W-ml-10)/(len(tl)-1):.1f}" y="{H-8}" text-anchor="middle" font-size="11" fill="var(--fg2)">{t["set"]}</text>' for i, t in enumerate(tl))
grid = "".join(f'<line x1="{ml}" x2="{W-10}" y1="{H-mb-g*(H-mb-20):.1f}" y2="{H-mb-g*(H-mb-20):.1f}" stroke="var(--line)" stroke-width="1"/><text x="{ml-4}" y="{H-mb-g*(H-mb-20)+4:.1f}" text-anchor="end" font-size="10" fill="var(--fg2)">{g*100:.0f}%</text>' for g in (0, .25, .5, .75, 1))
m4pts = [(i, v) for i, v in enumerate(m4) if v is not None]
m4path = " ".join(f"{'M' if j == 0 else 'L'}{ml + i*(W-ml-10)/(len(tl)-1):.1f},{H-mb-v*(H-mb-20):.1f}" for j, (i, v) in enumerate(m4pts))
m4dots = "".join(f'<circle cx="{ml + i*(W-ml-10)/(len(tl)-1):.1f}" cy="{H-mb-v*(H-mb-20):.1f}" r="3.5" fill="var(--c1)"/>' for i, v in m4pts)
svg3 = f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px">{grid}{xs}{svg_line(up, "var(--c2)", "反杀")}{svg_line(bbr, "var(--c3)", "都不要")}<path d="{m4path}" fill="none" stroke="var(--c1)" stroke-width="2" stroke-dasharray="5,4"/>{m4dots}</svg>'
# ---- 4 十维 ----
DIMS = [("device", "有装置", "无装置"), ("linelen", "长句行", "短句行"), ("punct", "满标点", "无标点"), ("density", "密", "疏"), ("ending", "悬置", "落地"),
        ("simile", "有喻", "无喻"), ("register", "口语", "书面"), ("abstract", "抽象", "具象"), ("person", "有你", "无你"), ("heat", "热", "冷")]
rows4 = ""
for k, l, r in DIMS:
    h = S["dim_h"].get(k, [0, 0]); m = S["dim_m"].get(k, [0, 0])
    def cell(v):
        a, b = v[0], v[1]; n = a + b; p = binom2(a, n) if n else 1
        lead = l if a >= b else r
        return f"<td>{bar(max(a,b)/max(1,n)*100, 'var(--c1)' if p < 0.05 else 'var(--c4)', text=f'{lead} {max(a,b)} : {min(a,b)}')}</td><td>{pstr(p)}</td>"
    rows4 += f"<tr><td>{l} / {r}</td>{cell(h)}{cell(m)}</tr>"
# ---- 5 诗人 ----
rows5 = ""
poets = [(p, v) for p, v in S["poet_hh"].items() if v[1] >= 8]
for p, (w, n) in sorted(poets, key=lambda x: -(x[1][0] / x[1][1])):
    pv = binom2(w, n); ha = S["poet_ha"].get(p, [0, 0])
    rows5 += f"<tr><td>{p}</td><td>{bar(w/n*100, 'var(--c1)' if pv < 0.05 else 'var(--c4)', text=f'{w}/{n} = {w/n:.0%}')}</td><td>{pstr(pv)}</td><td>{ha[0]}/{ha[1]}</td></tr>"
# ---- 6 深度分析 ----
def top(sec, key_a, key_b, la, lb, n=8, fmt="{:.2f}"):
    out = ""
    for x in sec[:n]:
        out += f"<tr><td>{x['label']}</td><td>{fmt.format(x[key_a])}</td><td>{fmt.format(x[key_b])}</td><td>{pstr(x['p'])}</td></tr>"
    return f"<table><tr><th>可数特征</th><th>{la}</th><th>{lb}</th><th>p</th></tr>{out}</table>"
def paired_tbl(sec, n=8):
    out = ""
    for x in sec[:n]:
        txt = str(x['winner_higher']) + " : " + str(x['winner_lower'])
        out += "<tr><td>" + x['label'] + "</td><td>" + bar(x['winner_higher']/max(1,x['n'])*100, 'var(--c1)' if x['p']<0.05 else 'var(--c4)', text=txt) + "</td><td>" + pstr(x['p']) + "</td></tr>"
    return f"<table><tr><th>可数特征</th><th>胜者更高 : 胜者更低（局数）</th><th>p</th></tr>{out}</table>"
arm_rows = ""
for arm, d in sorted(A["by_arm"].items(), key=lambda x: -x[1]["cls100"]):
    nm = '真人' if arm == 'human' else NAME(arm); b = bar(d['cls100']/2.5*100, 'var(--c3)' if arm != 'human' else 'var(--c2)', text="%.2f" % d['cls100'])
    arm_rows += "<tr><td>%s</td><td>%d</td><td>%s</td><td>%.1f</td><td>%.1f</td><td>%.2f</td><td>%.0f</td></tr>" % (nm, d['n'], b, d['cpl'], d['punct100'], d['ttr'], d['chars'])
lr = A["lr_ha"]; lr2 = A["lr_hh"]; lr3 = A["lr_aa"]
LABEL = {"chars": "字数", "lines": "行数", "cpl": "字/行", "stanzas": "节数", "maxline": "最长行字数", "short_share": "短行占比", "punct100": "标点/百字",
         "qmark": "问号数", "excl": "叹号数", "ellipsis": "省略号数", "dash": "破折号数", "cls100": "「一+量词」/百字", "sim100": "比喻词/百字", "decl100": "陈述大词/百字",
         "abs100": "抽象名词/百字", "you100": "「你」/百字", "i100": "「我」/百字", "de100": "「的」/百字", "rep_max": "同一行最多重复次数", "rep_share": "重复行占比",
         "title_echo": "含题目的行数", "sect": "有分节标号", "last_len": "末行字数", "last_q": "末行问号收尾", "last_abs": "末行含抽象名词", "last_period": "末行句号收尾",
         "ttr": "用字丰富度", "latin": "拉丁字母数", "first_len": "首行字数"}
def coefs(d): return "；".join(f"{LABEL.get(k, k)} {w:+.2f}" for k, w in d["coef"][:6])
def aucs(d): return "、".join(f"{s} {v:.2f}" for s, v in d["auc_by_set"].items())
page = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>主人标记总表</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1f1d1a;--fg2:#6b6660;--line:#e6e1d8;--card:#ffffff;--c1:#2f6f8f;--c2:#3f8f5f;--c3:#b8503a;--c4:#a9a39a}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#15161a;--fg:#ece8e1;--fg2:#a29c93;--line:#2c2e35;--card:#1d1f25;--c1:#6fb0d6;--c2:#7cc99a;--c3:#e08a74;--c4:#6d6862}}}}
:root[data-theme=dark]{{--bg:#15161a;--fg:#ece8e1;--fg2:#a29c93;--line:#2c2e35;--card:#1d1f25;--c1:#6fb0d6;--c2:#7cc99a;--c3:#e08a74;--c4:#6d6862}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;max-width:1100px;margin:0 auto}}
h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:28px 0 8px;border-left:4px solid var(--c1);padding-left:10px}} .lead{{color:var(--fg2);margin:0 0 8px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:middle}} th{{color:var(--fg2);font-weight:500}}
.bar{{display:inline-block;height:12px;background:var(--line);border-radius:3px;overflow:hidden;vertical-align:middle;margin-right:8px}} .bar>span{{display:block;height:100%}} .bt{{white-space:nowrap}}
.sub{{color:var(--fg2);font-size:12px}} .kp{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}} .kp .card{{margin:0}} .big{{font-size:26px;font-weight:600}}
.leg span{{display:inline-block;margin-right:14px}} .leg i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
.note{{color:var(--fg2);font-size:13px}} @media (max-width:600px){{td,th{{padding:5px 4px}} .bar{{width:90px!important}}}}
</style></head><body>
<h1>主人标记总表</h1><p class="lead">2026-09-21 全量重编 · 十六场战役 · 1,420 对次 · 214 条批注 · 只数可数的东西，没有任何模型打分。判决只认票。</p>
<div class="kp">
<div class="card"><div class="sub">现役 M4 · AI 对 AI</div><div class="big">83 / 124 = 67%</div><div class="sub">p &lt; 0.001，五卷稳定过半</div></div>
<div class="card"><div class="sub">现役 M4 · 反杀真人</div><div class="big">14 / 69 = 20%</div><div class="sub">唯一能反杀的臂</div></div>
<div class="card"><div class="sub">机机局「都不要」</div><div class="big">25% → 55% → 52%</div><div class="sub">v9 → v10b → v11，三代共同病根：偏好训练参考模型接错</div></div>
<div class="card"><div class="sub">第 11 卷</div><div class="big">M7F 0 : 10</div><div class="sub">修正版全参对现役，判负</div></div>
</div>

<h2>一、臂级累计（v5–v11，全部机机局 + 真伪局）</h2>
<div class="card"><table><tr><th>臂</th><th>AI 对 AI 胜 / 场</th><th>p</th><th>真伪题反杀 / 场</th><th>真伪题里连真人一起「都不要」</th></tr>{rows1}</table>
<p class="note">p = 对 50% 的精确二项检验（双侧）。M6b 的 56% 是被 M7F 抬上去的（对 M4 仍 8 : 13）。</p></div>

<h2>二、逐对战绩</h2>
<div class="card"><table><tr><th>对局</th><th>领先方 胜 : 负（决定票）</th><th>p</th><th>都不要（占该对局）</th></tr>{rows2}</table></div>

<h2>三、按卷时间线</h2>
<div class="card"><div class="leg"><span><i style="background:var(--c2)"></i>AI 反杀真人的比例（真伪题决定票）</span><span><i style="background:var(--c3)"></i>机机局「都不要」比例</span><span><i style="background:var(--c1)"></i>M4 在机机决定票里的胜率（虚线）</span></div>{svg3}
<p class="note">反杀率自 v6 起稳定在 5–16%，没有上升趋势；「都不要」从 v9 起翻到 25–55%——从 v9 起上卷的新臂（M5/M6/M6b/M7F）全是「旧偏好数据套新底座」，参考模型接错把诗拽短拽碎。</p></div>

<h2>四、口味十维（九卷合并，两口径）</h2>
<div class="card"><table><tr><th>维度</th><th>纯人对</th><th>p</th><th>含机对</th><th>p</th></tr>{rows4}</table>
<p class="note">深色 = 显著（p&lt;0.05）。「无装置」四卷连显但只在含机口径——罚的是机器的机械复沓，不是特征本身；「有你」同理。纯人对里十维全平：这十维量不到主人在真人之间怎么选。</p></div>

<h2>五、诗人（对真人口径，出场 ≥ 8）</h2>
<div class="card"><table><tr><th>诗人</th><th>对真人 胜 / 场</th><th>p</th><th>人侧对 AI 胜 / 场</th></tr>{rows5}</table>
<p class="note">显著的只有陈舸、昌耀、杨炼（正向）和韩东（负向）。杨炼是 v11 单卷 8/8 抬起来的，待跨卷复验。权重面板（README）不动，改表权在主人。</p></div>

<h2>六、从 1,078 局原始票里数出来的东西（09-21 新分析）</h2>
<div class="card"><h3 style="margin:4px 0 6px;font-size:16px">6.1 机器味的可数指纹：真人诗 280 首 对 AI 诗 280 首（真伪局）</h3>
{top(A["human_vs_ai"], "human_med", "ai_med", "真人（中位）", "AI（中位）", n=10)}
<p class="note">最硬的一条：「一 + 量词」（一个/一只/一片/一种……）真人每百字 0.69 个，AI 1.80 个，p = 10⁻¹⁹——主人批注里骂的「量词泛滥、一什么一什么」，数出来正是这个。其余：AI 分节多（3 对 1）、「我」多一倍、用字更贫、标点更密、行更短。这些都不在旧的十维里。</p></div>

<div class="card"><h3 style="margin:4px 0 6px;font-size:16px">6.2 各臂的机器味（中位数）</h3>
<table><tr><th>臂</th><th>首数</th><th>「一+量词」/百字（真人 0.69）</th><th>字/行</th><th>标点/百字</th><th>用字丰富度</th><th>字数</th></tr>{arm_rows}</table>
<p class="note">M7F 的量词密度是全部臂里最高的（2.26，真人的 3.3 倍）——出卷前若有这一项，不用等票就能预警。</p></div>

<div class="card"><h3 style="margin:4px 0 6px;font-size:16px">6.3 主人的纯口味：纯人对 345 局，胜者与败者比什么</h3>
{paired_tbl(A["hh_paired"], 10)}
<p class="note">在真人与真人之间，主人选的是：每行更长、首行更长、最长的一行更长、用字更丰富、短行更少、「的」更少、行数更少、末行句号收尾。这是没有机器混杂的口味，样本 345 局。</p></div>

<div class="card"><h3 style="margin:4px 0 6px;font-size:16px">6.4 机机局 378 局：赢的那首比输的那首</h3>
{paired_tbl(A["aa_paired"], 8)}
<p class="note">末行更长、节数更少、抽象名词更少、每行更长、比喻词更少。注意「抽象名词」：真人用得比 AI 多且照样赢（6.1），AI 之间谁用得多谁输——和「装置」一样是人机反转：同一特征在真人手里是本事，在机器手里是套话。</p></div>

<div class="card"><h3 style="margin:4px 0 6px;font-size:16px">6.5 「都不要」的 74 局长什么样（机机局，两首均值）</h3>
{top(A["bothbad_vs_decided"], "bothbad_med", "decided_med", "都不要（中位）", "有决定票（中位）", n=8)}
<p class="note">两首都被否的局：标点更密、用字更贫、破折号和叹号更多、重复行更多、回显题目——全是机器味最重的那一档。</p></div>

<div class="card"><h3 style="margin:4px 0 6px;font-size:16px">6.6 可数特征能解释多少票？（逻辑回归，配对差，留一卷交叉验证）</h3>
<table><tr><th>局型</th><th>决定票</th><th>留一卷 AUC（0.5 = 瞎猜）</th><th>权重最大的特征</th></tr>
<tr><td>真伪局（人 对 AI）</td><td>{lr['n']}</td><td>平均 <b>{sum(lr['auc_by_set'].values())/len(lr['auc_by_set']):.2f}</b><div class="sub">{aucs(lr)}</div></td><td>{coefs(lr)}</td></tr>
<tr><td>纯人对</td><td>{lr2['n']}</td><td>平均 <b>{sum(lr2['auc_by_set'].values())/len(lr2['auc_by_set']):.2f}</b><div class="sub">{aucs(lr2)}</div></td><td>{coefs(lr2)}</td></tr>
<tr><td>机机局</td><td>{lr3['n']}</td><td>平均 <b>{sum(lr3['auc_by_set'].values())/len(lr3['auc_by_set']):.2f}</b><div class="sub">{aucs(lr3)}</div></td><td>{coefs(lr3)}</td></tr></table>
<p class="note">读法：可数特征分辨「人还是机器」有七成把握（0.74），分辨「主人在两首 AI 之间选哪首」几乎没把握（0.56，且各卷忽高忽低）。所以：机器味（量词、碎行、复读、标点密）是必须去掉的门槛，去掉之后主人在 AI 之间怎么选，靠可数的东西预测不了——这正是「可数指标只排序不做门、文学判断权 100% 在人」这条规矩的数据依据。</p></div>

<h2>七、批注词根（214 条）</h2>
<div class="card"><table><tr><th>词根</th>{"".join(f"<th>{s}</th>" for s in ["v5","v6","v7","v8","v9","v10b","v11"])}</tr>
{"".join(f"<tr><td>{k}</td>" + "".join(f"<td>{A['marks_by_set'][s].get(k,0)}</td>" for s in ["v5","v6","v7","v8","v9","v10b","v11"]) + "</tr>" for k in ["量词","流水账","比喻差","幼稚/学生作文","垃圾/狗屎","语言差","结尾","太短太碎","都不错/还行","AI味/机器"])}</table>
<p class="note">「垃圾/狗屎」从 v9 的 9 条到 v11 的 14 条；「都不错/还行」在 v10b 最多（18）——那一卷 AI 胜真人却因太短太碎被弃的现象也最明显。</p></div>
<p class="note" style="margin-top:24px">数据文件：quiz_v3/arm_ledger_v5_v11.json · merged_labels_stats.json · label_history_analysis.json；脚本：arm_ledger.py · merge_all_labels.py · label_history_analysis.py · build_ledger_dashboard.py。文字版：cyberpoet_repo/docs/卷宗/标记总报告_20260921.md。</p>
</body></html>"""
open(Q + "主人标记总表_20260921.html", "w", encoding="utf-8").write(page)
print("写出 主人标记总表_20260921.html", len(page), "bytes")
