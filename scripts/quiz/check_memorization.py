"""零记忆核验（CPU，三臂通用）：任意生成 jsonl 对训练语料做 10 字窗重合扫描。
用法: python3 check_memorization.py <语料json> <gens.jsonl> [gens2.jsonl ...]
  语料 json 为 [{"text":...}] 列表（如 data/pt8_train.json）；gens 每行 {"title","seed","body",...}。
惯例：主人接受模型记住语料，但数字每轮必报；≥3 窗的逐条列出供人工核对是否成语/惯用语。
教训（v9）：只扫 M6 漏掉了 M5 一首化用海子 127 窗的候选——每臂都要扫。"""
import json, re, sys, collections
nsp = lambda t: re.sub(r'\s', '', t)
corpus_path, gens = sys.argv[1], sys.argv[2:]
corpus = set()
for r in json.load(open(corpus_path)):
    b = nsp(r['text']); corpus.update(b[i:i+10] for i in range(len(b)-9))
print(f"语料窗库: {len(corpus):,}（{corpus_path}）")
for f in gens:
    tot = hits = 0; worst = collections.Counter()
    for l in open(f):
        r = json.loads(l); b = nsp(r['body']); tot += 1
        n = sum(1 for i in range(len(b)-9) if b[i:i+10] in corpus)
        if n: hits += 1; worst[f"{r.get('title','?')}|seed{r.get('seed','?')}"] = n
    print(f"{f}: 生成 {tot} 首，含重合窗 {hits} 首")
    for k, v in worst.most_common(8):
        if v >= 3: print(f"  ≥3窗 {k}: {v}")
