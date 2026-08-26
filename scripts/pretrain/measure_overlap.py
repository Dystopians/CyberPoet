"""量一件事：模型写出来的诗，和语料里的原诗最长有多少字是逐字一样的。
用法：python measure_overlap.py 生成结果.jsonl   （每行一个 {"body": "..."}）
不是门禁，是刻度尺——用来看训练轮数推到第几轮时开始出现整句照抄。"""
import json, re, sys, collections
from pathlib import Path

D = Path("/data/peilincai/CyberPoet_poetry_dataset_v0.3.0/repository/poetry_dataset/splits")
corpus = []
for split in ("train", "validation", "test"):
    for l in open(D / f"{split}.jsonl"):
        r = json.loads(l)
        corpus.append((r["author"], r.get("title", ""), re.sub(r"\s", "", r["text"])))

N = 10  # 以 10 字为窗口建索引，能查出所有 ≥10 字的逐字重合
index = collections.defaultdict(list)
for i, (a, t, txt) in enumerate(corpus):
    for j in range(len(txt) - N + 1):
        index[txt[j:j + N]].append((i, j))

def longest_overlap(gen):
    g = re.sub(r"\s", "", gen)
    best = (0, None)
    for j in range(len(g) - N + 1):
        for (i, k) in index.get(g[j:j + N], []):
            txt = corpus[i][2]
            n = N
            while j + n < len(g) and k + n < len(txt) and g[j + n] == txt[k + n]:
                n += 1
            if n > best[0]:
                best = (n, (corpus[i][0], corpus[i][1], g[j:j + n]))
    return best

if __name__ == "__main__":
    rows = [json.loads(l) for l in open(sys.argv[1])]
    results = []
    for r in rows:
        body = r.get("body") or r.get("best_draft") or r.get("text", "")
        n, hit = longest_overlap(body)
        results.append(n)
        if n >= 20:
            print(f"⚠ 逐字重合 {n} 字 ← {hit[0]}《{hit[1]}》：{hit[2][:60]}")
    results.sort()
    print(f"\n共 {len(results)} 条：最长重合 {max(results)} 字，中位 {results[len(results)//2]} 字，"
          f"≥20 字的 {sum(1 for x in results if x >= 20)} 条，≥50 字的 {sum(1 for x in results if x >= 50)} 条")
