# v9：24 hh（5家定案局）+ 40 ha（M6×24/M5×8/M4×8）+ 56 aa（M6vsM4 19 / M6vsM5 18 / M5vsM4 19）→ 诗味测验9_新一代对决卷.html
# 相对 v4 的三处主人裁决（2026-08-27）：
#   1) aa 减半（24 hh + 24 ha + 12 aa）；AI 得票拆「真伪题胜原作」与「aa 内部对决」两类展示
#   2) 诗人光谱移入详细分析层
#   3) 默认层新增「口味词象」：从用户实际选中的诗里取手工摘录的原文词，按其强势维度吻合度挑选，
#      底部黑色小字标注出处与对应指数
# 其余承袭 v4：11 维标签、五档判定（45–55% 均衡 / n<6 样本不足）、备注、localStorage、结果码
import json, re, collections, hashlib
from v5_lib import tags, norm, chars, DIMK

pairs = json.load(open('v14_pairs_final.json'))
words = {}
assert 56 <= len(pairs) <= 80, len(pairs)   # v14
kinds = collections.Counter(p["kind"] for p in pairs)
assert kinds["hh"] == 0 and 18 <= kinds["ha"] <= 24 and 36 <= kinds["aa"] <= 56, kinds  # v14

# ---- 固定检查（规范 1/2/6/8/9）----
allk = collections.Counter(norm(p[s]["body"]) for p in pairs for s in "AB")
assert all(v == 1 for v in allk.values()), "题内正文重复"
hist = set(json.load(open('used_bodies.json'))) - set(allk)
assert not (set(allk) & hist), "与历史登记表撞车"
for i, p in enumerate(pairs):
    a, b = chars(p["A"]["body"]), chars(p["B"]["body"])
    assert max(a, b) / min(a, b) <= 1.6, f"[{i}] 篇幅比超限"
ha_pos = collections.Counter("A" if p["A"]["src"] == "human" else "B" for p in pairs if p["kind"] == "ha")
assert abs(ha_pos["A"] - ha_pos["B"]) <= 2, f"真伪题侧位失衡 {dict(ha_pos)}"
import collections as _cc
for duel in ("M8vsM4", "M8vsM8sft"):
    rows = [p for p in pairs if p.get("duel") == duel]
    a1 = duel.split("vs")[0] + "_dpo"
    lead = sum(1 for p in rows if p["A"].get("model") == a1)
    assert abs(lead - len(rows) / 2) <= 1, f"aa {duel} 侧位失衡 {lead}/{len(rows)}"

def side(s):
    body = s["body"].strip()
    w = words.get(hashlib.md5(norm(body).encode()).hexdigest()[:8], [])
    return {"b": body, "who": s.get("author") or s.get("model"),
            "src": s["src"], "t": tags(body), "w": w}

data = [{"kind": p["kind"], "dim": p.get("dim", ""), "title": p.get("title", ""),
         "A": side(p["A"]), "B": side(p["B"])} for p in pairs]


DIMK_V6 = [k for k in DIMK if k != "narrative"]  # 叙事维本卷可对比仅3对，按规范9撤下
dimcov = collections.Counter()
for q in data:
    for k in DIMK_V6:
        a, b = q["A"]["t"][k], q["B"]["t"][k]
        if a and b and a != b:
            dimcov[k] += 1
print("各维度可对比对数:", dict(dimcov))
low = [k for k in DIMK_V6 if dimcov[k] < 6]
assert not low, f"维度覆盖不足: {low}"

payload = json.dumps(data, ensure_ascii=False)

html = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>诗味测验 v14 · 重训卷</title><style>
:root{--bg:#faf8f4;--fg:#2b2b2b;--mut:#8a8378;--card:#fff;--line:#e6e0d4;--acc:#7a5c3e;--sel:#f3ead9;--foot:#3a3a3a}
@media(prefers-color-scheme:dark){:root{--bg:#191714;--fg:#e8e2d6;--mut:#8f887c;--card:#211e1a;--line:#3a352d;--acc:#c9a469;--sel:#2e2820;--foot:#b9b2a6}}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font:16px/1.9 "Noto Serif SC","Songti SC",serif;padding:24px 12px 80px}
.wrap{max-width:900px;margin:0 auto}
h1{font-size:22px;letter-spacing:.2em;text-align:center;margin:18px 0 6px}
.sub{color:var(--mut);text-align:center;font-size:13px;margin-bottom:18px}
.rules{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px;font-size:14px;margin-bottom:18px}
.rules li{margin:4px 0 4px 1.2em}
.prog{height:6px;background:var(--line);border-radius:3px;margin:14px 0;overflow:hidden}
.prog i{display:block;height:100%;background:var(--acc);transition:width .3s}
.qno{color:var(--mut);font-size:13px;text-align:center;margin:8px 0}
.pair{display:flex;gap:14px;flex-wrap:wrap}
.poem{flex:1 1 380px;background:var(--card);border:2px solid var(--line);border-radius:12px;padding:20px 22px;cursor:pointer;white-space:pre-wrap;transition:border .15s}
.poem:hover{border-color:var(--acc)}
.poem .tag{color:var(--mut);font-size:12px;margin-bottom:8px;font-family:sans-serif}
.ops{display:flex;gap:10px;justify-content:center;margin:16px 0;flex-wrap:wrap}
button{font:14px sans-serif;padding:9px 20px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:8px;cursor:pointer}
button:hover{border-color:var(--acc)}
button.warn{color:#a05c3b}
textarea{width:100%;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:10px;font:14px/1.6 sans-serif;resize:vertical;min-height:44px}
.hint{color:var(--mut);font-size:12px;text-align:center;margin-top:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 26px;margin:16px 0}
.card h3{font-size:16px;margin-bottom:12px;letter-spacing:.1em}
.words{font-size:26px;line-height:2.1;text-align:center;margin:14px 0 18px;letter-spacing:.05em}
.words .dot{color:var(--mut);margin:0 .35em}
.foot{font-size:12px;color:var(--foot);line-height:1.9;border-top:1px dashed var(--line);padding-top:10px;font-family:sans-serif}
.stmt{margin:10px 0;font-size:15px}
.stmt .mini{display:inline-block;width:120px;height:8px;background:var(--line);border-radius:4px;overflow:hidden;vertical-align:middle;margin:0 8px}
.stmt .mini i{display:block;height:100%;background:var(--acc)}
.stmt .n{color:var(--mut);font-size:13px}
.mets{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px}
.met{flex:1 1 160px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;text-align:center}
.met b{font-size:30px;display:block}
.met span{color:var(--mut);font-size:13px;font-family:sans-serif}
.spec{font-size:14px;font-family:sans-serif}
.spec .row{display:flex;align-items:center;gap:10px;margin:7px 0}
.spec .nm{width:9.5em;text-align:right;flex:none}
.spec .ct{flex:none;width:10em;color:var(--mut);font-size:12px}
.spec .bar{flex:1;height:14px;background:var(--line);border-radius:7px;overflow:hidden}
.spec .bar i{display:block;height:100%;background:var(--acc)}
.spec .bar i.ai{background:#9a86b8}
.det{display:none}
.det.open{display:block}
table{border-collapse:collapse;width:100%;font-size:13px;font-family:sans-serif;margin:10px 0}
td,th{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--sel)}
.weak{color:var(--mut)}
.small{font-size:12px;color:var(--mut)}
.mono{font-family:monospace;word-break:break-all;font-size:11px;background:var(--sel);padding:10px;border-radius:8px;max-height:120px;overflow:auto}
.hovercard{display:none;position:fixed;z-index:99;max-width:420px;max-height:62vh;overflow:auto;white-space:pre-wrap;background:var(--card);color:var(--fg);border:1.5px solid var(--acc);border-radius:10px;padding:14px 16px;font-size:14px;line-height:1.8;box-shadow:0 6px 24px rgba(0,0,0,.25)}
td.pv{cursor:help;text-decoration:underline dotted}
.nav{display:flex;flex-wrap:wrap;gap:3px;margin:8px 0 12px}
.nav b{width:27px;height:22px;font-size:11px;font-weight:400;display:flex;align-items:center;justify-content:center;border:1px solid var(--line);border-radius:5px;cursor:pointer;background:var(--card);color:var(--fg)}
.nav b.done{background:#2f9e5a;color:#fff;border-color:#2f9e5a}
.nav b.cur{outline:2px solid var(--acc);outline-offset:1px}
.hovercard{cursor:copy}
.copied{color:#2f9e5a;font-size:12px}
</style></head><body><div class="wrap">
<h1>诗 味 测 验 · 拾肆</h1>
<div class="sub">重训卷 · 按溃败反思重训的新臂 M8 对现役 M4 · M8 对它自己没做偏好训练的桥 · 备注即黄金</div>
<div id="app"></div>
</div><script>
const P=__PAYLOAD__;
const KEY='quiz_v14_state';
let st=JSON.parse(localStorage.getItem(KEY)||'null')||{nick:'',i:0,picks:{},marks:{}};
const QVER=14;
const PRELOAD='__PRELOAD__';
let viewing=false, myst=null;
function importCode(pre){
 const c=pre||window.prompt('粘贴结果码：');
 if(!c)return;
 let d=null;
 try{d=JSON.parse(decodeURIComponent(escape(atob(c.trim()))))}catch(e){alert('结果码无法解析');return}
 if(!d||!d.picks){alert('结果码内容不完整');return}
 if(d.v!==QVER){alert('这是 v'+d.v+' 的结果码，本页是 v'+QVER+'，题目对不上');return}
 if(!viewing)myst=st;
 viewing=true;
 st={nick:d.nick||'',i:P.length,picks:d.picks,marks:d.marks||{}};
 result();window.scrollTo(0,0);
}
function exitView(){st=myst;viewing=false;myst=null;st.i>=P.length?result():start();window.scrollTo(0,0)}
const $=h=>{const d=document.createElement('div');d.innerHTML=h;return d};
const app=document.getElementById('app');
function save(){if(viewing)return;localStorage.setItem(KEY,JSON.stringify(st))}
function navHtml(){return '<div class="nav">'+P.map((q,i)=>`<b class="${st.picks[i]!==undefined?'done':''}${i===st.i?' cur':''}" data-j="${i}" title="第${i+1}题">${i+1}</b>`).join('')+'</div>'}
function bindNav(){app.querySelectorAll('.nav b').forEach(b=>b.onclick=()=>{const m=document.getElementById('mark');if(m&&st.i<P.length)st.marks[st.i]=m.value;st.i=+b.dataset.j;save();ask();window.scrollTo(0,0)})}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function start(){
 app.innerHTML='';
 app.append($(`<div class="rules"><b>怎么玩</b><ul>
 <li>每题两首诗，<b>只选你真心更喜欢的那首</b>——不是猜哪首更"对"，是偏爱。</li>
 <li>两首都不喜欢：按 <b>↓</b> 或点"都不喜欢"，这也是重要的一票。</li>
 <li>备注栏随手写一句为什么（可空）——你的理由比选择更珍贵。</li>
 <li>键盘：<b>1</b> 选左，<b>2</b> 选右，<b>↓</b> 都不喜欢；点诗即选择并自动进下一题。</li>
 <li>进度自动保存，关掉页面回来接着做。</li></ul>
 <div style="margin-top:10px"><input id="nick" placeholder="留个名号（用于汇总标注）" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font:14px sans-serif" value="${st.nick||''}"></div>
 <div class="ops"><button id="go">${st.i>0?'继续（第'+(st.i+1)+'题）':'开始'}</button><button id="imp0">读取结果码</button>${st.i>0?'<button class="warn" id="reset">清空重做</button>':''}</div></div>`));
 document.getElementById('go').onclick=()=>{st.nick=document.getElementById('nick').value.trim();save();ask()};
 const im0=document.getElementById('imp0');if(im0)im0.onclick=importCode;
 const r=document.getElementById('reset');if(r)r.onclick=()=>{if(confirm('清空全部进度？')){st={nick:st.nick,i:0,picks:{},marks:{}};save();start()}};
}
function ask(){
 if(st.i>=P.length)return result();
 const q=P[st.i];
 app.innerHTML='';
 app.append($(`<div class="prog"><i style="width:${st.i/P.length*100}%"></i></div>
 ${navHtml()}
 <div class="qno">第 ${st.i+1} / ${P.length} 题${q.title?' · 同题《'+q.title+'》':''}</div>
 <div class="pair">
  <div class="poem" id="pa"><div class="tag">甲</div>${esc(q.A.b)}</div>
  <div class="poem" id="pb"><div class="tag">乙</div>${esc(q.B.b)}</div>
 </div>
 <div style="margin-top:12px"><textarea id="mark" placeholder="备注（一句理由的价值高于选择本身——机器味在哪、好在哪、坏在哪）">${st.marks[st.i]||''}</textarea></div>
 <div class="ops">
  <button id="skip" class="warn">都不喜欢（↓）</button>
  ${st.i>0?'<button id="back">上一题</button>':''}
  ${Object.keys(st.picks).length>=P.length?'<button id="toRes">查看结果 ▸</button>':''}
 </div>
 <div class="hint">点诗即选择并进入下一题 · 1/2 键同效</div>`));
 const pick=v=>{st.picks[st.i]=v;st.marks[st.i]=document.getElementById('mark').value;st.i++;save();ask();window.scrollTo(0,0)};
 document.getElementById('pa').onclick=()=>pick('A');
 document.getElementById('pb').onclick=()=>pick('B');
 document.getElementById('skip').onclick=()=>pick('X');
 const bk=document.getElementById('back');if(bk)bk.onclick=()=>{st.marks[st.i]=document.getElementById('mark').value;st.i--;save();ask()};
 const tr=document.getElementById('toRes');if(tr)tr.onclick=()=>{st.marks[st.i]=document.getElementById('mark').value;st.i=P.length;save();result();window.scrollTo(0,0)};
 bindNav();
 window.onkeydown=e=>{
  if(e.target.tagName==='TEXTAREA'&&e.key!=='Enter')return;
  if(e.key==='1')pick('A');else if(e.key==='2')pick('B');
  else if(e.key==='ArrowDown'){e.preventDefault();pick('X')}
 };
}
// ---------- 结果 ----------
const DIMS=[
 {k:'density', name:'意象密度', L:'密', R:'疏', desc:'实词紧排还是虚词流动'},
 {k:'device',  name:'复沓装置', L:'有装置', R:'无装置', desc:'吃不吃复沓与排比'},
 {k:'ending',  name:'收尾方式', L:'悬置', R:'落地', desc:'收在虚处还是实处'},
 {k:'simile',  name:'明喻',     L:'有喻', R:'无喻', desc:'像、仿佛、如同'},
 {k:'register',name:'语域',     L:'口语', R:'书面', desc:'说话的诗还是写字的诗'},
 {k:'abstract',name:'词汇质地', L:'抽象', R:'具象', desc:'时间灵魂命运 vs 桌子马匹街道'},
 {k:'punct',   name:'标点',     L:'满标点', R:'无标点', desc:'句读森严还是一泻到底'},
 {k:'linelen', name:'行的长短', L:'长句行', R:'短句行', desc:'长句铺陈还是短句斩截'},
 {k:'person',  name:'对话感',   L:'有你', R:'无你', desc:'诗里有没有一个"你"'},
 {k:'heat',    name:'温度',     L:'热', R:'冷', desc:'呼告感叹还是冷面陈述'},
 ];
function binom2(l,n){ // 双侧精确二项 p (p0=0.5)
 if(n===0)return 1;
 const logC=(n,k)=>{let s=0;for(let i=1;i<=k;i++)s+=Math.log(n-k+i)-Math.log(i);return s};
 const pk=k=>Math.exp(logC(n,k)+n*Math.log(0.5));
 const obs=pk(l); let p=0;
 for(let k=0;k<=n;k++){if(pk(k)<=obs+1e-12)p+=pk(k)}
 return Math.min(1,p);
}
function verdict(l,r){
 const n=l+r;
 if(n<6)return {band:'样本不足',score:0,pv:binom2(l,n)};
 const p=l/n;
 const pv=binom2(l,n);
 if(p>=0.65)return {band:'明显偏',side:'L',score:2,p,pv};
 if(p>0.55) return {band:'略偏',side:'L',score:1,p,pv};
 if(p<=0.35)return {band:'明显偏',side:'R',score:2,p,pv};
 if(p<0.45) return {band:'略偏',side:'R',score:1,p,pv};
 return {band:'均衡',score:0,p,pv};
}
function result(){
 window.onkeydown=null;
 const stat=DIMS.map(d=>{
  let l=0,r=0;
  P.forEach((q,i)=>{const p=st.picks[i];if(p!=='A'&&p!=='B')return;
   const a=q.A.t[d.k],b=q.B.t[d.k];if(!a||!b||a===b)return;
   if(q[p].t[d.k]===d.L)l++;else r++});
  return {...d,l,r,v:verdict(l,r)};
 });
 const strong=stat.filter(s=>s.v.score>=1)
  .sort((a,b)=>b.v.score-a.v.score||Math.abs(b.v.p-0.5)*Math.sqrt(b.l+b.r)-Math.abs(a.v.p-0.5)*Math.sqrt(a.l+a.r));
 // 分臂火眼：真伪题按 AI 臂拆分（主人版核心信号）
 const haByArm={};
 P.forEach((q,i)=>{const p=st.picks[i];if(q.kind!=='ha')return;
  const ai=q.A.src==='ai'?q.A:q.B;
  const a=ai.who; haByArm[a]=haByArm[a]||{n:0,hu:0,ai:0};
  if(p!=='A'&&p!=='B')return;
  haByArm[a].n++;
  if(q[p].src==='human')haByArm[a].hu++; else haByArm[a].ai++;});
 // 真伪 / 挑剔 / 批注
 let hu=0,hn=0;P.forEach((q,i)=>{const p=st.picks[i];if(q.kind!=='ha'||(p!=='A'&&p!=='B'))return;hn++;if(q[p].src==='human')hu++});
 const skip=Object.values(st.picks).filter(v=>v==='X').length;
 const marked=Object.keys(st.marks).filter(k=>st.marks[k]).length;
 // 详细层：诗人光谱 + AI 两类得票
 const poet={};P.forEach((q,i)=>{const p=st.picks[i];if(q.kind!=='hh'||(p!=='A'&&p!=='B'))return;
  for(const s of ['A','B']){const w=q[s].who;poet[w]=poet[w]||{n:0,win:0};poet[w].n++;if(p===s)poet[w].win++}});
 const spec=Object.entries(poet).map(([name,d])=>({name,n:d.n,win:d.win,rate:d.win/d.n,pv:binom2(d.win,d.n)}))
  .sort((a,b)=>Math.abs(b.rate-0.5)*Math.sqrt(b.n)-Math.abs(a.rate-0.5)*Math.sqrt(a.n));
 const haArm={};P.forEach((q,i)=>{const p=st.picks[i];if(q.kind!=='ha'||(p!=='A'&&p!=='B'))return;
  const s=q[p];if(s.src!=='human')haArm[s.who]=(haArm[s.who]||0)+1});
 const aaArm={};P.forEach((q,i)=>{const p=st.picks[i];if(q.kind!=='aa'||(p!=='A'&&p!=='B'))return;
  const w=q[p].who;aaArm[w]=(aaArm[w]||0)+1});

 let rows='';P.forEach((q,i)=>{const p=st.picks[i]||'—';
  const w=s=>`${s.src==='human'?s.who:'AI·'+s.who}`;
  rows+=`<tr><td>${i+1}</td><td>${q.kind}${q.dim?'·'+q.dim:''}</td><td>${q.title||''}</td><td class="pv" data-i="${i}" data-s="A">${w(q.A)}</td><td class="pv" data-i="${i}" data-s="B">${w(q.B)}</td><td><b>${p==='X'?'都不要':p}</b></td><td>${esc(st.marks[i]||'')}</td></tr>`});
 const out={v:QVER,nick:st.nick,picks:st.picks,marks:st.marks,ts:Date.now()};
 const b64=btoa(unescape(encodeURIComponent(JSON.stringify(out))));
 const armHtml=`<table><tr><th>AI 臂</th><th>对局</th><th>你选了原作</th><th>AI 反杀</th><th>该臂图灵率</th></tr>${
  Object.entries(haByArm).map(([a,d])=>`<tr><td>${a}</td><td>${d.n}</td><td>${d.hu}</td><td><b>${d.ai}</b></td><td>${d.n?Math.round(d.ai/d.n*100):0}%</td></tr>`).join('')}</table>
  <div class="small">M8 = 09-21 按溃败反思重训的新臂（新桥 + 参考模型改对的偏好训练 + 你全部机机决定票重组的偏好数据）；M8sft = 同一座新桥、没做偏好训练；M4 = 现役。M8 对 M4 = 新臂能不能过现役；M8 对 M8sft = 修正后的偏好训练到底有没有用。</div>`;
 const stmtHtml=strong.slice(0,3).length?strong.slice(0,3).map(s=>{
  const side=s.v.side==='L'?s.L:s.R, other=s.v.side==='L'?s.R:s.L;
  const win=s.v.side==='L'?s.l:s.r, lose=s.v.side==='L'?s.r:s.l;
  const pct=Math.round(win/(win+lose)*100);
  return `<div class="stmt">${s.name}：<b>${s.v.band}「${side}」</b><span class="mini"><i style="width:${pct}%"></i></span><span class="n">${side} ${win} : ${lose} ${other}</span><br><span class="small">${s.desc}</span></div>`
 }).join(''):'<div class="stmt">各维度都没拉开差距——口味均衡，不轻易站队。全表见详细分析。</div>';
 app.innerHTML='';
 app.append($(`
 <div class="card"><h3>逐题跳转</h3>${navHtml()}<div class="small">绿色 = 已作答；点数字可回到该题修改（只读查看模式下修改不会保存）。</div></div>
 <div class="card"><h3>真伪对局 · 分臂图灵率</h3>${armHtml}</div>
 <div class="card"><h3>诗人面板（本卷无真人互殴局）</h3>
  <div class="spec">${spec.map(s=>{
   const pv=s.pv<0.001?'<0.001':s.pv.toFixed(3);
   const sig=s.pv<0.05&&s.n>=6;
   return `<div class="row"><span class="nm">${sig?'<b>'+s.name+'</b>':s.name}</span><span class="bar"><i style="width:${Math.round(s.rate*100)}%"></i></span><span class="ct">${s.win}/${s.n} · ${Math.round(s.rate*100)}%${sig?' · <b>p '+pv+'</b>':' · p '+pv}</span></div>`
  }).join('')||'<div class="small">无</div>'}</div>
  <div class="small" style="margin-top:8px">胜率 = 得票/有效出场；p 对 50% 双侧精确二项，加粗 = 过 0.05 且出场≥6。本卷六家各 8 出场（保罗·策兰/洛夫/商禽/马雁/张枣/多多），单卷可出诗人级倾向，显著判定要并入总账。</div></div>
 <div class="mets">
  <div class="met"><b>${hu}/${hn}</b><span>火眼指数<br>同题真伪里选中真人</span></div>
  <div class="met"><b>${skip}</b><span>挑剔指数<br>「都不喜欢」次数</span></div>
  <div class="met"><b>${marked}</b><span>批注热情<br>写了备注的题数</span></div>
 </div>
 <div class="card"><h3>全部 ${DIMS.length} 个维度（精确二项 p，对 50% 双侧）</h3>
   <table><tr><th>维度</th><th>说明</th><th>对比票</th><th>判定</th><th>p 值</th></tr>
   ${stat.map(s=>{
    const pv=s.v.pv===undefined?'—':(s.v.pv<0.001?'<0.001':s.v.pv.toFixed(3));
    const cells=`<td>${s.name}</td><td class="small">${s.desc}</td><td>${s.L} ${s.l} : ${s.r} ${s.R}</td>`;
    if(s.v.score===0)return `<tr class="weak">${cells}<td>${s.v.band}</td><td>${pv}</td></tr>`;
    const side=s.v.side==='L'?s.L:s.R;
    return `<tr>${cells}<td><b>${s.v.band}「${side}」</b>（${Math.round((s.v.side==='L'?s.v.p:1-s.v.p)*100)}%）</td><td>${s.v.pv<0.05?'<b>'+pv+'</b>':pv}</td></tr>`
   }).join('')}</table>
   <div class="small">只统计"两首诗在该维度上确实不同"的题；p 加粗 = 过 0.05。</div></div>
 <div class="card"><h3>你态度最鲜明的口味</h3>${stmtHtml}
  <div class="small">只报有把握的：票数比落在 45%–55% 之间记为"均衡"，对比不足 6 次记为"样本不足"，都不下断言。</div></div>
 ${viewing?`<div class="card" style="border-color:var(--acc)"><b>正在查看「${esc(st.nick||'匿名')}」的结果卷（只读）</b>——你自己的进度未受影响。</div>`:''}
 <div class="ops"><button id="more">展开详细分析 ▾</button><button id="exp">复制结果码</button><button id="impR">读取结果码</button>${viewing?'<button id="back0">返回我的答卷</button>':'<button class="warn" id="redo">重新测</button>'}</div>
 <div class="det" id="det">

  <div class="card"><h3>AI 得票的两种含金量</h3>
   <table><tr><th>场合</th><th>臂</th><th>得票</th><th>怎么读</th></tr>
   ${Object.entries(haArm).map(([k,v])=>`<tr><td>同题真伪（对面是原作）</td><td>${k}</td><td>${v}</td><td>硬通货：赢过了真人原作</td></tr>`).join('')||'<tr><td>同题真伪</td><td>—</td><td>0</td><td>没有 AI 赢过原作</td></tr>'}
   ${Object.entries(aaArm).map(([k,v])=>`<tr><td>AI 内部对决</td><td>${k}</td><td>${v}</td><td>只反映两臂相对强弱</td></tr>`).join('')}
   </table>
   <div class="small">此前版本把两类票加总展示，AI 得票被 AI 内部对决题保底抬高，已拆开。社区对比待部署版接入。</div></div>

  <div class="card"><h3>逐题揭盲</h3><div class="small">悬浮 甲·乙 栏可查看该诗全文；<b>点击即复制原文</b>到剪贴板（点浮窗本身也可复制）。</div>
   <table><tr><th>#</th><th>类</th><th>同题</th><th>甲</th><th>乙</th><th>你选</th><th>备注</th></tr>${rows}</table></div>
  <div class="card"><h3>结果码</h3>（发给出题人即可）<div class="mono">${b64}</div></div>
 </div>`));
 if(app.querySelectorAll && document.body){
  let hc=document.querySelector('.hovercard');
  if(!hc){hc=document.createElement('div');hc.className='hovercard';document.body.appendChild(hc)}
  const show=(td,e)=>{const q=P[+td.dataset.i];const s=q[td.dataset.s];
   hc.textContent=(q.title?'《'+q.title+'》\\n':'')+s.b;hc.style.display='block';
   const x=Math.min(e.clientX+14,window.innerWidth-440);
   hc.style.left=Math.max(8,x)+'px';
   hc.style.top='0px';
   const y=Math.min(e.clientY+12,window.innerHeight-hc.offsetHeight-12);
   hc.style.top=Math.max(8,y)+'px';};
  app.querySelectorAll('td.pv').forEach(td=>{
   td.addEventListener('mousemove',e=>show(td,e));
   td.addEventListener('mouseleave',()=>hc.style.display='none');
   td.addEventListener('click',e=>{e.stopPropagation();const q=P[+td.dataset.i];const s=q[td.dataset.s];const txt=(q.title?'《'+q.title+'》\\n':'')+s.b;show(td,e);navigator.clipboard.writeText(txt).then(()=>{hc.textContent=txt+'\\n\\n✓ 已复制原文'}).catch(()=>{hc.textContent=txt+'\\n\\n（复制失败：请手动选取）'})});
  });
  hc.onclick=e=>{e.stopPropagation();const t=hc.textContent.replace(/\\n\\n✓ 已复制原文$/,'');navigator.clipboard.writeText(t).then(()=>{hc.textContent=t+'\\n\\n✓ 已复制原文'})};
  document.addEventListener('click',()=>hc.style.display='none');
  bindNav();
 }
 document.getElementById('more').onclick=e=>{const d=document.getElementById('det');d.classList.toggle('open');e.target.textContent=d.classList.contains('open')?'收起详细分析 ▴':'展开详细分析 ▾'};
 document.getElementById('exp').onclick=()=>{navigator.clipboard.writeText(b64).then(()=>alert('已复制'))};
 const rd=document.getElementById('redo');if(rd)rd.onclick=()=>{if(confirm('清空重做？')){st={nick:st.nick,i:0,picks:{},marks:{}};save();start()}};
 const bk0=document.getElementById('back0');if(bk0)bk0.onclick=exitView;
 const imR=document.getElementById('impR');if(imR)imR.onclick=importCode;
}
if(PRELOAD){importCode(PRELOAD)}else{start()}
</script></body></html>"""

import os
OUT = os.environ.get('OUT', '诗味测验14_重训卷.html')
html = html.replace("__PAYLOAD__", payload).replace("__PRELOAD__", os.environ.get('PRELOAD_CODE', '').strip())
open(OUT, 'w').write(html)
print("写出", OUT, len(html), "bytes")
