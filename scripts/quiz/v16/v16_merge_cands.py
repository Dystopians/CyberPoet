# v16 候选合并（09-25）：两批候选合成门控脚本要的 v16_cands_{arm}.jsonl——
#   ① v15 题表未上卷槽的候选（M4 沿用 v15 未上卷正文、M4P 新生成，槽号 ha*/aa* 不变）；
#   ② 新命题 66 道（titles_v16_aa.json，槽号 ab{i}）→ 改成 aa{96+i}，并把题目追加进 v16_sources_proposed.json["aa"]。
# 只加不改：原始候选文件保留，合并结果写新文件。用法：两批候选齐了之后跑一次。
import json, os
S = json.load(open('v16_sources_proposed.json')); base = len(S["aa"])   # 96
T = json.load(open('titles_v16_aa.json')); A = {t["id"]: t for t in json.load(open('v16_aa_titles_with_author.json'))}
if not S.get("_v16_new_aa_appended"):
    for t in T: S["aa"].append({"author": A[t["id"]]["author"], "title": t["title"]})
    S["_v16_new_aa_appended"] = True
    json.dump(S, open('v16_sources_proposed.json', 'w'), ensure_ascii=False, indent=1)
idmap = {t["id"]: f"aa{base + int(t['id'][2:])}" for t in T}
for arm, old, new in (("M4P", "v16_cands_M4P.jsonl", "v16_cands_M4P_aa.jsonl"), ("M4", "v16_cands_M4.jsonl", "v16_cands_M4_aa.jsonl")):
    rows = [json.loads(l) for l in open(old, encoding="utf-8")]
    rows = [r for r in rows if not str(r["src_id"]).startswith("ab")]           # 幂等：去掉上次并入的
    for l in open(new, encoding="utf-8"):
        r = json.loads(l); r["src_id"] = idmap[r["src_id"]]; rows.append(r)
    with open(f"v16_cands_{arm}.jsonl", "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(arm, len(rows), "首（含新命题", sum(1 for r in rows if int(str(r['src_id'])[2:]) >= base and str(r['src_id']).startswith('aa')), "）")
GV = json.load(open('v16_gold_verdicts.json')); GV["drop_aa"] = [i for i in GV["drop_aa"] if i < base]
json.dump(GV, open('v16_gold_verdicts.json', 'w'), ensure_ascii=False, indent=1); print("gold verdicts: 新命题不在 drop 里")
