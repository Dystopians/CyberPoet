"""把诗歌语料整理成继续预训练能直接用的格式。只读原数据集，不改动任何现有文件。"""
import json, re, hashlib
from pathlib import Path

SRC = Path("/data/peilincai/CyberPoet_poetry_dataset_v0.3.0/repository/poetry_dataset/splits")
OUT = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/pretrain/data")
OUT.mkdir(parents=True, exist_ok=True)

def load(split):
    return [json.loads(l) for l in open(SRC / f"{split}.jsonl")]

def keep(rec):
    """按数据集自带的 sample_weight 做确定性下采样。
    洛夫的权重是 0.8504，意思是他的诗按比例少放一部分，避免一个人占掉太多篇幅。"""
    w = float(rec.get("sample_weight", 1.0))
    if w >= 1.0:
        return True
    h = int(hashlib.sha256(rec["id"].encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return h < w

for split, name in (("train", "pt_train"), ("validation", "pt_dev")):
    rows = load(split)
    kept = [r for r in rows if keep(r)]
    out = [{"text": r["text"].strip()} for r in kept]
    (OUT / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    by_author = {}
    for r in kept:
        by_author[r["author"]] = by_author.get(r["author"], 0) + len(re.sub(r"\s", "", r["text"]))
    total = sum(by_author.values())
    print(f"{name}: 原始 {len(rows)} 首 → 保留 {len(kept)} 首，{total:,} 字")
    if split == "train":
        top = sorted(by_author.items(), key=lambda x: -x[1])[:4]
        for a, c in top:
            print(f"    {a}: {c:,} 字 = {c/total:.1%}")

(OUT / "dataset_info.json").write_text(json.dumps({
    "cyberpoet_pt_train": {"file_name": "pt_train.json", "columns": {"prompt": "text"}},
    "cyberpoet_pt_dev":   {"file_name": "pt_dev.json",   "columns": {"prompt": "text"}},
}, ensure_ascii=False, indent=1), encoding="utf-8")
print("已写出 dataset_info.json")
