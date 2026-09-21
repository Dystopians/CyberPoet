"""LLaMA-Factory 启动器（09-21）：关掉 transformers 的显存预热再进训练。
原因：transformers 4.56 的 caching_allocator_warmup 在加载时先占一大块显存，14B 的 nf4 加载峰值因此到 26 GB 以上，
共卡时（只有 20–30 GB 空余）在加载阶段就 OOM（09-08 连死四次）。关掉后加载峰值 9.6 GB，训练稳态约 17 GB。
用法: CUDA_VISIBLE_DEVICES=<卡> python lf_nowarm.py <config.yaml>"""
import sys
import transformers.modeling_utils as mu
mu.caching_allocator_warmup = lambda *a, **k: None
from llamafactory.train.tuner import run_exp
run_exp()
