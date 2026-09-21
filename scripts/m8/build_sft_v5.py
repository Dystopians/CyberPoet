"""SFT 桥 v5（09-21 重组）。相对 v4 的改动，每条对应归因报告/复核记录里的一个发现：
  1. 去掉 600 条「续写」：它们的答案就是语料诗的后半段，纯背诵，推理时也用不到这种题面；
  2. 标题题面行重新抽样，排除：v14 卷的全部素材（金标 48 + 命题 96 的题名与正文）、出厂面板 66 题、复读实验 48 题
     ——保证出卷题与出厂检题都不在桥的训练集里（09-16 复核：旧口径下 48 题里 40 题在训练集内）；
  3. 目标正文剥掉首行题献、「——《总题》之N」式副题、带出处的题词（只动训练副本，不动语料）；
  4. 加入主人点名说好的 AI 诗 42 首（牌坊里的 AI 条目，去掉主人有保留的 3 首）做正面示例，题面=推理题面；
  5. 开发集换成干净的：从未进过预训练的留出诗 200 首做「题名→诗」，用来早停（旧开发集 80% 是预训练见过的诗）。
只加新文件：data/sft_train_v5.json / sft_dev_v5.json；dataset_info 只加不改。"""
import json, glob, re, random, collections, sys
sys.path.insert(0, "quiz_v3")
from fix_v75 import TRANSLATED
N = "/data/peilincai/CyberPoetTraining/claude_night_20260827"
SYS = open("/data/peilincai/CyberPoetTraining/cyberpoet_v1/prompts/poetry_system_v2.txt", encoding="utf-8").read().strip()
def norm(t): return re.sub(r"\s+", "", t)
def wins(t, k=10):
    f = norm(t); return {f[i:i+k] for i in range(max(0, len(f)-k+1))}

from poem_head_strip import strip_head, DED

# ---- 排除集 ----
S14 = json.load(open(f"{N}/quiz_v3/v14_sources_proposed.json"))
EX_TITLES = {p["title"].strip() for p in S14["ha"]} | {p["title"].strip() for p in S14["aa"]}
EX_TITLES |= {s["title"].strip() for s in json.load(open(f"{N}/quiz_v3/v7_ha_sources.json"))}
EX_TITLES |= {p["title"].strip() for p in json.load(open(f"{N}/quiz_v3/v12_sources_proposed.json"))["aa"][:48]}
EXW = set()
for p in S14["ha"]: EXW |= wins(p["body"])
used = json.load(open(f"{N}/quiz_v3/used_bodies.json")); UW = set().union(*[wins(b) for b in used])
TRAINW = set()
for r in json.load(open(f"{N}/data/pt9_s1.json")): TRAINW |= wins(r["text"])

pool, seen = [], set()
for r in (json.loads(l) for l in open(f"{N}/corpus_clean/base_fixed/all.jsonl")):
    k = norm(r["text"])
    if k in seen: continue
    seen.add(k); pool.append({"author": r["author"], "title": r.get("title", ""), "body": r["text"]})
rem = {json.loads(l)["uid"] for l in open(f"{N}/corpus_clean/剔除明细.jsonl")}
for fp in glob.glob(f"{N}/corpus_clean/poets_v2/*.jsonl"):
    for r in (json.loads(l) for l in open(fp)):
        if r.get("uid") in rem or r.get("origin") not in (None, "zh_orig"): continue
        k = norm(r["body"])
        if k in seen: continue
        seen.add(k); pool.append({"author": r["author"], "title": r.get("title", ""), "body": r["body"]})
def basic_ok(p):
    a, t, b = p["author"], p["title"].strip(), p["body"].strip()
    if a == "顾城" or a in TRANSLATED: return False
    if not t or len(t) > 30 or len(re.findall(r"[A-Za-z]", t)) >= 3: return False
    if not (60 <= len(norm(b)) <= 800) or len(re.findall(r"[A-Za-z]", b)) >= 3: return False
    return True
train_pool, heldout = [], []
for p in pool:
    if not basic_ok(p): continue
    w = wins(p["body"])
    in_train = len(w & TRAINW) >= max(3, len(w) // 2)
    if not in_train: heldout.append(p); continue          # 从未进过预训练（dev/test 隔离）→ 只做开发集
    if p["title"].strip() in EX_TITLES or (w & EXW) or (w & UW): continue
    train_pool.append(p)
print(f"语料池 {len(pool)}；可做训练标题行 {len(train_pool)}（诗人 {len({p['author'] for p in train_pool})}）；留出诗 {len(heldout)}")

old = [r for r in json.load(open(f"{N}/data/sft_train_v3.json")) if not r["instruction"].startswith("续写")]
meta = [json.loads(l) for l in open("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/sft_repair/sft_train_v2.meta.jsonl")]
NAME = {"luofu":"洛夫","changyao":"昌耀","duoduo":"多多","haizi":"海子","shangqin":"商禽","mudan":"穆旦","zhangzao":"张枣","bianzhilin":"卞之琳","yaxian":"痖弦","chengge":"陈舸","fengzhi":"冯至","wangwei":"王炜"}
old_cnt = collections.Counter()
for m in meta:
    if m.get("task") == "prefix_completion": continue
    mm = re.match(r"poem-([a-z]+)", str(m.get("source_poem_id"))); old_cnt[NAME.get(mm.group(1), "?")] += 1
tot_meta = sum(old_cnt.values()); old_cnt = collections.Counter({k: round(v * len(old) / tot_meta) for k, v in old_cnt.items()})

random.seed(20260921); random.shuffle(train_pool)
by = collections.defaultdict(list)
for p in train_pool: by[p["author"]].append(p)
TARGET = 2400; CAP = int((len(old) + min(TARGET, len(train_pool))) * 0.145)   # 单家 ≤15%（留一点余量）
rows, add_cnt = [], collections.Counter(); authors = sorted(by, key=lambda a: -len(by[a])); ptr = {a: 0 for a in authors}
while len(rows) < TARGET:
    moved = False
    for a in authors:
        if ptr[a] >= len(by[a]) or old_cnt[a] + add_cnt[a] >= CAP: continue
        p = by[a][ptr[a]]; ptr[a] += 1; moved = True
        t = p["title"].strip(); instr = f"以《{t}》为题写一首现代诗。" if random.random() < 0.8 else f"写一首题为《{t}》的现代诗。"
        rows.append({"instruction": instr, "input": "", "output": p["body"].strip(), "system": SYS}); add_cnt[a] += 1
        if len(rows) >= TARGET: break
    if not moved: break

# 主人点名说好的 AI 诗
E = json.load(open(f"{N}/quiz_v3/好诗牌坊_entries.json")); SKIP = {("v9", 4), ("v9", 18), ("v10b", 106)}
liked = []
for e in E:
    if e.get("human") or (e["ver"], e["i"]) in SKIP: continue
    b = e["body"].strip()
    if DED.match(b.split("\n")[0].strip()): continue
    liked.append({"instruction": f"以《{e['title']}》为题写一首现代诗。", "input": "", "output": b, "system": SYS})
print("主人点名说好的 AI 诗:", len(liked))

train = old + rows + liked
chg = collections.Counter()
for r in train:
    o, c = strip_head(r["output"])
    if c: r["output"] = o; chg[c] += 1
random.shuffle(train)
random.seed(7); random.shuffle(heldout)
# 09-21 补：留出诗只对预训练隔离还不够——旧的简报/重写行来自 8 月的早期语料，里面有预训练没收、却在桥训练集里的诗（实测 1 首全同、4 首部分重合）。
# 开发集再过一道：与桥训练集任何一条回答共享 ≥3 个 10 字窗的留出诗不进开发集。训练集不受影响（逐字节不变）。
SFTW = set()
for r in train: SFTW |= wins(r["output"])
_n0 = len(heldout); heldout = [p for p in heldout if len(wins(p["body"]) & SFTW) < 3]
print(f"留出诗与桥训练集重合而剔出开发集候选: {_n0 - len(heldout)}")
dev = [{"instruction": f"以《{p['title'].strip()}》为题写一首现代诗。", "input": "", "output": strip_head(p["body"].strip())[0], "system": SYS} for p in heldout[:200]]
json.dump(train, open(f"{N}/data/sft_train_v5.json", "w"), ensure_ascii=False, indent=1)
json.dump(dev, open(f"{N}/data/sft_dev_v5.json", "w"), ensure_ascii=False, indent=1)
tot = old_cnt + add_cnt
print(f"训练 {len(train)} = 旧(简报+重写) {len(old)} + 标题行 {len(rows)} + 主人点名 AI 诗 {len(liked)}；干净开发集 {len(dev)}；剥离 {dict(chg)}")
print("诗人分布前 12:", tot.most_common(12), "| 最大占比", round(max(tot.values()) / (len(old) + len(rows)), 3), "| 诗人数", len(tot))
ins = [r["instruction"] for r in train]; print("题面含《》的行占比", round(sum("《" in i for i in ins) / len(ins), 3))
info = json.load(open(f"{N}/data/dataset_info.json"))
for k, fn in (("cyberpoet_sft_v5_train", "sft_train_v5.json"), ("cyberpoet_sft_v5_dev", "sft_dev_v5.json")):
    info[k] = {"file_name": fn, "columns": {"prompt": "instruction", "query": "input", "response": "output", "system": "system"}}
json.dump(info, open(f"{N}/data/dataset_info.json", "w"), ensure_ascii=False, indent=1)
