# v16 合卷：hh 24 + ha≤24 + aa≤60 → v16_pairs_final.json（全局乱序）
import json, random, collections
pairs = json.load(open('v16_haaa_final.json'))
assert 30 <= len(pairs) <= 110, len(pairs)   # v16：ha ≤20 + aa ≤50（+ 标准局 ≤24）
random.Random(1600900).shuffle(pairs)
json.dump(pairs, open('v16_pairs_final.json', 'w'), ensure_ascii=False, indent=1)
print(f'合卷 {len(pairs)}:', dict(collections.Counter(p['kind'] for p in pairs)))
