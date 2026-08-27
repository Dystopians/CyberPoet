"""修复旧语料中洛夫的「超级空行」（每行之间一个空行，来自 luofu.epub 的排版事故）。
优先用 PoemWiki 版的真实分节移植；配不上的只能压平。
只写新文件，不改 codex 的树。"""
import json, re, difflib, collections
from pathlib import Path
OLD=Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1/data/poetry_dataset_v0.3.0-trainfix1/all.jsonl")
NEW=Path("/data/peilincai/CyberPoetTraining/claude_night_20260827/audit_package/poets/洛夫.jsonl")
OUT=Path("/data/peilincai/CyberPoetTraining/claude_night_20260827/luofu_fixed.jsonl")
key=lambda t: re.sub(r"[^一-鿿]","",t)
LN=lambda t: [x.strip() for x in t.split("\n") if x.strip()]
def dbl(t):
    ls=t.split("\n"); ne=[i for i,x in enumerate(ls) if x.strip()]
    return len(ne)>=4 and all(ne[i+1]-ne[i]==2 for i in range(len(ne)-1))
def breaks(t):
    """返回 PoemWiki 版在第几行之后有空行（0-based，指该行之后断节）"""
    out=set(); n=-1
    ls=t.split("\n")
    for i,x in enumerate(ls):
        if x.strip(): n+=1
        elif n>=0 and i+1<len(ls) and any(y.strip() for y in ls[i+1:]):
            out.add(n)
    return out

old=[json.loads(l) for l in open(OLD)]
new=[json.loads(l) for l in open(NEW)]
new=[r for r in new if not r.get("reject")]
nk=[(key(r["body"]), r) for r in new]
stat=collections.Counter(); recs=[]
for r in old:
    if r["author"]!="洛夫" or not dbl(r["text"]):
        continue
    a=LN(r["text"]); k=key(r["text"])
    best=None; bs=0
    for k2,r2 in nk:
        if abs(len(k2)-len(k))/max(len(k2),len(k))>0.12: continue
        s=difflib.SequenceMatcher(None,k,k2).ratio()
        if s>bs: bs,best=s,r2
    fixed=None; how=None
    if best and bs>=0.93:
        b=LN(best["body"]); br=breaks(best["body"])
        if len(a)==len(b) and all(key(a[i])==key(b[i]) for i in range(len(a))):
            how="移植分节(逐行一致)"
        else:
            # 用行级对齐把断节位置映射到旧版行号
            sm=difflib.SequenceMatcher(None,[key(x) for x in b],[key(x) for x in a])
            m={}
            for i1,j1,n in sm.get_matching_blocks():
                for d in range(n): m[i1+d]=j1+d
            if len(m) >= 0.8*len(b):
                br={m[i] for i in br if i in m}; how="移植分节(对齐后)"
        if how:
            out=[]
            for i,ln in enumerate(a):
                out.append(ln)
                if i in br: out.append("")
            fixed="\n".join(out).strip()
    if not fixed:
        fixed="\n".join(a); how="仅压平(无对照源)"
    stat[how]+=1
    recs.append({"id":r["id"],"author":r["author"],"title":r.get("title"),
                 "how":how,"match":round(bs,3) if best else None,
                 "lines":len(a),
                 "stanzas_before":len(a),  # 超级空行下每行即一节
                 "stanzas_after":len([x for x in re.split(r"\n\s*\n",fixed) if x.strip()]),
                 "text_fixed":fixed,"text_orig":r["text"]})
with open(OUT,"w") as f:
    for x in recs: f.write(json.dumps(x,ensure_ascii=False)+"\n")
print(f"处理 {len(recs)} 首")
for k,v in stat.most_common(): print(f"  {k}: {v}")
tr=[x for x in recs if x["how"].startswith("移植")]
print(f"\n移植分节的 {len(tr)} 首，节数分布: {collections.Counter(x['stanzas_after'] for x in tr).most_common(8)}")
print(f"写出 {OUT}")
