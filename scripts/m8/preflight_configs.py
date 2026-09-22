"""训练配置只读预检（09-22，Codex 评审建议 C3）：扫所有 yaml，凡写了 quantization_bit 的，quantization_method 必须是 bnb（LLaMA-Factory 0.9.5 的枚举值）；
写成 bitsandbytes 或别的值不报错、直接不量化（09-21 查明 93 份配置全中招）。用法: python3 preflight_configs.py [目录...]；退出码 1 = 有问题。"""
import sys, glob, os, yaml
dirs = sys.argv[1:] or ["/data/peilincai/CyberPoetTraining/claude_night_20260827/configs", "/data/peilincai/CyberPoetTraining/cyberpoet_repo/configs"]
bad = []
for d in dirs:
    for f in sorted(glob.glob(os.path.join(d, "*.yaml"))):
        try: c = yaml.safe_load(open(f, encoding="utf-8")) or {}
        except Exception as e: bad.append((f, f"yaml 解析失败: {e}")); continue
        if "quantization_bit" in c and c.get("quantization_method") != "bnb":
            bad.append((f, f"quantization_bit={c['quantization_bit']} 但 quantization_method={c.get('quantization_method')!r}（须为 bnb，否则静默不量化）"))
for f, why in bad: print("!!", f, "->", why)
print(f"扫描 {sum(len(glob.glob(os.path.join(d,'*.yaml'))) for d in dirs)} 份配置，问题 {len(bad)} 份")
sys.exit(1 if bad else 0)
