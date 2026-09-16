"""实验 C：QLoRA 训练(nf4底座) 与 推理(bf16底座) 的失配。同一 adapter 在两种底座上算 SFT dev 损失。"""
import json, torch, sys, math
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
R=Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1'); N=Path('/data/peilincai/CyberPoetTraining/claude_night_20260827')
ADAP=sys.argv[1]; OUT=sys.argv[2]; MODES=sys.argv[3].split(",")
tok=AutoTokenizer.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True)
dev=json.load(open(N/'data/sft_dev_v3.json'))[:150]
def seqs():
    for r in dev:
        p=tok.apply_chat_template([{"role":"system","content":r["system"]},{"role":"user","content":r["instruction"]+("\n"+r["input"] if r["input"] else "")}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        pid=tok(p,add_special_tokens=False)["input_ids"]; rid=tok(r["output"]+"<|im_end|>\n",add_special_tokens=False)["input_ids"]
        yield pid,rid
@torch.no_grad()
def devloss(model):
    tot=0.0; n=0
    for pid,rid in seqs():
        ids=torch.tensor([pid+rid],device="cuda:0")
        lg=model(input_ids=ids).logits[0,:-1].float(); lp=torch.log_softmax(lg,-1)
        tl=lp.gather(1,ids[0,1:][:,None])[:,0][len(pid)-1:]
        tot+=-float(tl.sum()); n+=len(rid)
    return tot/n
res={}
for mode in MODES:
    if mode=="nf4":
        q=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
        base=AutoModelForCausalLM.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True,quantization_config=q,device_map="cuda:0",torch_dtype=torch.bfloat16).eval()
    else:
        base=AutoModelForCausalLM.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True,torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
    res[mode+"_base"]=devloss(base)
    m=PeftModel.from_pretrained(base,ADAP).eval()
    res[mode+"_adapter"]=devloss(m)
    print(mode,res,flush=True)
    del m,base; torch.cuda.empty_cache()
json.dump(res,open(OUT,"w"),indent=1); print("done",res,flush=True)
