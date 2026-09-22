"""桥数据文本分层账（09-22，Codex 评审建议 C5）：只统计、不做门。对 sft_train_v4/v5 的训练目标与语料样本，按细读归纳的几类文本特征打标签、报占比。
标签（可数近似）：对话人声 = 含引号或「X说：」；顺序记事 = 然后/于是/接着/后来 ≥2 次；直接说理 = 含 因为/所以/意味着/就是/真理/生活就是 ≥2 次；
量词串 = 「一+量词」≥2.0/百字；童谣词 = 啊/呀/哩/多么/真好/真美 + 叹号 ≥0.6/百字；宏大词 = 文明/辉煌/史诗/丝绸之路/阶级/伟大/中华/民族/真理/意志 任一；
结尾抽象 = 末行含 时间/灵魂/命运/生命/记忆/永恒/孤独/世界/爱/死亡；极短 = <60 字；极长 = >500 字。"""
import json, re, collections, sys, random
N = "/data/peilincai/CyberPoetTraining/claude_night_20260827/"
CLS = re.compile(r"一[个只条种片段座张把颗根块道场阵抹缕丝声句行首朵棵株团粒滴层枚扇面册幅盏束簇]")
GAN = ["文明", "辉煌", "史诗", "丝绸之路", "阶级", "伟大", "中华", "民族", "真理", "意志"]
ABS = ["时间", "灵魂", "命运", "生命", "记忆", "永恒", "孤独", "世界", "爱", "死亡"]
def tags(t):
    z = re.sub(r"\s+", "", t); n = max(1, len(z)); L = [l.strip() for l in t.split("\n") if l.strip()]; last = L[-1] if L else ""
    return {"对话人声": bool(re.search(r"[“”「」]|说[：:]", t)),
            "顺序记事": len(re.findall(r"然后|于是|接着|后来", z)) >= 2,
            "直接说理": len(re.findall(r"因为|所以|意味着|就是|真理|生活就是", z)) >= 2,
            "量词串": len(CLS.findall(z)) / n * 100 >= 2.0,
            "童谣词": (len(re.findall(r"[啊呀哩]|多么|真[好美]", z)) + z.count("！")) / n * 100 >= 0.6,
            "宏大词": any(w in z for w in GAN), "结尾抽象": any(w in last for w in ABS), "极短(<60字)": n < 60, "极长(>500字)": n > 500}
def report(name, texts):
    c = collections.Counter(); 
    for t in texts:
        for k, v in tags(t).items(): c[k] += v
    return name, len(texts), {k: c[k] / max(1, len(texts)) for k in c}
rows = []
for v in ("v4", "v5"):
    d = json.load(open(N + f"data/sft_train_{v}.json"))
    kinds = {"标题行": [r["output"] for r in d if re.search(r"为题|题为", r["instruction"])], "简报行": [r["output"] for r in d if "简报" in r["instruction"]],
             "重写行": [r["output"] for r in d if "初稿" in r["instruction"] or "重写" in r["instruction"]], "续写行": [r["output"] for r in d if r["instruction"].startswith("续写")]}
    for k, t in kinds.items():
        if t: rows.append(report(f"{v} {k}", t))
random.seed(1); corpus = [json.loads(l)["text"] for l in open(N + "corpus_clean/base_fixed/all.jsonl")]; random.shuffle(corpus); rows.append(report("语料抽样 2000", corpus[:2000]))
for f, nm in (("quiz_v3/M8sft_panel_gens.jsonl", "桥 sft_pt9b 面板"), ("rca_20260905/M8b_ck45_panel_gens.jsonl", "M8 ck45 面板"), ("quiz_v3/M7F_panel_gens.jsonl", "M7F 面板"), ("quiz_v3/v14_cands_M4_ck50flawed.jsonl", "M4（旧题）候选")):
    try: rows.append(report(nm, [json.loads(l)["body"] for l in open(N + f)]))
    except FileNotFoundError: pass
keys = ["对话人声", "顺序记事", "直接说理", "量词串", "童谣词", "宏大词", "结尾抽象", "极短(<60字)", "极长(>500字)"]
print("| 层 | n | " + " | ".join(keys) + " |"); print("|---|---|" + "---|" * len(keys))
for nm, n, d in rows: print(f"| {nm} | {n} | " + " | ".join(f"{d.get(k,0):.0%}" for k in keys) + " |")
json.dump({nm: {"n": n, **d} for nm, n, d in rows}, open(N + "rca_20260905/sft_text_layers.json", "w"), ensure_ascii=False, indent=1)
