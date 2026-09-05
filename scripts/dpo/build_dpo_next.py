"""下一代偏好对：只用主人的票，chosen 必须是目标代模型自己的生成（09-02 结论：旧偏好数据套新底座会拽偏）。
用法: python3 build_dpo_next.py <标签> <目标臂,逗号分隔> <卷号 ...>
  例: python3 build_dpo_next.py v6 M7_dpo,M7F_dpo,M7Fsft_dpo v11 v12
取材：每卷 labels_owner_<卷>.json（主人票）× <卷>_pairs_final.json（卷子）。
  机机局有胜负 → chosen=胜方（须在目标臂），rejected=负方；真伪局 AI 反杀 → chosen=AI（须在目标臂），rejected=真人；
  「都不要」不入；真人胜的真伪局不入（dpo_v4 教训：真人不做 chosen）。
护栏（承 build_dpo.py + 08-31 建对纪律）：正文最短 20 字；近重复（4-gram Jaccard≥0.8）不入；同一正文最多出现 2 次；system 统一 v2。
输出: data/dpo_train_<标签>.json + 登记 data/dataset_info.json 的 cyberpoet_dpo_<标签>（只加不改）。
"""
import json, re, sys, collections
from pathlib import Path
N = Path(__file__).resolve().parent; R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
SYS = (R / "prompts/poetry_system_v2.txt").read_text(encoding="utf-8").strip()
def norm(t): return re.sub(r"\s+", "", t)
def grams(t):
    f = re.sub(r"[^一-鿿]", "", t); return {f[i:i+4] for i in range(max(0, len(f)-3))}
def near(x, y, thr=.8):
    a, b = grams(x), grams(y); return bool(a and b) and len(a & b) / len(a | b) >= thr

def main(tag, arms, vers, out_dir=N / "data", register=True, quiz_dir=N / "quiz_v3"):
    arms = set(arms); rows, seen, stat = [], collections.Counter(), collections.Counter()
    for ver in vers:
        L = json.load(open(quiz_dir / f"labels_owner_{ver}.json")); P = json.load(open(quiz_dir / f"{ver}_pairs_final.json"))
        for i, p in enumerate(P):
            v = L["picks"].get(str(i))
            if v not in ("A", "B") or p["kind"] == "hh": stat["弃权/互殴"] += 1; continue
            w, l = p[v], p["B" if v == "A" else "A"]
            if w["src"] != "ai": stat["真人胜（不入）"] += 1; continue
            if w.get("model") not in arms: stat[f"胜方臂不在目标集({w.get('model')})"] += 1; continue
            title = p.get("title") or w.get("title", "")
            c, j = w["body"].strip(), l["body"].strip()
            if len(norm(c)) < 20 or len(norm(j)) < 20: stat["太短"] += 1; continue
            if near(c, j): stat["近重复"] += 1; continue
            if seen[norm(c)] >= 2 or seen[norm(j)] >= 2: stat["正文超 2 次"] += 1; continue
            seen[norm(c)] += 1; seen[norm(j)] += 1
            rows.append({"system": SYS, "instruction": f"以《{title}》为题写一首现代诗。", "input": "", "chosen": c, "rejected": j,
                         "_src": f"{ver}[{i}]", "_kind": p["kind"], "_chosen_model": w.get("model"),
                         "_rejected": l.get("model") or l.get("author"), "_mark": L["marks"].get(str(i), "")})
            stat[f"入库/{p['kind']}"] += 1
    out_dir.mkdir(exist_ok=True); outp = out_dir / f"dpo_train_{tag}.json"
    json.dump(rows, open(outp, "w"), ensure_ascii=False, indent=1)
    print(f"{tag}: {dict(stat)} → {outp}（{len(rows)} 对）")
    if register:
        di = N / "data/dataset_info.json"; d = json.load(open(di)); key = f"cyberpoet_dpo_{tag}"
        if key not in d:
            d[key] = {"file_name": outp.name, "ranking": True,
                      "columns": {"prompt": "instruction", "query": "input", "chosen": "chosen", "rejected": "rejected", "system": "system"}}
            json.dump(d, open(di, "w"), ensure_ascii=False, indent=1); print("登记", key)
    return rows

if __name__ == "__main__":
    tag, arms, vers = sys.argv[1], sys.argv[2].split(","), sys.argv[3:]
    main(tag, arms, vers)
