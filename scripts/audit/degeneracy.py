"""实验 F：不加重复罚(rp=1.0)时各阶段模型是否自发复沓/碎行。多臂同题同种子，rp 1.0 与 1.08 各一遍。
用法: degeneracy.py out.jsonl  arm=base|adapter_path[:base_path] ..."""
import json, torch, sys, gc
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1'); N=Path('/data/peilincai/CyberPoetTraining/claude_night_20260827')
OUT=Path(sys.argv[1]); ARMS=sys.argv[2:]
SYS=(R/'prompts/poetry_system_v2.txt').read_text(encoding='utf-8').strip()
src=json.load(open(N/'quiz_v3/v12_sources_proposed.json')); titles=[p["title"] for p in src["aa"]][:48]
tok=AutoTokenizer.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True); tok.padding_side='left'
if tok.pad_token is None: tok.pad_token=tok.eos_token
out=open(OUT,"a")
for spec in ARMS:
    name,_,rest=spec.partition("=")
    adap,_,basep=rest.partition(":")
    basep=basep or str(R/'models/Qwen3-14B')
    base=AutoModelForCausalLM.from_pretrained(basep,trust_remote_code=True,torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
    model=PeftModel.from_pretrained(base,adap).eval() if adap not in ("","none") else base
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
                out.write(json.dumps({"arm":name,"rp":rp,"title":t,"body":body},ensure_ascii=False)+"\n")
            out.flush()
        print(name,rp,"done",flush=True)
    del model,base; gc.collect(); torch.cuda.empty_cache()
print("done",flush=True)
