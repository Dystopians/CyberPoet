# v14 合卷：ha≤24 + aa≤56（无 hh）→ v14_pairs_final.json（全局乱序）
import json, random, collections
pairs = json.load(open('v14_haaa_final.json'))
assert 56 <= len(pairs) <= 80, len(pairs)   # v14：如实缺额
random.Random(1400900).shuffle(pairs)
json.dump(pairs, open('v14_pairs_final.json', 'w'), ensure_ascii=False, indent=1)
print(f'合卷 {len(pairs)}:', dict(collections.Counter(p['kind'] for p in pairs)))
