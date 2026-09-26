# v16 审读稿生成（09-21，盲读版）：过闸候选按槽分组，**不显示臂名、不显示质感分、不显示预分配**，槽内各臂候选打乱成匿名编号 c1、c2…，
# 供总控逐首通读，只做客观否决（题献/伪造出处/点名真人/化用名句/退化/回显/错字）。编号↔臂的对照存 v16_blind_key.json，读完再对回。
# 依据：09-16 复核发现读稿否决不盲（v12 对 M7 臂否决率是 M7F 的 2.7 倍）。
# 臂位中立规则（v8 纪律）：按槽号 sha256 定序轮转分配，与候选质量无关；读稿前锁定写入 v16_slot_proposal.json。
import json, hashlib, collections, sys
sys.path.insert(0, '.')
from v5_lib import chars

GATED = json.load(open('v16_gen_gated.json'))
SRC = json.load(open('v16_sources_proposed.json'))
GV = json.load(open('v16_gold_verdicts.json'))
AA_DROP = set(GV['drop_aa']); HA_DROP = {int(x[2:]) for x in GV['drop_ha']}
ha_slots = [f"ha{i}" for i in range(len(SRC["ha"])) if i not in HA_DROP]
aa_slots = [f"aa{i}" for i in range(len(SRC["aa"])) if i not in AA_DROP]

# ---- ha 臂位预分配：M4P×10 / M4×10（20 槽 + 后备）----
from v16_arms import ARMS, DUEL_A, DUEL_B, DUEL_C, QUOTA_HA, QUOTA_AA, MAIN
order = sorted(ha_slots, key=lambda s: hashlib.sha256(("v16ha" + s).encode()).hexdigest())
plan = [MAIN] * QUOTA_HA[MAIN] + ["M4"] * QUOTA_HA["M4"] + ["备"] * max(0, len(order) - 20)
HA_PLAN = dict(zip(order, plan))
# ---- aa 对决预分配：M4PvsM4×28 ----
order2 = sorted(aa_slots, key=lambda s: hashlib.sha256(("v16aa" + s).encode()).hexdigest())
_fixed = [DUEL_A] * QUOTA_AA[DUEL_A]
duels = _fixed + ["备"] * (len(order2) - len(_fixed))
AA_PLAN = dict(zip(order2, duels))
json.dump({"ha": HA_PLAN, "aa": AA_PLAN}, open('v16_slot_proposal.json', 'w'), ensure_ascii=False, indent=1)

out = open('v16_审读稿.txt', 'w'); key = {}; n_c = 0
for sid in ha_slots + aa_slots:
    kind, idx = sid[:2], int(sid[2:]); src = SRC[kind][idx]
    items = [(arm, c) for arm in ARMS for c in GATED.get(f"{sid}|{arm}", [])]
    items.sort(key=lambda x: hashlib.sha256(f"v16blind|{sid}|{x[0]}|{x[1]['seed']}".encode()).hexdigest())
    out.write(f"\n{'='*70}\n## {sid} 《{src['title']}》\n")
    for j, (arm, c) in enumerate(items, 1):
        n_c += 1; key[f"{sid}|c{j}"] = [arm, c["seed"]]
        out.write(f"\n--- {sid}|c{j} {chars(c['body'])}字 ---\n{c['body']}\n")
out.close()
json.dump(key, open('v16_blind_key.json', 'w'), ensure_ascii=False, indent=1)
print(f"盲读审读稿 {n_c} 首 → v16_审读稿.txt；编号对照 → v16_blind_key.json；臂位预分配 → v16_slot_proposal.json")
print("ha 计划:", dict(collections.Counter(HA_PLAN.values()))); print("aa 计划:", dict(collections.Counter(AA_PLAN.values())))
