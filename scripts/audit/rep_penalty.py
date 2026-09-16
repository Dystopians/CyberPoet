"""实验 B：repetition_penalty 1.08 对标点/的/篇幅的影响。M4 同题同种子，两种罚。"""
import json, torch, re, sys
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1'); N=Path('/data/peilincai/CyberPoetTraining/claude_night_20260827')
OUT=Path(sys.argv[1]); ADAP=sys.argv[2]
SYS=(R/'prompts/poetry_system_v2.txt').read_text(encoding='utf-8').strip()
src=json.load(open(N/'quiz_v3/v12_sources_proposed.json'))
titles=[p["title"] for p in src["aa"]][:48]
tok=AutoTokenizer.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True); tok.padding_side='left'
if tok.pad_token is None: tok.pad_token=tok.eos_token
base=AutoModelForCausalLM.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True,torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
model=PeftModel.from_pretrained(base,ADAP).eval()
out=open(OUT,"w")
for rp in (1.0,1.08):
    for i in range(0,len(titles),8):
        chunk=titles[i:i+8]
        texts=[tok.apply_chat_template([{"role":"system","content":SYS},{"role":"user","content":f"以《{t}》为题写一首现代诗。"}],tokenize=False,add_generation_prompt=True,enable_thinking=False) for t in chunk]
        enc=tok(texts,return_tensors="pt",padding=True).to("cuda:0")
        torch.manual_seed(7000+i)
        with torch.no_grad():
            o=model.generate(**enc,max_new_tokens=560,do_sample=True,temperature=0.9,top_p=0.9,repetition_penalty=rp,pad_token_id=tok.pad_token_id)
        for t,sq in zip(chunk,o):
            body=tok.decode(sq[enc["input_ids"].shape[1]:],skip_special_tokens=True).strip()
            out.write(json.dumps({"rp":rp,"title":t,"body":body},ensure_ascii=False)+"\n")
        out.flush(); print(rp,i,flush=True)
print("done",flush=True)
