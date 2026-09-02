# v9 候选门控：v10_cands_{M6,M5,M4}.jsonl → v10_gen_gated.json（键 "sid|arm"）。
# 硬门控全家桶（卷宗 README 累积至 v8，每条有事故背书）：
#   长度 60–340 · 指令回显 · 退化（同行重复≥4）· LIZHI 词典 · Latin≥3 ·
#   双倍行距压平 unspace2（v8#78 事故）· 命题含「十四行」必须 14 行 ·
#   行尾空白/（注：…）尾注剥除 · 与登记表/pt8 语料回显无关（记忆核验另行跑）。
# 软旗（碎行/等压/箴言尾，2026-08-29 标定版）只记录排序，不做门。
import json, re, collections, sys
sys.path.insert(0, '.')
from v5_lib import norm, chars, flagged, unspace2, soft_flags
from texture_retrodict import texture

def clean(b, title=""):
    b = "\n".join(x.rstrip() for x in b.strip().splitlines())
    b = re.sub(r"\n（注：[^\n）]*）\s*$", "", b)
    b = re.sub(r"\n[（(]注[)）]\s*$", "", b)
    b = re.sub(r"\n[12]\d{3}年\d{1,2}月\d{1,2}日\s*$", "", b)     # 伪日期尾
    ls = b.splitlines()
    # 行首标题回显剥除（（《题》）/《题》/——《题》/裸题名 的独立首行）
    if ls and title:
        h = ls[0].strip()
        t = re.escape(title)
        # v10 通读所见三类回显：「——题目」「（——题目）」「——《题目》之五」「题目：」「题目——」、首行伪日期「（1987-08-23）」
        echo = (h in {title, f"《{title}》", f"（{title}）", f"（《{title}》）", f"——《{title}》", f"({title})"}
                or re.fullmatch(rf"[（(]?[—\-–]{{1,2}}\s*《?{t}》?\s*(（\d{{4}}）|\(\d{{4}}\)|之[一二三四五六七八九十]+)?[)）]?", h)
                or re.fullmatch(rf"{t}\s*[：:—\-–]+", h)
                or re.fullmatch(r"[（(]?\d{4}[-./年]\d{1,2}[-./月]\d{1,2}日?[)）]?", h))
        if echo:
            ls = ls[1:]
            while ls and not ls[0].strip(): ls = ls[1:]
    b = unspace2("\n".join(ls))
    return b.strip()

def gate(title, b):
    """返回 None=过闸, 否则拒因。"""
    c = chars(b)
    if not (60 <= c <= 340): return f"长度{c}"
    if re.search(r"以《|写一首现代诗|现代诗[:：]", b): return "指令回显"
    ls = [x.strip() for x in b.splitlines() if x.strip()]
    if ls and collections.Counter(ls).most_common(1)[0][1] >= 4: return "退化重复行"
    if flagged(b): return "LIZHI"
    if len(re.findall(r"[A-Za-z]", b)) >= 3: return "Latin"
    # 命题形式履约：题目含「N行」或正文自注「（N行）」都要兑现（v6/v8 栽十四行，v9 栽自注十二行）
    CN = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
          "十一":11,"十二":12,"十三":13,"十四":14,"十五":15,"十六":16,"十八":18,"二十":20}
    for src in (title, ls[0] if ls else ""):
        m = re.search(r"([一二三四五六七八九十]{1,2})行", src)
        if m and m.group(1) in CN:
            body_lines = [x for x in ls if not re.fullmatch(r"[（(][一二三四五六七八九十]{1,2}行[)）]", x)]
            if len(body_lines) != CN[m.group(1)]: return f"{m.group(1)}行不履约({len(body_lines)}行)"
    # 单行复读：同一 1–4 字单元带标点连续 ≥4 次（「在它，在它，在它，在它」「梨之梨之梨之」）
    if re.search(r"(.{1,4}[，,、之])\1{3,}", b): return "单行复读"
    return None

stat = collections.Counter()
gated = collections.defaultdict(list)
for arm in ("M6b", "M5b", "M4"):
    for l in open(f"v10_cands_{arm}.jsonl"):
        r = json.loads(l)
        b = clean(r["body"], r["title"])
        why = gate(r["title"], b)
        stat[f"{arm}:{why or '过'}"] += 1
        if why: continue
        gated[f"{r['src_id']}|{arm}"].append({
            "seed": int(r["seed"]), "title": r["title"], "body": b,
            "tex": f"{texture(b):.2f}", "soft": "/".join(soft_flags(b))})
# 组内按质感降序（rank-not-gate：质感只排序）
for k in gated: gated[k].sort(key=lambda c: -float(c["tex"]))
json.dump(dict(gated), open("v10_gen_gated.json", "w"), ensure_ascii=False, indent=1)
print("门控统计:", dict(stat))
cov = collections.Counter(k.split("|")[1] for k in gated)
print(f"过闸组: {len(gated)}（按臂: {dict(cov)}）→ v10_gen_gated.json")
# 覆盖缺口速报：哪些槽某臂全军覆没
slots = {k.split("|")[0] for k in gated}
for sid in sorted(slots, key=lambda s: (s[:2], int(s[2:]))):
    miss = [a for a in ("M6b","M5b","M4") if f"{sid}|{a}" not in gated]
    if miss: print(f"  {sid} 缺臂: {','.join(miss)}")
