"""为 flat_rewrite 重新生成草稿：草稿必须由答案那首诗本身压平而来，
这样「把草稿改写成诗」才是一个真实存在的关系。只读原数据，产物写到本目录。"""
import json, re, argparse, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
OUT = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825/sft_repair")

SYS = "你是一名中文写作助手，严格按要求输出，不添加任何说明。"
TMPL = """下面是一首现代诗。把它改写成一段平庸的初稿：

- 保留同样的场景、人物、动作和核心物象，不要换题材
- 把含蓄的地方直接说破，加入解释性的句子
- 节奏拖沓一些，可以用「仿佛」「像某种」「这就是」这类套话
- 仍然分行排列，行数可以和原诗不同

只输出改写后的初稿，不要标题、不要说明。

原诗：
{poem}"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "flat_drafts.jsonl"))
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = json.load(open(R / "data/llamafactory/sft_train.json"))
    meta = [json.loads(l) for l in open(R / "data/llamafactory/sft_train.meta.jsonl")]
    todo = [(i, r, m) for i, (r, m) in enumerate(zip(rows, meta)) if m["task"] == "flat_rewrite"]
    if args.limit: todo = todo[:args.limit]

    done = set()
    outp = Path(args.out)
    if outp.exists():
        done = {json.loads(l)["index"] for l in open(outp)}
    todo = [t for t in todo if t[0] not in done]
    print(f"待生成 {len(todo)}（已完成 {len(done)}）", flush=True)

    tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
    tok.padding_side = "left"
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        R / "models/Qwen3-14B", trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0")
    model.eval()

    f = open(args.out, "a")
    import time; t0 = time.time()
    for s in range(0, len(todo), args.batch):
        chunk = todo[s:s + args.batch]
        msgs = [tok.apply_chat_template(
            [{"role": "system", "content": SYS},
             {"role": "user", "content": TMPL.format(poem=r["output"])}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False) for _, r, _ in chunk]
        enc = tok(msgs, return_tensors="pt", padding=True).to("cuda:0")
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=420, do_sample=True, temperature=0.8,
                                 top_p=0.9, repetition_penalty=1.05, pad_token_id=tok.pad_token_id)
        for (idx, r, m), seq in zip(chunk, out):
            draft = tok.decode(seq[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            draft = re.sub(r"^(初稿|改写后的初稿)[：:]\s*", "", draft).strip()
            f.write(json.dumps({"index": idx, "source_poem_id": m["source_poem_id"],
                                "draft": draft}, ensure_ascii=False) + "\n")
        f.flush()
        n = s + len(chunk); el = (time.time() - t0) / 60
        print(f"[{n}/{len(todo)}] 已用 {el:.1f}分 预计总 {el/max(1,n)*len(todo):.0f}分", flush=True)

if __name__ == "__main__":
    main()
