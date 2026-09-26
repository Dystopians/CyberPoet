# v16 臂表（09-25，实验 2「pt6+散文」）：两臂同底不同语料——
#   M4 = 现役（尺子，pt6 语料）；M4P = M4 配方一字不改、预训练只多加 301 篇散文（outputs/dpo_pt6p）。
# 素材全部来自 v15 题表里没上卷的槽（金标 21、命题 29）：M4 候选沿用 v15 的（未上卷正文），M4P 候选新生成（同题同种子）。
# 标准局（AI 对主人 v15 纯人对里选中的诗人的诗）等 v15 结果码到了再加。
MAIN = "M4P"
ARMS = ("M4P", "M4")
HAS_W = False; HAS_N = False
DUEL_A = "M4PvsM4"; DUEL_B = None; DUEL_C = None; LEAD_B = MAIN
QUOTA_AA = {DUEL_A: 50}   # 29 道沿用 v15 未上卷命题 + 70 道新命题（titles_v16_aa.json）
QUOTA_HA = {"M4P": 10, "M4": 10}
