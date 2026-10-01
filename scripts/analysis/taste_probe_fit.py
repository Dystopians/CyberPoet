# 口味可学性探针 · 第二步（10-01）：只用主人自己的票，看「隐状态向量」能不能预测他没见过的那一卷的票。
# 留一卷交叉验证（训练用其余各卷，测试用留出的那一卷）；逻辑回归用 numpy 手写（环境里没有 sklearn）。
# 两个问题：① 成对：两首里他选哪首（准确率，0.5 = 瞎猜）；② 单首：AI 诗会不会被他「都不要」（AUC）。
# 结果只作可行性判断，不做门、不上卷。
import json, sys, numpy as np, collections
Q = "/data/peilincai/CyberPoetTraining/claude_night_20260827/quiz_v3/"
V1 = "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/preference/labels/all_labels.json"
def picks56(lf): d = json.load(open(lf)); return {int(i): v for i, v in d["picks"].items()}
def picks3(lf): d = json.load(open(lf)); return {r["i"]: r.get("choice") for r in d["labels"]}
SETS = [("v3", "pairs_final.json", picks3, "labels_owner_v3.json"), ("v5", "v5_pairs_final.json", picks56, "labels_owner_v5.json"), ("v6", "v6_pairs_final.json", picks56, "labels_owner_v6.json"),
        ("v7", "v7_pairs_final.json", picks56, "labels_owner_v7.json"), ("v7.5", "v75_hh_fixed.json", picks56, "labels_owner_v75.json"), ("v8", "v8_pairs_final.json", picks56, "labels_owner_v8.json"),
        ("v9", "v9_pairs_final.json", picks56, "labels_owner_v9.json"), ("v10b", "v10b_pairs_final.json", picks56, "labels_owner_v10b.json"), ("v11", "v11_pairs_final.json", picks56, "labels_owner_v11.json"),
        ("v12", "v12_pairs_final.json", picks56, "labels_owner_v12.json"), ("v13", "v13_pairs_final.json", picks56, "labels_owner_v13.json"), ("v14", "v14_pairs_final.json", picks56, "labels_owner_v14.json")]
rows = []
for name, pf, fn, lf in SETS:
    pairs = json.load(open(Q + pf)); picks = fn(Q + lf)
    for i, q in enumerate(pairs):
        pk = picks.get(i)
        if pk in ("A", "B", "X"): rows.append((name, q["kind"], q["A"]["src"], q["B"]["src"], q["A"]["body"].strip(), q["B"]["body"].strip(), pk))
for x in json.load(open(V1)):
    if x.get("choice") in ("A", "B", "X"): rows.append(("v1", "aa", "ai", "ai", x["ba"].strip(), x["bb"].strip(), x["choice"]))
E = np.load(Q + "taste_probe_emb.npz", allow_pickle=True); idx = {b: k for k, b in enumerate(E["bodies"])}
def feats(layer, k):
    X = E[layer].astype(np.float32); X = X - X.mean(0)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)          # 无监督降维（用全部诗，不看票）
    Z = U[:, :k] * S[:k]; Z = (Z - Z.mean(0)) / (Z.std(0) + 1e-6)
    nll = E["nll"].astype(np.float32)[:, None]; nll = (nll - nll.mean()) / nll.std()
    return np.concatenate([Z, nll], 1)
def fit_lr(X, y, lam, iters=300):
    w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(iters):                                    # 牛顿法太贵，用带动量的梯度下降
        p = 1 / (1 + np.exp(-(X @ w + b))); g = X.T @ (p - y) / len(y) + lam * w; gb = (p - y).mean()
        w -= 0.5 * g; b -= 0.5 * gb
    return w, b
def auc(s, y):
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / max(1, n1 * n0)
sets = sorted({r[0] for r in rows})
rng = np.random.RandomState(0)
print(f"局数 {len(rows)}；决定票 {sum(1 for r in rows if r[6] != 'X')}；都不要 {sum(1 for r in rows if r[6] == 'X')}")
for layer in ("L_m8", "L_m16", "L_last"):
    for k in (32, 96):
        F = feats(layer, k)
        for lam in (0.01, 0.1):
            # ① 成对
            res = collections.defaultdict(lambda: [0, 0])
            D = [(r[0], r[1], F[idx[r[4]]] - F[idx[r[5]]], 1 if r[6] == "A" else 0) for r in rows if r[6] != "X"]
            for held in sets:
                tr = [d for d in D if d[0] != held]; te = [d for d in D if d[0] == held]
                if not te: continue
                Xtr = np.array([d[2] for d in tr]); ytr = np.array([d[3] for d in tr], dtype=float)
                Xtr = np.concatenate([Xtr, -Xtr]); ytr = np.concatenate([ytr, 1 - ytr])     # 对称增广，去掉侧位偏置
                w, b = fit_lr(Xtr, ytr, lam)
                for d in te:
                    ok = ((d[2] @ w) > 0) == (d[3] == 1); res[d[1]][0] += ok; res[d[1]][1] += 1
            pair_txt = " ".join(f"{kk} {v[0]}/{v[1]}={v[0]/v[1]:.3f}" for kk, v in sorted(res.items()))
            # ② 单首：AI 诗「都不要」对「被选中」
            S = []
            for r in rows:
                for side, src, body in (("A", r[2], r[4]), ("B", r[3], r[5])):
                    if src != "ai": continue
                    if r[6] == "X": S.append((r[0], F[idx[body]], 0))
                    elif r[6] == side: S.append((r[0], F[idx[body]], 1))
            aucs = []
            for held in sets:
                tr = [d for d in S if d[0] != held]; te = [d for d in S if d[0] == held]
                yte = np.array([d[2] for d in te], dtype=float)
                if len(te) < 20 or yte.min() == yte.max(): continue
                w, b = fit_lr(np.array([d[1] for d in tr]), np.array([d[2] for d in tr], dtype=float), lam)
                aucs.append((held, auc(np.array([d[1] for d in te]) @ w, yte), len(te)))
            wavg = sum(a * n for _, a, n in aucs) / sum(n for _, _, n in aucs)
            print(f"{layer} k={k} lam={lam} | 成对留一卷 {pair_txt} | 单首要/不要 AUC 加权 {wavg:.3f}（" + " ".join(f"{h} {a:.2f}" for h, a, _ in aucs) + f"；AI 诗 {len(S)} 首：要 {sum(d[2] for d in S)} / 不要 {sum(1-d[2] for d in S)}）")
