"""枚举 PoemWiki 作者空间：id 1..3000，每 id 依次试 +80/+48/-48/-80 四种偏移。
404 探测间隔 0.35s，命中后 1.2s。产出 author_index.jsonl（id/name/b64/诗数线索）。"""
import base64, subprocess, time, re, json, sys
from pathlib import Path
A = 96969696969
OUT = Path(__file__).parent / "author_index.jsonl"
done = set()
if OUT.exists():
    for l in open(OUT):
        done.add(json.loads(l)["id"])
out = open(OUT, "a", encoding="utf-8")
lo, hi = int(sys.argv[1]), int(sys.argv[2])
for x in range(lo, hi + 1):
    if x in done: continue
    hit = None
    for off in (80, 48, -48, -80):
        b64 = base64.b64encode(str(A * x + off).encode()).decode()
        h = subprocess.run(["curl", "-s", "--max-time", "15",
            f"https://poemwiki.org/author/{b64}"], capture_output=True, text=True).stdout
        if "<title>404" not in h and len(h) > 2000:
            t = re.search(r"<title>([^<]*?) - PoemWiki", h)
            n_poems = len(re.findall(r'href="https://poemwiki\.org/p/', h))
            hit = {"id": x, "off": off, "b64": b64,
                   "name": t.group(1).strip() if t else "?", "poems_on_page": n_poems}
            time.sleep(1.2)
            break
        time.sleep(0.35)
    if hit:
        out.write(json.dumps(hit, ensure_ascii=False) + "\n"); out.flush()
        if x % 1 == 0: print(x, hit["name"], hit["poems_on_page"], flush=True)
    elif x % 50 == 0:
        print(x, "-", flush=True)
out.close()
