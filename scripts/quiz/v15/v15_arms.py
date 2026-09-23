# v15 臂表（09-22，实验 1「M4R」）：四个候选文件都在 M4 的底座上——
#   M4 = 现役（尺子）；M4R = M4 的桥合并后做「参考=桥、v6 主人票」偏好训练的末档（3 轮训满）；M4sft = 那座桥本身，不做偏好训练；
#   M4Rw = 同一次训练里奖励差≈2 的工作点存档，只做替补：若 M4R 末档出厂面板不过线（撞顶 >20% 或字数中位 >340），把 SWAP_W 改 True 用它顶替 M4R。
# 三种对决：A = M4R 对 M4（本卷的问题）；B = M4R 对 M4sft（偏好训练修法有没有改变桥）；C = M4 对 M4sft（M4 当年的偏好训练有没有用）。
import os
SWAP_W = False
MAIN = "M4Rw" if SWAP_W else "M4R"
ARMS = (MAIN, "M4sft", "M4")
HAS_W = False; HAS_N = False           # 不再按文件开关；M4Rw 只做替补
DUEL_A = f"{MAIN}vsM4"
DUEL_B = f"{MAIN}vsM4sft"
LEAD_B = MAIN
DUEL_C = "M4vsM4sft"
QUOTA_AA = {DUEL_A: 30, DUEL_B: 15, DUEL_C: 15}
QUOTA_HA = {MAIN: 12, "M4sft": 6, "M4": 6}
