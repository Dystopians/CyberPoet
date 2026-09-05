"""实验 A 分析：初始 margin、梯度权重、与长度差的关系。"""
import json,sys,math,statistics as st,collections
f=sys.argv[1]; beta=0.1
rows=[json.loads(l) for l in open(f)]
src=json.load(open("v1_src.json")) if len(sys.argv)<3 else None
pol=[k[:-2] for k in rows[0] if k.endswith("_c") and not k.startswith("ref_") and k not in("len_c","lines_c","tok_c")]
ref=[k[:-2] for k in rows[0] if k.startswith("ref_") and k.endswith("_c")][0]
print("policies:",pol,"| ref:",ref)
def pear(x,y):
    mx,my=st.mean(x),st.mean(y); sx=math.sqrt(sum((a-mx)**2 for a in x)); sy=math.sqrt(sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy) if sx and sy else float('nan')
for setname in sorted(set(r["set"] for r in rows)):
    rs=[r for r in rows if r["set"]==setname]
    print(f"\n=== {setname} n={len(rs)}")
    for p in pol:
        rc=[beta*(r[p+"_c"]-r[ref+"_c"]) for r in rs]; rr=[beta*(r[p+"_r"]-r[ref+"_r"]) for r in rs]
        m=[a-b for a,b in zip(rc,rr)]
        w=[1/(1+math.exp(min(50,max(-50,x)))) for x in m]   # σ(-m) 梯度权重
        loss=[math.log(1+math.exp(-x)) if x>-50 else -x for x in m]
        acc=sum(1 for x in m if x>0)/len(m)
        dl=[r["len_c"]-r["len_r"] for r in rs]; dtok=[r["tok_c"]-r["tok_r"] for r in rs]
        dead=sum(1 for x in w if x<0.05); hot=sum(1 for x in w if x>0.95)
        # effective training set: weight-averaged length difference
        wl=sum(a*b for a,b in zip(w,dl))/sum(w)
        # per-token advantage of policy over ref
        adv_c=st.median([(r[p+"_c"]-r[ref+"_c"])/r["tok_c"] for r in rs])
        print(f"{p:10s} init reward c/r {st.mean(rc):6.2f}/{st.mean(rr):6.2f} | margin mean {st.mean(m):6.2f} med {st.median(m):6.2f} sd {st.pstdev(m):5.2f} | init loss {st.mean(loss):.3f} acc {acc:.3f} | 权重<0.05(几乎不训) {dead:3d} 权重>0.95 {hot:3d} | corr(margin, len_c-len_r)={pear(m,dl):+.3f} corr(margin, tok diff)={pear(m,dtok):+.3f} | 权重加权后 chosen-rejected 字数差 {wl:+.1f}（原始均值 {st.mean(dl):+.1f}） | 每token优势 {adv_c:.3f}")
    if src and setname=="v1":
        by=collections.defaultdict(list)
        for r,s in zip(rs,src): by[s].append(r)
        p=pol[-1]
        for s,rr_ in by.items():
            m=[beta*((r[p+"_c"]-r[ref+"_c"])-(r[p+"_r"]-r[ref+"_r"])) for r in rr_]
            w=[1/(1+math.exp(min(50,max(-50,x)))) for x in m]
            print(f"   来源 {s:13s} n={len(rr_):3d} margin med {st.median(m):6.1f} 权重和 {sum(w):5.1f}")
