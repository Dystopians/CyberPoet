# v16 装配 · ha≤24 + aa≤56。臂位/对决按 v16_slot_proposal.json（读稿前哈希预分配，防看质量挑臂）；
# 通读否决按 v16_read_verdicts.json（盲读：否决先按匿名编号记，再经 v16_blind_key.json 对回 [槽, 臂, 种子]）。本卷无 hh。
# 09-21 两处改动（09-16 复核）：槽内候选按哈希随机序取（不再取质感第一）；机机局两臂谁先选按槽号哈希轮换（旧规则让先选臂占微小便宜）。
# 纪律：槽内换种子按质感序回退；配额缺口由「备」槽晋升（如实打印）；篇幅比≤1.6；
#   侧位配平（ha 人侧全局平衡；aa 逐对决类型平衡）；登记表+hh+选集内 10 字窗互查。
import json, re, random, collections, sys
sys.path.insert(0, '.')
from v5_lib import norm, chars

SRC = json.load(open('v16_sources_proposed.json'))
GATED = json.load(open('v16_gen_gated.json'))
PLAN = json.load(open('v16_slot_proposal.json'))
RV = json.load(open('v16_read_verdicts.json'))
import hashlib
VETO = {tuple(x) for x in RV.get("veto", [])}          # [sid, arm, seed]
FORCE = {k: tuple(v) for k, v in RV.get("force", {}).items()}   # sid -> (arm,seed) 或 aa: sid|arm -> seed

from v16_arms import DUEL_A, DUEL_B, DUEL_C, QUOTA_HA, QUOTA_AA, ARMS   # v16：ha M4P 10 / M4 10；aa M4PvsM4 28
pairs, log = [], []

_used0 = set(json.load(open('used_bodies.json')))
_usedg0 = set()
for _b in _used0: _usedg0 |= {_b[i:i+10] for i in range(max(len(_b)-9, 1))}
def _fg0(t):
    s = norm(t); return {s[i:i+10] for i in range(max(len(s)-9, 1))}
REG_SKIP = set()
def cands(sid, arm):
    for c in GATED.get(f"{sid}|{arm}", []):
        if (sid, arm, c["seed"]) in VETO: continue
        if _fg0(c["body"]) & _usedg0:          # 09-21：撞登记表的候选机械跳过（以前靠装配报错后手工否决）
            REG_SKIP.add((sid, arm, c["seed"])); continue
        yield c["seed"], c["body"]

def ratio_ok(b, ref_len):
    return ref_len is None or max(chars(b), ref_len) / min(chars(b), ref_len) <= 1.6

def fit(sid, arm, ref_len):
    # 锁种子只在合篇幅比时生效；不合则如实打印并回退到常规序（v9 事故：3 条 force 越过了篇幅比）
    if f"{sid}|{arm}" in FORCE:
        want = FORCE[f"{sid}|{arm}"]
        for s, b in cands(sid, arm):
            if s == want:
                if ratio_ok(b, ref_len): return s, b
                log.append(f"{sid}|{arm} 锁定 seed{want} 篇幅比不合（{chars(b)} vs {ref_len}），回退常规序")
    for s, b in cands(sid, arm):
        if ratio_ok(b, ref_len):
            return s, b
    return None, None


# ---- ha：预分配臂优先，缺口时 备槽晋升 + 配额重排 ----
DROP = set(RV.get("drop", []))                          # 整槽弃用（金标撞登记表/同题）
ha_plan = {s: a for s, a in PLAN["ha"].items() if s not in DROP}
gold = {f"ha{i}": p for i, p in enumerate(SRC["ha"])}
feas = {}
for sid, arm0 in ha_plan.items():
    g = gold[sid]; gl = chars(g["body"])
    for arm in ARMS:
        s, b = fit(sid, arm, gl)
        if b is not None: feas[(sid, arm)] = (s, b)
def pref(sid, arm):
    p = ha_plan[sid]
    return 0 if p == arm else (1 if p == "备" else 2)
chosen = {}
QUOTA = dict(QUOTA_HA)
singles = [sid for sid in ha_plan if sum((sid, a) in feas for a in QUOTA) == 1]
for sid in sorted(singles, key=lambda s: min(pref(s, a) for a in QUOTA if (s, a) in feas)):
    arm = next(a for a in QUOTA if (sid, a) in feas)
    if sum(1 for v in chosen.values() if v == arm) < QUOTA[arm] and len(chosen) < 24:
        chosen[sid] = arm
rest = sorted([s for s in ha_plan if s not in chosen and any((s, a) in feas for a in QUOTA)],
              key=lambda s: min(pref(s, a) for a in QUOTA if (s, a) in feas))
for sid in rest:
    if len(chosen) >= 24: break
    opts = [a for a in QUOTA if (sid, a) in feas and sum(1 for v in chosen.values() if v == a) < QUOTA[a]]
    if not opts: continue
    opts.sort(key=lambda a: pref(sid, a))
    chosen[sid] = opts[0]
assert len(chosen) >= 12, f"ha 只凑到 {len(chosen)}"   # v16：金标只剩 21 首，上限 20 尽力、如实缺额
log.append(f"ha 实装 {len(chosen)} 题（上限 24）")
assert all(c <= QUOTA_HA[a] for a, c in collections.Counter(chosen.values()).items()), collections.Counter(chosen.values())
moved = [f"{s}:{ha_plan[s]}->{a}" for s, a in chosen.items() if ha_plan[s] not in (a, "备")]
promoted = [s for s, a in chosen.items() if ha_plan[s] == "备"]
log += [f"ha 机械改判: {moved or '无'}", f"ha 备槽晋升: {promoted or '无'}"]
for sid, arm in sorted(chosen.items(), key=lambda x: int(x[0][2:])):
    g = gold[sid]; s, b = feas[(sid, arm)]
    pairs.append({"kind": "ha", "title": g["title"], "slot": sid,
                  "hu": {"src": "human", "author": g["author"], "title": g["title"], "body": g["body"].strip()},
                  "ai": {"src": "ai", "model": f"{arm}_dpo", "body": b}})

# ---- aa：逐对决类型装配 ----
aa_plan = {s: d for s, d in PLAN["aa"].items() if s not in DROP}
titles = {f"aa{i}": p["title"] for i, p in enumerate(SRC["aa"])}
got_by_duel = collections.defaultdict(list)
spare = [s for s, d in aa_plan.items() if d == "备"]
def try_slot(sid, duel):
    a1, a2 = duel.split("vs")
    first, second = (a1, a2) if int(hashlib.sha256(("v16first" + sid).encode()).hexdigest(), 16) % 2 == 0 else (a2, a1)
    for s1, b1 in cands(sid, first):
        s2, b2 = fit(sid, second, chars(b1))
        if b2 is not None:
            return (a1, s1, b1, a2, s2, b2) if first == a1 else (a1, s2, b2, a2, s1, b1)
    return None
for sid, duel in aa_plan.items():
    if duel == "备": continue
    r = try_slot(sid, duel)
    if r: got_by_duel[duel].append((sid, r))
    else: log.append(f"{sid} {duel} 无合比例组合")
failed = [sid for sid, duel in aa_plan.items() if duel != "备" and sid not in {s for rows in got_by_duel.values() for s, _ in rows}]
for duel, need in QUOTA_AA.items():
    while len(got_by_duel[duel]) < need and spare:
        sid = spare.pop(0)
        r = try_slot(sid, duel)
        if r: got_by_duel[duel].append((sid, r)); log.append(f"备槽晋升 {sid}->{duel}")
    # 备槽用尽仍缺：让本对决在其它对决装不上的槽里再试一遍（如实打印）；仍缺则如实缺额，不硬凑
    while len(got_by_duel[duel]) < need and failed:
        sid = failed.pop(0)
        r = try_slot(sid, duel)
        if r: got_by_duel[duel].append((sid, r)); log.append(f"落空槽改配 {sid}->{duel}")
    if len(got_by_duel[duel]) < need:
        log.append(f"!! {duel} 配额 {need} 只凑到 {len(got_by_duel[duel])}（整槽弃用/缺臂/篇幅比），如实缺额")
    got_by_duel[duel] = got_by_duel[duel][:need]
for duel, rows in got_by_duel.items():
    for sid, (a1, s1, b1, a2, s2, b2) in rows:
        pairs.append({"kind": "aa", "duel": duel, "title": titles[sid], "slot": sid,
                      "x": {"src": "ai", "model": f"{a1}_dpo", "body": b1},
                      "y": {"src": "ai", "model": f"{a2}_dpo", "body": b2}})

# ---- 侧位配平 ----
rng = random.Random(140099)
ha_pairs = [p for p in pairs if p["kind"] == "ha"]
aa_pairs = [p for p in pairs if p["kind"] == "aa"]
rng.shuffle(ha_pairs)
out = []
for i, p in enumerate(ha_pairs):
    A, B = (p["hu"], p["ai"]) if i % 2 == 0 else (p["ai"], p["hu"])
    out.append({"kind": "ha", "title": p["title"], "slot": p["slot"], "A": A, "B": B})
for duel in QUOTA_AA:
    rows = [p for p in aa_pairs if p["duel"] == duel]
    rng.shuffle(rows)
    for i, p in enumerate(rows):
        A, B = (p["x"], p["y"]) if i % 2 == 0 else (p["y"], p["x"])
        out.append({"kind": "aa", "duel": duel, "title": p["title"], "slot": p["slot"], "A": A, "B": B})

# ---- 交叉查重：登记表 + hh 卷 + 选集内 ----
errs = []
used = set(json.load(open('used_bodies.json')))
hh = []   # v16 无 hh（标准局另加）
def fg(t):
    s = norm(t); return {s[i:i+10] for i in range(max(len(s)-9, 1))}
allg = [((f"hh{i}", s), fg(p[s]["body"])) for i, p in enumerate(hh) for s in "AB"]
for i, p in enumerate(out):
    for s in "AB":
        b = p[s]["body"]
        if p[s]["src"] == "human" and norm(b) in used: errs.append(f"[{p['slot']}]{s} 金标已用过")
        allg.append(((p["slot"], s), fg(b)))
usedg = set()
for b in used: usedg |= {b[i:i+10] for i in range(max(len(b)-9, 1))}
for (k1, g1) in allg:
    if k1[0].startswith("hh"): continue
    if g1 & usedg: errs.append(f"{k1} 撞登记表")
for x in range(len(allg)):
    for y in range(x + 1, len(allg)):
        if allg[x][0][0] == allg[y][0][0]: continue
        if allg[x][1] & allg[y][1]: errs.append(f"互重 {allg[x][0]} {allg[y][0]}")
# 跨题型同题互斥（含 hh）
t_seen = collections.defaultdict(set)
for i, p in enumerate(hh):
    for s in "AB": t_seen[p[s]["title"]].add(f"hh{i}")
for p in out:
    t_seen[p["title"]].add(p["slot"])
for t, ks in t_seen.items():
    if len(ks) > 1: errs.append(f"同题《{t}》: {sorted(ks)}")

for l in log: print(l)
if REG_SKIP: print(f"撞登记表机械跳过的候选: {len(REG_SKIP)} 首")
if errs:
    json.dump(out, open('v16_haaa_draft.json', 'w'), ensure_ascii=False, indent=1)
    print("!! 待处理:"); [print("  -", e) for e in errs]
else:
    json.dump(out, open('v16_haaa_final.json', 'w'), ensure_ascii=False, indent=1)
    hu = collections.Counter("A" if p["A"]["src"] == "human" else "B" for p in out if p["kind"] == "ha")
    print(f"OK: ha {len(ha_pairs)}(人侧 {dict(hu)}) + aa {len(aa_pairs)} → v16_haaa_final.json")
    for duel in QUOTA_AA:
        c = collections.Counter(p["A"]["model"] for p in out if p.get("duel") == duel)
        print(f"  {duel}: {len(got_by_duel[duel])} 局, A侧 {dict(c)}")
    arm_use = collections.Counter(p["A"]["model"] if p["A"]["src"]=="ai" else p["B"]["model"] for p in out if p["kind"]=="ha")
    print("  ha 臂分布:", dict(arm_use))
