# afdm-e2e-main | AFDM Deep-Unfolded Joint Channel Estimation and Detection

## 启动规则（单轨：Trellis）

新对话开始时只做这一件事：
读 `STATE.md`（1–2 屏当前真相），输出一句话状态摘要，然后等待指令。
任务状态由 `.trellis/` 注入的 workflow-state 提供，不要主动读其他文件。

## 记录系统（2026-07-26 起）

| 内容 | 唯一位置 |
|------|----------|
| 当前真相/阶段/blocker/下一步 | `STATE.md`（只在真相变化时更新） |
| 当前全部待办 + 开放线索（有意思但未认证、值得追） | `STATE.md` 的"待办与开放线索"段（唯一权威；journal/台账里的下一步只是快照） |
| 已否定的线索/方向 | `.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md` |
| 跑前预测与打分 | `research-assets/prediction-ledger.md` |
| 任务意图/执行/验收 | `.trellis/tasks/<task>/`（prd.md 等） |
| 提炼结论（含出处/局限/取代链） | `research-assets/`（`res-YYYYMMDD-NN` 卡片 + index.md） |
| 跨任务稳定规则 | `.trellis/spec/research-protocol.md` |
| Raw 实验输出 | `afdm_sp_joint_unrolled/outputs_*`（原地不动，不可变证据） |
| 2026-07-26 前全部旧记录 | `_archive/legacy_records_20260726/`（只读，入口 `_QA_Index.md`） |

硬性规则：
- 旧归档只读，永不追加；查历史结论先看归档内 `_QA_Index.md` 倒序索引
- 结果只有拿到 `res-YYYYMMDD-NN` 资产卡才算"已接受真相"；STATE.md 引用卡片而不复制数字
- 取代旧结论必须显式 supersession（卡片互链），不许静默改写
- research parent 的关闭需用户显式验收；implementation child 完成 ≠ parent 完成

## Git 提交规范 (历史教训沉淀)

**背景**: 2026-03-27 (`df499c8`) → 2026-04-28 (`5056b7b` "FYP final state" squash) 整 32 天没 commit, 导致 4/23 paper eval 跑出 -37.7% / -48% headline 数字但**生成它的代码版本永久丢失** (QA #23-25 forensic 调查耗 3 天才靠 bash_history + outputs/results.json + paper_figure_code/ 三重冗余勉强重建). 永远不允许重蹈。

### 核心原则
1. **No long gaps**: 工作 session 结束前必须 commit, 哪怕 empty commit (`git commit --allow-empty -m "WIP: <state>"`). 超过 4 小时无 commit 就是预警.
2. **Boundary commits**: paper-cited eval 跑前跑后**各 commit 一次** (`before/after <X> eval`). 不要"等数据出来再决定要不要 commit".
3. **One commit per logical unit**: 一个 experiment / task / forensic investigation = 一个 commit. 不要把 5 件不相关的事塞一起 — squash 压扁就是 32-day gap 教训本源.
4. **Sync records**: commit 涉及真相变化时同步更新 `STATE.md`；提炼结论落 `research-assets/` 卡片；执行细节留在 `.trellis/tasks/<task>/`.

### Results.json reproducibility fingerprint (必备字段)
`paired_learned_eval.py` 已 enforce (QA #26 patch). 任何新 eval 脚本必须同等:
- `_argv`: 完整 `sys.argv` list — 永久 reproducible CLI 不依赖 shell history
- `_config`: 所有 flag 的运行时实际值 (use_hard / refine_rounds / cand_topm / defer_prune / protect_added / no_prune / tau_lookup / target_errors / min_frames / cdtype 等)

→ 不允许只靠 bash_history 重建 paper-cited 数字 (虽然 QA #25 救了一命, 这是 bug 不是 feature)

### Commit message 格式
- 第一行 ≤ 70 字符, 动词开头, 描述性 (例: "W8 ablation: SNR-weighted training is regime-dependent")
- 空行 + body: what + why + mechanism (不只是 what)
- HEREDOC 防 shell quoting 错乱

### Anti-patterns (历史踩过的坑)
- ❌ **"等做完一批再 commit"**: 一批做完后 `git add -p` 时已迷失方向 → 32-day gap 直接原因
- ❌ **Bash history-only reproducibility**: bash_history 是 forensic 兜底, 不是主 reproducibility 源
- ❌ **Squash commit 压月级 state**: `5056b7b` 教训 — 把多个 working tree state 压成一个 commit = 永久丢失中间状态
- ❌ **"跑完看看再决定要不要 commit"**: 跑得越久越懒得 commit, 越容易出 gap
- ❌ **跨项目混 commit**: 一个 commit 同时改 sibling 项目 (`../AFWDM_AFDM_CP/`) — 分开 commit

### .gitignore 边界
- **永不 commit**: ckpt (`*.pt`), 大 npz/npy, outputs_*/ 默认排除, secrets / credentials / API keys
- **显式 whitelist**: paper-cited tiny JSON (示例: `!afdm_sp_joint_unrolled/outputs_loop13_4B_retrain27k_snr25_eval/`, `!*/results.json`)
- 新增 paper-cited 结果文件必须在 `.gitignore` 显式 `!` whitelist, 否则会被默认规则吞掉

### Commit checklist (每次必走)
1. `git status --short` 确认 staged files 都相关 (不要混进 sibling project / 临时 scratch)
2. `git diff --staged` 看实际改动是否符合预期
3. `git log --oneline -5` 看最近 commits 格式
4. HEREDOC commit message (with body, with Co-Authored-By)
5. `git status` 确认 commit succeeded (working tree clean)
6. **不 push** (除非 user 明确说 "推送/push")
7. 不 amend 已有 commit (除非 user 明确说) — 永远 new commit, hook 失败也是 new commit

### 长 session 节奏
- 写代码 / 跑 smoke / 拿初步信号 → commit (state checkpoint)
- 起长训练 (>30 min GPU) 前 → commit `before <X> training`
- 训练完成 + eval 出数 → commit `after <X> eval, <main finding>`
- task / paper section 完工 → commit `<task> complete: <summary>`

→ 一个 active 工作日 (~6-8 hr) 应该 3-6 commits, 不是 1 个.

## Learned-receiver 方向 (2026-04-19 决定)
- **新主线**: `afdm_sp_joint_unrolled/classical_joint_unrolled.py` — 是对
  `afdm_baselines.joint_omp_mp_iterative` 的忠实可微展开；冻结超参时与 NumPy
  baseline 在 N=512 上 bit-exact (验证器 `verify_classical_unrolled_matches_numpy.py`)。
  BCE/DNN 微调基于这个 backbone，目标是严格超过 classical joint。
- **已弃用学习目标**: `afdm_joint_unrolled.py::JointSparseUnrolledReceiver`
  ("CurrentJoint")。它不是 classical joint 的忠实展开（MP 是学习的 nn.Linear、
  support proposal 是学习的 logits）；结果在高 SNR 时仍低于 classical teacher。
  保留用于 ablation/comparison，不再是主学习模型。

## GitHub 只读镜像（2026-10-13）

- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `trans/tcom-main` 已提交的本目录，排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 按需同步：仅当用户明确说「推 GitHub / 同步镜像」时，先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得主动推送，不得把 vault 本身推到该仓库。

## Remote Server
- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
- Login landing: `/home/guoyikun`，登录后需 `cd /data/guoyikun/`
- GPU: RTX 4090 单卡，约 5 位活跃用户共享
- Working dir: `/data/guoyikun/`
- Code dir: `/data/guoyikun/00inbox/AFDM-channel-estimation/`
- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。

### 实验结果回传规则（2026-07-26 起）
- 每个远程 run 结束后，**小结果文件**（`results.json`、`*_run.log`、表格 md、launcher `.sh`）scp 回本地 vault 的同名 `afdm_sp_joint_unrolled/outputs_*/` 目录，并在 `.gitignore` 显式 `!` whitelist 入 git
- **大文件**（npz/ckpt/per-frame dump >10MB）留远程不回传，但其**完整远程路径 + md5** 必须记入对应 asset card 的 provenance 或任务 notes——路径丢了等于数据丢了
- CPU 并行原则：单 job 线程数超过 ~32 后收益递减，多 job 并行吃满整机比单 job 独占 128 核吞吐更高；共享机器上合计留 ~16 核余量

## ⚠️ 硬性约束
- 禁止 `sudo` / `apt` 安装任何软件，无权限
- 所有文件必须在 `/data/<username>/` 下，其他目录会被定期清理
- 运行训练前必须先执行 `nvidia-smi` 检查 GPU 占用
- 远程执行 conda 相关命令需用登录 shell，否则会 `conda: command not found`，例：
  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`

### 共享目录禁用清单（**任何文件都不能写进去**）
严禁向以下位置写任何文件，包括中间产物 / 日志 / 临时 pickle：
- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
- `/home/guoyikun/` — 主目录虽属于本人但非项目空间，项目数据集中放 `/data/guoyikun/`
- `/opt/`、`/usr/`、`/root/` — 系统目录，权限错误或越权
- 其他用户 home：`/home/<他人>/`、`/data/<他人>/` — 越权

### 规范的落盘位置
| 文件类型 | 正确位置 |
|---|---|
| 某个项目实验的 `run.log` / `tee` 输出 / 结果 JSON | `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_*/` |
| 需要快速丢弃的 scratch 文件、smoke test 日志、跨项目临时 pickle | **`/data/guoyikun/tmp/`** ← 项目专用 tmp 目录，取代系统 `/tmp` |
| 跨天保留的抢救件 | `/data/guoyikun/00inbox/AFDM-channel-estimation/_tmp_rescue_YYYYMMDD/` |

**规则**：所有原本想写到系统 `/tmp/` 的操作，都改写到 `/data/guoyikun/tmp/`。
例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。

## GPU 使用
- 运行前 `nvidia-smi` 查看占用
- **不要求独占 GPU**：只要没有"强烈碰撞"，可并行跑合适规模的进程
- "强烈碰撞"经验阈值（**同时满足**才算冲突，避让或延后）：
  - 已用显存 > 18 GB（剩余 < ~6 GB，新进程极可能 OOM）
  - **且** GPU-Util 长期 > 90%（他人任务已吃满算力）
- 任一条件未满足 → 可以启动任务，但应主动控制 batch size / 显存占用
- 若必须跑大任务且他人占用高 → 先询问我（用户）沟通或延后
- 长任务用 tmux 防止 SSH 断开

### tmux 命名规范
- 所有 session 名以 `g_` 开头（例：`g_train_afdm`、`g_debug`），避免与他人撞名

## 环境管理
- 激活 conda 环境: `conda activate AFDM`
- 安装包: 先激活 `AFDM` 再 `pip install`/`conda install`，禁止 sudo，不装进 base 或其他环境

## 工作流
1. `cd /data/guoyikun/` 进入项目
2. `nvidia-smi` 确认 GPU 占用情况
3. `conda activate AFDM` 激活环境
4. `tmux new -s g_<session>` 开启持久会话
5. 运行代码，`tmux detach` 后台挂起
