"""把 bf16 权重量化成 nf4 并存盘（预量化检查点）。目的：以后加载时不再有「先把整份 bf16 拉上卡再量化」的 26–28 GB 峰值，
共卡（只有 ~20 GB 空余）也能训。量化口径与 LLaMA-Factory on-the-fly 完全一致（nf4 + double quant + compute/storage bf16）。
用法: prequantize.py <src_dir> <dst_dir> [--nowarm]"""
import sys, torch, time
import transformers.modeling_utils as mu
if "--nowarm" in sys.argv:
    mu.caching_allocator_warmup = lambda *a, **k: None   # 关掉 transformers 的显存预热（它会先占一大块）
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
src, dst = sys.argv[1], sys.argv[2]
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                       bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_storage=torch.bfloat16)
t = time.time()
m = AutoModelForCausalLM.from_pretrained(src, trust_remote_code=True, quantization_config=q, torch_dtype=torch.bfloat16, device_map={"": 0})
print(f"loaded in {time.time()-t:.0f}s | peak allocated {torch.cuda.max_memory_allocated()/2**30:.1f} GiB | peak reserved {torch.cuda.max_memory_reserved()/2**30:.1f} GiB | now allocated {torch.cuda.memory_allocated()/2**30:.1f} GiB", flush=True)
m.save_pretrained(dst, safe_serialization=True)
AutoTokenizer.from_pretrained(src, trust_remote_code=True).save_pretrained(dst)
print("saved ->", dst, flush=True)
