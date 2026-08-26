# 第二层：模型天然的“每行多少字”与题目要求的“每行多少字”是否兼容
import json, re, statistics, collections, os
R = "/data/peilincai/CyberPoetTraining/cyberpoet_v1"
prompts = {json.loads(l)["pid"]: json.loads(l) for l in open(f"{R}/v3/data/prompts_v3.jsonl")}
p = f"{R}/v3/data/targets_r1_superseded.jsonl"
r1 = [json.loads(l) for l in open(p if os.path.exists(p) else f"{R}/v3/data/targets_raw.jsonl")]

def body_stats(t):
    lines = [x for x in t.strip().splitlines() if x.strip()]
    chars = sum(len(re.sub(r"\s", "", x)) for x in lines)
    return len(lines), chars

print("===== 题目要求的每行字数 vs 模型实际写的每行字数 =====")
req_cpl, act_cpl, rows = [], [], []
for r in r1:
    sp = prompts.get(r["pid"]) or r.get("spec")
    lo, hi = sp["char_range"]; need_lines = sp["lines"]
    req = ((lo + hi) / 2) / need_lines
    nl, ch = body_stats(r.get("best_draft") or r.get("body",""))
    if nl == 0: continue
    act = ch / nl
    req_cpl.append(req); act_cpl.append(act)
    rows.append((r["pid"], r["status"], need_lines, nl, (lo, hi), ch, round(req, 1), round(act, 1)))

print(f"题目要求（区间中点/要求行数）中位 {statistics.median(req_cpl):.1f} 字/行   "
      f"范围 {min(req_cpl):.1f}–{max(req_cpl):.1f}")
print(f"模型实际写出       中位 {statistics.median(act_cpl):.1f} 字/行   "
      f"范围 {min(act_cpl):.1f}–{max(act_cpl):.1f}")

print("\n如果模型只是行数写多了、每行字数不变，字数区间还能不能满足？")
fix = collections.Counter()
for pid, st, need_lines, nl, (lo, hi), ch, req, act in rows:
    projected = act * need_lines          # 按模型自己的行长，写够要求的行数会是多少字
    fix["字数区间内" if lo <= projected <= hi else ("偏多" if projected > hi else "偏少")] += 1
for k, v in fix.most_common():
    print(f"  {k}: {v}/{len(rows)} = {v/len(rows):.0%}")

print("\n全部 408 题按“要求的每行字数”分布（看题目本身是否为难模型）：")
allreq = []
for sp in prompts.values():
    lo, hi = sp["char_range"]
    allreq.append(((lo + hi) / 2) / sp["lines"])
buckets = collections.Counter()
for x in allreq:
    buckets[f"{int(x)}–{int(x)+1} 字/行"] += 1
for k in sorted(buckets, key=lambda s: int(s.split("–")[0])):
    print(f"  {k:12s} {buckets[k]:3d} 条")
print(f"  中位 {statistics.median(allreq):.1f} 字/行")

print("\n逐条明细（题号 状态 要求行数 实际行数 字数区间 实际字数 要求字/行 实际字/行）：")
for row in rows[:14]:
    print("  ", *row)
