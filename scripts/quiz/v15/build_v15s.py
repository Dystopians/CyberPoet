#!/usr/bin/env python3
"""v15 精简卷（11-12，清洗窗口代管）：从 v15 原卷里只取两类题，题目、正文、顺序一字不改。
  · aa  M4R 对 M4        30 题（v15 的主问题：已训好的 M4R 比不比 M4 强）
  · ha  M4 对 真人诗      6 题（尺子：同卷里 M4 对真人的水平）
短卷的结果码由 v15s_to_v15.py 换回原卷题号，再用原封不动的 analyze_v15.py 读——判读标准沿用 09-22 开卷前写死的那套。
读：交付_20260923/诗味测验15_M4对照卷.html、quiz_v3/v15_pairs_final.json（只读）
写：交付_20261112/诗味测验15s_精简卷.html、quiz_v3/v15s_index_map.json（新文件）
"""
import json, re, hashlib, os
N = "/data/peilincai/CyberPoetTraining/claude_night_20260827"
SRC = f"{N}/交付_20260923/诗味测验15_M4对照卷.html"
OUT = f"{N}/交付_20261112/诗味测验15s_精简卷.html"
MAP = f"{N}/quiz_v3/v15s_index_map.json"

s = open(SRC, encoding="utf-8").read()
i = s.index("const P=") + len("const P=")
P, end = json.JSONDecoder().raw_decode(s[i:])
F = json.load(open(f"{N}/quiz_v3/v15_pairs_final.json"))
assert len(P) == len(F) == 108
assert all(P[k]["A"]["b"] == F[k]["A"]["body"] and P[k]["B"]["b"] == F[k]["B"]["body"] for k in range(108))

def model(x): return x.get("model") if x.get("src") == "ai" else "真人"
idx = []
for k, q in enumerate(F):
    pair = {model(q["A"]), model(q["B"])}
    if q["kind"] == "aa" and pair == {"M4R_dpo", "M4_dpo"}: idx.append(k)
    elif q["kind"] == "ha" and pair == {"M4_dpo", "真人"}: idx.append(k)
assert len(idx) == 36, len(idx)

sub = [P[k] for k in idx]
body_sha = hashlib.sha256("".join(P[k]["A"]["b"] + P[k]["B"]["b"] for k in idx).encode()).hexdigest()

t = s[:i] + json.dumps(sub, ensure_ascii=False) + s[i + end:]
for old, new in [("const KEY='quiz_v15_state';", "const KEY='quiz_v15s_state';"),   # 不和原卷的作答进度串
                 ("const QVER=15;", "const QVER='15s';"),
                 ("<title>诗味测验 v15 · M4 对照卷</title>", "<title>诗味测验 v15 精简 · M4R 对 M4</title>")]:
    assert t.count(old) == 1, old
    t = t.replace(old, new)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(t)
json.dump({"说明": "短卷第 j 题 = 原卷第 idx[j] 题（0 起）", "idx": idx, "body_sha256": body_sha,
           "源卷": SRC.replace(N + "/", ""), "源卷_sha256": hashlib.sha256(s.encode()).hexdigest()},
          open(MAP, "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(f"短卷 {len(sub)} 题：", dict(Counter(F[k]['kind'] for k in idx)), "→", OUT.replace(N + "/", ""))
