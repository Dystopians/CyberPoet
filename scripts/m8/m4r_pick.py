# M4R 存档选择（09-22，主人：不按验证损失挑）：末档 = M4R；训练奖励差最接近 2.0 的存档 = M4Rw。输出 m4r_dpo_choice.json，打印「末档 工作点」。
import json, glob, os, sys
D = sys.argv[1] if len(sys.argv) > 1 else "/data/peilincai/CyberPoetTraining/claude_night_20260827/outputs/dpo_m4r"
cks = sorted(int(p.split("-")[-1]) for p in glob.glob(D + "/checkpoint-*"))
st = json.load(open(D + "/trainer_state.json"))
tr = [h for h in st["log_history"] if "loss" in h and "eval_loss" not in h]
def margin(step):
    near = [h for h in tr if h["step"] <= step][-3:]
    return sum(h.get("rewards/margins", 0) for h in near) / max(1, len(near))
last = cks[-1]; work = min(cks, key=lambda s: abs(margin(s) - 2.0))
ev = {h["step"]: round(h["eval_loss"], 4) for h in st["log_history"] if "eval_loss" in h}
json.dump({"last": last, "work": work, "margins": {s: round(margin(s), 3) for s in cks}, "eval_loss": ev}, open(os.path.dirname(D.rstrip("/")) + "/../m4r_dpo_choice.json", "w"), indent=1)
print(last, work)
