"""为词汇诊断生成对照样本。两组实验，全部零训练：
  ladder：同一套提示词，扫 e8 预训练的 2/4/6/7 轮 checkpoint（都已在盘上），
          最后等 e2_lmhead 训完把它也测上——回答「标志词学不会是曝光不足还是读出层冻结」。
  prompt：固定模型（e8 2 轮 = 当前 pt2），换三种系统提示词——回答
          「现行提示词里『不模仿任何具体作者/避免空泛口号』是否正在压制缺失的语域」。
同题同序同种子，各条件可逐对比较。采样参数与偏好库生成完全一致。
"""
import argparse, json, time, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

R = Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W = Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS_CURRENT = (R / "prompts/poetry_system.txt").read_text(encoding="utf-8").strip()
SYS_OPEN = (
    "你是一位中文现代诗人。根据用户给出的主题、意象或情境写一首原创现代诗。"
    "只输出诗歌正文，不输出标题、署名、日期、说明、点评或 Markdown 标记。"
)
SYS_LINEAGE = SYS_OPEN + (
    "你的写作扎根于二十世纪中文现代诗传统（穆旦、昌耀、海子、洛夫、多多、张枣等），"
    "陈述、议论、呼告与形而上的词汇都可入诗，不必局限于小物件与动作的白描。"
)

E8 = W / "pretrain/outputs/e8"
CONDITIONS = {
    "ladder": [
        ("e2", E8 / "checkpoint-398", SYS_CURRENT),
        ("e4", E8 / "checkpoint-796", SYS_CURRENT),
        ("e6", E8 / "checkpoint-1194", SYS_CURRENT),
        ("e7", E8 / "checkpoint-1393", SYS_CURRENT),
    ],
    # lm_head 适配器带 modules_to_save，与普通适配器混挂在同一个 PeftModel 上
    # 在 PEFT 0.18 有已知风险，故单独一个进程跑
    "lmhead": [
        # 训练结束时最终权重写在 output_dir 根目录（398 不是 save_steps 的倍数，不会有 checkpoint-398）
        ("e2_lmhead", W / "pretrain/outputs/e2_lmhead", SYS_CURRENT),
    ],
    "prompt": [
        ("sys_none", E8 / "checkpoint-398", None),
        ("sys_open", E8 / "checkpoint-398", SYS_OPEN),
        ("sys_lineage", E8 / "checkpoint-398", SYS_LINEAGE),
    ],
    # 交叉：最优轮数 × 最优提示词，验证两项收益是否叠加
    "cross": [
        ("e7_none", E8 / "checkpoint-1393", None),
        ("e7_open", E8 / "checkpoint-1393", SYS_OPEN),
        ("e7_lineage", E8 / "checkpoint-1393", SYS_LINEAGE),
    ],
    # 加赛：首轮盲标筛出的两个决赛配置 + 现状对照，配全新种子重新采样
    "runoff": [
        ("e2", E8 / "checkpoint-398", SYS_CURRENT),
        ("e7_open", E8 / "checkpoint-1393", SYS_OPEN),
        ("e7_lineage", E8 / "checkpoint-1393", SYS_LINEAGE),
    ],
}

ap = argparse.ArgumentParser()
ap.add_argument("--job", choices=tuple(CONDITIONS), required=True)
ap.add_argument("--n-prompts", type=int, default=20)
ap.add_argument("--seeds", type=int, nargs="+", default=[20260826, 771003])
ap.add_argument("--batch", type=int, default=8)
ap.add_argument("--out", required=True)
a = ap.parse_args()

tasks = [json.loads(l) for l in open(R / "eval/benchmark/tasks.jsonl")][: a.n_prompts]
tok = AutoTokenizer.from_pretrained(R / "models/Qwen3-14B", trust_remote_code=True)
tok.padding_side = "left"
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

print("加载基座 …", flush=True)
base = AutoModelForCausalLM.from_pretrained(
    R / "models/Qwen3-14B", trust_remote_code=True,
    torch_dtype=torch.bfloat16, device_map="cuda:0").eval()

def ptext(instruction, sys):
    msgs = ([{"role": "system", "content": sys}] if sys else []) + [
        {"role": "user", "content": instruction}]
    return tok.apply_chat_template(msgs, tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)

def gen(model, texts, seed):
    enc = tok(texts, return_tensors="pt", padding=True).to("cuda:0")
    torch.manual_seed(seed)
    with torch.no_grad():
        o = model.generate(**enc, max_new_tokens=560, do_sample=True, temperature=0.9,
                           top_p=0.92, repetition_penalty=1.08,
                           pad_token_id=tok.pad_token_id)
    return [tok.decode(s[enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            for s in o]

out = open(a.out, "a", encoding="utf-8")
model, loaded = None, set()
t0 = time.time()
for cond, ckpt, sys in CONDITIONS[a.job]:
    # e2_lmhead 排在最后：训练若未结束就等它（save_only_model=false，等最终 checkpoint）
    waited = 0
    while not (ckpt / "adapter_model.safetensors").exists():
        if waited == 0:
            print(f"[{cond}] checkpoint 未就绪，等待 {ckpt} …", flush=True)
        time.sleep(60); waited += 1
        if waited > 60:
            print(f"[{cond}] 等了 60 分钟仍未出现，跳过", flush=True)
            break
    if not (ckpt / "adapter_model.safetensors").exists():
        continue
    if cond not in loaded:
        if model is None:
            model = PeftModel.from_pretrained(base, str(ckpt), adapter_name=cond)
        else:
            model.load_adapter(str(ckpt), adapter_name=cond)
        loaded.add(cond)
    model.set_adapter(cond); model.eval()
    for seed in a.seeds:
        for i in range(0, len(tasks), a.batch):
            chunk = tasks[i:i + a.batch]
            bodies = gen(model, [ptext(t["instruction"], sys) for t in chunk], seed + i)
            for t, body in zip(chunk, bodies):
                out.write(json.dumps({
                    "cond": cond, "prompt_key": t["id"], "seed": seed,
                    "prompt": t["instruction"], "body": body,
                }, ensure_ascii=False) + "\n")
            out.flush()
        print(f"[{cond}] seed {seed} 完成  {(time.time()-t0)/60:.1f} 分", flush=True)
out.close()
print("全部完成", flush=True)
