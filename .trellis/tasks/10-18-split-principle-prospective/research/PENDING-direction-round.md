# PENDING：方向评审（"先独立、后对照"），等 Codex 额度恢复

- 状态：**暂停**（2026-10-18）。Codex 不可用（网络或额度），用户说额度恢复后会通知。
- 已完成：编排者的独立判断已先行提交：`direction-claude-20261018.md`（commit 4d2f8b60）。
- 待做：
  1. 用 `direction-codex-prompt.txt` 原样运行 Codex（gpt-6.1-sol，xhigh，`--search`，只读）。运行时不得给它看编排者的结论。
  2. 生成分歧表（编排者 vs Codex）。
  3. 用户拍板论文主线。
  4. 同时请用户验收 5 张 draft 卡：res-20261017-04（先加收窄注记）、res-20261018-01、-02（补分簇说明）、-03、-04。
- 恢复命令（在项目根目录运行）：
  `codex --search exec -s read-only -m gpt-6.1-sol -c model_reasoning_effort="xhigh" -C "$PWD" -o <scratch>/codex_direction.md "$(cat .trellis/tasks/10-18-split-principle-prospective/research/direction-codex-prompt.txt)" </dev/null`
- 另一项未完成：E-1/E-2/E-3/E-3b 的 CI 需要按帧重新分簇复算（可以用 Codex 的 `tf_covariance_audit_20261018/sampling.py`），然后在各卡上加更正注记。这一项不依赖 Codex，可以随时做。
