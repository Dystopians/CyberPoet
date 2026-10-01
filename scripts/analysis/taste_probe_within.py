# 口味探针 · 第三步（10-01）：单首「要/不要」分数在**同一个模型内部**还管不管用（排除「其实是在认臂」）。
# 留一卷：用其余各卷全部 AI 诗训练，只在留出卷的 M4 诗上考；再看按分数排序后前三分之一与后三分之一的「要」率。
import json, numpy as np, collections
Q = "/data/peilincai/CyberPoetTraining/claude_night_20260827/quiz_v3/"
V1 = "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference/labels/all_labels.json"
def picks56(lf): d = json.load(open(lf)); return {int(i): v for i, v in d["picks"].items()}
def picks3(lf): d = json.load(open(lf)); return {r["i"]: r.get("choice") for r in d["labels"]}
SETS = [("v3", "pairs_final.json", picks3, "labels_owner_v3.json"), ("v5", "v5_pairs_final.json", picks56, "labels_owner_v5.json"), ("v6", "v6_pairs_final.json", picks56, "labels_owner_v6.json"),
        ("v7", "v7_pairs_final.json", picks56, "labels_owner_v7.json"), ("v8", "v8_pairs_final.json", picks56, "labels_owner_v8.json"),
        ("v9", "v9_pairs_final.json", picks56, "labels_owner_v9.json"), ("v10b", "v10b_pairs_final.json", picks56, "labels_owner_v10b.json"), ("v11", "v11_pairs_final.json", picks56, "labels_owner_v11.json"),
        ("v12", "v12_pairs_final.json", picks56, "labels_owner_v12.json"), ("v13", "v13_pairs_final.json", picks56, "labels_owner_v13.json"), ("v14", "v14_pairs_final.json", picks56, "labels_owner_v14.json")]
S = []   # (set, arm, body, y)  y=1 被选中；y=0 所在局「都不要」；另记 y=-1 同局输给对方（不进训练）
for name, pf, fn, lf in SETS:
    pairs = json.load(open(Q + pf)); picks = fn(Q + lf)
    for i, q in enumerate(pairs):
        pk = picks.get(i)
        if pk not in ("A", "B", "X"): continue
        for s in "AB":
            x = q[s]
            if x["src"] != "ai": continue
            y = 0 if pk == "X" else (1 if pk == s else -1)
            S.append((name, x.get("model", "?"), x["body"].strip(), y, q["kind"]))
for x in json.load(open(V1)):
    if x.get("choice") in ("A", "B", "X"):
        for s, b, m in (("A", x["ba"], x["ma"]), ("B", x["bb"], x["mb"])):
            S.append(("v1", m, b.strip(), 0 if x["choice"] == "X" else (1 if x["choice"] == s else -1), "aa"))
E = np.load(Q + "taste_probe_emb.npz", allow_pickle=True); idx = {b: k for k, b in enumerate(E["bodies"])}
def feats(layer, k):
    X = E[layer].astype(np.float32); X = X - X.mean(0); U, Sv, Vt = np.linalg.svd(X, full_matrices=False)
    Z = U[:, :k] * Sv[:k]; Z = (Z - Z.mean(0)) / (Z.std(0) + 1e-6)
    nll = E["nll"].astype(np.float32)[:, None]; nll = (nll - nll.mean()) / nll.std(); return np.concatenate([Z, nll], 1)
def fit_lr(X, y, lam, iters=300):
    w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ w + b))); w -= 0.5 * (X.T @ (p - y) / len(y) + lam * w); b -= 0.5 * (p - y).mean()
    return w, b
def auc(s, y):
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / max(1, n1 * n0)
print("各臂 要/不要/输给对方:", {a: (sum(1 for d in S if d[1] == a and d[3] == 1), sum(1 for d in S if d[1] == a and d[3] == 0), sum(1 for d in S if d[1] == a and d[3] == -1)) for a in ("M4_dpo", "M3_dpo", "M6b_dpo", "M7F_dpo", "M8_dpo")})
for layer, k, lam in (("L_last", 32, 0.1), ("L_m8", 32, 0.1), ("L_m16", 32, 0.1)):
    F = feats(layer, k)
    sets = sorted({d[0] for d in S})
    allsc = []   # 留出卷的 M4 诗：(分数, y)
    per = []
    for held in sets:
        tr = [d for d in S if d[0] != held and d[3] >= 0]; te = [d for d in S if d[0] == held and d[1] == "M4_dpo" and d[3] >= 0]
        if len(te) < 12: continue
        yte = np.array([d[3] for d in te], dtype=float)
        if yte.min() == yte.max(): continue
        w, b = fit_lr(np.array([F[idx[d[2]]] for d in tr]), np.array([d[3] for d in tr], dtype=float), lam)
        sc = np.array([F[idx[d[2]]] for d in te]) @ w
        per.append((held, auc(sc, yte), len(te))); allsc += list(zip((sc - sc.mean()) / (sc.std() + 1e-9), yte))
    a = np.array(allsc); o = np.argsort(-a[:, 0]); n = len(a); t = n // 3
    print(f"{layer} k={k}: 只考 M4 的诗 → 加权 AUC {sum(x[1]*x[2] for x in per)/sum(x[2] for x in per):.3f}（" + " ".join(f"{h} {v:.2f}/{m}" for h, v, m in per) + f"）；M4 诗 {n} 首：整体要率 {a[:,1].mean():.0%}，分数前 1/3 要率 {a[o[:t],1].mean():.0%}，后 1/3 要率 {a[o[-t:],1].mean():.0%}")
    # 包含「输给对方」的诗：前 1/3 里 被选中 / 输 / 都不要 的构成
    allp = []
    for held in sets:
        tr = [d for d in S if d[0] != held and d[3] >= 0]; te = [d for d in S if d[0] == held and d[1] == "M4_dpo"]
        if len(te) < 12: continue
        w, b = fit_lr(np.array([F[idx[d[2]]] for d in tr]), np.array([d[3] for d in tr], dtype=float), lam)
        sc = np.array([F[idx[d[2]]] for d in te]) @ w; allp += list(zip((sc - sc.mean()) / (sc.std() + 1e-9), [d[3] for d in te]))
    a = np.array(allp); o = np.argsort(-a[:, 0]); n = len(a); t = n // 3
    comp = lambda ix: {lab: f"{(a[ix,1]==v).mean():.0%}" for lab, v in (("被选中", 1), ("输给对方", -1), ("都不要", 0))}
    print(f"   含输局共 {n} 首：全体 {comp(np.arange(n))}；前 1/3 {comp(o[:t])}；后 1/3 {comp(o[-t:])}")
