"""把四方对照生成排版成单文件 HTML 阅读包。"""
import json, re, html, statistics, collections
from pathlib import Path
W=Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
D=Path("/data/peilincai/CyberPoet_poetry_dataset_v0.3.0/repository/poetry_dataset/splits")
src=W/"vocab_probe/gens_epoch_sweep.jsonl"
rows=[json.loads(l) for l in open(src)]
LABEL={"pt_sft":"旧版（2轮预训练 + 旧提示词）","M1_e4":"M1 · 4轮预训练","M1_e5":"M1 · 5轮预训练","M1_e7":"M1 · 7轮预训练"}
conds=[c for c in ("pt_sft","M1_e4","M1_e5","M1_e7") if c in rows[0]]
# 原作正文（仅供对照，不进训练）
ref={}
for s in ("train","validation","test"):
    for l in open(D/f"{s}.jsonl"):
        d=json.loads(l); ref[d["id"]]=(d.get("author",""), d.get("title",""), d["text"])
def st(t):
    L=[x for x in t.strip().splitlines() if x.strip()]; h=re.sub(r"[^一-鿿]","",t)
    sim=len(re.findall(r"像|仿佛|如同|宛如|似的",t))/max(1,len(h))*100
    return len(L), len(h), sim
def esc(s): return html.escape(s)
parts=["""<title>M1 轮数对照阅读包</title>
<style>
:root{--bg:#faf9f7;--fg:#1c1a17;--card:#fff;--line:#e3ded6;--accent:#7c5c3e;--muted:#6b655c}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161513;--fg:#eae6df;--card:#1f1e1b;--line:#33302b;--accent:#c79a6c;--muted:#9a938a}}
:root[data-theme="dark"]{--bg:#161513;--fg:#eae6df;--card:#1f1e1b;--line:#33302b;--accent:#c79a6c;--muted:#9a938a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.8 "Noto Serif CJK SC","Songti SC",Georgia,serif}
header{border-bottom:1px solid var(--line);padding:22px 20px;background:var(--card)}
h1{margin:0 0 6px;font-size:21px}
main{max-width:1500px;margin:0 auto;padding:20px}
.note{color:var(--muted);font-size:14px;line-height:1.7}
table.sum{border-collapse:collapse;margin:14px 0;font-size:14px}
table.sum th,table.sum td{border:1px solid var(--line);padding:6px 12px;text-align:right}
table.sum th:first-child,table.sum td:first-child{text-align:left}
.q{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
padding:12px 16px;margin:26px 0 14px;font-size:15px}
.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}
.poem{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:16px 18px;overflow-x:auto}
.poem h3{margin:0 0 4px;font-size:12px;letter-spacing:.08em;color:var(--accent);font-weight:700}
.poem .m{font-size:12px;color:var(--muted);margin-bottom:10px}
.poem pre{margin:0;font:inherit;white-space:pre-wrap}
.ref{border-left:3px solid var(--muted);margin-top:14px}
.ref h3{color:var(--muted)}
</style>
<header>
<h1>M1 轮数对照阅读包</h1>
<div class="note">12 道题 × 同一随机种子（20260827）× 同一套采样参数。四档的差别只有<b>预训练轮数</b>与<b>系统提示词</b>；
训练数据完全相同。旧版用旧提示词，三档 M1 用精简版 v2 提示词——各自用自己训练时的措辞。<br>
诗题命题的六道题末尾附了<b>语料原作</b>，仅供你对照阅读，不进任何训练数据。</div>
</header><main>"""]
parts.append('<table class="sum"><tr><th>条件</th><th>中位行数</th><th>中位字数</th><th>比喻/百字</th></tr>')
for c in conds:
    s=[st(r[c]) for r in rows]
    parts.append(f"<tr><td>{esc(LABEL[c])}</td><td>{statistics.median(x[0] for x in s):.0f}</td>"
                 f"<td>{statistics.median(x[1] for x in s):.0f}</td><td>{statistics.median(x[2] for x in s):.2f}</td></tr>")
parts.append('<tr><td>真实诗人（参照）</td><td>16</td><td>—</td><td>0.28</td></tr></table>')
for i,r in enumerate(rows,1):
    parts.append(f'<div class="q"><b>{i}. </b>{esc(r["prompt"])}</div><div class="row">')
    for c in conds:
        L,C,S=st(r[c])
        parts.append(f'<div class="poem"><h3>{esc(LABEL[c])}</h3><div class="m">{L} 行 · {C} 字 · 比喻 {S:.2f}/百字</div>'
                     f'<pre>{esc(r[c].strip())}</pre></div>')
    parts.append('</div>')
    rid=r.get("ref_id")
    if rid and rid in ref:
        a,t,txt=ref[rid]
        parts.append(f'<div class="row"><div class="poem ref" style="grid-column:1/-1">'
                     f'<h3>语料原作（仅供对照，不进训练）</h3><div class="m">{esc(a)}《{esc(t)}》</div>'
                     f'<pre>{esc(txt.strip())}</pre></div></div>')
parts.append("</main>")
out=W/"vocab_probe/阅读包_M1轮数对照.html"
out.write_text("\n".join(parts), encoding="utf-8")
print("写出", out, out.stat().st_size, "字节")
