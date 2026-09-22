# v14 臂表（09-21）：训练计划第五节第 3 条的补丁——若按验证票选出的 M8 几乎没训（训练奖励差 <1.0），
# 训后流程会另出工作点臂 M8w 的候选（v14_cands_M8w.jsonl）；此时「对桥」那 20 局改成 M8w 对 M8sft。
# 09-22：Codex 评审建议的消融臂 M8n（偏好数据去掉 v1 时代对）若有候选（v14_cands_M8n.jsonl），加 20 局 M8 对 M8n。
# 各制卷脚本统一从这里取臂表，文件在不在就是开关，不手改脚本。
import os
HAS_W = os.path.exists('v14_cands_M8w.jsonl')
HAS_N = os.path.exists('v14_cands_M8n.jsonl')
ARMS = ("M8", "M8sft", "M4") + (("M8w",) if HAS_W else ()) + (("M8n",) if HAS_N else ())
DUEL_A = "M8vsM4"
DUEL_B = "M8wvsM8sft" if HAS_W else "M8vsM8sft"
LEAD_B = "M8w" if HAS_W else "M8"
DUEL_C = "M8vsM8n" if HAS_N else None
