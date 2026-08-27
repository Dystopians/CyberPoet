"""对 audit_package 逐条审计。
剔除 → 行内加 "reject": 理由；修复 → 改 body 并留 "body_orig" + "fix"。
只动包内文件。"""
import json, glob, re, html, collections, shutil, os, sys
sys.path.insert(0,"/data/peilincai/CyberPoetTraining/claude_parallel_20260825/pylibs")
from opencc import OpenCC
cc=OpenCC('t2s')
D="/data/peilincai/CyberPoetTraining/claude_night_20260827/audit_package"
han=lambda t: len(re.findall(r"[一-鿿]",t))
lat=lambda t: len(re.findall(r"[A-Za-zÀ-ÿЀ-ӿ]",t))

files=sorted(glob.glob(f"{D}/poets/*.jsonl"))+sorted(glob.glob(f"{D}/poets_delta_*/*.jsonl"))
allrows=[]
for f in files:
    for i,l in enumerate(open(f)):
        r=json.loads(l); r["_f"]=f; r["_i"]=i; allrows.append(r)

# ── 1. 外文正文 ──
for r in allrows:
    h,l=han(r["body"]), lat(r["body"])
    if h+l>0 and h/(h+l) < 0.30:
        r["reject"]="非中文正文（原文或外语译本）"

# ── 2. 修复：HTML 实体 ──
ENT=re.compile(r"&(quot|amp|lt|gt|#0?39|apos|nbsp|#\d+);")
for r in allrows:
    if r.get("reject"): continue
    if ENT.search(r["body"]) or ENT.search(r.get("title") or ""):
        r.setdefault("body_orig", r["body"])
        r["body"]=html.unescape(r["body"])
        if r.get("title"): r["title"]=html.unescape(r["title"])
        r["fix"]=(r.get("fix","")+";HTML实体解码").strip(";")

# ── 3. 修复：剥离尾部元信息（注释/出处/译者署名/日期） ──
META=re.compile(r"^\s*(注[:：]|【附注】|附注[:：]|译注[:：]?\s*$|注\d+[:：]|选自|原载|译自|摘自|[（(]?\s*\S{2,6}\s*译\s*[)）]?\s*$|①|②|③)")
DATE=re.compile(r"^\s*\d{4}[\.\-年]\d{1,2}([\.\-月]\d{0,2}日?)?\s*$")
for r in allrows:
    if r.get("reject"): continue
    L=r["body"].split("\n")
    cut=len(L)
    # 从末尾往回，遇到元信息行就把切点前移；允许中间夹空行
    i=len(L)-1
    while i>=0:
        s=L[i].strip()
        if not s: i-=1; continue
        if META.match(s) or DATE.match(s): cut=i; i-=1; continue
        break
    if cut<len(L):
        body="\n".join(L[:cut]).rstrip()
        if han(body)>=10:
            r.setdefault("body_orig", r["body"]); r["body"]=body
            r["fix"]=(r.get("fix","")+";剥离尾部元信息").strip(";")

# ── 4. 修复：多首诗拼接（正文中间出现日期行且其后另起一首） ──
for r in allrows:
    if r.get("reject"): continue
    L=r["body"].split("\n")
    for i,ln in enumerate(L):
        if DATE.match(ln) and i < len(L)-3 and han("\n".join(L[:i]))>=40:
            after=[x for x in L[i+1:] if x.strip()]
            if len(after)>=3:
                r.setdefault("body_orig", r["body"])
                r["body"]="\n".join(L[:i]).rstrip()
                r["fix"]=(r.get("fix","")+";截断被拼接的下一首").strip(";")
            break

# ── 5. 修复：繁转简（逐字，转出生僻字则保留原字）──
def safe_t2s(t):
    out=[]
    for ch in t:
        c=cc.convert(ch)
        # opencc 会把「醲騞繻」等通用字映射到 CJK 扩展区，反而更生僻——保留原字
        if len(c)==1 and ord(c)>0x9FFF: c=ch
        out.append(c)
    return "".join(out)
for r in allrows:
    if r.get("reject"): continue
    s=safe_t2s(r["body"])
    if s!=r["body"]:
        r.setdefault("body_orig", r["body"]); r["body"]=s
        if r.get("title"): r["title"]=safe_t2s(r["title"])
        r["fix"]=(r.get("fix","")+";繁转简").strip(";")

# ── 6. 重复：同作者内正文归一后相同，保留一条 ──
key=lambda t: re.sub(r"[^一-鿿]","",t)[:80]
idx=collections.defaultdict(list)
for r in allrows:
    if r.get("reject"): continue
    k=key(r["body"])
    if len(k)>=25: idx[(r["author"],k)].append(r)
ndup=0
for (a,k),v in idx.items():
    if len(v)<2: continue
    v.sort(key=lambda r: (-han(r["body"]), -len(r.get("title") or ""), r.get("idx",0)))
    for r in v[1:]:
        r["reject"]=f"重复条目（保留 idx={v[0].get('idx')}《{v[0]['title']}》）"; ndup+=1

# ── 6b. 近重复：同作者内正文相似度 ≥0.93（如「石头/石块」「庞培/庞贝」这类一字之差）──
import difflib
byau=collections.defaultdict(list)
for r in allrows:
    if not r.get("reject") and han(r["body"])>=25: byau[r["author"]].append(r)
for a,rs in byau.items():
    rs.sort(key=lambda r: -han(r["body"]))
    for i,x in enumerate(rs):
        if x.get("reject"): continue
        kx=re.sub(r"[^一-鿿]","",x["body"])
        for y in rs[i+1:]:
            if y.get("reject"): continue
            ky=re.sub(r"[^一-鿿]","",y["body"])
            if abs(len(kx)-len(ky))/max(len(kx),len(ky)) > 0.15: continue
            # 同诗异译是不同的中文文本，保留；只在近乎逐字相同时才判重复
            translated = bool(x.get("translator") or y.get("translator"))
            if translated and (x.get("translator") != y.get("translator")): continue
            thr = 0.98 if translated else 0.93
            if difflib.SequenceMatcher(None, kx, ky).ratio() >= thr:
                y["reject"]=f"近重复 {difflib.SequenceMatcher(None,kx,ky).ratio():.3f}（保留 idx={x.get('idx')}《{x['title']}》）"; ndup+=1

# ── 写出 ──
os.makedirs(f"{D}/../audit_backup", exist_ok=True)
stat=collections.Counter()
bygroup=collections.defaultdict(list)
for r in allrows: bygroup[r["_f"]].append(r)
for f in files:
    tag = "delta1" if "poets_delta_1" in f else "main"
    bdir = f"{D}/../audit_backup" if tag=="main" else f"{D}/../audit_backup_delta1"
    os.makedirs(bdir, exist_ok=True)
    if not os.path.exists(f"{bdir}/{os.path.basename(f)}"):
        shutil.copy(f, f"{bdir}/{os.path.basename(f)}")
    rs=sorted(bygroup[f], key=lambda r: r["_i"])
    with open(f,"w") as out:
        for r in rs:
            r.pop("_f",None); r.pop("_i",None)
            if r.get("reject"): stat["剔除:"+r["reject"].split("（")[0]]+=1
            if r.get("fix"):
                for x in r["fix"].split(";"): stat["修复:"+x]+=1
            r["chars"]=han(r["body"])
            out.write(json.dumps(r, ensure_ascii=False)+"\n")
print(f"处理 {len(allrows)} 条")
for k,v in sorted(stat.items(), key=lambda x:-x[1]): print(f"  {k}: {v}")
kept=[r for r in allrows if not r.get("reject")]
print(f"\n保留 {len(kept)} 条 / {sum(han(r['body']) for r in kept)} 字")
