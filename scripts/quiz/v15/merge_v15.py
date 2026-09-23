# v15 合卷：hh 24 + ha≤24 + aa≤60 → v15_pairs_final.json（全局乱序）
import json, random, collections
pairs = json.load(open('v15_hh_pairs.json')) + json.load(open('v15_haaa_final.json'))
assert 70 <= len(pairs) <= 108, len(pairs)   # v15：如实缺额
random.Random(1500900).shuffle(pairs)
json.dump(pairs, open('v15_pairs_final.json', 'w'), ensure_ascii=False, indent=1)
print(f'合卷 {len(pairs)}:', dict(collections.Counter(p['kind'] for p in pairs)))
