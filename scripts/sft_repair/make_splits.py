"""把修好的数据切成训练/开发两份，按「来源诗」切，保证同一首诗不会同时出现在两边。"""
import json, hashlib, collections
from pathlib import Path
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/sft_repair")
OUT = W / "llamafactory"; OUT.mkdir(exist_ok=True)

rows = json.load(open(W / "sft_train_v2.json"))
meta = [json.loads(l) for l in open(W / "sft_train_v2.meta.jsonl")]
def dev_side(pid):  # 5% 进开发集，按诗的 id 哈希，确定可复现
    return int(hashlib.sha256(pid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < 0.05

tr, dv = [], []
for r, m in zip(rows, meta):
    (dv if dev_side(m["source_poem_id"]) else tr).append(r)
json.dump(tr, open(OUT / "sft_train.json", "w"), ensure_ascii=False, indent=1)
json.dump(dv, open(OUT / "sft_dev.json", "w"), ensure_ascii=False, indent=1)
cols = {"prompt": "instruction", "query": "input", "response": "output", "system": "system"}
json.dump({"cyberpoet_fixed_train": {"file_name": "sft_train.json", "columns": cols},
           "cyberpoet_fixed_dev": {"file_name": "sft_dev.json", "columns": cols}},
          open(OUT / "dataset_info.json", "w"), ensure_ascii=False, indent=1)
tr_ids = {m["source_poem_id"] for r, m in zip(rows, meta) if not dev_side(m["source_poem_id"])}
dv_ids = {m["source_poem_id"] for r, m in zip(rows, meta) if dev_side(m["source_poem_id"])}
print(f"训练 {len(tr)} 条（{len(tr_ids)} 首诗）  开发 {len(dv)} 条（{len(dv_ids)} 首诗）  两边重叠的诗：{len(tr_ids & dv_ids)}")
print("任务构成:", dict(collections.Counter(m["task"] for r, m in zip(rows, meta) if not dev_side(m["source_poem_id"]))))
