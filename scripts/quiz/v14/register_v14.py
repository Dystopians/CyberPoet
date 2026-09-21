# v14 登记：把上卷的每一首（人、机两侧）记进 used_bodies.json，供以后各卷 10 字窗查重。
# 与 v13 做法相同：先备份 used_bodies_pre_v14.json；只加不删；重复执行无副作用。
import json, os, sys
sys.path.insert(0, '.')
from v5_lib import norm
used = json.load(open('used_bodies.json'))
if not os.path.exists('used_bodies_pre_v14.json'):
    json.dump(used, open('used_bodies_pre_v14.json', 'w'), ensure_ascii=False)
pairs = json.load(open('v14_pairs_final.json'))
bodies = [norm(q[s]["body"]) for q in pairs for s in "AB"]
assert len(set(bodies)) == len(bodies), "卷内有重复正文"
have = set(used); add = [b for b in bodies if b not in have]
json.dump(used + add, open('used_bodies.json', 'w'), ensure_ascii=False)
print(f"登记表 {len(used)} → {len(used) + len(add)}（本卷 {len(bodies)} 首，新增 {len(add)}）")
