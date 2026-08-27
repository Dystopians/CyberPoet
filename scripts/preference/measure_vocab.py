"""词汇诊断的复现测量。与审核文档同一套口径：
  1. 机器口音：固定 10 词表，模型每万词 ÷ 语料每万词
  2. 缺失语域：固定 10 词表（语料 ≥5/万而模型 0 次）+ 11 个显著少用词，每万词率
  3. 诗人标志词覆盖：洛夫/海子/昌耀/穆旦 各取相对其余诗人最超用的 8 词，数命中
  4. 背诵护栏：与语料的最长逐字重合（10 字窗），高轮次 checkpoint 必查
词表 1、2 直接取自审核文档；标志词从带作者标签的 train split 现算（全条件共用一张表）。
"""
import json, re, sys, collections
from pathlib import Path

sys.path.insert(0, "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/pylibs")
import jieba
jieba.setLogLevel(60)

SRC = Path("/data/peilincai/CyberPoet_poetry_dataset_v0.3.0/repository/poetry_dataset/splits/train.jsonl")

ACCENT = ["碎玻璃", "台阶", "吞下", "裂缝", "咳嗽", "传来", "腹中", "尽头", "某种", "金属"]
MISSING = ["如果", "肉体", "多少", "她们", "草原", "歌唱", "永恒", "诗歌", "上帝", "这么"]
UNDERUSED = ["我们", "太阳", "你们", "死亡", "诗人", "头颅", "为了", "不能", "孤独", "痛苦", "历史"]
POETS = ["洛夫", "海子", "昌耀", "穆旦"]

def words_of(text):
    return [w for w in jieba.cut(re.sub(r"\s+", " ", text)) if re.search(r"[一-鿿]", w)]

# ---------- 语料侧 ----------
corpus = [json.loads(l) for l in open(SRC)]
corp_words = collections.Counter()
by_poet = collections.defaultdict(collections.Counter)
poet_df = collections.defaultdict(collections.Counter)   # 词在该诗人多少首不同的诗里出现
corp_text_all = []
for r in corpus:
    ws = words_of(r["text"])
    corp_words.update(ws)
    by_poet[r["author"]].update(ws)
    poet_df[r["author"]].update(set(ws))
    corp_text_all.append(re.sub(r"\s", "", r["text"]))
N_corp = sum(corp_words.values())

def per10k(cnt, n):
    return cnt / n * 10000 if n else 0.0

def signature(poet, k=8, min_cnt=8, min_df=3):
    # min_df：至少出现在该诗人 3 首不同的诗里，滤掉单篇复现与正字法怪词
    own, own_n = by_poet[poet], sum(by_poet[poet].values())
    rest = corp_words - own
    rest_n = N_corp - own_n
    scored = []
    for w, c in own.items():
        if c < min_cnt or len(w) < 2 or poet_df[poet][w] < min_df:
            continue
        ratio = (c / own_n) / ((rest.get(w, 0) + 0.5) / rest_n)
        scored.append((ratio, c, w))
    scored.sort(reverse=True)
    return [w for _, _, w in scored[:k]]

SIG = {p: signature(p) for p in POETS}

# 背诵护栏：语料 10 字窗集合
grams10 = set()
for t in corp_text_all:
    for i in range(len(t) - 9):
        grams10.add(t[i:i + 10])

def longest_overlap(body):
    t = re.sub(r"\s", "", body)
    best = run = 0
    i = 0
    while i <= len(t) - 10:
        if t[i:i + 10] in grams10:
            run = 10
            j = i + 10
            while j < len(t) and t[j - 9:j + 1] in grams10:
                run += 1; j += 1
            best = max(best, run)
            i = j
        else:
            i += 1
    return best

# ---------- 生成侧 ----------
gens = []
for path in sys.argv[1:]:
    gens += [json.loads(l) for l in open(path)]
by_cond = collections.defaultdict(list)
for g in gens:
    by_cond[g["cond"]].append(g)

corp_accent = {w: per10k(corp_words[w], N_corp) for w in ACCENT}
corp_missing = {w: per10k(corp_words[w], N_corp) for w in MISSING}
corp_under = {w: per10k(corp_words[w], N_corp) for w in UNDERUSED}

print(f"语料：{len(corpus)} 首 / {N_corp:,} 词次")
print("标志词表（现算，全条件共用）：")
for p in POETS:
    print(f"  {p}: {' '.join(SIG[p])}")
print()

hdr = ["条件", "n", "篇均字", "口音倍数(中位)", "口音每万", "缺失语域命中/10",
       "缺失每万", "少用每万", "标志词覆盖/32", "重合中位", "重合最大"]
print("\t".join(hdr))
for cond, rows in sorted(by_cond.items()):
    cnt = collections.Counter()
    n_words = 0
    chars = []
    overlaps = []
    for g in rows:
        ws = words_of(g["body"])
        cnt.update(ws)
        n_words += len(ws)
        chars.append(len(re.sub(r"\s", "", g["body"])))
        overlaps.append(longest_overlap(g["body"]))
    mults = []
    for w in ACCENT:
        m_rate = per10k(cnt[w], n_words)
        c_rate = corp_accent[w]
        if c_rate > 0:
            mults.append(m_rate / c_rate)
        elif m_rate > 0:
            mults.append(float("inf"))
    mults.sort()
    med_mult = mults[len(mults) // 2] if mults else 0
    accent_rate = per10k(sum(cnt[w] for w in ACCENT), n_words)
    miss_hit = sum(1 for w in MISSING if cnt[w] > 0)
    miss_rate = per10k(sum(cnt[w] for w in MISSING), n_words)
    under_rate = per10k(sum(cnt[w] for w in UNDERUSED), n_words)
    sig_cov = sum(1 for p in POETS for w in SIG[p] if cnt[w] > 0)
    chars.sort(); overlaps.sort()
    print("\t".join(str(x) for x in [
        cond, len(rows), chars[len(chars) // 2],
        f"{med_mult:.1f}", f"{accent_rate:.1f}",
        f"{miss_hit}", f"{miss_rate:.1f}", f"{under_rate:.1f}",
        sig_cov, overlaps[len(overlaps) // 2], overlaps[-1]]))

print()
print("参照（语料本身）：口音每万 "
      f"{per10k(sum(corp_words[w] for w in ACCENT), N_corp):.1f}，"
      f"缺失语域每万 {per10k(sum(corp_words[w] for w in MISSING), N_corp):.1f}，"
      f"少用词每万 {per10k(sum(corp_words[w] for w in UNDERUSED), N_corp):.1f}")
