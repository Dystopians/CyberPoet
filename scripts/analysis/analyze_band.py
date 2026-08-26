# 第三层：用“要求的每行字数是否落在模型天然区间”来预测能否通过
import json, re, os, statistics, collections
R = "/data/peilincai/CyberPoetTraining/cyberpoet_v1"
prompts = {json.loads(l)["pid"]: json.loads(l) for l in open(f"{R}/v3/data/prompts_v3.jsonl")}
p = f"{R}/v3/data/targets_r1_superseded.jsonl"
r1 = [json.loads(l) for l in open(p if os.path.exists(p) else f"{R}/v3/data/targets_raw.jsonl")]

def cpl_actual(t):
    lines = [x for x in t.strip().splitlines() if x.strip()]
    if not lines: return None
    return sum(len(re.sub(r"\s", "", x)) for x in lines) / len(lines)

acts = [c for c in (cpl_actual(r.get("best_draft") or r.get("body", "")) for r in r1) if c]
acts.sort()
lo_b, hi_b = acts[int(.10 * len(acts))], acts[int(.90 * len(acts))]
print(f"模型天然每行字数：中位 {statistics.median(acts):.1f}，10–90 分位 {lo_b:.1f}–{hi_b:.1f} 字/行")

def req_cpl(sp):
    lo, hi = sp["char_range"]; return ((lo + hi) / 2) / sp["lines"]

tab = collections.defaultdict(lambda: [0, 0])
for r in r1:
    sp = prompts.get(r["pid"]) or r["spec"]
    key = "落在模型区间内" if lo_b <= req_cpl(sp) <= hi_b else "落在区间外"
    tab[key][1] += 1; tab[key][0] += int(r["status"] == "accepted")
print("\n第一轮 40 条的验证：")
for k, (ok, tot) in tab.items():
    print(f"  {k}: 通过 {ok}/{tot} = {ok/tot:.0%}")

inb = [pid for pid, sp in prompts.items() if lo_b <= req_cpl(sp) <= hi_b]
print(f"\n全部 408 题：{len(inb)} 条（{len(inb)/408:.0%}）的要求落在模型天然区间内，"
      f"{408-len(inb)} 条在区间外")
sc = collections.Counter(pid.split('-f')[0] for pid in inb)
print(f"区间内的题覆盖 {len(sc)}/102 个场景；有 {sum(1 for s in sc.values() if s>=1)} 个场景至少剩 1 题")
by_st = collections.Counter(prompts[pid]["stanzas"] for pid in inb)
print("区间内题目的节数构成：", dict(sorted(by_st.items())))
open("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/data/feasible_pids.txt", "w").write("\n".join(sorted(inb)) + "\n")
