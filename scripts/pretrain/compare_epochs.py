"""不同预训练轮数的同题对照：同一批题目、同一个种子，只换 checkpoint。"""
import json, torch, re
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1"); W=Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS=(R/"prompts/poetry_system.txt").read_text(encoding="utf-8").strip()
CKS={"1轮":"checkpoint-199","2轮(最优)":"checkpoint-398","5轮":"checkpoint-995","7轮(过度)":"checkpoint-1393"}
tasks=[json.loads(l) for l in open(R/"eval/benchmark/tasks.jsonl")][:6]
tok=AutoTokenizer.from_pretrained(R/"models/Qwen3-14B", trust_remote_code=True)
if tok.pad_token is None: tok.pad_token=tok.eos_token
print("加载基座 …",flush=True)
base=AutoModelForCausalLM.from_pretrained(R/"models/Qwen3-14B",trust_remote_code=True,
      torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
def gen(m,t):
    u=t["instruction"]+(f"\n形式：{t['form_constraints']}" if t.get("form_constraints") else "")
    txt=tok.apply_chat_template([{"role":"system","content":SYS},{"role":"user","content":u}],
        tokenize=False,add_generation_prompt=True,enable_thinking=False)
    enc=tok([txt],return_tensors="pt").to("cuda:0"); torch.manual_seed(20260825)
    with torch.no_grad():
        o=m.generate(**enc,max_new_tokens=560,do_sample=True,temperature=0.85,top_p=0.9,
                     repetition_penalty=1.08,pad_token_id=tok.pad_token_id)
    return tok.decode(o[0,enc["input_ids"].shape[1]:],skip_special_tokens=True).strip()
res={}; model=None
for tag,ck in CKS.items():
    p=str(W/"pretrain/outputs/e8"/ck)
    if model is None: model=PeftModel.from_pretrained(base,p,adapter_name=tag)
    else: model.load_adapter(p,adapter_name=tag)
    model.set_adapter(tag); model.eval()
    for t in tasks:
        res[(tag,t["id"])]=gen(model,t); print(f"  {tag} {t['id']}",flush=True)
with open(W/"pretrain/epoch_compare.jsonl","w") as f:
    for t in tasks:
        f.write(json.dumps({"id":t["id"],"prompt":t["instruction"],
            **{tag:res[(tag,t["id"])] for tag in CKS}},ensure_ascii=False)+"\n")
print("完成",flush=True)
