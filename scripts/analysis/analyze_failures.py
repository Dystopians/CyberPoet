# 只读分析：把已落盘的生成结果做失败归因，不写入 codex 的目录
import json, re, sys, collections, statistics, os
R = "/data/peilincai/CyberPoetTraining/cyberpoet_v1"
prompts = {json.loads(l)["pid"]: json.loads(l) for l in open(f"{R}/v3/data/prompts_v3.jsonl")}

def parse_fail(s):
    """把中文失败描述解析成 (维度, 实际值, 要求值)"""
    m = re.match(r"行数(\d+)，需(增加|减少)(\d+)行（要求(\d+)行）", s)
    if m: return ("行数", int(m.group(1)), int(m.group(4)))
    m = re.match(r"节数(\d+)，要求(\d+)节", s)
    if m: return ("节数", int(m.group(1)), int(m.group(2)))
    m = re.match(r"字数(\d+)，.*?（要求(\d+)到(\d+)）", s)
    if m: return ("字数", int(m.group(1)), (int(m.group(2)), int(m.group(3))))
    if s.startswith("各节行数"): return ("每节行数", None, None)
    if s.startswith("核心物象缺失"): return ("缺物象", None, None)
    if s.startswith("结尾"): return ("结尾", None, None)
    if "禁词" in s: return ("禁词", None, None)
    return ("其他:" + s[:12], None, None)

def report(title, recs):
    """recs: [(pid, passed, fails)]"""
    print(f"\n===== {title}（{len(recs)} 条）=====")
    n_pass = sum(1 for _, p, _ in recs if p)
    print(f"通过 {n_pass}/{len(recs)} = {n_pass/len(recs):.0%}")

    # 按“要求几节”分组
    by_st = collections.defaultdict(lambda: [0, 0])
    for pid, p, _ in recs:
        st = prompts[pid]["stanzas"] if pid in prompts else None
        key = "要求单节" if st == 1 else f"要求{st}节"
        by_st[key][1] += 1
        by_st[key][0] += int(p)
    print("按规格分组的通过率：")
    for k in sorted(by_st, key=lambda x: -by_st[x][1]):
        ok, tot = by_st[k]
        print(f"  {k:8s} {ok:3d}/{tot:3d} = {ok/tot:4.0%}")

    # 失败维度频次
    dims = collections.Counter()
    line_dev, stanza_actual = [], []
    for pid, p, fails in recs:
        if p: continue
        seen = set()
        for f in fails:
            d, act, req = parse_fail(f)
            if d not in seen:
                dims[d] += 1; seen.add(d)
            if d == "行数" and act is not None: line_dev.append(act - req)
            if d == "节数" and act is not None and req == 1: stanza_actual.append(act)
    print("失败维度（每条只计一次）：")
    for d, c in dims.most_common():
        print(f"  {d:10s} {c:3d}  （占失败条数 {c/max(1,len(recs)-n_pass):.0%}）")
    if line_dev:
        near = sum(1 for x in line_dev if abs(x) <= 1)
        print(f"行数偏差：n={len(line_dev)}  中位 {statistics.median(line_dev):+.0f}  "
              f"偏差≤1行的近失 {near}/{len(line_dev)} = {near/len(line_dev):.0%}  "
              f"全部={sorted(line_dev)}")
    if stanza_actual:
        print(f"要求单节却分了节：实际节数 {sorted(stanza_actual)}（中位 {statistics.median(stanza_actual):.0f}）")

# 1) 措辞 A/B 的 64 条
ab = [json.loads(l) for l in open(f"{R}/v3/reports/ab_prompt_wording.jsonl")]
for tag in ("old", "new"):
    recs = [(r["pid"], r["all_pass"], r["fails"]) for r in ab if r["tag"] == tag]
    report(f"措辞 A/B · {tag}", recs)

# 2) 第一轮 target 生成的 40 条（已作废，但失败信息有效）
p1 = f"{R}/v3/data/targets_r1_superseded.jsonl"
p1 = p1 if os.path.exists(p1) else f"{R}/v3/data/targets_raw.jsonl"
r1 = [json.loads(l) for l in open(p1)]
report("第一轮 target 生成（择优后的最好一稿）",
       [(r["pid"], r["status"] == "accepted", r.get("fails", [])) for r in r1])

# 3) 整批题目的规格构成
print("\n===== 408 条题目的规格构成 =====")
c = collections.Counter(p["stanzas"] for p in prompts.values())
for k in sorted(c):
    print(f"  要求{k}节：{c[k]:3d} 条 = {c[k]/len(prompts):4.0%}")
long_single = sum(1 for p in prompts.values() if p["stanzas"] == 1 and p["lines"] >= 12)
print(f"  其中「单节且≥12行」：{long_single} 条 = {long_single/len(prompts):.0%}")
