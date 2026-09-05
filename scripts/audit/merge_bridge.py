"""把 sft_pt9 adapter 合并进 bf16 底座，存成完整权重（CPU 上做）。用途：让 LLaMA-Factory 的 disable_adapter() 参考 = SFT 桥。"""
import torch, sys
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
base_p, adap, out = sys.argv[1], sys.argv[2], sys.argv[3]
tok=AutoTokenizer.from_pretrained(base_p, trust_remote_code=True)
m=AutoModelForCausalLM.from_pretrained(base_p, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cpu")
m=PeftModel.from_pretrained(m, adap).merge_and_unload()
m.save_pretrained(out, safe_serialization=True, max_shard_size="5GB"); tok.save_pretrained(out)
print("merged ->", out, flush=True)
