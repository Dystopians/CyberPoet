"""通用出厂检面板生成：与历代同 66 题×3 种子（同参同提示）。用法: gen_panel_arm.py <臂名> <adapter路径>"""
import json, torch, gc, sys
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path('/data/peilincai/CyberPoetTraining/cyberpoet_v1'); N=Path('/data/peilincai/CyberPoetTraining/claude_night_20260827')
SYS=(R/'prompts/poetry_system_v2.txt').read_text(encoding='utf-8').strip()
srcs=json.load(open(N/'quiz_v3/v7_ha_sources.json'))
tok=AutoTokenizer.from_pretrained(R/'models/Qwen3-14B',trust_remote_code=True)
tok.padding_side='left'
if tok.pad_token is None: tok.pad_token=tok.eos_token
ARM=sys.argv[1]; ADAPTER=sys.argv[2]
BASE=sys.argv[3] if len(sys.argv)>3 else "models/Qwen3-14B"   # 09-02：M7F 的 LoRA 段挂在 pt9F_s2 全参权重上，底座可指定（绝对路径）
OUTP=sys.argv[4]; SEEDS=[(int(x),t) for x,t in zip(sys.argv[5].split(','),(0.85,0.9,0.95)[-len(sys.argv[5].split(',')):])]
out=open(OUTP,'w',encoding='utf-8')
ARMS=[(ARM+"_dpo", BASE, ADAPTER)]
for arm, basep, adap in ARMS:
    base=AutoModelForCausalLM.from_pretrained(basep if basep.startswith('/') else R/basep,
        trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()
    model=PeftModel.from_pretrained(base, adap).eval()
    for seed,temp in SEEDS:
        for i in range(0,len(srcs),8):
            chunk=srcs[i:i+8]
            texts=[tok.apply_chat_template([{"role":"system","content":SYS},
                {"role":"user","content":f"以《{s['title']}》为题写一首现代诗。"}],tokenize=False,
                add_generation_prompt=True,enable_thinking=False) for s in chunk]
            enc=tok(texts,return_tensors="pt",padding=True).to("cuda:0")
            torch.manual_seed(seed+i)
            with torch.no_grad():
                o=model.generate(**enc,max_new_tokens=560,do_sample=True,temperature=temp,
                    top_p=0.9,repetition_penalty=1.08,pad_token_id=tok.pad_token_id)
            for s,sq in zip(chunk,o):
                body=tok.decode(sq[enc["input_ids"].shape[1]:],skip_special_tokens=True).strip()
                out.write(json.dumps({"arm":arm,"src_id":s["id"],"title":s["title"],
                    "seed":seed,"body":body},ensure_ascii=False)+"\n")
            out.flush()
        print(arm,seed,"done",flush=True)
    del model,base; gc.collect(); torch.cuda.empty_cache()
print("完成",flush=True)
