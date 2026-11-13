#!/usr/bin/env python3
"""把 v15 精简卷的结果码换回原卷题号，输出一份 v15 结果码，交给原封不动的 analyze_v15.py。
用法：python3 v15s_to_v15.py <短卷结果码文件> > v15_from_short.code
      python3 analyze_v15.py v15_from_short.code
"""
import json, sys, base64, hashlib, os
D = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(f"{D}/v15s_index_map.json"))
F = json.load(open(f"{D}/v15_pairs_final.json"))
idx = m["idx"]
assert hashlib.sha256("".join(F[k]["A"]["body"] + F[k]["B"]["body"] for k in idx).encode()).hexdigest() == m["body_sha256"], "题库与映射对不上"
d = json.loads(base64.b64decode(open(sys.argv[1]).read().strip()).decode("utf-8"))
assert d.get("v") == "15s", f"这不是精简卷的结果码（v={d.get('v')}）"
remap = lambda o: {str(idx[int(j)]): v for j, v in (o or {}).items()}
out = {"v": 15, "nick": d.get("nick", ""), "picks": remap(d["picks"]), "marks": remap(d.get("marks")),
       "ts": d.get("ts"), "来自": "v15s 精简卷"}
print(base64.b64encode(json.dumps(out, ensure_ascii=False).encode("utf-8")).decode())
