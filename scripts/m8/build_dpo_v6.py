"""偏好数据 v6（09-21 重组，对应归因报告第 7 节与主人 09-21「彻底改进」指令）。
原则：只用主人的票；真人诗两侧都不进；裸底座输出两侧都不进（与当代策略分布太远）；截断样本不进；
     「两首都差」的决定票不进；同一对正反颠倒的两行都剔；每首正文最多用 2 次；按题面留验证集（不跨集）。
来源：① dpo_v1 里的 AI 对 AI 票（b1/b2/b4 去掉裸底座、选配置两轮、M1 四档）；
     ② 诗味测验 v5–v10b 全部机机决定票（167 局，题面=「以《X》为题写一首现代诗。」，即推理题面）；
     ③ 题献最小对（非口味信号，只教格式）：我按主人认可的读稿规则否决的「杜撰题献」候选做反例，
        同一首诗删掉题献行做正例——两侧只差那一行。单独打标，可整体去掉。
产物：data/dpo_train_v6.json、data/dpo_val_v6.json；dataset_info 只加不改。"""
import json, re, collections, hashlib, sys
from pathlib import Path
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825"); V = W / "vocab_probe"
R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1"); N = Path("/data/peilincai/CyberPoetTraining/claude_night_20260827")
Q = N / "quiz_v3"; OUT = N / "data"
SYS = (R / "prompts/poetry_system_v2.txt").read_text(encoding="utf-8").strip()
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
def ntok(t): return len(tok(t, add_special_tokens=False)["input_ids"])
def norm(t): return re.sub(r"\s+", "", t)
def grams(t):
    f = re.sub(r"[^一-鿿]", "", t); return {f[i:i+4] for i in range(max(0, len(f)-3))}
def near(x, y, thr=.8):
    a, b = grams(x), grams(y); return bool(a and b) and len(a & b) / len(a | b) >= thr
def tidy(t):
    t = "\n".join(l.rstrip() for l in t.strip().split("\n"))      # 行尾空白（含 Markdown 双空格）
    return t.replace("**", "")
rows = []; drop = collections.Counter()
def add(prompt, chosen, rejected, src, extra=None):
    chosen, rejected = tidy(chosen), tidy(rejected)
    if not prompt: drop["无题面"] += 1; return
    if len(norm(chosen)) < 20 or len(norm(rejected)) < 20: drop["过短"] += 1; return
    if near(chosen, rejected) and not src.startswith("ded"): drop["近重复"] += 1; return
    r = {"system": SYS, "instruction": prompt, "input": "", "chosen": chosen, "rejected": rejected, "_src": src}
    if extra: r.update(extra)
    rows.append(r)

# ---------- ① dpo_v1 的 AI 对 AI 票 ----------
pm = {}
for l in open(R / "eval/benchmark/tasks.jsonl"):
    d = json.loads(l); pm[d["id"]] = d["instruction"]
for l in open(R / "v3/probes/eval_36.jsonl"):
    d = json.loads(l); pm[d["id"]] = d["instruction"]
for l in open(W / "preference/batch2_B.jsonl"):
    d = json.loads(l); pm[d["prompt_key"]] = d["prompt"]
BASE = {"base", "base_sampled_accepted", "base_sampled_rejected"}
for x in json.load(open(W / "preference/labels/all_labels.json")):
    if x["choice"] not in ("A", "B"): continue
    if x["ma"] in BASE or x["mb"] in BASE: drop["裸底座"] += 1; continue
    pk = x["pk"].split(":", 1)[-1]; p = pm.get(pk) or pm.get(x["pk"])
    w, l = (x["ba"], x["bb"]) if x["choice"] == "A" else (x["bb"], x["ba"])
    add(p, w, l, f"v1_b_{x['batch']}")
for html, lab in (("选配置_盲标.html", "labels_config_choice.json"), ("选配置_加赛.html", "labels_config_choice_r2.json")):
    h = open(V / html, encoding="utf-8").read()
    P = json.loads(re.search(r"const PAIRS = (\[.*?\]);\n", h, re.S).group(1))
    idx = {(p["pk"], frozenset((p["A"]["cond"], p["B"]["cond"]))): p for p in P}
    for x in json.load(open(V / lab)):
        if x["choice"] not in ("A", "B"): continue
        p = idx.get((x["pk"], frozenset((x["A"], x["B"]))))
        if not p: continue
        w, l = (p["A"], p["B"]) if x["choice"] == "A" else (p["B"], p["A"])
        add(p["prompt"], w["body"], l["body"], "v1_cfg")
gid = {}
for p in json.load(open(V / "pairs_M1.json")):
    gid[p["A"]["gen_id"]] = (p["prompt"], p["A"]["body"]); gid[p["B"]["gen_id"]] = (p["prompt"], p["B"]["body"])
for x in json.load(open(V / "labels_m1_epochs.json")):
    if x["choice"] not in ("A", "B"): continue
    wa, wb = gid.get(x["A"]), gid.get(x["B"])
    if not wa or not wb: continue
    w, l = (wa, wb) if x["choice"] == "A" else (wb, wa)
    add(w[0], w[1], l[1], "v1_m1")

# ---------- ② 诗味测验 v5–v10b 机机决定票 ----------
BOTH_BAD = ("都一般", "都不太行", "都不行", "都很差", "都差", "都不怎么样", "两坨", "都是垃圾", "都很缺乏", "都太口语", "都不好", "都很烂")
for ver in ("v5", "v6", "v7", "v8", "v9", "v10b"):
    P = json.load(open(Q / f"{ver}_pairs_final.json")); L = json.load(open(Q / f"labels_owner_{ver}.json"))
    picks, marks = L.get("picks", {}), L.get("marks", {})
    for i, p in enumerate(P):
        if p.get("kind") != "aa": continue
        pk = picks.get(str(i))
        if pk not in ("A", "B"): continue
        mk = marks.get(str(i), "") or ""
        if any(k in mk for k in BOTH_BAD): drop["主人批注两首都差"] += 1; continue
        w, l = p[pk], p["B" if pk == "A" else "A"]
        if w.get("src") == "human" or l.get("src") == "human": drop["含真人"] += 1; continue
        title = p.get("title") or w.get("title") or l.get("title")
        add(f"以《{title}》为题写一首现代诗。", w["body"], l["body"], f"quiz_{ver}", {"_cm": w.get("model"), "_rm": l.get("model")})

# ---------- ③ 题献最小对 ----------
DED = re.compile(r"^[（(]?\s*[—–\-]{1,2}\s*(给|献给|赠|致|悼|怀念|纪念|兼致|兼赠|为)\s*([^\n，。、：]{1,16}?)(先生|女士|老师|同志|兄|君)?(的[^\n]{0,12})?[)）]?$")
n_ded = 0
for ver in ("v10", "v11", "v12", "v13"):
    try:
        RV = json.load(open(Q / f"{ver}_read_verdicts.json")); G = json.load(open(Q / f"{ver}_gen_gated.json")); S = json.load(open(Q / f"{ver}_sources_proposed.json"))
    except FileNotFoundError: continue
    titles = {f"ha{i}": p["title"] for i, p in enumerate(S["ha"])}; titles.update({f"aa{i}": p["title"] for i, p in enumerate(S["aa"])})
    for v in RV.get("veto", []):
        sid, arm, seed = v[0], v[1], v[2]
        body = next((c["body"] for c in G.get(f"{sid}|{arm}", []) if c["seed"] == seed), None)
        if not body: continue
        ls = body.strip().split("\n"); first = ls[0].strip(); m = DED.match(first)
        if not m: continue
        name = m.group(2).strip()
        rest = "\n".join(ls[1:]).lstrip("\n")
        if len(name) < 2 or name in rest or len(norm(rest)) < 60: continue
        if DED.match(rest.split("\n")[0].strip()): continue
        add(f"以《{titles[sid]}》为题写一首现代诗。", rest, body, f"ded_{ver}"); n_ded += 1

# ---------- 过滤：截断、颠倒对、用量上限 ----------
keep = []
for r in rows:
    tc, tr = ntok(r["chosen"]), ntok(r["rejected"])
    if tc >= 540 or tr >= 540: drop["截断(≥540 token)"] += 1; continue
    keep.append(r)
pairs = {(norm(r["chosen"]), norm(r["rejected"])) for r in keep}
keep2 = []
for r in keep:
    if (norm(r["rejected"]), norm(r["chosen"])) in pairs: drop["正反颠倒的同一对"] += 1; continue
    keep2.append(r)
seen, use, final = set(), collections.Counter(), []
for r in keep2:
    k = (norm(r["instruction"]), norm(r["chosen"]), norm(r["rejected"]))
    if k in seen: drop["重复行"] += 1; continue
    if use[norm(r["chosen"])] >= 2 or use[norm(r["rejected"])] >= 2: drop["同一首用满 2 次"] += 1; continue
    seen.add(k); use[norm(r["chosen"])] += 1; use[norm(r["rejected"])] += 1; final.append(r)

# ---------- 按题面切验证集（12% 题面；题献最小对全进训练集）----------
def is_val(r):
    if r["_src"].startswith("ded"): return False
    return int(hashlib.sha256(("v6val" + norm(r["instruction"])).encode()).hexdigest(), 16) % 100 < 16
train = [r for r in final if not is_val(r)]; val = [r for r in final if is_val(r)]
assert not ({norm(r["instruction"]) for r in train} & {norm(r["instruction"]) for r in val})

def n(t): return len(norm(t))
def nl(t): return len([l for l in t.split("\n") if l.strip()])
import statistics as st
def report(name, rs):
    if not rs: return
    dc = [n(r["chosen"]) - n(r["rejected"]) for r in rs]; dl = [nl(r["chosen"]) - nl(r["rejected"]) for r in rs]
    cpl = [n(r["chosen"]) / nl(r["chosen"]) - n(r["rejected"]) / nl(r["rejected"]) for r in rs]
    print(f"{name}: n={len(rs)} | 正例字数中位 {st.median(n(r['chosen']) for r in rs):.0f} 反例 {st.median(n(r['rejected']) for r in rs):.0f} | 字数差 均值 {st.mean(dc):+.1f} 中位 {st.median(dc):+.0f} | 行数差 均值 {st.mean(dl):+.1f} | 字/行差 均值 {st.mean(cpl):+.2f} | 正例更短占比 {sum(x<0 for x in dc)/len(rs):.2f}")
print("剔除:", dict(drop)); print("题献最小对:", n_ded)
print("来源(训练):", dict(collections.Counter(r["_src"] for r in train))); print("来源(验证):", dict(collections.Counter(r["_src"] for r in val)))
report("全部(不含题献对)", [r for r in final if not r["_src"].startswith("ded")]); report("  旧 dpo_v1 部分", [r for r in final if r["_src"].startswith("v1")]); report("  测验机机票部分", [r for r in final if r["_src"].startswith("quiz")])
cm = collections.Counter((r.get("_cm"), r.get("_rm")) for r in final if r["_src"].startswith("quiz")); print("测验票 正例臂→反例臂:", cm.most_common(12))
strip = lambda r: {k: v for k, v in r.items() if not k.startswith("_")}
json.dump([strip(r) for r in train], open(OUT / "dpo_train_v6.json", "w"), ensure_ascii=False, indent=1)
json.dump([strip(r) for r in val], open(OUT / "dpo_val_v6.json", "w"), ensure_ascii=False, indent=1)
json.dump([{"src": r["_src"], "cm": r.get("_cm"), "rm": r.get("_rm")} for r in train], open(OUT / "dpo_train_v6.meta.json", "w"), ensure_ascii=False)
info = json.load(open(OUT / "dataset_info.json"))
for k, fn in (("cyberpoet_dpo_v6", "dpo_train_v6.json"), ("cyberpoet_dpo_v6_val", "dpo_val_v6.json")):
    info[k] = {"file_name": fn, "ranking": True, "columns": {"prompt": "instruction", "query": "input", "chosen": "chosen", "rejected": "rejected", "system": "system"}}
json.dump(info, open(OUT / "dataset_info.json", "w"), ensure_ascii=False, indent=1)
print(f"写出 训练 {len(train)} 对 / 验证 {len(val)} 对")
