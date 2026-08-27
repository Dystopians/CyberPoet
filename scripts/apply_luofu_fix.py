"""把 luofu_fixed.jsonl 的修复应用到语料。默认 dry-run，加 --write 才落盘。
不覆盖原文件，输出到 --out 指定的新文件。"""
import json, argparse, re
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument("--corpus", default="/data/peilincai/CyberPoetTraining/cyberpoet_v1/data/poetry_dataset_v0.3.0-trainfix1/all.jsonl")
ap.add_argument("--fixes",  default="/data/peilincai/CyberPoetTraining/claude_night_20260827/luofu_fixed.jsonl")
ap.add_argument("--out",    default="/data/peilincai/CyberPoetTraining/claude_night_20260827/all_luofu_fixed.jsonl")
ap.add_argument("--only-transplanted", action="store_true", help="只应用移植分节的 137 首，不应用压平的 372 首")
ap.add_argument("--write", action="store_true")
a=ap.parse_args()
fixes={x["id"]:x for x in (json.loads(l) for l in open(a.fixes))}
if a.only_transplanted:
    fixes={k:v for k,v in fixes.items() if v["how"].startswith("移植")}
n=0; rows=[]
for l in open(a.corpus):
    r=json.loads(l); f=fixes.get(r["id"])
    if f:
        assert re.sub(r"[^一-鿿]","",r["text"])==re.sub(r"[^一-鿿]","",f["text_orig"]), f"正文不匹配 {r['id']}"
        r["text"]=f["text_fixed"]; r["blankline_fix"]=f["how"]; n+=1
        if "integrity" in r and isinstance(r["integrity"],dict):
            import hashlib
            r["integrity"]["text_sha256"]=hashlib.sha256(f["text_fixed"].encode()).hexdigest()
    rows.append(r)
print(f"将修复 {n} 首（共 {len(rows)} 条）")
if a.write:
    with open(a.out,"w") as o:
        for r in rows: o.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"写出 {a.out}")
else:
    print("dry-run，未落盘；加 --write 生效")
