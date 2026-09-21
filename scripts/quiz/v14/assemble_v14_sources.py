# v14 素材装配（派生自 v13）：ha 金标候选 48（终选 24）+ aa 命题候选 96（终选 ≤64）。先于 SFT v5 建库：这些题与正文从 M8 的桥数据里排除。
# 08-31 主人裁决：不规避名篇（FAMOUS 不再做门）；其余纪律照旧（登记表+10字窗、60–340、无拉丁、跳顾城/译诗）。
# 规则：登记表+10字窗模糊全查重；名诗黑名单（含 ha 人侧，08-28 裁决）；60-340字；
#       无拉丁≥3/．；跳过顾城；aa 题避开古典名句式标题（昨夜星辰教训）与名诗题。
import json, re, glob, collections, random
from v5_lib import norm, chars, flagged, suihang
from fix_v75 import FAMOUS, TRANSLATED, SKIP_AUTHORS, full_grams

used = set(json.load(open('used_bodies.json')))
pool, seen = [], set()
for r in (json.loads(l) for l in open('../corpus_clean/base_fixed/all.jsonl')):
    k = norm(r["text"])
    if k in seen: continue
    seen.add(k); pool.append({"author": r["author"], "title": r.get("title",""), "body": r["text"]})
for fp in glob.glob('../corpus_clean/poets_v2/*.jsonl'):
    for r in (json.loads(l) for l in open(fp)):
        k = norm(r["body"])
        if k in seen: continue
        seen.add(k); pool.append({"author": r["author"], "title": r.get("title",""), "body": r["body"]})

from fix_v75 import FAMOUS
FAMOUS_TITLES = {x[1] if isinstance(x, tuple) else x for x in FAMOUS}
PAST_AA = set()
for f in ("v7_pairs_final.json","v8_pairs_final.json","v9_pairs_final.json","v10b_pairs_final.json","v11_pairs_final.json","v12_pairs_final.json","v13_pairs_final.json"):
    PAST_AA |= {p["title"] for p in json.load(open(f)) if p.get("kind") == "aa"}
used_grams = set()
for b in used:
    for i in range(max(len(b)-9, 1)): used_grams.add(b[i:i+10])

for f in ("v7_pairs_final.json","v8_pairs_final.json","v9_pairs_final.json","v10b_pairs_final.json","v11_pairs_final.json","v12_pairs_final.json","v13_pairs_final.json"):
    PAST_AA |= {p["title"] for p in json.load(open(f)) if p.get("kind") == "ha" and p.get("title")}
CLASSICAL = re.compile(r"[，。]")  # 标题含句读的古典引句式一律避开
def ok(p, need_title=True):
    a, t, b = p["author"], p["title"], p["body"].strip()
    if a in SKIP_AUTHORS or a in TRANSLATED: return False
    if need_title and (not t or len(t) > 14 or CLASSICAL.search(t) or "无题" in t or t in PAST_AA or any(ft in t for ft in FAMOUS_TITLES if len(ft) >= 3)): return False   # 第十一卷起：极著名诗题不做 AI 命题（09-02 乡愁事故）
    c = chars(b)
    if not (60 <= c <= 340): return False
    if len(re.findall(r"[A-Za-z]", b)) >= 3 or "．" in b: return False
    if flagged(b): return False
    if norm(b) in used: return False
    if full_grams(b) & used_grams: return False
    return True

random.seed(140001)
cands = [p for p in pool if ok(p)]
random.shuffle(cands)
# ha 金标：强文本诗人优先（面板与既证强者），每人≤4；aa 命题：题目池打散，作者≤3
HA_PREF = ["昌耀","张枣","陈舸","多多","西川","柏桦","臧棣","马雁","韩东","商禽","痖弦","洛夫","海子","余怒","翟永明","杨炼","戈麦","骆一禾","陆忆敏","张执浩","韩博","王敖","于坚"]
rank = {a: i for i, a in enumerate(HA_PREF)}
cands.sort(key=lambda p: rank.get(p["author"], 99))
ha, aa, cnt_ha, cnt_aa = [], [], collections.Counter(), collections.Counter()
taken = set()
for p in cands:
    a = p["author"]; k = norm(p["body"])
    if k in taken: continue
    if len(ha) < 48 and cnt_ha[a] < 4:
        ha.append(p); cnt_ha[a] += 1; taken.add(k); continue
    if len(aa) < 96 and cnt_aa[a] < 5:
        aa.append(p); cnt_aa[a] += 1; taken.add(k)
    if len(ha) >= 48 and len(aa) >= 96: break

json.dump({"ha": ha, "aa": [{"author": p["author"], "title": p["title"]} for p in aa]},
          open('v14_sources_proposed.json', 'w'), ensure_ascii=False, indent=1)
with open('v14_ha审读稿.txt', 'w') as f:
    for i, p in enumerate(ha):
        f.write(f"\n{'='*46}\n[ha{i}] {p['author']}《{p['title']}》 {chars(p['body'])}字\n{p['body'].strip()}\n")
    f.write("\n\n==== aa 命题候选（只用题，不用正文；避免与金标同题）====\n")
    for i, p in enumerate(aa):
        f.write(f"[aa{i}] {p['author']}《{p['title']}》\n")
print(f"ha 金标候选 {len(ha)}（{dict(cnt_ha)}）; aa 命题候选 {len(aa)}")
print("→ v14_ha审读稿.txt 待逐首人工读")
