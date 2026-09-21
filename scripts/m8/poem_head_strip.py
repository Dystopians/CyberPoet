"""开头题献/副题/题词剥离（只处理诗的开头，只用于训练副本）。被 build_sft_v5.py 与 assemble_pt10_s3.py 共用。"""
import re
def norm(t): return re.sub(r"\s+", "", t)
# ---- 题献/副题/题词剥离（只处理开头）----
DED = re.compile(r"^[（(]?\s*[—–\-]{1,2}\s*(给|献给|赠|致|悼|怀念|纪念|兼致|兼赠)[^\n]{1,30}[)）]?$")
SUB = re.compile(r"^[—–\-]{1,2}\s*[《“\"「][^\n]{1,24}$")
ATTR = re.compile(r"^[—–\-]{1,2}\s*[^\n，。！？]{2,16}$")
def strip_head(t):
    ls = t.strip().split("\n"); changed = None
    nz = [i for i, l in enumerate(ls) if l.strip()]
    if not nz: return t, None
    f = ls[nz[0]].strip()
    if DED.match(f): ls = ls[nz[0]+1:]; changed = "题献"
    elif SUB.match(f): ls = ls[nz[0]+1:]; changed = "副题"
    elif len(nz) >= 3:
        s2 = ls[nz[1]].strip()
        if ATTR.match(s2) and ("·" in s2 or "《" in s2) and len(norm(f)) <= 40:
            ls = ls[nz[1]+1:]; changed = "题词"
    out = "\n".join(ls).strip("\n")
    return (out, changed) if changed and len(norm(out)) >= 40 else (t, None)

