"""按「形式只作参考、不作硬约束」的思路修复微调数据。
修四处：
  1. 指令不再说「全新的」——答案本来就是既有作品，两句话不能自相矛盾
  2. 形式栏改成从答案数出来的真实描述，并明说仅供参考
  3. 物象栏改成真的在答案里出现的意象（原来 73% 的条目一个字都没出现）
  4. 避免栏剔除掉答案自己犯了的那几项
另外把洛夫那批被电子书排版拆散的诗压回单倍行距。
只读 codex 的数据，产物全部写到本目录。
"""
import json, re, math, argparse, collections, hashlib
from pathlib import Path

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
OUT = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/sft_repair")
STOP = set("的了在是我你他她它们不一而就也和与之有着过又却把被从向到上下这那который")

def lines_of(t):  return [x for x in t.strip().splitlines() if x.strip()]
def blocks_of(t): return [b for b in re.split(r"\n\s*\n", t.strip()) if b.strip()]
def is_double_spaced(t):
    L, B = lines_of(t), blocks_of(t)
    return len(L) >= 6 and len(B) == len(L)
def collapse(t): return re.sub(r"\n\s*\n", "\n", t.strip())

import sys
sys.path.insert(0, "/data/peilincai/CyberPoetTraining/claude_parallel_20260825/pylibs")
import jieba, jieba.posseg as pseg
jieba.setLogLevel(60)

KEEP_POS = ("n", "ns", "nz", "nr", "s")   # 名词、地名、专名、处所词
def nouns(t):
    """把诗切成词，只留名词——这些才是「意象」。"""
    flat = re.sub(r"\s+", " ", t)
    out = []
    for w in pseg.cut(flat):
        if w.flag in KEEP_POS and len(w.word) >= 2 and not (set(w.word) & STOP):
            out.append(w.word)
    return out

def build_df(texts):
    df = collections.Counter()
    for t in texts: df.update(set(nouns(t)))
    return df, len(texts)

def motifs_of(text, df, N, k=3):
    """挑出这首诗里最有辨识度的具体意象——每一个都真的在诗里出现。"""
    tf = collections.Counter(nouns(text))
    scored = [(c * math.log(N / (1 + df[g])), g) for g, c in tf.items() if 2 <= df[g] <= N * 0.25]
    scored.sort(reverse=True)
    picked, seen = [], set()
    for _, g in scored:
        if any(ch in seen for ch in g): continue
        picked.append(g); seen.update(g)
        if len(picked) == k: break
    return picked

def person_of(t):
    body = "".join(lines_of(t))
    c = [(len(re.findall(r"我们|我", body)), "第一人称"),
         (len(re.findall(r"你们|你", body)), "第二人称"),
         (len(re.findall(r"他们|她们|他|她|它", body)), "第三人称")]
    c.sort(reverse=True)
    return c[0][1] if c[0][0] >= 2 * max(1, c[1][0]) else None

def form_hint(t):
    """真实的形式描述，但措辞是「大致」，不是「必须」。"""
    L, B = lines_of(t), blocks_of(t)
    parts = [f"大致{len(L)}行"]
    if len(B) == 1: parts.append("不分节")
    else:
        per = [len(lines_of(b)) for b in B]
        parts.append(f"分{len(B)}节" + (f"，每节{per[0]}行左右" if len(set(per)) == 1 else ""))
    p = person_of(t)
    if p: parts.append(f"以{p}为主")
    return "，".join(parts)

SYSTEM = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8").strip()
# 这段提示词恒定出现在全部 2988 条样本里，它写着「原创」「不得复述现成诗句」
# 「不模仿任何具体作者」，而每条的答案都是具体诗人的既有作品——确实矛盾。
# 但它是恒定的，教不出「忽略某字段」那种可判别的规律（形式栏之所以有害，
# 是因为它逐条变化且 82% 造假）。改掉会让本项目 10 个脚本的推理条件与训练不一致，
# 也会污染与既有结果的对照，故保持原样，把矛盾写进交接件由所有者定夺。

INSTRUCTION = ("依据下面的创作简报写一首中文现代诗。简报给的是方向，"
               "形式一栏仅供参考，不必严格照做；把语言写准，让意象之间有内在关联，"
               "不要把主题直接说破。")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--luofu", choices=("collapse", "keep", "drop"), default="collapse")
    ap.add_argument("--flat-drafts", default=str(OUT / "flat_drafts.jsonl"),
                    help="重新生成的草稿；有就用上，没有则 flat_rewrite 暂时原样保留")
    args = ap.parse_args()

    rows = json.load(open(R / "data/llamafactory/sft_train.json"))
    meta = [json.loads(l) for l in open(R / "data/llamafactory/sft_train.meta.jsonl")]
    drafts = {}
    p = Path(args.flat_drafts)
    if p.exists():
        drafts = {json.loads(l)["index"]: json.loads(l)["draft"] for l in open(p)}

    df, N = build_df([r["output"] for r in rows])
    out_rows, out_meta, stat = [], [], collections.Counter()

    for i, (r, m) in enumerate(zip(rows, meta)):
        r, m = dict(r), dict(m)
        text = r["output"]
        if is_double_spaced(text):
            stat["洛夫式双倍行距"] += 1
            if args.luofu == "drop": stat["剔除"] += 1; continue
            if args.luofu == "collapse":
                text = collapse(text); r["output"] = text
                m["text_fix"] = "电子书排版把每行拆成一节，已压回单倍行距"

        r["system"] = SYSTEM
        task = m["task"]
        if task in ("brief_to_poem", "brief_to_long_poem_part"):
            inp = r.get("input", "")
            brief = (re.search(r"诗意方向：(.*)", inp) or [None, ""])[1] if re.search(r"诗意方向：(.*)", inp) else ""
            avoid = (re.search(r"避免：(.*)", inp).group(1) if re.search(r"避免：(.*)", inp) else "")
            av_items = [x.strip() for x in re.split(r"[、；;]", avoid) if x.strip()]
            av_keep = [x for x in av_items if x not in text]
            if len(av_keep) != len(av_items): stat["剔除了答案自己犯规的避免项"] += 1
            mo = motifs_of(text, df, N)
            stat["重建了物象栏"] += 1
            new_inp = [f"诗意方向：{brief}" if brief else None,
                       f"可参考的意象：{'、'.join(mo)}" if mo else None,
                       f"形式（仅供参考）：{form_hint(text)}",
                       f"避免：{'；'.join(av_keep)}" if av_keep else None]
            r["input"] = "\n".join(x for x in new_inp if x)
            r["instruction"] = INSTRUCTION
            m["motifs_after"] = mo
            m["form_hint_after"] = form_hint(text)
            stat["重写了简报"] += 1
        elif task == "flat_rewrite":
            if i in drafts:
                r["input"] = drafts[i]
                r["instruction"] = ("下面这段初稿把话说得太满、节奏拖沓。"
                                    "把它重写成一首有语言自觉的现代诗：保留同样的场景与物象，"
                                    "去掉解释和套话，让分行自己产生节奏。")
                m["draft_source"] = "由答案那首诗压平生成"
                stat["换上了新草稿"] += 1
            else:
                stat["草稿尚未生成，原样保留"] += 1
        elif task == "prefix_completion":
            if m.get("text_fix") and re.search(r"\n\s*\n", r.get("input", "")):
                r["input"] = collapse(r["input"])
                stat["续写类：前缀同步压平"] += 1
            else:
                stat["续写类：本来就自洽，未改"] += 1

        out_rows.append(r); out_meta.append(m)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sft_train_v2.json").write_text(json.dumps(out_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / "sft_train_v2.meta.jsonl", "w") as f:
        for m in out_meta: f.write(json.dumps(m, ensure_ascii=False) + "\n")
    (OUT / "dataset_info.json").write_text(json.dumps({
        "cyberpoet_sft_repaired": {"file_name": "sft_train_v2.json",
            "columns": {"prompt": "instruction", "query": "input", "response": "output", "system": "system"}}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in stat.items(): print(f"  {k}: {v}")
    print(f"  输出 {len(out_rows)} 条  sha256 {hashlib.sha256((OUT/'sft_train_v2.json').read_bytes()).hexdigest()[:16]}")

if __name__ == "__main__":
    main()
