"""pt10 末段数据 = pt9_s3（纯中文诗按权重面板加权 + 10% 回放）逐条剥掉首行题献/「——《总题》之N」副题/带出处的题词。
只动训练副本（读 data/pt9_s3.json 写 data/pt10_s3.json），不动语料。理由：三代模型读稿否决里题献/伪造出处一直是第一大类。"""
import json, collections
from poem_head_strip import strip_head
N = "/data/peilincai/CyberPoetTraining/claude_night_20260827"
d = json.load(open(f"{N}/data/pt9_s3.json")); chg = collections.Counter()
for r in d:
    if r.get("origin") != "zh_orig": continue
    o, c = strip_head(r["text"])
    if c: r["text"] = o; chg[c] += 1
json.dump(d, open(f"{N}/data/pt10_s3.json", "w"), ensure_ascii=False)
info = json.load(open(f"{N}/data/dataset_info.json")); info["cyberpoet_pt10_s3"] = {"file_name": "pt10_s3.json", "columns": {"prompt": "text"}}
json.dump(info, open(f"{N}/data/dataset_info.json", "w"), ensure_ascii=False, indent=1)
print("docs", len(d), "剥离", dict(chg))
