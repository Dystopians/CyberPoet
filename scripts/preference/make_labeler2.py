"""生成一个单文件网页：左右并排读两首诗，按键选哪首更好，标注存在浏览器里，随时导出。
诗的来源在标注时不可见，导出后才对得上号。"""
import json
from pathlib import Path
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference")
pairs = json.load(open(W / "pairs2.json"))
# 网页里不暴露模型名，只留 gen_id
safe = [{"i": i, "prompt": p["prompt"], "pk": p["prompt_key"],
         "A": {"id": p["A"]["gen_id"], "body": p["A"]["body"]},
         "B": {"id": p["B"]["gen_id"], "body": p["B"]["body"]}} for i, p in enumerate(pairs)]

html = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>诗歌偏好标注</title><style>
:root{--bg:#faf9f7;--fg:#1c1a17;--card:#fff;--line:#e3ded6;--accent:#7c5c3e;--muted:#6b655c}
@media(prefers-color-scheme:dark){:root{--bg:#16151300;--bg:#161513;--fg:#eae6df;--card:#1f1e1b;--line:#33302b;--accent:#c79a6c;--muted:#9a938a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.75 "Noto Serif CJK SC","Songti SC",Georgia,serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 20px;z-index:9}
.bar{height:4px;background:var(--line);border-radius:2px;margin-top:8px}
.bar div{height:100%;background:var(--accent);border-radius:2px;transition:width .2s}
main{max-width:1100px;margin:0 auto;padding:20px}
.prompt{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
padding:12px 16px;margin-bottom:18px;font-size:15px;color:var(--muted)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:760px){.row{grid-template-columns:1fr}}
.poem{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:18px 20px;cursor:pointer}
.poem:hover{border-color:var(--accent)}
.poem h3{margin:0 0 10px;font-size:13px;letter-spacing:.1em;color:var(--muted);font-weight:600}
.poem pre{margin:0;font:inherit;white-space:pre-wrap}
.keys{margin-top:18px;color:var(--muted);font-size:14px;text-align:center}
button{font:inherit;padding:7px 14px;border:1px solid var(--line);background:var(--card);
color:var(--fg);border-radius:5px;cursor:pointer;margin-left:8px}
button:hover{border-color:var(--accent)}
.done{text-align:center;padding:60px 20px}
</style></head><body>
<header><b>诗歌偏好标注 · 第二批</b>　<span id="n"></span>
<button onclick="undo()">撤销 ↑</button><button onclick="exp()">导出标注</button>
<div class="bar"><div id="p" style="width:0"></div></div></header>
<main id="m"></main>
<script>
const PAIRS = __PAIRS__;
const KEY = "cyberpoet_prefs_v2";
let labels = JSON.parse(localStorage.getItem(KEY) || "{}");
function idx(){ for(let i=0;i<PAIRS.length;i++) if(!(i in labels)) return i; return -1; }
function save(){ try{ localStorage.setItem(KEY, JSON.stringify(labels)); }catch(e){} }
function pick(v){ const i=idx(); if(i<0) return; labels[i]={choice:v,at:Date.now()}; save(); render(); }
function undo(){ const done=Object.keys(labels).map(Number).sort((a,b)=>a-b); if(!done.length) return;
  delete labels[done[done.length-1]]; save(); render(); }
function exp(){ const out=Object.entries(labels).map(([i,v])=>({
    prompt_key:PAIRS[i].pk, A:PAIRS[i].A.id, B:PAIRS[i].B.id, choice:v.choice}));
  const b=new Blob([JSON.stringify(out,null,1)],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(b);
  a.download="preference_labels.json"; a.click(); }
function render(){
  const i=idx(), n=Object.keys(labels).length;
  document.getElementById("n").textContent = n+" / "+PAIRS.length;
  document.getElementById("p").style.width = (100*n/PAIRS.length)+"%";
  const m=document.getElementById("m");
  if(i<0){ m.innerHTML='<div class="done"><h2>全部标完了</h2><p>点右上角「导出标注」保存结果。</p></div>'; return; }
  const p=PAIRS[i];
  m.innerHTML='<div class="prompt">'+(p.prompt||"（无题目文字）")+'</div><div class="row">'+
    '<div class="poem" onclick="pick(\\'A\\')"><h3>甲</h3><pre>'+esc(p.A.body)+'</pre></div>'+
    '<div class="poem" onclick="pick(\\'B\\')"><h3>乙</h3><pre>'+esc(p.B.body)+'</pre></div></div>'+
    '<div class="keys">← 选甲　→ 选乙　↓ <b>两首都不值得留</b>（哪怕一首没那么烂也按这个）　↑ 撤销</div>';
}
function esc(s){ return s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
addEventListener("keydown",e=>{
  if(e.key==="ArrowLeft") pick("A"); else if(e.key==="ArrowRight") pick("B");
  else if(e.key==="ArrowDown") pick("tie"); else if(e.key==="ArrowUp") undo();
});
render();
</script></body></html>"""
out = W / "标注_第二批.html"
out.write_text(html.replace("__PAIRS__", json.dumps(safe, ensure_ascii=False)), encoding="utf-8")
print(f"写出 {out}（{len(safe)} 对）")
