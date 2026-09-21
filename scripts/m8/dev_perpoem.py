"""开发集按篇全量重算（修 09-16 复核发现的口径问题：LLaMA-Factory 分片 packing 只算了 221 首的 58%）。
逐篇不打包、截断 2048 token、正文后加 <|im_end|>（与预训练处理一致），nf4 底座（与训练前向一致）。
输出每个存档：按篇平均 NLL、按 token 加权 NLL、去掉 4 篇超长文后的按篇平均。"""
import json, sys, torch, time
import transformers.modeling_utils as mu
mu.caching_allocator_warmup = lambda *a, **k: None
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
N="/data/peilincai/CyberPoetTraining/claude_night_20260827"
OUT=sys.argv[1]; CKPTS=sys.argv[2:]
tok=AutoTokenizer.from_pretrained(N+"/outputs/nf4_Qwen3-14B",trust_remote_code=True)
dev=[r["text"] for r in json.load(open(N+"/data/pt5_dev.json"))]
eos=tok.convert_tokens_to_ids("<|im_end|>")
enc=[]
for t in dev:
    ids=tok(t,add_special_tokens=False)["input_ids"]+[eos]
    enc.append((len(ids),ids[:2048]))
long_idx={i for i,(n,_) in enumerate(enc) if n>2048}
print("dev docs",len(enc),"tokens",sum(n for n,_ in enc),"long(>2048):",len(long_idx),flush=True)
base=AutoModelForCausalLM.from_pretrained(N+"/outputs/nf4_Qwen3-14B",trust_remote_code=True,torch_dtype=torch.bfloat16,device_map={"":0}).eval()
@torch.no_grad()
def run(model):
    per=[];tot=0.0;ntok=0
    for n,ids in enc:
        x=torch.tensor([ids],device="cuda:0")
        lg=model(input_ids=x).logits[0,:-1].float()
        nll=torch.nn.functional.cross_entropy(lg,x[0,1:],reduction="sum").item()
        k=len(ids)-1; per.append(nll/k); tot+=nll; ntok+=k
    import statistics as st
    short=[p for i,p in enumerate(per) if i not in long_idx]
    return {"per_doc_mean":st.mean(per),"token_weighted":tot/ntok,"per_doc_mean_nolong":st.mean(short),"per_doc_median":st.median(per)}
res={}
res["base"]={"per_doc_mean":4.762467352975371,"token_weighted":4.508997243695554,"per_doc_mean_nolong":4.778146714059676,"per_doc_median":4.802523268866785}  # 已算过（nf4 裸底座）
model=None
for ck in CKPTS:
    name=ck.replace(N+"/outputs/","")
    t=time.time()
    nm=f"ck{len(res)}"   # 名字不能含在 "lora_" 里（PEFT 会按名字替换键名），每个存档用独立名字
    if model is None: model=PeftModel.from_pretrained(base,ck,adapter_name=nm).eval()
    else:
        model.load_adapter(ck,adapter_name=nm); model.set_adapter(nm)
        for old_nm in [a for a in list(model.peft_config) if a!=nm]: model.delete_adapter(old_nm)
    res[name]=run(model); print(name,{k:round(v,4) for k,v in res[name].items()},f"{time.time()-t:.0f}s",flush=True)
    json.dump(res,open(OUT,"w"),indent=1)
print("done",flush=True)
