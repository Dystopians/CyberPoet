"""桥数据 v5c（09-21 归因用，也可能就是修复版）：v5 + 上一代桥数据里被我删掉的 600 条「续写」行（题面原文：「续写下面这首未完成的现代诗。保持既有呼吸和语义张力，不重复前文；只输出续写正文。」）。
归因线索：今天训的桥无论底座、量化与否、步数、退火，面板循环都在 10–16%；上一代桥（含续写行）0.5–2%。续写行是两版数据之间最大的一处差别（占 v4 的 12%）。
同时补一个漏洞：v5 的旧行（简报/重写）没有对 v14 金标正文查重，31 行的目标诗与 v14 真人金标共享 ≥3 个 10 字窗——一并剔除（续写行里 7 条同理剔除）。
只加新文件：data/sft_train_v5c.json；dataset_info 只加不改。"""
import json, re, random
N = "/data/peilincai/CyberPoetTraining/claude_night_20260827"
norm = lambda t: re.sub(r"\s+", "", t)
def wins(t, k=10):
    f = norm(t); return {f[i:i+k] for i in range(max(0, len(f)-k+1))}
S14 = json.load(open(f"{N}/quiz_v3/v14_sources_proposed.json"))
EXW = set()
for p in S14["ha"]: EXW |= wins(p["body"])
leak = lambda r: len((wins(r["output"]) | wins(r.get("input", ""))) & EXW) >= 3
v5 = json.load(open(f"{N}/data/sft_train_v5.json")); SYS = v5[0]["system"]
keep = [r for r in v5 if not leak(r)]
cont = [dict(r, system=SYS) for r in json.load(open(f"{N}/data/sft_train_v3.json")) if r["instruction"].startswith("续写") and not leak(r)]
out = keep + cont
random.seed(20260921); random.shuffle(out)
json.dump(out, open(f"{N}/data/sft_train_v5c.json", "w"), ensure_ascii=False, indent=1)
info = json.load(open(f"{N}/data/dataset_info.json"))
info["cyberpoet_sft_v5c_train"] = {"file_name": "sft_train_v5c.json", "columns": {"prompt": "instruction", "query": "input", "response": "output", "system": "system"}}
json.dump(info, open(f"{N}/data/dataset_info.json", "w"), ensure_ascii=False, indent=1)
print(f"v5c = v5 {len(v5)} − 与 v14 金标重合 {len(v5)-len(keep)} + 续写 {len(cont)} = {len(out)}")
