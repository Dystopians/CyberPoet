# scripts · 索引

分析与工程脚本。**不含语料、不含模型权重**——数据路径都指向仓库外的本地目录。

| 目录 | 内容 |
|---|---|
| `audit/` | **训练审计**：权重差分尸检三件套。任何新训练方式首次落地必跑 |
| `analysis/` | 生成结果的分布分析（长度/失败模式/带宽）|
| `preference/` | 偏好数据与标注页的构建（配对、生成、页面装配）|
| `pretrain/` | 预训练侧的数据准备与轮次对照、逐字重合度测量 |
| `sft_repair/` | SFT 数据的修复与切分 |
| `corpus_fix/` | 语料定点修复（洛夫假分节/双倍行距）|

## audit/ —— 最该先看的三个

| 脚本 | 回答什么问题 | 成本 |
|---|---|---|
| `weigh_fullparam.py` | **训练到底发生了没有？** 逐权重比对新模型与基座：零变化参数占比、逐层 ‖Δ‖/‖W‖、输出头是否动过 | CPU 几分钟 |
| `weigh_ulp_test.py` | 零变化是**数值精度地板**还是调度没覆盖？（判据：未变权重是否系统性更大）| CPU 几分钟 |
| `weigh_crossover.py` | 精度地板机制的**定量预言检验**：零变化率是否在 \|w\|≈ULP 临界处出现悬崖 | CPU 几分钟 |

这三个脚本是 08-29 那次尸检的产物——它们查出全参臂 **79.56% 的参数逐比特未变**，
把「全参路线不行」这个结论从方法失败改判为配置失败。
结论见 `../docs/证据链/11-全参失败根因尸检.md`。

**教训固化**：跑完了、loss 有数字、生成不是乱码，这三件事都不能证明训练发生了。
新训练方式首次落地，先跑 `audit/weigh_fullparam.py` 或 `audit/check_weight_diff.py`；**09-02 口径：零变化率 >70% 且 ‖Δ‖/‖W‖ <5e-4 才是未训签名，单看占比不熔断**。

## audit/ —— 09-05 归因与 09-16 复核用到的脚本

| 脚本 | 回答什么问题 | 成本 | 已知局限 |
|---|---|---|---|
| `score_pairs.py` | DPO 每一对的开局差距与梯度权重（原版） | GPU 30 min | **用 HF 模板带空 think 块，与训练格式差 4 个 token，数字偏大两三成**；留作可复现件 |
| `score_pairs_trainfmt.py` | 同上，训练格式（真值） | GPU 30 min | — |
| `analyze_margins.py` | 汇总打分结果：权重分布、加权长度差 | CPU | 按来源分组，未按反例身份分组 |
| `degeneracy.py` | 关/开重复罚下的整行复读率 | GPU 10 min/臂 | 48 题只能分辨 20 个百分点；题集 40/48 在 sft_v4 内 |
| `analyze_gens.py` / `compare_panels.py` | 生成形状统计（字数、字/行、碎行率、标点、重复行） | CPU | 面板数字须标口径 |
| `merge_bridge.py` | 把 SFT 桥合并成完整权重（参考=桥 DPO 的前置） | CPU 5 min | 合并后 nf4 加载 |
| `check_weight_diff.py` | 全参训练中途/段末权重差分（第 3 参数为已轮到层） | CPU 几分钟 | — |
| `think_block.py` / `rep_penalty.py` | 空 think 块 / 重复罚对生成形状的影响 | GPU 10 min | 48 题非配对；两者共用同一份 rp=1.08 样本 |
| `quant_mismatch.py` | nf4 训、bf16 推的 dev 损失差 | GPU 5 min | dev 145 条；两臂都带空 think 块，不可与训练日志相减 |
| `gen_panel_seeds.py` | 指定底座 + adapter + 种子出面板 | GPU 20 min/198 首 | — |
| `run_epoch_loop_exp.sh` / `run_rca2_card*.sh` | 实验 G 与 09-16 补充实验的串行脚本 | — | 服务器绝对路径 |

另：`dpo/build_dpo_next.py` 从主人票建当代偏好对（真人不做正例、「都不要」不入）；`quiz/gate_v10.py` 候选门控。
