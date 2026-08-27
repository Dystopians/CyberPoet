"""四方对照生成：pt_sft / M1-e4 / M1-e5 / M1-e7，同题同种子。"""
import json, torch, random
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1")
W=Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
SYS_OLD=(R/"prompts/poetry_system.txt").read_text(encoding="utf-8").strip()
SYS_V2 =(R/"prompts/poetry_system_v2.txt").read_text(encoding="utf-8").strip()
def last_ck(d):
    cks=sorted(Path(d).glob("checkpoint-*"), key=lambda p:int(p.name.split("-")[1]))
    return str(cks[-1]) if cks else None
CONDS=[("pt_sft", str(W/"sft_repair/outputs/pt2_then_sft/checkpoint-950"), SYS_OLD),
       ("M1_e4", last_ck(W/"sft_repair/outputs/M1_e4_open"), SYS_V2),
       ("M1_e5", last_ck(W/"sft_repair/outputs/M1_e5_open"), SYS_V2),
       ("M1_e7", str(W/"sft_repair/outputs/M1_e7_open/checkpoint-710"), SYS_V2)]
CONDS=[c for c in CONDS if c[1]]
rng=random.Random(20260827)
title=[t for t in (json.loads(l) for l in open(W/"vocab_probe/probes_title.jsonl")) if "[" not in t["instruction"]]
imag =[json.loads(l) for l in open(W/"vocab_probe/probes_imagery.jsonl")]
tasks=rng.sample(title,6)+rng.sample(imag,6)
tok=AutoTokenizer.from_pretrained(R/"models/Qwen3-14B", trust_remote_code=True)
if tok.pad_token is None: tok.pad_token=tok.eos_token
print("加载基座 …",flush=True)
base=AutoModelForCausalLM.from_pretrained(R/"models/Qwen3-14B",trust_remote_code=True,
      torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
model=None; out={}
for tag,path,sys_txt in CONDS:
    if model is None: model=PeftModel.from_pretrained(base,path,adapter_name=tag)
    else: model.load_adapter(path,adapter_name=tag)
    model.set_adapter(tag); model.eval()
    for t in tasks:
        txt=tok.apply_chat_template([{"role":"system","content":sys_txt},
            {"role":"user","content":t["instruction"]}],tokenize=False,
            add_generation_prompt=True,enable_thinking=False)
        enc=tok([txt],return_tensors="pt").to("cuda:0"); torch.manual_seed(20260827)
        with torch.no_grad():
            o=model.generate(**enc,max_new_tokens=560,do_sample=True,temperature=0.85,
                             top_p=0.9,repetition_penalty=1.08,pad_token_id=tok.pad_token_id)
        out[(tag,t["id"])]=tok.decode(o[0,enc["input_ids"].shape[1]:],skip_special_tokens=True).strip()
        print(f"  {tag} {t['id']}",flush=True)
with open(W/"vocab_probe/gens_epoch_sweep.jsonl","w") as f:
    for t in tasks:
        f.write(json.dumps({"id":t["id"],"prompt":t["instruction"],
            "ref_author":t.get("ref_author"),"ref_id":t.get("ref_id"),
            **{tag:out[(tag,t["id"])] for tag,_,_ in CONDS}},ensure_ascii=False)+"\n")
print("完成",flush=True)
