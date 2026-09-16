# artifacts/night_20260827 · 08-27 夜训过程件

- `pw_new_poems.json`（爬取诗歌 42 万字）、`dpo_train.json`（290 对含正反例正文，其中 31 行真人诗做正例、4 行做反例）、`quiz_pairs_final.json`（题组含真人诗）三份文件**因含诗歌正文已于 2026-09-16 从工作区移除**。它们从未进入 git（`.gitignore` 的 `*.json` 规则），不需要改写历史。服务器原件：`claude_night_20260827/pw_crawl/`、`claude_night_20260827/data/dpo_train.json`、`claude_night_20260827/quiz_v3/`。
- `labels_night_quiz.json` 只有票（pk / A / B / choice），无正文；留在工作区，同样不入库。
- `build_dpo.py` 引用的是服务器绝对路径，不受影响。
- git 历史里唯一含真人原作的是提交 `0101729` 的阅读包 html（30 首，08-29 已从当前版本移除）；是否重写历史由主人决定。
