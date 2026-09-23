# v15 素材装配（派生自 v14，09-22）：ha 金标候选 48（终选 24）+ aa 命题候选 96（终选 60）。四臂都在 M4 的底座上（M4 / M4R / M4Rw / M4sft），
# 出卷题与金标避开 M4 系的训练题面与目标正文：桥数据 sft_train_v3、dpo_v1（dpo_train.json）、dpo_v6（M4R 的偏好数据）；并避开 v7–v14 全部用过的题。
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
for f in ("v7_pairs_final.json","v8_pairs_final.json","v9_pairs_final.json","v10b_pairs_final.json","v11_pairs_final.json","v12_pairs_final.json","v13_pairs_final.json","v14_pairs_final.json"):
    PAST_AA |= {p["title"] for p in json.load(open(f)) if p.get("kind") == "aa"}
used_grams = set()
for b in used:
    for i in range(max(len(b)-9, 1)): used_grams.add(b[i:i+10])

for f in ("v7_pairs_final.json","v8_pairs_final.json","v9_pairs_final.json","v10b_pairs_final.json","v11_pairs_final.json","v12_pairs_final.json","v13_pairs_final.json","v14_pairs_final.json"):
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

# （v14 历史注记）09-21 21:55 重抽（v14b）：M8 的桥改用上一代 sft_pt9b（桥数据 v4），出卷题与金标必须同时避开 v4 与 v5 的训练题面和目标正文（第一次抽样只避了 v5，结果 40 首金标里 38 首在 v4 里、84 道命题 71 道在 v4 里）。
TRAIN_TITLES, TRAIN_GRAMS = set(), set()
for _f in ("../data/sft_train_v3.json", "../data/dpo_train.json", "../data/dpo_train_v6.json"):
    for _r in json.load(open(_f)):
        _m = re.search(r"《(.+?)》", _r.get("instruction", ""))
        if _m: TRAIN_TITLES.add(_m.group(1).strip())
        for _k in ("output", "chosen", "rejected", "input"):
            if _r.get(_k): TRAIN_GRAMS |= full_grams(_r[_k])
_ok0 = ok
def ok(p, need_title=True):
    if not _ok0(p, need_title): return False
    if p["title"].strip() in TRAIN_TITLES: return False
    if len(full_grams(p["body"]) & TRAIN_GRAMS) >= 3: return False
    return True
random.seed(150001)
cands = [p for p in pool if ok(p)]
random.shuffle(cands)
# ha 金标：强文本诗人优先（面板与既证强者），每人≤4；aa 命题：题目池打散，作者≤3
HA_PREF = ["昌耀","张枣","陈舸","多多","西川","柏桦","臧棣","马雁","韩东","商禽","痖弦","洛夫","海子","余怒","翟永明","杨炼","戈麦","骆一禾","陆忆敏","张执浩","韩博","王敖","于坚"]
rank = {a: i for i, a in enumerate(HA_PREF)}
cands.sort(key=lambda p: rank.get(p["author"], 99))
# aa 命题只用题不用正文：放宽到「题面合规 + 题不在训练题里 + 该题的原诗正文不在训练集里」（含外译诗人的题；字数/拉丁字母等正文门槛不适用）
def ok_aa(p):
    a, t, b = p["author"], p["title"], p["body"].strip()
    if a in SKIP_AUTHORS: return False
    if not t or len(t) > 14 or CLASSICAL.search(t) or "无题" in t or t in PAST_AA or any(ft in t for ft in FAMOUS_TITLES if len(ft) >= 3): return False
    if len(re.findall(r"[A-Za-z]", t)) >= 1: return False
    if t.strip() in TRAIN_TITLES: return False
    if len(full_grams(b) & TRAIN_GRAMS) >= 3: return False
    if norm(b) in used or (full_grams(b) & used_grams): return False
    return True
aa_pool = [p for p in pool if ok_aa(p)]
random.shuffle(aa_pool)
ha, aa, cnt_ha, cnt_aa = [], [], collections.Counter(), collections.Counter()
taken = set()
for p in cands:
    a = p["author"]; k = norm(p["body"])
    if k in taken: continue
    if len(ha) < 48 and cnt_ha[a] < 4:
        ha.append(p); cnt_ha[a] += 1; taken.add(k); continue
    if len(ha) >= 48: break
ha_titles = {p["title"] for p in ha}
for p in aa_pool:
    a = p["author"]; k = norm(p["body"])
    if k in taken or p["title"] in ha_titles: continue
    if len(aa) < 96 and cnt_aa[a] < 5:
        aa.append(p); cnt_aa[a] += 1; taken.add(k)
    if len(aa) >= 96: break

json.dump({"ha": ha, "aa": [{"author": p["author"], "title": p["title"]} for p in aa]},
          open('v15_sources_proposed.json', 'w'), ensure_ascii=False, indent=1)
with open('v15_ha审读稿.txt', 'w') as f:
    for i, p in enumerate(ha):
        f.write(f"\n{'='*46}\n[ha{i}] {p['author']}《{p['title']}》 {chars(p['body'])}字\n{p['body'].strip()}\n")
    f.write("\n\n==== aa 命题候选（只用题，不用正文；避免与金标同题）====\n")
    for i, p in enumerate(aa):
        f.write(f"[aa{i}] {p['author']}《{p['title']}》\n")
print(f"ha 金标候选 {len(ha)}（{dict(cnt_ha)}）; aa 命题候选 {len(aa)}")
print("→ v15_ha审读稿.txt 待逐首人工读")
