# v14 盲读助手（09-21）：只读「会上卷的那几首」，读的时候不知道是哪个臂。
# 流程：① 把按匿名编号记的否决（v14_read_codes.json）经 v14_blind_key.json 对回 [槽, 臂, 种子]，写 v14_read_verdicts.json；
#       ② 跑一遍装配；③ 把装上卷的 AI 诗对回匿名编号，挑出还没读过的，写 v14_待读.txt（只有编号、题目、正文）；
#       ④ 我读完把每个编号记成 ok 或否决原因，再跑本脚本；直到「待读 0 首」为止——上卷的每一首都读过，且全程不看臂名。
# v14_read_codes.json 格式：{"ok": ["ha3|c2", ...], "veto": {"aa17|c4": "题献", ...}, "drop": ["ha5", ...]}
import json, subprocess, sys, os
KEY = json.load(open('v14_blind_key.json'))
GATED = json.load(open('v14_gen_gated.json'))
RC = json.load(open('v14_read_codes.json')) if os.path.exists('v14_read_codes.json') else {"ok": [], "veto": {}, "drop": []}
bad = [c for c in list(RC.get("veto", {})) + RC.get("ok", []) if c not in KEY]
assert not bad, f"编号不在对照表里: {bad}"
def build_inv():
    inv = {}
    for code, (arm, seed) in KEY.items():
        sid = code.split("|")[0]
        for c in GATED.get(f"{sid}|{arm}", []):
            if c["seed"] == seed: inv[(sid, c["body"])] = code
    return inv
INV = build_inv()
def write_verdicts():
    veto = []
    for code in list(RC.get("veto", {})) + list(RC.get("auto", {})):
        sid = code.split("|")[0]; arm, seed = KEY[code]; veto.append([sid, arm, seed])
    json.dump({"veto": veto, "drop": RC.get("drop", []), "force": {}}, open('v14_read_verdicts.json', 'w'), ensure_ascii=False, indent=1)
import re
for _round in range(30):   # 选集内互重（两首诗共用 10 字窗）机械处理：否决排在后面的那首 AI 诗，记入 auto，再装一遍
    write_verdicts()
    for f in ('v14_haaa_final.json', 'v14_haaa_draft.json'):
        if os.path.exists(f): os.remove(f)
    r = subprocess.run([sys.executable, 'assemble_v14_haaa.py'], capture_output=True, text=True)
    lines = (r.stdout + r.stderr).strip().splitlines()
    dup = [re.findall(r"\('(\w+)', '([AB])'\)", l) for l in lines if l.strip().startswith("- 互重")]
    if not dup or not os.path.exists('v14_haaa_draft.json'): break
    draft = {p["slot"]: p for p in json.load(open('v14_haaa_draft.json'))}
    added = 0
    for pair in dup:
        for slot, side in reversed(pair):          # 先试排在后面的那首
            poem = draft[slot][side]
            if poem["src"] != "ai": continue
            code = INV.get((slot, poem["body"]))
            if code and code not in RC.setdefault("auto", {}):
                RC["auto"][code] = "选集内互重（机械）"; added += 1
            break
    if not added: break
    json.dump(RC, open('v14_read_codes.json', 'w'), ensure_ascii=False, indent=1)
# 装配日志里带臂名的行不给我看（防不盲）：只留 OK / 待处理 / 缺额 三类行，并把臂名抹掉
def blind(l): return re.sub(r"M8sft|M8w|M8|M4", "臂", l)
for l in lines:
    if l.startswith(("OK", "!!", "  -", "ha 实装")) or "缺额" in l or "Error" in l or "Traceback" in l or "assert" in l.lower(): print(blind(l))
if not os.path.exists('v14_haaa_final.json'):
    print("装配没出成品（见上），先处理再跑"); sys.exit(1)
inv = INV
seen = set(RC.get("ok", [])) | set(RC.get("veto", {}))
todo = []
for p in json.load(open('v14_haaa_final.json')):
    for s in "AB":
        if p[s]["src"] != "ai": continue
        code = inv.get((p["slot"], p[s]["body"]))
        assert code, f"{p['slot']} 的 AI 诗对不回编号"
        if code not in seen: todo.append((code, p["title"], p[s]["body"]))
todo.sort(key=lambda x: (x[0][:2], int(x[0].split("|")[0][2:]), x[0]))
with open('v14_待读.txt', 'w') as f:
    for code, title, body in todo: f.write(f"\n{'='*60}\n## {code} 《{title}》\n{body}\n")
print(f"已读 {len(seen)}（否决 {len(RC.get('veto', {}))}；机械否决 {len(RC.get('auto', {}))}）；本轮待读 {len(todo)} 首 → v14_待读.txt")
