"""按主人 2026-08-27 的意见重建评估/偏好采样题目集，替换 36 道人造命题：
  A. 原作命题（probes_title.jsonl）：直接以真实诗的标题命题，自带文学母版，
     阅读包可以把原作并排给主人对照。
  B. 有限意象（probes_imagery.jsonl）：从真实诗里抽 2 个具辨识度的意象名词，
     只给意象不给情节，不规定"具体发生的事"。
两集各 40 题，跨诗人均衡，选取确定性（种子固定）。"""
import json, re, random, collections, sys
from pathlib import Path

sys.path.insert(0, "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/pylibs")
import jieba.posseg as pseg
import jieba
jieba.setLogLevel(60)

SRC = Path("/data/peilincai/CyberPoet_poetry_dataset_v0.3.0/repository/poetry_dataset/splits/train.jsonl")
OUT = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/vocab_probe")
rng = random.Random(20260827)

rows = [json.loads(l) for l in open(SRC)]
by_author = collections.defaultdict(list)
for r in rows:
    t = (r.get("title") or "").strip()
    if not (2 <= len(t) <= 10):          # 太短/太长/无题的跳过
        continue
    if re.search(r"[0-9〇一二三四五六七八九十]+章|之[一二三四五六七八九十]|（|\(|\[|【", t):
        continue                          # 组诗分章、括号注记跳过
    if re.search(r"^[怀赠悼致寄别送挽]|先生|同志|女士|君$", t):
        continue                          # 赠答悼亡类指向具体人物，不适合做命题
    by_author[r["author"]].append(r)

authors = sorted(by_author, key=lambda a: -len(by_author[a]))
print("可用诗人：", {a: len(by_author[a]) for a in authors})

# ---- A. 原作命题：每位诗人轮流抽，共 40 题 ----
title_probes, used_titles = [], set()
i = 0
pools = {a: rng.sample(by_author[a], len(by_author[a])) for a in authors}
while len(title_probes) < 40:
    a = authors[i % len(authors)]
    i += 1
    while pools[a]:
        r = pools[a].pop()
        if r["title"] in used_titles:
            continue
        used_titles.add(r["title"])
        title_probes.append({
            "id": f"tp-{len(title_probes)+1:03d}",
            "instruction": f"以《{r['title']}》为题写一首现代诗。",
            "ref_id": r["id"], "ref_author": r["author"], "ref_title": r["title"],
            "provenance": "title_from_corpus_v1",
        })
        break

with open(OUT / "probes_title.jsonl", "w", encoding="utf-8") as f:
    for p in title_probes:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

# ---- B. 有限意象：从真实诗抽 2 个具辨识度名词 ----
KEEP = ("n", "ns", "nz", "s")
df = collections.Counter()
poem_nouns = []
for r in rows:
    ns = [w.word for w in pseg.cut(re.sub(r"\s+", " ", r["text"]))
          if w.flag in KEEP and len(w.word) >= 2]
    poem_nouns.append((r, ns))
    df.update(set(ns))

imagery_probes, seen_pairs = [], set()
cands = rng.sample(poem_nouns, len(poem_nouns))
for r, ns in cands:
    if len(imagery_probes) >= 40:
        break
    # 具辨识度 = 在语料 3~80 首里出现过（既不生僻到怪，也不烂大街）
    good = [w for w in dict.fromkeys(ns)
            if 3 <= df[w] <= 80 and w[0] != w[1]]   # 叠词多为误切
    if len(good) < 2:
        continue
    pair = tuple(sorted(rng.sample(good, 2)))
    if pair in seen_pairs:
        continue
    seen_pairs.add(pair)
    imagery_probes.append({
        "id": f"ip-{len(imagery_probes)+1:03d}",
        "instruction": f"写一首现代诗，其中出现「{pair[0]}」与「{pair[1]}」。",
        "ref_id": r["id"], "ref_author": r["author"],
        "provenance": "imagery_from_corpus_v1",
    })

with open(OUT / "probes_imagery.jsonl", "w", encoding="utf-8") as f:
    for p in imagery_probes:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"原作命题 {len(title_probes)} 题；有限意象 {len(imagery_probes)} 题")
for p in title_probes[:4]: print(" ", p["instruction"], f"←{p['ref_author']}")
for p in imagery_probes[:4]: print(" ", p["instruction"], f"←{p['ref_author']}")
