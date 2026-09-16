"""对照生成的形状统计：按 key 分组（rp / fmt），配对同题比较。"""
import json,re,sys,statistics as st,collections
f=sys.argv[1]; key=sys.argv[2]
def n(t): return len(re.sub(r"\s+","",t))
def lines(t): return [l for l in t.split("\n") if l.strip()]
rows=[json.loads(l) for l in open(f)]
by=collections.defaultdict(list)
for r in rows: by[str(r[key])].append(r)
def stats(b):
    ch=[n(x) for x in b]; ln=[len(lines(x)) for x in b]
    cpl=[st.median([n(l) for l in lines(x)]) for x in b if lines(x)]
    frag=[sum(1 for l in lines(x) if n(l)<=4)/len(lines(x)) for x in b if lines(x)]
    punct=[len(re.findall(r"[，。；：、！？]",x))/max(1,n(x))*100 for x in b]
    de=[x.count("的")/max(1,n(x))*100 for x in b]
    # distinct char ratio
    dr=[len(set(re.sub(r"\s","",x)))/max(1,n(x)) for x in b]
    maxrep=[max(collections.Counter(l.strip() for l in lines(x)).values()) if lines(x) else 0 for x in b]
    echo=sum(1 for x in b if re.match(r"^\s*(——|《|题目|以《)",x) )
    return dict(n=len(b),chars=st.median(ch),lines=st.median(ln),cpl=round(st.median(cpl),1),frag=round(st.mean(frag),3),punct=round(st.median(punct),1),de=round(st.median(de),2),distinct=round(st.median(dr),3),rep_lines=sum(1 for m in maxrep if m>=2),short60=sum(1 for c in ch if c<60),echo=echo)
for k,v in by.items(): print(k, stats([r["body"] for r in v]))
