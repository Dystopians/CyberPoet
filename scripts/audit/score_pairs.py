"""实验 A：DPO 参考模型偏移。对 dpo_v1 (290) / v4 新增 (194) / v5 新增 (99) 每对，
在 策略初始(桥) 与 LLaMA-Factory 实际参考(禁用 adapter = 裸底座) 下算响应对数似然，
得到初始 margin 与梯度权重 σ(-m)。输出 jsonl。"""
import json, re, sys, torch, math
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1'); N=Path('/data/peilincai/CyberPoetTraining/claude_night_20260827')
OUT=Path(sys.argv[1]); BASE=sys.argv[2]; ADAPTERS=sys.argv[3].split(',')
tok=AutoTokenizer.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True)
def k(r): return (re.sub(r"\s+","",r["instruction"]),re.sub(r"\s+","",r["chosen"]),re.sub(r"\s+","",r["rejected"]))
v1=json.load(open(N/"data/dpo_train.json")); s1={k(r) for r in v1}
v4=[r for r in json.load(open(N/"data/dpo_train_v4.json")) if k(r) not in s1]
v5=[r for r in json.load(open(N/"data/dpo_train_v5.json")) if k(r) not in s1]
sets=[("v1",v1),("v4add",v4),("v5add",v5)]
basep=BASE if BASE.startswith('/') else str(R/BASE)
base=AutoModelForCausalLM.from_pretrained(basep,trust_remote_code=True,torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
@torch.no_grad()
def logp(model,system,instr,resp):
    p=tok.apply_chat_template([{"role":"system","content":system},{"role":"user","content":instr}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
    pid=tok(p,add_special_tokens=False)["input_ids"]; rid=tok(resp+"<|im_end|>\n",add_special_tokens=False)["input_ids"]
    ids=torch.tensor([pid+rid],device="cuda:0")
    lg=model(input_ids=ids).logits[0,:-1].float()
    lp=torch.log_softmax(lg,-1); tgt=ids[0,1:]
    tl=lp.gather(1,tgt[:,None])[:,0][len(pid)-1:]
    return float(tl.sum()), len(rid)
model=PeftModel.from_pretrained(base,ADAPTERS[0],adapter_name=Path(ADAPTERS[0]).name).eval()
names=["ref_"+Path(basep).name]+[Path(a).name for a in ADAPTERS]
if len(ADAPTERS)>1:
    for a in ADAPTERS[1:]: model.load_adapter(a,adapter_name=Path(a).name)
rows=[]
for setname,rowsin in sets:
    for i,r in enumerate(rowsin):
        rec={"set":setname,"i":i,"instr":r["instruction"][:40],"len_c":len(re.sub(r"\s+","",r["chosen"])),"len_r":len(re.sub(r"\s+","",r["rejected"])),
             "lines_c":len([l for l in r["chosen"].split("\n") if l.strip()]),"lines_r":len([l for l in r["rejected"].split("\n") if l.strip()])}
        with model.disable_adapter():
            rec["ref_c"],rec["tok_c"]=logp(model,r["system"],r["instruction"],r["chosen"]); rec["ref_r"],rec["tok_r"]=logp(model,r["system"],r["instruction"],r["rejected"])
        for a in ADAPTERS:
            nm=Path(a).name; model.set_adapter(nm)
            rec[nm+"_c"],_=logp(model,r["system"],r["instruction"],r["chosen"]); rec[nm+"_r"],_=logp(model,r["system"],r["instruction"],r["rejected"])
        rows.append(rec)
        if i%50==0: print(setname,i,flush=True)
    with open(OUT,"w") as f:
        for x in rows: f.write(json.dumps(x,ensure_ascii=False)+"\n")
print("done",flush=True)
