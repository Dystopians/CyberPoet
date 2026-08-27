"""把四档轮数对照做成两选一配对：每题 2 对，同题内不重用同一首。"""
import json, random, re, hashlib, collections, itertools
from pathlib import Path
W=Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
rows=[json.loads(l) for l in open(W/"vocab_probe/gens_epoch_sweep.jsonl")]
CONDS=["pt_sft","M1_e4","M1_e5","M1_e7"]
# 六种搭配轮转，保证每种出现次数均等，且同一题内两对不共用同一首
ROT=[(("pt_sft","M1_e4"),("M1_e5","M1_e7")),
     (("pt_sft","M1_e5"),("M1_e4","M1_e7")),
     (("pt_sft","M1_e7"),("M1_e4","M1_e5"))]
rng=random.Random(20260827)
def grams(t):
    f=re.sub(r"[^一-鿿]","",t); return {f[i:i+4] for i in range(max(0,len(f)-3))}
def near(x,y,thr=.8):
    a,b=grams(x),grams(y); return bool(a and b) and len(a&b)/len(a|b)>=thr
gid=lambda pk,m,b: hashlib.sha256(f"{pk}|{m}|{b}".encode()).hexdigest()[:16]
pairs=[]
for i,r in enumerate(rows):
    for m1,m2 in ROT[i%3]:
        a,b=r.get(m1,""),r.get(m2,"")
        if len(a)<20 or len(b)<20 or near(a,b): continue
        x={"gen_id":gid(r["id"],m1,a),"model":m1,"body":a}
        y={"gen_id":gid(r["id"],m2,b),"model":m2,"body":b}
        if rng.random()<.5: x,y=y,x
        pairs.append({"prompt_key":r["id"],"prompt":r["prompt"],"A":x,"B":y})
rng.shuffle(pairs)
json.dump(pairs, open(W/"vocab_probe/pairs_M1.json","w"), ensure_ascii=False, indent=1)
c=collections.Counter(tuple(sorted((p["A"]["model"],p["B"]["model"]))) for p in pairs)
print(f"共 {len(pairs)} 对，覆盖 {len({p['prompt_key'] for p in pairs})} 道题")
for k,v in c.most_common(): print(f"  {k[0]} vs {k[1]}: {v}")
ids=[p[s]["gen_id"] for p in pairs for s in ("A","B")]
print(f"重复使用的生成 {sum(1 for i in set(ids) if ids.count(i)>1)} 条")
