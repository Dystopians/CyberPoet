"""M8 偏好训练选存档（规则训前写死，见 configs/dpo_m8.yaml 头注与训练计划_M8_20260921）：
① 验证损失最低的存档；② 与最低值差 <0.01 的算并列，取最早的；③ 面板字数中位须在 120–300，否则向更早一档退（由 run_m8_post.sh 逐档验）。
输出 m8_dpo_choice.json：{"order":[首选步, 更早一档, ...], "table":[每档 验证损失/验证准确率/验证奖励差/训练奖励差]}"""
import json, glob, os
N = "/data/peilincai/CyberPoetTraining/claude_night_20260827/"
cks = sorted(glob.glob(N + "outputs/dpo_m8/checkpoint-*"), key=lambda p: int(p.split("-")[-1]))
st = json.load(open((N + "outputs/dpo_m8/trainer_state.json") if os.path.exists(N + "outputs/dpo_m8/trainer_state.json") else cks[-1] + "/trainer_state.json"))
ev = {h["step"]: h for h in st["log_history"] if "eval_loss" in h}
tr = [h for h in st["log_history"] if "loss" in h and "eval_loss" not in h]
def train_margin(step):
    near = [h for h in tr if h["step"] <= step][-3:]
    return sum(h.get("rewards/margins", 0) for h in near) / max(1, len(near))
have = [int(p.split("-")[-1]) for p in cks]
table = [{"step": s, "eval_loss": round(ev[s]["eval_loss"], 4), "eval_acc": round(ev[s].get("eval_rewards/accuracies", float("nan")), 3),
          "eval_margin": round(ev[s].get("eval_rewards/margins", float("nan")), 3), "train_margin_last3": round(train_margin(s), 3)} for s in sorted(ev) if s in have]
best = min(t["eval_loss"] for t in table)
tied = [t["step"] for t in table if t["eval_loss"] - best < 0.01]
first = min(tied)
order = [first] + sorted([t["step"] for t in table if t["step"] < first], reverse=True)
json.dump({"order": order, "best_eval_loss": best, "tied": tied, "table": table}, open(N + "m8_dpo_choice.json", "w"), ensure_ascii=False, indent=1)
for t in table: print(t)
print("验证损失最低", best, "并列", tied, "→ 首选 checkpoint-%d；退档顺序 %s" % (first, order[1:]))
