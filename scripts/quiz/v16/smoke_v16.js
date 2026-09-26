// v16 页面冒烟：正常答完 / 全跳过 / 空卷 / 结果码导入与退出 / 错版码拒收
// 运行：node smoke_v75.js 诗味测验7点5_真人对决卷.html
const fs = require('fs');
const file = process.argv[2] || '诗味测验16_散文对照卷.html';
const html = fs.readFileSync(file, 'utf8');
// eval 内 const/function 不外泄，把测试要摸的两个名字提升到 globalThis
const js = html.split('<script>')[1].split('</script>')[0]
  .replace(/\bconst P=/, 'globalThis.P=')
  .replace(/\bfunction importCode\(/, 'globalThis.importCode=function importCode(');

// ---- 极简 DOM 桩 ----
let registry = {};        // id -> element stub
let pvCells = [];         // td.pv stubs
let lastAlert = null, promptValue = null;
function parseIds(h) {
  for (const m of h.matchAll(/id="([\w]+)"/g))
    if (!registry[m[1]]) registry[m[1]] = mkEl();
  for (const m of h.matchAll(/class="pv" data-i="(\d+)" data-s="(\w)"/g))
    pvCells.push({ dataset: { i: m[1], s: m[2] }, addEventListener() {}, style: {} });
}
function mkEl() {
  return {
    _html: '', value: '', textContent: '', style: {}, onclick: null,
    classList: { _s: new Set(), toggle(c){this._s.has(c)?this._s.delete(c):this._s.add(c)}, contains(c){return this._s.has(c)}, add(c){this._s.add(c)} },
    set innerHTML(h) { this._html = h; parseIds(h); },
    get innerHTML() { return this._html; },
    append(n) { this._html += n._html; },
    querySelectorAll(sel) { return sel === 'td.pv' ? pvCells : []; },
    addEventListener() {},
    appendChild() {},
  };
}
const appEl = mkEl(); registry['app'] = appEl;
global.document = {
  createElement: () => mkEl(),
  getElementById: id => registry[id] || null,
  querySelector: () => null,
  body: { appendChild() {} },
  addEventListener() {},
};
let store = {};
global.localStorage = { getItem: k => store[k] ?? null, setItem: (k, v) => { store[k] = v; }, removeItem: k => { delete store[k]; } };
global.window = {
  prompt: () => promptValue,
  scrollTo() {}, onkeydown: null,
  innerWidth: 1400, innerHeight: 900,
};
global.alert = m => { lastAlert = m; };
global.confirm = () => true;
global.navigator = { clipboard: { writeText: () => Promise.resolve() } };

function freshRun() { registry = { app: appEl }; pvCells = []; appEl._html = ''; }

// ---- 载入页面脚本 ----
freshRun();
eval(js);

const N = P.length;
console.log('题数:', N);
const EXP = JSON.parse(require('fs').readFileSync('v16_pairs_final.json', 'utf8')).length;
if (N !== EXP) throw '题数不是 ' + EXP + ': ' + N;
if (!P.some(q => q.A.src === 'ai' || q.B.src === 'ai')) throw '未见 AI 侧';

// ---- 1) 正常答完 ----
registry['nick'].value = '冒烟测试';
registry['go'].onclick();
for (let i = 0; i < N; i++) {
  if (!registry['mark']) throw '缺备注框';
  registry['mark'].value = i % 17 === 0 ? '试批注' + i : '';
  const key = i % 9 === 0 ? 'ArrowDown' : (i % 2 ? '1' : '2');
  global.window.onkeydown({ key, target: { tagName: 'DIV' }, preventDefault() {} });
}
let h = appEl._html;
for (const need of ['分臂图灵率', '诗人面板', '挑剔指数', '批注热情', '逐题揭盲', '结果码'])
  if (!h.includes(need)) throw '结果页缺: ' + need;
if (!pvCells.length) throw '揭盲表无悬浮读诗单元格';
const b64 = h.match(/<div class="mono">([^<]+)<\/div>/)[1];
const decoded = JSON.parse(decodeURIComponent(escape(atob(b64))));
if (decoded.v !== 16) throw '结果码版本不是 16: ' + decoded.v;
if (Object.keys(decoded.picks).length !== N) throw '结果码票数不全';
console.log('① 正常答完 ✓  跳过', Object.values(decoded.picks).filter(v => v === 'X').length, '票, 码长', b64.length);

// 光谱行：v13 无 hh，诗人面板应为「无」；有 hh 的卷才查诗人名与 p 值
const hasHH = P.some(q => q.kind === 'hh');
const specRow = h.match(/<span class="nm">(?:<b>)?([^<]+)/);
if (hasHH) {
  if (!specRow || /^\d+$/.test(specRow[1])) throw '光谱行诗人名异常: ' + (specRow && specRow[1]);
  if (!/· p /.test(h)) throw '光谱缺 p 值';
  console.log('   光谱首行诗人:', specRow[1]);
} else {
  if (specRow) throw '无 hh 却出现光谱行';
  if (!h.includes('诗人面板')) throw '无 hh 时诗人面板缺失';
  console.log('   本卷无 hh，诗人面板为空 ✓');
}

// ---- 2) 结果码导入（只读查看 + 退出）----
promptValue = b64;
importCode();
if (!appEl._html.includes('只读')) throw '导入后无只读横幅';
registry['back0'].onclick();
console.log('② 结果码导入/退出 ✓');

// ---- 3) 错版码拒收 ----
lastAlert = null;
promptValue = btoa(unescape(encodeURIComponent(JSON.stringify({ v: 7.5, picks: { 0: 'A' } }))));
importCode();
if (!/题目对不上/.test(lastAlert || '')) throw '错版码未被拒: ' + lastAlert;
console.log('③ 错版码拒收 ✓');

// ---- 4) 全跳过 ----
store = {}; freshRun();
eval(js);
registry['go'].onclick();
for (let i = 0; i < N; i++) global.window.onkeydown({ key: 'ArrowDown', target: { tagName: 'DIV' }, preventDefault() {} });
h = appEl._html;
if (!h.includes('诗人面板')) throw '全跳过结果页异常';
if (!h.match(/<b>120<\/b><span>挑剔指数/) && !h.includes('挑剔指数')) throw '全跳过挑剔指数缺失';
console.log('④ 全跳过 ✓');

// ---- 5) 空卷直接出结果 ----
store = { quiz_v16_state: JSON.stringify({ nick: '', i: 999, picks: {}, marks: {} }) };
freshRun();
eval(js);
registry['go'].onclick();   // 首屏永远是规则卡，继续后才进结果
if (!appEl._html.includes('诗人面板')) throw '空卷结果页异常';
console.log('⑤ 空卷渲染 ✓');
console.log('全部冒烟通过');
