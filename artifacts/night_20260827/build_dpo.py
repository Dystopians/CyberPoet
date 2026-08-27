"""DPO 数据：主人全部有胜负的盲标对（能恢复题面者）。
chosen=主人选中侧，rejected=弃选侧。含真迹对（人类诗被选＝向真实诗分布偏好）。
规则：题面可恢复才入；正文去重（每首最多出现 2 次）；近重复护栏；system 统一 v2。"""
import json, re, collections
from pathlib import Path

W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
V = W / "vocab_probe"
R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
OUT = Path("/data/peilincai/CyberPoetTraining/claude_night_20260827/data")
SYS = (R / "prompts/poetry_system_v2.txt").read_text(encoding="utf-8").strip()

pm = {}   # prompt_key -> instruction
for l in open(R / "eval/benchmark/tasks.jsonl"):
    d = json.loads(l); pm[d["id"]] = d["instruction"]
for l in open(R / "v3/probes/eval_36.jsonl"):
    d = json.loads(l); pm[d["id"]] = d["instruction"]
for l in open(W / "preference/batch2_B.jsonl"):
    d = json.loads(l); pm[d["prompt_key"]] = d["prompt"]

def norm(t): return re.sub(r"\s+", "", t)
def grams(t):
    f = re.sub(r"[^一-鿿]", "", t)
    return {f[i:i+4] for i in range(max(0, len(f)-3))}
def near(x, y, thr=.8):
    a, b = grams(x), grams(y)
    return bool(a and b) and len(a & b) / len(a | b) >= thr

rows = []
def add(prompt, chosen, rejected, src):
    if not prompt or len(norm(chosen)) < 20 or len(norm(rejected)) < 20: return
    if near(chosen, rejected): return
    rows.append({"system": SYS, "instruction": prompt, "input": "",
                 "chosen": chosen.strip(), "rejected": rejected.strip(), "_src": src})

# 1) b1/b2/b4
for x in json.load(open(W / "preference/labels/all_labels.json")):
    if x["choice"] not in ("A", "B"): continue
    pk = x["pk"].split(":", 1)[-1]
    p = pm.get(pk) or pm.get(x["pk"])
    if not p: continue
    w, l = (x["ba"], x["bb"]) if x["choice"] == "A" else (x["bb"], x["ba"])
    add(p, w, l, f"b_{x['batch']}")

# 2) 选配置两轮（HTML 内嵌 PAIRS + 标注）
for html, lab in (("选配置_盲标.html", "labels_config_choice.json"),
                  ("选配置_加赛.html", "labels_config_choice_r2.json")):
    h = open(V / html, encoding="utf-8").read()
    P = json.loads(re.search(r"const PAIRS = (\[.*?\]);\n", h, re.S).group(1))
    idx = {(p["pk"], frozenset((p["A"]["cond"], p["B"]["cond"]))): p for p in P}
    for x in json.load(open(V / lab)):
        if x["choice"] not in ("A", "B"): continue
        p = idx.get((x["pk"], frozenset((x["A"], x["B"]))))
        if not p: continue
        w, l = (p["A"], p["B"]) if x["choice"] == "A" else (p["B"], p["A"])
        add(p["prompt"], w["body"], l["body"], "cfg")

# 3) 诗味测验 v1/v2（真迹对与笔墨对）
for html_file, labels in (("诗味测验.html", "quiz1"), ("诗味测验2.html", "quiz2")):
    pass  # 测验标注在 Drive JSON，下面直接用解码副本
for lab_file, html in (("labels_quiz1.json", "诗味测验.html"), ("labels_quiz2.json", "诗味测验2.html")):
    f = V / lab_file
    if not f.exists(): continue
    h = open(V / html, encoding="utf-8").read()
    P = json.loads(re.search(r"const PAIRS = (\[.*?\]);\n", h, re.S).group(1))
    idx = {}
    for p in P: idx.setdefault(p["pid"], []).append(p)
    data = json.load(open(f))
    for x in data["labels"]:
        if x["choice"] not in ("A", "B"): continue
        cands = [p for p in idx.get(x["pid"], [])
                 if {p["A"]["who"], p["B"]["who"]} == {x["A"], x["B"]}]
        if len(cands) != 1: continue
        p = cands[0]
        w, l = (p["A"], p["B"]) if x["choice"] == "A" else (p["B"], p["A"])
        prompt = p["head"].replace("同题：", "以") + "为题写一首现代诗。" if p["kind"] == "human_ai" else None
        if p["kind"] == "human_ai":
            prompt = f"以{p['head'].split('：',1)[-1]}为题写一首现代诗。"
        else:
            continue   # 笔墨对题面来自 sweep，恢复复杂，先跳过
        add(prompt, w["body"], l["body"], f"{lab_file[:-5]}")

# 4) M1 四档对照 60 对
gid = {}
for p in json.load(open(V / "pairs_M1.json")):
    gid[p["A"]["gen_id"]] = (p["prompt"], p["A"]["body"])
    gid[p["B"]["gen_id"]] = (p["prompt"], p["B"]["body"])
for x in json.load(open(V / "labels_m1_epochs.json")):
    if x["choice"] not in ("A", "B"): continue
    wa, wb = gid.get(x["A"]), gid.get(x["B"])
    if not wa or not wb: continue
    w, l = (wa, wb) if x["choice"] == "A" else (wb, wa)
    add(w[0], w[1], l[1], "m1_epochs")

# 去重：同 (题面, chosen, rejected) 只留一条；每首正文最多出现 2 次
seen, use = set(), collections.Counter()
final = []
for r in rows:
    k = (norm(r["instruction"]), norm(r["chosen"]), norm(r["rejected"]))
    if k in seen: continue
    if use[norm(r["chosen"])] >= 2 or use[norm(r["rejected"])] >= 2: continue
    seen.add(k); use[norm(r["chosen"])] += 1; use[norm(r["rejected"])] += 1
    final.append(r)

print("来源分布:", collections.Counter(r["_src"] for r in final))
for r in final: r.pop("_src")
json.dump(final, open(OUT / "dpo_train.json", "w"), ensure_ascii=False, indent=1)
info = json.load(open(OUT / "dataset_info.json"))
info["cyberpoet_dpo"] = {"file_name": "dpo_train.json", "ranking": True,
    "columns": {"prompt": "instruction", "query": "input",
                "chosen": "chosen", "rejected": "rejected", "system": "system"}}
json.dump(info, open(OUT / "dataset_info.json", "w"), ensure_ascii=False, indent=1)
print(f"DPO 对数: {len(final)}")
