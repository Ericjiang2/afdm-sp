# afdm-sp — AFDM 研究只读镜像（供 GPT 阅读）

项目：AFDM Deep-Unfolded Joint Channel Estimation and Detection（SP-AFDM，`afdm-e2e-main`）。
本仓库是本地研究 vault 中 `00_Inbox/AFDM-channel-estimation/` 的**已提交快照**，由 `.sync/sync.sh` 生成；
每个 commit 消息记录对应的 vault commit hash。不要在此仓库直接修改。

## 阅读顺序

1. [STATE.md](STATE.md) — 当前真相、阶段、blocker、下一步（最新段落在最上）。
2. [research-assets/index.md](research-assets/index.md) — 已接受/草稿结论卡片 `res-YYYYMMDD-NN`（含出处、局限、取代链）。只有卡片才算已接受结论。
3. [.trellis/spec/research-protocol.md](.trellis/spec/research-protocol.md) — 跨任务研究规则。
4. `.trellis/tasks/<task>/` — 各任务的 `prd.md`、`research/` 推导与规格。
5. 代码主线：[afdm_sp_joint_unrolled/classical_joint_unrolled.py](afdm_sp_joint_unrolled/classical_joint_unrolled.py)（classical joint OMP-MP 的可微展开），评估入口 [paired_learned_eval.py](afdm_sp_joint_unrolled/paired_learned_eval.py)。
6. 实验输出：`afdm_sp_joint_unrolled/outputs_*/`、`results/`、`experiments/`（`results.json` 含 `_argv` / `_config` 复现字段）。
7. 论文：`paper/`、`paper-tmlcn/`、`tcom_plan/`。
8. 历史（2026-07-26 前，只读）：[_archive/legacy_records_20260726/_QA_Index.md](_archive/legacy_records_20260726/_QA_Index.md)。

## 镜像中被排除的内容

- `.mission/`、`.claude/`、`.codex/`、`.agents/`（agent 运行痕迹）。`STATE.md` 中指向 `.mission/...csv` 的链接在此会失效。
- 二进制数据：`*.npz *.npy *.pt *.pth *.ckpt *.mat *.pkl *.h5 *.gz *.zip *.tar *.fig` 等。
- 单文件 > 50 MB。
- vault 中尚未 commit 的改动。

原项目 README（早期 OTFS 学习说明）不再作为入口。
