"""把验证损失从头算一遍：逐 token 的交叉熵，看它到底在惩罚什么。"""
import json, torch, math
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
R=Path("/data/peilincai/CyberPoetTraining/cyberpoet_v1"); W=Path("/data/peilincai/CyberPoetTraining/claude_parallel_20260825")
CK=str(W/"pretrain/outputs/e8/checkpoint-398")   # 2 轮，验证损失最低的那个
tok=AutoTokenizer.from_pretrained(R/"models/Qwen3-14B",trust_remote_code=True)
base=AutoModelForCausalLM.from_pretrained(R/"models/Qwen3-14B",trust_remote_code=True,
      torch_dtype=torch.bfloat16,device_map="cuda:0").eval()
model=PeftModel.from_pretrained(base,CK).eval()
dev=json.load(open(W/"pretrain/data/pt_dev.json"))

def poem_loss(text, detail=False):
    ids=tok(text+tok.eos_token, add_special_tokens=False, return_tensors="pt").input_ids.to("cuda:0")
    with torch.no_grad():
        logits=model(ids).logits.float()
    # 第 i 个位置的输出用来预测第 i+1 个 token
    lp=torch.log_softmax(logits[0,:-1],-1)
    tgt=ids[0,1:]
    tok_loss=-lp[torch.arange(len(tgt)),tgt]        # 每个 token 的 -log p
    if detail:
        print(f"  这首诗有 {len(tgt)} 个待预测 token")
        print(f"  {'位置':>4} {'真实下一个字':<10} {'模型给它的概率':>12} {'该 token 损失':>12}  模型最想接的字")
        for i in list(range(6))+[len(tgt)//2, len(tgt)-2]:
            top=lp[i].argmax().item()
            print(f"  {i:>4} {repr(tok.decode([tgt[i]])):<12} {math.exp(-tok_loss[i].item()):>12.4f} {tok_loss[i].item():>12.3f}  {repr(tok.decode([top]))}")
        print(f"  → 这首诗的损失 = 所有 token 损失的平均 = {tok_loss.mean().item():.4f}")
    return tok_loss.mean().item(), len(tgt)

print("═══ 单首诗的逐字明细 ═══")
p=dev[0]["text"]
print("诗（前 40 字）:", p[:40].replace("\n"," / "))
poem_loss(p, detail=True)

print("\n═══ 整个开发集 189 首 ═══")
tot=[]
for i,d in enumerate(dev):
    l,n=poem_loss(d["text"]); tot.append(l)
    if (i+1)%60==0: print(f"  已算 {i+1}/189，当前平均 {sum(tot)/len(tot):.4f}",flush=True)
mean=sum(tot)/len(tot)
print(f"\n  189 首各自损失的平均 = {mean:.4f}")
print(f"  （训练日志里 checkpoint-398 记的是 4.0674）")
print(f"  换算成困惑度 = e^{mean:.4f} = {math.exp(mean):.1f}")
print(f"  意思是：模型预测下一个字时，相当于在 {math.exp(mean):.0f} 个字里犹豫")
import statistics
print(f"  最容易的一首 {min(tot):.3f}，最难的一首 {max(tot):.3f}，中位 {statistics.median(tot):.3f}")
