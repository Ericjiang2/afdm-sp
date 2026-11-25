OpenAI Codex v0.170.0
--------
workdir: /tmp
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20ea5-466d-72d3-aa7f-1778585682be
--------
user
You are Sol performing a concise (<= 3 min) pre-launch static review of Stage A5 in `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/`:
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA5_PROTOCOL.md`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/test_stageA5.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5_launch.sh`

Check specifically:
1. Mathematical & model exactness vs `stageA4.py` (`model`, `fims`, `crb_nu`, `metric`):
   - `T = sum_i g_i diag(c_i(nu_i)) P_{l_i}`, `C = v_d T T^H + sigma2 I`, `e = r - T p_t`, `NLL = logdet C + e^H C^-1 e`.
   - Fast sparse-diagonal `build_covariance_fast`, `_build_cov_without_path`, `_nll_for_path`, and `_gls_gains`.
   - `PW`, `SB`, `KD` search specs (no truth peeking for `g_i` or `nu_i`; true delays only).
   - Metric `sum |g_i|^2 min(|nu_hat - nu|, 0.375) / sum |g_i|^2` and outlier `> 0.25`.
2. Gates G1–G4 (`stageA5_gate.json`): G1 noiseless KD from `truth + 0.1` within `1e-3`; G2 12 dB 100-draw KD MC var/CRB_known in `[0.7, 1.5]`; G3 benign SB (`rho=.30, 12 dB, 20 draws`) `mean SB <= 1.5 x SB-CRB`; G4 cost `×1.3 <= 6.0` core-hours (`300,400,500` if fits else `400`).
3. Frozen readout (`E = min_{rho in {.10,.15}} mean SB at 4 dB`, paired bootstrap 2000 draws seed `20261125`, `PASS <= 0.08`, `FAIL > 0.08`, `BORDERLINE` else), efficiency vs `stageA4` CRB, deinlab rules (`AFDM` env, 6 thread vars = 1, `CUDA_VISIBLE_DEVICES=""`, `<= 32` workers, `/data/guoyikun/tmp`, zero `/dev/shm`, `_argv`/`_config`, atomic writes).
4. Any bugs, edge cases, or numerical traps.

Be concise and end with `VERDICT: PASS` or `VERDICT: FIX`.

warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
hook: SessionStart
hook: SessionStart Completed
codex
自检：1 个红项（纠正记录（自检故障））；自查信号待复核 84 项，最早 2026-11-19，说“跑一次 L2”处理。等你处理：4 个红项（L0、Vault 工作树、复盘证据 等 4 项）（决定项见最近系统报告 2026-11-18）。详情见 vault 的 系统状态.md

我会用 `research-checkpoint` 技能做发车前静态审查，先对照冻结协议和 Stage A4 的公式，再核对门槛、读出和启动脚本。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba STAGEA5_PROTOCOL.md; nl -ba stageA5_launch.sh; if test -f stageA5_gate.json; then cat stageA5_gate.json; fi' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     1	# 阶段 A5：半盲第 0 轮多普勒估计器代理检验——协议（`STAGEA5_PROTOCOL.md`）
     2	
     3	**状态**：冻结前稿（待 Sol 静态审查后冻结并提交 `Before data-pilot-fer stage A5 ...`）
     4	**承接**：[STAGEA4_READOUT.md](STAGEA4_READOUT.md)（`SB-REACHABLE`：4 dB 下半盲高斯 CRB 为 `.040/.037` bin）与 [sameframe_cd2_20261125/READOUT.md](../sameframe_cd2_20261125/READOUT.md)（以 `CD2` 为基线后 `P1'` 为 `INCONCLUSIVE`，对 `s100` 余量 `+0.58 [+0.32, +0.84] dB`）。
     5	
     6	---
     7	
     8	## 1. 核心问题
     9	
    10	在**已知真时延** $l_i$ 条件下，实际可运行的半盲高斯最大似然第 0 轮多普勒估计器（`SB`），在低导频比例 $\rho \in \{0.10, 0.15\}$、$\text{SNR} = 4\text{ dB}$ 下，其功率加权平均绝对误差能否达到 $\le 0.08\text{ bin}$（Stage A3 中保住约 60% 收益的代理门槛）？
    11	
    12	---
    13	
    14	## 2. 信号模型与三种估计器（复用 `stageA4.model` 约定，不改冻结文件）
    15	
    16	原始单位下（与 `stageA4.model` 一致至 $10^{-15}$）：
    17	$$r = \mathrm{daft}(y, \text{inverse}) = T x_t + w, \qquad x_t = \mathrm{daft}(p + d, \text{inverse}), \qquad T = \sum_{i=1}^{P} g_i\,\mathrm{diag}(c_i(\nu_i))\,P_{l_i}$$
    18	其中 $c_i[k] = \mathrm{cp}_i(k)\exp(j 2\pi k \nu_i / N)$ 与 `stageA4.model` 完全一致，$v_d = \mathrm{mean}(|d|^2) = 1-\rho$，噪声方差 $\sigma^2 = \text{raw['sigma2']}$。三条估计器均已知真时延 $l_i$，复增益 $g_i$ 为干扰参数（不使用真值 $g_i$ 或 $\nu_i$）：
    19	
    20	1. **`PW`（纯导频，把数据当白噪声）**：
    21	   - 初始化：逐径在 `[-3, 3]` 上以 `0.05` 步长（121 点）做单径导频匹配滤波最大化 $|a_i(\nu)^H r|^2$，其中列向量 $a_i(\nu)[k] = c_i(\nu)[k]\,p_t[(k-l_i)\bmod N]$。随后用初始 $\nu$ 求多径最小二乘增益 $g_{\mathrm{LS}}$，按 $|g_{\mathrm{LS},i}|$ 从大到小排坐标搜索顺序（绝不偷看真增益）。
    22	   - 坐标搜索：2 轮扫描，每径在当前 $\nu_i$ 的 $\pm 0.5$ 窗内（裁至 `[-3, 3]`）以 `0.05` 步长粗搜最小化 $\|r - A(\nu) g_{\mathrm{LS}}\|^2$，再在最优格点 $\pm 0.05$ 内有界精搜（`scipy.optimize.minimize_scalar(..., method='bounded', xatol=0.005)`）。结束时更新 $g_{\mathrm{PW}} = \arg\min_g \|r - A(\nu_{\mathrm{PW}}) g\|^2$。
    23	2. **`SB`（半盲高斯最大似然）**：
    24	   - 初值：从 `PW` 的 $(\nu_{\mathrm{PW}}, g_{\mathrm{PW}})$ 出发，先用当前 $C(\nu_{\mathrm{PW}}, g_{\mathrm{PW}})$ 做一次 GLS 增益更新 $g = (A^H C^{-1} A)^{-1} A^H C^{-1} r$。
    25	   - 目标函数：最小化精确高斯负对数似然 $\mathrm{NLL}(\nu, g) = \log\det C + e^H C^{-1} e$，其中 $C = v_d T T^H + \sigma^2 I$（利用 $T$ 每行仅 8 个非零元的精确稀疏对角和构造，经 Cholesky 分解计算，与稠密 $T T^H$ 一致至 $10^{-14}$），$e = r - T p_t$。
    26	   - 坐标搜索：2 轮扫描，按当前 $|g_i|$ 从大到小逐径在 $\pm 0.4$ 窗内（裁至 `[-3, 3]`）以 `0.04` 步长粗搜，再在最优格点 $\pm 0.04$ 内有界精搜（`xatol=0.005`）；两轮扫描之间以当前 $C$ 做一次 GLS 增益更新 $g = (A^H C^{-1} A)^{-1} A^H C^{-1} r$。
    27	3. **`KD`（已知数据天花板，健全性对照）**：
    28	   - 同样坐标搜索结构（用全信号 $x_t = \mathrm{daft}(p+d, \text{inverse})$ 匹配滤波初始化，按 $|g_{\mathrm{LS},i}|$ 降序 2 轮 $\pm 0.5$ 窗、`0.05` 步长 + 有界精搜 `xatol=1e-4`），最小化 $\|r - A_{\mathrm{full}}(\nu) g_{\mathrm{LS}}\|^2$。
    29	
    30	### 评价指标（与 A3/A4 一致）
    31	$$M(\hat{\nu}, \nu, g) = \frac{\sum_{i=1}^{P} |g_i|^2 \min(|\hat{\nu}_i - \nu_i|,\; 0.375)}{\sum_{i=1}^{P} |g_i|^2}$$
    32	（逐径误差超过 `0.375` bin 截顶；同时单独统计离群路径比例 $|\hat{\nu}_i - \nu_i| > 0.25$ bin。）
    33	
    34	---
    35	
    36	## 3. 数据网格与门禁（`out/stageA5_gate.json`）
    37	
    38	- **数据网格**：帧 `41000–41099` × 场景 `U/G`（共 **200 个信道抽样**，与 Stage A4 相同）；$\rho \in \{100, 150, 200\}$ permille；主判 SNR = `400`（4 dB）；若 G4 外推（×1.3）在 6 核时预算内允许，则同时跑 `300, 400, 500`（3/4/5 dB），否则仅跑 `400`。输入经 `stageA.setup()` 产生：`raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s, rho), rho, snr)`，取 `raw['y'], raw['pilot'], raw['data'], raw['sigma2'], truth['l_i'], truth['k_real'], truth['g_i']`。
    39	- **门禁 G1–G4（全部通过才允许启动主跑）**：
    40	  - **G1（优化器精确性 + `C` 构造一致性）**：4 个无噪声已知数据键上，从 `truth['k_real'] + 0.1` bin 出发，`KD` 恢复真多普勒的最大误差 $< 10^{-3}$ bin；同时验证快速对角 `C` 与 `stageA4.model` 稠密 $v_d T T^H + \sigma^2 I$ 相对误差 $< 10^{-13}$。
    41	  - **G2（`KD` 12 dB 蒙特卡洛 vs `known` CRB）**：单键（`U`, $\rho=.10$, 12 dB, frame `41000`）100 次独立加噪，8 条径的 $\mathrm{Var}(\hat{\nu}_i - \nu_i) / \mathrm{CRB}_{\mathrm{known}, i}$（取自 `stageA4.fims`）中位数须落在 **`[0.7, 1.5]`**。
    42	  - **G3（`SB` 良性工况验证）**：隔离帧 `41200–41209` × `U/G`（20 抽样），$\rho = .30$，12 dB，实测 `SB` 均值指标 $\le 1.5 \times$ 该 20 抽样 `SB-CRB` 对应指标均值（取自 `stageA4.fims` / `stageA4.metric`）。
    43	  - **G4（成本外推 ×1.3，$\le 6.0$ 核时，$\le 32$ 进程）**：在隔离帧测 `PW + SB + KD` 单键 CPU 耗时，优先检查 `SNRS=(300,400,500)` × 1.3 $\le 6.0$ 核时；若超出则降为 `SNRS=(400,)` × 1.3 $\le 6.0$ 核时；若仍超出则停机汇报。
    44	
    45	---
    46	
    47	## 4. 冻结判读规则（跑后永不改标）
    48	
    49	- **主估计量**：$E = \min_{\rho \in \{0.10, 0.15\}} \overline{M}_{\mathrm{SB}}(\rho, 4\text{ dB})$（200 个信道上的均值）。
    50	- **自助法**：对 200 个 `(frame, scenario)` 抽样联合做 **2,000 次配对自助重采样**（`seed = 20261125`），每次重采样上先算两档 $\rho$ 均值再取 $\min$，取 **95% 百分位区间** `[2.5, 97.5]`。
    51	- **唯一互斥判定表**：
    52	  - **`PASS`**：95% CI 上界 $\le 0.08$ bin（下一步：引入未知时延估计，再进端到端 FER）
    53	  - **`FAIL`**：95% CI 下界 $> 0.08$ bin（终止第 0 轮多普勒线，转写论文）
    54	  - **`BORDERLINE`**：其余情况（CI 横跨 `0.08`，由 Eric 决定）
    55	- **描述性次要读数**：各 $\rho$ 下 `PW` / `SB` / `KD` 均值与中位数；效率比 `SB mean / SB-CRB` 与 `PW mean / pilot_white-CRB`（同 200 抽样取自 `stageA4`）；离群路径占比（$|\hat{\nu}_i - \nu_i| > 0.25$ bin）；`PW` 对比 Stage A 现有导频估计器实际误差（`.157/.108/.082`）。
    56	
    57	---
    58	
    59	## 5. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）
    60	
    61	- **Claude**：
    62	  - `A5-C1`（判定）：`PASS` .30 / `BORDERLINE` .35 / `FAIL` .35
    63	  - `A5-C2`（效率）：4 dB、$\rho=.10$ 下 `SB` 效率（`SB mean / SB-CRB`）落在 `[1.3, 2.5]`：.60
    64	- **agy（Gemini 4 Neon）**：
    65	  - `A5-G1`（判定）：`PASS` .40 / `BORDERLINE` .30 / `FAIL` .30
    66	  - `A5-G2`（效率）：4 dB、$\rho=.10$ 下 `SB` 效率落在 `[1.3, 2.5]`：.55
    67	
    68	---
    69	
    70	## 6. deinlab 执行规范
    71	
    72	- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，日志首行打印 `sys.executable`）。
    73	- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp` 或 `/home/guoyikun`；`tmux` 会话名 `g_a5`；工作进程 `24`（$\le 32$）。
    74	- 原始逐键行（`out/stageA5/rows.jsonl.gz`）留远端并记录 MD5 到 `out/stageA5/REMOTE_ROWS_MD5.txt`；本地回传 `stageA5_gate.json`、`out/stageA5/results.json`（含 `_argv`/`_config`）、`RESULTS.md`、`STATUS` 与日志。
     1	#!/usr/bin/env bash
     2	set -euo pipefail
     3	
     4	if [ "$#" -ne 2 ]; then
     5	    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gate | run)" >&2
     6	    exit 2
     7	fi
     8	MODE="$1"
     9	FREEZE_COMMIT="$2"
    10	
    11	REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
    12	HERE="$REPO/experiments/data_pilot_fer_20261121"
    13	OUT="$HERE/out/stageA5"
    14	GATE_JSON="$HERE/out/stageA5_gate.json"
    15	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
    16	
    17	LOCKDIR="$OUT/.lock"
    18	if ! mkdir "$LOCKDIR" 2>/dev/null; then
    19	    echo "ERROR: lock $LOCKDIR already held" >&2
    20	    exit 1
    21	fi
    22	
    23	cd "$REPO"
    24	set +u
    25	source /opt/anaconda3/etc/profile.d/conda.sh
    26	conda activate AFDM
    27	set -u
    28	
    29	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    30	if [ "$(which python)" != "$PY" ]; then
    31	    rmdir "$LOCKDIR" 2>/dev/null || true
    32	    echo "ERROR: active python $(which python) != $PY" >&2
    33	    exit 1
    34	fi
    35	
    36	export PYTHONDONTWRITEBYTECODE=1
    37	export CUDA_VISIBLE_DEVICES=""
    38	export TMPDIR="/data/guoyikun/tmp"
    39	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
    40	export OMP_NUM_THREADS=1
    41	export OPENBLAS_NUM_THREADS=1
    42	export MKL_NUM_THREADS=1
    43	export NUMEXPR_NUM_THREADS=1
    44	export BLIS_NUM_THREADS=1
    45	export VECLIB_MAXIMUM_THREADS=1
    46	
    47	if [ "$MODE" = "gate" ]; then
    48	    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    49	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gate_cpu.txt" \
    50	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/stageA5.py" \
    51	        gate --out "$GATE_JSON" --workers 16 \
    52	        > "$OUT/gate.log" 2>&1
    53	    exit $?
    54	fi
    55	
    56	if [ "$MODE" = "run" ]; then
    57	    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/rows_shard*.jsonl* >/dev/null 2>&1; then
    58	        rmdir "$LOCKDIR" 2>/dev/null || true
    59	        echo "ERROR: $OUT/raw already contains shards; refuse to overwrite" >&2
    60	        exit 1
    61	    fi
    62	    status=STOPPED
    63	    cleanup() {
    64	        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    65	        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    66	        rmdir "$LOCKDIR" 2>/dev/null || true
    67	    }
    68	    trap cleanup EXIT
    69	
    70	    # Python enforces cumulative CPU <= 6.0 core-hours; wall cap 1800s outer safety net
    71	    set +e
    72	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/run_cpu.txt" \
    73	        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/stageA5.py" \
    74	        run --gate "$GATE_JSON" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    75	        > "$OUT/run.log" 2>&1
    76	    rc=$?
    77	    set -e
    78	    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    79	        status=STOPPED_BUDGET
    80	        exit 124
    81	    fi
    82	    if [ "$rc" -ne 0 ]; then
    83	        exit "$rc"
    84	    fi
    85	    test -s "$OUT/results.json"
    86	    test -s "$OUT/RESULTS.md"
    87	    status=DONE
    88	    exit 0
    89	fi
    90	
    91	rmdir "$LOCKDIR" 2>/dev/null || true
    92	echo "Unknown MODE: $MODE" >&2
    93	exit 2

exec
/bin/zsh -lc 'cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md' in /tmp
 succeeded in 0ms:
---
name: research-checkpoint
description: Use at four moments in any research project — (1) before freezing an experiment protocol or launching a pre-registered run, (2) before reporting results or writing/accepting a result card, (3) when a result contradicts expectation or you are about to explain a result, (4) when choosing or changing research direction or the paper's main line. Gives a short checklist for each moment.
---

# Research checkpoint

These are short checklists. Do the one for the current moment, write its answers into the artifact (protocol, card,
report or decision brief), then continue. Background: `../../docs/methods-handbook.md`
and `../../RULES_MAP.md` (relative to this skill's source directory; resolve its symlink first).

## 1. Before freezing a protocol or launching a pre-registered run

1. **Competing hypotheses.** Write down 2–3 alternatives and what each predicts for every arm. If all of them predict the
   same thing, the experiment cannot discriminate: redesign or drop it.
2. **Design validity, four questions.**
   - (a) Does each contrast change exactly one factor? If the conclusion will credit a component (a term, a module, a prior),
     is there an arm that removes it entirely, and is the simplest baseline in? If not, write why. The external design review
     (item 5) checks this too. Handbook A12.
   - (b) Leverage: from existing data or gate units only, is the expected difference clearly above noise? If a hypothesis
     predicts no difference, write an equivalence prediction.
   - (c) Statistical unit: cluster at the level where randomness is shared.
   - (d) What exactly does every proxy or oracle mean?
3. **Premortem.** If the result came out opposite to expectation, what is the most likely reason, and does the design
   already rule it out?
4. **Prediction ledger.** Record your own predictions with probabilities.
5. If the conclusion will be stated as a **mechanism**, get one short external review of the design and decision rule,
   using a different model, before freezing.
6. Verify every gate statement against the code. Commit before running. Run long jobs as one unattended chain with a cost
   stop and a DONE/STOPPED status line, and do not poll.
7. Optional, judge per case: would a small slice answer the decision question earlier? If the run is costly or its
   answer may change the plan, offer a staged look (pilot slice where events are dense, stop at the first useful result,
   report). Not for confirmatory claims. See `docs/methods-handbook.md` B8.

## 2. Before reporting results or writing a result card

- Report in three layers:
  1. observation (numbers);
  2. pre-registered verdict, stated as frozen and never relabelled;
  3. candidate explanation, marked *untested* with an H/M/L confidence.
- Credit an effect to a component only against a neutral control (its removal or the simplest working baseline), and only
  if the comparator is not worse than no intervention; otherwise say "A beats B", not "X causes it". When removal is
  ill-defined, say why and use the simplest working baseline.
- Say "unified", "proven" or "refuted" only after a pre-registered or prospective test has passed.
- Correct earlier findings with explicit correction notes; never rewrite them silently.
- Score the prediction-ledger entries for this run.
- Before writing shared records (IDs, state files, indexes), check what is already there.

## 3. When a result contradicts expectation

1. **Audit before explaining**: check data consistency across experiments, confounds and the statistical unit. If the
   surprise is a difference between two pipelines, first list every stage that differs and toggle the unintended ones
   (handbook B9).
2. Offer at most **one** new explanation, together with its cheapest falsifying test. Do not stack explanations on
   untested ones.
3. Optionally, ask a different model for up to two explanations without showing it yours, then compare.

## 4. When choosing or changing direction or the main line

1. Write your own assessment and commit it first.
2. Ask a different model for an independent assessment. Give it an input bundle: the goal, the primary evidence (result cards
   including drafts, open anomalies, the negative-results ledger) and nothing of your assessment or framing. It states the
   problem in its own words first, and gives at least one rival explanation that needs neither the main component nor the
   main claim. Trigger an extra outside audit on events, not on a calendar: a premise of the main claim is falsified, the
   claim survives only by narrowing twice, an unexplained tie or reversal stays open, and once before writing starts.
   Choose the model by capability for the task.
3. When you relay other models' analyses, list each source's own conclusion and every point with its source, and state
   adopt / modify / reject with a reason before merging; afterwards check that every point appears or is marked rejected.
   Then make the divergence table. The user decides. Do not run multi-round debates.
4. Value decisions (starting a line, changing direction, calling a result Transactions-level or a principle), handbook A13:
   - Headroom first: in the target regime, measure the simplest sane baseline, our method and a genie or bound. Look for a
     principle only where the baseline is clearly short of the genie and fails for a nameable reason.
   - Who already does it: a table of the 5–10 closest papers, one plain sentence each with equation or section location;
     the user spot-checks two rows against the source. A "nobody does X" claim lists its search terms and the three closest
     papers.
   - Case for and case against, by two different models from the same bundle, each citing checkable evidence and stating
     what would change its mind. A third pass names only the 1–3 factual cruxes and the cheapest check for each. Decide by
     checking the cruxes, not by which case reads better. Offer 「白话」 for all three.
   - A "no" parks the idea in the open-threads list with a revival condition; a "yes" passes a cheap kill test before
     large investment.
   - Suggest showing the three plain sentences to the advisor or a senior student.
   Not for routine experiments, status reports or small decisions inside a settled direction.
5. Use the top-level checks: importance (Hamming), feasibility × interest (Alon), Heilmeier questions, and the outside
   view (base rates).
6. Every recommendation gives the strongest alternative, the evidence that would change it, and a confidence level.

exec
/bin/zsh -lc "ls -a; wc -l STAGEA5_PROTOCOL.md stageA5.py test_stageA5.py stageA5_launch.sh stageA4.py; rg -n '"'^def |''^class '"' stageA5.py test_stageA5.py stageA4.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
.
..
STAGE0B_READOUT.md
STAGE0B_RULES.md
STAGE0_READOUT.md
STAGE0_RULES.md
STAGEA2_PROTOCOL.md
STAGEA2_READOUT.md
STAGEA3_PROTOCOL.md
STAGEA3_READOUT.md
STAGEA4_PROTOCOL.md
STAGEA4_READOUT.md
STAGEA5_PROTOCOL.md
STAGEA_PROTOCOL.md
STAGEA_READOUT.md
__pycache__
out
stage0.py
stage0b.py
stageA.py
stageA2.py
stageA3.py
stageA4.py
stageA5.py
stageA5_launch.sh
test_stageA5.py
      74 STAGEA5_PROTOCOL.md
    1015 stageA5.py
      64 test_stageA5.py
      93 stageA5_launch.sh
     226 stageA4.py
    1472 total
test_stageA5.py:14:def test_fast_covariance_and_nll_exactness():
test_stageA5.py:48:def test_verdict_and_metric():
stageA4.py:33:def model(truth, n, c1):
stageA4.py:45:def dense(cols, vals, n):
stageA4.py:50:def prepare(truth, n, c1):
stageA4.py:62:def fims(P, p, d, sigma2, n, c1, c2):
stageA4.py:74:def crb_nu(F, n_paths):
stageA4.py:81:def metric(crb, g):
stageA4.py:86:def keys_for(C, frame, s_):
stageA4.py:100:def draw_job(job):
stageA4.py:115:def gate(out):
stageA4.py:168:def run(out):
stageA4.py:184:def read(out):
stageA5.py:62:def own_md5() -> dict[str, str]:
stageA5.py:66:def _used_cpu_seconds() -> float:
stageA5.py:71:def _active_pids_cpu(pids: list[int]) -> float:
stageA5.py:84:def precompute_delay_geometry(delays: np.ndarray, n: int, c1: float) -> dict[str, Any]:
stageA5.py:102:def doppler_vectors(geom: dict[str, Any], nu: np.ndarray) -> np.ndarray:
stageA5.py:108:def build_basis_matrix(geom: dict[str, Any], c_mat: np.ndarray, x_t: np.ndarray) -> np.ndarray:
stageA5.py:114:def build_covariance_fast(
stageA5.py:138:def _build_cov_without_path(
stageA5.py:165:def _nll_for_path(
stageA5.py:205:def _gls_gains(
stageA5.py:228:def _mf_init(geom: dict[str, Any], x_t: np.ndarray, r: np.ndarray, step: float = 0.05) -> np.ndarray:
stageA5.py:242:def _ls_coordinate_search(
stageA5.py:319:def estimate_pw(geom: dict[str, Any], p_t: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
stageA5.py:325:def estimate_kd(
stageA5.py:339:def estimate_sb(
stageA5.py:399:def doppler_metric(nu_hat: np.ndarray, nu_true: np.ndarray, g_true: np.ndarray) -> tuple[float, float, list[float]]:
stageA5.py:409:def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
stageA5.py:438:def _load_runtime():
stageA5.py:449:def _g3_worker(in_path: str, out_path: str):
stageA5.py:478:def _g4_worker(in_path: str, out_path: str):
stageA5.py:511:def cmd_gate(args):
stageA5.py:651:def _run_shard_worker(shard_idx: int, draws: list[tuple[int, str]], snrs: tuple[int, ...], raw_dir: Path):
stageA5.py:699:def verdict_a5(ci_lo: float, ci_hi: float) -> str:
stageA5.py:707:def analyze_stageA5(
stageA5.py:829:def render_results_md(res: dict[str, Any]) -> str:
stageA5.py:866:def cmd_run(args):
stageA5.py:997:def main():

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '707,1015p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   707	def analyze_stageA5(
   708	    rows: list[dict[str, Any]],
   709	    a4_rows: list[dict[str, Any]],
   710	    snrs: tuple[int, ...],
   711	    a3_actual_pilot: dict[str, float],
   712	    *,
   713	    boot_draws: int = BOOT_DRAWS,
   714	    boot_seed: int = BOOT_SEED,
   715	) -> dict[str, Any]:
   716	    """Frozen Stage A5 readout with paired bootstrap over the 200 (frame, scenario) draws."""
   717	    draws = sorted({(int(r['frame']), r['scenario']) for r in rows})
   718	    di = {k: i for i, k in enumerate(draws)}
   719	    n_draws = len(draws)
   720	    ests = ('PW', 'SB', 'KD')
   721	
   722	    M = np.full((len(ests), len(RHOS), len(snrs), n_draws), np.nan, dtype=np.float64)
   723	    O = np.full((len(ests), len(RHOS), len(snrs), n_draws), np.nan, dtype=np.float64)
   724	    for r in rows:
   725	        ri = RHOS.index(int(r['rho']))
   726	        si = snrs.index(int(r['snr']))
   727	        d_idx = di[(int(r['frame']), r['scenario'])]
   728	        for ei, e in enumerate(ests):
   729	            M[ei, ri, si, d_idx] = float(r['metric'][e])
   730	            O[ei, ri, si, d_idx] = float(r['outlier_frac'][e])
   731	    if np.isnan(M).any():
   732	        raise RuntimeError('Incomplete Stage A5 metric grid')
   733	
   734	    # Pair with Stage A4 CRB metrics on the exact same 200 draws
   735	    a4_bounds = ('pilot_white', 'pilot', 'semiblind', 'known')
   736	    B = np.full((len(a4_bounds), len(RHOS), len(snrs), n_draws), np.nan, dtype=np.float64)
   737	    for r in a4_rows:
   738	        snr = int(r['snr'])
   739	        if snr not in snrs:
   740	            continue
   741	        k = (int(r['frame']), r['scenario'])
   742	        if k not in di:
   743	            continue
   744	        ri = RHOS.index(int(r['rho']))
   745	        si = snrs.index(snr)
   746	        d_idx = di[k]
   747	        for bi, bname in enumerate(a4_bounds):
   748	            B[bi, ri, si, d_idx] = float(r['metric'][bname])
   749	    if np.isnan(B).any():
   750	        raise RuntimeError('Incomplete Stage A4 paired CRB grid')
   751	
   752	    rng = np.random.default_rng(boot_seed)
   753	    boot_idx = rng.integers(0, n_draws, size=(boot_draws, n_draws))
   754	
   755	    # Primary E = min_{rho in {100,150}} mean(SB at 4 dB)
   756	    si_400 = snrs.index(DECIDE_SNR)
   757	    ei_sb = ests.index('SB')
   758	    ri_100, ri_150 = RHOS.index(100), RHOS.index(150)
   759	    sb_100 = M[ei_sb, ri_100, si_400]
   760	    sb_150 = M[ei_sb, ri_150, si_400]
   761	    mean_100 = float(sb_100.mean())
   762	    mean_150 = float(sb_150.mean())
   763	    E_pt = min(mean_100, mean_150)
   764	    E_rho = 100 if mean_100 <= mean_150 else 150
   765	    b_100 = sb_100[boot_idx].mean(axis=1)
   766	    b_150 = sb_150[boot_idx].mean(axis=1)
   767	    E_boot = np.minimum(b_100, b_150)
   768	    E_lo, E_hi = (float(x) for x in np.percentile(E_boot, [2.5, 97.5]))
   769	    verdict = verdict_a5(E_lo, E_hi)
   770	
   771	    table: dict[str, dict[str, Any]] = {}
   772	    for ei, e in enumerate(ests):
   773	        table[e] = {}
   774	        for ri, rho in enumerate(RHOS):
   775	            for si, snr in enumerate(snrs):
   776	                v = M[ei, ri, si]
   777	                bm = v[boot_idx].mean(axis=1)
   778	                ci = [float(x) for x in np.percentile(bm, [2.5, 97.5])]
   779	                table[e][f'{rho}_{snr}'] = dict(
   780	                    mean=float(v.mean()),
   781	                    median=float(np.median(v)),
   782	                    ci95=ci,
   783	                    outlier_gt_0p25_frac=float(O[ei, ri, si].mean()),
   784	                )
   785	
   786	    crb_table: dict[str, dict[str, float]] = {}
   787	    for bi, bname in enumerate(a4_bounds):
   788	        crb_table[bname] = {
   789	            f'{rho}_{snr}': float(B[bi, ri, si].mean())
   790	            for ri, rho in enumerate(RHOS) for si, snr in enumerate(snrs)
   791	        }
   792	
   793	    efficiency: dict[str, Any] = {}
   794	    for ri, rho in enumerate(RHOS):
   795	        key4 = f'{rho}_{DECIDE_SNR}'
   796	        sb_m = table['SB'][key4]['mean']
   797	        sb_c = crb_table['semiblind'][key4]
   798	        pw_m = table['PW'][key4]['mean']
   799	        pw_c = crb_table['pilot_white'][key4]
   800	        kd_m = table['KD'][key4]['mean']
   801	        kd_c = crb_table['known'][key4]
   802	        efficiency[str(rho)] = dict(
   803	            sb_over_sb_crb=float(sb_m / sb_c),
   804	            pw_over_pilot_white_crb=float(pw_m / pw_c),
   805	            kd_over_known_crb=float(kd_m / kd_c),
   806	            pw_4db_mean=pw_m,
   807	            stageA_actual_pilot_4_5db=float(a3_actual_pilot[str(rho)]),
   808	            pw_over_stageA_actual=float(pw_m / float(a3_actual_pilot[str(rho)])),
   809	        )
   810	
   811	    return dict(
   812	        draws=n_draws,
   813	        snrs=list(snrs),
   814	        boot_draws=boot_draws,
   815	        boot_seed=boot_seed,
   816	        primary=dict(
   817	            E_point=E_pt,
   818	            E_ci95=[E_lo, E_hi],
   819	            best_rho=E_rho,
   820	            threshold=PASS_THRESH,
   821	            verdict=verdict,
   822	        ),
   823	        table=table,
   824	        crb_mean=crb_table,
   825	        efficiency_4db=efficiency,
   826	    )
   827	
   828	
   829	def render_results_md(res: dict[str, Any]) -> str:
   830	    a = res['analysis']
   831	    p = a['primary']
   832	    lines = [
   833	        '# Stage A5 Results: Semi-Blind Round-0 Doppler Proxy Check',
   834	        '',
   835	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
   836	        f'- Draws: **{a["draws"]}** (frames `41000–41099` × U/G), SNRs: `{a["snrs"]}`',
   837	        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 6.0 h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
   838	        '',
   839	        '## Primary Verdict (Pre-Registered, SNR = 4 dB)',
   840	        '',
   841	        f'- `E = min_{{ρ ∈ {{0.10, 0.15}}}} mean(SB)` = **{p["E_point"]:.4f} bin** (at ρ={p["best_rho"]/1000:.2f}), '
   842	        f'95% CI **[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] bin** → **{p["verdict"]}** (threshold `0.08` bin)',
   843	        '',
   844	        '## 4 dB Summary Table (Power-Weighted Capped MAE, bin; 200 Draws)',
   845	        '',
   846	        '| ρ | PW mean [med] | SB mean [med] (95% CI) | KD mean [med] | SB-CRB | PW-CRB | SB Eff | PW Eff | SB Outlier >0.25 | Stage A Actual (4–5 dB) |',
   847	        '|---:|---|---|---|---:|---:|---:|---:|---:|---:|',
   848	    ]
   849	    for rho in RHOS:
   850	        k4 = f'{rho}_400'
   851	        pw = a['table']['PW'][k4]
   852	        sb = a['table']['SB'][k4]
   853	        kd = a['table']['KD'][k4]
   854	        eff = a['efficiency_4db'][str(rho)]
   855	        lines.append(
   856	            f'| {rho/1000:.2f} | {pw["mean"]:.4f} [{pw["median"]:.4f}] | '
   857	            f'**{sb["mean"]:.4f}** [{sb["median"]:.4f}] ([{sb["ci95"][0]:.4f}, {sb["ci95"][1]:.4f}]) | '
   858	            f'{kd["mean"]:.4f} [{kd["median"]:.4f}] | '
   859	            f'{a["crb_mean"]["semiblind"][k4]:.4f} | {a["crb_mean"]["pilot_white"][k4]:.4f} | '
   860	            f'{eff["sb_over_sb_crb"]:.2f}× | {eff["pw_over_pilot_white_crb"]:.2f}× | '
   861	            f'{100*sb["outlier_gt_0p25_frac"]:.2f}% | {eff["stageA_actual_pilot_4_5db"]:.4f} |'
   862	        )
   863	    return '\n'.join(lines) + '\n'
   864	
   865	
   866	def cmd_run(args):
   867	    print(sys.executable, flush=True)
   868	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   869	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   870	    ar.check_thread_env()
   871	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   872	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   873	    if not 1 <= args.workers <= 32:
   874	        raise ValueError('workers must be in 1..32')
   875	
   876	    gate_path = args.gate.resolve()
   877	    gate_bytes = gate_path.read_bytes()
   878	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   879	    gate = json.loads(gate_bytes.decode('utf-8'))
   880	    if not gate.get('all_passed') or not gate.get('selected'):
   881	        raise RuntimeError('Refusing to run without passing stageA5_gate.json')
   882	    live_own = own_md5()
   883	    if gate['_config']['own_md5'] != live_own:
   884	        raise RuntimeError('gate.json own_md5 mismatch; re-run gates')
   885	    if gate['_config']['stageA_py_md5'] != ar.md5_file(HERE / 'stageA.py') or gate['_config']['stageA4_py_md5'] != ar.md5_file(HERE / 'stageA4.py'):
   886	        raise RuntimeError('Reused stageA/stageA4 MD5 mismatch vs gate.json')
   887	
   888	    snrs = tuple(int(s) for s in gate['selected']['snrs'])
   889	    out_dir = args.out.resolve()
   890	    raw_dir = out_dir / 'raw'
   891	    raw_dir.mkdir(parents=True, exist_ok=True)
   892	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   893	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   894	
   895	    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
   896	    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
   897	        raise RuntimeError('stageA4 rows.jsonl.gz MD5 mismatch')
   898	
   899	    wall_start = time.monotonic()
   900	    all_draws = [(f, s) for f in FRAMES for s in SCENARIOS]
   901	    n_shards = args.workers
   902	    mp_ctx = multiprocessing.get_context('spawn')
   903	    running = {}
   904	    budget_hit = False
   905	    print(f'Launching Stage A5: {len(all_draws)} draws x {len(RHOS)} rhos x {len(snrs)} SNRs ({snrs}) on {n_shards} workers...', flush=True)
   906	    try:
   907	        for idx in range(n_shards):
   908	            sub_draws = all_draws[idx::n_shards]
   909	            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_draws, snrs, raw_dir))
   910	            p.start()
   911	            running[p.sentinel] = (idx, p)
   912	        while running:
   913	            ready = wait(running, timeout=10.0)
   914	            for r in ready:
   915	                idx, p = running.pop(r)
   916	                p.join()
   917	                code = p.exitcode
   918	                p.close()
   919	                if code != 0:
   920	                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
   921	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   922	            if live_cpu >= BUDGET_CAP_SEC - 180.0:
   923	                budget_hit = True
   924	                break
   925	    finally:
   926	        for _, p in running.values():
   927	            p.terminate()
   928	        for _, p in running.values():
   929	            p.join()
   930	            p.close()
   931	    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
   932	        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   933	        sys.exit(BUDGET_EXIT_CODE)
   934	
   935	    # Merge shard MD5s and load all rows
   936	    raw_md5 = {}
   937	    rows = []
   938	    for idx in range(n_shards):
   939	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
   940	        raw_md5[sp.name] = ar.md5_file(sp)
   941	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   942	            for line in fh:
   943	                rows.append(json.loads(line))
   944	    ar.atomic_write_text(
   945	        out_dir / 'REMOTE_ROWS_MD5.txt',
   946	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
   947	    )
   948	
   949	    a4_rows = [json.loads(ln) for ln in gzip.open(a4_rows_path, 'rt', encoding='utf-8')]
   950	    a3_actual = json.loads((HERE / 'out' / 'stageA3' / 'results.json').read_text(encoding='utf-8'))['r0_doppler_err_snr4_5']['delay']
   951	    analysis = analyze_stageA5(rows, a4_rows, snrs, a3_actual)
   952	
   953	    total_cpu_h = _used_cpu_seconds() / 3600.0
   954	    if total_cpu_h >= BUDGET_CAP_HOURS:
   955	        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
   956	        sys.exit(BUDGET_EXIT_CODE)
   957	
   958	    results = dict(
   959	        _argv=sys.argv,
   960	        _config=dict(
   961	            freeze_commit=args.freeze_commit,
   962	            python_executable=sys.executable,
   963	            own_md5=live_own,
   964	            gate_md5=gate_md5,
   965	            snrs=list(snrs),
   966	            rhos=list(RHOS),
   967	            frames=[FRAMES[0], FRAMES[-1]],
   968	            draws=len(all_draws),
   969	            raw_output_dir=str(raw_dir),
   970	            raw_rows_md5=raw_md5,
   971	            stageA4_rows_md5=STAGEA4_ROWS_MD5,
   972	        ),
   973	        gates=dict(
   974	            all_passed=gate['all_passed'],
   975	            selected=gate['selected'],
   976	            G2_median_var_over_crb=gate['G2']['median_var_over_crb'],
   977	            G3_sb_over_crb_ratio=gate['G3']['ratio'],
   978	        ),
   979	        runtime=dict(
   980	            total_core_hours=total_cpu_h,
   981	            wall_seconds=time.monotonic() - wall_start,
   982	            cpu_cap_core_hours=BUDGET_CAP_HOURS,
   983	        ),
   984	        analysis=analysis,
   985	    )
   986	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
   987	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
   988	    p = analysis['primary']
   989	    print(
   990	        f'STAGEA5_DONE verdict={p["verdict"]} E={p["E_point"]:.4f} '
   991	        f'ci=[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] rho={p["best_rho"]} '
   992	        f'cpu_hours={total_cpu_h:.4f}',
   993	        flush=True,
   994	    )
   995	
   996	
   997	def main():
   998	    ap = argparse.ArgumentParser(description=__doc__)
   999	    sub = ap.add_subparsers(dest='mode', required=True)
  1000	    g = sub.add_parser('gate')
  1001	    g.add_argument('--out', type=Path, required=True)
  1002	    g.add_argument('--workers', type=int, default=16)
  1003	
  1004	    r = sub.add_parser('run')
  1005	    r.add_argument('--gate', type=Path, required=True)
  1006	    r.add_argument('--out', type=Path, required=True)
  1007	    r.add_argument('--freeze-commit', required=True)
  1008	    r.add_argument('--workers', type=int, default=WORKERS)
  1009	
  1010	    args = ap.parse_args()
  1011	    dict(gate=cmd_gate, run=cmd_run)[args.mode](args)
  1012	
  1013	
  1014	if __name__ == '__main__':
  1015	    main()

exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '1,448p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     1	"""Stage A5 (STAGEA5_PROTOCOL.md): semi-blind Gaussian ML round-0 Doppler proxy check (true delays).
     2	
     3	Reuses stageA.setup() and stageA4.{model, prepare, fims, crb_nu, metric} without editing frozen files.
     4	Estimators (all given true delays l_i; gains are nuisance, never peeking at truth g_i or nu_i):
     5	  PW = pilot-only (data treated as white noise): single-path MF init + 2 sweeps coordinate search
     6	  SB = semi-blind Gaussian ML: start from PW, GLS gain update, 2 sweeps minimizing logdet C + e^H C^-1 e
     7	  KD = known data (sanity ceiling): full-signal MF init + 2 sweeps coordinate search
     8	"""
     9	from __future__ import annotations
    10	
    11	import argparse
    12	import gzip
    13	import hashlib
    14	import json
    15	import multiprocessing
    16	from multiprocessing.connection import wait
    17	import os
    18	from pathlib import Path
    19	import platform
    20	import re
    21	import resource
    22	import shutil
    23	import sys
    24	import time
    25	from typing import Any
    26	
    27	import numpy as np
    28	from scipy.linalg import cho_factor, cho_solve, solve_triangular
    29	from scipy.optimize import minimize_scalar
    30	
    31	HERE = Path(__file__).resolve().parent
    32	EXP = HERE.parent
    33	sys.path.insert(0, str(HERE))
    34	sys.path.insert(0, str(EXP / 'huang_steelman_20261124'))
    35	
    36	import hs_arms as ar  # noqa: E402
    37	
    38	FRAMES = tuple(range(41000, 41100))
    39	SCENARIOS = ('U', 'G')
    40	RHOS = (100, 150, 200)
    41	ALL_SNRS = (300, 400, 500)
    42	DECIDE_SNR = 400
    43	DECIDE_RHOS = (100, 150)
    44	CAP = 0.375
    45	PASS_THRESH = 0.08
    46	OUTLIER_THRESH = 0.25
    47	BOOT_DRAWS = 2000
    48	BOOT_SEED = 20261125
    49	WORKERS = 24
    50	BUDGET_CAP_HOURS = 6.0
    51	BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
    52	COST_MARGIN = 1.3
    53	OVERHEAD_HOURS = 0.10
    54	BUDGET_EXIT_CODE = 124
    55	NU_MIN, NU_MAX = -3.0, 3.0
    56	CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100
    57	
    58	OWN_FILES = ('STAGEA5_PROTOCOL.md', 'stageA5.py', 'test_stageA5.py', 'stageA5_launch.sh')
    59	STAGEA4_ROWS_MD5 = 'a662fa94be8f76a960a3f43413c95973'
    60	
    61	
    62	def own_md5() -> dict[str, str]:
    63	    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}
    64	
    65	
    66	def _used_cpu_seconds() -> float:
    67	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    68	    return time.process_time() + ch.ru_utime + ch.ru_stime
    69	
    70	
    71	def _active_pids_cpu(pids: list[int]) -> float:
    72	    total = 0.0
    73	    for pid in pids:
    74	        try:
    75	            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
    76	            after = raw[raw.rfind(')') + 2:].split()
    77	            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
    78	        except OSError:
    79	            pass
    80	    return total
    81	
    82	
    83	# --------------------------------------------------------------------------- Core math & estimators
    84	def precompute_delay_geometry(delays: np.ndarray, n: int, c1: float) -> dict[str, Any]:
    85	    """Precompute delay-dependent chirp phase cp_i[k] and shifted column indices matching stageA4.model."""
    86	    k = np.arange(n, dtype=np.int64)
    87	    l_arr = np.asarray(delays, dtype=np.int64)
    88	    p = len(l_arr)
    89	    cols = np.empty((p, n), dtype=np.int64)
    90	    cp = np.empty((p, n), dtype=np.complex128)
    91	    for i, li in enumerate(l_arr):
    92	        cols[i] = (k - li) % n
    93	        cp[i] = np.where(k < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (k - li))), 1.0 + 0j)
    94	    # Cross-index shift for T @ T^H: entry (k, (k - l_i + l_j) % n)
    95	    cross_col = np.empty((p, p, n), dtype=np.int64)
    96	    for i in range(p):
    97	        for j in range(p):
    98	            cross_col[i, j] = (k - l_arr[i] + l_arr[j]) % n
    99	    return dict(n=n, p=p, k=k, k_norm=2j * np.pi * k / float(n), delays=l_arr, cols=cols, cp=cp, cross_col=cross_col)
   100	
   101	
   102	def doppler_vectors(geom: dict[str, Any], nu: np.ndarray) -> np.ndarray:
   103	    """Return c[p, n] where c[i, k] = cp_i[k] * exp(2j*pi*k*nu_i/n), exact match to stageA4.model."""
   104	    nu_arr = np.asarray(nu, dtype=np.float64)
   105	    return geom['cp'] * np.exp(nu_arr[:, None] * geom['k_norm'][None, :])
   106	
   107	
   108	def build_basis_matrix(geom: dict[str, Any], c_mat: np.ndarray, x_t: np.ndarray) -> np.ndarray:
   109	    """Build A[n, P] with column i = c_i(nu_i) * x_t[(k - l_i) % n]."""
   110	    shifted = x_t[geom['cols']]  # [P, n]
   111	    return (c_mat * shifted).T   # [n, P]
   112	
   113	
   114	def build_covariance_fast(
   115	    geom: dict[str, Any],
   116	    c_mat: np.ndarray,
   117	    g: np.ndarray,
   118	    vd: float,
   119	    sigma2: float,
   120	) -> np.ndarray:
   121	    """Build dense C = vd * T @ T^H + sigma2 * I using exact P^2 sparse diagonals (exact to ~1e-15)."""
   122	    n, p = geom['n'], geom['p']
   123	    k = geom['k']
   124	    cross_col = geom['cross_col']
   125	    C = np.zeros((n, n), dtype=np.complex128)
   126	    diag_val = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
   127	    C[k, k] = diag_val
   128	    for i in range(p):
   129	        gi_ci = (float(vd) * g[i]) * c_mat[i]
   130	        for j in range(p):
   131	            if i == j:
   132	                continue
   133	            m = cross_col[i, j]
   134	            C[k, m] += gi_ci * np.conj(g[j] * c_mat[j, m])
   135	    return C
   136	
   137	
   138	def _build_cov_without_path(
   139	    geom: dict[str, Any],
   140	    c_mat: np.ndarray,
   141	    g: np.ndarray,
   142	    vd: float,
   143	    sigma2: float,
   144	    skip_p: int,
   145	) -> np.ndarray:
   146	    """Build base covariance excluding cross-terms involving path skip_p (includes all diagonals)."""
   147	    n, p = geom['n'], geom['p']
   148	    k = geom['k']
   149	    cross_col = geom['cross_col']
   150	    C = np.zeros((n, n), dtype=np.complex128)
   151	    diag_val = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
   152	    C[k, k] = diag_val
   153	    for i in range(p):
   154	        if i == skip_p:
   155	            continue
   156	        gi_ci = (float(vd) * g[i]) * c_mat[i]
   157	        for j in range(p):
   158	            if j == skip_p or j == i:
   159	                continue
   160	            m = cross_col[i, j]
   161	            C[k, m] += gi_ci * np.conj(g[j] * c_mat[j, m])
   162	    return C
   163	
   164	
   165	def _nll_for_path(
   166	    nu_p: float,
   167	    p_idx: int,
   168	    geom: dict[str, Any],
   169	    c_mat: np.ndarray,
   170	    g: np.ndarray,
   171	    vd: float,
   172	    C_base: np.ndarray,
   173	    e_base: np.ndarray,
   174	    p_t_shifted_p: np.ndarray,
   175	) -> float:
   176	    """Exact Gaussian NLL = logdet C + e^H C^-1 e when varying only nu[p_idx]."""
   177	    k = geom['k']
   178	    p = geom['p']
   179	    cross_col = geom['cross_col']
   180	    cp_p = geom['cp'][p_idx] * np.exp(float(nu_p) * geom['k_norm'])
   181	    C = C_base.copy()
   182	    gp_cp = (float(vd) * g[p_idx]) * cp_p
   183	    for j in range(p):
   184	        if j == p_idx:
   185	            continue
   186	        m_pj = cross_col[p_idx, j]
   187	        term_pj = gp_cp * np.conj(g[j] * c_mat[j, m_pj])
   188	        C[k, m_pj] += term_pj
   189	        # Hermitian conjugate entry at (m_pj, k)
   190	        C[m_pj, k] += np.conj(term_pj)
   191	    e = e_base - (g[p_idx] * cp_p) * p_t_shifted_p
   192	    L, _ = cho_factor(C, lower=True, overwrite_a=True, check_finite=False)
   193	    diag_L = np.diag(L).real
   194	    if np.any(diag_L <= 0.0) or not np.isfinite(diag_L).all():
   195	        return 1e30
   196	    logdet = 2.0 * float(np.sum(np.log(diag_L)))
   197	    z = solve_triangular(L, e, lower=True, check_finite=False)
   198	    quad = float(np.vdot(z, z).real)
   199	    val = logdet + quad
   200	    if not np.isfinite(val):
   201	        return 1e30
   202	    return val
   203	
   204	
   205	def _gls_gains(
   206	    geom: dict[str, Any],
   207	    c_mat: np.ndarray,
   208	    g_curr: np.ndarray,
   209	    p_t: np.ndarray,
   210	    r: np.ndarray,
   211	    vd: float,
   212	    sigma2: float,
   213	) -> np.ndarray:
   214	    """GLS gain update g = (A^H C^-1 A)^-1 A^H C^-1 r using C from current (nu, g)."""
   215	    A = build_basis_matrix(geom, c_mat, p_t)
   216	    C = build_covariance_fast(geom, c_mat, g_curr, vd, sigma2)
   217	    cf = cho_factor(C, lower=True, overwrite_a=True, check_finite=False)
   218	    CiA = cho_solve(cf, A, check_finite=False)
   219	    Cir = cho_solve(cf, r, check_finite=False)
   220	    G = A.conj().T @ CiA
   221	    rhs = A.conj().T @ Cir
   222	    g_new = np.linalg.solve(G, rhs)
   223	    if not np.isfinite(g_new).all():
   224	        raise FloatingPointError('Nonfinite GLS gain update in SB')
   225	    return g_new
   226	
   227	
   228	def _mf_init(geom: dict[str, Any], x_t: np.ndarray, r: np.ndarray, step: float = 0.05) -> np.ndarray:
   229	    """Single-path matched filter initialization over [-3, 3] with given grid step."""
   230	    n_grid = int(round((NU_MAX - NU_MIN) / step)) + 1
   231	    grid = np.linspace(NU_MIN, NU_MAX, n_grid)
   232	    E = np.exp(np.outer(grid, geom['k_norm']))  # [G, n]
   233	    nu_init = np.empty(geom['p'], dtype=np.float64)
   234	    for i in range(geom['p']):
   235	        base = geom['cp'][i] * x_t[geom['cols'][i]]
   236	        # a_i(nu)^H r = sum_k conj(base[k]) * exp(-2j*pi*k*nu/n) * r[k] = conj(E) @ (conj(base) * r)
   237	        corr = np.conj(E) @ (np.conj(base) * r)
   238	        nu_init[i] = float(grid[int(np.argmax(np.abs(corr) ** 2))])
   239	    return nu_init
   240	
   241	
   242	def _ls_coordinate_search(
   243	    geom: dict[str, Any],
   244	    x_t: np.ndarray,
   245	    r: np.ndarray,
   246	    nu_start: np.ndarray,
   247	    *,
   248	    half_win: float = 0.5,
   249	    grid_step: float = 0.05,
   250	    xatol: float = 0.005,
   251	    sweeps: int = 2,
   252	) -> tuple[np.ndarray, np.ndarray]:
   253	    """Coordinate search minimizing ||r - A(nu) g_LS||^2 (used by PW and KD)."""
   254	    nu = np.asarray(nu_start, dtype=np.float64).copy()
   255	    c_mat = doppler_vectors(geom, nu)
   256	    A = build_basis_matrix(geom, c_mat, x_t)
   257	    g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)
   258	    shifted = x_t[geom['cols']]  # [P, n]
   259	    r_norm2 = float(np.vdot(r, r).real)
   260	
   261	    for _ in range(sweeps):
   262	        order = np.argsort(-np.abs(g))
   263	        for idx in order:
   264	            p_idx = int(idx)
   265	            lo = max(NU_MIN, nu[p_idx] - half_win)
   266	            hi = min(NU_MAX, nu[p_idx] + half_win)
   267	            n_pts = max(3, int(round((hi - lo) / grid_step)) + 1)
   268	            grid = np.linspace(lo, hi, n_pts)
   269	
   270	            # Orthonormal basis Q_other for all other columns -> fast exact projection residual!
   271	            other = [j for j in range(geom['p']) if j != p_idx]
   272	            if other:
   273	                Q_o, _ = np.linalg.qr(A[:, other], mode='reduced')
   274	                r_perp = r - Q_o @ (Q_o.conj().T @ r)
   275	                r_perp_norm2 = float(np.vdot(r_perp, r_perp).real)
   276	            else:
   277	                Q_o = None
   278	                r_perp = r
   279	                r_perp_norm2 = r_norm2
   280	
   281	            base_p = geom['cp'][p_idx] * shifted[p_idx]
   282	
   283	            def obj(val: float) -> float:
   284	                col = base_p * np.exp(float(val) * geom['k_norm'])
   285	                if Q_o is not None:
   286	                    u = col - Q_o @ (Q_o.conj().T @ col)
   287	                else:
   288	                    u = col
   289	                u_n2 = float(np.vdot(u, u).real)
   290	                if u_n2 <= 1e-18:
   291	                    return r_perp_norm2
   292	                proj = abs(np.vdot(u, r_perp)) ** 2 / u_n2
   293	                return max(0.0, r_perp_norm2 - proj)
   294	
   295	            # Vectorized coarse grid evaluation
   296	            cols_grid = base_p[:, None] * np.exp(np.outer(geom['k_norm'], grid))  # [n, G]
   297	            if Q_o is not None:
   298	                U_grid = cols_grid - Q_o @ (Q_o.conj().T @ cols_grid)
   299	            else:
   300	                U_grid = cols_grid
   301	            u_n2_vec = np.sum(np.abs(U_grid) ** 2, axis=0)
   302	            num_vec = np.abs(U_grid.conj().T @ r_perp) ** 2
   303	            scores = np.where(u_n2_vec > 1e-18, np.maximum(0.0, r_perp_norm2 - num_vec / np.maximum(u_n2_vec, 1e-30)), r_perp_norm2)
   304	            best_g = float(grid[int(np.argmin(scores))])
   305	
   306	            b_lo = max(lo, best_g - grid_step)
   307	            b_hi = min(hi, best_g + grid_step)
   308	            res = minimize_scalar(obj, bounds=(b_lo, b_hi), method='bounded', options={'xatol': xatol})
   309	            cand = float(res.x)
   310	            nu[p_idx] = cand if obj(cand) <= obj(best_g) else best_g
   311	            c_mat[p_idx] = geom['cp'][p_idx] * np.exp(nu[p_idx] * geom['k_norm'])
   312	            A[:, p_idx] = c_mat[p_idx] * shifted[p_idx]
   313	        g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)
   314	    if not (np.isfinite(nu).all() and np.isfinite(g).all()):
   315	        raise FloatingPointError('Nonfinite output in LS coordinate search')
   316	    return nu, g
   317	
   318	
   319	def estimate_pw(geom: dict[str, Any], p_t: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
   320	    """PW: pilot-only estimator treating data as white noise."""
   321	    nu0 = _mf_init(geom, p_t, r, step=0.05)
   322	    return _ls_coordinate_search(geom, p_t, r, nu0, half_win=0.5, grid_step=0.05, xatol=0.005, sweeps=2)
   323	
   324	
   325	def estimate_kd(
   326	    geom: dict[str, Any],
   327	    x_t: np.ndarray,
   328	    r: np.ndarray,
   329	    *,
   330	    nu_init: np.ndarray | None = None,
   331	    sweeps: int = 2,
   332	    xatol: float = 1e-4,
   333	) -> tuple[np.ndarray, np.ndarray]:
   334	    """KD: known-data sanity ceiling."""
   335	    nu0 = _mf_init(geom, x_t, r, step=0.05) if nu_init is None else np.asarray(nu_init, dtype=np.float64)
   336	    return _ls_coordinate_search(geom, x_t, r, nu0, half_win=0.5, grid_step=0.05, xatol=xatol, sweeps=sweeps)
   337	
   338	
   339	def estimate_sb(
   340	    geom: dict[str, Any],
   341	    p_t: np.ndarray,
   342	    r: np.ndarray,
   343	    vd: float,
   344	    sigma2: float,
   345	    nu_pw: np.ndarray,
   346	    g_pw: np.ndarray,
   347	    *,
   348	    half_win: float = 0.4,
   349	    grid_step: float = 0.04,
   350	    xatol: float = 0.005,
   351	    sweeps: int = 2,
   352	) -> tuple[np.ndarray, np.ndarray]:
   353	    """SB: semi-blind Gaussian ML minimizing logdet C + e^H C^-1 e with GLS gain updates."""
   354	    nu = np.asarray(nu_pw, dtype=np.float64).copy()
   355	    c_mat = doppler_vectors(geom, nu)
   356	    # Initial GLS gain update from PW estimate using C(nu_pw, g_pw)
   357	    g = _gls_gains(geom, c_mat, np.asarray(g_pw, dtype=np.complex128), p_t, r, vd, sigma2)
   358	    shifted = p_t[geom['cols']]  # [P, n]
   359	
   360	    for sw in range(sweeps):
   361	        order = np.argsort(-np.abs(g))
   362	        for idx in order:
   363	            p_idx = int(idx)
   364	            lo = max(NU_MIN, nu[p_idx] - half_win)
   365	            hi = min(NU_MAX, nu[p_idx] + half_win)
   366	            n_pts = max(3, int(round((hi - lo) / grid_step)) + 1)
   367	            grid = np.linspace(lo, hi, n_pts)
   368	
   369	            C_base = _build_cov_without_path(geom, c_mat, g, vd, sigma2, p_idx)
   370	            # e_base = r - sum_{j != p_idx} g_j * c_j * p_t_shifted_j
   371	            e_base = r.copy()
   372	            for j in range(geom['p']):
   373	                if j != p_idx:
   374	                    e_base -= (g[j] * c_mat[j]) * shifted[j]
   375	            p_sh = shifted[p_idx]
   376	
   377	            def obj(val: float) -> float:
   378	                return _nll_for_path(val, p_idx, geom, c_mat, g, vd, C_base, e_base, p_sh)
   379	
   380	            scores = [obj(float(v)) for v in grid]
   381	            best_idx = int(np.argmin(scores))
   382	            best_g = float(grid[best_idx])
   383	            best_val = scores[best_idx]
   384	
   385	            b_lo = max(lo, best_g - grid_step)
   386	            b_hi = min(hi, best_g + grid_step)
   387	            res = minimize_scalar(obj, bounds=(b_lo, b_hi), method='bounded', options={'xatol': xatol})
   388	            cand = float(res.x)
   389	            cand_val = float(res.fun)
   390	            nu[p_idx] = cand if cand_val <= best_val else best_g
   391	            c_mat[p_idx] = geom['cp'][p_idx] * np.exp(nu[p_idx] * geom['k_norm'])
   392	        if sw < sweeps - 1:
   393	            g = _gls_gains(geom, c_mat, g, p_t, r, vd, sigma2)
   394	    if not (np.isfinite(nu).all() and np.isfinite(g).all()):
   395	        raise FloatingPointError('Nonfinite output in SB estimator')
   396	    return nu, g
   397	
   398	
   399	def doppler_metric(nu_hat: np.ndarray, nu_true: np.ndarray, g_true: np.ndarray) -> tuple[float, float, list[float]]:
   400	    """A3/A4 power-weighted capped MAE + outlier (>0.25 bin) path fraction."""
   401	    abs_err = np.abs(np.asarray(nu_hat, dtype=np.float64) - np.asarray(nu_true, dtype=np.float64))
   402	    pw = np.abs(np.asarray(g_true, dtype=np.complex128)) ** 2
   403	    val = float(np.sum(pw * np.minimum(abs_err, CAP)) / np.sum(pw))
   404	    out_frac = float(np.mean(abs_err > OUTLIER_THRESH))
   405	    return val, out_frac, abs_err.tolist()
   406	
   407	
   408	# --------------------------------------------------------------------------- File-IPC worker helper
   409	def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
   410	    n_workers = min(max_workers, max(1, len(items)))
   411	    buckets = [items[i::n_workers] for i in range(n_workers)]
   412	    mp_ctx = multiprocessing.get_context('spawn')
   413	    out_files = []
   414	    procs = []
   415	    for wi, bucket in enumerate(buckets):
   416	        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
   417	        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
   418	        in_f.write_text(json.dumps(bucket), encoding='utf-8')
   419	        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
   420	        p.start()
   421	        procs.append((wi, p))
   422	        out_files.append(out_f)
   423	    for wi, p in procs:
   424	        p.join()
   425	        code = p.exitcode
   426	        p.close()
   427	        if code != 0:
   428	            raise RuntimeError(f'Worker {tag}/{wi} exited with code {code}')
   429	    merged: list[tuple[int, Any]] = []
   430	    for wi, out_f in enumerate(out_files):
   431	        chunk = json.loads(out_f.read_text(encoding='utf-8'))
   432	        for pos, val in enumerate(chunk):
   433	            merged.append((wi + pos * n_workers, val))
   434	    merged.sort(key=lambda x: x[0])
   435	    return [v for _, v in merged]
   436	
   437	
   438	def _load_runtime():
   439	    ar.verify_frozen_extra_md5()
   440	    import stageA  # noqa: E402
   441	    import stageA4  # noqa: E402
   442	    from physical import daft  # noqa: E402
   443	
   444	    C = stageA.setup()
   445	    return C, stageA4, daft
   446	
   447	
   448	# --------------------------------------------------------------------------- Gates G1-G4

exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '449,706p'; find out -name '*stageA5*' -print" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   449	def _g3_worker(in_path: str, out_path: str):
   450	    C, stageA4, daft = _load_runtime()
   451	    st, ctx = C['stage3'], C['ctx']
   452	    c1, c2 = ctx.system.c1, ctx.system.c2
   453	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   454	    out = []
   455	    for frame, s in jobs:
   456	        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, 300), 300, 1200)
   457	        y = np.asarray(raw['y'], dtype=np.complex128)
   458	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   459	        d = np.asarray(raw['data'], dtype=np.complex128)
   460	        sigma2 = float(raw['sigma2'])
   461	        vd = float(np.mean(np.abs(d) ** 2))
   462	        n = len(y)
   463	        r = daft(y, c1, c2, True)
   464	        p_t = daft(p, c1, c2, True)
   465	        geom = precompute_delay_geometry(truth['l_i'], n, c1)
   466	        nu_pw, g_pw = estimate_pw(geom, p_t, r)
   467	        nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   468	        m_sb, out_sb, _ = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   469	        m_pw, _, _ = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
   470	        P = stageA4.prepare(truth, n, c1)
   471	        F = stageA4.fims(P, p, d, sigma2, n, c1, c2)
   472	        crb_sb = stageA4.crb_nu(F['semiblind'], len(truth['l_i']))
   473	        m_crb_sb = stageA4.metric(crb_sb, truth['g_i'])
   474	        out.append(dict(frame=frame, scenario=s, sb=m_sb, pw=m_pw, sb_crb=m_crb_sb, outlier_sb=out_sb))
   475	    ar.atomic_write_text(Path(out_path), json.dumps(out))
   476	
   477	
   478	def _g4_worker(in_path: str, out_path: str):
   479	    C, _, daft = _load_runtime()
   480	    st, ctx = C['stage3'], C['ctx']
   481	    c1, c2 = ctx.system.c1, ctx.system.c2
   482	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   483	    out = []
   484	    for frame, s, rho, snr in jobs:
   485	        t0 = time.process_time()
   486	        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, snr)
   487	        y = np.asarray(raw['y'], dtype=np.complex128)
   488	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   489	        d = np.asarray(raw['data'], dtype=np.complex128)
   490	        sigma2 = float(raw['sigma2'])
   491	        vd = float(np.mean(np.abs(d) ** 2))
   492	        n = len(y)
   493	        r = daft(y, c1, c2, True)
   494	        p_t = daft(p, c1, c2, True)
   495	        x_t = daft(p + d, c1, c2, True)
   496	        geom = precompute_delay_geometry(truth['l_i'], n, c1)
   497	        t_pw0 = time.process_time()
   498	        nu_pw, g_pw = estimate_pw(geom, p_t, r)
   499	        t_pw = time.process_time() - t_pw0
   500	        t_sb0 = time.process_time()
   501	        nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   502	        t_sb = time.process_time() - t_sb0
   503	        t_kd0 = time.process_time()
   504	        nu_kd, _ = estimate_kd(geom, x_t, r)
   505	        t_kd = time.process_time() - t_kd0
   506	        tot = time.process_time() - t0
   507	        out.append(dict(key=[frame, s, rho, snr], total_cpu=tot, pw_cpu=t_pw, sb_cpu=t_sb, kd_cpu=t_kd))
   508	    ar.atomic_write_text(Path(out_path), json.dumps(out))
   509	
   510	
   511	def cmd_gate(args):
   512	    print(sys.executable, flush=True)
   513	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   514	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   515	    thread_env = ar.check_thread_env()
   516	    started = time.monotonic()
   517	
   518	    gate_path = args.out.resolve()
   519	    gate_path.parent.mkdir(parents=True, exist_ok=True)
   520	    if gate_path.exists():
   521	        gate_path.unlink()
   522	
   523	    C, stageA4, daft = _load_runtime()
   524	    st, ctx = C['stage3'], C['ctx']
   525	    c1, c2 = ctx.system.c1, ctx.system.c2
   526	
   527	    # Verify stageA4 rows archive exists & matches MD5
   528	    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
   529	    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
   530	        raise RuntimeError(f'stageA4 rows.jsonl.gz MD5 mismatch: {ar.md5_file(a4_rows_path)}')
   531	
   532	    # G1: noiseless KD from truth + 0.1 bin on 4 keys + fast covariance exactness check
   533	    g1_keys = (('U', 100, 400, 41200), ('G', 150, 400, 41201), ('U', 200, 400, 41202), ('G', 100, 400, 41203))
   534	    g1_rows = []
   535	    for s, rho, snr, frame in g1_keys:
   536	        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, snr)
   537	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   538	        d = np.asarray(raw['data'], dtype=np.complex128)
   539	        y0 = np.asarray(raw['noiseless'], dtype=np.complex128)
   540	        n = len(y0)
   541	        r0 = daft(y0, c1, c2, True)
   542	        x_t = daft(p + d, c1, c2, True)
   543	        geom = precompute_delay_geometry(truth['l_i'], n, c1)
   544	        nu_true = np.asarray(truth['k_real'], dtype=np.float64)
   545	        nu_hat, _ = estimate_kd(geom, x_t, r0, nu_init=nu_true + 0.1, sweeps=2, xatol=1e-4)
   546	        max_err = float(np.max(np.abs(nu_hat - nu_true)))
   547	
   548	        # Verify fast covariance vs dense stageA4.model
   549	        T_ref, _ = stageA4.model(truth, n, c1)
   550	        vd = float(np.mean(np.abs(d) ** 2))
   551	        s2 = float(raw['sigma2'])
   552	        C_ref = vd * (T_ref @ T_ref.conj().T) + s2 * np.eye(n, dtype=np.complex128)
   553	        c_mat = doppler_vectors(geom, nu_true)
   554	        C_fast = build_covariance_fast(geom, c_mat, np.asarray(truth['g_i'], dtype=np.complex128), vd, s2)
   555	        cov_err = float(np.linalg.norm(C_fast - C_ref) / np.linalg.norm(C_ref))
   556	        g1_rows.append(dict(key=[s, rho, snr, frame], max_nu_err=max_err, cov_rel_err=cov_err))
   557	    g1_pass = bool(all(x['max_nu_err'] < 1e-3 and x['cov_rel_err'] < 1e-13 for x in g1_rows))
   558	    print(f'G1 {"PASS" if g1_pass else "FAIL"} max_nu_err={max(x["max_nu_err"] for x in g1_rows):.2e} cov_err={max(x["cov_rel_err"] for x in g1_rows):.2e}', flush=True)
   559	
   560	    # G2: KD Monte Carlo at 12 dB, 100 noise draws on one key -> median var / CRB_known in [0.7, 1.5]
   561	    raw_g2, _, truth_g2 = st.observed(ctx, st.inputs(ctx, 41200, 'U', 100), 100, 1200)
   562	    p_g2 = np.asarray(raw_g2['pilot'], dtype=np.complex128)
   563	    d_g2 = np.asarray(raw_g2['data'], dtype=np.complex128)
   564	    y0_g2 = np.asarray(raw_g2['noiseless'], dtype=np.complex128)
   565	    s2_g2 = float(raw_g2['sigma2'])
   566	    n_g2 = len(y0_g2)
   567	    r0_g2 = daft(y0_g2, c1, c2, True)
   568	    xt_g2 = daft(p_g2 + d_g2, c1, c2, True)
   569	    geom_g2 = precompute_delay_geometry(truth_g2['l_i'], n_g2, c1)
   570	    nu_true_g2 = np.asarray(truth_g2['k_real'], dtype=np.float64)
   571	    P_g2 = stageA4.prepare(truth_g2, n_g2, c1)
   572	    F_g2 = stageA4.fims(P_g2, p_g2, d_g2, s2_g2, n_g2, c1, c2)
   573	    crb_kd = stageA4.crb_nu(F_g2['known'], len(nu_true_g2))
   574	    rng_g2 = np.random.default_rng(BOOT_SEED)
   575	    errs_g2 = np.empty((100, len(nu_true_g2)), dtype=np.float64)
   576	    for di in range(100):
   577	        w = np.sqrt(s2_g2 / 2.0) * (rng_g2.standard_normal(n_g2) + 1j * rng_g2.standard_normal(n_g2))
   578	        nu_h, _ = estimate_kd(geom_g2, xt_g2, r0_g2 + w, sweeps=2, xatol=1e-4)
   579	        errs_g2[di] = nu_h - nu_true_g2
   580	    var_ratio = np.var(errs_g2, axis=0, ddof=1) / crb_kd
   581	    med_ratio = float(np.median(var_ratio))
   582	    g2_pass = bool(0.7 <= med_ratio <= 1.5)
   583	    print(f'G2 {"PASS" if g2_pass else "FAIL"} median var/CRB_known={med_ratio:.3f} per_path={[round(float(v), 3) for v in var_ratio]}', flush=True)
   584	
   585	    # G3 (20 benign draws: frames 41200..41209 x U/G at rho=.30, 12 dB) & G4 (6 cost keys at 4 dB)
   586	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   587	    ipc_dir = tmp_root / f'stageA5_gates_ipc_{os.getpid()}'
   588	    ipc_dir.mkdir(parents=True, exist_ok=True)
   589	    try:
   590	        g3_jobs = [[f, s] for f in range(41200, 41210) for s in SCENARIOS]
   591	        print('Running G3 (20 benign draws: rho=0.30, 12 dB)...', flush=True)
   592	        g3_rows = _spawn_map(_g3_worker, g3_jobs, min(args.workers, 20), ipc_dir, 'g3')
   593	        mean_sb = float(np.mean([x['sb'] for x in g3_rows]))
   594	        mean_sb_crb = float(np.mean([x['sb_crb'] for x in g3_rows]))
   595	        mean_pw = float(np.mean([x['pw'] for x in g3_rows]))
   596	        sb_ratio = mean_sb / mean_sb_crb
   597	        g3_pass = bool(sb_ratio <= 1.5)
   598	        print(f'G3 {"PASS" if g3_pass else "FAIL"} mean_sb={mean_sb:.5f} mean_sb_crb={mean_sb_crb:.5f} ratio={sb_ratio:.3f} (mean_pw={mean_pw:.5f})', flush=True)
   599	
   600	        g4_jobs = [[41220, 'U', rho, 400] for rho in RHOS] + [[41221, 'G', rho, 400] for rho in RHOS]
   601	        print('Running G4 cost benchmark (6 keys at 4 dB)...', flush=True)
   602	        g4_rows = _spawn_map(_g4_worker, g4_jobs, min(args.workers, 6), ipc_dir, 'g4')
   603	    finally:
   604	        shutil.rmtree(ipc_dir, ignore_errors=True)
   605	
   606	    mean_key_cpu = float(np.mean([x['total_cpu'] for x in g4_rows]))
   607	    candidates = []
   608	    for snrs in ((300, 400, 500), (400,)):
   609	        n_keys = len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(snrs)
   610	        raw_h = mean_key_cpu * n_keys / 3600.0 + OVERHEAD_HOURS
   611	        marg_h = raw_h * COST_MARGIN
   612	        candidates.append(dict(
   613	            snrs=list(snrs),
   614	            n_keys=n_keys,
   615	            mean_cpu_sec_per_key=mean_key_cpu,
   616	            raw_hours=raw_h,
   617	            projected_hours_with_margin=marg_h,
   618	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   619	        ))
   620	    selected = next((c for c in candidates if c['within_budget']), None)
   621	    g4_pass = selected is not None
   622	    all_passed = bool(g1_pass and g2_pass and g3_pass and g4_pass)
   623	    gate_cpu_h = _used_cpu_seconds() / 3600.0
   624	
   625	    payload = dict(
   626	        _argv=sys.argv,
   627	        _config=dict(
   628	            python_executable=sys.executable,
   629	            threads=thread_env,
   630	            workers=args.workers,
   631	            own_md5=own_md5(),
   632	            stageA_py_md5=ar.md5_file(HERE / 'stageA.py'),
   633	            stageA4_py_md5=ar.md5_file(HERE / 'stageA4.py'),
   634	            stageA4_rows_md5=STAGEA4_ROWS_MD5,
   635	        ),
   636	        all_passed=all_passed,
   637	        selected=selected,
   638	        G1=dict(passed=g1_pass, rows=g1_rows),
   639	        G2=dict(passed=g2_pass, draws=100, median_var_over_crb=med_ratio, per_path_var_over_crb=var_ratio.tolist()),
   640	        G3=dict(passed=g3_pass, draws=len(g3_rows), mean_sb=mean_sb, mean_sb_crb=mean_sb_crb, ratio=sb_ratio, mean_pw=mean_pw, rows=g3_rows),
   641	        G4=dict(passed=g4_pass, budget_cap_core_hours=BUDGET_CAP_HOURS, margin=COST_MARGIN, candidates=candidates, samples=g4_rows),
   642	        gate_cpu_hours=gate_cpu_h,
   643	        gate_wall_seconds=time.monotonic() - started,
   644	    )
   645	    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
   646	    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
   647	    sys.exit(0 if all_passed else 1)
   648	
   649	
   650	# --------------------------------------------------------------------------- Main run & readout
   651	def _run_shard_worker(shard_idx: int, draws: list[tuple[int, str]], snrs: tuple[int, ...], raw_dir: Path):
   652	    C, _, daft = _load_runtime()
   653	    st, ctx = C['stage3'], C['ctx']
   654	    c1, c2 = ctx.system.c1, ctx.system.c2
   655	    lines: list[str] = []
   656	    for frame, s in draws:
   657	        for rho in RHOS:
   658	            base = st.inputs(ctx, frame, s, rho)
   659	            for snr in snrs:
   660	                raw, _, truth = st.observed(ctx, base, rho, snr)
   661	                y = np.asarray(raw['y'], dtype=np.complex128)
   662	                p = np.asarray(raw['pilot'], dtype=np.complex128)
   663	                d = np.asarray(raw['data'], dtype=np.complex128)
   664	                sigma2 = float(raw['sigma2'])
   665	                vd = float(np.mean(np.abs(d) ** 2))
   666	                n = len(y)
   667	                r = daft(y, c1, c2, True)
   668	                p_t = daft(p, c1, c2, True)
   669	                x_t = daft(p + d, c1, c2, True)
   670	                geom = precompute_delay_geometry(truth['l_i'], n, c1)
   671	
   672	                nu_pw, g_pw = estimate_pw(geom, p_t, r)
   673	                nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   674	                nu_kd, _ = estimate_kd(geom, x_t, r)
   675	
   676	                m_pw, o_pw, e_pw = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
   677	                m_sb, o_sb, e_sb = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   678	                m_kd, o_kd, e_kd = doppler_metric(nu_kd, truth['k_real'], truth['g_i'])
   679	
   680	                lines.append(json.dumps(dict(
   681	                    frame=frame, scenario=s, rho=rho, snr=snr,
   682	                    metric=dict(PW=m_pw, SB=m_sb, KD=m_kd),
   683	                    outlier_frac=dict(PW=o_pw, SB=o_sb, KD=o_kd),
   684	                    abs_err=dict(PW=e_pw, SB=e_sb, KD=e_kd),
   685	                ), allow_nan=False) + '\n')
   686	
   687	    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
   688	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   689	    with part_path.open('wb') as raw_fh:
   690	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
   691	            for ln in lines:
   692	                gz.write(ln.encode('utf-8'))
   693	        raw_fh.flush()
   694	        os.fsync(raw_fh.fileno())
   695	    os.replace(part_path, final_path)
   696	    print(f'Shard {shard_idx:03d} done ({len(lines)} keys)', flush=True)
   697	
   698	
   699	def verdict_a5(ci_lo: float, ci_hi: float) -> str:
   700	    if ci_hi <= PASS_THRESH:
   701	        return 'PASS'
   702	    if ci_lo > PASS_THRESH:
   703	        return 'FAIL'
   704	    return 'BORDERLINE'
   705	
   706	
out/stageA5_sol_review.md

exec
/bin/zsh -lc "nl -ba stageA4.py | sed -n '1,226p'; nl -ba test_stageA5.py; rg -n '"'^(def (setup|inputs|observed|atomic|daft)|.*(/dev/shm|multiprocessing))'"' stageA.py stageA3.py stageA2.py stage0.py; git status --short -- STAGEA5_PROTOCOL.md stageA5.py test_stageA5.py stageA5_launch.sh; for d in . .. ../..; do for f in AGENTS.md STATE.md .trellis/workflow.md; do if test -f \""'$d/$f"; then ls "$d/$f"; fi; done; done' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     1	"""Stage A4 (STAGEA4_PROTOCOL.md): round-0 Doppler Cramer-Rao bounds given the true delays.
     2	
     3	Model (raw units, exact to 1e-12 against raw['noiseless']): y = F T F^H (p + d) + w, F = DAFT (unitary),
     4	T = sum_i g_i diag(c_i) P_{l_i}, c_i[k] = cp_i[k] exp(2j pi k nu_i / n), (P_l x)[k] = x[(k - l) % n].
     5	Unknowns theta = (nu_1..nu_P, Re g, Im g); delays known.  Bounds on nu (nuisance gains included):
     6	  pilot_white  data treated as white noise:            2 Re(mu_i^H mu_j) / (sigma2 + v_d tr(TT^H)/n), mu = T p_t
     7	  pilot        data as interference with exact C:      2 Re(mu_i^H C^-1 mu_j),  C = v_d T T^H + sigma2 I
     8	  semiblind    Gaussian data, Slepian-Bangs:           pilot + tr(C^-1 C_i C^-1 C_j),  C_k = v_d (T_k T^H + T T_k^H)
     9	  known        all data known:                          2 Re(J^H J) / sigma2, J = d(T (p_t + d_t)) / d theta
    10	Metric (stage A3's): sum |g_i|^2 min(sqrt(2/pi) sqrt(CRB_i), CAP) / sum |g_i|^2.
    11	
    12	  python stageA4.py gate --out out/stageA4_gate.json
    13	  python stageA4.py run  --out out/stageA4
    14	  python stageA4.py read --out out/stageA4
    15	"""
    16	import argparse, gzip, json, os, resource, sys, time
    17	from multiprocessing import get_context
    18	from pathlib import Path
    19	import numpy as np
    20	
    21	import stageA
    22	from stageA import SCENARIOS, setup
    23	from physical import daft, regressors, Channel
    24	
    25	FRAMES = range(41000, 41100)
    26	RHOS = (100, 150, 200)
    27	SNRS = (300, 400, 500)
    28	BOUNDS = ('pilot_white', 'pilot', 'semiblind', 'known')
    29	CAP, TARGET, LOOSE, DECIDE_SNR, DECIDE_RHOS = 0.375, 0.04, 0.08, 400, (100, 150)
    30	WORKERS, BOOT, SEED = 32, 2000, 20261121
    31	
    32	
    33	def model(truth, n, c1):
    34	    """Dense T and, per parameter, the single nonzero per row of T_k: (cols, vals)."""
    35	    k = np.arange(n); l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float)
    36	    g = np.asarray(truth['g_i'], complex); T = np.zeros((n, n), complex); parts = [[], [], []]
    37	    for li, ni, gi in zip(l, nu, g):
    38	        cols = (k - li) % n
    39	        c = np.where(k < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (k - li))), 1.) * np.exp(2j * np.pi * k * ni / n)
    40	        T[k, cols] += gi * c
    41	        parts[0].append((cols, gi * c * 2j * np.pi * k / n)); parts[1].append((cols, c)); parts[2].append((cols, 1j * c))
    42	    return T, parts[0] + parts[1] + parts[2]
    43	
    44	
    45	def dense(cols, vals, n):
    46	    M = np.zeros((n, n), complex); M[np.arange(n), cols] = vals
    47	    return M
    48	
    49	
    50	def prepare(truth, n, c1):
    51	    """Everything that depends on the channel only (not on rho, SNR, pilot or data)."""
    52	    T, ops = model(truth, n, c1)
    53	    lam, U = np.linalg.eigh(T @ T.conj().T)
    54	    A = T.conj().T @ U
    55	    X = np.empty((len(ops), n * n), complex)
    56	    for j, (cols, vals) in enumerate(ops):
    57	        B = np.zeros((n, n), complex); B[cols] = vals.conj()[:, None] * U          # B = T_k^H U
    58	        D = B.conj().T @ A; X[j] = (D + D.conj().T).ravel()                         # U^H (T_k T^H + T T_k^H) U
    59	    return dict(T=T, ops=ops, lam=np.maximum(lam, 0.), U=U, X=X, trTT=float(np.real(np.trace(T @ T.conj().T))))
    60	
    61	
    62	def fims(P, p, d, sigma2, n, c1, c2):
    63	    """Fisher matrices of the four bounds for one (rho, SNR); p, d in raw DAFT units."""
    64	    ops = P['ops']; pt = daft(p, c1, c2, True); st = daft(p + d, c1, c2, True); vd = float(np.mean(np.abs(d) ** 2))
    65	    Jp = np.stack([v * pt[c] for c, v in ops], 1); Js = np.stack([v * st[c] for c, v in ops], 1)
    66	    w = 1. / (vd * P['lam'] + sigma2); M = P['U'].conj().T @ Jp
    67	    pilot = 2 * np.real(M.conj().T @ (w[:, None] * M))
    68	    q = vd * w; X = P['X']
    69	    cov = np.real((X * np.outer(q, q).ravel()) @ X.conj().T)
    70	    return dict(pilot_white=2 * np.real(Jp.conj().T @ Jp) / (sigma2 + vd * P['trTT'] / n), pilot=pilot,
    71	                semiblind=pilot + cov, known=2 * np.real(Js.conj().T @ Js) / sigma2)
    72	
    73	
    74	def crb_nu(F, n_paths):
    75	    ev = np.linalg.eigvalsh(F)
    76	    if ev.min() <= 1e-12 * ev.max():
    77	        return np.full(n_paths, np.inf)
    78	    return np.diag(np.linalg.inv(F))[:n_paths].real
    79	
    80	
    81	def metric(crb, g):
    82	    pw = np.abs(np.asarray(g)) ** 2
    83	    return float(np.sum(pw * np.minimum(np.sqrt(2 / np.pi) * np.sqrt(np.maximum(crb, 0)), CAP)) / pw.sum())
    84	
    85	
    86	def keys_for(C, frame, s_):
    87	    st, ctx = C['stage3'], C['ctx']; ref = None
    88	    for rho in RHOS:
    89	        base = st.inputs(ctx, frame, s_, rho)
    90	        for snr in SNRS:
    91	            raw, obs, truth = st.observed(ctx, base, rho, snr)
    92	            t = (tuple(truth['l_i']), tuple(truth['k_real']), tuple(truth['g_i']))
    93	            if ref is None:
    94	                ref = t
    95	            elif t != ref:
    96	                raise ValueError(f'channel differs across rho/SNR at {frame} {s_}')
    97	            yield rho, snr, raw, truth
    98	
    99	
   100	def draw_job(job):
   101	    frame, s_ = job
   102	    C = setup(); c1, c2 = C['ctx'].system.c1, C['ctx'].system.c2
   103	    rows, P = [], None
   104	    for rho, snr, raw, truth in keys_for(C, frame, s_):
   105	        n = len(raw['y'])
   106	        if P is None:
   107	            P = prepare(truth, n, c1)
   108	        F = fims(P, np.asarray(raw['pilot']), np.asarray(raw['data']), float(raw['sigma2']), n, c1, c2)
   109	        g = np.asarray(truth['g_i']); crbs = {b: crb_nu(F[b], len(g)) for b in BOUNDS}
   110	        rows.append(dict(frame=frame, scenario=s_, rho=rho, snr=snr, power=(np.abs(g) ** 2).tolist(),
   111	                         crb={b: v.tolist() for b, v in crbs.items()}, metric={b: metric(v, g) for b, v in crbs.items()}))
   112	    return rows
   113	
   114	
   115	def gate(out):
   116	    """G1 reconstruction; G2 derivatives; G3 known-data ML Monte Carlo vs CRB; G4 fast trace term vs dense."""
   117	    from scipy.optimize import least_squares
   118	    C = setup(); st, ctx = C['stage3'], C['ctx']; c1, c2 = ctx.system.c1, ctx.system.c2
   119	    res = dict(G1=[], G2=[], G3=None, G4=None)
   120	    for s_, rho, snr, frame in (('U', 100, 400, 41000), ('G', 150, 300, 41001), ('U', 200, 500, 41002), ('G', 100, 400, 41003)):
   121	        raw, obs, truth = st.observed(ctx, st.inputs(ctx, frame, s_, rho), rho, snr)
   122	        p, d, y0 = (np.asarray(raw[k]) for k in ('pilot', 'data', 'noiseless')); n = len(y0)
   123	        T, ops = model(truth, n, c1)
   124	        rec = daft(T @ daft(p + d, c1, c2, True), c1, c2)
   125	        res['G1'].append(float(np.linalg.norm(rec - y0) / np.linalg.norm(y0)))
   126	        l, nu, g = (np.asarray(truth[k]) for k in ('l_i', 'k_real', 'g_i')); errs = []
   127	        for i in range(len(l)):
   128	            h = 1e-5; tp = dict(truth, k_real=nu + h * (np.arange(len(l)) == i)); tm = dict(truth, k_real=nu - h * (np.arange(len(l)) == i))
   129	            fd = (model(tp, n, c1)[0] - model(tm, n, c1)[0]) / (2 * h); an = dense(*ops[i], n)
   130	            errs.append(float(np.linalg.norm(fd - an) / np.linalg.norm(an)))
   131	            ch = Channel(n, c1, c2, l, nu, g).regressors(p + d, derivative=True)[:, i] * g[i]
   132	            mine = daft(an @ daft(p + d, c1, c2, True), c1, c2)
   133	            errs.append(float(np.linalg.norm(ch - mine) / np.linalg.norm(mine)))
   134	        res['G2'].append(max(errs))
   135	    # G3: known-data ML at 20 dB from the true start, 300 noise draws
   136	    raw, obs, truth = st.observed(ctx, st.inputs(ctx, 41000, 'U', 100), 100, 2000)
   137	    p, d, y0 = (np.asarray(raw[k]) for k in ('pilot', 'data', 'noiseless')); n = len(y0); s2 = float(raw['sigma2'])
   138	    l, nu, g = (np.asarray(truth[k]) for k in ('l_i', 'k_real', 'g_i')); x = p + d
   139	    crb = crb_nu(fims(prepare(truth, n, c1), p, d, s2, n, c1, c2)['known'], len(l))
   140	    rng = np.random.default_rng(SEED); est = []
   141	    for _ in range(300):
   142	        y = y0 + np.sqrt(s2 / 2) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
   143	
   144	        def resid(v):
   145	            A = regressors(x, l, v, c1, c2); r = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
   146	            return np.concatenate([r.real, r.imag])
   147	        est.append(least_squares(resid, nu.copy(), x_scale=np.sqrt(crb), xtol=1e-12, ftol=1e-12).x)
   148	    ratio = np.var(np.array(est) - nu, axis=0) / crb
   149	    res['G3'] = dict(crb_std=np.sqrt(crb).tolist(), ratio=ratio.tolist(), median=float(np.median(ratio)))
   150	    # G4: eigen-basis trace term against a dense computation for a few entries
   151	    raw, obs, truth = st.observed(ctx, st.inputs(ctx, 41001, 'G', 100), 100, 400)
   152	    p, d = np.asarray(raw['pilot']), np.asarray(raw['data']); n = len(p); s2 = float(raw['sigma2']); vd = float(np.mean(np.abs(d) ** 2))
   153	    P = prepare(truth, n, c1); F = fims(P, p, d, s2, n, c1, c2); T = P['T']
   154	    Ci = np.linalg.inv(vd * T @ T.conj().T + s2 * np.eye(n)); errs = []
   155	    for i, j in ((0, 0), (0, 3), (2, 9), (5, 20), (12, 17)):
   156	        Di, Dj = (vd * (dense(*P['ops'][k], n) @ T.conj().T + T @ dense(*P['ops'][k], n).conj().T) for k in (i, j))
   157	        ref = float(np.real(np.trace(Ci @ Di @ Ci @ Dj)))
   158	        errs.append(abs((F['semiblind'] - F['pilot'])[i, j] - ref) / abs(ref))
   159	    res['G4'] = float(max(errs))
   160	    t = time.process_time(); draw_job((41099, 'G')); per_draw = time.process_time() - t
   161	    out_ = dict(G1=bool(max(res['G1']) < 1e-10), G2=bool(max(res['G2']) < 1e-5), G3=bool(0.8 <= res['G3']['median'] <= 1.25),
   162	                G4=bool(res['G4'] < 1e-8),
   163	                detail=res, cpu_seconds_per_draw=per_draw,
   164	                projected_core_hours=per_draw * len(FRAMES) * len(SCENARIOS) / 3600 * 1.3)
   165	    Path(out).write_text(json.dumps(out_, indent=1)); print(json.dumps(out_, indent=1))
   166	
   167	
   168	def run(out):
   169	    out = Path(out); out.mkdir(parents=True, exist_ok=False)
   170	    jobs = [(f, s_) for f in FRAMES for s_ in SCENARIOS]
   171	    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
   172	        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, bounds=BOUNDS, cap=CAP, workers=WORKERS), indent=1))
   173	    t0 = time.time(); n = 0
   174	    with gzip.open(out / 'rows.jsonl.gz', 'wt') as fh, get_context('spawn').Pool(WORKERS) as pool:
   175	        for rows in pool.imap_unordered(draw_job, jobs):
   176	            for r in rows:
   177	                print(json.dumps(r), file=fh); n += 1
   178	    ch = resource.getrusage(resource.RUSAGE_CHILDREN); hours = (ch.ru_utime + ch.ru_stime) / 3600
   179	    want = len(jobs) * len(RHOS) * len(SNRS)
   180	    (out / 'STATUS').write_text((f'DONE {n} {hours:.4f}' if n == want else f'STOPPED {n}/{want} {hours:.4f}') + '\n')
   181	    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))
   182	
   183	
   184	def read(out):
   185	    out = Path(out); status = (out / 'STATUS').read_text().split()
   186	    if status[0] != 'DONE':
   187	        raise ValueError(status)
   188	    rows = [json.loads(x) for x in gzip.open(out / 'rows.jsonl.gz', 'rt')]
   189	    draws = sorted({(r['frame'], r['scenario']) for r in rows}); di = {k: i for i, k in enumerate(draws)}
   190	    V = np.full((len(BOUNDS), len(RHOS), len(SNRS), len(draws)), np.nan)
   191	    for r in rows:
   192	        for b, bound in enumerate(BOUNDS):
   193	            V[b, RHOS.index(r['rho']), SNRS.index(r['snr']), di[(r['frame'], r['scenario'])]] = r['metric'][bound]
   194	    if np.isnan(V).any():
   195	        raise ValueError('incomplete grid')
   196	    rng = np.random.default_rng(SEED)
   197	    idx = rng.integers(0, len(draws), (BOOT, len(draws)))
   198	    table = {}
   199	    for b, bound in enumerate(BOUNDS):
   200	        table[bound] = {}
   201	        for i, rho in enumerate(RHOS):
   202	            for j, snr in enumerate(SNRS):
   203	                v = V[b, i, j]; boots = v[idx].mean(axis=1)
   204	                table[bound][f'{rho}_{snr}'] = dict(mean=float(v.mean()), median=float(np.median(v)),
   205	                                                    ci=[float(x) for x in np.percentile(boots, [2.5, 97.5])])
   206	    j = SNRS.index(DECIDE_SNR); label, why = 'CLOSED', 'known'
   207	    for bound, name in (('pilot', 'PILOT-ENOUGH'), ('semiblind', 'SB-REACHABLE'), ('known', 'ALPHABET-ONLY')):
   208	        best = min(DECIDE_RHOS, key=lambda r: table[bound][f'{r}_{DECIDE_SNR}']['mean'])
   209	        if table[bound][f'{best}_{DECIDE_SNR}']['mean'] <= TARGET:
   210	            label, why = name, bound
   211	            break
   212	    best = min(DECIDE_RHOS, key=lambda r: table[why][f'{r}_{DECIDE_SNR}']['mean']); lo, hi = table[why][f'{best}_{DECIDE_SNR}']['ci']
   213	    verdict = label + (' (borderline)' if lo <= TARGET <= hi else '')
   214	    a3 = json.loads((out.parent / 'stageA3' / 'results.json').read_text())['r0_doppler_err_snr4_5']['delay']
   215	    eff = {str(r): dict(actual_pilot_r0_err_snr4_5=a3[str(r)],
   216	                        pilot_white_bound_snr4_5=float(np.mean([table['pilot_white'][f'{r}_{s}']['mean'] for s in (400, 500)])))
   217	           for r in RHOS}
   218	    res = dict(_argv=sys.argv, protocol='STAGEA4_PROTOCOL.md', table=table, verdict=verdict, deciding_bound=why,
   219	               deciding_rho=best, target=TARGET, loose=LOOSE, efficiency=eff, status=status)
   220	    (out / 'results.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
   221	
   222	
   223	if __name__ == '__main__':
   224	    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('gate', 'run', 'read')); ap.add_argument('--out', required=True)
   225	    a = ap.parse_args()
   226	    dict(gate=gate, run=run, read=read)[a.mode](a.out)
     1	"""Unit tests for stageA5.py: fast covariance exactness, NLL exactness, metric, and verdict boundaries."""
     2	from __future__ import annotations
     3	
     4	import sys
     5	from pathlib import Path
     6	import numpy as np
     7	
     8	HERE = Path(__file__).resolve().parent
     9	sys.path.insert(0, str(HERE))
    10	
    11	import stageA5 as a5  # noqa: E402
    12	
    13	
    14	def test_fast_covariance_and_nll_exactness():
    15	    rng = np.random.default_rng(123)
    16	    n, p, c1 = 64, 5, 0.004395
    17	    delays = np.array([0, 3, 11, 25, 41], dtype=int)
    18	    nu = np.array([-1.3, -0.2, 0.45, 1.1, 2.05], dtype=float)
    19	    g = (rng.standard_normal(p) + 1j * rng.standard_normal(p)) * 0.4
    20	    p_t = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    21	    r = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    22	    vd, sigma2 = 0.85, 0.4
    23	
    24	    geom = a5.precompute_delay_geometry(delays, n, c1)
    25	    c_mat = a5.doppler_vectors(geom, nu)
    26	
    27	    # Dense reference T
    28	    k = np.arange(n)
    29	    T = np.zeros((n, n), dtype=np.complex128)
    30	    for i in range(p):
    31	        T[k, (k - delays[i]) % n] += g[i] * c_mat[i]
    32	    C_ref = vd * (T @ T.conj().T) + sigma2 * np.eye(n, dtype=np.complex128)
    33	    C_fast = a5.build_covariance_fast(geom, c_mat, g, vd, sigma2)
    34	    assert np.linalg.norm(C_fast - C_ref) / np.linalg.norm(C_ref) < 1e-14
    35	
    36	    # Check _nll_for_path against direct slogdet + solve
    37	    p_idx = 2
    38	    C_base = a5._build_cov_without_path(geom, c_mat, g, vd, sigma2, p_idx)
    39	    shifted = p_t[geom['cols']]
    40	    e_base = r - sum((g[j] * c_mat[j]) * shifted[j] for j in range(p) if j != p_idx)
    41	    nll_fast = a5._nll_for_path(nu[p_idx], p_idx, geom, c_mat, g, vd, C_base, e_base, shifted[p_idx])
    42	    e_ref = r - T @ p_t
    43	    _, ld = np.linalg.slogdet(C_ref)
    44	    nll_ref = float(ld + np.vdot(e_ref, np.linalg.solve(C_ref, e_ref)).real)
    45	    assert abs(nll_fast - nll_ref) / abs(nll_ref) < 1e-13, (nll_fast, nll_ref)
    46	
    47	
    48	def test_verdict_and_metric():
    49	    assert a5.verdict_a5(0.04, 0.08) == 'PASS'
    50	    assert a5.verdict_a5(0.04, 0.079) == 'PASS'
    51	    assert a5.verdict_a5(0.0801, 0.12) == 'FAIL'
    52	    assert a5.verdict_a5(0.08, 0.12) == 'BORDERLINE'
    53	    assert a5.verdict_a5(0.06, 0.09) == 'BORDERLINE'
    54	
    55	    # Cap at 0.375 and outlier > 0.25
    56	    m, o, _ = a5.doppler_metric(np.array([0.0, 1.0]), np.array([0.05, 0.0]), np.array([1.0, 1.0]))
    57	    assert abs(m - 0.5 * (0.05 + 0.375)) < 1e-12
    58	    assert abs(o - 0.5) < 1e-12
    59	
    60	
    61	if __name__ == '__main__':
    62	    test_fast_covariance_and_nll_exactness()
    63	    test_verdict_and_metric()
    64	    print('ALL_STAGEA5_UNIT_TESTS_PASS')
stageA2.py:15:from multiprocessing import get_context
stage0.py:8:from multiprocessing import get_context
stage0.py:28:def setup():
stageA3.py:12:from multiprocessing import get_context
stageA.py:13:from multiprocessing import get_context
stageA.py:34:def setup():
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-yWcfhLvQ' (errno=Operation not permitted)
?? STAGEA5_PROTOCOL.md
?? stageA5.py
?? stageA5_launch.sh
?? test_stageA5.py
../../AGENTS.md
../../STATE.md
../../.trellis/workflow.md

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '651,865p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   651	def _run_shard_worker(shard_idx: int, draws: list[tuple[int, str]], snrs: tuple[int, ...], raw_dir: Path):
   652	    C, _, daft = _load_runtime()
   653	    st, ctx = C['stage3'], C['ctx']
   654	    c1, c2 = ctx.system.c1, ctx.system.c2
   655	    lines: list[str] = []
   656	    for frame, s in draws:
   657	        for rho in RHOS:
   658	            base = st.inputs(ctx, frame, s, rho)
   659	            for snr in snrs:
   660	                raw, _, truth = st.observed(ctx, base, rho, snr)
   661	                y = np.asarray(raw['y'], dtype=np.complex128)
   662	                p = np.asarray(raw['pilot'], dtype=np.complex128)
   663	                d = np.asarray(raw['data'], dtype=np.complex128)
   664	                sigma2 = float(raw['sigma2'])
   665	                vd = float(np.mean(np.abs(d) ** 2))
   666	                n = len(y)
   667	                r = daft(y, c1, c2, True)
   668	                p_t = daft(p, c1, c2, True)
   669	                x_t = daft(p + d, c1, c2, True)
   670	                geom = precompute_delay_geometry(truth['l_i'], n, c1)
   671	
   672	                nu_pw, g_pw = estimate_pw(geom, p_t, r)
   673	                nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   674	                nu_kd, _ = estimate_kd(geom, x_t, r)
   675	
   676	                m_pw, o_pw, e_pw = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
   677	                m_sb, o_sb, e_sb = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   678	                m_kd, o_kd, e_kd = doppler_metric(nu_kd, truth['k_real'], truth['g_i'])
   679	
   680	                lines.append(json.dumps(dict(
   681	                    frame=frame, scenario=s, rho=rho, snr=snr,
   682	                    metric=dict(PW=m_pw, SB=m_sb, KD=m_kd),
   683	                    outlier_frac=dict(PW=o_pw, SB=o_sb, KD=o_kd),
   684	                    abs_err=dict(PW=e_pw, SB=e_sb, KD=e_kd),
   685	                ), allow_nan=False) + '\n')
   686	
   687	    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
   688	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   689	    with part_path.open('wb') as raw_fh:
   690	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
   691	            for ln in lines:
   692	                gz.write(ln.encode('utf-8'))
   693	        raw_fh.flush()
   694	        os.fsync(raw_fh.fileno())
   695	    os.replace(part_path, final_path)
   696	    print(f'Shard {shard_idx:03d} done ({len(lines)} keys)', flush=True)
   697	
   698	
   699	def verdict_a5(ci_lo: float, ci_hi: float) -> str:
   700	    if ci_hi <= PASS_THRESH:
   701	        return 'PASS'
   702	    if ci_lo > PASS_THRESH:
   703	        return 'FAIL'
   704	    return 'BORDERLINE'
   705	
   706	
   707	def analyze_stageA5(
   708	    rows: list[dict[str, Any]],
   709	    a4_rows: list[dict[str, Any]],
   710	    snrs: tuple[int, ...],
   711	    a3_actual_pilot: dict[str, float],
   712	    *,
   713	    boot_draws: int = BOOT_DRAWS,
   714	    boot_seed: int = BOOT_SEED,
   715	) -> dict[str, Any]:
   716	    """Frozen Stage A5 readout with paired bootstrap over the 200 (frame, scenario) draws."""
   717	    draws = sorted({(int(r['frame']), r['scenario']) for r in rows})
   718	    di = {k: i for i, k in enumerate(draws)}
   719	    n_draws = len(draws)
   720	    ests = ('PW', 'SB', 'KD')
   721	
   722	    M = np.full((len(ests), len(RHOS), len(snrs), n_draws), np.nan, dtype=np.float64)
   723	    O = np.full((len(ests), len(RHOS), len(snrs), n_draws), np.nan, dtype=np.float64)
   724	    for r in rows:
   725	        ri = RHOS.index(int(r['rho']))
   726	        si = snrs.index(int(r['snr']))
   727	        d_idx = di[(int(r['frame']), r['scenario'])]
   728	        for ei, e in enumerate(ests):
   729	            M[ei, ri, si, d_idx] = float(r['metric'][e])
   730	            O[ei, ri, si, d_idx] = float(r['outlier_frac'][e])
   731	    if np.isnan(M).any():
   732	        raise RuntimeError('Incomplete Stage A5 metric grid')
   733	
   734	    # Pair with Stage A4 CRB metrics on the exact same 200 draws
   735	    a4_bounds = ('pilot_white', 'pilot', 'semiblind', 'known')
   736	    B = np.full((len(a4_bounds), len(RHOS), len(snrs), n_draws), np.nan, dtype=np.float64)
   737	    for r in a4_rows:
   738	        snr = int(r['snr'])
   739	        if snr not in snrs:
   740	            continue
   741	        k = (int(r['frame']), r['scenario'])
   742	        if k not in di:
   743	            continue
   744	        ri = RHOS.index(int(r['rho']))
   745	        si = snrs.index(snr)
   746	        d_idx = di[k]
   747	        for bi, bname in enumerate(a4_bounds):
   748	            B[bi, ri, si, d_idx] = float(r['metric'][bname])
   749	    if np.isnan(B).any():
   750	        raise RuntimeError('Incomplete Stage A4 paired CRB grid')
   751	
   752	    rng = np.random.default_rng(boot_seed)
   753	    boot_idx = rng.integers(0, n_draws, size=(boot_draws, n_draws))
   754	
   755	    # Primary E = min_{rho in {100,150}} mean(SB at 4 dB)
   756	    si_400 = snrs.index(DECIDE_SNR)
   757	    ei_sb = ests.index('SB')
   758	    ri_100, ri_150 = RHOS.index(100), RHOS.index(150)
   759	    sb_100 = M[ei_sb, ri_100, si_400]
   760	    sb_150 = M[ei_sb, ri_150, si_400]
   761	    mean_100 = float(sb_100.mean())
   762	    mean_150 = float(sb_150.mean())
   763	    E_pt = min(mean_100, mean_150)
   764	    E_rho = 100 if mean_100 <= mean_150 else 150
   765	    b_100 = sb_100[boot_idx].mean(axis=1)
   766	    b_150 = sb_150[boot_idx].mean(axis=1)
   767	    E_boot = np.minimum(b_100, b_150)
   768	    E_lo, E_hi = (float(x) for x in np.percentile(E_boot, [2.5, 97.5]))
   769	    verdict = verdict_a5(E_lo, E_hi)
   770	
   771	    table: dict[str, dict[str, Any]] = {}
   772	    for ei, e in enumerate(ests):
   773	        table[e] = {}
   774	        for ri, rho in enumerate(RHOS):
   775	            for si, snr in enumerate(snrs):
   776	                v = M[ei, ri, si]
   777	                bm = v[boot_idx].mean(axis=1)
   778	                ci = [float(x) for x in np.percentile(bm, [2.5, 97.5])]
   779	                table[e][f'{rho}_{snr}'] = dict(
   780	                    mean=float(v.mean()),
   781	                    median=float(np.median(v)),
   782	                    ci95=ci,
   783	                    outlier_gt_0p25_frac=float(O[ei, ri, si].mean()),
   784	                )
   785	
   786	    crb_table: dict[str, dict[str, float]] = {}
   787	    for bi, bname in enumerate(a4_bounds):
   788	        crb_table[bname] = {
   789	            f'{rho}_{snr}': float(B[bi, ri, si].mean())
   790	            for ri, rho in enumerate(RHOS) for si, snr in enumerate(snrs)
   791	        }
   792	
   793	    efficiency: dict[str, Any] = {}
   794	    for ri, rho in enumerate(RHOS):
   795	        key4 = f'{rho}_{DECIDE_SNR}'
   796	        sb_m = table['SB'][key4]['mean']
   797	        sb_c = crb_table['semiblind'][key4]
   798	        pw_m = table['PW'][key4]['mean']
   799	        pw_c = crb_table['pilot_white'][key4]
   800	        kd_m = table['KD'][key4]['mean']
   801	        kd_c = crb_table['known'][key4]
   802	        efficiency[str(rho)] = dict(
   803	            sb_over_sb_crb=float(sb_m / sb_c),
   804	            pw_over_pilot_white_crb=float(pw_m / pw_c),
   805	            kd_over_known_crb=float(kd_m / kd_c),
   806	            pw_4db_mean=pw_m,
   807	            stageA_actual_pilot_4_5db=float(a3_actual_pilot[str(rho)]),
   808	            pw_over_stageA_actual=float(pw_m / float(a3_actual_pilot[str(rho)])),
   809	        )
   810	
   811	    return dict(
   812	        draws=n_draws,
   813	        snrs=list(snrs),
   814	        boot_draws=boot_draws,
   815	        boot_seed=boot_seed,
   816	        primary=dict(
   817	            E_point=E_pt,
   818	            E_ci95=[E_lo, E_hi],
   819	            best_rho=E_rho,
   820	            threshold=PASS_THRESH,
   821	            verdict=verdict,
   822	        ),
   823	        table=table,
   824	        crb_mean=crb_table,
   825	        efficiency_4db=efficiency,
   826	    )
   827	
   828	
   829	def render_results_md(res: dict[str, Any]) -> str:
   830	    a = res['analysis']
   831	    p = a['primary']
   832	    lines = [
   833	        '# Stage A5 Results: Semi-Blind Round-0 Doppler Proxy Check',
   834	        '',
   835	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
   836	        f'- Draws: **{a["draws"]}** (frames `41000–41099` × U/G), SNRs: `{a["snrs"]}`',
   837	        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 6.0 h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
   838	        '',
   839	        '## Primary Verdict (Pre-Registered, SNR = 4 dB)',
   840	        '',
   841	        f'- `E = min_{{ρ ∈ {{0.10, 0.15}}}} mean(SB)` = **{p["E_point"]:.4f} bin** (at ρ={p["best_rho"]/1000:.2f}), '
   842	        f'95% CI **[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] bin** → **{p["verdict"]}** (threshold `0.08` bin)',
   843	        '',
   844	        '## 4 dB Summary Table (Power-Weighted Capped MAE, bin; 200 Draws)',
   845	        '',
   846	        '| ρ | PW mean [med] | SB mean [med] (95% CI) | KD mean [med] | SB-CRB | PW-CRB | SB Eff | PW Eff | SB Outlier >0.25 | Stage A Actual (4–5 dB) |',
   847	        '|---:|---|---|---|---:|---:|---:|---:|---:|---:|',
   848	    ]
   849	    for rho in RHOS:
   850	        k4 = f'{rho}_400'
   851	        pw = a['table']['PW'][k4]
   852	        sb = a['table']['SB'][k4]
   853	        kd = a['table']['KD'][k4]
   854	        eff = a['efficiency_4db'][str(rho)]
   855	        lines.append(
   856	            f'| {rho/1000:.2f} | {pw["mean"]:.4f} [{pw["median"]:.4f}] | '
   857	            f'**{sb["mean"]:.4f}** [{sb["median"]:.4f}] ([{sb["ci95"][0]:.4f}, {sb["ci95"][1]:.4f}]) | '
   858	            f'{kd["mean"]:.4f} [{kd["median"]:.4f}] | '
   859	            f'{a["crb_mean"]["semiblind"][k4]:.4f} | {a["crb_mean"]["pilot_white"][k4]:.4f} | '
   860	            f'{eff["sb_over_sb_crb"]:.2f}× | {eff["pw_over_pilot_white_crb"]:.2f}× | '
   861	            f'{100*sb["outlier_gt_0p25_frac"]:.2f}% | {eff["stageA_actual_pilot_4_5db"]:.4f} |'
   862	        )
   863	    return '\n'.join(lines) + '\n'
   864	
   865	

exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '409,650p'; find out -name '*stageA5*' -print" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   409	def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
   410	    n_workers = min(max_workers, max(1, len(items)))
   411	    buckets = [items[i::n_workers] for i in range(n_workers)]
   412	    mp_ctx = multiprocessing.get_context('spawn')
   413	    out_files = []
   414	    procs = []
   415	    for wi, bucket in enumerate(buckets):
   416	        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
   417	        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
   418	        in_f.write_text(json.dumps(bucket), encoding='utf-8')
   419	        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
   420	        p.start()
   421	        procs.append((wi, p))
   422	        out_files.append(out_f)
   423	    for wi, p in procs:
   424	        p.join()
   425	        code = p.exitcode
   426	        p.close()
   427	        if code != 0:
   428	            raise RuntimeError(f'Worker {tag}/{wi} exited with code {code}')
   429	    merged: list[tuple[int, Any]] = []
   430	    for wi, out_f in enumerate(out_files):
   431	        chunk = json.loads(out_f.read_text(encoding='utf-8'))
   432	        for pos, val in enumerate(chunk):
   433	            merged.append((wi + pos * n_workers, val))
   434	    merged.sort(key=lambda x: x[0])
   435	    return [v for _, v in merged]
   436	
   437	
   438	def _load_runtime():
   439	    ar.verify_frozen_extra_md5()
   440	    import stageA  # noqa: E402
   441	    import stageA4  # noqa: E402
   442	    from physical import daft  # noqa: E402
   443	
   444	    C = stageA.setup()
   445	    return C, stageA4, daft
   446	
   447	
   448	# --------------------------------------------------------------------------- Gates G1-G4
   449	def _g3_worker(in_path: str, out_path: str):
   450	    C, stageA4, daft = _load_runtime()
   451	    st, ctx = C['stage3'], C['ctx']
   452	    c1, c2 = ctx.system.c1, ctx.system.c2
   453	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   454	    out = []
   455	    for frame, s in jobs:
   456	        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, 300), 300, 1200)
   457	        y = np.asarray(raw['y'], dtype=np.complex128)
   458	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   459	        d = np.asarray(raw['data'], dtype=np.complex128)
   460	        sigma2 = float(raw['sigma2'])
   461	        vd = float(np.mean(np.abs(d) ** 2))
   462	        n = len(y)
   463	        r = daft(y, c1, c2, True)
   464	        p_t = daft(p, c1, c2, True)
   465	        geom = precompute_delay_geometry(truth['l_i'], n, c1)
   466	        nu_pw, g_pw = estimate_pw(geom, p_t, r)
   467	        nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   468	        m_sb, out_sb, _ = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   469	        m_pw, _, _ = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
   470	        P = stageA4.prepare(truth, n, c1)
   471	        F = stageA4.fims(P, p, d, sigma2, n, c1, c2)
   472	        crb_sb = stageA4.crb_nu(F['semiblind'], len(truth['l_i']))
   473	        m_crb_sb = stageA4.metric(crb_sb, truth['g_i'])
   474	        out.append(dict(frame=frame, scenario=s, sb=m_sb, pw=m_pw, sb_crb=m_crb_sb, outlier_sb=out_sb))
   475	    ar.atomic_write_text(Path(out_path), json.dumps(out))
   476	
   477	
   478	def _g4_worker(in_path: str, out_path: str):
   479	    C, _, daft = _load_runtime()
   480	    st, ctx = C['stage3'], C['ctx']
   481	    c1, c2 = ctx.system.c1, ctx.system.c2
   482	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   483	    out = []
   484	    for frame, s, rho, snr in jobs:
   485	        t0 = time.process_time()
   486	        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, snr)
   487	        y = np.asarray(raw['y'], dtype=np.complex128)
   488	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   489	        d = np.asarray(raw['data'], dtype=np.complex128)
   490	        sigma2 = float(raw['sigma2'])
   491	        vd = float(np.mean(np.abs(d) ** 2))
   492	        n = len(y)
   493	        r = daft(y, c1, c2, True)
   494	        p_t = daft(p, c1, c2, True)
   495	        x_t = daft(p + d, c1, c2, True)
   496	        geom = precompute_delay_geometry(truth['l_i'], n, c1)
   497	        t_pw0 = time.process_time()
   498	        nu_pw, g_pw = estimate_pw(geom, p_t, r)
   499	        t_pw = time.process_time() - t_pw0
   500	        t_sb0 = time.process_time()
   501	        nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   502	        t_sb = time.process_time() - t_sb0
   503	        t_kd0 = time.process_time()
   504	        nu_kd, _ = estimate_kd(geom, x_t, r)
   505	        t_kd = time.process_time() - t_kd0
   506	        tot = time.process_time() - t0
   507	        out.append(dict(key=[frame, s, rho, snr], total_cpu=tot, pw_cpu=t_pw, sb_cpu=t_sb, kd_cpu=t_kd))
   508	    ar.atomic_write_text(Path(out_path), json.dumps(out))
   509	
   510	
   511	def cmd_gate(args):
   512	    print(sys.executable, flush=True)
   513	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   514	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   515	    thread_env = ar.check_thread_env()
   516	    started = time.monotonic()
   517	
   518	    gate_path = args.out.resolve()
   519	    gate_path.parent.mkdir(parents=True, exist_ok=True)
   520	    if gate_path.exists():
   521	        gate_path.unlink()
   522	
   523	    C, stageA4, daft = _load_runtime()
   524	    st, ctx = C['stage3'], C['ctx']
   525	    c1, c2 = ctx.system.c1, ctx.system.c2
   526	
   527	    # Verify stageA4 rows archive exists & matches MD5
   528	    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
   529	    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
   530	        raise RuntimeError(f'stageA4 rows.jsonl.gz MD5 mismatch: {ar.md5_file(a4_rows_path)}')
   531	
   532	    # G1: noiseless KD from truth + 0.1 bin on 4 keys + fast covariance exactness check
   533	    g1_keys = (('U', 100, 400, 41200), ('G', 150, 400, 41201), ('U', 200, 400, 41202), ('G', 100, 400, 41203))
   534	    g1_rows = []
   535	    for s, rho, snr, frame in g1_keys:
   536	        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, snr)
   537	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   538	        d = np.asarray(raw['data'], dtype=np.complex128)
   539	        y0 = np.asarray(raw['noiseless'], dtype=np.complex128)
   540	        n = len(y0)
   541	        r0 = daft(y0, c1, c2, True)
   542	        x_t = daft(p + d, c1, c2, True)
   543	        geom = precompute_delay_geometry(truth['l_i'], n, c1)
   544	        nu_true = np.asarray(truth['k_real'], dtype=np.float64)
   545	        nu_hat, _ = estimate_kd(geom, x_t, r0, nu_init=nu_true + 0.1, sweeps=2, xatol=1e-4)
   546	        max_err = float(np.max(np.abs(nu_hat - nu_true)))
   547	
   548	        # Verify fast covariance vs dense stageA4.model
   549	        T_ref, _ = stageA4.model(truth, n, c1)
   550	        vd = float(np.mean(np.abs(d) ** 2))
   551	        s2 = float(raw['sigma2'])
   552	        C_ref = vd * (T_ref @ T_ref.conj().T) + s2 * np.eye(n, dtype=np.complex128)
   553	        c_mat = doppler_vectors(geom, nu_true)
   554	        C_fast = build_covariance_fast(geom, c_mat, np.asarray(truth['g_i'], dtype=np.complex128), vd, s2)
   555	        cov_err = float(np.linalg.norm(C_fast - C_ref) / np.linalg.norm(C_ref))
   556	        g1_rows.append(dict(key=[s, rho, snr, frame], max_nu_err=max_err, cov_rel_err=cov_err))
   557	    g1_pass = bool(all(x['max_nu_err'] < 1e-3 and x['cov_rel_err'] < 1e-13 for x in g1_rows))
   558	    print(f'G1 {"PASS" if g1_pass else "FAIL"} max_nu_err={max(x["max_nu_err"] for x in g1_rows):.2e} cov_err={max(x["cov_rel_err"] for x in g1_rows):.2e}', flush=True)
   559	
   560	    # G2: KD Monte Carlo at 12 dB, 100 noise draws on one key -> median var / CRB_known in [0.7, 1.5]
   561	    raw_g2, _, truth_g2 = st.observed(ctx, st.inputs(ctx, 41200, 'U', 100), 100, 1200)
   562	    p_g2 = np.asarray(raw_g2['pilot'], dtype=np.complex128)
   563	    d_g2 = np.asarray(raw_g2['data'], dtype=np.complex128)
   564	    y0_g2 = np.asarray(raw_g2['noiseless'], dtype=np.complex128)
   565	    s2_g2 = float(raw_g2['sigma2'])
   566	    n_g2 = len(y0_g2)
   567	    r0_g2 = daft(y0_g2, c1, c2, True)
   568	    xt_g2 = daft(p_g2 + d_g2, c1, c2, True)
   569	    geom_g2 = precompute_delay_geometry(truth_g2['l_i'], n_g2, c1)
   570	    nu_true_g2 = np.asarray(truth_g2['k_real'], dtype=np.float64)
   571	    P_g2 = stageA4.prepare(truth_g2, n_g2, c1)
   572	    F_g2 = stageA4.fims(P_g2, p_g2, d_g2, s2_g2, n_g2, c1, c2)
   573	    crb_kd = stageA4.crb_nu(F_g2['known'], len(nu_true_g2))
   574	    rng_g2 = np.random.default_rng(BOOT_SEED)
   575	    errs_g2 = np.empty((100, len(nu_true_g2)), dtype=np.float64)
   576	    for di in range(100):
   577	        w = np.sqrt(s2_g2 / 2.0) * (rng_g2.standard_normal(n_g2) + 1j * rng_g2.standard_normal(n_g2))
   578	        nu_h, _ = estimate_kd(geom_g2, xt_g2, r0_g2 + w, sweeps=2, xatol=1e-4)
   579	        errs_g2[di] = nu_h - nu_true_g2
   580	    var_ratio = np.var(errs_g2, axis=0, ddof=1) / crb_kd
   581	    med_ratio = float(np.median(var_ratio))
   582	    g2_pass = bool(0.7 <= med_ratio <= 1.5)
   583	    print(f'G2 {"PASS" if g2_pass else "FAIL"} median var/CRB_known={med_ratio:.3f} per_path={[round(float(v), 3) for v in var_ratio]}', flush=True)
   584	
   585	    # G3 (20 benign draws: frames 41200..41209 x U/G at rho=.30, 12 dB) & G4 (6 cost keys at 4 dB)
   586	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   587	    ipc_dir = tmp_root / f'stageA5_gates_ipc_{os.getpid()}'
   588	    ipc_dir.mkdir(parents=True, exist_ok=True)
   589	    try:
   590	        g3_jobs = [[f, s] for f in range(41200, 41210) for s in SCENARIOS]
   591	        print('Running G3 (20 benign draws: rho=0.30, 12 dB)...', flush=True)
   592	        g3_rows = _spawn_map(_g3_worker, g3_jobs, min(args.workers, 20), ipc_dir, 'g3')
   593	        mean_sb = float(np.mean([x['sb'] for x in g3_rows]))
   594	        mean_sb_crb = float(np.mean([x['sb_crb'] for x in g3_rows]))
   595	        mean_pw = float(np.mean([x['pw'] for x in g3_rows]))
   596	        sb_ratio = mean_sb / mean_sb_crb
   597	        g3_pass = bool(sb_ratio <= 1.5)
   598	        print(f'G3 {"PASS" if g3_pass else "FAIL"} mean_sb={mean_sb:.5f} mean_sb_crb={mean_sb_crb:.5f} ratio={sb_ratio:.3f} (mean_pw={mean_pw:.5f})', flush=True)
   599	
   600	        g4_jobs = [[41220, 'U', rho, 400] for rho in RHOS] + [[41221, 'G', rho, 400] for rho in RHOS]
   601	        print('Running G4 cost benchmark (6 keys at 4 dB)...', flush=True)
   602	        g4_rows = _spawn_map(_g4_worker, g4_jobs, min(args.workers, 6), ipc_dir, 'g4')
   603	    finally:
   604	        shutil.rmtree(ipc_dir, ignore_errors=True)
   605	
   606	    mean_key_cpu = float(np.mean([x['total_cpu'] for x in g4_rows]))
   607	    candidates = []
   608	    for snrs in ((300, 400, 500), (400,)):
   609	        n_keys = len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(snrs)
   610	        raw_h = mean_key_cpu * n_keys / 3600.0 + OVERHEAD_HOURS
   611	        marg_h = raw_h * COST_MARGIN
   612	        candidates.append(dict(
   613	            snrs=list(snrs),
   614	            n_keys=n_keys,
   615	            mean_cpu_sec_per_key=mean_key_cpu,
   616	            raw_hours=raw_h,
   617	            projected_hours_with_margin=marg_h,
   618	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   619	        ))
   620	    selected = next((c for c in candidates if c['within_budget']), None)
   621	    g4_pass = selected is not None
   622	    all_passed = bool(g1_pass and g2_pass and g3_pass and g4_pass)
   623	    gate_cpu_h = _used_cpu_seconds() / 3600.0
   624	
   625	    payload = dict(
   626	        _argv=sys.argv,
   627	        _config=dict(
   628	            python_executable=sys.executable,
   629	            threads=thread_env,
   630	            workers=args.workers,
   631	            own_md5=own_md5(),
   632	            stageA_py_md5=ar.md5_file(HERE / 'stageA.py'),
   633	            stageA4_py_md5=ar.md5_file(HERE / 'stageA4.py'),
   634	            stageA4_rows_md5=STAGEA4_ROWS_MD5,
   635	        ),
   636	        all_passed=all_passed,
   637	        selected=selected,
   638	        G1=dict(passed=g1_pass, rows=g1_rows),
   639	        G2=dict(passed=g2_pass, draws=100, median_var_over_crb=med_ratio, per_path_var_over_crb=var_ratio.tolist()),
   640	        G3=dict(passed=g3_pass, draws=len(g3_rows), mean_sb=mean_sb, mean_sb_crb=mean_sb_crb, ratio=sb_ratio, mean_pw=mean_pw, rows=g3_rows),
   641	        G4=dict(passed=g4_pass, budget_cap_core_hours=BUDGET_CAP_HOURS, margin=COST_MARGIN, candidates=candidates, samples=g4_rows),
   642	        gate_cpu_hours=gate_cpu_h,
   643	        gate_wall_seconds=time.monotonic() - started,
   644	    )
   645	    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
   646	    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
   647	    sys.exit(0 if all_passed else 1)
   648	
   649	
   650	# --------------------------------------------------------------------------- Main run & readout
out/stageA5_sol_review.md

exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '866,1015p'; wc -l ../../AGENTS.md ../../STATE.md ../../.trellis/workflow.md; rg -n -i 'current|active|stage a5|stagea5|read.only|static|review' ../../AGENTS.md ../../STATE.md ../../.trellis/workflow.md; ls -a ../../.trellis" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   866	def cmd_run(args):
   867	    print(sys.executable, flush=True)
   868	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   869	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   870	    ar.check_thread_env()
   871	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   872	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   873	    if not 1 <= args.workers <= 32:
   874	        raise ValueError('workers must be in 1..32')
   875	
   876	    gate_path = args.gate.resolve()
   877	    gate_bytes = gate_path.read_bytes()
   878	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   879	    gate = json.loads(gate_bytes.decode('utf-8'))
   880	    if not gate.get('all_passed') or not gate.get('selected'):
   881	        raise RuntimeError('Refusing to run without passing stageA5_gate.json')
   882	    live_own = own_md5()
   883	    if gate['_config']['own_md5'] != live_own:
   884	        raise RuntimeError('gate.json own_md5 mismatch; re-run gates')
   885	    if gate['_config']['stageA_py_md5'] != ar.md5_file(HERE / 'stageA.py') or gate['_config']['stageA4_py_md5'] != ar.md5_file(HERE / 'stageA4.py'):
   886	        raise RuntimeError('Reused stageA/stageA4 MD5 mismatch vs gate.json')
   887	
   888	    snrs = tuple(int(s) for s in gate['selected']['snrs'])
   889	    out_dir = args.out.resolve()
   890	    raw_dir = out_dir / 'raw'
   891	    raw_dir.mkdir(parents=True, exist_ok=True)
   892	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   893	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   894	
   895	    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
   896	    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
   897	        raise RuntimeError('stageA4 rows.jsonl.gz MD5 mismatch')
   898	
   899	    wall_start = time.monotonic()
   900	    all_draws = [(f, s) for f in FRAMES for s in SCENARIOS]
   901	    n_shards = args.workers
   902	    mp_ctx = multiprocessing.get_context('spawn')
   903	    running = {}
   904	    budget_hit = False
   905	    print(f'Launching Stage A5: {len(all_draws)} draws x {len(RHOS)} rhos x {len(snrs)} SNRs ({snrs}) on {n_shards} workers...', flush=True)
   906	    try:
   907	        for idx in range(n_shards):
   908	            sub_draws = all_draws[idx::n_shards]
   909	            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_draws, snrs, raw_dir))
   910	            p.start()
   911	            running[p.sentinel] = (idx, p)
   912	        while running:
   913	            ready = wait(running, timeout=10.0)
   914	            for r in ready:
   915	                idx, p = running.pop(r)
   916	                p.join()
   917	                code = p.exitcode
   918	                p.close()
   919	                if code != 0:
   920	                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
   921	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   922	            if live_cpu >= BUDGET_CAP_SEC - 180.0:
   923	                budget_hit = True
   924	                break
   925	    finally:
   926	        for _, p in running.values():
   927	            p.terminate()
   928	        for _, p in running.values():
   929	            p.join()
   930	            p.close()
   931	    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
   932	        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   933	        sys.exit(BUDGET_EXIT_CODE)
   934	
   935	    # Merge shard MD5s and load all rows
   936	    raw_md5 = {}
   937	    rows = []
   938	    for idx in range(n_shards):
   939	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
   940	        raw_md5[sp.name] = ar.md5_file(sp)
   941	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   942	            for line in fh:
   943	                rows.append(json.loads(line))
   944	    ar.atomic_write_text(
   945	        out_dir / 'REMOTE_ROWS_MD5.txt',
   946	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
   947	    )
   948	
   949	    a4_rows = [json.loads(ln) for ln in gzip.open(a4_rows_path, 'rt', encoding='utf-8')]
   950	    a3_actual = json.loads((HERE / 'out' / 'stageA3' / 'results.json').read_text(encoding='utf-8'))['r0_doppler_err_snr4_5']['delay']
   951	    analysis = analyze_stageA5(rows, a4_rows, snrs, a3_actual)
   952	
   953	    total_cpu_h = _used_cpu_seconds() / 3600.0
   954	    if total_cpu_h >= BUDGET_CAP_HOURS:
   955	        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
   956	        sys.exit(BUDGET_EXIT_CODE)
   957	
   958	    results = dict(
   959	        _argv=sys.argv,
   960	        _config=dict(
   961	            freeze_commit=args.freeze_commit,
   962	            python_executable=sys.executable,
   963	            own_md5=live_own,
   964	            gate_md5=gate_md5,
   965	            snrs=list(snrs),
   966	            rhos=list(RHOS),
   967	            frames=[FRAMES[0], FRAMES[-1]],
   968	            draws=len(all_draws),
   969	            raw_output_dir=str(raw_dir),
   970	            raw_rows_md5=raw_md5,
   971	            stageA4_rows_md5=STAGEA4_ROWS_MD5,
   972	        ),
   973	        gates=dict(
   974	            all_passed=gate['all_passed'],
   975	            selected=gate['selected'],
   976	            G2_median_var_over_crb=gate['G2']['median_var_over_crb'],
   977	            G3_sb_over_crb_ratio=gate['G3']['ratio'],
   978	        ),
   979	        runtime=dict(
   980	            total_core_hours=total_cpu_h,
   981	            wall_seconds=time.monotonic() - wall_start,
   982	            cpu_cap_core_hours=BUDGET_CAP_HOURS,
   983	        ),
   984	        analysis=analysis,
   985	    )
   986	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
   987	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
   988	    p = analysis['primary']
   989	    print(
   990	        f'STAGEA5_DONE verdict={p["verdict"]} E={p["E_point"]:.4f} '
   991	        f'ci=[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] rho={p["best_rho"]} '
   992	        f'cpu_hours={total_cpu_h:.4f}',
   993	        flush=True,
   994	    )
   995	
   996	
   997	def main():
   998	    ap = argparse.ArgumentParser(description=__doc__)
   999	    sub = ap.add_subparsers(dest='mode', required=True)
  1000	    g = sub.add_parser('gate')
  1001	    g.add_argument('--out', type=Path, required=True)
  1002	    g.add_argument('--workers', type=int, default=16)
  1003	
  1004	    r = sub.add_parser('run')
  1005	    r.add_argument('--gate', type=Path, required=True)
  1006	    r.add_argument('--out', type=Path, required=True)
  1007	    r.add_argument('--freeze-commit', required=True)
  1008	    r.add_argument('--workers', type=int, default=WORKERS)
  1009	
  1010	    args = ap.parse_args()
  1011	    dict(gate=cmd_gate, run=cmd_run)[args.mode](args)
  1012	
  1013	
  1014	if __name__ == '__main__':
  1015	    main()
      37 ../../AGENTS.md
     142 ../../STATE.md
     726 ../../.trellis/workflow.md
     905 total
../../.trellis/workflow.md:11:5. **Capture learnings** — after each task, review and write new knowledge back to spec
../../.trellis/workflow.md:47:python3 ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
../../.trellis/workflow.md:48:python3 ./.trellis/scripts/task.py current --source      # show active task and source
../../.trellis/workflow.md:49:python3 ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
../../.trellis/workflow.md:76:**Current-task mechanism**: `task.py create` creates the task directory and (when session identity is available) auto-sets the per-session active-task pointer so the planning breadcrumb fires immediately. `task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`. State is stored under `.trellis/.runtime/sessions/`. If no context key is available from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable, there is no active task and `task.py start` fails with a session identity hint. `task.py finish` deletes the current session file (status unchanged). `task.py archive <task>` writes `status=completed`, moves the directory to `archive/`, and deletes any runtime session files that still point at the archived task.
../../.trellis/workflow.md:83:- `index.md` — personal index (total sessions, last active).
../../.trellis/workflow.md:110:  degrades to a generic "Refer to workflow.md for current step." line —
../../.trellis/workflow.md:121:    [workflow-state:no_task]      → no active task; before Phase 1
../../.trellis/workflow.md:128:    [workflow-state:completed]    → currently DEAD: cmd_archive flips
../../.trellis/workflow.md:154:- Simple read-only work: execute directly with appropriate evidence and validation; do not create a Trellis task.
../../.trellis/workflow.md:163:- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
../../.trellis/workflow.md:169:Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.
../../.trellis/workflow.md:175:<!-- Per-turn breadcrumb: shown when there is no active task (before Phase 1) -->
../../.trellis/workflow.md:178:No active task. First classify the current turn by work type and task weight.
../../.trellis/workflow.md:179:Simple read-only work: execute directly with evidence and validation; do not create a Trellis task.
../../.trellis/workflow.md:189:- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
../../.trellis/workflow.md:196:Lightweight: `prd.md` can be enough. Complex: finish `prd.md`, `design.md`, and `implement.md`; ask for review before `task.py start`.
../../.trellis/workflow.md:209:Lightweight: `prd.md` can be enough. Complex: finish `prd.md`, `design.md`, and `implement.md`; ask for review before `task.py start`.
../../.trellis/workflow.md:225:Sub-agent dispatch protocol applies to all platforms and all sub-agents, including class-2 Codex/Gemini/Qoder/Copilot/ZCode/Reasonix/Trae and `trellis-research`: every dispatch prompt starts with `Active task: <task path from task.py current>` before role-specific instructions.
../../.trellis/workflow.md:231:Dispatch prompt starts with `Active task: <task path from task.py current>`. Read context: jsonl entries -> `prd.md` -> `design.md if present` -> `implement.md if present`.
../../.trellis/workflow.md:254:     Currently DEAD in normal flow: cmd_archive writes status='completed' in
../../.trellis/workflow.md:255:     the same call that moves the task dir to archive/, so the active-task
../../.trellis/workflow.md:273:### Active Task Routing
../../.trellis/workflow.md:275:When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.
../../.trellis/workflow.md:295:- Task creation approval is not implementation approval; implementation waits for `task.py start` after artifact review.
../../.trellis/workflow.md:328:Run only `create` here — do not also run `start`. `start` flips status to `in_progress`, which switches the breadcrumb to the implementation phase before planning artifacts are reviewed. Save `start` for step 1.4.
../../.trellis/workflow.md:330:Skip when `python3 ./.trellis/scripts/task.py current --source` already points to a task.
../../.trellis/workflow.md:334:Load the `trellis-brainstorm` skill and explore requirements interactively with the user per the skill's guidance.
../../.trellis/workflow.md:347:- Parent tasks own source requirements, child-task mapping, cross-child acceptance criteria, and final integration review.
../../.trellis/workflow.md:370:Do the research in the main session directly and write findings into `{TASK_DIR}/research/`. (For `codex-inline` this avoids the `fork_turns="none"` isolation that prevents `trellis-research` sub-agents from resolving the active task path.)
../../.trellis/workflow.md:440:After artifact review, flip the task status to `in_progress`:
../../.trellis/workflow.md:446:For lightweight tasks, `prd.md` can be enough. For complex tasks, `prd.md`, `design.md`, and `implement.md` must exist and be reviewed before start. On sub-agent-dispatch platforms, `implement.jsonl` and `check.jsonl` must both have real curated entries before start. Runtime consumers tolerate missing or seed-only manifests for compatibility, but that tolerance is not a planning-ready state.
../../.trellis/workflow.md:473:Goal: turn reviewed planning artifacts into code that passes quality checks.
../../.trellis/workflow.md:482:- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running project lint and type-check
../../.trellis/workflow.md:496:- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running project lint and type-check
../../.trellis/workflow.md:497:- **Dispatch prompt guard**: The prompt MUST start with `Active task: <task path>`, then explicitly say the spawned agent is already `trellis-implement` and must implement directly without spawning another `trellis-implement` / `trellis-check`.
../../.trellis/workflow.md:500:- Resolves the active task with `task.py current --source`, then reads `prd.md`, `design.md` if present, and `implement.md` if present
../../.trellis/workflow.md:510:- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running project lint and type-check
../../.trellis/workflow.md:524:4. Implement the code per reviewed artifacts
../../.trellis/workflow.md:536:- **Task description**: Review all code changes against specs and task artifacts; fix any findings directly; ensure lint and type-check pass
../../.trellis/workflow.md:537:- **Dispatch prompt guard**: Tell the spawned agent it is already the `trellis-check` sub-agent and must review/fix directly, not spawn another `trellis-check` / `trellis-implement`.
../../.trellis/workflow.md:540:- Review code changes against specs
../../.trellis/workflow.md:541:- Review code changes against `prd.md`, `design.md` if present, and `implement.md` if present
../../.trellis/workflow.md:583:Load the `trellis-update-spec` skill and review whether this task produced new knowledge worth recording:
../../.trellis/workflow.md:651:- Trellis is the sole project-local task lifecycle authority. Global helpers may select a planning method or execution backend, but must not duplicate task weight, phase, active-task, or archive state.
../../.trellis/workflow.md:653:- Native / Architect / Council are planning methods inside the current Trellis task, not parallel lifecycles.
../../.trellis/workflow.md:656:- Mission-linked tasks use `execution.md` only for static artifact references. Mission CSV remains the only live issue-state authority.
../../.trellis/workflow.md:657:- Mission REVIEW closes only its execution child; it does not complete a research parent. Trellis lifecycle closure still requires explicit user acceptance.
../../.trellis/workflow.md:671:- No active task must triage first and ask for task-creation consent before creating a Trellis task.
../../.trellis/workflow.md:679:| No active task (before Phase 1) | `[workflow-state:no_task]` (after the Phase Index ASCII art) |
../../.trellis/workflow.md:684:| After Phase 3.5 (archived) | `[workflow-state:completed]` (after Phase 3 summary; **currently DEAD**) |
../../.trellis/workflow.md:701:- STATUS charset: `[A-Za-z0-9_-]+` (underscores and hyphens allowed, e.g. `in-review`, `blocked-by-team`)
../../.trellis/workflow.md:719:Supported events: `after_create / after_start / after_finish / after_archive`. Note that `after_finish` ≠ a status change (it only clears the active-task pointer); use `after_archive` for "task is done" notifications.
../../AGENTS.md:11:- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)
../../AGENTS.md:28:- 主会话负责一次性加载 Trellis 生命周期、当前任务及服务器规则。子代理不重复运行 trellis-start、get_context.py、task.py current，不重新分类或创建任务。
../../STATE.md:55:- 当前骨架：[叙事骨架 v1.4.2（11-19 可辨识度准则版 + 措辞修正）](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)（Prop 1–3 证明 v2 已完成：Astra 撰写，Claude 与 agy 独立核查，修订后复核通过，剩 2(d) 单帧一处已声明的缺口；11-20 已编译 12 页，含秩注记；[证明与核查](.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/review-divergence-20261119.md)）；[4 篇 2026 预印本源码核对](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)。论文定位与科学验收待 Eric 定。
../../STATE.md:67:1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
../../STATE.md:113:11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。
.
..
.DS_Store
.backup-2026-09-08T12-56-43
.backup-2026-09-08T12-56-59
.developer
.gitignore
.runtime
.template-hashes.json
.version
agents
config.yaml
research-project-scaffold.json
research-project.json
scripts
spec
tasks
workflow.md
workspace

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "cat ../../AGENTS.md; sed -n '1,34p' ../../STATE.md; ls ../../.trellis/tasks; sed -n '1,100p' stageA.py; sed -n '1,95p' stageA3.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

- 流程从简：只做必要检查，避免重复审查和过度文档化，尽快执行并汇报结果；服务器规则照常严格遵守。
- 记录去处（结果、线索、预测、待办写在哪）以项目 `CLAUDE.md` 的"记录系统"表为准；Codex 同样遵守，不另建记录文件。

## 子代理使用与上下文复用（2026-10-28 更新）

- 主会话负责一次性加载 Trellis 生命周期、当前任务及服务器规则。子代理不重复运行 trellis-start、get_context.py、task.py current，不重新分类或创建任务。
- 每次分派提供紧凑交接：任务/CSV 路径、子任务目标、文件所有权、验收条件、必需约束与待读文件。已注入内容不再读一遍；缺少具体约束时只补读对应文件或向主会话索取。
- 同一子代理优先复用；follow-up 只发送变化、证据与下一步，子代理保留已读上下文。新代理仍须获得必要代码规范和科学/服务器安全边界，不把未读取的内容谎报为已加载。
- 是否委派及模型选择遵循全局 Personal Agent Rules（唯一来源：`~/projects/personal-ai-workflow/templates/personal/personal-rules.md`）：默认主会话推进，Trellis 的实现与独立检查也按需委派，拿不准先问 Eric；确需 Codex 子代理时默认用 GPT-6.1 Sol。已有代理按当前工作收尾，保留前任代码、结果、审计记录；不因换模型重新仿真。

## GitHub 只读镜像（2026-10-13）

- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `trans/tcom-main` 已提交的本目录，排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 按需同步：仅当用户明确说「推 GitHub / 同步镜像」时，先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得主动推送，不得把 vault 本身推到该仓库。
# STATE — AFDM-channel-estimation

> Project ID: `afdm-e2e-main`
>
> Title: AFDM Deep-Unfolded Joint Channel Estimation and Detection（历史项目名；论文标题禁用 learned/neural，见下方决定 1）
>
> Lifecycle stage: `contribution framing`（阶段 5：定贡献框架，尚未进入正式写论文阶段）
>
> 当前根：research-assets/index.md 中已接受的结果卡，加本文件“待办与开放线索”。目标期刊沿用已登记的 TCOM；paper/、fyp_new_short/、paper-tmlcn/ 是已结束阶段的旧稿，不带入新论文。开放线索不因登记而成为已接受结果。
>
> 2026-11-18 之前的完整记录逐字保存在 [STATE-history.md](STATE-history.md)（只读）。

## ▶ 接续入口（2026-11-22 更新；新会话先读这里）
- **11-22 Eric 确认（经白话剥壳后）：接收机幻影 / 协方差主线降级**（骨架 v1.4.2、`CODELAY` 与 Γ = 0 等效那条线）：不再是唯一推进线，但不锁死——现稿路线（11-20 定）与已接受卡照旧保留，随时可回来写。
- 当前重心：用 [idea 漏斗](ideas/FUNNEL.md) 找原理级、够 Trans 的新问题（[看板](ideas/BOARD.md)）；`11-21-data-pilot-fer`（低导频）状态不变。下面两条是 11-20 交接时的快照。
- **先读[交接笔记](.trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md)**：Eric 想要什么（三条主线 + "大一统、妙的 idea"）、我们在追什么（"免费得到的预言"）、已试候选与结果、待他决定的 5 件事。
- 11-20 一句话（已被上面 11-22 两条取代）：原理主线已立（骨架 v1.4.2，前瞻检验支持）；"妙"还没拿到——交换预算预言成立但只是系统层规则（res-19-08），网格 η 预言失败（res-19-09）；写作任务未建。新会话先按交接笔记 §4 的建议顺序问 Eric：先建写作任务，还是先继续挖"妙"（挖哪一条）。
- 11-20 16-QAM 线三方评估后 **Eric 定：对本文关闭**（[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/16qam-line-divergence-20261120.md)）；σ² 判决导向"改符号"已零成本否定（负面台账）。
  待选候选：a₁ ∈ {0,1,5} chirp 临界检验（agy）、反相双径外移律（[Astra xhigh](.trellis/tasks/09-22-tf-production-gap-audit/research/miao-astra-scientist-20261120.md)，计数未复算）；Fable 第 1 轮押"自洽类定律"（`miao-fable-20261120.md`），第 2 轮（自定义"妙"）进行中。
- 11-20 Fable 预言前瞻应验：交换中删去 Γ（Γ = 0）幻影率与 CODELAY 同为 1.84%、救回等效，冻结判定 P-A SUPPORTED / P-B EQUIVALENT（[res-20261120-01](research-assets/res-20261120-01.md)，draft）。
  待 Eric 定：贡献框架是否从"需要精确同延块"改为"自洽性准则"（E-1 解读与骨架第 4 句的更正提议见卡片末节）。
- 11-20 MIXED8（真双径）：Γ = 0 无幻影、双径占位等效，FER 等效未成立（+1.00 pp，INCONCLUSIVE），[res-20261120-02](research-assets/res-20261120-02.md)（draft）；文献检查：分数 Doppler 支撑搜索里无人用对角模型（[lit](.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md)）。
- 11-20 MIXED8 重复检验（2,400 新帧）：Γ = 0 的 FER 与 CODELAY 在 ±1.5 pp 内等效，但 CODELAY 保留真近距双径更好（−1.54 pp），[res-20261120-03](research-assets/res-20261120-03.md)（draft）。三腿合起来待 Eric 定贡献框架。
- 11-20 **Eric 定论文路线**（采纳 Astra 版）：现稿以"译码失败后继续迭代还是重搜、各需多少时间"为中心，协方差陷阱降为一节，撤"精确协方差不可替代"；原目标另给两周只看低导频漏径（[分歧表与决定](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261120/divergence.md)）。依据：kill-argument（[报告](.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/KILL_ARGUMENT.md)）、L1 查新（[Gemini](.trellis/tasks/11-20-gamma0-exchange/research/novelty-gemini-20261120.md)：已知部件的新组合）、四份根因分析与 Astra 两步评估。
- 11-24 Huang-2010 式两遍全局重找径对照（冻结 `4772365c`，帧 5400–5799）：`HG_AHEAD`——两遍全局 OMP 最优 4.45 dB（ρ = .20）比局部交换 CD 最优 5.10（ρ = .30）好 0.65 [0.19, 0.97] dB，粗字典版耗时仅 1.07×；Γ = 0 与 CD 等效（+0.05）。现稿"局部交换胜过全局重找"不成立；CD 未给两遍外环（不对称未测）。路线待 Eric 定（[读数](experiments/huang_steelman_20261124/READOUT.md)；[路线分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/route-after-huang-divergence-20261124.md)：两方都否定现稿主张，Neon 默认写诚实系统论文，Claude 先做同帧检验再定）。
- 11-25 同帧检验（冻结 `918a24747`，10.9 核时）：**更正上一条**——轮数对齐后两遍 CD 追平 HG（−0.12 [−0.55, +0.08]，`CATCHES_UP`；换 8 条版 −0.19 [−0.58, −0.01]），"局部交换不如全局重找"不成立，HG 的 0.65 dB 来自多一轮；耗时未测。低导频帧上 HG 之后第 0 轮多普勒余量 0.73 [0.45, 1.04] dB（0.08 bin 口径，`INCONCLUSIVE`，下界差 0.05 未过 0.5），0.04 bin 口径 1.12 dB；对两遍 CD 的余量未测（[读数](experiments/sameframe_hg_20261124/READOUT.md)）。
- 11-25 两遍 CD 同帧复核（冻结 `e3bf93f64`，3.25 核时）：低导频帧上 CD2 最优 4.42 dB（ρ = .20）≈ 真时延上限、好于 HG 0.16 dB；之后第 0 轮多普勒余量 0.58 [0.32, 0.84] dB（0.08 bin，`INCONCLUSIVE`），0.04 bin 口径 0.96 dB。静默计时 ρ = .20：CD2 每次触发均值 189 ms，HG 640 ms（3.4×），粗字典 HGint 199 ms（[读数](experiments/sameframe_cd2_20261125/READOUT.md)）。
- 11-20 低导频漏径线**按停止条件 3 停**（Eric 选零成本探针后停；11-20 验收归档）：ρ = .15 的 CD4 失败帧残留弱径（中位 0.19σ²）、多搜找回 0/19；ρ = .30 失败帧不缺路径（0.012σ²），syndrome 已能预测（AUC .81）。[第一步读数](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/step1-readout-20261120.md)、[探针](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/visible-probe-readout-20261120.md)；台账已记，任务待 Eric 验收归档。
- 11-20 候选一（"有反馈时导频只管捕获"）第 0 步计算**未通过**冻结判读：首轮单次匹配滤波下 ZC 导频旁瓣主导弱径检测（80%），预言了不存在的崩塌；**Eric 11-21 停**，已记否定台账（[读数](experiments/pilot_acquisition_calc_20261120/READOUT.md)）。
- 11-20 外部候选三（Stein 闭合估噪）零成本读数：合并判据**成立**（σ̂²/σ² 中位 0.94），但偏差随 SNR 从 0.78 升到 2.66，只在 5.0–5.5 dB 校准；能否收回 1.64 dB 需端到端检验，待 Eric 定（[读数](experiments/stein_sigma2_readout_20261120/READOUT.md)）。
- 11-21 Stein 估噪端到端（冻结）：穿越点 5.46 dB，对已知 σ² 差 +0.31 [0.17, 0.48]（P1 不确定），好于 SF 0.93 [0.65, 1.39]（P2 BETTER），收回 DD 损失约 81%；Eric 11-21：暂不成卡，任务归档，结果留作论文"未知噪声"一节的备选（[读数](experiments/sigma2_stein_20261121/READOUT.md)）。
- 11-21 外部候选"数据当导频"（接收信号延迟–多普勒自相关找径）真实设定零接收机检验（Astra 审后冻结）：ρ = .15 有效弱径捕获 .948，补回导频漏掉的 .919，独立数据对照只有 .042，R1/R2/R3 全过；只证"看得见"，FER 是否移动与新意未检验（[读数](experiments/data_autocorr_acq_20261121/READOUT.md)）。
- 11-21 "数据当导频"查新（Gemini，两步）：(a) 数据二阶统计辨识时变信道、(b) 径对在差分时延–多普勒处恢复多径均**已被做过**（Tsatsanis–Giannakis、Cordes 闪烁弧、Ranieri 稀疏相位恢复、AFDM 上的 Ranasinghe 2407.05328 多帧协方差）；(c) 机制已有、新场景；只剩 (d) 单帧 + 编码 SP-AFDM 降导频交叉点为候选新意，端到端未证。Claude 抽查 2 篇：Ranasinghe 属实（但"T = 1 很差"原文未写），Cordes 差分时延–多普勒属实（全息表述待核 PDF）（[查新](experiments/data_autocorr_acq_20261121/novelty-gemini.md)）。
- 11-21 "数据当导频"第二步（去掉真锚、用导频消镜像，冻结）：R4/R5 全过，ρ = .15 锚正确 1.000，导频漏掉的弱径找回 .832；ρ = .05 第 0 轮覆盖从 .563 提到 .883。下一步只剩改接收机看 FER（决定性检验，待 Eric 定）（[读数](experiments/data_autocorr_acq_20261121/READOUT2.md)）。
00-bootstrap-guidelines
07-26-e1-ldpc-coded-ber
07-26-e2-firm-seed-baselines
07-26-e6-lambda-cost-dump
07-26-tmlcn-paper-submission
08-30-claim-audit-archive
09-05-budgeted-support-repair
09-05-contract-and-baseline
09-06-bottleneck-diagnostics
09-06-minimal-repair-mechanism
09-12-i1-bottleneck-pilot
09-12-i1-light-gap-closure
09-13-trans-next
09-21-sp-afdm-frozen-evidence
09-21-sp-afdm-native-joint
09-22-tf-production-gap-audit
10-02-afdm-algebraic-decoupling
10-02-inference-causal-defects
10-04-shared-channel-followup
10-05-method-advantage
10-08-doppler-cluster
10-08-headroom-ladder
10-17-offgrid-sbl-e3b
10-18-gamma-support-only
10-18-model-matched-gamma
10-18-shrink-vs-misspec-e3c
10-18-split-principle-prospective
10-19-generator-snr-audit
10-19-rank-inversion-posthoc
10-19-slot-mismatch
10-20-sbl-freeze-replay
11-14-entropy-step1
11-14-entropy-step2-p3-close
11-18-admission-law-test
11-18-codelay-sbl-stage3
11-18-ratio-sweep
11-18-sbl-split-diagnostic
11-18-sigma2-dd
11-19-doublet-conflict-check
11-19-edit-budget-lowrho
11-19-gate-sbl-test
11-19-gate-screen
11-19-grid-eta-dual
11-19-readout-batch
11-19-rho-sweep
11-19-sbl-residual-gap
11-19-sbl-spectral-split
11-19-unified-cov-prospective
11-20-gamma0-exchange
11-20-paper-iterate-or-research
11-21-data-pilot-fer
11-22-matched-ldpc-kill-test
archive
"""Stage A (STAGEA_PROTOCOL.md): does a true-delay round-0 support let low pilot fractions beat the best baseline?

Arms per key (same observation): base = F0 + CODELAY exchange (rho-sweep pipeline); delay = the same with the round-0
support replaced by the 8 true delays (Doppler centers observable: best pilot-MF integer column at each delay).
Injection replaces ctx.native.pilot_front only for the 'delay' F0 call; everything downstream is unchanged.
Reuses unified_cov_prospective_20261119/cstate.py (context, stage3 inputs/observed/e1.f0_state/e1.run_branch).

  python stageA.py gate  --out out/stageA_gate.json
  python stageA.py run   --out out/stageA                 (rows + STATUS)
  python stageA.py read  --out out/stageA                 (frozen readout -> results.json)
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / 'unified_cov_prospective_20261119'))
sys.path.insert(0, str(EXP / 'sp_afdm_frozen_20260920' / 'src'))

FRAMES = range(41000, 41400)
SCENARIOS = ('U', 'G')
RHOS = (50, 100, 150, 200, 250, 300)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
ARMS = ('base', 'delay')
FRAMES_PER_SHARD = 5
WORKERS = 32
TAU = 0.2
BOOT, SEED, GATE_DB = 2000, 20261121, 0.3
_C = None


def setup():
    global _C
    if _C is None:
        import cstate
        from physical import regressors
        ctx, full, cd, _ = cstate.context()
        s = ctx.system; lmax = int(s.l_max_cap)
        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
        _C = dict(stage3=cstate.stage3, ctx=ctx, cd=cd, U=U / np.linalg.norm(U, axis=0, keepdims=True),
                  lmax=lmax, orig_front=ctx.native.pilot_front)
    return _C


def f0(C, obs, inject=None):
    """F0 with an optional round-0 support override; the native module's pilot_front is restored afterwards."""
    ctx, orig = C['ctx'], C['orig_front']
    if inject is None:
        return C['stage3'].e1.f0_state(ctx, obs)

    def front(observed, system, code):
        s = orig(observed, system, code)
        ls, ks, gs = inject
        gs = np.ones(len(ls), complex) if gs is None else np.asarray(gs, complex)
        return dict(s, delays=np.asarray(ls, int), dopplers=np.asarray(ks, float), gains=gs)
    ctx.native.pilot_front = front
    try:
        return C['stage3'].e1.f0_state(ctx, obs)
    finally:
        ctx.native.pilot_front = orig


def support_stats(delays, dopplers, truth, sigma2):
    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.abs(np.asarray(truth['g_i'])) ** 2
    rel = g >= TAU * sigma2
    have = set(int(d) for d in delays)
    miss = float(sum(g[i] for i in range(len(l)) if rel[i] and l[i] not in have))
    err, wsum = 0.0, 0.0
    for i in range(len(l)):
        if l[i] in have:
            cand = [float(dopplers[k]) for k, d in enumerate(delays) if int(d) == l[i]]
            err += g[i] * min(abs(c - nu[i]) for c in cand); wsum += g[i]
    return dict(missing_power=miss, doppler_err=err / wsum if wsum else None,
                support_right=bool(all(l[i] in have for i in range(len(l)) if rel[i])))


def one_arm(C, obs, truth, inject):
    ctx, stage3 = C['ctx'], C['stage3']
    dec, arrays, syndrome, _ = f0(C, obs, inject)
    s2 = float(obs['sigma2'])
    rec = dict(syndrome=int(syndrome),
               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    if syndrome:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    else:
        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    return rec


def genie_inject(C, obs, truth):
    z5 = (np.abs(C['U'].conj().T @ obs['y']) ** 2).reshape(C['lmax'] + 1, 5)
    ls = [int(d) for d in truth['l_i']]
"""Stage A3 (STAGEA3_PROTOCOL.md): Doppler-error tolerance of the round-0 channel.  Round 0 gets the true delays and
true Doppler plus Gaussian error sigma * z (z ~ N(0,1) per path, fixed per frame and scenario, shared across sigma,
rho and SNR); gains are the pilot LS solution of time_refine at those values (stage A2 'ldop' with perturbed Doppler).
one_arm is stageA2.one_arm with the truth passed to f0_true replaced by the perturbed one (stageA2.one_arm scores
against the truth it injects, so it cannot be called directly).

  python stageA3.py gate --out out/stageA3_gate.json   (needs out/stageA2 rows)
  python stageA3.py run  --out out/stageA3
  python stageA3.py read --out out/stageA3             (needs out/stageA and out/stageA2 rows)
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

import stageA, stageA2
from stageA import FRAMES, SCENARIOS, setup, support_stats
from stageA2 import f0_true, crossing, load

RHOS = (100, 150, 200)
SNRS = stageA2.SNRS
SIGMAS = (25, 50, 100, 200)                      # Doppler error std in 1/1000 bin
ARMS = tuple(f's{s:03d}' for s in SIGMAS)
FRAMES_PER_SHARD, WORKERS = 5, 32
BOOT, SEED = 2000, 20261121


def z_paths(frame, s_, n):
    return np.random.default_rng([SEED, frame, SCENARIOS.index(s_)]).standard_normal(n)


def one_arm(C, obs, truth, sigma, z):
    ctx, stage3 = C['ctx'], C['stage3']
    pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + sigma / 1000 * z).tolist())
    dec, arrays, syndrome, _ = f0_true(C, obs, pert, 'ls')
    s2 = float(obs['sigma2'])
    rec = dict(syndrome=int(syndrome),
               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    if syndrome:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    else:
        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    return rec


def run_key(C, base, s_, rho, snr, frame, sigmas=SIGMAS):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    z = z_paths(frame, s_, len(truth['l_i']))
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
                arms={f's{s:03d}': one_arm(C, obs, truth, s, z) for s in sigmas})


def shard_job(job):
    idx, frames, out = job
    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
    with open(path, 'x') as fh:
        for frame in frames:
            for s_ in SCENARIOS:
                for rho in RHOS:
                    base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
                    for snr in SNRS:
                        print(json.dumps(run_key(C, base, s_, rho, snr, frame)), file=fh); n += 1
    os.system(f'gzip -n {path}')
    return idx, n


def gate(out):
    """G1: sigma = 0 reproduces the stage A2 'ldop' rows (syndrome, F0 errors, final errors).
    G2: for sigma = .05 bin, round 0 carries the true delays and exactly k_real + .05 z, with z fixed across rho/SNR."""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    rows = {}
    with gzip.open(Path(out).parent / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt') as fh:
        for line in fh:
            r = json.loads(line); rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    keys = [k for k in rows if k[1] in (100, 200) and k[2] in (400, 600)][:8]
    res = []
    for s_, rho, snr, frame in keys:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        z = z_paths(frame, s_, len(truth['l_i']))
        rec = one_arm(C, obs, truth, 0, z); a = rows[(s_, rho, snr, frame)]['arms']['ldop']
        reproduce = all(rec[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors'))
        pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + .05 * z).tolist())
        _, arr, _, _ = f0_true(C, obs, pert, 'ls')
        l = list(np.asarray(truth['l_i'], int)); order = [l.index(d) for d in arr['r0_delays']]
        exact = (sorted(arr['r0_delays'].tolist()) == sorted(l)
                 and np.allclose(arr['r0_dopplers'], (np.asarray(truth['k_real']) + .05 * z)[order]))
        res.append(dict(key=[s_, rho, snr, frame], reproduce=bool(reproduce), r0_exact=bool(exact)))
    t = time.process_time(); base = stage3.inputs(ctx, 41399, 'G', 100)
    for snr in (400, 600):

exec
/bin/zsh -lc "nl -ba stageA5.py | sed -n '785,875p'; ls -lah out/stageA4/ out/stageA3/; rg -n 'a662fa|MD5|rho|30%' STAGEA4_READOUT.md ../huang_steelman_20261124/hs_arms.py; rg -n 'def (inputs|observed)|choice\\(|def simulate' ../*/*.py ../../src -g '*.py' | rg 'stage3|physical\\.py' | head -60" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   785	
   786	    crb_table: dict[str, dict[str, float]] = {}
   787	    for bi, bname in enumerate(a4_bounds):
   788	        crb_table[bname] = {
   789	            f'{rho}_{snr}': float(B[bi, ri, si].mean())
   790	            for ri, rho in enumerate(RHOS) for si, snr in enumerate(snrs)
   791	        }
   792	
   793	    efficiency: dict[str, Any] = {}
   794	    for ri, rho in enumerate(RHOS):
   795	        key4 = f'{rho}_{DECIDE_SNR}'
   796	        sb_m = table['SB'][key4]['mean']
   797	        sb_c = crb_table['semiblind'][key4]
   798	        pw_m = table['PW'][key4]['mean']
   799	        pw_c = crb_table['pilot_white'][key4]
   800	        kd_m = table['KD'][key4]['mean']
   801	        kd_c = crb_table['known'][key4]
   802	        efficiency[str(rho)] = dict(
   803	            sb_over_sb_crb=float(sb_m / sb_c),
   804	            pw_over_pilot_white_crb=float(pw_m / pw_c),
   805	            kd_over_known_crb=float(kd_m / kd_c),
   806	            pw_4db_mean=pw_m,
   807	            stageA_actual_pilot_4_5db=float(a3_actual_pilot[str(rho)]),
   808	            pw_over_stageA_actual=float(pw_m / float(a3_actual_pilot[str(rho)])),
   809	        )
   810	
   811	    return dict(
   812	        draws=n_draws,
   813	        snrs=list(snrs),
   814	        boot_draws=boot_draws,
   815	        boot_seed=boot_seed,
   816	        primary=dict(
   817	            E_point=E_pt,
   818	            E_ci95=[E_lo, E_hi],
   819	            best_rho=E_rho,
   820	            threshold=PASS_THRESH,
   821	            verdict=verdict,
   822	        ),
   823	        table=table,
   824	        crb_mean=crb_table,
   825	        efficiency_4db=efficiency,
   826	    )
   827	
   828	
   829	def render_results_md(res: dict[str, Any]) -> str:
   830	    a = res['analysis']
   831	    p = a['primary']
   832	    lines = [
   833	        '# Stage A5 Results: Semi-Blind Round-0 Doppler Proxy Check',
   834	        '',
   835	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
   836	        f'- Draws: **{a["draws"]}** (frames `41000–41099` × U/G), SNRs: `{a["snrs"]}`',
   837	        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 6.0 h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
   838	        '',
   839	        '## Primary Verdict (Pre-Registered, SNR = 4 dB)',
   840	        '',
   841	        f'- `E = min_{{ρ ∈ {{0.10, 0.15}}}} mean(SB)` = **{p["E_point"]:.4f} bin** (at ρ={p["best_rho"]/1000:.2f}), '
   842	        f'95% CI **[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] bin** → **{p["verdict"]}** (threshold `0.08` bin)',
   843	        '',
   844	        '## 4 dB Summary Table (Power-Weighted Capped MAE, bin; 200 Draws)',
   845	        '',
   846	        '| ρ | PW mean [med] | SB mean [med] (95% CI) | KD mean [med] | SB-CRB | PW-CRB | SB Eff | PW Eff | SB Outlier >0.25 | Stage A Actual (4–5 dB) |',
   847	        '|---:|---|---|---|---:|---:|---:|---:|---:|---:|',
   848	    ]
   849	    for rho in RHOS:
   850	        k4 = f'{rho}_400'
   851	        pw = a['table']['PW'][k4]
   852	        sb = a['table']['SB'][k4]
   853	        kd = a['table']['KD'][k4]
   854	        eff = a['efficiency_4db'][str(rho)]
   855	        lines.append(
   856	            f'| {rho/1000:.2f} | {pw["mean"]:.4f} [{pw["median"]:.4f}] | '
   857	            f'**{sb["mean"]:.4f}** [{sb["median"]:.4f}] ([{sb["ci95"][0]:.4f}, {sb["ci95"][1]:.4f}]) | '
   858	            f'{kd["mean"]:.4f} [{kd["median"]:.4f}] | '
   859	            f'{a["crb_mean"]["semiblind"][k4]:.4f} | {a["crb_mean"]["pilot_white"][k4]:.4f} | '
   860	            f'{eff["sb_over_sb_crb"]:.2f}× | {eff["pw_over_pilot_white_crb"]:.2f}× | '
   861	            f'{100*sb["outlier_gt_0p25_frac"]:.2f}% | {eff["stageA_actual_pilot_4_5db"]:.4f} |'
   862	        )
   863	    return '\n'.join(lines) + '\n'
   864	
   865	
   866	def cmd_run(args):
   867	    print(sys.executable, flush=True)
   868	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   869	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   870	    ar.check_thread_env()
   871	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   872	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   873	    if not 1 <= args.workers <= 32:
   874	        raise ValueError('workers must be in 1..32')
   875	
out/stageA3/:
total 80
drwxr-xr-x@  7 guoyikun  staff   224B Nov 21 13:43 .
drwxr-xr-x@ 13 guoyikun  staff   416B Nov 25 01:40 ..
-rw-r--r--@  1 guoyikun  staff   4.5K Nov 21 13:43 REMOTE_ROWS_MD5.txt
-rw-r--r--@  1 guoyikun  staff   415B Nov 21 13:43 RUN_CONFIG.json
-rw-r--r--@  1 guoyikun  staff    16B Nov 21 13:43 STATUS
-rw-r--r--@  1 guoyikun  staff   1.9K Nov 21 13:43 results.json
-rw-r--r--@  1 guoyikun  staff    18K Nov 21 13:43 run.log

out/stageA4/:
total 88
drwxr-xr-x@  7 guoyikun  staff   224B Nov 21 14:07 .
drwxr-xr-x@ 13 guoyikun  staff   416B Nov 25 01:40 ..
-rw-r--r--@  1 guoyikun  staff    48B Nov 21 14:07 REMOTE_ROWS_MD5.txt
-rw-r--r--@  1 guoyikun  staff   308B Nov 21 14:06 RUN_CONFIG.json
-rw-r--r--@  1 guoyikun  staff    17B Nov 21 14:06 STATUS
-rw-r--r--@  1 guoyikun  staff   6.4K Nov 21 14:06 results.json
-rw-r--r--@  1 guoyikun  staff    22K Nov 21 14:06 run.log
STAGEA4_READOUT.md:3:协议 [STAGEA4_PROTOCOL.md](STAGEA4_PROTOCOL.md)（`c3548de9`，运行前提交）；结果 `out/stageA4/results.json`；1.7 核时（门槛外推 0.6，低估是因为 spawn 进程各自加载上下文），墙钟 200 s。行文件 `rows.jsonl.gz`（653 KB）留在远程 `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/out/stageA4/`，md5 `a662fa94be8f76a960a3f43413c95973`。
../huang_steelman_20261124/hs_arms.py:21:RHO_SWEEP = EXPERIMENTS / 'rho_sweep_20261119'
../huang_steelman_20261124/hs_arms.py:23:RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
../huang_steelman_20261124/hs_arms.py:24:RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'
../huang_steelman_20261124/hs_arms.py:32:KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
../huang_steelman_20261124/hs_arms.py:48:FROZEN_EXTRA_MD5 = {
../huang_steelman_20261124/hs_arms.py:154:    for rel, expected in FROZEN_EXTRA_MD5.items():
../huang_steelman_20261124/hs_arms.py:157:            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
../huang_steelman_20261124/hs_arms.py:170:    """Verify frozen MD5s BEFORE importing, then load Stage 3 context + zero_variance wrapper."""
../huang_steelman_20261124/hs_arms.py:360:    pd = 1.0 - system.rho  # 0.5 in normalized observe() convention
../huang_steelman_20261124/hs_arms.py:506:    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))
../huang_steelman_20261124/hs_arms.py:509:def load_archived_rho_sweep(
../huang_steelman_20261124/hs_arms.py:511:    md5_manifest: Path = RHO_ARCHIVE_MD5,
../huang_steelman_20261124/hs_arms.py:513:    """Pin manifest SHA-256, verify all 24 shard MD5s, validate 62,400 keys, 18,009 triggers, and invariants."""
../huang_steelman_20261124/hs_arms.py:515:    if manifest_sha != RHO_ARCHIVE_MD5_SHA256:
../huang_steelman_20261124/hs_arms.py:516:        raise RuntimeError(f'Archive manifest SHA-256 mismatch: {manifest_sha} != {RHO_ARCHIVE_MD5_SHA256}')
../huang_steelman_20261124/hs_arms.py:536:            raise RuntimeError(f'Archived shard MD5 mismatch for {name}: {actual} != {exp}')
../huang_steelman_20261124/hs_arms.py:557:        (s, rho, snr, frame)
../huang_steelman_20261124/hs_arms.py:558:        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
rg: ../../src: No such file or directory (os error 2)
../cstate_codelay_sbl_stage3_20261118/run.py:69:def inputs(ctx, frame, scenario, rho):
../cstate_codelay_sbl_stage3_20261118/run.py:74:def observed(ctx, base, rho, snr):
../cstate_codelay_sbl_stage3_20261118/run.py:149:            def choice(trace):
../cstate_codelay_sbl_stage3_20261118/run.py:152:            assert choice(got) == choice(ref), (field, choice(got), choice(ref))

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba ../cstate_codelay_sbl_stage3_20261118/run.py | sed -n '35,100p'; rg -n 'def (raw|sample|_sample|draw|generate)|replace=False|standard_normal|rng.*choice' ../sp_afdm_frozen_20260920/src/physical.py ../cstate_codelay_sbl_stage3_20261118 -g '*.py' | head -50; sed -n '110,169p' ../huang_steelman_20261124/hs_arms.py; rg -n 'deinlab|/dev/shm' ../../CLAUDE.md ../../.trellis/spec -g '*.md' | head -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
    35	
    36	
    37	def write_json(path, value):
    38	    with path.open('x') as handle:
    39	        json.dump(value, handle, indent=2, allow_nan=False)
    40	        handle.write('\n')
    41	
    42	
    43	def read_rows(path):
    44	    with path.open() as handle:
    45	        for line in handle:
    46	            yield json.loads(line)
    47	
    48	
    49	def context():
    50	    ctx = e1.p1ctx.load()
    51	    checked = e1.check_frozen_md5(ctx)
    52	    if any(r['status'] != 'ok' for r in checked.values()):
    53	        raise AssertionError('E-1 source inventory did not pass')
    54	    if {name: ctx.source_md5[name] for name in P1_MD5} != P1_MD5:
    55	        raise AssertionError('P1 imports differ from the historical SBL archives')
    56	    full = e1.load_variant()
    57	    route = codelay.load(full)
    58	    return ctx, full, route, checked
    59	
    60	
    61	def key_of(row):
    62	    return tuple(row[field] for field in e1.KEY_FIELDS)
    63	
    64	
    65	def main_keys():
    66	    return {(s, rho, snr, frame) for frame in MAIN_FRAMES for s, rho in CELLS for snr in GRID[rho]}
    67	
    68	
    69	def inputs(ctx, frame, scenario, rho):
    70	    raw, diag = e1.p1ctx.base(ctx, scenario, rho/1000, frame)
    71	    return raw, diag
    72	
    73	
    74	def observed(ctx, base, rho, snr):
    75	    raw, obs, truth = e1.gd.observe(ctx, *base, rho/1000, snr)
    76	    return raw, obs, truth
    77	
    78	
    79	def digest(a):
    80	    a = np.asarray(a)
    81	    h = hashlib.sha256()
    82	    h.update(str(a.dtype).encode())
    83	    h.update(repr(a.shape).encode())
    84	    h.update(np.ascontiguousarray(a).tobytes())
    85	    return h.hexdigest()
    86	
    87	
    88	def truth_record(obs, truth):
    89	    return dict(sigma2=float(obs['sigma2']), delays=truth['l_i'].tolist(),
    90	                dopplers=truth['k_real'].tolist(),
    91	                gains=[[float(g.real), float(g.imag)] for g in truth['g_i']])
    92	
    93	
    94	def decoded(ctx, output, truth):
    95	    bits = output['decoded']
    96	    errors = e1.gd.score(ctx, bits, truth)
    97	    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))
    98	
    99	
   100	def arm(ctx, kernel, obs, truth, arrays, syndrome, f0):
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def own_md5() -> dict[str, str]:
    out = {}
    for name in OWN_SOURCE_FILES:
        p = HERE / name
        if not p.is_file():
            raise FileNotFoundError(f'Missing own experiment file: {p}')
        out[name] = md5_file(p)
    return out


def atomic_write_text(path: Path, text: str):
    """Write via temporary .part file + fsync + atomic os.replace."""
    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
    with partial.open('w', encoding='utf-8') as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def check_thread_env() -> dict[str, str]:
    bad = [k for k in THREADS if os.environ.get(k) != '1']
    if bad:
        raise RuntimeError(f'Single-thread env vars must be 1, bad={bad}')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty string for CPU-only execution')
    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}


def verify_frozen_extra_md5() -> dict[str, str]:
    extra_md5 = {}
    for rel, expected in FROZEN_EXTRA_MD5.items():
        actual = md5_file(EXPERIMENTS / rel)
        if actual != expected:
            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
        extra_md5[rel] = actual
    return extra_md5


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_context():
../../CLAUDE.md:101:- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
../../CLAUDE.md:106:- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
../../CLAUDE.md:107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
../../CLAUDE.md:119:  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`
../../CLAUDE.md:123:- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
../../.trellis/spec/backend/research-diagnostics.md:955:On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
../../.trellis/spec/backend/research-diagnostics.md:1024:deinlab, record its SSH root and verify it before deleting task-created local

exec
/bin/zsh -lc "ls -a ../../.trellis/tasks/11-21-data-pilot-fer; rg -n 'Stage A5|stageA5' ../../.trellis/tasks/11-21-data-pilot-fer -g '*.md' | cut -c1-240 | head -24; rg -n 'def (raw|observe|make_frame)|sample.*channel|gd =' ../cstate_codelay_sbl_stage3_20261118/run.py ../sp_afdm_frozen_20260920/src -g '*.py' | head -36; ls -l /opt/anaconda3/bin/python; cat out/stageA4/REMOTE_ROWS_MD5.txt" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
.
..
check.jsonl
design.md
implement.jsonl
implement.md
prd.md
research
task.json
../cstate_codelay_sbl_stage3_20261118/run.py:74:def observed(ctx, base, rho, snr):
lrwxr-xr-x  1 guoyikun  staff  10 Sep 19  2025 /opt/anaconda3/bin/python -> python3.13
a662fa94be8f76a960a3f43413c95973  rows.jsonl.gz

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "sed -n '1,36p' ../cstate_codelay_sbl_stage3_20261118/run.py; sed -n '1,80p' ../unified_cov_prospective_20261119/cstate.py; rg -n 'def (base|observe)\\(' ../p1* ../*exchange* ../*genie* -g '*.py' 2>/dev/null | head -40; sed -n '95,160p' ../../CLAUDE.md; sed -n '943,970p' ../../.trellis/spec/backend/research-diagnostics.md; sed -n '1,65p' ../../.trellis/tasks/11-21-data-pilot-fer/prd.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
"""Stage 3 receiver qualification and paired-main sharding."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import numpy as np

import codelay

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP/'tf_cstate_e1_20261017'))
import e1_driver as e1

CELLS = tuple((s, r) for s in ('U', 'G') for r in (300, 500))
GRID = {300: (500, 550, 600, 700, 800, 900, 1000, 1100),
        500: (500, 550, 600, 650, 700, 800, 900, 1000, 1100)}
ARMS = ('F0', 'FULL', 'CODELAY')
MAIN_FRAMES = range(4000, 4400)
HISTORIC_KEYS = EXP/'tf_cstate_e1_20261017/out/select/triggered_keys.json'
P1_MD5 = dict(gen_fixed='9a3a987e0a1aaecde33018da5f38c74c',
              gs_driver='10611942919e1efcf2839ee5c260d22a',
              native_twofft='d47af1373b2f0052e6de078de40711ba',
              p1_driver='e8594ebfe04f490a86fc16ebd5069cd2',
              p1ctx='e66268616035f8111aacb4910d5bc8a2',
              receiver='228411ca9751eecfca2f794ace909dfd')


def dump(value, dst):
    print(json.dumps(value, allow_nan=False), file=dst, flush=True)


"""Stage 3 continuation with trial-support spectral covariance."""

import importlib.util
import inspect
from functools import lru_cache
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import numpy as np

from projector import block_projector, low_projector

STAGE3 = Path(__file__).resolve().parents[1] / 'cstate_codelay_sbl_stage3_20261118'
sys.path.insert(0, str(STAGE3))
spec = importlib.util.spec_from_file_location('stage3_codelay_run', STAGE3 / 'run.py')
stage3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage3)
SPECTRAL_ARMS = ('U', 'C-hi', 'C-lo')
ARMS = ('F0', 'A2', 'CD', *SPECTRAL_ARMS)
TAU = .5


def context():
    return stage3.context()


def _empty_census():
    return dict(scored_trials=0, nonempty_scored_trials=0, valid_trials=0, nonempty_trials=0,
                checked_trials=0, max_relative_score_error=0.)


def _trial_projectors(delays, dopplers, slot, candidate_delays, candidate_dopplers, n, tau):
    """Rebuild each changed co-delay block, retaining disjoint unchanged blocks."""
    keep = np.flatnonzero(np.arange(len(delays)) != slot)
    common = np.zeros((len(delays), len(delays)), dtype=complex)
    common[np.ix_(keep, keep)] = low_projector(delays[keep], dopplers[keep], n, tau)
    shape = (len(candidate_delays), *common.shape)
    projectors = np.broadcast_to(common, shape).copy()
    for delay in np.unique(delays[keep]):
        rows = np.flatnonzero(candidate_delays == delay)
        if not len(rows):
            continue
        members = keep[delays[keep] == delay]
        # Match the per-support slot order used by _system at the threshold.
        slots = np.sort(np.r_[slot, members])
        block_dopplers = np.broadcast_to(dopplers[slots], (len(rows), len(slots))).copy()
        block_dopplers[:, np.searchsorted(slots, slot)] = candidate_dopplers[rows]
        projectors[np.ix_(rows, slots, slots)], _ = block_projector(block_dopplers, n, tau)
    return projectors


def _replace_spectrum(gamma, projector, total, arm):
    if arm == 'U':
        return gamma + total * projector
    if arm == 'C-hi':
        high = np.eye(gamma.shape[-1]) - projector
        return high @ gamma @ high + total * projector
    if arm == 'C-lo':
        return projector @ gamma @ projector + total * (np.eye(gamma.shape[-1]) - projector)
    raise ValueError(f'Unknown spectral covariance {arm}')


def _reference_arm(arm, tau, total):
    if arm in SPECTRAL_ARMS and (not tau or not total):
        return 'A2' if arm == 'C-lo' else 'CD'
    return arm


def support_covariance(full, cd, v, delays, dopplers, c1, *, arm, tau=TAU):
    """Actual covariance selected by the arm on a fresh support."""
    system, mode = _support_system(full, cd, v, arm, tau)
    gamma = system.__globals__['projected_variance'](v, delays, dopplers, c1)
    return np.diag(np.diag(gamma)) if mode == 'diag' else gamma


# Copy E-1 geometry_validation_variant.py::reopen_geometry to bind a new projector before each pass and check descent on that objective; the frozen interface lacks those callbacks.
@lru_cache(maxsize=1)
def _pass_code(reference):
zsh:1: no matches found: ../p1*
- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `main` 已提交的本目录（2026-11-21 前为 `trans/tcom-main`），排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 同步：Eric 2026-11-21 授权由 Claude 负责推送镜像（idea 漏斗每轮开始前、或 Eric 要求时）；先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得把 vault 本身推到该仓库。
- 例外：`funnel/*` 分支由 idea 漏斗的云端 runner 写入，只改 `ideas/`；`main` 只由 `sync.sh` 更新。

## Remote Server
- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
- Login landing: `/home/guoyikun`，登录后需 `cd /data/guoyikun/`
- GPU: RTX 4090 单卡，约 5 位活跃用户共享
- Working dir: `/data/guoyikun/`
- Code dir: `/data/guoyikun/00inbox/AFDM-channel-estimation/`
- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。

### 实验结果回传规则（2026-07-26 起）
- 新实验的远程 run 结束后，**小结果文件**（`results.json`、`*_run.log`、表格 md、launcher `.sh`）回传到本地该实验的 `experiments/<experiment>/out/`；既有 run 仍回传到其记录的同名历史 `afdm_sp_joint_unrolled/outputs_*/`，不搬已有证据。文件若被忽略，按具体小文件显式 whitelist；Git 纳入/提交仍遵守当次授权，大文件不因新位置变成可提交。
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
| 新实验的 `run.log` / `tee` 输出 / 结果 JSON | `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/<experiment>/out/`；已有 run 仍按记录的历史 `afdm_sp_joint_unrolled/outputs_*/` 原地保存，不覆写冻结证据 |
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
Keep truth in generation and offline diagnostics; never pass scoring truth into
an operational receiver decision. Save the actual damped/masked I1 H as exact COO
on every frame; check dense canaries on the first two frames. Last LS gains are
not that matrix. Retain every decoder call and native round, input/APP/check,
iteration/syndrome metadata, successful checkpoints and failed-attempt time.

Complete cost includes failed work. Unknown failed-stage splits are explicit
`None`, never fabricated zero. All finite attempt times enter reference latency,
tie breaks and runtime summaries. A timely completed checkpoint remains eligible
after a later failure; future decisions do not qualify. Record whole-process peak
RSS separately from instrumented receiver latency and array storage.

On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
CUDA is hidden and BLAS/OpenMP/Torch use one thread. Existing `build()` owns the
one-time Torch inter-op binding; verify afterward rather than setting it twice.
No concurrently timed numerical jobs; preserve PID/deadline/exit/argv/environment.

### 4. Validation and error matrix

- Identity/hash/duplicate-key/ledger-artifact mismatch -> fail before reuse.
- Invalid frame count, NaN/negative/wrong-type time, inconsistent stage/round or
  checkpoint time -> explicit validation failure, no selection.
- Artifact/storage/programming error -> propagate, never label numerical failure.
- Numerical receiver failure -> retain actual elapsed work and allowed earlier
  checkpoint; unavailable raw bits stay missing in BER recount.
- Valid orphan artifact -> preserve for audit before an explicit rerun; never
  silently append it as a completed ledger decision.

# 数据当导频：自相关候选进第 0 轮的 FER 决定性检验

Eric 2026-11-21 选"建任务设计"。前置证据（都只到"看得见"这一层）：
- [第一步读数](../../../experiments/data_autocorr_acq_20261121/READOUT.md)：真锚条件下，ρ = .15 时自相关捕获有效弱径 .948；独立数据对照只剩 .042。
- [第二步读数](../../../experiments/data_autocorr_acq_20261121/READOUT2.md)：改用导频估出的锚、用导频消前后镜像后，ρ = .15 时导频漏掉的弱径找回 .832；ρ = .05 时第 0 轮覆盖从 .563 提到 .883。
- [查新](../../../experiments/data_autocorr_acq_20261121/novelty-gemini.md)："用数据二阶统计认信道"和"径对出现在时延差、多普勒差处"都已有人做过；可能还新的只有"单帧、编码叠加导频 AFDM 里借此降导频"。

## Goal
回答一个问题：**把自相关候选送进 F0 第 0 轮之后，编码接收机的 FER = 1% 穿越点和系统最优导频比，会不会好于现有最好的接收机（F0 + `CODELAY` 交换，最优点在 ρ = .30）？**

## 价值判断（先说层级：整机）
- 谁卡住了：叠加导频接收机在 ρ < .25 时第 0 轮漏掉弱径，之后交换也救不回（ρ 扫描；低导频读数入口缺失功率的 AUC 为 .83）。
- 最简单的替代：继续用 ρ = .30。新方法的上限：总功率固定时，ρ 从 .30 降到 .05，数据功率最多多出约 1.33 dB。
- 是不是原理：不是。最好的结果是"已知原理搬进编码 AFDM，实测降低导频开销"的工程论文。

## Acceptance Criteria
- [ ] 设计与实现计划（design.md、implement.md）经 Astra 审、Eric 批准后，按 research-checkpoint 第 1 时刻冻结。
- [ ] 阶段 A（真时延进第 0 轮的上界）按冻结判读读出；不过就停，写否定台账。
- [ ] 阶段 A 通过后再跑阶段 B（自相关候选），按冻结判读读出；预测打分；结论由 Eric 定。

## Out of scope
不改现稿任务；不处理同时延近邻径（P1 中不存在）；不做多 N、多信道族（结果为正再说）。

exec
/bin/zsh -lc "rg -n 'def (daft|md5_file)|FROZEN_EXTRA_MD5|THREADS =' ../huang_steelman_20261124/hs_arms.py ../sp_afdm_frozen_20260920/src -g '*.py' | head -22; cat out/stageA3/results.json | sed -n '1,80p'; ls -l stageA5_launch.sh; rg -n 'Process|SharedMemory|Queue|Pool|torch' ../unified_cov_prospective_20261119/cstate.py ../huang_steelman_20261124/hs_arms.py | head -32" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
../huang_steelman_20261124/hs_arms.py:33:THREADS = (
../huang_steelman_20261124/hs_arms.py:48:FROZEN_EXTRA_MD5 = {
../huang_steelman_20261124/hs_arms.py:107:def md5_file(path: Path) -> str:
../huang_steelman_20261124/hs_arms.py:154:    for rel, expected in FROZEN_EXTRA_MD5.items():
../sp_afdm_frozen_20260920/src/physical.py:87:def daft(x,c1,c2,inverse=False):
{
 "_argv": [
  "stageA3.py",
  "read",
  "--out",
  "out/stageA3"
 ],
 "protocol": "STAGEA3_PROTOCOL.md",
 "mean_crossing": {
  "delay": {
   "100": 6.363147192765458,
   "150": 4.446896406445989,
   "200": 4.4
  },
  "ldop": {
   "100": 3.4518234921449324,
   "150": 3.4848027579359577,
   "200": 4.0721139531130754
  },
  "s025": {
   "100": 3.4525806276076887,
   "150": 3.6211487592806386,
   "200": 4.056579816629107
  },
  "s050": {
   "100": 3.4558996000315423,
   "150": 3.486120218565426,
   "200": 4.088377632967893
  },
  "s100": {
   "100": 3.8391069300412353,
   "150": 4.06174976443504,
   "200": 4.248899223661354
  },
  "s200": {
   "100": Infinity,
   "150": Infinity,
   "200": 10.565063125417424
  }
 },
 "best": {
  "delay": 4.4,
  "ldop": 3.4518234921449324,
  "s025": 3.4525806276076887,
  "s050": 3.4558996000315423,
  "s100": 3.8391069300412353,
  "s200": 10.565063125417424
 },
 "retained_fraction": {
  "s025": {
   "point": 0.9992014825757822,
   "ci": [
    0.9974037075062896,
    1.0008091015124065
   ]
  },
  "s050": {
   "point": 0.995701108545886,
   "ci": [
    0.9926273662849471,
    0.998142372988172
   ]
  },
  "s100": {
   "point": 0.5915492161133563,
   "ci": [
    0.33084521642891623,
    0.8498831813650136
   ]
  },
  "s200": {
   "point": -6.502020535568653,
   "ci": [
    NaN,
    NaN
   ]
  }
 },
 "verdict": "MIDDLE",
 "r0_doppler_err_snr4_5": {
-rwxr-xr-x@ 1 guoyikun  staff  2619 Nov 25 01:39 stageA5_launch.sh
../huang_steelman_20261124/hs_arms.py:15:import torch
../huang_steelman_20261124/hs_arms.py:241:        torch.tensor(y, dtype=torch.complex64),
../huang_steelman_20261124/hs_arms.py:242:        torch.tensor(A, dtype=torch.complex64),

codex
已确认两处协议偏差。纯导频和已知数据搜索对每个候选点都重新拟合增益，G2 也用了与协议不同的帧。我再核对数据生成、成本门槛和落盘路径。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "ls -l out/stageA5_sol_review.md; find . -name stageA5_gate.json -print; rg -n 'G1|G2|Stage A5|stageA5' ../../.trellis/tasks/11-21-data-pilot-fer -g '*.md' | cut -c1-240 | head -25; sed -n '30,63p' ../huang_steelman_20261124/hs_arms.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
-rw-r--r--@ 1 guoyikun  staff  193793 Nov 25 01:41 out/stageA5_sol_review.md
../../.trellis/tasks/11-21-data-pilot-fer/implement.md:5:1. **读管线**：确认 ρ 扫描里 F0 + CSTATE 的入口、物理 ρ 的归一化，以及 `pilot_front` → `time_refine` 的接口。检查：能在旧键上复现 ρ 扫描行（G1）。
../../.trellis/tasks/11-21-data-pilot-fer/implement.md:6:2. **注入点**：写一个包装函数，替换第 0 轮送进 `time_refine` 的 (ls, ks, gs)。A-delay 用真时延（多普勒中心取可观测量）；B-rank、B-challenge 用自相关候选。下游一律不改。检查：注入"`pilot_front` 原样输出"时与基线逐位相同（G2）。
MAIN_FRAMES = tuple(range(5400, 5800))
SMOKE_FRAMES = tuple(range(5800, 5840))
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
THREADS = (
    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
)
EXPECTED_TOTAL_TRIGGERS = 18009
EXPECTED_TRIGGERS_BY_STRATUM = {
    (150, 'low'): 1462, (150, 'mid'): 2186,
    (200, 'low'): 1443, (200, 'mid'): 1174,
    (250, 'low'): 1501, (250, 'mid'): 807,
    (300, 'low'): 1569, (300, 'mid'): 791,
    (400, 'low'): 1600, (400, 'mid'): 1419,
    (500, 'low'): 1600, (500, 'mid'): 2457,
}

# Frozen dependencies verified identical between local vault and deinlab BEFORE importing.
FROZEN_EXTRA_MD5 = {
    'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9',
    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
}
OWN_SOURCE_FILES = (
    'PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'test_analysis.py',
    'gates.py', 'run_main.py', 'timing.py', 'launch_main.sh',
)
OWN_MODULE_NAMES = frozenset({
    'hs_arms', 'hs_analysis', 'test_analysis', 'gates', 'run_main', 'timing', 'hs_p1_agg',
})

exec
/bin/zsh -lc "sed -n '1,67p' ../tf_cstate_e1_20261017/e1_driver.py; rg -n '"'^def (base|observe)'"\\(' ../ -g '*.py' | rg 'genie|p1|fixed|paf' | head -26; rg -n 'replace=False|l_i.*choice|choice.*l_i|def.*sample' ../sp_afdm_frozen_20260920/src -g '*.py' | head -30; nl -ba ../sp_afdm_frozen_20260920/src/physical.py | sed -n '81,108p'; rg -n 'TORCH|TMPDIR|shm|git rev-parse|freeze_commit' ../sameframe_cd2_20261125 -g '*.py' -g '*.sh' | head -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
#!/usr/bin/env python
"""E-1 driver (task 10-17-discrete-acquisition-e1; see PROTOCOL.md, which supersedes design.md where they differ).

--mode select  scan the frozen P1 ledger (arms.B.triggered) for the given SNRs and write triggered_keys.json (the unit list).
--mode run     per unit (scenario, rho, snr, frame) with F0 final syndrome != 0: regenerate the P1 frame, rerun F0
               (native_twofft.receive rounds=2 iterations=20 soft/joint), assert G4a (syndrome != 0), then run arms A1..A6 from that
               SAME F0 state; one JSONL row per unit.
--mode gate    G1/G2/G3/G4b on real P1 states: all keys of the given frames/SNRs (triggered and not).
--mode gate-merge  merge gate shards into gates.json.

Arms (all share the captured F0 state; CSTATE20 branch = run_validation._branch re-implemented with per-arm parameters):
  A1 full Gamma  max_edits=2 compact local_passes=2   (production CSTATE20; must reproduce the ledger bitwise)
  A2 diag Gamma  max_edits=2 compact local_passes=2
  A3 full Gamma  max_edits=0 compact local_passes=2
  A4 diag Gamma  max_edits=0 compact local_passes=2
  A5 no geometry call: Channel(r1_delays, r1_dopplers, r1_gains) -> scalar_joint(prior=r1_check) -> LDPC
  A6 full Gamma  max_edits=0 compact local_passes=0   (soft ridge gain refit only; reported arm)
  A7 literal third F0 round: native_twofft.receive(rounds=3, ...) from scratch on the same observation (PROTOCOL.md section 10, O2);
     G5 (every unit): its round-0 and round-1 arrays are bitwise equal to the captured rounds=2 state.
Nothing frozen is edited; the Gamma variant lives in geometry_*_variant.py.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EXPERIMENTS / 'tcom_genie_support_20261016'))
import e1_lib  # noqa: E402
import gs_driver as gd  # noqa: E402
from gs_driver import p1ctx  # noqa: E402

P1_ROWS = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'out' / 'p1'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'  # O1: full P1 grid is the primary unit set
GATE_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
ARMS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7')
ARM_SPECS = {
    'A1': dict(gamma_mode='full', max_edits=2, local_passes=2),
    'A2': dict(gamma_mode='diag', max_edits=2, local_passes=2),
    'A3': dict(gamma_mode='full', max_edits=0, local_passes=2),
    'A4': dict(gamma_mode='diag', max_edits=0, local_passes=2),
    'A5': None,
    'A6': dict(gamma_mode='full', max_edits=0, local_passes=0),
}
A7_SPEC = 'native_twofft.receive rounds=3 iterations=20 ce_mode=soft gain_mode=joint from scratch; G5 compares all r0_*/r1_* arrays with the rounds=2 state'
GEOMETRY_STAGES = ('geometry_setup', 'structural_field_build', 'structural_scoring', 'structural_selection_trace',
                   'structural_refit_refresh', 'structural_fallback_direct', 'local_refinement', 'geometry_finalization')
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')


# ----------------------------------------------------------------------------- provenance
def load_variant():
    e1_lib.prepare_paths()
    import geometry_validation_variant as kvar
    return kvar
../tcom_genie_support_20261016/gs_driver.py:57:def observe(ctx, raw_base, diag_base, rho, snr_centi):
../tcom_channel_crb_20261016/p1ctx.py:19:def base(ctx, scenario, rho, frame):
../sp_afdm_frozen_20260920/src/seal.py:80:        choices = [cell for cell in cell_info if cell["id"] not in {item["id"] for item in chosen}]
    81	    D=dkernel(nu[None,:]+2*n*c1*l[None,:]-s[:,None],n)
    82	    return (D@C)*np.exp(2j*np.pi*c2*((k[None,:]+s[:,None])%n)**2-2j*np.pi*c2*k[None,:]**2)
    83	
    84	# Design-freeze extensions: matrix-free action and exact rowwise weak moments.
    85	from dataclasses import dataclass
    86	
    87	def daft(x,c1,c2,inverse=False):
    88	    x=np.asarray(x,complex);n=x.shape[0];k=np.arange(n);shape=(n,)+(1,)*(x.ndim-1)
    89	    a=np.exp(2j*np.pi*c1*k*k).reshape(shape);b=np.exp(2j*np.pi*c2*k*k).reshape(shape)
    90	    return a.conj()*np.fft.ifft(b.conj()*x,axis=0)*np.sqrt(n) if inverse else b*np.fft.fft(a*x,axis=0)/np.sqrt(n)
    91	
    92	@dataclass(frozen=True)
    93	class Channel:
    94	    n:int;c1:float;c2:float;delays:np.ndarray;dopplers:np.ndarray;gains:np.ndarray
    95	    def __post_init__(self):
    96	        for key,dt in [('delays',int),('dopplers',float),('gains',complex)]:
    97	            object.__setattr__(self,key,np.asarray(getattr(self,key),dtype=dt).copy())
    98	        if self.n<2 or not(len(self.delays)==len(self.dopplers)==len(self.gains)>0):raise ValueError('Invalid path dimensions')
    99	        if np.any(self.delays<0) or np.any(self.delays>=self.n):raise ValueError('Invalid delay')
   100	        if not np.isfinite(self.gains).all() or not np.isfinite(self.dopplers).all():raise ValueError('Nonfinite path')
   101	    @property
   102	    def p(self):return len(self.delays)
   103	    def regressors(self,x,derivative=False):
   104	        if not derivative:return regressors(x,self.delays,self.dopplers,self.c1,self.c2)
   105	        n=self.n;k=np.arange(n);t=daft(x,self.c1,self.c2,True);idx=k[:,None]-self.delays
   106	        cp=np.where(idx<0,np.exp(2j*np.pi*self.c1*(n*n+2*n*idx)),1)
   107	        tt=t[idx%n]*cp*np.exp(2j*np.pi*k[:,None]*self.dopplers/n)*(2j*np.pi*k[:,None]/n)
   108	        return daft(tt,self.c1,self.c2)
../sameframe_cd2_20261125/sameframe_cd2.py:112:def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
../sameframe_cd2_20261125/sameframe_cd2.py:123:        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'{freeze_commit}^{{commit}}'],
../sameframe_cd2_20261125/sameframe_cd2.py:127:        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo')
../sameframe_cd2_20261125/sameframe_cd2.py:135:            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
../sameframe_cd2_20261125/sameframe_cd2.py:139:            raise RuntimeError(f'freeze_commit {freeze_commit} missing {name}')
../sameframe_cd2_20261125/sameframe_cd2.py:141:            raise RuntimeError(f'Live {name} differs from freeze_commit {freeze_commit}')
../sameframe_cd2_20261125/sameframe_cd2.py:318:    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
../sameframe_cd2_20261125/sameframe_cd2.py:580:        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
../sameframe_cd2_20261125/sameframe_cd2.py:645:    freeze_commit: str,
../sameframe_cd2_20261125/sameframe_cd2.py:779:            freeze_commit=freeze_commit,
../sameframe_cd2_20261125/sameframe_cd2.py:818:    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
../sameframe_cd2_20261125/sameframe_cd2.py:819:        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
../sameframe_cd2_20261125/sameframe_cd2.py:836:    verify_freeze_commit_if_git(args.freeze_commit, live_own)
../sameframe_cd2_20261125/sameframe_cd2.py:883:        out_dir, gate, gate_md5, args.freeze_commit, runtime_info, raw_md5,
../sameframe_cd2_20261125/sameframe_cd2.py:924:    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
../sameframe_cd2_20261125/sameframe_cd2.py:925:        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
../sameframe_cd2_20261125/sameframe_cd2.py:940:    verify_freeze_commit_if_git(args.freeze_commit, own_md5())
../sameframe_cd2_20261125/sameframe_cd2.py:943:    if results['_config']['freeze_commit'] != args.freeze_commit:
../sameframe_cd2_20261125/sameframe_cd2.py:1165:            freeze_commit=args.freeze_commit,
../sameframe_cd2_20261125/launch.sh:37:export TMPDIR="/data/guoyikun/tmp"

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba ../tcom_channel_crb_20261016/p1ctx.py | sed -n '1,103p'; nl -ba ../tcom_genie_support_20261016/gs_driver.py | sed -n '48,90p'; rg -n 'def (base|generate)|replace=False|choice\\(|noise_seed|default_rng' ../tcom_reference_frame_20261015 -g '*.py' | head -48; sed -n '1,40p' ../../.trellis/tasks/11-21-data-pilot-fer/task.json; rg -n 'seed|scenario|same.*(frame|pilot|noise)' STAGEA4_PROTOCOL.md | head -18" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     1	"""P1 context and frames for the CRB task: the frozen P1 driver is imported unchanged (same entropy, domain, generator)."""
     2	from __future__ import annotations
     3	
     4	from pathlib import Path
     5	import sys
     6	
     7	HERE = Path(__file__).resolve().parent
     8	P1_DIR = HERE.parent / 'tcom_reference_frame_20261015'
     9	sys.path.insert(0, str(P1_DIR))
    10	import p1_driver  # noqa: E402
    11	
    12	SEED_FN = p1_driver.make_seed_fn()  # P1 ENTROPY_HEX 2261fde3..., DOMAIN TCRF
    13	
    14	
    15	def load():
    16	    return p1_driver.load_context()
    17	
    18	
    19	def base(ctx, scenario, rho, frame):
    20	    """Frame at the first P1 SNR (4.5 dB), exactly as p1_driver.run_shard builds it."""
    21	    return p1_driver.generate(ctx, scenario, rho, 4.5, frame, SEED_FN)
    22	
    23	
    24	def frame(ctx, scenario, rho, snr_db, frame_id):
    25	    raw_base, diag_base = base(ctx, scenario, rho, frame_id)
    26	    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_db)
    27	    return raw, diag, ctx.hd.truth_from_raw(raw, diag)
    48	    return u[np.argsort(-energy, kind='stable')]
    49	
    50	
    51	def run_gs(ctx, obs, refine, gain_mode='joint', arm='genie_support'):
    52	    """Production schedule with the refit replaced by ``refine``; front, detector and decoder unchanged."""
    53	    return ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm=arm, rounds=2, iterations=20,
    54	                                      gain_mode=gain_mode, refine_override=refine)
    55	
    56	
    57	def observe(ctx, raw_base, diag_base, rho, snr_centi):
    58	    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
    59	    return raw, ctx.hd.observe(raw, rho, snr_centi / 100), ctx.hd.truth_from_raw(raw, diag)
    60	
    61	
    62	def score(ctx, decoded, truth):
    63	    return int(np.count_nonzero(ctx.extract_info(ctx.code, np.asarray(decoded)) != truth['info']))
    64	
    65	
    66	def paths(delays, dopplers, gains):
    67	    return dict(delays=[int(x) for x in np.asarray(delays)], dopplers=[float(x) for x in np.asarray(dopplers)],
    68	                gains=np.asarray(gains, complex))
    69	
    70	
    71	def gs_arm(ctx, obs, truth, arm, n):
    72	    delays = genie_delays(truth, arm)
    73	    log = []
    74	    t0 = time.perf_counter()
    75	    res = run_gs(ctx, obs, ctx.arms.make_a1_refine(delays, log))
    76	    seconds = time.perf_counter() - t0
    77	    a = res.arrays
    78	    # S4: the supplied delay list is used verbatim in both rounds; both refits logged; geometry finite and in range
    79	    for r in (0, 1):
    80	        assert np.array_equal(np.asarray(a[f'r{r}_delays'], int), delays), f'S4 delay list changed ({arm}, round {r})'
    81	        nu = np.asarray(a[f'r{r}_dopplers'], float)
    82	        assert np.all(np.abs(nu) <= 3) and np.isfinite(nu).all(), f'S4 Doppler out of range ({arm})'
    83	        assert np.isfinite(a[f'r{r}_gains']).all() and np.isfinite(a[f'r{r}_ce_gains']).all(), f'S4 nonfinite gains ({arm})'
    84	    assert len(log) == 2, f'S4 expected 2 refits, got {len(log)} ({arm})'
    85	    truth_p = dict(delays=np.asarray(truth['l_i'], int), dopplers=np.asarray(truth['k_real'], float),
    86	                   gains=np.asarray(truth['g_i'], complex))
    87	    dec = res.decoder['decoded']
    88	    return dict(fer=int(score(ctx, dec, truth) > 0), info_errors=score(ctx, dec, truth),
    89	                syndrome=int(ctx.hd.syndrome_weight(ctx, dec)), decoded_sha256=bits_sha(dec),
    90	                ldpc_iters=int(res.decoder['iterations']), seconds=seconds,
../tcom_reference_frame_20261015/p1_agg.py:347:    rng = np.random.default_rng(seed)
../tcom_reference_frame_20261015/p1_agg.py:443:    rng = np.random.default_rng(5)
../tcom_reference_frame_20261015/s0_gates.py:207:    geo = np.random.default_rng(seed + 1)
../tcom_reference_frame_20261015/s0_gates.py:248:    rng = np.random.default_rng(seed)
../tcom_reference_frame_20261015/p2b_agg.py:153:    rng = np.random.default_rng(seed)
../tcom_reference_frame_20261015/p2b_agg.py:259:    rng = np.random.default_rng(3)
../tcom_reference_frame_20261015/p2b_agg.py:277:    data2, snr2, _, _ = build(synth(np.random.default_rng(21), 30000, snrs, two, bits), list(two))
../tcom_reference_frame_20261015/p2b_agg.py:278:    cal2 = crossing_calibration(data2, 'SPG_r300', 'A3_r300', snr2, 1000, np.random.default_rng(22))
../tcom_reference_frame_20261015/z_agg.py:187:    rng = np.random.default_rng(seed)
../tcom_reference_frame_20261015/z_agg.py:259:    rng = np.random.default_rng(4)
../tcom_reference_frame_20261015/zheng_check.py:81:    rng = np.random.default_rng(3)
../tcom_reference_frame_20261015/zheng_check.py:98:                   audit=Zheng().audit(np.random.default_rng(0)), rows=rows,
../tcom_reference_frame_20261015/zheng_repro.py:61:    return np.random.default_rng(np.random.SeedSequence(entropy_words(ENTROPY_HEX) + [DOMAIN, int(frame), COMPONENTS[component]]))
../tcom_reference_frame_20261015/zheng_repro.py:102:        numpy=np.__version__, python=sys.version.split()[0], audit=z.audit(np.random.default_rng(0))))
../tcom_reference_frame_20261015/zheng_repro.py:357:        print(json.dumps(Zheng().audit(np.random.default_rng(0)), indent=1))
../tcom_reference_frame_20261015/p2b_gates.py:122:    rng = np.random.default_rng(20261017)
../tcom_reference_frame_20261015/p2b_gates.py:181:    rng = np.random.default_rng(7)
../tcom_reference_frame_20261015/p2b_gates.py:330:    rng = np.random.default_rng(11)
../tcom_reference_frame_20261015/p1_driver.py:242:def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
../tcom_reference_frame_20261015/gen_fixed.py:96:        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
../tcom_reference_frame_20261015/gen_fixed.py:101:    return int(np.random.default_rng(np.random.SeedSequence(
../tcom_reference_frame_20261015/gen_fixed.py:211:    return np.random.default_rng(np.random.SeedSequence([int(channel_seed), GEO_DOMAIN]))
../tcom_reference_frame_20261015/gen_fixed.py:292:def generate_channel(system, channel_seed, flags):
../tcom_reference_frame_20261015/gen_fixed.py:320:def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
../tcom_reference_frame_20261015/zport_gates.py:88:    rng = np.random.default_rng(12)
../tcom_reference_frame_20261015/zport_gates.py:93:            l = rng.choice(zp.l_max + 1, size=8, replace=False)
../tcom_reference_frame_20261015/zport_gates.py:97:                nu = rng.choice([v for v in np.arange(-3., 3. + 1e-9, .25) if v != round(v)], size=8)
../tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:76:        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
../tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:81:    return int(np.random.default_rng(np.random.SeedSequence(
../tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:190:    return np.random.default_rng(np.random.SeedSequence([int(channel_seed), GEO_DOMAIN]))
../tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:271:def generate_channel(system, channel_seed, flags):
../tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:299:def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
{
  "id": "data-pilot-fer",
  "name": "data-pilot-fer",
  "title": "数据当导频：自相关候选进第 0 轮的 FER 决定性检验",
  "description": "",
  "status": "in_progress",
  "dev_type": null,
  "scope": null,
  "package": null,
  "priority": "P2",
  "creator": "guoyikun",
  "assignee": "guoyikun",
  "createdAt": "2026-11-21",
  "completedAt": null,
  "branch": null,
  "base_branch": "main",
  "worktree_path": null,
  "commit": null,
  "pr_url": null,
  "subtasks": [],
  "children": [],
  "parent": null,
  "relatedFiles": [],
  "notes": "",
  "meta": {}
}
exec
/bin/zsh -lc "rg -n 'def (build|generate)|replace=False|choice\\(|default_rng|l_i|k_real' ../tcom_* -g 'gen_fixed.py' | head -58; rg -n 'torch.set_num_threads|set_num_interop_threads' ../tcom_reference_frame_20261015 ../sp_afdm_frozen_20260920/src ../tcom_channel_crb_20261016 -g '*.py' | head -18; rg -n 'STAGEA5|STAGE_A5' out -g '*gate*' -g '"'!*.gz'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 exited 1 in 0ms:
../tcom_reference_frame_20261015/gen_fixed.py:22:                        theta ~ U[0, 2 pi), nu_max = UWA_NU_MAX_99 (99% quantile of |k_real| under the UWA law).
../tcom_reference_frame_20261015/gen_fixed.py:44:# 99% quantile of |k_real| under the frozen UWA law, frozen here after the S0 estimate
../tcom_reference_frame_20261015/gen_fixed.py:96:        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
../tcom_reference_frame_20261015/gen_fixed.py:101:    return int(np.random.default_rng(np.random.SeedSequence(
../tcom_reference_frame_20261015/gen_fixed.py:127:    """Delay bin l_i of each path.  Frozen (afdm_env.py:532-533): l = clip(round(delay_s / delay_res), 0, l_max_cap)
../tcom_reference_frame_20261015/gen_fixed.py:195:def doppler_k_real(system, doppler_a, flags, geo_rng):
../tcom_reference_frame_20261015/gen_fixed.py:196:    """Continuous Doppler bins k_real.  UWA (afdm_env.py:550-554): k = (a fc / fs) N, clipped to +-k_clip.
../tcom_reference_frame_20261015/gen_fixed.py:200:        k_real = (doppler_a * system.fc / system.fs) * n
../tcom_reference_frame_20261015/gen_fixed.py:205:        k_real = UWA_NU_MAX_99 * np.cos(theta)
../tcom_reference_frame_20261015/gen_fixed.py:207:    return np.clip(k_real, -float(k_clip), float(k_clip))
../tcom_reference_frame_20261015/gen_fixed.py:211:    return np.random.default_rng(np.random.SeedSequence([int(channel_seed), GEO_DOMAIN]))
../tcom_reference_frame_20261015/gen_fixed.py:225:    l_i = delay_bins(system, delay_idx_bar, flags)
../tcom_reference_frame_20261015/gen_fixed.py:226:    k_real = doppler_k_real(system, doppler_a, flags, geo_rng_for(channel_seed))
../tcom_reference_frame_20261015/gen_fixed.py:229:    k_max = float(np.max(np.abs(k_real))) if taps > 0 else 0.0
../tcom_reference_frame_20261015/gen_fixed.py:235:        k_base = int(np.round(k_real[i]))
../tcom_reference_frame_20261015/gen_fixed.py:236:        kappa = k_real[i] - k_base
../tcom_reference_frame_20261015/gen_fixed.py:249:            l_exp.append(int(l_i[i]))
../tcom_reference_frame_20261015/gen_fixed.py:252:    k_i_stored = k_real
../tcom_reference_frame_20261015/gen_fixed.py:276:        doppler_a_out = k_real / n * system.fs / system.fc
../tcom_reference_frame_20261015/gen_fixed.py:281:        'g_i': g_i, 'g_i_raw': g_i_raw, 'l_i': l_i, 'k_i': k_i_stored, 'k_real': k_real, 'k_max': k_max,
../tcom_reference_frame_20261015/gen_fixed.py:282:        'k_max_int': k_max_int, 'delay_spread': int(np.max(l_i)) if taps > 0 else 0, 'taps': taps,
../tcom_reference_frame_20261015/gen_fixed.py:292:def generate_channel(system, channel_seed, flags):
../tcom_reference_frame_20261015/gen_fixed.py:320:def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
../tcom_reference_frame_20261015/gen_fixed.py:337:        prefix = max(prefix, RECEIVER_BANK_MAX_DELAY, int(np.max(raw['params']['l_i'])))
../tcom_reference_frame_20261015/gen_fixed.py:339:    diag['gen_fixed'] = dict(raw['gen_fixed'], prefix_length=prefix, max_delay=int(np.max(raw['params']['l_i'])),
../tcom_reference_frame_20261015/gen_fixed.py:340:                             prefix_ge_max_delay=bool(prefix >= int(np.max(raw['params']['l_i']))),

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba ../sameframe_cd2_20261125/launch.sh | sed -n '9,76p'; rg -n 'N ?= ?[0-9]+|k_clip|distinct' STAGEA4_PROTOCOL.md ../tcom_reference_frame_20261015/p1_driver.py ../tcom_reference_frame_20261015/gen_fixed.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     9	FREEZE_COMMIT="$2"
    10	
    11	REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
    12	HERE="$REPO/experiments/sameframe_cd2_20261125"
    13	OUT="$HERE/out"
    14	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
    15	
    16	LOCKDIR="$OUT/.lock"
    17	if ! mkdir "$LOCKDIR" 2>/dev/null; then
    18	    echo "ERROR: lock $LOCKDIR already held" >&2
    19	    exit 1
    20	fi
    21	
    22	cd "$REPO"
    23	set +u
    24	source /opt/anaconda3/etc/profile.d/conda.sh
    25	conda activate AFDM
    26	set -u
    27	
    28	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    29	if [ "$(which python)" != "$PY" ]; then
    30	    rmdir "$LOCKDIR" 2>/dev/null || true
    31	    echo "ERROR: active python $(which python) != $PY" >&2
    32	    exit 1
    33	fi
    34	
    35	export PYTHONDONTWRITEBYTECODE=1
    36	export CUDA_VISIBLE_DEVICES=""
    37	export TMPDIR="/data/guoyikun/tmp"
    38	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
    39	export OMP_NUM_THREADS=1
    40	export OPENBLAS_NUM_THREADS=1
    41	export MKL_NUM_THREADS=1
    42	export NUMEXPR_NUM_THREADS=1
    43	export BLIS_NUM_THREADS=1
    44	export VECLIB_MAXIMUM_THREADS=1
    45	
    46	if [ "$MODE" = "gate" ]; then
    47	    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    48	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gate_cpu.txt" \
    49	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/sameframe_cd2.py" \
    50	        gate --out "$OUT" --workers 16 \
    51	        > "$OUT/gate.log" 2>&1
    52	    exit $?
    53	fi
    54	
    55	if [ "$MODE" = "run" ]; then
    56	    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/partA_shard*.jsonl* >/dev/null 2>&1; then
    57	        rmdir "$LOCKDIR" 2>/dev/null || true
    58	        echo "ERROR: $OUT/raw already contains shards; refuse to overwrite" >&2
    59	        exit 1
    60	    fi
    61	    status=STOPPED
    62	    cleanup() {
    63	        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    64	        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    65	        rmdir "$LOCKDIR" 2>/dev/null || true
    66	    }
    67	    trap cleanup EXIT
    68	
    69	    # Part A: Python enforces cumulative CPU <= 6.0 core-hours; wall cap 1800s outer safety net
    70	    set +e
    71	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/partA_cpu.txt" \
    72	        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/sameframe_cd2.py" \
    73	        partA --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    74	        > "$OUT/partA.log" 2>&1
    75	    rc=$?
    76	    set -e
../tcom_reference_frame_20261015/gen_fixed.py:26:                        frame and, with distinct delays (D1+D2), ||H||_F^2 / N = 1 exactly.
../tcom_reference_frame_20261015/gen_fixed.py:41:GEO_DOMAIN = 0x47454F4D        # "GEOM": SeedSequence([channel_seed, GEO_DOMAIN]) feeds the geometric angles
../tcom_reference_frame_20261015/gen_fixed.py:196:    """Continuous Doppler bins k_real.  UWA (afdm_env.py:550-554): k = (a fc / fs) N, clipped to +-k_clip.
../tcom_reference_frame_20261015/gen_fixed.py:206:    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
../tcom_reference_frame_20261015/gen_fixed.py:207:    return np.clip(k_real, -float(k_clip), float(k_clip))
../tcom_reference_frame_20261015/gen_fixed.py:228:    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
../tcom_reference_frame_20261015/gen_fixed.py:244:            if abs(k_eff) > k_clip:
../tcom_reference_frame_20261015/gen_fixed.py:298:                  fallback_clip=bool(d['fallback']), delay_index=np.asarray(d['delay_index']))
../tcom_reference_frame_20261015/p1_driver.py:46:DOMAIN = 0x54435246  # "TCRF"; distinct from HRLD 0x48524C44, CLUS 0x434C5553, CSTA 0x43535441, GEOM 0x47454F4D and every [20260920, ...] stream
../tcom_reference_frame_20261015/p1_driver.py:250:    out.update(gen_flags=g['flags'], gen_redraws=int(g['redraws']), gen_fallback_clip=bool(g['fallback_clip']),

exec
/bin/zsh -lc "nl -ba ../tcom_reference_frame_20261015/p1_driver.py | sed -n '55,130p;228,257p'; nl -ba ../tcom_reference_frame_20261015/gen_fixed.py | sed -n '91,123p;124,162p;195,231p;292,337p'; rg -n 'def.*(draw|generate)|tx =|noise.*=|np\\.sqrt\\(1.*rho' ../tcom_reference_frame_20261015/gen_fixed.py | tail -28" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
    55	    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
    56	    B='F0 + run_validation._branch CSTATE20 iff F0 final syndrome != 0 (F0 prefix included in B seconds)',
    57	    LOCAL='F0 + run_validation._branch LOCAL20 iff F0 final syndrome != 0',
    58	    C='cstate_necessity_stageA_20260928/native_f1.receive_f1 (frozen NOMP front + TF_J20_R2)',
    59	    D='C + run_validation._branch CSTATE20 iff C final syndrome != 0',
    60	    A3='interventions.run_fixed_channel detector=tf with the true (l_i, k_real, g_i)',
    61	    final_decoded_sha256='sha256 of uint8 decoded bits (same convention as Stage A / five-policy decisions)')
    62	
    63	
    64	# ----------------------------------------------------------------------------- headroom driver (frozen, imported)
    65	def load_headroom():
    66	    spec = importlib.util.spec_from_file_location('headroom_driver', HEADROOM / 'driver.py')
    67	    module = importlib.util.module_from_spec(spec)
    68	    spec.loader.exec_module(module)
    69	    return module
    70	
    71	
    72	def md5_file(path):
    73	    return hashlib.md5(Path(path).read_bytes()).hexdigest()
    74	
    75	
    76	def sha256_file(path):
    77	    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    78	
    79	
    80	def project_module_files():
    81	    """Every imported module whose source lives inside the project tree (not site-packages)."""
    82	    out = {}
    83	    root = str(PROJECT)
    84	    for name, module in sorted(sys.modules.items()):
    85	        if name.startswith('__'):
    86	            continue
    87	        path = getattr(module, '__file__', None)
    88	        if path and os.path.isabs(path) and path.endswith('.py') and str(Path(path).resolve()).startswith(root):
    89	            out[name] = str(Path(path).resolve())
    90	    return out
    91	
    92	
    93	def load_context():
    94	    """Frozen headroom context (system, code, native, kernel, branch, wrappers, arms) + the Stage-A F1 receiver."""
    95	    hd = load_headroom()
    96	    args = hd.parse_args(['--mode', 'generate', '--out', str(HERE / 'out' / 'p1_ctx'), '--project', str(PROJECT)])
    97	    ctx = hd.load_context(args)
    98	    sys.path.insert(0, str(STAGE_A))
    99	    from native_f1 import receive_f1
   100	    ctx.receive_f1 = receive_f1
   101	    ctx.hd = hd
   102	    files = project_module_files()
   103	    files['p1_driver'] = str(HERE / 'p1_driver.py')
   104	    files['gen_fixed'] = str(HERE / 'gen_fixed.py')
   105	    ctx.source_md5 = {k: md5_file(v) for k, v in sorted(files.items())}
   106	    ctx.source_sha256 = {k: sha256_file(v) for k, v in sorted(files.items())}
   107	    ctx.source_paths = {k: str(Path(v).relative_to(PROJECT)) for k, v in sorted(files.items())}
   108	    return ctx
   109	
   110	
   111	# ----------------------------------------------------------------------------- seeds
   112	def entropy_words(entropy_hex):
   113	    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
   114	        raise ValueError('entropy must be 64 lowercase hex characters')
   115	    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]
   116	
   117	
   118	def make_seed_fn(entropy_hex=ENTROPY_HEX, domain=DOMAIN):
   119	    words = entropy_words(entropy_hex)
   120	
   121	    def seed_fn(frame, component):
   122	        if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
   123	            raise ValueError('invalid stream coordinate')
   124	        return words + [domain, frame, component]
   125	    return seed_fn
   126	
   127	
   128	# ----------------------------------------------------------------------------- arms
   129	def _syndrome(ctx, decoded):
   130	    return ctx.hd.syndrome_weight(ctx, decoded)
   228	            continue
   229	        sc = ctx.hd.score(ctx, res, truth)
   230	        rec = dict(status='ok', fer=int(sc['info_errors'] > 0), info_errors=sc['info_errors'], coded_errors=sc['coded_errors'],
   231	                   syndrome=sc['syndrome'], triggered=res.get('triggered'), seconds=sc['seconds'],
   232	                   ldpc_iters=sc['ldpc_iters'], logloss_bits=sc['logloss_bits'],
   233	                   decoded_sha256=_bits_sha(res['decoded']))
   234	        for key in ('prefix_seconds', 'branch_seconds', 'f0_syndrome', 'c_syndrome', 'fit_delays', 'fit_dopplers'):
   235	            if key in res:
   236	                rec[key] = res[key]
   237	        out[arm] = rec
   238	    return out
   239	
   240	
   241	# ----------------------------------------------------------------------------- one cell
   242	def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
   243	    flags = SCENARIOS[scenario_or_flags] if isinstance(scenario_or_flags, str) else scenario_or_flags
   244	    return gen_fixed.generate_base(ctx, rho, snr_db, frame, seed_fn, flags)
   245	
   246	
   247	def truth_fields(ctx, truth, diag):
   248	    out = ctx.hd.truth_summary(truth)
   249	    g = diag['gen_fixed']
   250	    out.update(gen_flags=g['flags'], gen_redraws=int(g['redraws']), gen_fallback_clip=bool(g['fallback_clip']),
   251	               gen_prefix=int(g['prefix_length']), gen_max_delay=int(g['max_delay']), gen_path_power=float(g['path_power']),
   252	               gen_energy_per_dim=float(diag['channel_energy_per_dimension']),
   253	               gen_nu_max=g['nu_max_99'])
   254	    return out
   255	
   256	
   257	def pair_fingerprint(truth):
    91	# --------------------------------------------------------------------------- streams (copied from driver.py)
    92	def make_rng_factory(seed_fn, frame):
    93	    def rng_factory(_replicate, index, component, *, split):
    94	        if index != frame or split != 2 or component not in COMPONENTS.values():
    95	            raise ValueError('generator requested an unregistered random stream')
    96	        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
    97	    return rng_factory
    98	
    99	
   100	def expected_channel_seed(seed_fn, frame):
   101	    return int(np.random.default_rng(np.random.SeedSequence(
   102	        seed_fn(frame, COMPONENTS['channel']))).integers(0, 2**31))
   103	
   104	
   105	# --------------------------------------------------------------------------- grid / cap
   106	def effective_grid(system, flags):
   107	    """Delay grid actually used by the draw.  Frozen: delta_f = 15 Hz (afdm_env.py:36) -> 65.1 us bins
   108	    while samples are Ts = 62.5 us.  D2: delta_f := fs/N so that delay_resolution == Ts."""
   109	    ts = float(system.Ts)
   110	    n = int(system.N_total)
   111	    if flags.fix_delay_grid:
   112	        delta_f = float(system.fs) / n
   113	        res = 1.0 / (n * delta_f)
   114	        if not np.isclose(res, ts, rtol=1e-12, atol=0):
   115	            raise AssertionError('D2 grid inconsistent: delay_resolution != Ts')
   116	    else:
   117	        delta_f = float(system.delta_f)
   118	        res = float(system.delay_resolution)
   119	    l_cap = int(system.l_max_cap)
   120	    # D1: the cap the loop would have used had it been computed after the final fs/Ts (afdm_env.py:78-79 formula)
   121	    cap_idx_fixed = int(np.floor(l_cap * res / ts + 1e-9)) + 1
   122	    return dict(ts=ts, delta_f=delta_f, delay_res=res, cap_idx_fixed=cap_idx_fixed,
   123	                cap_idx_frozen=int(system.max_delay_idx_bar_supported))
   124	
   125	
   126	def delay_bins(system, delay_idx_bar, flags, *, clip=True):
   127	    """Delay bin l_i of each path.  Frozen (afdm_env.py:532-533): l = clip(round(delay_s / delay_res), 0, l_max_cap)
   128	    with delay_s = (idx - 1) * Ts.  D2: l = idx - 1 exactly (integer samples)."""
   129	    grid = effective_grid(system, flags)
   130	    idx = np.asarray(delay_idx_bar)
   131	    if flags.fix_delay_grid:
   132	        l = (idx - 1).astype(int)
   133	    else:
   134	        delays = (idx - 1) * grid['ts']
   135	        l = np.round(delays / grid['delay_res']).astype(int)
   136	    return np.clip(l, 0, int(system.l_max_cap)) if clip else l
   137	
   138	
   139	# --------------------------------------------------------------------------- path draws
   140	def one_attempt(system, rs, flags):
   141	    """One pass of the draw loop of generate_uwa_channel (afdm_env.py:311-340); same call order on ``rs``."""
   142	    P = int(system.P_paths)
   143	    ts = effective_grid(system, flags)['ts']
   144	    tau_mean = system.tau_mean if flags.delay_scale == 1.0 else system.tau_mean * flags.delay_scale
   145	    d_tau = rs.exponential(scale=tau_mean, size=P)
   146	    d_tau_index = np.maximum(1, np.ceil(d_tau / ts).astype(int))
   147	    delay_index = np.cumsum(d_tau_index)
   148	    delay_vec = (delay_index - 1) * ts
   149	    alpha = np.log(10 ** (system.att_dB / 10.0)) / system.tau_spread
   150	    path_var = np.exp(-alpha * delay_vec)
   151	    sigma = np.sqrt(path_var * 2.0 / (4.0 - np.pi))
   152	    amp = rs.rayleigh(scale=sigma)
   153	    amp_norm = np.linalg.norm(amp)
   154	    if amp_norm > 0:
   155	        amp = amp / amp_norm
   156	    phases = 2.0 * np.pi * rs.rand(P)
   157	    gain_tap = amp * np.exp(1j * phases)
   158	    velocities = np.abs(system.v_mean + system.v_std * rs.randn(P))
   159	    doppler_a = velocities / system.c_sound
   160	    delay_idx_bar = np.maximum(1, np.ceil(delay_index / (1.0 + doppler_a)).astype(int))
   161	    return dict(gain_tap=gain_tap, delay_idx_bar=delay_idx_bar, path_var=path_var,
   162	                doppler_a=doppler_a, velocities=velocities, delay_index=delay_index)
   195	def doppler_k_real(system, doppler_a, flags, geo_rng):
   196	    """Continuous Doppler bins k_real.  UWA (afdm_env.py:550-554): k = (a fc / fs) N, clipped to +-k_clip.
   197	    Geometric: k = UWA_NU_MAX_99 cos(theta), theta ~ U[0, 2 pi) from ``geo_rng`` (same clip, inert)."""
   198	    n = int(system.N_total)
   199	    if flags.doppler_law == 'uwa':
   200	        k_real = (doppler_a * system.fc / system.fs) * n
   201	    else:
   202	        if UWA_NU_MAX_99 is None:
   203	            raise RuntimeError('UWA_NU_MAX_99 has not been frozen')
   204	        theta = geo_rng.uniform(0., 2. * np.pi, size=len(doppler_a))
   205	        k_real = UWA_NU_MAX_99 * np.cos(theta)
   206	    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
   207	    return np.clip(k_real, -float(k_clip), float(k_clip))
   208	
   209	
   210	def geo_rng_for(channel_seed):
   211	    return np.random.default_rng(np.random.SeedSequence([int(channel_seed), GEO_DOMAIN]))
   212	
   213	
   214	# --------------------------------------------------------------------------- channel (copy of generate_channel_matrix)
   215	def paths_to_channel(system, d, flags, channel_seed):
   216	    """Copy of AFDMEnvMixin.generate_channel_matrix (afdm_env.py:527-674) after the path draw, minus H_time."""
   217	    if getattr(system, 'delay_collision', None) is not None:
   218	        raise ValueError('delay_collision is not part of the production draw')
   219	    if not system.use_frac_doppler:
   220	        raise ValueError('production draw uses the fractional (Dirichlet) Doppler mode')
   221	    delays, g_i_raw, delay_idx_bar = d['delay_bar'], d['gain_tap'], d['delay_idx_bar']
   222	    path_var, doppler_a, velocities = d['path_var'], d['doppler_a'], d['velocities']
   223	    taps = len(g_i_raw)
   224	
   225	    l_i = delay_bins(system, delay_idx_bar, flags)
   226	    k_real = doppler_k_real(system, doppler_a, flags, geo_rng_for(channel_seed))
   227	    n = int(system.N_total)
   228	    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
   229	    k_max = float(np.max(np.abs(k_real))) if taps > 0 else 0.0
   230	
   231	    chan_coef_exp, l_exp, k_exp = [], [], []
   292	def generate_channel(system, channel_seed, flags):
   293	    """RandomState(channel_seed) == np.random.seed(channel_seed) + module-level draws (frozen make_frame)."""
   294	    rs = np.random.RandomState(int(channel_seed))
   295	    d = draw_paths(system, rs, flags)
   296	    h_eff, params = paths_to_channel(system, d, flags, channel_seed)
   297	    extras = dict(flags=flags.tag(), attempts=int(d['attempts']), redraws=int(d['attempts']) - 1,
   298	                  fallback_clip=bool(d['fallback']), delay_index=np.asarray(d['delay_index']))
   299	    return h_eff, params, extras
   300	
   301	
   302	# --------------------------------------------------------------------------- frame (copy of make_frame)
   303	def make_frame(system, code, replicate, index, snr, flags, *, split, rng_factory, encode, qpsk_map):
   304	    """Copy of budgeted_support_eval.make_frame (lines 114-129), coded frames only."""
   305	    n = system.N_total
   306	    channel_seed = int(rng_factory(replicate, index, 1, split=split).integers(0, 2**31))
   307	    h, params, extras = generate_channel(system, channel_seed, flags)
   308	    info = rng_factory(replicate, index, 2, split=split).integers(0, 2, size=code['k']).astype(np.uint8)
   309	    coded = encode(code, info)
   310	    data = np.sqrt(1 - system.rho) * qpsk_map(coded, scale=1)
   311	    pilot = np.sqrt(system.rho) * system._zc_seq
   312	    rng = rng_factory(replicate, index, 3, split=split)
   313	    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
   314	    sigma2 = 10 ** (-snr / 10)
   315	    y = h @ (pilot + data) + np.sqrt(sigma2) * noise
   316	    return dict(y=y, H=h, params=params, info=info, coded=coded, data=data, pilot=pilot, noise=noise,
   317	                sigma2=sigma2, channel_seed=channel_seed, uncoded=False, split_id=split, gen_fixed=extras)
   318	
   319	
   320	def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
   321	    """Copy of headroom driver.generate_base (driver.py:209-224).  rho shim as in the frozen driver.
   322	
   323	    Prefix: flags off -> prefix_length = system.l_max_cap (= 102, frozen, unchanged).  D1 on -> prefix =
   324	    max(l_max_cap, RECEIVER_BANK_MAX_DELAY, largest drawn delay); with the explicit truncation at 102 this is
   325	    always 102, i.e. the frozen value already satisfies prefix >= max delay and nothing changes.
   326	    """
   327	    shim = copy.copy(ctx.system)
   328	    shim.rho = float(rho)
   329	    raw = make_frame(shim, ctx.code, 0, frame, snr_db, flags, split=2,
   330	                     rng_factory=make_rng_factory(seed_fn, frame), encode=ctx.encode, qpsk_map=ctx.qpsk_map)
   331	    if raw['channel_seed'] != expected_channel_seed(seed_fn, frame):
   332	        raise AssertionError('channel stream does not match its registered descriptor')
   333	    if not np.array_equal(raw['pilot'], np.sqrt(shim.rho) * ctx.system._zc_seq):
   334	        raise AssertionError('pilot law differs')
   335	    prefix = int(shim.l_max_cap)
   336	    if flags.fix_delay_cap:
   337	        prefix = max(prefix, RECEIVER_BANK_MAX_DELAY, int(np.max(raw['params']['l_i'])))
165:def draw_paths(system, rs, flags):
292:def generate_channel(system, channel_seed, flags):
310:    data = np.sqrt(1 - system.rho) * qpsk_map(coded, scale=1)
313:    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
316:    return dict(y=y, H=h, params=params, info=info, coded=coded, data=data, pilot=pilot, noise=noise,
320:def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'sys\\.executable|tmux|rows\\.jsonl\\.gz|REMOTE_ROWS_MD5|_argv|_config' STAGEA5_PROTOCOL.md stageA5.py stageA5_launch.sh; rg -n 'scenarios|paired|seed' ../sameframe_cd2_20261125/PROTOCOL.md | head -15" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
exec
/bin/zsh -lc "nl -ba ../tcom_reference_frame_20261015/p1_driver.py | sed -n '42,56p'; nl -ba ../tcom_reference_frame_20261015/gen_fixed.py | sed -n '163,195p'; nl -ba stageA5.py | sed -n '780,785p;866,897p;910,957p'; nl -ba stageA5_launch.sh | sed -n '15,31p;62,88p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
STAGEA5_PROTOCOL.md:72:- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，日志首行打印 `sys.executable`）。
STAGEA5_PROTOCOL.md:73:- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp` 或 `/home/guoyikun`；`tmux` 会话名 `g_a5`；工作进程 `24`（$\le 32$）。
STAGEA5_PROTOCOL.md:74:- 原始逐键行（`out/stageA5/rows.jsonl.gz`）留远端并记录 MD5 到 `out/stageA5/REMOTE_ROWS_MD5.txt`；本地回传 `stageA5_gate.json`、`out/stageA5/results.json`（含 `_argv`/`_config`）、`RESULTS.md`、`STATUS` 与日志。
stageA5.py:512:    print(sys.executable, flush=True)
stageA5.py:513:    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
stageA5.py:514:        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
stageA5.py:528:    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
stageA5.py:530:        raise RuntimeError(f'stageA4 rows.jsonl.gz MD5 mismatch: {ar.md5_file(a4_rows_path)}')
stageA5.py:626:        _argv=sys.argv,
stageA5.py:627:        _config=dict(
stageA5.py:628:            python_executable=sys.executable,
stageA5.py:835:        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
stageA5.py:867:    print(sys.executable, flush=True)
stageA5.py:868:    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
stageA5.py:869:        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
stageA5.py:883:    if gate['_config']['own_md5'] != live_own:
stageA5.py:885:    if gate['_config']['stageA_py_md5'] != ar.md5_file(HERE / 'stageA.py') or gate['_config']['stageA4_py_md5'] != ar.md5_file(HERE / 'stageA4.py'):
stageA5.py:895:    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
stageA5.py:897:        raise RuntimeError('stageA4 rows.jsonl.gz MD5 mismatch')
stageA5.py:945:        out_dir / 'REMOTE_ROWS_MD5.txt',
stageA5.py:959:        _argv=sys.argv,
stageA5.py:960:        _config=dict(
stageA5.py:962:            python_executable=sys.executable,
52:- **自助法**：物理帧配对重采样（`2,000` 次，**`seed = 20261125`**），联合重采样 `stageA`、`stageA2`、`stageA3`、`sameframe_hg` Part 1 与本实验 Part A；取 **95% 百分位区间**（`[2.5, 97.5]`；若出现截断抽样则用保守最近秩界并汇报 `censored_draw_fraction`）。

 succeeded in 0ms:
    42	
    43	# --- frozen constants (protocol.md section 3.1 and amendment A1) ------------------------------------------------
    44	# New 256-bit OS entropy (os.urandom(32).hex(), generated 2026-10-15 before any P1 data); never used by an earlier stream.
    45	ENTROPY_HEX = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
    46	DOMAIN = 0x54435246  # "TCRF"; distinct from HRLD 0x48524C44, CLUS 0x434C5553, CSTA 0x43535441, GEOM 0x47454F4D and every [20260920, ...] stream
    47	COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
    48	STREAM_ALGORITHM = ('numpy.SeedSequence(8 entropy uint32 words, TCRF domain, frame, component); NOT keyed by rho, snr or scenario')
    49	SCENARIOS = {'U': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='uwa', fix_energy=True),
    50	             'G': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='geometric', fix_energy=True)}
    51	ALL_ARMS = ('F0', 'B', 'LOCAL', 'C', 'D', 'A3')
    52	DEFAULT_RHO = '0.3,0.5'
    53	DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
    54	RECEIVER_CONFIG = dict(
    55	    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
    56	    B='F0 + run_validation._branch CSTATE20 iff F0 final syndrome != 0 (F0 prefix included in B seconds)',
   163	
   164	
   165	def draw_paths(system, rs, flags):
   166	    """Copy of generate_uwa_channel (afdm_env.py:285-359) with the D1/D2 options.
   167	
   168	    Returns the accepted draw plus ``attempts`` (1 = accepted immediately).  Flags off: loop of at most
   169	    ``uwa_resample_max_tries`` attempts against the stale cap, then the frozen clip fallback.  D1: loop until
   170	    the largest delay bin is <= flags.trunc_bin (102 by default; 25 in scenario S; no clip fallback).
   171	    """
   172	    grid = effective_grid(system, flags)
   173	    ts = grid['ts']
   174	    if flags.fix_delay_cap:
   175	        if int(system.l_max_cap) != RECEIVER_BANK_MAX_DELAY:
   176	            raise AssertionError('system.l_max_cap differs from the receiver bank maximum')
   177	        for attempt in range(1, MAX_REDRAWS_FIXED + 1):
   178	            d = one_attempt(system, rs, flags)
   179	            if delay_bins(system, d['delay_idx_bar'], flags, clip=False).max() <= flags.trunc_bin:
   180	                d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=attempt, fallback=False)
   181	                return d
   182	        raise RuntimeError('D1 redraw did not terminate')
   183	    max_supported = grid['cap_idx_frozen']
   184	    tries = int(system.uwa_resample_max_tries)
   185	    for attempt in range(1, tries + 1):
   186	        d = one_attempt(system, rs, flags)
   187	        if np.max(d['delay_idx_bar']) <= max_supported:
   188	            d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=attempt, fallback=False)
   189	            return d
   190	    d['delay_idx_bar'] = np.minimum(d['delay_idx_bar'], max_supported)  # frozen clip fallback (afdm_env.py:353-359)
   191	    d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=tries, fallback=True)
   192	    return d
   193	
   194	
   195	def doppler_k_real(system, doppler_a, flags, geo_rng):
   780	                    mean=float(v.mean()),
   781	                    median=float(np.median(v)),
   782	                    ci95=ci,
   783	                    outlier_gt_0p25_frac=float(O[ei, ri, si].mean()),
   784	                )
   785	
   866	def cmd_run(args):
   867	    print(sys.executable, flush=True)
   868	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   869	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   870	    ar.check_thread_env()
   871	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   872	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   873	    if not 1 <= args.workers <= 32:
   874	        raise ValueError('workers must be in 1..32')
   875	
   876	    gate_path = args.gate.resolve()
   877	    gate_bytes = gate_path.read_bytes()
   878	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   879	    gate = json.loads(gate_bytes.decode('utf-8'))
   880	    if not gate.get('all_passed') or not gate.get('selected'):
   881	        raise RuntimeError('Refusing to run without passing stageA5_gate.json')
   882	    live_own = own_md5()
   883	    if gate['_config']['own_md5'] != live_own:
   884	        raise RuntimeError('gate.json own_md5 mismatch; re-run gates')
   885	    if gate['_config']['stageA_py_md5'] != ar.md5_file(HERE / 'stageA.py') or gate['_config']['stageA4_py_md5'] != ar.md5_file(HERE / 'stageA4.py'):
   886	        raise RuntimeError('Reused stageA/stageA4 MD5 mismatch vs gate.json')
   887	
   888	    snrs = tuple(int(s) for s in gate['selected']['snrs'])
   889	    out_dir = args.out.resolve()
   890	    raw_dir = out_dir / 'raw'
   891	    raw_dir.mkdir(parents=True, exist_ok=True)
   892	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   893	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   894	
   895	    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
   896	    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
   897	        raise RuntimeError('stageA4 rows.jsonl.gz MD5 mismatch')
   910	            p.start()
   911	            running[p.sentinel] = (idx, p)
   912	        while running:
   913	            ready = wait(running, timeout=10.0)
   914	            for r in ready:
   915	                idx, p = running.pop(r)
   916	                p.join()
   917	                code = p.exitcode
   918	                p.close()
   919	                if code != 0:
   920	                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
   921	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   922	            if live_cpu >= BUDGET_CAP_SEC - 180.0:
   923	                budget_hit = True
   924	                break
   925	    finally:
   926	        for _, p in running.values():
   927	            p.terminate()
   928	        for _, p in running.values():
   929	            p.join()
   930	            p.close()
   931	    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
   932	        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   933	        sys.exit(BUDGET_EXIT_CODE)
   934	
   935	    # Merge shard MD5s and load all rows
   936	    raw_md5 = {}
   937	    rows = []
   938	    for idx in range(n_shards):
   939	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
   940	        raw_md5[sp.name] = ar.md5_file(sp)
   941	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   942	            for line in fh:
   943	                rows.append(json.loads(line))
   944	    ar.atomic_write_text(
   945	        out_dir / 'REMOTE_ROWS_MD5.txt',
   946	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
   947	    )
   948	
   949	    a4_rows = [json.loads(ln) for ln in gzip.open(a4_rows_path, 'rt', encoding='utf-8')]
   950	    a3_actual = json.loads((HERE / 'out' / 'stageA3' / 'results.json').read_text(encoding='utf-8'))['r0_doppler_err_snr4_5']['delay']
   951	    analysis = analyze_stageA5(rows, a4_rows, snrs, a3_actual)
   952	
   953	    total_cpu_h = _used_cpu_seconds() / 3600.0
   954	    if total_cpu_h >= BUDGET_CAP_HOURS:
   955	        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
   956	        sys.exit(BUDGET_EXIT_CODE)
   957	
    15	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
    16	
    17	LOCKDIR="$OUT/.lock"
    18	if ! mkdir "$LOCKDIR" 2>/dev/null; then
    19	    echo "ERROR: lock $LOCKDIR already held" >&2
    20	    exit 1
    21	fi
    22	
    23	cd "$REPO"
    24	set +u
    25	source /opt/anaconda3/etc/profile.d/conda.sh
    26	conda activate AFDM
    27	set -u
    28	
    29	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    30	if [ "$(which python)" != "$PY" ]; then
    31	    rmdir "$LOCKDIR" 2>/dev/null || true
    62	    status=STOPPED
    63	    cleanup() {
    64	        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    65	        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    66	        rmdir "$LOCKDIR" 2>/dev/null || true
    67	    }
    68	    trap cleanup EXIT
    69	
    70	    # Python enforces cumulative CPU <= 6.0 core-hours; wall cap 1800s outer safety net
    71	    set +e
    72	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/run_cpu.txt" \
    73	        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/stageA5.py" \
    74	        run --gate "$GATE_JSON" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    75	        > "$OUT/run.log" 2>&1
    76	    rc=$?
    77	    set -e
    78	    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    79	        status=STOPPED_BUDGET
    80	        exit 124
    81	    fi
    82	    if [ "$rc" -ne 0 ]; then
    83	        exit "$rc"
    84	    fi
    85	    test -s "$OUT/results.json"
    86	    test -s "$OUT/RESULTS.md"
    87	    status=DONE
    88	    exit 0

codex
**发车前要修两处会改变实验结论的问题：主判读的重采样单位，以及纯导频和已知数据估计器实际执行的搜索目标。**

1. **主判读应按 100 个物理帧重采样。** 同一帧的 U/G 两个场景共用信道、数据和噪声的随机种子，当前实现却独立抽取 200 个 `(frame, scenario)` 行。冻结前应改为每次按帧抽样，同时保留 U/G 和两档导频比例。4 dB 下先求两档均值再取较小值、2,000 次重采样、种子 `20261125` 和 `0.08` 的判定边界均符合协议。与 A4 的 Cramér–Rao 界（CRB）效率比也按同键计算。 [随机种子](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_driver.py:43) · [主判读](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:752)
2. **纯导频（PW）和已知数据（KD）的搜索目标与协议不同。** 代码对每个候选多普勒重新拟合全部增益，而协议写的是用固定的最小二乘增益评分。冻结前统一两者。信道矩阵、快速协方差、逐径负对数似然和固定协方差下的广义最小二乘更新推导一致。主跑只把真时延交给估计器，真增益和真多普勒用于评分。功率加权、`0.375` 截顶和严格 `> 0.25` 的离群条件正确。 [搜索实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:253)
3. **G2 用错帧，运行限额也有缺口。** G2 使用 `41200`，协议指定 `41000`。12 dB、100 次独立加噪和中位数区间 `[0.7, 1.5]` 正确。G1、G3 与协议一致，G4 也按 `×1.3`、6 核时优先选三档。但主跑每 10 秒查一次 CPU，24 个进程在两次检查间最多消耗约 240 核秒，超过预留的 180 核秒。应缩短检查间隔或扩大预留。 [G2](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:560) · [预算检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:912)
4. **落盘和冻结追踪需对齐。** 启动脚本配置了 AFDM 环境、六个单线程变量、禁用 CUDA、指定临时目录和进程上限。进程间传输走文件和管道，静态未见 `/dev/shm` 写入路径。主要产物原子写入，门槛和结果均含 `_argv`、`_config`。实际只写分片，协议指定的合并归档不会生成。冻结提交号也只校验格式，应核对提交内容。 [落盘实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:935) · [冻结提交校验](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:866)

本次仅做静态审查。本地未找到 `stageA5_gate.json`，各门槛的实际通过情况尚未验证。

VERDICT: FIX
hook: Stop
hook: Stop Completed
tokens used
98,717
**发车前要修两处会改变实验结论的问题：主判读的重采样单位，以及纯导频和已知数据估计器实际执行的搜索目标。**

1. **主判读应按 100 个物理帧重采样。** 同一帧的 U/G 两个场景共用信道、数据和噪声的随机种子，当前实现却独立抽取 200 个 `(frame, scenario)` 行。冻结前应改为每次按帧抽样，同时保留 U/G 和两档导频比例。4 dB 下先求两档均值再取较小值、2,000 次重采样、种子 `20261125` 和 `0.08` 的判定边界均符合协议。与 A4 的 Cramér–Rao 界（CRB）效率比也按同键计算。 [随机种子](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_driver.py:43) · [主判读](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:752)
2. **纯导频（PW）和已知数据（KD）的搜索目标与协议不同。** 代码对每个候选多普勒重新拟合全部增益，而协议写的是用固定的最小二乘增益评分。冻结前统一两者。信道矩阵、快速协方差、逐径负对数似然和固定协方差下的广义最小二乘更新推导一致。主跑只把真时延交给估计器，真增益和真多普勒用于评分。功率加权、`0.375` 截顶和严格 `> 0.25` 的离群条件正确。 [搜索实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:253)
3. **G2 用错帧，运行限额也有缺口。** G2 使用 `41200`，协议指定 `41000`。12 dB、100 次独立加噪和中位数区间 `[0.7, 1.5]` 正确。G1、G3 与协议一致，G4 也按 `×1.3`、6 核时优先选三档。但主跑每 10 秒查一次 CPU，24 个进程在两次检查间最多消耗约 240 核秒，超过预留的 180 核秒。应缩短检查间隔或扩大预留。 [G2](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:560) · [预算检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:912)
4. **落盘和冻结追踪需对齐。** 启动脚本配置了 AFDM 环境、六个单线程变量、禁用 CUDA、指定临时目录和进程上限。进程间传输走文件和管道，静态未见 `/dev/shm` 写入路径。主要产物原子写入，门槛和结果均含 `_argv`、`_config`。实际只写分片，协议指定的合并归档不会生成。冻结提交号也只校验格式，应核对提交内容。 [落盘实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:935) · [冻结提交校验](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py:866)

本次仅做静态审查。本地未找到 `stageA5_gate.json`，各门槛的实际通过情况尚未验证。

VERDICT: FIX
