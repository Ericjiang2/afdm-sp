# 全问题补充实验进度检查点（2026-09-10 A-01/S-01）

逐项状态只在 Mission CSV。本文只记录可回滚边界、现场作业和禁止声称，不关闭科学行，不复制确认数字。

**取代当前下一步：** [supplement-resume-20260910.md](supplement-resume-20260910.md) 仍是 DET 追加 runner / 16T 资格门的检查点，不再代表当前执行入口。

## 权威

- CSV：`.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv`
- 入口：[execution.md](../execution.md)
- 父任务：`09-05-budgeted-support-repair`（in_progress）
- 旧 v3 HOLD 与 D_test 仍封存
- Grok 会话：`01a08989-f9cb-7911-ad97-16886150db9e`（Codex 不可用后的主执行）接续 `01a08abd-ca21-7a23-bbe5-fb2727c20dd2`（本检查点）

## 绑定约束（全程有效）

- 主会话执行；不调 Codex；不为常规事项开子代理。
- 不重跑 16T，不改 16T NPZ 字节。冻结 v2 verifier 对 16T 仍记 FAIL；isclose 复核 PASS 另列。
- D1=BP80 只是 DET-01R 开发集选择冻结参考，**不是最优检测器**。
- H-01 / M-01 / I-02 / A-01 / S-01 都是开发，不是 F_H / F_M / F_A / F_I / F_R 确认。
- COST-02 正式计时独占，不与 A-01/S-01 同时打时间戳。
- S-01 无笛卡尔积；真 P 不进接收机；**G1 未准入**。
- 弱审查 = 过程见证，不是 fully independent auditor。

## 代码回滚点

| 提交 | 内容 |
|---|---|
| `5ad3c5bc` | A* 协议修订冻结（DET-01R） |
| `bac33c14` | D1_FREEZE BP80 |
| `b58f18f2` | H-01 准入/启动 |
| `4590b652` | H-01 harvest；M-01 cuda:0 |
| `1a421058` | M-01 harvest |
| `8e7eb9f5` | I-02 harvest |
| `5f6c5d5e` | A-01 启动 |
| `911d3d62` | A-01 CPU harvest 代码 |
| `839a492f` | S-01 runner + s01 protocol + source zip |
| `f8f2c775` | S-01 远端夹具/准入/启动收据 + CSV/STATE |

分支：`trans/tcom-main`。未 push。

## 冻结身份

- D1 SHA `4cb7a61722dcb014d0d1ceb8d567f6a66ea0c597ece15840a18658b0b93632b3`
- 旧 G0 data-protocol SHA `3b24ce24142a10b162ba577f71071795777ed6a93cf102ccefd268b34b439960`（**未改**）
- S-01 协议：`evidence/data-protocol-s01-v1.json`（G0 子集兼容，另加 integer/overlap/P4/P12/rho25/rho75；G1 `admitted=false`）
- S-01 源码 zip SHA `a70044a149d63ac6f4aa233348e0b3c4d8c359667ffd0a16b0a33ad783b83e33`
- checkpoint `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`

## 现场（写本文时）

远端根：`/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/`

| 作业 | tmux / sock | 状态 |
|---|---|---|
| A-01 | `g_afdm_supp_a01_mech_v1` `/data/guoyikun/tmp/g_afdm_supp_a01.sock` | 进行中；harvest 已 overlay，等 `a01-mechanism-queue-v1.exit==0` |
| S-01 | `g_afdm_supp_s01_scene_v1` `/data/guoyikun/tmp/g_afdm_supp_s01.sock` pane PID 285270 | 已启动 3456F；G1 不跑 |
| H-01 / M-01 / I-02 | 已退出 | 开发收数完成，exit 0 |

GPU：同卡共享，A-01 allocator 0.35、S-01 0.30。强碰撞门未触发。

## 本轮已做、未做

已做：

- 从 Grok 会话 `01a08989-...` 接手：H-01/M-01/I-02 已收数，A-01 已在跑。
- A-01 harvest 接到 runner 与远端 overlay，未在队列未完成时收数。
- S-01：counterexample 开发 split、单因素六单元、B_star、3456F；本地 17 项 + 远端 CPU 夹具 PASS；准入并与 A-01 同卡启动。
- CSV S-01 `dev_state=进行中`；STATE 指向 CSV。

未做 / 禁止声称：

- A-01、S-01 队列未结束，不得关行。
- G1 数值合同未写，S-01 不得跑 G1。
- CONF-\* 未冻结本家族 n/预算，未生成确认数据。
- COST-02 正式独占计时未准入；7/9 dB prior 仍缺。
- 未解封 D_test，未改论文主线，未称最优检测器，未重跑 16T。

## 下一步

1. `a01-mechanism-queue-v1.exit==0` 后 CPU harvest → `evidence/a-01.json`。
2. `s01-counterexample-queue-v1.exit==0` 后 CPU harvest → `evidence/s-01.json`（G1 仍记 blocked）。
3. 不与 COST-02 正式计时并行。CONF-\* 等各自开发依赖与家族冻结。
