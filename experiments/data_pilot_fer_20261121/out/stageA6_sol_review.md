OpenAI Codex v0.170.0
--------
workdir: /tmp
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a210ae-8534-7111-a142-94f94cefdf03
--------
user
You are Sol performing a concise (<= 3 min) pre-launch static review of Stage A6 in `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/`:
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA6_PROTOCOL.md`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/test_stageA6.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6_launch.sh`

Check specifically:
1. Single-factor arm exactness vs `stageA3.one_arm` / `stageA2.f0_true(..., 'ls')`:
   - `SBdop` and `PWdop` inject `nu_hat` into `pert['k_real']` (true delays only, no truth peeking for `g_i` or `k_real`), gains stay pilot LS via `stageA2.f0_true`, `run_branch(..., 'A1')` on `syndrome != 0`, score against real `truth`.
2. Gates G1–G3 (`out/stageA6_gate.json`):
   - G1: `nu_hat = truth['k_real']` reproduces `stageA2` `ldop` (syndrome, F0 errors, final errors) on 4 keys.
   - G2: 4 keys from A5 (`41000-41099`, 4 dB, `rho .10/.15`) reproduce A5 `estimate_sb` raw `abs_err['SB']` & `metric['SB']` within `1e-6`.
   - G3: stratified cost `x1.3 <= 40.0` core-hours (`<= 32` workers), drop SNR `550` first, then `200`, record selection.
3. Frozen readout & archive verification:
   - `stageA2.crossing` at 1% FER U/G mean; `D = min_{rho in {100..250}} CD2 - min_{rho in {100,150}} SBdop`; joint paired physical-frame bootstrap exact match to `sameframe_cd2.analyze_partA` (2000 draws, seed `20261125`, 95% CI, censored bounds); `GO` if CI lower `>= 0.5`, `STOP` if CI upper `< 0.3`, else `ERIC`.
   - Archive MD5 & manifest SHA-256 verification for `stageA`, `stageA2`, `stageA3`, `stageA5`, `sameframe_cd2`; no rerunning archived arms.
   - Descriptive diagnostics: per-rho crossings, contrasts (`SBdop - s050`, `SBdop - ldop`, `CD2 - PWdop`), round-0 Doppler metric per SNR vs A5, F0-failure weak-path outlier (`> 0.25` bin) share, per-key SB CPU time.
4. deinlab safety (`AFDM` env, 6 thread vars = 1, `CUDA_VISIBLE_DEVICES=""`, `<= 32` workers, `/data/guoyikun/tmp`, zero `/tmp`/`/dev/shm`, atomic writes, CPU budget stop margin) and any bugs or edge cases.

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

我会用 `research-checkpoint` 做启动前静态审查，先核对实验协议和代码，再对照历史实现、归档校验和启动脚本。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba stageA6_launch.sh; nl -ba STAGEA6_PROTOCOL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
exec
/bin/zsh -lc 'cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md; pwd; ls -a' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
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
/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
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
STAGEA5_READOUT.md
STAGEA6_PROTOCOL.md
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
stageA6.py
stageA6_launch.sh
test_stageA5.py
test_stageA6.py

 succeeded in 0ms:
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
    13	OUT="$HERE/out/stageA6"
    14	GATE_JSON="$HERE/out/stageA6_gate.json"
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
    50	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/stageA6.py" \
    51	        gate --out "$GATE_JSON" --workers 28 \
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
    70	    # Python enforces cumulative CPU <= 40.0 core-hours; wall cap 7200s outer safety net
    71	    set +e
    72	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/run_cpu.txt" \
    73	        timeout --kill-after=5s 7200s "$PY" -B -u "$HERE/stageA6.py" \
    74	        run --gate "$GATE_JSON" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 32 \
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
     1	# 阶段 A6：半盲第 0 轮多普勒估计的端到端 FER 天花板检验——协议（`STAGEA6_PROTOCOL.md`）
     2	
     3	**状态**：冻结前稿（待 Sol 静态审查及 G1–G3 门控通过后冻结提交 `Before data-pilot-fer stage A6 ...`）
     4	**承接**：
     5	- [STAGEA5_READOUT.md](STAGEA5_READOUT.md)：给定真时延时，半盲高斯 ML 估计器 `SB` 在 4 dB、$\rho \in \{0.10, 0.15\}$ 达到 `0.0527 / 0.0430` bin（`PASS`），但存在弱径离群尾（`23.3% / 18.6%` 路径 $> 0.25$ bin）。
     6	- [sameframe_cd2_20261125/READOUT.md](../sameframe_cd2_20261125/READOUT.md)：在帧 `41000–41399` 上，基线 `CD2` 最优 1% FER 交叉点为 `4.4156 dB`（$\rho=.20$），对照 `s050 = 3.4559 dB`、`s100 = 3.8391 dB`、`ldop = 3.4518 dB`（均在 $\rho=.10$）。
     7	
     8	---
     9	
    10	## 1. 核心问题
    11	
    12	在**已知真时延** $l_i$ 且第 0 轮多普勒采用 Stage A5 半盲高斯 ML 估计 `SB` 的条件下，端到端接收机（`SBdop`）在相同帧 `41000–41399`（U/G 均值）的 **1% info-FER 交叉点**能领先现行最强基线 `CD2` 多少 dB？
    13	
    14	---
    15	
    16	## 2. 实验臂（相对 Stage A3 的单因素改动，不修改任何冻结文件）
    17	
    18	精确复用 `stageA3.one_arm` 的接收机链路，唯一改动是将注入给 `stageA2.f0_true(C, obs, pert, 'ls')` 的 `pert['k_real']` 从 `truth + sigma*z` 替换为该键实测的连续多普勒估计 $\hat{\nu}$；复增益保持 `stageA2.f0_true(..., 'ls')` 的导频最小二乘解；若 F0 校验子非零（`syndrome != 0`），按 `stageA3` 完全一致调用 `stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')`；全部译码错误均对照真实 `truth` 计分。
    19	
    20	1. **`SBdop`（主臂）**：$\hat{\nu} = \text{stageA5.estimate\_sb}$ （从该键的 `stageA5.estimate_pw` 初值出发，输入为该键原始 `raw['y']`、`raw['pilot']`、`raw['data']` 方差 $v_d$、`raw['sigma2']` 与真时延 `truth['l_i']`，绝不使用真多普勒或真增益）。
    21	2. **`PWdop`（诊断臂）**：$\hat{\nu} = \text{stageA5.estimate\_pw}$ （仅真时延 + 连续导频变量投影 LS，用于拆分"真时延 + 连续导频 LS"本身与"半盲协方差项"各自贡献的 FER 增益）。
    22	
    23	---
    24	
    25	## 3. 数据网格与归档复用
    26	
    27	- **新跑网格**：帧 `41000–41399`（400 物理帧）× 场景 `U/G` × $\rho \in \{100, 150\}$ permille × 初始候选 SNR `{200, 250, 300, 400, 450, 500, 550}`（2.0–5.5 dB，7 档）。
    28	- **预算与逐级降档规则（G3 门控执行）**：总 CPU 预算上限 **`40.0` 核时**（按实测分层耗时 × `1.3` 外推），工作进程 `<= 32`（固定 `32`）。按顺序尝试：
    29	  1. 全部 7 档 `(200, 250, 300, 400, 450, 500, 550)`；
    30	  2. 若超 `40.0` 核时，先删 `550` → 6 档 `(200, 250, 300, 400, 450, 500)`；
    31	  3. 若仍超 `40.0` 核时，再删 `200` → 5 档 `(250, 300, 400, 450, 500)`；
    32	  4. 若仍超则停机汇报。选定网格写入 `out/stageA6_gate.json` 并于冻结前记录。
    33	- **不重跑已归档对照组**：`CD2`、`s050`、`s100`、`ldop`（及 `full`）直接读取 deinlab 上已冻结的 `sameframe_cd2_20261125`、`stageA`、`stageA2`、`stageA3` 原始分片，并在门控与读出阶段逐一核验其 `REMOTE_ROWS_MD5.txt` 清单 SHA-256 及每个分片文件的 MD5。
    34	
    35	---
    36	
    37	## 4. 门禁 G1–G3（`out/stageA6_gate.json`，全部通过方可启动主跑）
    38	
    39	- **G1（`ldop` 精确复现）**：4 个来自 `stageA2` 的键上，令 $\hat{\nu} = \text{truth['k\_real']}$，`one_arm_nu` 的 `syndrome`、`f0_errors`、`errors` 与归档 `stageA2` 的 `ldop` 臂逐位完全一致（4/4）。
    40	- **G2（`stageA5` 估计复现）**：4 个来自 `stageA5` 的键（`frames 41000–41099`, 4 dB, $\rho \in \{.10, .15\}$）上，调用 `stageA5.estimate_sb` 所得逐径 $|\hat{\nu}_i - \nu_i|$（及功率加权指标）与 `stageA5` 远端原始行 `abs_err['SB']` 的最大绝对差 `< 1e-6`（注：`stageA5` 原始行落盘了全部 8 径的精确 `abs_err['SB']` 与 `metric['SB']`）。
    41	- **G3（分层成本外推 ×1.3，$\le 40.0$ 核时，$\le 32$ 进程）**：在隔离帧 `41400–41403` 上对全部 7 个 SNR 各测 4 键（覆盖 `U/G` × `rho 100/150`，共 28 键），按各 SNR 实测均值外推全网耗时 × `1.3`（加 `0.15` 核时 IO/分析余量），按 §3 降档规则选定符合 `<= 40.0` 核时的 SNR 网格。
    42	
    43	---
    44	
    45	## 5. 冻结判读规则（跑后永不改标）
    46	
    47	- **交叉点定义**：`stageA2.crossing`（1% info-FER，log10 线性插值），U/G 等权平均；含截尾保守上下界处理（完全复用 `sameframe_cd2.analyze_partA` 与 `sameframe.crossing_bounds_stageA2`）。
    48	- **主估计量**：
    49	  $$D = \min_{\rho \in \{100,150,200,250\}} C_{\mathrm{CD2}}(\rho) \;-\; \min_{\rho \in \{100,150\}} C_{\mathrm{SBdop}}(\rho)$$
    50	- **联合配对自助法**：按 400 个物理帧（`41000–41399`）联合重采样（`2,000` 次，`seed = 20261125`），与 `sameframe_cd2.analyze_partA` 权重矩阵生成序列完全一致，取 95% 百分位区间（截尾时用保守秩次区间）。
    51	- **唯一互斥判定表**：
    52	  - **`GO`**：95% CI 下界 $\ge 0.5\text{ dB}$（下一步：放开未知时延）
    53	  - **`STOP`**：95% CI 上界 $< 0.3\text{ dB}$（终止第 0 轮多普勒线，转写论文）
    54	  - **`ERIC`**：其余情况（交由 Eric 裁决）
    55	- **描述性次要读数**：
    56	  1. `SBdop`、`PWdop` 各 $\rho$ 的 U/G 与均值 1% FER 交叉点；
    57	  2. 带 95% CI 的对照差值：`SBdop − s050`、`SBdop − ldop`、`CD2 − PWdop`（及 `PWdop − SBdop`）；
    58	  3. `SBdop`（与 `PWdop`）在各 SNR 下的第 0 轮多普勒误差（及 4 dB 下对 `41000–41099` 200 抽样子集与 Stage A5 的一致性核对）；
    59	  4. `SBdop` 的 F0 失败键中存在离群路径（$> 0.25$ bin）的占比（分别报告：任意径离群、弱径离群（功率低于中位数）、仅弱径离群、强径离群，并与 F0 成功键对照）；
    60	  5. 单键 `SB`（及 `PW`）CPU 耗时均值/中位/p95。
    61	
    62	---
    63	
    64	## 6. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）
    65	
    66	- **Claude**：
    67	  - `A6-C1`（主判定）：`GO` .45 / `ERIC` .45 / `STOP` .10
    68	  - `A6-C2`（交叉点）：`SBdop` 最优 1% FER 交叉点落在 `[3.50, 3.80] dB`：.55
    69	- **agy（Gemini 4 Neon）**：
    70	  - `A6-G1`（主判定）：`GO` .50 / `ERIC` .42 / `STOP` .08
    71	  - `A6-G2`（交叉点）：`SBdop` 最优 1% FER 交叉点落在 `[3.50, 3.80] dB`：.60
    72	
    73	---
    74	
    75	## 7. deinlab 执行规范
    76	
    77	- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，日志首行打印 `sys.executable`）。
    78	- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp`、`/dev/shm` 或 `/home/guoyikun`；`tmux` 会话名 `g_a6`；工作进程 `32`。
    79	- 原始逐键分片（`out/stageA6/raw/rows_shard*.jsonl.gz`）留远端并记录 MD5 到 `out/stageA6/REMOTE_ROWS_MD5.txt`；本地回传 `out/stageA6_gate.json`、`out/stageA6/{results.json,RESULTS.md,REMOTE_ROWS_MD5.txt,STATUS,run.log,run_cpu.txt}`。

exec
/bin/zsh -lc "wc -l STAGEA6_PROTOCOL.md stageA6.py test_stageA6.py stageA6_launch.sh; rg -n '"'^(def |class |#)'"' stageA6.py test_stageA6.py STAGEA6_PROTOCOL.md; ls -a ../.." in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
      79 STAGEA6_PROTOCOL.md
    1053 stageA6.py
     112 test_stageA6.py
      93 stageA6_launch.sh
    1337 total
test_stageA6.py:16:def test_verdict_boundaries():
test_stageA6.py:27:def test_joint_bootstrap_and_contrasts():
test_stageA6.py:70:def test_outlier_diagnostics():
STAGEA6_PROTOCOL.md:1:# 阶段 A6：半盲第 0 轮多普勒估计的端到端 FER 天花板检验——协议（`STAGEA6_PROTOCOL.md`）
STAGEA6_PROTOCOL.md:10:## 1. 核心问题
STAGEA6_PROTOCOL.md:16:## 2. 实验臂（相对 Stage A3 的单因素改动，不修改任何冻结文件）
STAGEA6_PROTOCOL.md:25:## 3. 数据网格与归档复用
STAGEA6_PROTOCOL.md:37:## 4. 门禁 G1–G3（`out/stageA6_gate.json`，全部通过方可启动主跑）
STAGEA6_PROTOCOL.md:45:## 5. 冻结判读规则（跑后永不改标）
STAGEA6_PROTOCOL.md:64:## 6. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）
STAGEA6_PROTOCOL.md:75:## 7. deinlab 执行规范
stageA6.py:120:def own_md5() -> dict[str, str]:
stageA6.py:124:def verify_pinned_code() -> dict[str, str]:
stageA6.py:134:def verify_archive(name: str) -> dict[str, str]:
stageA6.py:157:def verify_all_archives(names: tuple[str, ...]) -> dict[str, dict[str, str]]:
stageA6.py:161:def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
stageA6.py:192:def _used_cpu_seconds() -> float:
stageA6.py:197:def _active_pids_cpu(pids: list[int]) -> float:
stageA6.py:209:# --------------------------------------------------------------------------- Runtime & arm execution
stageA6.py:210:def _load_runtime():
stageA6.py:221:def one_arm_nu(C, stageA, stageA2, obs, truth, nu_hat: np.ndarray) -> dict[str, Any]:
stageA6.py:249:def eval_key(C, stageA, stageA2, stageA5, daft, base, s: str, rho: int, snr: int, frame: int) -> dict[str, Any]:
stageA6.py:298:# --------------------------------------------------------------------------- File-IPC helper
stageA6.py:299:def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
stageA6.py:325:# --------------------------------------------------------------------------- Gates G1-G3
stageA6.py:326:def _g3_cost_worker(in_path: str, out_path: str):
stageA6.py:346:def cmd_gate(args):
stageA6.py:506:# --------------------------------------------------------------------------- Main worker & readout
stageA6.py:507:def _run_shard_worker(shard_idx: int, frames: tuple[int, ...], snrs: tuple[int, ...], raw_dir: Path):
stageA6.py:531:def verdict_a6(ci_lo: float, ci_hi: float) -> str:
stageA6.py:539:def _to_float_bound(val: Any) -> float:
stageA6.py:549:def analyze_stageA6(
stageA6.py:673:def summarize_diagnostics(rows: list[dict[str, Any]], snrs: tuple[int, ...]) -> dict[str, Any]:
stageA6.py:772:def render_results_md(res: dict[str, Any]) -> str:
stageA6.py:845:def _load_cd2_fail_grid() -> np.ndarray:
stageA6.py:871:def cmd_run(args):
stageA6.py:1035:def main():
.
..
.DS_Store
.agents
.aris
.claude
.codex
.commandcode
.devin
.gitattributes
.gitignore
.mission
.mypy_cache
.obsidian
.pytest_cache
.ruff_cache
.trellis
.vscode
AFDM_UWA_acoustic.m
AFDM_claim_audit_bundle_20260726.zip
AGENTS.md
CLAUDE.md
DERIVATION_PACKAGE.md
FROZEN_DEPENDENCIES.md
Final Report Template-and-requirements
README.md
STATE-history.md
STATE.md
_archive
_claim_audit_bundle_20260726
_claim_audit_bundle_v2
afdm_sp_joint_unrolled
ana-html
experiments
figures
frozen-i1-smoke-fixture-v1.json
fyp_new_short
ideas
issues
learning
legacy_for_ablation
matlab
novelty
oracle_io
paper
paper-tmlcn
paper_figure_code
papers
pelican-bike.html
refer_paper
requirements.txt
research-assets
results
review-stage
run_frozen_i1_smoke.py
standalone
tcom_plan
tests
tools

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA6.py | sed -n '346,672p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   346	def cmd_gate(args):
   347	    print(sys.executable, flush=True)
   348	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   349	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   350	    thread_env = ar.check_thread_env()
   351	    if not 1 <= args.workers <= 32:
   352	        raise ValueError('workers must be in 1..32')
   353	    started = time.monotonic()
   354	
   355	    gate_path = args.out.resolve()
   356	    gate_path.parent.mkdir(parents=True, exist_ok=True)
   357	    if gate_path.exists():
   358	        gate_path.unlink()
   359	
   360	    pinned_md5 = verify_pinned_code()
   361	    manifests = verify_all_archives(('stageA', 'stageA2', 'stageA3', 'stageA5', 'sameframe_cd2'))
   362	    C, stageA, stageA2, stageA5, daft = _load_runtime()
   363	    st, ctx = C['stage3'], C['ctx']
   364	    c1, c2 = ctx.system.c1, ctx.system.c2
   365	
   366	    # G1: nu_hat = truth['k_real'] reproduces archived stageA2 'ldop' exactly on 4 keys
   367	    a2_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   368	    with gzip.open(HERE / 'out' / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt', encoding='utf-8') as fh:
   369	        for line in fh:
   370	            r = json.loads(line)
   371	            a2_rows[(r['scenario'], int(r['rho']), int(r['snr']), int(r['frame']))] = r
   372	    g1_keys = (('U', 100, 300, 41000), ('G', 150, 400, 41001), ('U', 150, 450, 41002), ('G', 100, 500, 41003))
   373	    g1_rows = []
   374	    for s, rho, snr, frame in g1_keys:
   375	        base = st.inputs(ctx, frame, s, rho)
   376	        _, obs, truth = st.observed(ctx, base, rho, snr)
   377	        rec = one_arm_nu(C, stageA, stageA2, obs, truth, np.asarray(truth['k_real'], dtype=np.float64))
   378	        ref = a2_rows[(s, rho, snr, frame)]['arms']['ldop']
   379	        ok = all(int(rec[k]) == int(ref[k]) for k in ('syndrome', 'f0_errors', 'errors'))
   380	        g1_rows.append(dict(
   381	            key=[s, rho, snr, frame],
   382	            passed=bool(ok),
   383	            got={k: int(rec[k]) for k in ('syndrome', 'f0_errors', 'errors')},
   384	            ref={k: int(ref[k]) for k in ('syndrome', 'f0_errors', 'errors')},
   385	        ))
   386	    g1_pass = bool(len(g1_rows) == 4 and all(x['passed'] for x in g1_rows))
   387	    print(f'G1 {"PASS" if g1_pass else "FAIL"} ({sum(x["passed"] for x in g1_rows)}/4 exact ldop replay)', flush=True)
   388	
   389	    # G2: 4 keys from A5 (frames 41000-41099, 4 dB, rho .10/.15) reproduce A5 raw abs_err['SB'] & metric['SB'] within 1e-6
   390	    g2_targets = {(41000, 'U', 100, 400), (41001, 'G', 150, 400), (41002, 'U', 150, 400), (41003, 'G', 100, 400)}
   391	    a5_ref: dict[tuple[int, str, int, int], dict[str, Any]] = {}
   392	    for sp in sorted((HERE / 'out' / 'stageA5' / 'raw').glob('rows_shard*.jsonl.gz')):
   393	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   394	            for line in fh:
   395	                r = json.loads(line)
   396	                k = (int(r['frame']), r['scenario'], int(r['rho']), int(r['snr']))
   397	                if k in g2_targets:
   398	                    a5_ref[k] = r
   399	        if len(a5_ref) == len(g2_targets):
   400	            break
   401	    if len(a5_ref) != len(g2_targets):
   402	        raise RuntimeError(f'Missing G2 keys in stageA5 archive: found {sorted(a5_ref)}')
   403	
   404	    g2_rows = []
   405	    for frame, s, rho, snr in sorted(g2_targets):
   406	        base = st.inputs(ctx, frame, s, rho)
   407	        raw, _, truth = st.observed(ctx, base, rho, snr)
   408	        y = np.asarray(raw['y'], dtype=np.complex128)
   409	        p = np.asarray(raw['pilot'], dtype=np.complex128)
   410	        d = np.asarray(raw['data'], dtype=np.complex128)
   411	        r_td = daft(y, c1, c2, True)
   412	        p_t = daft(p, c1, c2, True)
   413	        geom = stageA5.precompute_delay_geometry(truth['l_i'], len(y), c1)
   414	        nu_pw, g_pw = stageA5.estimate_pw(geom, p_t, r_td)
   415	        nu_sb, _ = stageA5.estimate_sb(geom, p_t, r_td, float(np.mean(np.abs(d) ** 2)), float(raw['sigma2']), nu_pw, g_pw)
   416	        m_sb, _, e_sb = stageA5.doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   417	        ref = a5_ref[(frame, s, rho, snr)]
   418	        max_abs_diff = float(np.max(np.abs(np.asarray(e_sb) - np.asarray(ref['abs_err']['SB']))))
   419	        metric_diff = float(abs(m_sb - float(ref['metric']['SB'])))
   420	        ok = bool(max_abs_diff < 1e-6 and metric_diff < 1e-6)
   421	        g2_rows.append(dict(
   422	            key=[frame, s, rho, snr],
   423	            passed=ok,
   424	            max_abs_err_diff=max_abs_diff,
   425	            metric_diff=metric_diff,
   426	        ))
   427	    g2_pass = bool(len(g2_rows) == 4 and all(x['passed'] for x in g2_rows))
   428	    print(f'G2 {"PASS" if g2_pass else "FAIL"} max_diff={max(x["max_abs_err_diff"] for x in g2_rows):.2e}', flush=True)
   429	
   430	    # G3: stratified cost projection across all 7 SNRs on isolated frames 41400-41403 (28 keys)
   431	    g3_jobs = []
   432	    for snr in FULL_SNRS:
   433	        g3_jobs.extend([
   434	            [41400, 'U', 100, snr],
   435	            [41401, 'G', 100, snr],
   436	            [41402, 'U', 150, snr],
   437	            [41403, 'G', 150, snr],
   438	        ])
   439	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   440	    ipc_dir = tmp_root / f'stageA6_gates_ipc_{os.getpid()}'
   441	    ipc_dir.mkdir(parents=True, exist_ok=True)
   442	    try:
   443	        print(f'Running G3 stratified cost benchmark ({len(g3_jobs)} keys across {len(FULL_SNRS)} SNRs)...', flush=True)
   444	        g3_samples = _spawn_map(_g3_cost_worker, g3_jobs, min(args.workers, len(g3_jobs)), ipc_dir, 'g3')
   445	    finally:
   446	        shutil.rmtree(ipc_dir, ignore_errors=True)
   447	
   448	    mean_cpu_by_snr = {
   449	        snr: float(np.mean([x['total_cpu'] for x in g3_samples if int(x['snr']) == snr]))
   450	        for snr in FULL_SNRS
   451	    }
   452	    mean_sb_by_snr = {
   453	        snr: float(np.mean([x['sb_cpu'] for x in g3_samples if int(x['snr']) == snr]))
   454	        for snr in FULL_SNRS
   455	    }
   456	    keys_per_snr = len(FRAMES) * len(SCENARIOS) * len(RHOS)  # 400 * 2 * 2 = 1600
   457	    candidates = []
   458	    for cand_snrs in CANDIDATE_SNRS:
   459	        raw_h = sum(mean_cpu_by_snr[s] * keys_per_snr for s in cand_snrs) / 3600.0 + OVERHEAD_HOURS
   460	        marg_h = raw_h * COST_MARGIN
   461	        candidates.append(dict(
   462	            snrs=list(cand_snrs),
   463	            dropped_snrs=[s for s in FULL_SNRS if s not in cand_snrs],
   464	            n_keys=keys_per_snr * len(cand_snrs),
   465	            raw_hours=raw_h,
   466	            projected_hours_with_margin=marg_h,
   467	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   468	        ))
   469	    selected = next((c for c in candidates if c['within_budget']), None)
   470	    g3_pass = selected is not None
   471	    all_passed = bool(g1_pass and g2_pass and g3_pass)
   472	    gate_cpu_h = _used_cpu_seconds() / 3600.0
   473	
   474	    payload = dict(
   475	        _argv=sys.argv,
   476	        _config=dict(
   477	            python_executable=sys.executable,
   478	            threads=thread_env,
   479	            workers=args.workers,
   480	            own_md5=own_md5(),
   481	            pinned_code_md5=pinned_md5,
   482	            archive_shards_verified={k: len(v) for k, v in manifests.items()},
   483	        ),
   484	        all_passed=all_passed,
   485	        selected=selected,
   486	        G1=dict(passed=g1_pass, rows=g1_rows),
   487	        G2=dict(passed=g2_pass, rows=g2_rows),
   488	        G3=dict(
   489	            passed=g3_pass,
   490	            budget_cap_core_hours=BUDGET_CAP_HOURS,
   491	            margin=COST_MARGIN,
   492	            overhead_hours=OVERHEAD_HOURS,
   493	            mean_total_cpu_sec_by_snr={str(k): v for k, v in mean_cpu_by_snr.items()},
   494	            mean_sb_cpu_sec_by_snr={str(k): v for k, v in mean_sb_by_snr.items()},
   495	            candidates=candidates,
   496	            samples=g3_samples,
   497	        ),
   498	        gate_cpu_hours=gate_cpu_h,
   499	        gate_wall_seconds=time.monotonic() - started,
   500	    )
   501	    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
   502	    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
   503	    sys.exit(0 if all_passed else 1)
   504	
   505	
   506	# --------------------------------------------------------------------------- Main worker & readout
   507	def _run_shard_worker(shard_idx: int, frames: tuple[int, ...], snrs: tuple[int, ...], raw_dir: Path):
   508	    C, stageA, stageA2, stageA5, daft = _load_runtime()
   509	    st, ctx = C['stage3'], C['ctx']
   510	    lines: list[str] = []
   511	    for frame in frames:
   512	        for s in SCENARIOS:
   513	            for rho in RHOS:
   514	                base = st.inputs(ctx, frame, s, rho)
   515	                for snr in snrs:
   516	                    row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
   517	                    lines.append(json.dumps(row, allow_nan=False) + '\n')
   518	
   519	    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
   520	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   521	    with part_path.open('wb') as raw_fh:
   522	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
   523	            for ln in lines:
   524	                gz.write(ln.encode('utf-8'))
   525	        raw_fh.flush()
   526	        os.fsync(raw_fh.fileno())
   527	    os.replace(part_path, final_path)
   528	    print(f'Shard {shard_idx:03d} done ({len(lines)} keys, {len(frames)} frames)', flush=True)
   529	
   530	
   531	def verdict_a6(ci_lo: float, ci_hi: float) -> str:
   532	    if ci_lo >= GO_THRESH_DB:
   533	        return 'GO'
   534	    if ci_hi < STOP_THRESH_DB:
   535	        return 'STOP'
   536	    return 'ERIC'
   537	
   538	
   539	def _to_float_bound(val: Any) -> float:
   540	    if isinstance(val, (int, float)):
   541	        return float(val)
   542	    if val == '-inf':
   543	        return -math.inf
   544	    if val == 'inf':
   545	        return math.inf
   546	    raise ValueError(f'Unexpected bound representation: {val!r}')
   547	
   548	
   549	def analyze_stageA6(
   550	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   551	    crossing_fn,
   552	    diagnostics: dict[str, Any],
   553	    *,
   554	    boot_draws: int = BOOT_DRAWS,
   555	    boot_seed: int = BOOT_SEED,
   556	) -> dict[str, Any]:
   557	    """Frozen Stage A6 readout with exact sameframe_cd2 joint paired physical-frame bootstrap."""
   558	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   559	    rng = np.random.default_rng(boot_seed)
   560	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   561	    weights[0] = 1.0 / n_frames
   562	    for b in range(1, boot_draws + 1):
   563	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   564	
   565	    arm_lo: dict[str, np.ndarray] = {}
   566	    arm_hi: dict[str, np.ndarray] = {}
   567	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   568	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   569	    arm_best_lo: dict[str, np.ndarray] = {}
   570	    arm_best_hi: dict[str, np.ndarray] = {}
   571	    arm_best_rho: dict[str, int] = {}
   572	
   573	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   574	        n_r = len(rhos)
   575	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   576	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   577	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   578	        scen_pt = {'U': {}, 'G': {}}
   579	        for ri, rho in enumerate(rhos):
   580	            for bi in range(boot_draws + 1):
   581	                u_lo, u_hi = sf.crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   582	                g_lo, g_hi = sf.crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   583	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   584	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   585	                if bi == 0:
   586	                    scen_pt['U'][str(rho)] = sf._rep(u_lo) if u_lo == u_hi else [sf._rep(u_lo), sf._rep(u_hi)]
   587	                    scen_pt['G'][str(rho)] = sf._rep(g_lo) if g_lo == g_hi else [sf._rep(g_lo), sf._rep(g_hi)]
   588	        arm_lo[arm] = lo_arr
   589	        arm_hi[arm] = hi_arr
   590	        arm_scen_pt[arm] = scen_pt
   591	        arm_mean_pt[arm] = {
   592	            str(rho): (sf._rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [sf._rep(lo_arr[0, ri]), sf._rep(hi_arr[0, ri])])
   593	            for ri, rho in enumerate(rhos)
   594	        }
   595	        if arm in ('full', 'ldop'):
   596	            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
   597	        else:
   598	            sub_idx = list(range(n_r))
   599	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   600	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   601	        arm_best_rho[arm] = int(rhos[sub_idx[int(np.argmin(hi_arr[0, sub_idx]))]])
   602	
   603	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   604	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   605	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   606	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   607	        if cens_frac == 0.0:
   608	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   609	        else:
   610	            lo = an._nearest_rank(d_lo[1:], 0.025)
   611	            hi = an._nearest_rank(d_hi[1:], 0.975)
   612	        pt = sf._rep(d_lo[0]) if d_lo[0] == d_hi[0] else [sf._rep(d_lo[0]), sf._rep(d_hi[0])]
   613	        return dict(
   614	            point_db=pt,
   615	            ci95_db=[sf._rep(lo), sf._rep(hi)],
   616	            censored_draw_fraction=cens_frac,
   617	            arm_a_best_db=sf._rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [sf._rep(arm_best_lo[arm_a][0]), sf._rep(arm_best_hi[arm_a][0])],
   618	            arm_a_best_rho=arm_best_rho[arm_a],
   619	            arm_b_best_db=sf._rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [sf._rep(arm_best_lo[arm_b][0]), sf._rep(arm_best_hi[arm_b][0])],
   620	            arm_b_best_rho=arm_best_rho[arm_b],
   621	        )
   622	
   623	    primary = contrast('CD2', 'SBdop')
   624	    lo_val = _to_float_bound(primary['ci95_db'][0])
   625	    hi_val = _to_float_bound(primary['ci95_db'][1])
   626	    primary['verdict'] = verdict_a6(lo_val, hi_val)
   627	    primary['go_threshold_db'] = GO_THRESH_DB
   628	    primary['stop_threshold_db'] = STOP_THRESH_DB
   629	
   630	    # Best crossing CIs for SBdop & PWdop
   631	    best_ci = {}
   632	    for arm in ('SBdop', 'PWdop', 'CD2', 's050', 's100', 'ldop'):
   633	        if arm not in arm_best_lo:
   634	            continue
   635	        blo, bhi = arm_best_lo[arm], arm_best_hi[arm]
   636	        cf = float(np.mean(~(np.isfinite(blo[1:]) & np.isfinite(bhi[1:]))))
   637	        if cf == 0.0:
   638	            c_lo, c_hi = (float(v) for v in np.percentile(blo[1:], [2.5, 97.5]))
   639	        else:
   640	            c_lo = an._nearest_rank(blo[1:], 0.025)
   641	            c_hi = an._nearest_rank(bhi[1:], 0.975)
   642	        best_ci[arm] = dict(
   643	            best_db=sf._rep(blo[0]) if blo[0] == bhi[0] else [sf._rep(blo[0]), sf._rep(bhi[0])],
   644	            best_rho=arm_best_rho[arm],
   645	            ci95_db=[sf._rep(c_lo), sf._rep(c_hi)],
   646	            censored_draw_fraction=cf,
   647	        )
   648	
   649	    secondary = {
   650	        'SBdop_minus_s050': contrast('SBdop', 's050'),
   651	        'SBdop_minus_ldop': contrast('SBdop', 'ldop'),
   652	        'CD2_minus_PWdop': contrast('CD2', 'PWdop'),
   653	        'PWdop_minus_SBdop': contrast('PWdop', 'SBdop'),
   654	        'SBdop_minus_s100': contrast('SBdop', 's100'),
   655	        'CD2_minus_s050': contrast('CD2', 's050'),
   656	        'CD2_minus_ldop': contrast('CD2', 'ldop'),
   657	    }
   658	
   659	    return dict(
   660	        frames=n_frames,
   661	        boot_draws=boot_draws,
   662	        boot_seed=boot_seed,
   663	        primary=primary,
   664	        best_crossings=best_ci,
   665	        secondary_contrasts=secondary,
   666	        mean_crossing=arm_mean_pt,
   667	        crossings_by_scenario=arm_scen_pt,
   668	        best_rho=arm_best_rho,
   669	        diagnostics=diagnostics,
   670	    )
   671	
   672	

exec
/bin/zsh -lc "nl -ba stageA6.py | sed -n '673,1060p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   673	def summarize_diagnostics(rows: list[dict[str, Any]], snrs: tuple[int, ...]) -> dict[str, Any]:
   674	    """Compute per-SNR Doppler error, A5 subset check, F0-failure outlier breakdown, and SB/PW timing."""
   675	    by_rho_snr: dict[str, dict[str, Any]] = {}
   676	    for rho in RHOS:
   677	        for snr in snrs:
   678	            sub = [r for r in rows if int(r['rho']) == rho and int(r['snr']) == snr]
   679	            sb_m = np.array([r['sb_metric'] for r in sub], dtype=np.float64)
   680	            pw_m = np.array([r['pw_metric'] for r in sub], dtype=np.float64)
   681	            sb_o = np.array([r['sb_outlier_frac'] for r in sub], dtype=np.float64)
   682	            sb_fer_f0 = float(np.mean([r['arms']['SBdop']['f0_errors'] > 0 for r in sub]))
   683	            sb_fer_fin = float(np.mean([r['arms']['SBdop']['errors'] > 0 for r in sub]))
   684	            pw_fer_fin = float(np.mean([r['arms']['PWdop']['errors'] > 0 for r in sub]))
   685	            by_rho_snr[f'{rho}_{snr}'] = dict(
   686	                n=len(sub),
   687	                sb_doppler_mean=float(sb_m.mean()),
   688	                sb_doppler_median=float(np.median(sb_m)),
   689	                sb_outlier_gt_0p25_frac=float(sb_o.mean()),
   690	                pw_doppler_mean=float(pw_m.mean()),
   691	                pw_doppler_median=float(np.median(pw_m)),
   692	                sb_f0_fer=sb_fer_f0,
   693	                sb_final_fer=sb_fer_fin,
   694	                pw_final_fer=pw_fer_fin,
   695	            )
   696	
   697	    # Check A5 subset (frames 41000-41099, 4 dB)
   698	    a5_subset = {}
   699	    if 400 in snrs:
   700	        for rho in RHOS:
   701	            sub = [r for r in rows if 41000 <= int(r['frame']) <= 41099 and int(r['rho']) == rho and int(r['snr']) == 400]
   702	            a5_subset[str(rho)] = dict(
   703	                n=len(sub),
   704	                sb_mean=float(np.mean([r['sb_metric'] for r in sub])),
   705	                pw_mean=float(np.mean([r['pw_metric'] for r in sub])),
   706	            )
   707	
   708	    # Weak-path & any-path outlier (> 0.25 bin) shares among SBdop F0 failures vs F0 successes
   709	    def classify_outliers(sub_rows: list[dict[str, Any]]) -> dict[str, Any]:
   710	        n = len(sub_rows)
   711	        if n == 0:
   712	            return dict(n=0, any_outlier=None, weak_outlier=None, weak_only_outlier=None, strong_outlier=None)
   713	        any_c = weak_c = weak_only_c = strong_c = 0
   714	        for r in sub_rows:
   715	            errs = np.asarray(r['sb_abs_err'], dtype=np.float64)
   716	            pw = np.asarray(r['truth_power'], dtype=np.float64)
   717	            med_pw = float(np.median(pw))
   718	            is_weak = pw < med_pw
   719	            is_strong = ~is_weak
   720	            has_any = bool(np.any(errs > OUTLIER_THRESH))
   721	            has_weak = bool(np.any(errs[is_weak] > OUTLIER_THRESH))
   722	            has_strong = bool(np.any(errs[is_strong] > OUTLIER_THRESH))
   723	            any_c += int(has_any)
   724	            weak_c += int(has_weak)
   725	            weak_only_c += int(has_weak and not has_strong)
   726	            strong_c += int(has_strong)
   727	        return dict(
   728	            n=n,
   729	            any_outlier=float(any_c / n),
   730	            weak_outlier=float(weak_c / n),
   731	            weak_only_outlier=float(weak_only_c / n),
   732	            strong_outlier=float(strong_c / n),
   733	        )
   734	
   735	    f0_fail_rows = [r for r in rows if int(r['arms']['SBdop']['f0_errors']) > 0]
   736	    f0_ok_rows = [r for r in rows if int(r['arms']['SBdop']['f0_errors']) == 0]
   737	    syn_fail_rows = [r for r in rows if int(r['arms']['SBdop']['syndrome']) != 0]
   738	    final_fail_rows = [r for r in rows if int(r['arms']['SBdop']['errors']) > 0]
   739	    # Also breakdown at operating band SNR in {300, 400, 450}
   740	    op_f0_fail = [r for r in f0_fail_rows if int(r['snr']) in (300, 400, 450)]
   741	    op_f0_ok = [r for r in f0_ok_rows if int(r['snr']) in (300, 400, 450)]
   742	
   743	    sb_t = np.array([r['sb_cpu'] for r in rows], dtype=np.float64)
   744	    pw_t = np.array([r['pw_cpu'] for r in rows], dtype=np.float64)
   745	
   746	    return dict(
   747	        by_rho_snr=by_rho_snr,
   748	        a5_4db_subset_check=a5_subset,
   749	        sb_outlier_breakdown=dict(
   750	            f0_errors_gt0_all_snrs=classify_outliers(f0_fail_rows),
   751	            f0_errors_eq0_all_snrs=classify_outliers(f0_ok_rows),
   752	            f0_syndrome_nz_all_snrs=classify_outliers(syn_fail_rows),
   753	            final_errors_gt0_all_snrs=classify_outliers(final_fail_rows),
   754	            f0_errors_gt0_snr300_450=classify_outliers(op_f0_fail),
   755	            f0_errors_eq0_snr300_450=classify_outliers(op_f0_ok),
   756	        ),
   757	        timing_cpu_sec=dict(
   758	            sb_mean=float(sb_t.mean()),
   759	            sb_median=float(np.median(sb_t)),
   760	            sb_p95=float(np.percentile(sb_t, 95)),
   761	            pw_mean=float(pw_t.mean()),
   762	            pw_median=float(np.median(pw_t)),
   763	            pw_p95=float(np.percentile(pw_t, 95)),
   764	            sb_by_snr={
   765	                str(snr): float(np.mean([r['sb_cpu'] for r in rows if int(r['snr']) == snr]))
   766	                for snr in snrs
   767	            },
   768	        ),
   769	    )
   770	
   771	
   772	def render_results_md(res: dict[str, Any]) -> str:
   773	    a = res['analysis']
   774	    p = a['primary']
   775	    d = a['diagnostics']
   776	
   777	    def fval(x):
   778	        if isinstance(x, list):
   779	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
   780	        return x if isinstance(x, str) else f'{x:.4f}'
   781	
   782	    lines = [
   783	        '# Stage A6 Results: End-to-End 1% FER Ceiling of Semi-Blind Round-0 Doppler (`SBdop`)',
   784	        '',
   785	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
   786	        f'- Grid: frames `41000–41399` × U/G (`800` draws/cell), ρ ∈ `{res["_config"]["rhos"]}`, SNRs = `{res["_config"]["snrs"]}`',
   787	        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap {res["runtime"]["cpu_cap_core_hours"]:.1f} h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
   788	        '',
   789	        '## Primary Verdict (Pre-Registered, 1% info-FER U/G Mean)',
   790	        '',
   791	        '| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |',
   792	        '|---|---:|---|---|',
   793	        f'| `min CD2 (100..250) − min SBdop (100..150)` | **{fval(p["point_db"])}** | **[{fval(p["ci95_db"][0])}, {fval(p["ci95_db"][1])}]** | **{p["verdict"]}** |',
   794	        '',
   795	        '## 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
   796	        '',
   797	        '| Arm | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | Best (dB) [95% CI] | Best ρ |',
   798	        '|---|---:|---:|---:|---:|---|---:|',
   799	    ]
   800	    for arm in ('CD2', 'PWdop', 'SBdop', 's100', 's050', 'ldop'):
   801	        if arm not in a['mean_crossing']:
   802	            continue
   803	        cells = [fval(a['mean_crossing'][arm][r]) if r in a['mean_crossing'][arm] else '—' for r in ('100', '150', '200', '250')]
   804	        bc = a['best_crossings'][arm]
   805	        lines.append(
   806	            f'| {arm} | ' + ' | '.join(cells) + f' | **{fval(bc["best_db"])}** [{fval(bc["ci95_db"][0])}, {fval(bc["ci95_db"][1])}] | {bc["best_rho"]/1000:.2f} |'
   807	        )
   808	
   809	    lines += ['', '## Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
   810	    for name, c in a['secondary_contrasts'].items():
   811	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')
   812	
   813	    lines += ['', '## Round-0 Doppler Metric & FER by (ρ, SNR) (800 Draws/Cell)', '', '| ρ | SNR (dB) | SB MAE [med] | PW MAE [med] | SB Outlier >0.25 | SB F0 FER | SB Final FER | PW Final FER |', '|---:|---:|---|---|---:|---:|---:|---:|']
   814	    for rho in RHOS:
   815	        for snr in res['_config']['snrs']:
   816	            c = d['by_rho_snr'][f'{rho}_{snr}']
   817	            lines.append(
   818	                f'| {rho/1000:.2f} | {snr/100:.1f} | {c["sb_doppler_mean"]:.4f} [{c["sb_doppler_median"]:.4f}] | '
   819	                f'{c["pw_doppler_mean"]:.4f} [{c["pw_doppler_median"]:.4f}] | '
   820	                f'{100*c["sb_outlier_gt_0p25_frac"]:.2f}% | {100*c["sb_f0_fer"]:.2f}% | {100*c["sb_final_fer"]:.2f}% | {100*c["pw_final_fer"]:.2f}% |'
   821	            )
   822	
   823	    ob = d['sb_outlier_breakdown']
   824	    tm = d['timing_cpu_sec']
   825	    lines += [
   826	        '',
   827	        '## SB Outlier & Timing Diagnostics',
   828	        '',
   829	        f'- F0 failures (all SNRs, n={ob["f0_errors_gt0_all_snrs"]["n"]}): any >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["any_outlier"]:.2f}%`, '
   830	        f'weak-path >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["weak_outlier"]:.2f}%`, '
   831	        f'weak-only >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["weak_only_outlier"]:.2f}%`, '
   832	        f'strong-path >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["strong_outlier"]:.2f}%` '
   833	        f'(vs F0 successes n={ob["f0_errors_eq0_all_snrs"]["n"]}: any `{100*ob["f0_errors_eq0_all_snrs"]["any_outlier"]:.2f}%`, '
   834	        f'weak `{100*ob["f0_errors_eq0_all_snrs"]["weak_outlier"]:.2f}%`, strong `{100*ob["f0_errors_eq0_all_snrs"]["strong_outlier"]:.2f}%`).',
   835	        f'- F0 failures (operating band 3.0–4.5 dB, n={ob["f0_errors_gt0_snr300_450"]["n"]}): '
   836	        f'any `{100*ob["f0_errors_gt0_snr300_450"]["any_outlier"]:.2f}%`, '
   837	        f'weak `{100*ob["f0_errors_gt0_snr300_450"]["weak_outlier"]:.2f}%`, '
   838	        f'strong `{100*ob["f0_errors_gt0_snr300_450"]["strong_outlier"]:.2f}%`.',
   839	        f'- Per-key `SB` CPU time: mean **`{tm["sb_mean"]:.3f} s`**, median `{tm["sb_median"]:.3f} s`, p95 `{tm["sb_p95"]:.3f} s` '
   840	        f'(`PW` mean `{tm["pw_mean"]:.4f} s`).',
   841	    ]
   842	    return '\n'.join(lines) + '\n'
   843	
   844	
   845	def _load_cd2_fail_grid() -> np.ndarray:
   846	    """Load verified CD2 failure grid (400 frames x 2 scen x 4 rhos x 13 SNRs) from stageA + sameframe_cd2."""
   847	    stageA_base = sf.load_stageA_base(CD2_RHOS)
   848	    fi = {f: i for i, f in enumerate(FRAMES)}
   849	    fail = np.zeros((len(FRAMES), 2, len(CD2_RHOS), len(CD2_SNRS)), dtype=bool)
   850	    seen = np.zeros_like(fail)
   851	    for (s, rho, snr, f), b in stageA_base.items():
   852	        if b['syndrome'] == 0:
   853	            ix = (fi[f], SCENARIOS.index(s), CD2_RHOS.index(rho), CD2_SNRS.index(snr))
   854	            fail[ix] = b['f0_errors'] > 0
   855	            seen[ix] = True
   856	    cd2_raw = SAMEFRAME_CD2_DIR / 'out' / 'raw'
   857	    for sp in sorted(cd2_raw.glob('partA_shard*.jsonl.gz')):
   858	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   859	            for line in fh:
   860	                r = json.loads(line)
   861	                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), CD2_RHOS.index(int(r['rho'])), CD2_SNRS.index(int(r['snr'])))
   862	                if seen[ix]:
   863	                    raise RuntimeError(f'Duplicate CD2 key {r}')
   864	                fail[ix] = int(r['arms']['CD2']['errors']) > 0
   865	                seen[ix] = True
   866	    if not seen.all():
   867	        raise RuntimeError('Incomplete archived CD2 grid')
   868	    return fail
   869	
   870	
   871	def cmd_run(args):
   872	    print(sys.executable, flush=True)
   873	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   874	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   875	    ar.check_thread_env()
   876	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   877	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   878	    if not 1 <= args.workers <= 32:
   879	        raise ValueError('workers must be in 1..32')
   880	
   881	    pinned_md5 = verify_pinned_code()
   882	    live_own = own_md5()
   883	    freeze_git_ok = verify_freeze_commit_if_git(args.freeze_commit, live_own)
   884	    manifests = verify_all_archives(('stageA', 'stageA2', 'stageA3', 'sameframe_cd2'))
   885	
   886	    gate_path = args.gate.resolve()
   887	    gate_bytes = gate_path.read_bytes()
   888	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   889	    gate = json.loads(gate_bytes.decode('utf-8'))
   890	    if not gate.get('all_passed') or not gate.get('selected'):
   891	        raise RuntimeError('Refusing to run without passing stageA6_gate.json')
   892	    if gate['_config']['own_md5'] != live_own:
   893	        raise RuntimeError('stageA6_gate.json own_md5 mismatch; re-run gates')
   894	    if gate['_config']['pinned_code_md5'] != pinned_md5:
   895	        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA6_gate.json')
   896	
   897	    snrs = tuple(int(s) for s in gate['selected']['snrs'])
   898	    out_dir = args.out.resolve()
   899	    raw_dir = out_dir / 'raw'
   900	    raw_dir.mkdir(parents=True, exist_ok=True)
   901	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   902	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   903	
   904	    wall_start = time.monotonic()
   905	    n_shards = args.workers
   906	    mp_ctx = multiprocessing.get_context('spawn')
   907	    running = {}
   908	    budget_hit = False
   909	    print(
   910	        f'Launching Stage A6: {len(FRAMES)} frames x 2 scen x {len(RHOS)} rhos x {len(snrs)} SNRs '
   911	        f'({snrs}) = {len(FRAMES)*2*len(RHOS)*len(snrs)} keys on {n_shards} workers...',
   912	        flush=True,
   913	    )
   914	    try:
   915	        for idx in range(n_shards):
   916	            sub_frames = tuple(FRAMES[idx::n_shards])
   917	            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_frames, snrs, raw_dir))
   918	            p.start()
   919	            running[p.sentinel] = (idx, p)
   920	        while running:
   921	            ready = wait(running, timeout=5.0)
   922	            for r in ready:
   923	                idx, p = running.pop(r)
   924	                p.join()
   925	                code = p.exitcode
   926	                p.close()
   927	                if code != 0:
   928	                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
   929	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   930	            if live_cpu >= BUDGET_CAP_SEC - 480.0:
   931	                budget_hit = True
   932	                break
   933	    finally:
   934	        for _, p in running.values():
   935	            p.terminate()
   936	        for _, p in running.values():
   937	            p.join()
   938	            p.close()
   939	    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
   940	        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   941	        sys.exit(BUDGET_EXIT_CODE)
   942	
   943	    # Record shard MD5s and load new rows
   944	    raw_md5: dict[str, str] = {}
   945	    rows: list[dict[str, Any]] = []
   946	    fi = {f: i for i, f in enumerate(FRAMES)}
   947	    sb_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
   948	    pw_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
   949	    seen = np.zeros_like(sb_fail)
   950	    for idx in range(n_shards):
   951	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
   952	        raw_md5[sp.name] = ar.md5_file(sp)
   953	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   954	            for line in fh:
   955	                r = json.loads(line)
   956	                rows.append(r)
   957	                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), RHOS.index(int(r['rho'])), snrs.index(int(r['snr'])))
   958	                if seen[ix]:
   959	                    raise RuntimeError(f'Duplicate Stage A6 key {r["frame"]} {r["scenario"]} {r["rho"]} {r["snr"]}')
   960	                sb_fail[ix] = int(r['arms']['SBdop']['errors']) > 0
   961	                pw_fail[ix] = int(r['arms']['PWdop']['errors']) > 0
   962	                seen[ix] = True
   963	    if not seen.all():
   964	        raise RuntimeError('Incomplete Stage A6 failure grid')
   965	    ar.atomic_write_text(
   966	        out_dir / 'REMOTE_ROWS_MD5.txt',
   967	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
   968	    )
   969	
   970	    # Load frozen comparator grids (verified above)
   971	    import stageA2  # noqa: E402
   972	    import stageA3  # noqa: E402
   973	
   974	    cd2_fail = _load_cd2_fail_grid()
   975	    fa2, _ = stageA2.load(HERE / 'out' / 'stageA2', stageA2.ARMS, A2_RHOS, A23_SNRS)
   976	    fa3, _ = stageA2.load(HERE / 'out' / 'stageA3', stageA3.ARMS, A3_RHOS, A23_SNRS)
   977	
   978	    fail_by_arm = {
   979	        'CD2': (CD2_RHOS, CD2_SNRS, cd2_fail),
   980	        'SBdop': (RHOS, snrs, sb_fail),
   981	        'PWdop': (RHOS, snrs, pw_fail),
   982	        'full': (A2_RHOS, A23_SNRS, fa2[:, 0]),
   983	        'ldop': (A2_RHOS, A23_SNRS, fa2[:, 1]),
   984	        's050': (A3_RHOS, A23_SNRS, fa3[:, stageA3.ARMS.index('s050')]),
   985	        's100': (A3_RHOS, A23_SNRS, fa3[:, stageA3.ARMS.index('s100')]),
   986	    }
   987	    diagnostics = summarize_diagnostics(rows, snrs)
   988	    analysis = analyze_stageA6(fail_by_arm, stageA2.crossing, diagnostics)
   989	
   990	    total_cpu_h = _used_cpu_seconds() / 3600.0
   991	    if total_cpu_h >= BUDGET_CAP_HOURS:
   992	        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
   993	        sys.exit(BUDGET_EXIT_CODE)
   994	
   995	    results = dict(
   996	        _argv=sys.argv,
   997	        _config=dict(
   998	            freeze_commit=args.freeze_commit,
   999	            freeze_commit_git_verified=freeze_git_ok,
  1000	            python_executable=sys.executable,
  1001	            own_md5=live_own,
  1002	            pinned_code_md5=pinned_md5,
  1003	            gate_md5=gate_md5,
  1004	            archive_shards_verified={k: len(v) for k, v in manifests.items()},
  1005	            snrs=list(snrs),
  1006	            rhos=list(RHOS),
  1007	            frames=[FRAMES[0], FRAMES[-1]],
  1008	            raw_output_dir=str(raw_dir),
  1009	            raw_rows_md5=raw_md5,
  1010	        ),
  1011	        gates=dict(
  1012	            all_passed=gate['all_passed'],
  1013	            selected=gate['selected'],
  1014	            G1_passed=gate['G1']['passed'],
  1015	            G2_passed=gate['G2']['passed'],
  1016	        ),
  1017	        runtime=dict(
  1018	            total_core_hours=total_cpu_h,
  1019	            wall_seconds=time.monotonic() - wall_start,
  1020	            cpu_cap_core_hours=BUDGET_CAP_HOURS,
  1021	        ),
  1022	        analysis=analysis,
  1023	    )
  1024	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
  1025	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
  1026	    p = analysis['primary']
  1027	    print(
  1028	        f'STAGEA6_DONE verdict={p["verdict"]} D={p["point_db"]} '
  1029	        f'ci={p["ci95_db"]} SBdop_best={p["arm_b_best_db"]}@rho{p["arm_b_best_rho"]} '
  1030	        f'cpu_hours={total_cpu_h:.4f}',
  1031	        flush=True,
  1032	    )
  1033	
  1034	
  1035	def main():
  1036	    ap = argparse.ArgumentParser(description=__doc__)
  1037	    sub = ap.add_subparsers(dest='mode', required=True)
  1038	    g = sub.add_parser('gate')
  1039	    g.add_argument('--out', type=Path, required=True)
  1040	    g.add_argument('--workers', type=int, default=28)
  1041	
  1042	    r = sub.add_parser('run')
  1043	    r.add_argument('--gate', type=Path, required=True)
  1044	    r.add_argument('--out', type=Path, required=True)
  1045	    r.add_argument('--freeze-commit', required=True)
  1046	    r.add_argument('--workers', type=int, default=WORKERS)
  1047	
  1048	    args = ap.parse_args()
  1049	    dict(gate=cmd_gate, run=cmd_run)[args.mode](args)
  1050	
  1051	
  1052	if __name__ == '__main__':
  1053	    main()

exec
/bin/zsh -lc "nl -ba stageA6.py | sed -n '1,345p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     1	"""Stage A6 (STAGEA6_PROTOCOL.md): end-to-end 1% FER ceiling of semi-blind round-0 Doppler estimation (true delays).
     2	
     3	Reuses stageA.setup(), stageA2.{f0_true, crossing, load}, stageA5.{precompute_delay_geometry, estimate_pw, estimate_sb,
     4	doppler_metric}, sameframe.{crossing_bounds_stageA2, _rep}, and hs_analysis._nearest_rank without editing frozen files.
     5	Arms per key (single-factor change vs stageA3.one_arm: replace injected k_real by continuous estimate nu_hat):
     6	  SBdop = round 0 injects (true delays, stageA5.estimate_sb), pilot LS gains via stageA2.f0_true(..., 'ls'), A1 on F0 fail
     7	  PWdop = round 0 injects (true delays, stageA5.estimate_pw), pilot LS gains via stageA2.f0_true(..., 'ls'), A1 on F0 fail
     8	Comparators (CD2, s050, s100, ldop, full) loaded from verified frozen archives on deinlab.
     9	"""
    10	from __future__ import annotations
    11	
    12	import argparse
    13	import gzip
    14	import hashlib
    15	import json
    16	import math
    17	import multiprocessing
    18	from multiprocessing.connection import wait
    19	import os
    20	from pathlib import Path
    21	import platform
    22	import re
    23	import resource
    24	import shutil
    25	import subprocess
    26	import sys
    27	import time
    28	from typing import Any
    29	
    30	import numpy as np
    31	
    32	HERE = Path(__file__).resolve().parent
    33	EXP = HERE.parent
    34	HUANG_DIR = EXP / 'huang_steelman_20261124'
    35	SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'
    36	SAMEFRAME_CD2_DIR = EXP / 'sameframe_cd2_20261125'
    37	
    38	sys.path.insert(0, str(HERE))
    39	sys.path.insert(0, str(HUANG_DIR))
    40	sys.path.insert(0, str(SAMEFRAME_HG_DIR))
    41	
    42	import hs_analysis as an  # noqa: E402
    43	import hs_arms as ar  # noqa: E402
    44	import sameframe as sf  # noqa: E402
    45	
    46	FRAMES = tuple(range(41000, 41400))
    47	SCENARIOS = ('U', 'G')
    48	RHOS = (100, 150)
    49	CANDIDATE_SNRS: tuple[tuple[int, ...], ...] = (
    50	    (200, 250, 300, 400, 450, 500, 550),
    51	    (200, 250, 300, 400, 450, 500),
    52	    (250, 300, 400, 450, 500),
    53	)
    54	FULL_SNRS = CANDIDATE_SNRS[0]
    55	CD2_RHOS = (100, 150, 200, 250)
    56	CD2_SNRS = (300, 350, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1200)
    57	A2_RHOS = (50, 100, 150, 200)
    58	A3_RHOS = (100, 150, 200)
    59	A23_SNRS = (200, 250) + CD2_SNRS
    60	
    61	BOOT_DRAWS = 2000
    62	BOOT_SEED = 20261125
    63	GO_THRESH_DB = 0.5
    64	STOP_THRESH_DB = 0.3
    65	OUTLIER_THRESH = 0.25
    66	
    67	WORKERS = 32
    68	N_SHARDS = 32
    69	BUDGET_CAP_HOURS = 40.0
    70	BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
    71	COST_MARGIN = 1.3
    72	OVERHEAD_HOURS = 0.15
    73	BUDGET_EXIT_CODE = 124
    74	CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100
    75	
    76	OWN_FILES = ('STAGEA6_PROTOCOL.md', 'stageA6.py', 'test_stageA6.py', 'stageA6_launch.sh')
    77	PINNED_CODE_MD5 = {
    78	    'data_pilot_fer_20261121/stageA.py': '17be1c3e75e07fb9a4dec1b3774c54aa',
    79	    'data_pilot_fer_20261121/stageA2.py': '01a72e6942ec39de99c0e788b3b5b0a9',
    80	    'data_pilot_fer_20261121/stageA3.py': '305645c21bf13b1bc35ec300aa1bcbb2',
    81	    'data_pilot_fer_20261121/stageA5.py': '073b76973298fbd58ecb0ef38953c97d',
    82	    'sameframe_hg_20261124/sameframe.py': '01197778b2ec3cf7f37719ca3b192152',
    83	    'huang_steelman_20261124/hs_arms.py': 'a43f2934c085bde1b69f929fddf06bf6',
    84	    'huang_steelman_20261124/hs_analysis.py': '864b8b7510872c33dc60fc725c57a45d',
    85	}
    86	ARCHIVE_SPECS = {
    87	    'stageA': (
    88	        HERE / 'out' / 'stageA' / 'REMOTE_ROWS_MD5.txt',
    89	        HERE / 'out' / 'stageA',
    90	        '30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68',
    91	        'rows_shard*.jsonl.gz',
    92	    ),
    93	    'stageA2': (
    94	        HERE / 'out' / 'stageA2' / 'REMOTE_ROWS_MD5.txt',
    95	        HERE / 'out' / 'stageA2',
    96	        '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354',
    97	        'rows_shard*.jsonl.gz',
    98	    ),
    99	    'stageA3': (
   100	        HERE / 'out' / 'stageA3' / 'REMOTE_ROWS_MD5.txt',
   101	        HERE / 'out' / 'stageA3',
   102	        '6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a',
   103	        'rows_shard*.jsonl.gz',
   104	    ),
   105	    'stageA5': (
   106	        HERE / 'out' / 'stageA5' / 'REMOTE_ROWS_MD5.txt',
   107	        HERE / 'out' / 'stageA5' / 'raw',
   108	        'bbbcb37b3fc946c2687c14b09897e10e6c69999e369689cdbf9820a7b76448e2',
   109	        'rows_shard*.jsonl.gz',
   110	    ),
   111	    'sameframe_cd2': (
   112	        SAMEFRAME_CD2_DIR / 'out' / 'REMOTE_ROWS_MD5.txt',
   113	        SAMEFRAME_CD2_DIR / 'out' / 'raw',
   114	        '86513c348dcef47a18cdaebb2bc6ade15e7b9f81b95c66ae832653309dae5a85',
   115	        'partA_shard*.jsonl.gz',
   116	    ),
   117	}
   118	
   119	
   120	def own_md5() -> dict[str, str]:
   121	    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}
   122	
   123	
   124	def verify_pinned_code() -> dict[str, str]:
   125	    out: dict[str, str] = {}
   126	    for rel, expected in PINNED_CODE_MD5.items():
   127	        actual = ar.md5_file(EXP / rel)
   128	        if actual != expected:
   129	            raise RuntimeError(f'Pinned dependency MD5 mismatch for {rel}: {actual} != {expected}')
   130	        out[rel] = actual
   131	    return out
   132	
   133	
   134	def verify_archive(name: str) -> dict[str, str]:
   135	    manifest_path, shard_dir, exp_sha, glob_pat = ARCHIVE_SPECS[name]
   136	    got_sha = ar.sha256_file(manifest_path)
   137	    if got_sha != exp_sha:
   138	        raise RuntimeError(f'{name} manifest SHA-256 mismatch: {got_sha} != {exp_sha}')
   139	    expected: dict[str, str] = {}
   140	    for line in manifest_path.read_text(encoding='utf-8').splitlines():
   141	        if not line.strip():
   142	            continue
   143	        digest, fname = line.split()
   144	        p = shard_dir / fname
   145	        if not p.is_file():
   146	            raise FileNotFoundError(f'Missing {name} shard {p}')
   147	        actual = ar.md5_file(p)
   148	        if actual != digest:
   149	            raise RuntimeError(f'{name} shard MD5 mismatch {p}: {actual} != {digest}')
   150	        expected[fname] = actual
   151	    disk = {p.name for p in shard_dir.glob(glob_pat)}
   152	    if disk != set(expected):
   153	        raise RuntimeError(f'{name} shard set mismatch on disk: {sorted(disk ^ set(expected))}')
   154	    return expected
   155	
   156	
   157	def verify_all_archives(names: tuple[str, ...]) -> dict[str, dict[str, str]]:
   158	    return {name: verify_archive(name) for name in names}
   159	
   160	
   161	def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
   162	    repo_root = EXP.parent
   163	    probe = subprocess.run(
   164	        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
   165	        capture_output=True, text=True, check=False,
   166	    )
   167	    if probe.returncode != 0 or probe.stdout.strip() != 'true':
   168	        return False
   169	    chk = subprocess.run(
   170	        ['git', '-C', str(repo_root), 'cat-file', '-e', f'{freeze_commit}^{{commit}}'],
   171	        capture_output=True, text=True, check=False,
   172	    )
   173	    if chk.returncode != 0:
   174	        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo: {chk.stderr.strip()}')
   175	    top = Path(subprocess.run(
   176	        ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
   177	        capture_output=True, text=True, check=True,
   178	    ).stdout.strip())
   179	    rel_dir = HERE.relative_to(top)
   180	    for name, exp_md5 in live_own.items():
   181	        blob = subprocess.run(
   182	            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
   183	            capture_output=True, check=False,
   184	        )
   185	        if blob.returncode != 0:
   186	            raise RuntimeError(f'{name} missing from freeze_commit {freeze_commit}')
   187	        if hashlib.md5(blob.stdout).hexdigest() != exp_md5:
   188	            raise RuntimeError(f'Live {name} differs from freeze_commit {freeze_commit}')
   189	    return True
   190	
   191	
   192	def _used_cpu_seconds() -> float:
   193	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   194	    return time.process_time() + ch.ru_utime + ch.ru_stime
   195	
   196	
   197	def _active_pids_cpu(pids: list[int]) -> float:
   198	    total = 0.0
   199	    for pid in pids:
   200	        try:
   201	            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
   202	            after = raw[raw.rfind(')') + 2:].split()
   203	            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
   204	        except OSError:
   205	            pass
   206	    return total
   207	
   208	
   209	# --------------------------------------------------------------------------- Runtime & arm execution
   210	def _load_runtime():
   211	    import stageA  # noqa: E402
   212	    import stageA2  # noqa: E402
   213	    import stageA5  # noqa: E402
   214	
   215	    C = stageA.setup()
   216	    from physical import daft  # noqa: E402
   217	
   218	    return C, stageA, stageA2, stageA5, daft
   219	
   220	
   221	def one_arm_nu(C, stageA, stageA2, obs, truth, nu_hat: np.ndarray) -> dict[str, Any]:
   222	    """Exact copy of stageA3.one_arm with injected k_real replaced by nu_hat (gains stay pilot LS)."""
   223	    ctx, stage3 = C['ctx'], C['stage3']
   224	    pert = dict(truth, k_real=np.asarray(nu_hat, dtype=np.float64).tolist())
   225	    dec, arrays, syndrome, _ = stageA2.f0_true(C, obs, pert, 'ls')
   226	    s2 = float(obs['sigma2'])
   227	    rec = dict(
   228	        syndrome=int(syndrome),
   229	        r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
   230	        f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
   231	        r0=stageA.support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
   232	        r1=stageA.support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2),
   233	    )
   234	    if syndrome:
   235	        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
   236	        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
   237	        rec['final'] = stageA.support_stats(
   238	            [p.delay for p in br['result'].paths],
   239	            [p.doppler for p in br['result'].paths],
   240	            truth,
   241	            s2,
   242	        )
   243	    else:
   244	        rec['errors'] = rec['f0_errors']
   245	        rec['final'] = rec['r1']
   246	    return rec
   247	
   248	
   249	def eval_key(C, stageA, stageA2, stageA5, daft, base, s: str, rho: int, snr: int, frame: int) -> dict[str, Any]:
   250	    """Evaluate SBdop and PWdop on one observation key (true delays only; no truth peeking in estimators)."""
   251	    st, ctx = C['stage3'], C['ctx']
   252	    c1, c2 = ctx.system.c1, ctx.system.c2
   253	    raw, obs, truth = st.observed(ctx, base, rho, snr)
   254	
   255	    y = np.asarray(raw['y'], dtype=np.complex128)
   256	    p = np.asarray(raw['pilot'], dtype=np.complex128)
   257	    d = np.asarray(raw['data'], dtype=np.complex128)
   258	    sigma2 = float(raw['sigma2'])
   259	    vd = float(np.mean(np.abs(d) ** 2))
   260	    n = len(y)
   261	    r = daft(y, c1, c2, True)
   262	    p_t = daft(p, c1, c2, True)
   263	    geom = stageA5.precompute_delay_geometry(truth['l_i'], n, c1)
   264	
   265	    t0 = time.process_time()
   266	    nu_pw, g_pw = stageA5.estimate_pw(geom, p_t, r)
   267	    pw_cpu = time.process_time() - t0
   268	
   269	    t1 = time.process_time()
   270	    nu_sb, _ = stageA5.estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   271	    sb_cpu = time.process_time() - t1
   272	
   273	    m_pw, o_pw, e_pw = stageA5.doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
   274	    m_sb, o_sb, e_sb = stageA5.doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   275	
   276	    rec_sb = one_arm_nu(C, stageA, stageA2, obs, truth, nu_sb)
   277	    rec_pw = one_arm_nu(C, stageA, stageA2, obs, truth, nu_pw)
   278	
   279	    return dict(
   280	        frame=frame,
   281	        scenario=s,
   282	        rho=rho,
   283	        snr=snr,
   284	        sigma2=float(obs['sigma2']),
   285	        pw_cpu=float(pw_cpu),
   286	        sb_cpu=float(sb_cpu),
   287	        sb_metric=float(m_sb),
   288	        sb_outlier_frac=float(o_sb),
   289	        sb_abs_err=e_sb,
   290	        pw_metric=float(m_pw),
   291	        pw_outlier_frac=float(o_pw),
   292	        pw_abs_err=e_pw,
   293	        truth_power=(np.abs(np.asarray(truth['g_i'], dtype=np.complex128)) ** 2).tolist(),
   294	        arms=dict(SBdop=rec_sb, PWdop=rec_pw),
   295	    )
   296	
   297	
   298	# --------------------------------------------------------------------------- File-IPC helper
   299	def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
   300	    n_workers = min(max_workers, max(1, len(items)))
   301	    buckets = [items[i::n_workers] for i in range(n_workers)]
   302	    mp_ctx = multiprocessing.get_context('spawn')
   303	    out_files = []
   304	    procs = []
   305	    for wi, bucket in enumerate(buckets):
   306	        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
   307	        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
   308	        in_f.write_text(json.dumps(bucket), encoding='utf-8')
   309	        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
   310	        p.start()
   311	        procs.append((wi, p))
   312	        out_files.append(out_f)
   313	    for wi, p in procs:
   314	        p.join()
   315	        code = p.exitcode
   316	        p.close()
   317	        if code != 0:
   318	            raise RuntimeError(f'{tag} worker {wi} exited with code {code}')
   319	    rows: list[Any] = []
   320	    for out_f in out_files:
   321	        rows.extend(json.loads(out_f.read_text(encoding='utf-8')))
   322	    return rows
   323	
   324	
   325	# --------------------------------------------------------------------------- Gates G1-G3
   326	def _g3_cost_worker(in_path: str, out_path: str):
   327	    C, stageA, stageA2, stageA5, daft = _load_runtime()
   328	    st, ctx = C['stage3'], C['ctx']
   329	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   330	    out = []
   331	    for frame, s, rho, snr in jobs:
   332	        t0 = time.process_time()
   333	        base = st.inputs(ctx, frame, s, rho)
   334	        row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
   335	        tot = time.process_time() - t0
   336	        out.append(dict(
   337	            key=[frame, s, rho, snr],
   338	            snr=snr,
   339	            total_cpu=float(tot),
   340	            pw_cpu=row['pw_cpu'],
   341	            sb_cpu=row['sb_cpu'],
   342	        ))
   343	    ar.atomic_write_text(Path(out_path), json.dumps(out))
   344	
   345	

exec
/bin/zsh -lc "nl -ba test_stageA6.py; rg -n 'def (one_arm|f0_true|crossing|analyze_partA|crossing_bounds_stageA2|estimate_pw|estimate_sb|eval_key)|ldop' stageA{2,3,5}.py ../sameframe*/*.py; cat ../../AGENTS.md; rg -n 'A6|sameframe|data.pilot' ../../STATE.md ../../.trellis/workflow.md; ls -a out" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
     1	"""Unit tests for stageA6.py: verdict thresholds, joint paired bootstrap, and outlier classification."""
     2	from __future__ import annotations
     3	
     4	import math
     5	import sys
     6	from pathlib import Path
     7	import numpy as np
     8	
     9	HERE = Path(__file__).resolve().parent
    10	sys.path.insert(0, str(HERE))
    11	
    12	import stageA2  # noqa: E402
    13	import stageA6 as a6  # noqa: E402
    14	
    15	
    16	def test_verdict_boundaries():
    17	    assert a6.verdict_a6(0.50, 0.90) == 'GO'
    18	    assert a6.verdict_a6(0.5001, 0.80) == 'GO'
    19	    assert a6.verdict_a6(0.4999, 0.80) == 'ERIC'
    20	    assert a6.verdict_a6(0.10, 0.30) == 'ERIC'
    21	    assert a6.verdict_a6(0.10, 0.2999) == 'STOP'
    22	    assert a6.verdict_a6(-math.inf, 0.20) == 'STOP'
    23	    assert a6.verdict_a6(-math.inf, math.inf) == 'ERIC'
    24	    assert a6.verdict_a6(0.60, math.inf) == 'GO'
    25	
    26	
    27	def test_joint_bootstrap_and_contrasts():
    28	    # Synthetic 100-frame grid where CD2 crosses at 4.5 dB and SBdop crosses at 3.5 dB -> D = +1.0 dB -> GO
    29	    n_f = 100
    30	    snrs_cd2 = (300, 400, 450, 500)
    31	    snrs_sb = (250, 300, 400, 450, 500)
    32	    rhos_cd2 = (100, 150, 200, 250)
    33	    rhos_sb = (100, 150)
    34	
    35	    def make_grid(rhos, snrs, cross_by_rho):
    36	        arr = np.zeros((n_f, 2, len(rhos), len(snrs)), dtype=bool)
    37	        for ri, rho in enumerate(rhos):
    38	            c_db = cross_by_rho[rho]
    39	            for si, snr in enumerate(snrs):
    40	                s_db = snr / 100.0
    41	                # Exact 10% FER below cross, 0.1% (=0/100 -> floored 1e-4) above cross
    42	                if s_db < c_db:
    43	                    arr[:10, :, ri, si] = True
    44	                elif s_db == c_db:
    45	                    arr[:1, :, ri, si] = True
    46	        return arr
    47	
    48	    cd2_g = make_grid(rhos_cd2, snrs_cd2, {100: 5.0, 150: 4.5, 200: 4.5, 250: 5.0})
    49	    sb_g = make_grid(rhos_sb, snrs_sb, {100: 3.5, 150: 4.0})
    50	    pw_g = make_grid(rhos_sb, snrs_sb, {100: 4.0, 150: 4.0})
    51	    s050_g = make_grid((100, 150, 200), snrs_sb, {100: 3.5, 150: 4.0, 200: 4.0})
    52	    s100_g = make_grid((100, 150, 200), snrs_sb, {100: 4.0, 150: 4.0, 200: 4.5})
    53	    ldop_g = make_grid((50, 100, 150, 200), snrs_sb, {50: 3.0, 100: 3.5, 150: 4.0, 200: 4.0})
    54	
    55	    fail_by_arm = {
    56	        'CD2': (rhos_cd2, snrs_cd2, cd2_g),
    57	        'SBdop': (rhos_sb, snrs_sb, sb_g),
    58	        'PWdop': (rhos_sb, snrs_sb, pw_g),
    59	        's050': ((100, 150, 200), snrs_sb, s050_g),
    60	        's100': ((100, 150, 200), snrs_sb, s100_g),
    61	        'ldop': ((50, 100, 150, 200), snrs_sb, ldop_g),
    62	    }
    63	    res = a6.analyze_stageA6(fail_by_arm, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)
    64	    # Confirm ldop ignores rho=50 and takes min over 100..200 (matching sameframe_cd2)
    65	    assert res['best_rho']['ldop'] == 100
    66	    assert res['primary']['verdict'] == 'GO'
    67	    assert res['primary']['point_db'] > 0.7
    68	
    69	
    70	def test_outlier_diagnostics():
    71	    rows = [
    72	        # Weak-only outlier (bottom 4 powers have error 0.5, top 4 have 0.02), F0 fail
    73	        dict(
    74	            frame=41000, scenario='U', rho=100, snr=400, pw_cpu=0.03, sb_cpu=9.0,
    75	            sb_metric=0.04, sb_outlier_frac=0.125, pw_metric=0.09, pw_outlier_frac=0.25,
    76	            sb_abs_err=[0.02, 0.02, 0.02, 0.02, 0.50, 0.01, 0.01, 0.01],
    77	            truth_power=[0.4, 0.25, 0.15, 0.10, 0.04, 0.03, 0.02, 0.01],
    78	            arms=dict(SBdop=dict(syndrome=5, f0_errors=10, errors=0), PWdop=dict(syndrome=5, f0_errors=10, errors=5)),
    79	        ),
    80	        # Strong outlier, F0 fail
    81	        dict(
    82	            frame=41001, scenario='G', rho=100, snr=400, pw_cpu=0.03, sb_cpu=11.0,
    83	            sb_metric=0.12, sb_outlier_frac=0.125, pw_metric=0.14, pw_outlier_frac=0.25,
    84	            sb_abs_err=[0.40, 0.02, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01],
    85	            truth_power=[0.4, 0.25, 0.15, 0.10, 0.04, 0.03, 0.02, 0.01],
    86	            arms=dict(SBdop=dict(syndrome=8, f0_errors=15, errors=12), PWdop=dict(syndrome=8, f0_errors=15, errors=15)),
    87	        ),
    88	        # No outlier, F0 pass
    89	        dict(
    90	            frame=41000, scenario='U', rho=150, snr=400, pw_cpu=0.03, sb_cpu=8.0,
    91	            sb_metric=0.02, sb_outlier_frac=0.0, pw_metric=0.06, pw_outlier_frac=0.0,
    92	            sb_abs_err=[0.02] * 8,
    93	            truth_power=[0.4, 0.25, 0.15, 0.10, 0.04, 0.03, 0.02, 0.01],
    94	            arms=dict(SBdop=dict(syndrome=0, f0_errors=0, errors=0), PWdop=dict(syndrome=0, f0_errors=0, errors=0)),
    95	        ),
    96	    ]
    97	    diag = a6.summarize_diagnostics(rows, (400,))
    98	    f0f = diag['sb_outlier_breakdown']['f0_errors_gt0_all_snrs']
    99	    assert f0f['n'] == 2
   100	    assert abs(f0f['any_outlier'] - 1.0) < 1e-12
   101	    assert abs(f0f['weak_outlier'] - 0.5) < 1e-12
   102	    assert abs(f0f['weak_only_outlier'] - 0.5) < 1e-12
   103	    assert abs(f0f['strong_outlier'] - 0.5) < 1e-12
   104	    f0ok = diag['sb_outlier_breakdown']['f0_errors_eq0_all_snrs']
   105	    assert f0ok['n'] == 1 and f0ok['any_outlier'] == 0.0
   106	
   107	
   108	if __name__ == '__main__':
   109	    test_verdict_boundaries()
   110	    test_joint_bootstrap_and_contrasts()
   111	    test_outlier_diagnostics()
   112	    print('ALL_STAGEA6_UNIT_TESTS_PASS')
stageA5.py:322:def estimate_pw(geom: dict[str, Any], p_t: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
stageA5.py:342:def estimate_sb(
stageA2.py:7:  ldop = round 0 uses the true (l_i, k_real); gains are the LS solution of time_refine at those values (no search).
stageA2.py:24:ARMS = ('full', 'ldop')
stageA2.py:29:def f0_true(C, obs, truth, gains):
stageA2.py:51:def one_arm(C, obs, truth, gains):
stageA2.py:72:                arms=dict(full=one_arm(C, obs, truth, 'true'), ldop=one_arm(C, obs, truth, 'ls')))
stageA2.py:158:def crossing(fer, snrs):
stageA2.py:197:    fb, diag = load(out, ARMS, RHOS, SNRS)                                            # full, ldop
stageA3.py:3:rho and SNR); gains are the pilot LS solution of time_refine at those values (stage A2 'ldop' with perturbed Doppler).
stageA3.py:32:def one_arm(C, obs, truth, sigma, z):
stageA3.py:73:    """G1: sigma = 0 reproduces the stage A2 'ldop' rows (syndrome, F0 errors, final errors).
stageA3.py:86:        rec = one_arm(C, obs, truth, 0, z); a = rows[(s_, rho, snr, frame)]['arms']['ldop']
stageA3.py:140:    fb, _ = load(out.parent / 'stageA2', stageA2.ARMS, stageA2.RHOS, SNRS)           # full, ldop
stageA3.py:151:        delay_best, ldop_best = ma[1].min(), mb[1].min()
stageA3.py:153:        return np.concatenate([(delay_best - best) / (delay_best - ldop_best), best, [delay_best, ldop_best]])
stageA3.py:169:                                  ldop={str(r): float(mb[1, j]) for j, r in enumerate(RHOS)},
stageA3.py:171:               best=dict(delay=float(g[2 * k]), ldop=float(g[2 * k + 1]), **{a: float(g[k + i]) for i, a in enumerate(ARMS)}),
../sameframe_cd2_20261125/sameframe_cd2.py:464:def analyze_partA(
../sameframe_cd2_20261125/sameframe_cd2.py:511:        if arm in ('delay', 'full', 'ldop'):
../sameframe_cd2_20261125/sameframe_cd2.py:545:    for comp in ('s050', 'ldop', 'full', 'delay', 'base', 'HG', 'HGint'):
../sameframe_cd2_20261125/sameframe_cd2.py:549:        for comp in ('s100', 's050', 'ldop', 'full', 'HG', 'HGint', 'CD2'):
../sameframe_cd2_20261125/sameframe_cd2.py:592:    arms_order = [a for a in ('base', 'delay', 'HG', 'HGint', 'CD2', 'CD2e8', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in pA['mean_crossing']]
../sameframe_cd2_20261125/sameframe_cd2.py:752:        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
../sameframe_hg_20261124/sameframe.py:885:def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
../sameframe_hg_20261124/sameframe.py:972:        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; full/ldop/delay over 100..200; base over all
../sameframe_hg_20261124/sameframe.py:973:        if arm in ('delay', 'full', 'ldop'):
../sameframe_hg_20261124/sameframe.py:1009:    for comp in ('s050', 'ldop', 'full', 'delay', 'base'):
../sameframe_hg_20261124/sameframe.py:1014:        for comp in ('s100', 's050', 'ldop', 'full', 'HG'):
../sameframe_hg_20261124/sameframe.py:1185:    p1_arms = [a for a in ('base', 'delay', 'HG', 'HG1', 'HGint', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in p1['mean_crossing']]
../sameframe_hg_20261124/sameframe.py:1292:        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
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
../../STATE.md:15:- 当前重心：用 [idea 漏斗](ideas/FUNNEL.md) 找原理级、够 Trans 的新问题（[看板](ideas/BOARD.md)）；`11-21-data-pilot-fer`（低导频）状态不变。下面两条是 11-20 交接时的快照。
../../STATE.md:26:- 11-25 同帧检验（冻结 `918a24747`，10.9 核时）：**更正上一条**——轮数对齐后两遍 CD 追平 HG（−0.12 [−0.55, +0.08]，`CATCHES_UP`；换 8 条版 −0.19 [−0.58, −0.01]），"局部交换不如全局重找"不成立，HG 的 0.65 dB 来自多一轮；耗时未测。低导频帧上 HG 之后第 0 轮多普勒余量 0.73 [0.45, 1.04] dB（0.08 bin 口径，`INCONCLUSIVE`，下界差 0.05 未过 0.5），0.04 bin 口径 1.12 dB；对两遍 CD 的余量未测（[读数](experiments/sameframe_hg_20261124/READOUT.md)）。
../../STATE.md:27:- 11-25 两遍 CD 同帧复核（冻结 `e3bf93f64`，3.25 核时）：低导频帧上 CD2 最优 4.42 dB（ρ = .20）≈ 真时延上限、好于 HG 0.16 dB；之后第 0 轮多普勒余量 0.58 [0.32, 0.84] dB（0.08 bin，`INCONCLUSIVE`），0.04 bin 口径 0.96 dB。静默计时 ρ = .20：CD2 每次触发均值 189 ms，HG 640 ms（3.4×），粗字典 HGint 199 ms（[读数](experiments/sameframe_cd2_20261125/READOUT.md)）。
../../STATE.md:35:- 11-21 建任务 `11-21-data-pilot-fer`（planning）：自相关候选进 F0 第 0 轮的 FER 决定性检验，分阶段 0 预检（只用观测量的选择器）→ A（真时延上界，配对余量门槛 0.3 dB）→ B；设计 v2 已过 Astra 审，待 Eric 批后实现（[设计](.trellis/tasks/11-21-data-pilot-fer/design.md)）。
../../STATE.md:36:- 11-21 data-pilot-fer 阶段 0（只用观测量的选择器，冻结）**PASS**：F0 第 0 轮实际漏掉的有效径，召回 .653；但候选精度只有 .192，阶段 B 的槽位规则要防假径（[读数](experiments/data_pilot_fer_20261121/STAGE0_READOUT.md)）。
../../STATE.md:37:- 11-21 data-pilot-fer 阶段 A（冻结，11.8 核时）**CONTINUE**：第 0 轮给真时延后，低导频最优 4.40 dB（ρ = .20）对基线最优 4.95 dB（ρ = .25），余量 0.55 [0.39, 0.76] dB；时延全对后仍失败的约一半与多普勒误差有关。0b 多锚打分 FALLBACK（[读数](experiments/data_pilot_fer_20261121/STAGEA_READOUT.md)）。
../../STATE.md:39:- 11-21 data-pilot-fer 阶段 A2（冻结，7.9 核时）**CONTINUE**：第 0 轮给全真信道后最优 3.45 dB（ρ = .10），比真时延上限 4.40 再好 0.95 [0.79, 1.07] dB，比基线最优好 1.51 dB；增益用导频 LS 结果几乎不变，值钱的是多普勒精度。ρ = .05 给全真信道也失败，原因是检测器联合增益重估失稳（探索性，20 键）（[读数](experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md)）。
../../STATE.md:40:- 11-21 data-pilot-fer 阶段 A3（冻结，10.9 核时）**MIDDLE**：第 0 轮多普勒误差 σ ≤ 0.05 bin 时 A2 收益几乎全保住，σ = 0.1 保住 0.59 [0.33, 0.85]，σ = 0.2 崩掉；导频在 ρ = .10 的误差约 0.16。下一步按规则先算导频单独、导频加数据两种多普勒下界（[读数](experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md)）。
../../STATE.md:41:- 11-21 data-pilot-fer 阶段 A4（冻结，1.7 核时）**SB-REACHABLE**：第 0 轮多普勒下界（功率加权平均绝对误差，4 dB）导频白噪声 .085/.068、最好纯导频 .074/.060、半盲 .040/.037、数据全知 .015（ρ .10/.15）；现有导频估计器比自身下界差 1.6–1.9 倍。半盲刚好够到 0.04，需要近乎有效的估计器（[读数](experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md)）。
.
..
stage0.json
stage0b.json
stageA
stageA2
stageA2_gate.json
stageA3
stageA3_gate.json
stageA4
stageA4_gate.json
stageA5
stageA5_gate.json
stageA5_sol_review.md
stageA6_sol_review.md
stageA_gate.json

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA6.py | sed -n '673,958p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
exec
/bin/zsh -lc "nl -ba stageA6.py | sed -n '430,672p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   430	    # G3: stratified cost projection across all 7 SNRs on isolated frames 41400-41403 (28 keys)
   431	    g3_jobs = []
   432	    for snr in FULL_SNRS:
   433	        g3_jobs.extend([
   434	            [41400, 'U', 100, snr],
   435	            [41401, 'G', 100, snr],
   436	            [41402, 'U', 150, snr],
   437	            [41403, 'G', 150, snr],
   438	        ])
   439	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   440	    ipc_dir = tmp_root / f'stageA6_gates_ipc_{os.getpid()}'
   441	    ipc_dir.mkdir(parents=True, exist_ok=True)
   442	    try:
   443	        print(f'Running G3 stratified cost benchmark ({len(g3_jobs)} keys across {len(FULL_SNRS)} SNRs)...', flush=True)
   444	        g3_samples = _spawn_map(_g3_cost_worker, g3_jobs, min(args.workers, len(g3_jobs)), ipc_dir, 'g3')
   445	    finally:
   446	        shutil.rmtree(ipc_dir, ignore_errors=True)
   447	
   448	    mean_cpu_by_snr = {
   449	        snr: float(np.mean([x['total_cpu'] for x in g3_samples if int(x['snr']) == snr]))
   450	        for snr in FULL_SNRS
   451	    }
   452	    mean_sb_by_snr = {
   453	        snr: float(np.mean([x['sb_cpu'] for x in g3_samples if int(x['snr']) == snr]))
   454	        for snr in FULL_SNRS
   455	    }
   456	    keys_per_snr = len(FRAMES) * len(SCENARIOS) * len(RHOS)  # 400 * 2 * 2 = 1600
   457	    candidates = []
   458	    for cand_snrs in CANDIDATE_SNRS:
   459	        raw_h = sum(mean_cpu_by_snr[s] * keys_per_snr for s in cand_snrs) / 3600.0 + OVERHEAD_HOURS
   460	        marg_h = raw_h * COST_MARGIN
   461	        candidates.append(dict(
   462	            snrs=list(cand_snrs),
   463	            dropped_snrs=[s for s in FULL_SNRS if s not in cand_snrs],
   464	            n_keys=keys_per_snr * len(cand_snrs),
   465	            raw_hours=raw_h,
   466	            projected_hours_with_margin=marg_h,
   467	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   468	        ))
   469	    selected = next((c for c in candidates if c['within_budget']), None)
   470	    g3_pass = selected is not None
   471	    all_passed = bool(g1_pass and g2_pass and g3_pass)
   472	    gate_cpu_h = _used_cpu_seconds() / 3600.0
   473	
   474	    payload = dict(
   475	        _argv=sys.argv,
   476	        _config=dict(
   477	            python_executable=sys.executable,
   478	            threads=thread_env,
   479	            workers=args.workers,
   480	            own_md5=own_md5(),
   481	            pinned_code_md5=pinned_md5,
   482	            archive_shards_verified={k: len(v) for k, v in manifests.items()},
   483	        ),
   484	        all_passed=all_passed,
   485	        selected=selected,
   486	        G1=dict(passed=g1_pass, rows=g1_rows),
   487	        G2=dict(passed=g2_pass, rows=g2_rows),
   488	        G3=dict(
   489	            passed=g3_pass,
   490	            budget_cap_core_hours=BUDGET_CAP_HOURS,
   491	            margin=COST_MARGIN,
   492	            overhead_hours=OVERHEAD_HOURS,
   493	            mean_total_cpu_sec_by_snr={str(k): v for k, v in mean_cpu_by_snr.items()},
   494	            mean_sb_cpu_sec_by_snr={str(k): v for k, v in mean_sb_by_snr.items()},
   495	            candidates=candidates,
   496	            samples=g3_samples,
   497	        ),
   498	        gate_cpu_hours=gate_cpu_h,
   499	        gate_wall_seconds=time.monotonic() - started,
   500	    )
   501	    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
   502	    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
   503	    sys.exit(0 if all_passed else 1)
   504	
   505	
   506	# --------------------------------------------------------------------------- Main worker & readout
   507	def _run_shard_worker(shard_idx: int, frames: tuple[int, ...], snrs: tuple[int, ...], raw_dir: Path):
   508	    C, stageA, stageA2, stageA5, daft = _load_runtime()
   509	    st, ctx = C['stage3'], C['ctx']
   510	    lines: list[str] = []
   511	    for frame in frames:
   512	        for s in SCENARIOS:
   513	            for rho in RHOS:
   514	                base = st.inputs(ctx, frame, s, rho)
   515	                for snr in snrs:
   516	                    row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
   517	                    lines.append(json.dumps(row, allow_nan=False) + '\n')
   518	
   519	    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
   520	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   521	    with part_path.open('wb') as raw_fh:
   522	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
   523	            for ln in lines:
   524	                gz.write(ln.encode('utf-8'))
   525	        raw_fh.flush()
   526	        os.fsync(raw_fh.fileno())
   527	    os.replace(part_path, final_path)
   528	    print(f'Shard {shard_idx:03d} done ({len(lines)} keys, {len(frames)} frames)', flush=True)
   529	
   530	
   531	def verdict_a6(ci_lo: float, ci_hi: float) -> str:
   532	    if ci_lo >= GO_THRESH_DB:
   533	        return 'GO'
   534	    if ci_hi < STOP_THRESH_DB:
   535	        return 'STOP'
   536	    return 'ERIC'
   537	
   538	
   539	def _to_float_bound(val: Any) -> float:
   540	    if isinstance(val, (int, float)):
   541	        return float(val)
   542	    if val == '-inf':
   543	        return -math.inf
   544	    if val == 'inf':
   545	        return math.inf
   546	    raise ValueError(f'Unexpected bound representation: {val!r}')
   547	
   548	
   549	def analyze_stageA6(
   550	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   551	    crossing_fn,
   552	    diagnostics: dict[str, Any],
   553	    *,
   554	    boot_draws: int = BOOT_DRAWS,
   555	    boot_seed: int = BOOT_SEED,
   556	) -> dict[str, Any]:
   557	    """Frozen Stage A6 readout with exact sameframe_cd2 joint paired physical-frame bootstrap."""
   558	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   559	    rng = np.random.default_rng(boot_seed)
   560	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   561	    weights[0] = 1.0 / n_frames
   562	    for b in range(1, boot_draws + 1):
   563	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   564	
   565	    arm_lo: dict[str, np.ndarray] = {}
   566	    arm_hi: dict[str, np.ndarray] = {}
   567	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   568	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   569	    arm_best_lo: dict[str, np.ndarray] = {}
   570	    arm_best_hi: dict[str, np.ndarray] = {}
   571	    arm_best_rho: dict[str, int] = {}
   572	
   573	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   574	        n_r = len(rhos)
   575	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   576	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   577	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   578	        scen_pt = {'U': {}, 'G': {}}
   579	        for ri, rho in enumerate(rhos):
   580	            for bi in range(boot_draws + 1):
   581	                u_lo, u_hi = sf.crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   582	                g_lo, g_hi = sf.crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   583	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   584	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   585	                if bi == 0:
   586	                    scen_pt['U'][str(rho)] = sf._rep(u_lo) if u_lo == u_hi else [sf._rep(u_lo), sf._rep(u_hi)]
   587	                    scen_pt['G'][str(rho)] = sf._rep(g_lo) if g_lo == g_hi else [sf._rep(g_lo), sf._rep(g_hi)]
   588	        arm_lo[arm] = lo_arr
   589	        arm_hi[arm] = hi_arr
   590	        arm_scen_pt[arm] = scen_pt
   591	        arm_mean_pt[arm] = {
   592	            str(rho): (sf._rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [sf._rep(lo_arr[0, ri]), sf._rep(hi_arr[0, ri])])
   593	            for ri, rho in enumerate(rhos)
   594	        }
   595	        if arm in ('full', 'ldop'):
   596	            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
   597	        else:
   598	            sub_idx = list(range(n_r))
   599	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   600	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   601	        arm_best_rho[arm] = int(rhos[sub_idx[int(np.argmin(hi_arr[0, sub_idx]))]])
   602	
   603	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   604	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   605	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   606	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   607	        if cens_frac == 0.0:
   608	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   609	        else:
   610	            lo = an._nearest_rank(d_lo[1:], 0.025)
   611	            hi = an._nearest_rank(d_hi[1:], 0.975)
   612	        pt = sf._rep(d_lo[0]) if d_lo[0] == d_hi[0] else [sf._rep(d_lo[0]), sf._rep(d_hi[0])]
   613	        return dict(
   614	            point_db=pt,
   615	            ci95_db=[sf._rep(lo), sf._rep(hi)],
   616	            censored_draw_fraction=cens_frac,
   617	            arm_a_best_db=sf._rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [sf._rep(arm_best_lo[arm_a][0]), sf._rep(arm_best_hi[arm_a][0])],
   618	            arm_a_best_rho=arm_best_rho[arm_a],
   619	            arm_b_best_db=sf._rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [sf._rep(arm_best_lo[arm_b][0]), sf._rep(arm_best_hi[arm_b][0])],
   620	            arm_b_best_rho=arm_best_rho[arm_b],
   621	        )
   622	
   623	    primary = contrast('CD2', 'SBdop')
   624	    lo_val = _to_float_bound(primary['ci95_db'][0])
   625	    hi_val = _to_float_bound(primary['ci95_db'][1])
   626	    primary['verdict'] = verdict_a6(lo_val, hi_val)
   627	    primary['go_threshold_db'] = GO_THRESH_DB
   628	    primary['stop_threshold_db'] = STOP_THRESH_DB
   629	
   630	    # Best crossing CIs for SBdop & PWdop
   631	    best_ci = {}
   632	    for arm in ('SBdop', 'PWdop', 'CD2', 's050', 's100', 'ldop'):
   633	        if arm not in arm_best_lo:
   634	            continue
   635	        blo, bhi = arm_best_lo[arm], arm_best_hi[arm]
   636	        cf = float(np.mean(~(np.isfinite(blo[1:]) & np.isfinite(bhi[1:]))))
   637	        if cf == 0.0:
   638	            c_lo, c_hi = (float(v) for v in np.percentile(blo[1:], [2.5, 97.5]))
   639	        else:
   640	            c_lo = an._nearest_rank(blo[1:], 0.025)
   641	            c_hi = an._nearest_rank(bhi[1:], 0.975)
   642	        best_ci[arm] = dict(
   643	            best_db=sf._rep(blo[0]) if blo[0] == bhi[0] else [sf._rep(blo[0]), sf._rep(bhi[0])],
   644	            best_rho=arm_best_rho[arm],
   645	            ci95_db=[sf._rep(c_lo), sf._rep(c_hi)],
   646	            censored_draw_fraction=cf,
   647	        )
   648	
   649	    secondary = {
   650	        'SBdop_minus_s050': contrast('SBdop', 's050'),
   651	        'SBdop_minus_ldop': contrast('SBdop', 'ldop'),
   652	        'CD2_minus_PWdop': contrast('CD2', 'PWdop'),
   653	        'PWdop_minus_SBdop': contrast('PWdop', 'SBdop'),
   654	        'SBdop_minus_s100': contrast('SBdop', 's100'),
   655	        'CD2_minus_s050': contrast('CD2', 's050'),
   656	        'CD2_minus_ldop': contrast('CD2', 'ldop'),
   657	    }
   658	
   659	    return dict(
   660	        frames=n_frames,
   661	        boot_draws=boot_draws,
   662	        boot_seed=boot_seed,
   663	        primary=primary,
   664	        best_crossings=best_ci,
   665	        secondary_contrasts=secondary,
   666	        mean_crossing=arm_mean_pt,
   667	        crossings_by_scenario=arm_scen_pt,
   668	        best_rho=arm_best_rho,
   669	        diagnostics=diagnostics,
   670	    )
   671	
   672	

 succeeded in 0ms:
   673	def summarize_diagnostics(rows: list[dict[str, Any]], snrs: tuple[int, ...]) -> dict[str, Any]:
   674	    """Compute per-SNR Doppler error, A5 subset check, F0-failure outlier breakdown, and SB/PW timing."""
   675	    by_rho_snr: dict[str, dict[str, Any]] = {}
   676	    for rho in RHOS:
   677	        for snr in snrs:
   678	            sub = [r for r in rows if int(r['rho']) == rho and int(r['snr']) == snr]
   679	            sb_m = np.array([r['sb_metric'] for r in sub], dtype=np.float64)
   680	            pw_m = np.array([r['pw_metric'] for r in sub], dtype=np.float64)
   681	            sb_o = np.array([r['sb_outlier_frac'] for r in sub], dtype=np.float64)
   682	            sb_fer_f0 = float(np.mean([r['arms']['SBdop']['f0_errors'] > 0 for r in sub]))
   683	            sb_fer_fin = float(np.mean([r['arms']['SBdop']['errors'] > 0 for r in sub]))
   684	            pw_fer_fin = float(np.mean([r['arms']['PWdop']['errors'] > 0 for r in sub]))
   685	            by_rho_snr[f'{rho}_{snr}'] = dict(
   686	                n=len(sub),
   687	                sb_doppler_mean=float(sb_m.mean()),
   688	                sb_doppler_median=float(np.median(sb_m)),
   689	                sb_outlier_gt_0p25_frac=float(sb_o.mean()),
   690	                pw_doppler_mean=float(pw_m.mean()),
   691	                pw_doppler_median=float(np.median(pw_m)),
   692	                sb_f0_fer=sb_fer_f0,
   693	                sb_final_fer=sb_fer_fin,
   694	                pw_final_fer=pw_fer_fin,
   695	            )
   696	
   697	    # Check A5 subset (frames 41000-41099, 4 dB)
   698	    a5_subset = {}
   699	    if 400 in snrs:
   700	        for rho in RHOS:
   701	            sub = [r for r in rows if 41000 <= int(r['frame']) <= 41099 and int(r['rho']) == rho and int(r['snr']) == 400]
   702	            a5_subset[str(rho)] = dict(
   703	                n=len(sub),
   704	                sb_mean=float(np.mean([r['sb_metric'] for r in sub])),
   705	                pw_mean=float(np.mean([r['pw_metric'] for r in sub])),
   706	            )
   707	
   708	    # Weak-path & any-path outlier (> 0.25 bin) shares among SBdop F0 failures vs F0 successes
   709	    def classify_outliers(sub_rows: list[dict[str, Any]]) -> dict[str, Any]:
   710	        n = len(sub_rows)
   711	        if n == 0:
   712	            return dict(n=0, any_outlier=None, weak_outlier=None, weak_only_outlier=None, strong_outlier=None)
   713	        any_c = weak_c = weak_only_c = strong_c = 0
   714	        for r in sub_rows:
   715	            errs = np.asarray(r['sb_abs_err'], dtype=np.float64)
   716	            pw = np.asarray(r['truth_power'], dtype=np.float64)
   717	            med_pw = float(np.median(pw))
   718	            is_weak = pw < med_pw
   719	            is_strong = ~is_weak
   720	            has_any = bool(np.any(errs > OUTLIER_THRESH))
   721	            has_weak = bool(np.any(errs[is_weak] > OUTLIER_THRESH))
   722	            has_strong = bool(np.any(errs[is_strong] > OUTLIER_THRESH))
   723	            any_c += int(has_any)
   724	            weak_c += int(has_weak)
   725	            weak_only_c += int(has_weak and not has_strong)
   726	            strong_c += int(has_strong)
   727	        return dict(
   728	            n=n,
   729	            any_outlier=float(any_c / n),
   730	            weak_outlier=float(weak_c / n),
   731	            weak_only_outlier=float(weak_only_c / n),
   732	            strong_outlier=float(strong_c / n),
   733	        )
   734	
   735	    f0_fail_rows = [r for r in rows if int(r['arms']['SBdop']['f0_errors']) > 0]
   736	    f0_ok_rows = [r for r in rows if int(r['arms']['SBdop']['f0_errors']) == 0]
   737	    syn_fail_rows = [r for r in rows if int(r['arms']['SBdop']['syndrome']) != 0]
   738	    final_fail_rows = [r for r in rows if int(r['arms']['SBdop']['errors']) > 0]
   739	    # Also breakdown at operating band SNR in {300, 400, 450}
   740	    op_f0_fail = [r for r in f0_fail_rows if int(r['snr']) in (300, 400, 450)]
   741	    op_f0_ok = [r for r in f0_ok_rows if int(r['snr']) in (300, 400, 450)]
   742	
   743	    sb_t = np.array([r['sb_cpu'] for r in rows], dtype=np.float64)
   744	    pw_t = np.array([r['pw_cpu'] for r in rows], dtype=np.float64)
   745	
   746	    return dict(
   747	        by_rho_snr=by_rho_snr,
   748	        a5_4db_subset_check=a5_subset,
   749	        sb_outlier_breakdown=dict(
   750	            f0_errors_gt0_all_snrs=classify_outliers(f0_fail_rows),
   751	            f0_errors_eq0_all_snrs=classify_outliers(f0_ok_rows),
   752	            f0_syndrome_nz_all_snrs=classify_outliers(syn_fail_rows),
   753	            final_errors_gt0_all_snrs=classify_outliers(final_fail_rows),
   754	            f0_errors_gt0_snr300_450=classify_outliers(op_f0_fail),
   755	            f0_errors_eq0_snr300_450=classify_outliers(op_f0_ok),
   756	        ),
   757	        timing_cpu_sec=dict(
   758	            sb_mean=float(sb_t.mean()),
   759	            sb_median=float(np.median(sb_t)),
   760	            sb_p95=float(np.percentile(sb_t, 95)),
   761	            pw_mean=float(pw_t.mean()),
   762	            pw_median=float(np.median(pw_t)),
   763	            pw_p95=float(np.percentile(pw_t, 95)),
   764	            sb_by_snr={
   765	                str(snr): float(np.mean([r['sb_cpu'] for r in rows if int(r['snr']) == snr]))
   766	                for snr in snrs
   767	            },
   768	        ),
   769	    )
   770	
   771	
   772	def render_results_md(res: dict[str, Any]) -> str:
   773	    a = res['analysis']
   774	    p = a['primary']
   775	    d = a['diagnostics']
   776	
   777	    def fval(x):
   778	        if isinstance(x, list):
   779	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
   780	        return x if isinstance(x, str) else f'{x:.4f}'
   781	
   782	    lines = [
   783	        '# Stage A6 Results: End-to-End 1% FER Ceiling of Semi-Blind Round-0 Doppler (`SBdop`)',
   784	        '',
   785	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
   786	        f'- Grid: frames `41000–41399` × U/G (`800` draws/cell), ρ ∈ `{res["_config"]["rhos"]}`, SNRs = `{res["_config"]["snrs"]}`',
   787	        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap {res["runtime"]["cpu_cap_core_hours"]:.1f} h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
   788	        '',
   789	        '## Primary Verdict (Pre-Registered, 1% info-FER U/G Mean)',
   790	        '',
   791	        '| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |',
   792	        '|---|---:|---|---|',
   793	        f'| `min CD2 (100..250) − min SBdop (100..150)` | **{fval(p["point_db"])}** | **[{fval(p["ci95_db"][0])}, {fval(p["ci95_db"][1])}]** | **{p["verdict"]}** |',
   794	        '',
   795	        '## 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
   796	        '',
   797	        '| Arm | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | Best (dB) [95% CI] | Best ρ |',
   798	        '|---|---:|---:|---:|---:|---|---:|',
   799	    ]
   800	    for arm in ('CD2', 'PWdop', 'SBdop', 's100', 's050', 'ldop'):
   801	        if arm not in a['mean_crossing']:
   802	            continue
   803	        cells = [fval(a['mean_crossing'][arm][r]) if r in a['mean_crossing'][arm] else '—' for r in ('100', '150', '200', '250')]
   804	        bc = a['best_crossings'][arm]
   805	        lines.append(
   806	            f'| {arm} | ' + ' | '.join(cells) + f' | **{fval(bc["best_db"])}** [{fval(bc["ci95_db"][0])}, {fval(bc["ci95_db"][1])}] | {bc["best_rho"]/1000:.2f} |'
   807	        )
   808	
   809	    lines += ['', '## Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
   810	    for name, c in a['secondary_contrasts'].items():
   811	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')
   812	
   813	    lines += ['', '## Round-0 Doppler Metric & FER by (ρ, SNR) (800 Draws/Cell)', '', '| ρ | SNR (dB) | SB MAE [med] | PW MAE [med] | SB Outlier >0.25 | SB F0 FER | SB Final FER | PW Final FER |', '|---:|---:|---|---|---:|---:|---:|---:|']
   814	    for rho in RHOS:
   815	        for snr in res['_config']['snrs']:
   816	            c = d['by_rho_snr'][f'{rho}_{snr}']
   817	            lines.append(
   818	                f'| {rho/1000:.2f} | {snr/100:.1f} | {c["sb_doppler_mean"]:.4f} [{c["sb_doppler_median"]:.4f}] | '
   819	                f'{c["pw_doppler_mean"]:.4f} [{c["pw_doppler_median"]:.4f}] | '
   820	                f'{100*c["sb_outlier_gt_0p25_frac"]:.2f}% | {100*c["sb_f0_fer"]:.2f}% | {100*c["sb_final_fer"]:.2f}% | {100*c["pw_final_fer"]:.2f}% |'
   821	            )
   822	
   823	    ob = d['sb_outlier_breakdown']
   824	    tm = d['timing_cpu_sec']
   825	    lines += [
   826	        '',
   827	        '## SB Outlier & Timing Diagnostics',
   828	        '',
   829	        f'- F0 failures (all SNRs, n={ob["f0_errors_gt0_all_snrs"]["n"]}): any >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["any_outlier"]:.2f}%`, '
   830	        f'weak-path >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["weak_outlier"]:.2f}%`, '
   831	        f'weak-only >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["weak_only_outlier"]:.2f}%`, '
   832	        f'strong-path >0.25 = `{100*ob["f0_errors_gt0_all_snrs"]["strong_outlier"]:.2f}%` '
   833	        f'(vs F0 successes n={ob["f0_errors_eq0_all_snrs"]["n"]}: any `{100*ob["f0_errors_eq0_all_snrs"]["any_outlier"]:.2f}%`, '
   834	        f'weak `{100*ob["f0_errors_eq0_all_snrs"]["weak_outlier"]:.2f}%`, strong `{100*ob["f0_errors_eq0_all_snrs"]["strong_outlier"]:.2f}%`).',
   835	        f'- F0 failures (operating band 3.0–4.5 dB, n={ob["f0_errors_gt0_snr300_450"]["n"]}): '
   836	        f'any `{100*ob["f0_errors_gt0_snr300_450"]["any_outlier"]:.2f}%`, '
   837	        f'weak `{100*ob["f0_errors_gt0_snr300_450"]["weak_outlier"]:.2f}%`, '
   838	        f'strong `{100*ob["f0_errors_gt0_snr300_450"]["strong_outlier"]:.2f}%`.',
   839	        f'- Per-key `SB` CPU time: mean **`{tm["sb_mean"]:.3f} s`**, median `{tm["sb_median"]:.3f} s`, p95 `{tm["sb_p95"]:.3f} s` '
   840	        f'(`PW` mean `{tm["pw_mean"]:.4f} s`).',
   841	    ]
   842	    return '\n'.join(lines) + '\n'
   843	
   844	
   845	def _load_cd2_fail_grid() -> np.ndarray:
   846	    """Load verified CD2 failure grid (400 frames x 2 scen x 4 rhos x 13 SNRs) from stageA + sameframe_cd2."""
   847	    stageA_base = sf.load_stageA_base(CD2_RHOS)
   848	    fi = {f: i for i, f in enumerate(FRAMES)}
   849	    fail = np.zeros((len(FRAMES), 2, len(CD2_RHOS), len(CD2_SNRS)), dtype=bool)
   850	    seen = np.zeros_like(fail)
   851	    for (s, rho, snr, f), b in stageA_base.items():
   852	        if b['syndrome'] == 0:
   853	            ix = (fi[f], SCENARIOS.index(s), CD2_RHOS.index(rho), CD2_SNRS.index(snr))
   854	            fail[ix] = b['f0_errors'] > 0
   855	            seen[ix] = True
   856	    cd2_raw = SAMEFRAME_CD2_DIR / 'out' / 'raw'
   857	    for sp in sorted(cd2_raw.glob('partA_shard*.jsonl.gz')):
   858	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   859	            for line in fh:
   860	                r = json.loads(line)
   861	                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), CD2_RHOS.index(int(r['rho'])), CD2_SNRS.index(int(r['snr'])))
   862	                if seen[ix]:
   863	                    raise RuntimeError(f'Duplicate CD2 key {r}')
   864	                fail[ix] = int(r['arms']['CD2']['errors']) > 0
   865	                seen[ix] = True
   866	    if not seen.all():
   867	        raise RuntimeError('Incomplete archived CD2 grid')
   868	    return fail
   869	
   870	
   871	def cmd_run(args):
   872	    print(sys.executable, flush=True)
   873	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   874	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   875	    ar.check_thread_env()
   876	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   877	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   878	    if not 1 <= args.workers <= 32:
   879	        raise ValueError('workers must be in 1..32')
   880	
   881	    pinned_md5 = verify_pinned_code()
   882	    live_own = own_md5()
   883	    freeze_git_ok = verify_freeze_commit_if_git(args.freeze_commit, live_own)
   884	    manifests = verify_all_archives(('stageA', 'stageA2', 'stageA3', 'sameframe_cd2'))
   885	
   886	    gate_path = args.gate.resolve()
   887	    gate_bytes = gate_path.read_bytes()
   888	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   889	    gate = json.loads(gate_bytes.decode('utf-8'))
   890	    if not gate.get('all_passed') or not gate.get('selected'):
   891	        raise RuntimeError('Refusing to run without passing stageA6_gate.json')
   892	    if gate['_config']['own_md5'] != live_own:
   893	        raise RuntimeError('stageA6_gate.json own_md5 mismatch; re-run gates')
   894	    if gate['_config']['pinned_code_md5'] != pinned_md5:
   895	        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA6_gate.json')
   896	
   897	    snrs = tuple(int(s) for s in gate['selected']['snrs'])
   898	    out_dir = args.out.resolve()
   899	    raw_dir = out_dir / 'raw'
   900	    raw_dir.mkdir(parents=True, exist_ok=True)
   901	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   902	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   903	
   904	    wall_start = time.monotonic()
   905	    n_shards = args.workers
   906	    mp_ctx = multiprocessing.get_context('spawn')
   907	    running = {}
   908	    budget_hit = False
   909	    print(
   910	        f'Launching Stage A6: {len(FRAMES)} frames x 2 scen x {len(RHOS)} rhos x {len(snrs)} SNRs '
   911	        f'({snrs}) = {len(FRAMES)*2*len(RHOS)*len(snrs)} keys on {n_shards} workers...',
   912	        flush=True,
   913	    )
   914	    try:
   915	        for idx in range(n_shards):
   916	            sub_frames = tuple(FRAMES[idx::n_shards])
   917	            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_frames, snrs, raw_dir))
   918	            p.start()
   919	            running[p.sentinel] = (idx, p)
   920	        while running:
   921	            ready = wait(running, timeout=5.0)
   922	            for r in ready:
   923	                idx, p = running.pop(r)
   924	                p.join()
   925	                code = p.exitcode
   926	                p.close()
   927	                if code != 0:
   928	                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
   929	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   930	            if live_cpu >= BUDGET_CAP_SEC - 480.0:
   931	                budget_hit = True
   932	                break
   933	    finally:
   934	        for _, p in running.values():
   935	            p.terminate()
   936	        for _, p in running.values():
   937	            p.join()
   938	            p.close()
   939	    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
   940	        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   941	        sys.exit(BUDGET_EXIT_CODE)
   942	
   943	    # Record shard MD5s and load new rows
   944	    raw_md5: dict[str, str] = {}
   945	    rows: list[dict[str, Any]] = []
   946	    fi = {f: i for i, f in enumerate(FRAMES)}
   947	    sb_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
   948	    pw_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
   949	    seen = np.zeros_like(sb_fail)
   950	    for idx in range(n_shards):
   951	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
   952	        raw_md5[sp.name] = ar.md5_file(sp)
   953	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   954	            for line in fh:
   955	                r = json.loads(line)
   956	                rows.append(r)
   957	                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), RHOS.index(int(r['rho'])), snrs.index(int(r['snr'])))
   958	                if seen[ix]:

exec
/bin/zsh -lc "nl -ba ../sameframe_cd2_20261125/sameframe_cd2.py | sed -n '410,579p'; nl -ba ../sameframe_hg_20261124/sameframe.py | sed -n '876,923p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   410	    sys.exit(0 if all_passed else 1)
   411	
   412	
   413	# --------------------------------------------------------------------------- Part A worker & analysis
   414	def _partA_shard_worker(
   415	    shard_idx: int,
   416	    frames: tuple[int, ...],
   417	    trig_by_frame: dict[int, list[tuple[str, int, int, int, int, int]]],
   418	    include_cd2e8: bool,
   419	    raw_dir: Path,
   420	):
   421	    C, _, _, helpers = sf.load_stage_runtime()
   422	    stage3, ctx = C['stage3'], C['ctx']
   423	    final_path = raw_dir / f'partA_shard{shard_idx:03d}.jsonl.gz'
   424	    out_lines: list[str] = []
   425	    for frame in frames:
   426	        items = trig_by_frame.get(frame, [])
   427	        grouped: dict[tuple[str, int], list[tuple[int, int, int, int]]] = {}
   428	        for s, rho, snr, exp_syn, exp_f0_err, exp_base_err in items:
   429	            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err, exp_base_err))
   430	        for (s, rho), grp in sorted(grouped.items()):
   431	            base = stage3.inputs(ctx, frame, s, rho)
   432	            for snr, exp_syn, exp_f0_err, exp_base_err in sorted(grp):
   433	                _, obs, truth = stage3.observed(ctx, base, rho, snr)
   434	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   435	                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   436	                if int(syn) != exp_syn or f0_err != exp_f0_err:
   437	                    raise RuntimeError(
   438	                        f'PartA F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
   439	                    )
   440	                cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
   441	                if int(cd2['pass1_errors']) != exp_base_err:
   442	                    raise RuntimeError(
   443	                        f'PartA CD2 pass-1 drift vs stageA base at {(s, rho, snr, frame)}: '
   444	                        f'{cd2["pass1_errors"]} != {exp_base_err}'
   445	                    )
   446	                arms_rec = dict(CD2=cd2)
   447	                if include_cd2e8:
   448	                    arms_rec['CD2e8'] = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   449	                out_lines.append(json.dumps(dict(
   450	                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
   451	                ), allow_nan=False) + '\n')
   452	    sf._write_gzip_jsonl_atomic(final_path, out_lines)
   453	    print(f'PartA shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   454	
   455	
   456	def p1p_verdict(ci_lo: float, ci_hi: float) -> str:
   457	    if ci_lo >= P1P_THRESHOLD_DB:
   458	        return 'DOPPLER-LINE'
   459	    if ci_hi < P1P_THRESHOLD_DB:
   460	        return 'STOP-LINE'
   461	    return 'INCONCLUSIVE'
   462	
   463	
   464	def analyze_partA(
   465	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   466	    include_cd2e8: bool,
   467	    crossing_fn,
   468	    diag_stats: dict[str, Any],
   469	    *,
   470	    boot_draws: int = BOOT_DRAWS,
   471	    boot_seed: int = BOOT_SEED,
   472	) -> dict[str, Any]:
   473	    """Joint paired physical-frame bootstrap analysis for P1' (frames 41000-41399, seed 20261125)."""
   474	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   475	    rng = np.random.default_rng(boot_seed)
   476	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   477	    weights[0] = 1.0 / n_frames
   478	    for b in range(1, boot_draws + 1):
   479	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   480	
   481	    arm_lo: dict[str, np.ndarray] = {}
   482	    arm_hi: dict[str, np.ndarray] = {}
   483	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   484	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   485	    arm_best_lo: dict[str, np.ndarray] = {}
   486	    arm_best_hi: dict[str, np.ndarray] = {}
   487	    arm_best_rho: dict[str, int] = {}
   488	
   489	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   490	        n_r = len(rhos)
   491	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   492	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   493	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   494	        scen_pt = {'U': {}, 'G': {}}
   495	        for ri, rho in enumerate(rhos):
   496	            for bi in range(boot_draws + 1):
   497	                u_lo, u_hi = sf.crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   498	                g_lo, g_hi = sf.crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   499	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   500	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   501	                if bi == 0:
   502	                    scen_pt['U'][str(rho)] = sf._rep(u_lo) if u_lo == u_hi else [sf._rep(u_lo), sf._rep(u_hi)]
   503	                    scen_pt['G'][str(rho)] = sf._rep(g_lo) if g_lo == g_hi else [sf._rep(g_lo), sf._rep(g_hi)]
   504	        arm_lo[arm] = lo_arr
   505	        arm_hi[arm] = hi_arr
   506	        arm_scen_pt[arm] = scen_pt
   507	        arm_mean_pt[arm] = {
   508	            str(rho): (sf._rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [sf._rep(lo_arr[0, ri]), sf._rep(hi_arr[0, ri])])
   509	            for ri, rho in enumerate(rhos)
   510	        }
   511	        if arm in ('delay', 'full', 'ldop'):
   512	            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
   513	        else:
   514	            sub_idx = list(range(n_r))
   515	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   516	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   517	        arm_best_rho[arm] = int(rhos[sub_idx[int(np.argmin(hi_arr[0, sub_idx]))]])
   518	
   519	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   520	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   521	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   522	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   523	        if cens_frac == 0.0:
   524	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   525	        else:
   526	            lo = an._nearest_rank(d_lo[1:], 0.025)
   527	            hi = an._nearest_rank(d_hi[1:], 0.975)
   528	        pt = sf._rep(d_lo[0]) if d_lo[0] == d_hi[0] else [sf._rep(d_lo[0]), sf._rep(d_hi[0])]
   529	        return dict(
   530	            point_db=pt,
   531	            ci95_db=[sf._rep(lo), sf._rep(hi)],
   532	            censored_draw_fraction=cens_frac,
   533	            arm_a_best_db=sf._rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [sf._rep(arm_best_lo[arm_a][0]), sf._rep(arm_best_hi[arm_a][0])],
   534	            arm_a_best_rho=arm_best_rho[arm_a],
   535	            arm_b_best_db=sf._rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [sf._rep(arm_best_lo[arm_b][0]), sf._rep(arm_best_hi[arm_b][0])],
   536	            arm_b_best_rho=arm_best_rho[arm_b],
   537	        )
   538	
   539	    p1p = contrast('CD2', 's100')
   540	    lo_val = float(p1p['ci95_db'][0]) if isinstance(p1p['ci95_db'][0], float) else (-math.inf if p1p['ci95_db'][0] == '-inf' else math.inf)
   541	    hi_val = float(p1p['ci95_db'][1]) if isinstance(p1p['ci95_db'][1], float) else (-math.inf if p1p['ci95_db'][1] == '-inf' else math.inf)
   542	    p1p['verdict'] = p1p_verdict(lo_val, hi_val)
   543	
   544	    sec = {}
   545	    for comp in ('s050', 'ldop', 'full', 'delay', 'base', 'HG', 'HGint'):
   546	        if comp in fail_by_arm:
   547	            sec[f'CD2_minus_{comp}'] = contrast('CD2', comp)
   548	    if include_cd2e8 and 'CD2e8' in fail_by_arm:
   549	        for comp in ('s100', 's050', 'ldop', 'full', 'HG', 'HGint', 'CD2'):
   550	            if comp in fail_by_arm:
   551	                sec[f'CD2e8_minus_{comp}'] = contrast('CD2e8', comp)
   552	    sec['HG_minus_s100'] = contrast('HG', 's100')
   553	
   554	    return dict(
   555	        boot_draws=boot_draws,
   556	        boot_seed=boot_seed,
   557	        partA_rhos=list(PARTA_RHOS),
   558	        include_cd2e8=include_cd2e8,
   559	        primary_P1_prime=p1p,
   560	        secondary_contrasts=sec,
   561	        mean_crossing=arm_mean_pt,
   562	        crossings_by_scenario=arm_scen_pt,
   563	        best_rho=arm_best_rho,
   564	        diagnostics=diag_stats,
   565	    )
   566	
   567	
   568	def render_results_md(res: dict[str, Any]) -> str:
   569	    pA = res['partA']
   570	    p1p = pA['primary_P1_prime']
   571	
   572	    def fval(x):
   573	        if isinstance(x, list):
   574	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
   575	        return x if isinstance(x, str) else f'{x:.4f}'
   576	
   577	    lines = [
   578	        '# Same-Frame CD2 Headroom & Quiet Timing Results (`sameframe_cd2_20261125`)',
   579	        '',
   876	        for _, proc in running.values():
   877	            proc.join()
   878	            proc.close()
   879	    if budget_hit or _used_cpu_seconds() >= cpu_cap_sec:
   880	        print(f'STOPPED_BUDGET: CPU limit reached ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   881	        sys.exit(BUDGET_EXIT_CODE)
   882	
   883	
   884	# --------------------------------------------------------------------------- Analysis (P1 & P2)
   885	def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
   886	    """Wrap stageA2.crossing into conservative (lo, hi) bounds so censored draws never silently yield NaN."""
   887	    c = float(crossing_fn(fer, snrs))
   888	    if math.isfinite(c):
   889	        return c, c
   890	    if c < 0:
   891	        return -math.inf, float(snrs[0]) / 100.0
   892	    return float(snrs[-1]) / 100.0, math.inf
   893	
   894	
   895	def p1_verdict(ci_lo: float, ci_hi: float) -> str:
   896	    if ci_lo >= P1_THRESHOLD_DB:
   897	        return 'DOPPLER-LINE'
   898	    if ci_hi < P1_THRESHOLD_DB:
   899	        return 'WRITE-A'
   900	    return 'INCONCLUSIVE'
   901	
   902	
   903	def p2_verdict(ci_lo: float, ci_hi: float) -> str:
   904	    if ci_lo > P2_THRESHOLD_DB:
   905	        return 'STILL_BEHIND'
   906	    if ci_hi < P2_THRESHOLD_DB:
   907	        return 'CATCHES_UP'
   908	    return 'MIXED'
   909	
   910	
   911	def _rep(v: float) -> Any:
   912	    if math.isinf(v):
   913	        return '+inf' if v > 0 else '-inf'
   914	    if math.isnan(v):
   915	        raise FloatingPointError('NaN encountered in readout')
   916	    return float(v)
   917	
   918	
   919	def analyze_part1(
   920	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   921	    part1_rhos: tuple[int, ...],
   922	    include_hgint: bool,
   923	    crossing_fn,

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA2.py | sed -n '19,172p'; nl -ba stageA3.py | sed -n '17,102p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
    19	import stageA
    20	from stageA import FRAMES, SCENARIOS, setup, support_stats
    21	
    22	RHOS = (50, 100, 150, 200)
    23	SNRS = (200, 250) + stageA.SNRS
    24	ARMS = ('full', 'ldop')
    25	FRAMES_PER_SHARD, WORKERS = 5, 32
    26	BOOT, SEED, KILL_DB = 2000, 20261121, 0.15
    27	
    28	
    29	def f0_true(C, obs, truth, gains):
    30	    """F0 whose round-0 time_refine returns the true channel; gains='true' or 'ls'. Restores time_refine afterwards."""
    31	    native = C['ctx'].native
    32	    orig = native.time_refine
    33	    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    34	    state = dict(calls=0)
    35	
    36	    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw):
    37	        state['calls'] += 1
    38	        if state['calls'] > 1:
    39	            return orig(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw)
    40	        ch, det = orig(y, pilot, mu, v, l, nu, g, c1, c2, noise, **dict(kw, rounds=0))
    41	        if gains == 'true':
    42	            ch = type(ch)(ch.n, ch.c1, ch.c2, ch.delays, ch.dopplers, [g[list(l).index(d)] for d in ch.delays])
    43	        return ch, det
    44	    native.time_refine = refine
    45	    try:
    46	        return C['stage3'].e1.f0_state(C['ctx'], obs)
    47	    finally:
    48	        native.time_refine = orig
    49	
    50	
    51	def one_arm(C, obs, truth, gains):
    52	    ctx, stage3 = C['ctx'], C['stage3']
    53	    dec, arrays, syndrome, _ = f0_true(C, obs, truth, gains)
    54	    s2 = float(obs['sigma2'])
    55	    rec = dict(syndrome=int(syndrome),
    56	               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
    57	               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
    58	               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
    59	               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    60	    if syndrome:
    61	        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
    62	        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    63	        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    64	    else:
    65	        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    66	    return rec
    67	
    68	
    69	def run_key(C, base, s_, rho, snr, frame):
    70	    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    71	    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
    72	                arms=dict(full=one_arm(C, obs, truth, 'true'), ldop=one_arm(C, obs, truth, 'ls')))
    73	
    74	
    75	def shard_job(job):
    76	    idx, frames, out = job
    77	    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
    78	    with open(path, 'x') as fh:
    79	        for frame in frames:
    80	            for s_ in SCENARIOS:
    81	                for rho in RHOS:
    82	                    base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
    83	                    for snr in SNRS:
    84	                        print(json.dumps(run_key(C, base, s_, rho, snr, frame)), file=fh); n += 1
    85	    os.system(f'gzip -n {path}')
    86	    return idx, n
    87	
    88	
    89	def gate(out):
    90	    """G1: identity time_refine wrapper is bitwise the baseline, and the base arm reproduces stage A rows.
    91	    G2: round 0 of 'full' carries exactly the true delays, Doppler and gains.
    92	    G3: gain convention: noiseless, true data known, LS gains at the true (l, nu) align with truth g_i (cosine >= .999)."""
    93	    C = setup(); stage3, ctx, native = C['stage3'], C['ctx'], C['ctx'].native
    94	    rows = {}
    95	    with gzip.open(Path(out).parent / 'stageA' / 'rows_shard000.jsonl.gz', 'rt') as fh:
    96	        for line in fh:
    97	            r = json.loads(line); rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    98	    keys = [k for k in rows if k[1] in (100, 200) and k[2] in (500, 800)][:8]
    99	    res = []
   100	    for s_, rho, snr, frame in keys:
   101	        base = stage3.inputs(ctx, frame, s_, rho)
   102	        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
   103	        rec = stageA.one_arm(C, obs, truth, None); a = rows[(s_, rho, snr, frame)]['arms']['base']
   104	        reproduce = all(rec[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors'))
   105	        dec0, arr0, _, _ = stageA.f0(C, obs)
   106	        orig = native.time_refine
   107	        native.time_refine = lambda *p, **kw: orig(*p, **kw)
   108	        try:
   109	            dec1, arr1, _, _ = stage3.e1.f0_state(ctx, obs)
   110	        finally:
   111	            native.time_refine = orig
   112	        ident = all(np.array_equal(arr0[k], arr1[k]) for k in ('r0_delays', 'r0_dopplers', 'r1_delays', 'r1_dopplers')) \
   113	            and np.array_equal(dec0['decoded'], dec1['decoded'])
   114	        _, arr2, _, _ = f0_true(C, obs, truth, 'true')
   115	        l = np.asarray(truth['l_i'], int); order = [list(l).index(d) for d in arr2['r0_delays']]
   116	        g2 = (sorted(arr2['r0_delays'].tolist()) == sorted(l.tolist())
   117	              and np.allclose(arr2['r0_dopplers'], np.asarray(truth['k_real'])[order])
   118	              and np.allclose(arr2['r0_ce_gains'], np.asarray(truth['g_i'])[order]))
   119	        res.append(dict(key=[s_, rho, snr, frame], reproduce=bool(reproduce), identity=bool(ident), full_r0_true=bool(g2)))
   120	    cos = []
   121	    for frame in (41000, 41001, 41002, 41003):
   122	        base = stage3.inputs(ctx, frame, 'U', 300)
   123	        raw, obs, truth = stage3.observed(ctx, base, 300, 1200)
   124	        l = np.asarray(truth['l_i'], int); g = np.asarray(truth['g_i'], complex); y0 = np.asarray(raw['noiseless'])
   125	        # noiseless observation with the true data known: LS gains at the true (l, nu) must equal truth g_i
   126	        ch, _ = native.time_refine(y0, obs['pilot'], np.asarray(raw['data']), np.zeros(len(y0)), l,
   127	                                   np.asarray(truth['k_real'], float), g, ctx.system.c1, ctx.system.c2, 1e-12,
   128	                                   mode='mean', max_paths=8, rounds=0)
   129	        gt = np.array([g[list(l).index(d)] for d in ch.delays])
   130	        cos.append(float(abs(np.vdot(ch.gains, gt)) / np.linalg.norm(ch.gains) / np.linalg.norm(gt)))
   131	    t = time.process_time(); base = stage3.inputs(ctx, 41399, 'G', 100)
   132	    for snr in (500, 800):
   133	        run_key(C, base, 'G', 100, snr, 41399)
   134	    per_key = (time.process_time() - t) / 2
   135	    out_ = dict(cpu_seconds_per_key=per_key,
   136	                projected_core_hours=per_key * len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(SNRS) / 3600 * 1.3,
   137	                G1=all(x['reproduce'] and x['identity'] for x in res), G2=all(x['full_r0_true'] for x in res),
   138	                G3=min(cos) >= .999, cosines=cos, keys=res)
   139	    Path(out).write_text(json.dumps(out_, indent=1)); print(json.dumps(out_, indent=1))
   140	
   141	
   142	def run(out):
   143	    out = Path(out); out.mkdir(parents=True, exist_ok=False)
   144	    frames = list(FRAMES)
   145	    jobs = [(i, frames[k:k + FRAMES_PER_SHARD], str(out)) for i, k in enumerate(range(0, len(frames), FRAMES_PER_SHARD))]
   146	    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
   147	        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS), indent=1))
   148	    t0 = time.time(); done = 0
   149	    with get_context('spawn').Pool(WORKERS) as pool:
   150	        for idx, n in pool.imap_unordered(shard_job, jobs):
   151	            done += n > 0
   152	    ch = resource.getrusage(resource.RUSAGE_CHILDREN); hours = (ch.ru_utime + ch.ru_stime) / 3600
   153	    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
   154	    (out / 'STATUS').write_text((f'DONE {done} {hours:.4f}' if done == len(jobs) else f'STOPPED incomplete {hours:.4f}') + '\n')
   155	    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))
   156	
   157	
   158	def crossing(fer, snrs):
   159	    """stageA.crossing on an arbitrary SNR grid (dB)."""
   160	    x = np.asarray(snrs) / 100; lf = np.log10(np.maximum(fer, 1e-4))
   161	    if fer[0] <= .01:
   162	        return -np.inf
   163	    for i in range(1, len(x)):
   164	        if fer[i] <= .01:
   165	            t = (lf[i - 1] + 2) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
   166	            return x[i - 1] + t * (x[i] - x[i - 1])
   167	    return np.inf
   168	
   169	
   170	def load(out, arms, rhos, snrs):
   171	    fi = {f: i for i, f in enumerate(FRAMES)}
   172	    fail = np.zeros((len(FRAMES), len(arms), len(SCENARIOS), len(rhos), len(snrs)), bool); seen = np.zeros_like(fail)
    17	from stageA import FRAMES, SCENARIOS, setup, support_stats
    18	from stageA2 import f0_true, crossing, load
    19	
    20	RHOS = (100, 150, 200)
    21	SNRS = stageA2.SNRS
    22	SIGMAS = (25, 50, 100, 200)                      # Doppler error std in 1/1000 bin
    23	ARMS = tuple(f's{s:03d}' for s in SIGMAS)
    24	FRAMES_PER_SHARD, WORKERS = 5, 32
    25	BOOT, SEED = 2000, 20261121
    26	
    27	
    28	def z_paths(frame, s_, n):
    29	    return np.random.default_rng([SEED, frame, SCENARIOS.index(s_)]).standard_normal(n)
    30	
    31	
    32	def one_arm(C, obs, truth, sigma, z):
    33	    ctx, stage3 = C['ctx'], C['stage3']
    34	    pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + sigma / 1000 * z).tolist())
    35	    dec, arrays, syndrome, _ = f0_true(C, obs, pert, 'ls')
    36	    s2 = float(obs['sigma2'])
    37	    rec = dict(syndrome=int(syndrome),
    38	               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
    39	               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
    40	               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
    41	               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    42	    if syndrome:
    43	        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
    44	        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    45	        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    46	    else:
    47	        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    48	    return rec
    49	
    50	
    51	def run_key(C, base, s_, rho, snr, frame, sigmas=SIGMAS):
    52	    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    53	    z = z_paths(frame, s_, len(truth['l_i']))
    54	    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
    55	                arms={f's{s:03d}': one_arm(C, obs, truth, s, z) for s in sigmas})
    56	
    57	
    58	def shard_job(job):
    59	    idx, frames, out = job
    60	    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
    61	    with open(path, 'x') as fh:
    62	        for frame in frames:
    63	            for s_ in SCENARIOS:
    64	                for rho in RHOS:
    65	                    base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
    66	                    for snr in SNRS:
    67	                        print(json.dumps(run_key(C, base, s_, rho, snr, frame)), file=fh); n += 1
    68	    os.system(f'gzip -n {path}')
    69	    return idx, n
    70	
    71	
    72	def gate(out):
    73	    """G1: sigma = 0 reproduces the stage A2 'ldop' rows (syndrome, F0 errors, final errors).
    74	    G2: for sigma = .05 bin, round 0 carries the true delays and exactly k_real + .05 z, with z fixed across rho/SNR."""
    75	    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    76	    rows = {}
    77	    with gzip.open(Path(out).parent / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt') as fh:
    78	        for line in fh:
    79	            r = json.loads(line); rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    80	    keys = [k for k in rows if k[1] in (100, 200) and k[2] in (400, 600)][:8]
    81	    res = []
    82	    for s_, rho, snr, frame in keys:
    83	        base = stage3.inputs(ctx, frame, s_, rho)
    84	        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    85	        z = z_paths(frame, s_, len(truth['l_i']))
    86	        rec = one_arm(C, obs, truth, 0, z); a = rows[(s_, rho, snr, frame)]['arms']['ldop']
    87	        reproduce = all(rec[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors'))
    88	        pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + .05 * z).tolist())
    89	        _, arr, _, _ = f0_true(C, obs, pert, 'ls')
    90	        l = list(np.asarray(truth['l_i'], int)); order = [l.index(d) for d in arr['r0_delays']]
    91	        exact = (sorted(arr['r0_delays'].tolist()) == sorted(l)
    92	                 and np.allclose(arr['r0_dopplers'], (np.asarray(truth['k_real']) + .05 * z)[order]))
    93	        res.append(dict(key=[s_, rho, snr, frame], reproduce=bool(reproduce), r0_exact=bool(exact)))
    94	    t = time.process_time(); base = stage3.inputs(ctx, 41399, 'G', 100)
    95	    for snr in (400, 600):
    96	        run_key(C, base, 'G', 100, snr, 41399)
    97	    per_key = (time.process_time() - t) / 2
    98	    out_ = dict(cpu_seconds_per_key=per_key,
    99	                projected_core_hours=per_key * len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(SNRS) / 3600 * 1.3,
   100	                G1=all(x['reproduce'] for x in res), G2=all(x['r0_exact'] for x in res), keys=res)
   101	    Path(out).write_text(json.dumps(out_, indent=1)); print(json.dumps(out_, indent=1))
   102	

exec
/bin/zsh -lc 'md5 stageA.py stageA2.py stageA3.py stageA5.py ../sameframe_hg_20261124/sameframe.py ../huang_steelman_20261124/{hs_arms,hs_analysis}.py; git status --short -- STAGEA6_PROTOCOL.md stageA6.py test_stageA6.py stageA6_launch.sh' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
MD5 (stageA.py) = 17be1c3e75e07fb9a4dec1b3774c54aa
MD5 (stageA2.py) = 01a72e6942ec39de99c0e788b3b5b0a9
MD5 (stageA3.py) = 305645c21bf13b1bc35ec300aa1bcbb2
MD5 (stageA5.py) = 073b76973298fbd58ecb0ef38953c97d
MD5 (../sameframe_hg_20261124/sameframe.py) = 01197778b2ec3cf7f37719ca3b192152
MD5 (../huang_steelman_20261124/hs_arms.py) = a43f2934c085bde1b69f929fddf06bf6
MD5 (../huang_steelman_20261124/hs_analysis.py) = 864b8b7510872c33dc60fc725c57a45d
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-pdLISd35' (errno=Operation not permitted)
?? STAGEA6_PROTOCOL.md
?? stageA6.py
?? stageA6_launch.sh
?? test_stageA6.py

exec
/bin/zsh -lc "sed -n '1,100p' out/stageA6_sol_review.md; ls -a ../../.trellis/tasks/11-21-data-pilot-fer; rg -n 'deinlab|/dev/shm|/tmp' ../../CLAUDE.md ../../.trellis/spec -g '*.md'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
OpenAI Codex v0.170.0
--------
workdir: /tmp
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a210ae-8534-7111-a142-94f94cefdf03
--------
user
You are Sol performing a concise (<= 3 min) pre-launch static review of Stage A6 in `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/`:
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA6_PROTOCOL.md`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/test_stageA6.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6_launch.sh`

Check specifically:
1. Single-factor arm exactness vs `stageA3.one_arm` / `stageA2.f0_true(..., 'ls')`:
   - `SBdop` and `PWdop` inject `nu_hat` into `pert['k_real']` (true delays only, no truth peeking for `g_i` or `k_real`), gains stay pilot LS via `stageA2.f0_true`, `run_branch(..., 'A1')` on `syndrome != 0`, score against real `truth`.
2. Gates G1–G3 (`out/stageA6_gate.json`):
   - G1: `nu_hat = truth['k_real']` reproduces `stageA2` `ldop` (syndrome, F0 errors, final errors) on 4 keys.
   - G2: 4 keys from A5 (`41000-41099`, 4 dB, `rho .10/.15`) reproduce A5 `estimate_sb` raw `abs_err['SB']` & `metric['SB']` within `1e-6`.
   - G3: stratified cost `x1.3 <= 40.0` core-hours (`<= 32` workers), drop SNR `550` first, then `200`, record selection.
3. Frozen readout & archive verification:
   - `stageA2.crossing` at 1% FER U/G mean; `D = min_{rho in {100..250}} CD2 - min_{rho in {100,150}} SBdop`; joint paired physical-frame bootstrap exact match to `sameframe_cd2.analyze_partA` (2000 draws, seed `20261125`, 95% CI, censored bounds); `GO` if CI lower `>= 0.5`, `STOP` if CI upper `< 0.3`, else `ERIC`.
   - Archive MD5 & manifest SHA-256 verification for `stageA`, `stageA2`, `stageA3`, `stageA5`, `sameframe_cd2`; no rerunning archived arms.
   - Descriptive diagnostics: per-rho crossings, contrasts (`SBdop - s050`, `SBdop - ldop`, `CD2 - PWdop`), round-0 Doppler metric per SNR vs A5, F0-failure weak-path outlier (`> 0.25` bin) share, per-key SB CPU time.
4. deinlab safety (`AFDM` env, 6 thread vars = 1, `CUDA_VISIBLE_DEVICES=""`, `<= 32` workers, `/data/guoyikun/tmp`, zero `/tmp`/`/dev/shm`, atomic writes, CPU budget stop margin) and any bugs or edge cases.

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

我会用 `research-checkpoint` 做启动前静态审查，先核对实验协议和代码，再对照历史实现、归档校验和启动脚本。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba stageA6_launch.sh; nl -ba STAGEA6_PROTOCOL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
exec
/bin/zsh -lc 'cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md; pwd; ls -a' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
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
.
..
check.jsonl
design.md
implement.jsonl
implement.md
prd.md
research
task.json
../../CLAUDE.md:101:- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
../../CLAUDE.md:106:- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
../../CLAUDE.md:107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
../../CLAUDE.md:119:  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`
../../CLAUDE.md:123:- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
../../CLAUDE.md:132:| 需要快速丢弃的 scratch 文件、smoke test 日志、跨项目临时 pickle | **`/data/guoyikun/tmp/`** ← 项目专用 tmp 目录，取代系统 `/tmp` |
../../CLAUDE.md:135:**规则**：所有原本想写到系统 `/tmp/` 的操作，都改写到 `/data/guoyikun/tmp/`。
../../CLAUDE.md:136:例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。
../../.trellis/spec/backend/research-diagnostics.md:955:On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
../../.trellis/spec/backend/research-diagnostics.md:1024:deinlab, record its SSH root and verify it before deleting task-created local

exec
/bin/zsh -lc "rg -n 'def (load_stageA_base|check_thread_env|atomic_write_text|_nearest_rank)|PARTA_RHOS|PARTA_SNRS' ../sameframe_hg_20261124/sameframe.py ../sameframe_cd2_20261125/sameframe_cd2.py ../huang_steelman_20261124/{hs_arms,hs_analysis}.py; rg -n 'def |metric|41000|400|RHOS' stageA5.py | tail -65; ls -l out/stageA{,2,3,5} ../sameframe_cd2_20261125/out; for d in out/stageA{,2,3,5} ../sameframe_cd2_20261125/out; do shasum -a 256 \""'$d/REMOTE_ROWS_MD5.txt"; head -n 2 "$d/REMOTE_ROWS_MD5.txt"; done' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
../huang_steelman_20261124/hs_arms.py:133:def atomic_write_text(path: Path, text: str):
../huang_steelman_20261124/hs_arms.py:143:def check_thread_env() -> dict[str, str]:
../sameframe_cd2_20261125/sameframe_cd2.py:35:PARTA_RHOS = sf.PART1_RHOS
../sameframe_cd2_20261125/sameframe_cd2.py:36:PARTA_SNRS = sf.PART1_SNRS
../sameframe_cd2_20261125/sameframe_cd2.py:286:    stageA_base = sf.load_stageA_base(PARTA_RHOS)
../sameframe_cd2_20261125/sameframe_cd2.py:295:    for rho in PARTA_RHOS:
../sameframe_cd2_20261125/sameframe_cd2.py:342:        for rho in PARTA_RHOS:
../sameframe_cd2_20261125/sameframe_cd2.py:388:            partA_rhos=list(PARTA_RHOS),
../sameframe_cd2_20261125/sameframe_cd2.py:557:        partA_rhos=list(PARTA_RHOS),
../sameframe_cd2_20261125/sameframe_cd2.py:668:    stageA_base = sf.load_stageA_base(PARTA_RHOS)
../sameframe_cd2_20261125/sameframe_cd2.py:673:    hg_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in hg_arms}
../sameframe_cd2_20261125/sameframe_cd2.py:674:    hg_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
../sameframe_cd2_20261125/sameframe_cd2.py:677:            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
../sameframe_cd2_20261125/sameframe_cd2.py:687:                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
../sameframe_cd2_20261125/sameframe_cd2.py:698:    pA_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in new_arms}
../sameframe_cd2_20261125/sameframe_cd2.py:699:    pA_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
../sameframe_cd2_20261125/sameframe_cd2.py:702:            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
../sameframe_cd2_20261125/sameframe_cd2.py:715:                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
../sameframe_cd2_20261125/sameframe_cd2.py:757:        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, hg_fail[a])
../sameframe_cd2_20261125/sameframe_cd2.py:759:        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, pA_fail[a])
../sameframe_cd2_20261125/sameframe_cd2.py:783:            partA_rhos=list(PARTA_RHOS),
../sameframe_cd2_20261125/sameframe_cd2.py:851:    stageA_base = sf.load_stageA_base(PARTA_RHOS)
../huang_steelman_20261124/hs_analysis.py:59:def _nearest_rank(draws: np.ndarray, probability: float) -> float:
../sameframe_hg_20261124/sameframe.py:265:def load_stageA_base(rhos: tuple[int, ...] = PART1_RHOS) -> dict[tuple[str, int, int, int], dict[str, int]]:
41:RHOS = (100, 150, 200)
42:ALL_SNRS = (300, 400, 500)
43:DECIDE_SNR = 400
44:DECIDE_RHOS = (100, 150)
65:def own_md5() -> dict[str, str]:
69:def verify_pinned_deps() -> dict[str, str]:
79:def verify_freeze_commit_if_git(freeze_commit: str) -> bool:
103:def _used_cpu_seconds() -> float:
108:def _active_pids_cpu(pids: list[int]) -> float:
121:def precompute_delay_geometry(delays: np.ndarray, n: int, c1: float) -> dict[str, Any]:
139:def doppler_vectors(geom: dict[str, Any], nu: np.ndarray) -> np.ndarray:
145:def build_basis_matrix(geom: dict[str, Any], c_mat: np.ndarray, x_t: np.ndarray) -> np.ndarray:
151:def build_covariance_fast(
175:def sb_nll_and_grad(
231:def _mf_init(geom: dict[str, Any], x_t: np.ndarray, r: np.ndarray, step: float = 0.05) -> np.ndarray:
245:def _ls_coordinate_search(
286:            def obj(val: float) -> float:
322:def estimate_pw(geom: dict[str, Any], p_t: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
328:def estimate_kd(
342:def estimate_sb(
377:def doppler_metric(nu_hat: np.ndarray, nu_true: np.ndarray, g_true: np.ndarray) -> tuple[float, float, list[float]]:
387:def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
416:def _load_runtime():
427:def _g3_worker(in_path: str, out_path: str):
446:        m_sb, out_sb, _ = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
447:        m_pw, _, _ = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
451:        m_crb_sb = stageA4.metric(crb_sb, truth['g_i'])
456:def _g4_worker(in_path: str, out_path: str):
489:def cmd_gate(args):
512:    g1_keys = (('U', 100, 400, 41200), ('G', 150, 400, 41201), ('U', 200, 400, 41202), ('G', 100, 400, 41203))
579:        g4_jobs = [[41220, 'U', rho, 400] for rho in RHOS] + [[41221, 'G', rho, 400] for rho in RHOS]
587:    for snrs in ((300, 400, 500), (400,)):
588:        n_keys = len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(snrs)
630:def _run_shard_worker(shard_idx: int, draws: list[tuple[int, str]], snrs: tuple[int, ...], raw_dir: Path):
636:        for rho in RHOS:
655:                m_pw, o_pw, e_pw = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
656:                m_sb, o_sb, e_sb = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
657:                m_kd, o_kd, e_kd = doppler_metric(nu_kd, truth['k_real'], truth['g_i'])
661:                    metric=dict(PW=m_pw, SB=m_sb, KD=m_kd),
678:def verdict_a5(ci_lo: float, ci_hi: float) -> str:
686:def analyze_stageA5(
704:    M = np.full((len(ests), len(RHOS), len(snrs), n_frames, n_scen), np.nan, dtype=np.float64)
705:    O = np.full((len(ests), len(RHOS), len(snrs), n_frames, n_scen), np.nan, dtype=np.float64)
707:        ri = RHOS.index(int(r['rho']))
712:            M[ei, ri, si, f_idx, sc_idx] = float(r['metric'][e])
715:        raise RuntimeError('Incomplete Stage A5 metric grid')
717:    # Pair with Stage A4 CRB metrics on the exact same frames x scenarios
719:    B = np.full((len(a4_bounds), len(RHOS), len(snrs), n_frames, n_scen), np.nan, dtype=np.float64)
727:        ri = RHOS.index(int(r['rho']))
732:            B[bi, ri, si, f_idx, sc_idx] = float(r['metric'][bname])
742:    si_400 = snrs.index(DECIDE_SNR)
744:    ri_100, ri_150 = RHOS.index(100), RHOS.index(150)
745:    sb_100_f = M_frame[ei_sb, ri_100, si_400]
746:    sb_150_f = M_frame[ei_sb, ri_150, si_400]
760:        for ri, rho in enumerate(RHOS):
777:            for ri, rho in enumerate(RHOS) for si, snr in enumerate(snrs)
781:    for ri, rho in enumerate(RHOS):
818:def render_results_md(res: dict[str, Any]) -> str:
825:        f'- Draws: **{a["draws"]}** (frames `41000–41099` × U/G), SNRs: `{a["snrs"]}`',
838:    for rho in RHOS:
839:        k4 = f'{rho}_400'
855:def cmd_run(args):
896:    print(f'Launching Stage A5: {len(all_draws)} draws x {len(RHOS)} rhos x {len(snrs)} SNRs ({snrs}) on {n_shards} workers...', flush=True)
960:            rhos=list(RHOS),
991:def main():
../sameframe_cd2_20261125/out:
total 256
-rw-r--r--@ 1 guoyikun  staff   1444 Nov 25 01:19 REMOTE_ROWS_MD5.txt
-rw-r--r--@ 1 guoyikun  staff   4167 Nov 25 01:19 RESULTS.md
-rw-r--r--@ 1 guoyikun  staff      5 Nov 25 01:19 STATUS
-rw-r--r--@ 1 guoyikun  staff  17524 Nov 25 00:59 gate.json
-rw-r--r--@ 1 guoyikun  staff  17375 Nov 25 00:59 gate.log
-rw-r--r--@ 1 guoyikun  staff     19 Nov 25 00:59 gate_cpu.txt
-rw-r--r--@ 1 guoyikun  staff  14162 Nov 25 01:19 partA.log
-rw-r--r--@ 1 guoyikun  staff     22 Nov 25 01:19 partA_cpu.txt
-rw-r--r--@ 1 guoyikun  staff  26845 Nov 25 01:19 results.json
-rw-r--r--@ 1 guoyikun  staff   1155 Nov 25 01:19 timing.log
-rw-r--r--@ 1 guoyikun  staff     20 Nov 25 01:19 timing_cpu.txt
-rw-r--r--@ 1 guoyikun  staff   8577 Nov 25 01:19 timing_summary.json

out/stageA:
total 80
-rw-r--r--@ 1 guoyikun  staff   4560 Nov 21 02:14 REMOTE_ROWS_MD5.txt
-rw-r--r--@ 1 guoyikun  staff    349 Nov 21 02:14 RUN_CONFIG.json
-rw-r--r--@ 1 guoyikun  staff     16 Nov 21 02:14 STATUS
-rw-r--r--@ 1 guoyikun  staff   1490 Nov 21 02:14 results.json
-rw-r--r--@ 1 guoyikun  staff  18021 Nov 21 02:14 run.log

out/stageA2:
total 80
-rw-r--r--@ 1 guoyikun  staff   4560 Nov 21 11:10 REMOTE_ROWS_MD5.txt
-rw-r--r--@ 1 guoyikun  staff    350 Nov 21 11:10 RUN_CONFIG.json
-rw-r--r--@ 1 guoyikun  staff     15 Nov 21 11:10 STATUS
-rw-r--r--@ 1 guoyikun  staff   1850 Nov 21 11:10 results.json
-rw-r--r--@ 1 guoyikun  staff  18348 Nov 21 11:10 run.log

out/stageA3:
total 80
-rw-r--r--@ 1 guoyikun  staff   4560 Nov 21 13:43 REMOTE_ROWS_MD5.txt
-rw-r--r--@ 1 guoyikun  staff    415 Nov 21 13:43 RUN_CONFIG.json
-rw-r--r--@ 1 guoyikun  staff     16 Nov 21 13:43 STATUS
-rw-r--r--@ 1 guoyikun  staff   1994 Nov 21 13:43 results.json
-rw-r--r--@ 1 guoyikun  staff  18493 Nov 21 13:43 run.log

out/stageA5:
total 120
-rw-r--r--@ 1 guoyikun  staff   1368 Nov 25 02:07 REMOTE_ROWS_MD5.txt
-rw-r--r--@ 1 guoyikun  staff   1119 Nov 25 02:07 RESULTS.md
-rw-r--r--@ 1 guoyikun  staff      5 Nov 25 02:07 STATUS
-rw-r--r--@ 1 guoyikun  staff  12404 Nov 25 02:00 gate.log
-rw-r--r--@ 1 guoyikun  staff     19 Nov 25 02:00 gate_cpu.txt
-rw-r--r--@ 1 guoyikun  staff   8014 Nov 25 02:07 results.json
-rw-r--r--@ 1 guoyikun  staff  13133 Nov 25 02:07 run.log
-rw-r--r--@ 1 guoyikun  staff     22 Nov 25 02:07 run_cpu.txt
30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68  out/stageA/REMOTE_ROWS_MD5.txt
4ff578d51d0de33f9d2a1187b2d3e30c  rows_shard000.jsonl.gz
d4b794f3d038fa2012ac5978c6c2d2db  rows_shard001.jsonl.gz
5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354  out/stageA2/REMOTE_ROWS_MD5.txt
27b188b2c9606324ed31041f1c020249  rows_shard000.jsonl.gz
68f940c752f70281d569f3a2fcf7f57e  rows_shard001.jsonl.gz
6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a  out/stageA3/REMOTE_ROWS_MD5.txt
ce023e54f6494292ef45a0e0db887f80  rows_shard000.jsonl.gz
dbc17b5040d70f9f8db8a8bd48d8d55c  rows_shard001.jsonl.gz
bbbcb37b3fc946c2687c14b09897e10e6c69999e369689cdbf9820a7b76448e2  out/stageA5/REMOTE_ROWS_MD5.txt
dd22c0a0d6423773b32fbdef7be97c02  rows_shard000.jsonl.gz
6681386d8f1d2179e449fd358476b8b7  rows_shard001.jsonl.gz
86513c348dcef47a18cdaebb2bc6ade15e7b9f81b95c66ae832653309dae5a85  ../sameframe_cd2_20261125/out/REMOTE_ROWS_MD5.txt
3511a5289b2a83ad500bae4fe518de0b  partA_shard000.jsonl.gz
850d0e1432156c58ab9ad3526bb06df9  partA_shard001.jsonl.gz

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba ../huang_steelman_20261124/hs_arms.py | sed -n '126,167p'; nl -ba ../sameframe_hg_20261124/sameframe.py | sed -n '256,303p'; nl -ba ../huang_steelman_20261124/hs_analysis.py | sed -n '50,76p'; nl -ba stageA5.py | sed -n '630,669p'; cat out/stageA5/RESULTS.md; rg -n 'A6|40\\.0|420|480' ../../.trellis/tasks/11-21-data-pilot-fer --glob '*.md' | head -40" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   126	        p = HERE / name
   127	        if not p.is_file():
   128	            raise FileNotFoundError(f'Missing own experiment file: {p}')
   129	        out[name] = md5_file(p)
   130	    return out
   131	
   132	
   133	def atomic_write_text(path: Path, text: str):
   134	    """Write via temporary .part file + fsync + atomic os.replace."""
   135	    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
   136	    with partial.open('w', encoding='utf-8') as handle:
   137	        handle.write(text)
   138	        handle.flush()
   139	        os.fsync(handle.fileno())
   140	    os.replace(partial, path)
   141	
   142	
   143	def check_thread_env() -> dict[str, str]:
   144	    bad = [k for k in THREADS if os.environ.get(k) != '1']
   145	    if bad:
   146	        raise RuntimeError(f'Single-thread env vars must be 1, bad={bad}')
   147	    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
   148	        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty string for CPU-only execution')
   149	    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}
   150	
   151	
   152	def verify_frozen_extra_md5() -> dict[str, str]:
   153	    extra_md5 = {}
   154	    for rel, expected in FROZEN_EXTRA_MD5.items():
   155	        actual = md5_file(EXPERIMENTS / rel)
   156	        if actual != expected:
   157	            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
   158	        extra_md5[rel] = actual
   159	    return extra_md5
   160	
   161	
   162	def _load_module(name: str, path: Path):
   163	    spec = importlib.util.spec_from_file_location(name, path)
   164	    mod = importlib.util.module_from_spec(spec)
   165	    spec.loader.exec_module(mod)
   166	    return mod
   167	
   256	        passes_used=2,
   257	        pass1_errors=d1['errors'],
   258	        pass1_syndrome=syn1,
   259	        pass1_edits=len(res1.edits),
   260	        pass2_edits=len(res2.edits),
   261	        numerical_fallback=False,
   262	    )
   263	
   264	
   265	def load_stageA_base(rhos: tuple[int, ...] = PART1_RHOS) -> dict[tuple[str, int, int, int], dict[str, int]]:
   266	    """Load archived stageA arms.base (syndrome, f0_errors, errors) for requested rhos."""
   267	    base_dir = DATA_PILOT_DIR / 'out' / 'stageA'
   268	    out: dict[tuple[str, int, int, int], dict[str, int]] = {}
   269	    for p in sorted(base_dir.glob('rows_shard*.jsonl.gz')):
   270	        with gzip.open(p, 'rt', encoding='utf-8') as fh:
   271	            for line in fh:
   272	                r = json.loads(line)
   273	                rho = int(r['rho'])
   274	                if rho not in rhos:
   275	                    continue
   276	                k = (r['scenario'], rho, int(r['snr']), int(r['frame']))
   277	                b = r['arms']['base']
   278	                out[k] = dict(
   279	                    syndrome=int(b['syndrome']),
   280	                    f0_errors=int(b['f0_errors']),
   281	                    errors=int(b['errors']),
   282	                )
   283	    expected = len(PART1_FRAMES) * 2 * len(rhos) * len(PART1_SNRS)
   284	    if len(out) != expected:
   285	        raise RuntimeError(f'stageA base count mismatch: got {len(out)}, expected {expected}')
   286	    return out
   287	
   288	
   289	def _used_cpu_seconds() -> float:
   290	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   291	    return time.process_time() + ch.ru_utime + ch.ru_stime
   292	
   293	
   294	def _active_pids_cpu(pids: list[int]) -> float:
   295	    total = 0.0
   296	    for pid in pids:
   297	        try:
   298	            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
   299	            after = raw[raw.rfind(')') + 2:].split()
   300	            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
   301	        except OSError:
   302	            pass
   303	    return total
    50	
    51	
    52	def _minimum(bounds_list: list[Bounds]) -> Bounds:
    53	    return Bounds(
    54	        np.min([b.lower for b in bounds_list], axis=0),
    55	        np.min([b.upper for b in bounds_list], axis=0),
    56	    )
    57	
    58	
    59	def _nearest_rank(draws: np.ndarray, probability: float) -> float:
    60	    n = len(draws)
    61	    rank = min(n - 1, max(0, math.ceil(n * probability) - 1))
    62	    return float(np.partition(draws, rank)[rank])
    63	
    64	
    65	def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
    66	    return (
    67	        _nearest_rank(bounds.lower[1:], alpha / 2.0),
    68	        _nearest_rank(bounds.upper[1:], 1.0 - alpha / 2.0),
    69	    )
    70	
    71	
    72	def _represent(value: float) -> Any:
    73	    if np.isposinf(value):
    74	        return '+inf'
    75	    if np.isneginf(value):
    76	        return '-inf'
   630	def _run_shard_worker(shard_idx: int, draws: list[tuple[int, str]], snrs: tuple[int, ...], raw_dir: Path):
   631	    C, _, daft = _load_runtime()
   632	    st, ctx = C['stage3'], C['ctx']
   633	    c1, c2 = ctx.system.c1, ctx.system.c2
   634	    lines: list[str] = []
   635	    for frame, s in draws:
   636	        for rho in RHOS:
   637	            base = st.inputs(ctx, frame, s, rho)
   638	            for snr in snrs:
   639	                raw, _, truth = st.observed(ctx, base, rho, snr)
   640	                y = np.asarray(raw['y'], dtype=np.complex128)
   641	                p = np.asarray(raw['pilot'], dtype=np.complex128)
   642	                d = np.asarray(raw['data'], dtype=np.complex128)
   643	                sigma2 = float(raw['sigma2'])
   644	                vd = float(np.mean(np.abs(d) ** 2))
   645	                n = len(y)
   646	                r = daft(y, c1, c2, True)
   647	                p_t = daft(p, c1, c2, True)
   648	                x_t = daft(p + d, c1, c2, True)
   649	                geom = precompute_delay_geometry(truth['l_i'], n, c1)
   650	
   651	                nu_pw, g_pw = estimate_pw(geom, p_t, r)
   652	                nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
   653	                nu_kd, _ = estimate_kd(geom, x_t, r)
   654	
   655	                m_pw, o_pw, e_pw = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
   656	                m_sb, o_sb, e_sb = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   657	                m_kd, o_kd, e_kd = doppler_metric(nu_kd, truth['k_real'], truth['g_i'])
   658	
   659	                lines.append(json.dumps(dict(
   660	                    frame=frame, scenario=s, rho=rho, snr=snr,
   661	                    metric=dict(PW=m_pw, SB=m_sb, KD=m_kd),
   662	                    outlier_frac=dict(PW=o_pw, SB=o_sb, KD=o_kd),
   663	                    abs_err=dict(PW=e_pw, SB=e_sb, KD=e_kd),
   664	                ), allow_nan=False) + '\n')
   665	
   666	    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
   667	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   668	    with part_path.open('wb') as raw_fh:
   669	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
# Stage A5 Results: Semi-Blind Round-0 Doppler Proxy Check

- Freeze commit: `75530d4d2a953a9efc54c5d0771d840c2134a0af`
- Draws: **200** (frames `41000–41099` × U/G), SNRs: `[400]`
- Runtime: **1.9665 core-hours** (cap 6.0 h, wall 327.0 s)

## Primary Verdict (Pre-Registered, SNR = 4 dB)

- `E = min_{ρ ∈ {0.10, 0.15}} mean(SB)` = **0.0430 bin** (at ρ=0.15), 95% CI **[0.0408, 0.0455] bin** → **PASS** (threshold `0.08` bin)

## 4 dB Summary Table (Power-Weighted Capped MAE, bin; 200 Draws)

| ρ | PW mean [med] | SB mean [med] (95% CI) | KD mean [med] | SB-CRB | PW-CRB | SB Eff | PW Eff | SB Outlier >0.25 | Stage A Actual (4–5 dB) |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.0930 [0.0874] | **0.0527** [0.0472] ([0.0495, 0.0559]) | 0.0154 [0.0149] | 0.0398 | 0.0852 | 1.32× | 1.09× | 23.25% | 0.1568 |
| 0.15 | 0.0726 [0.0702] | **0.0430** [0.0408] ([0.0408, 0.0455]) | 0.0155 [0.0151] | 0.0369 | 0.0684 | 1.17× | 1.06× | 18.62% | 0.1079 |
| 0.20 | 0.0607 [0.0585] | **0.0376** [0.0361] ([0.0355, 0.0398]) | 0.0156 [0.0152] | 0.0346 | 0.0581 | 1.09× | 1.04× | 15.06% | 0.0824 |

exec
/bin/zsh -lc "rg -n 'def (time_refine|f0_state|observed|inputs)|"'^def setup|''^SNRS|''^PART1_'"' stageA.py ../sameframe_hg_20261124/sameframe.py ../ -g '*.py' | head -100; sed -n '100,153p' ../../CLAUDE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
../sameframe_hg_20261124/sameframe.py:36:PART1_RHOS = (100, 150, 200, 250)
../sameframe_hg_20261124/sameframe.py:37:PART1_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
../sameframe_hg_20261124/sameframe.py:38:PART1_FRAMES = tuple(range(41000, 41400))
../sameframe_hg_20261124/sameframe.py:39:PART1_BOOT_DRAWS = 2000
../sameframe_hg_20261124/sameframe.py:40:PART1_BOOT_SEED = 20261124
stageA.py:25:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
stageA.py:34:def setup():
../gamma0_exchange_20261120/phase1.py:179:            def observed_reopen(y, geometry_mean, variance, initial, **kwargs):
../sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_feedback_run.py:39:SNRS = (7, 8, 9)
../sbl_spectral_split_20261119/aggregate.py:21:SNRS = range(600, 1200, 100)
../cstate_necessity_stageA_20260928/keep_slots.py:23:def time_refine_keep_slots(y, pilot, mu, v, ls, ks, gs, c1, c2, noise,
../tf_cgr_mechanism_20260923/tf_base.py:83:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_h01.py:39:SNRS = (7, 8, 9)
../tf_cgr_mechanism_20260923/tf_cgr.py:83:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../data_pilot_fer_20261121/stageA3.py:21:SNRS = stageA2.SNRS
../data_pilot_fer_20261121/stageA.py:25:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
../data_pilot_fer_20261121/stageA.py:34:def setup():
../data_pilot_fer_20261121/stageA2.py:23:SNRS = (200, 250) + stageA.SNRS
../sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_scene_candidates.py:42:SNRS = (7, 8, 9)
../tf_cgr_mechanism_20260923/tf_sham.py:87:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../tf_e3b_offgrid_20261017/e3b_lib.py:30:SNRS = (600, 700, 800, 900, 1000, 1100)          # centi-dB
../data_pilot_fer_20261121/stageA4.py:27:SNRS = (300, 400, 500)
../data_pilot_fer_20261121/stage0.py:28:def setup():
../afdm_shared_channel_20261004/production_diagnostic.py:232:def observed_h_receive(observation, rt):
../sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:214:        def observed_scorer(Phi_t,y_t,S,candidates,sigma2):
../sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_s01.py:38:SNRS = (7, 8, 9)
../sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_detectors.py:37:def inputs(y,H,sigma,constellation,device):
../tf_mm_gamma_20261018/mm_agg.py:34:SNRS = (600, 700, 800)
../huang_steelman_20261124/hs_arms.py:28:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
../slot_mismatch_20261019/phase3_readout.py:23:SNRS = list(range(450, 801, 50))
../slot_mismatch_20261019/sm_driver.py:114:def f0_state(ctx, vr, obs, s):
../tf_mm_gamma_20261018/mm_driver.py:39:SNRS = (600, 700, 800)                 # centi-dB
../afdm_efficient_information/audit.py:97:def observed_polynomials(y):
../gate_sbl_test_20261119/run_main.py:38:def inputs(args):
../afdm_efficient_information/features.py:49:def observed_features(y_time):
../tf_cgr_mechanism_20260923_v2/tf_base.py:83:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../matched_ldpc_20261122/forest_minimal.py:17:SNRS = (750, 775)
../tf_cgr_mechanism_20260923_v2/tf_cgr.py:83:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../tf_gso_20261018/gso_lib.py:37:SNRS = b3lib.SNRS                                        # centi-dB 600..1100
../tf_cgr_mechanism_20260923_v2/tf_sham.py:87:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../tf_cstate_e1_20261017/e1_driver.py:169:def f0_state(ctx, obs):
../tf_cstate_e1_20261017/test_e1_agg.py:16:SNRS = (450, 500, 550, 600, 650, 700, 750, 800)
../f0_round_budget_20261118/screen.py:22:SNRS = (550,600,650,700,750,800,900)
../sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../rho_sweep_20261119/phase1.py:28:SNRS = tuple(sorted((*range(300, 1201, 100), 450, 550, 650)))
../rho_sweep_20261119/run_main.py:24:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
../afdm_higher_order_information/bridge.py:22:def observed_features(observation,c1,c2,physical):
../cstate_necessity_stageB_resume_20260928/f2_capture_qp.py:147:    def observed_active(delta, n):
../cstate_necessity_stageB_resume_20260928/f2_capture_qp.py:151:    def observed_grid(y, x, phi, delays, nus, mean, covariance, chosen,
../cstate_necessity_stageB_resume_20260928/f2_capture_qp.py:164:    def observed_minimize(objective, x0, *positional, **keyword):
../afdm_higher_order_information/features.py:21:def observed_features(y_daft, c1, c2, lags):
../sp_afdm_native_joint_20260921/src/twofft.py:82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../cstate_codelay_sbl_stage3_20261118/run.py:69:def inputs(ctx, frame, scenario, rho):
../cstate_codelay_sbl_stage3_20261118/run.py:74:def observed(ctx, base, rho, snr):
../tf_e3c_shrink_20261018/e3c_lib.py:32:SNRS = b3lib.SNRS                                   # centi-dB 600..1100
../admission_law_20261118/replay.py:234:def observed_kernel(kernel, observation):
../admission_law_20261118/run_main.py:23:SNRS = tuple(range(450, 701, 50))
../admission_law_20261118/gates.py:22:SNRS = tuple(range(450, 801, 50))
../headroom_ladder_20261008/driver.py:140:def setup_paths(args):
../sameframe_hg_20261124/sameframe.py:36:PART1_RHOS = (100, 150, 200, 250)
../sameframe_hg_20261124/sameframe.py:37:PART1_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
../sameframe_hg_20261124/sameframe.py:38:PART1_FRAMES = tuple(range(41000, 41400))
../sameframe_hg_20261124/sameframe.py:39:PART1_BOOT_DRAWS = 2000
../sameframe_hg_20261124/sameframe.py:40:PART1_BOOT_SEED = 20261124
../edit_budget_lowrho_20261119/report_main.py:20:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 1000)
../edit_budget_lowrho_20261119/run_main.py:24:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 1000)
../sigma2_stein_20261121/gate.py:19:SNRS = tuple(range(450, 801, 50))
../sigma2_stein_20261121/readout_stein.py:18:SNRS = tuple(range(450, 801, 50))
../sigma2_stein_20261121/run_stein.py:27:SNRS = tuple(range(450, 801, 50))
../sigma2_dd_20261118/qualify.py:21:SNRS = tuple(range(450, 801, 50))
../headroom_ladder_20261008/m2_cost.py:24:SNRS, FRAMES = 6, 1000
../sigma2_dd_20261118/run_main.py:20:SNRS = tuple(range(450, 801, 50))
../sbl_residual_gap_20261119/run_main.py:18:SNRS = (600, 700, 800, 900, 1000, 1100)
../gate_screen_20261119/s2.py:16:SNRS = (600, 700, 800, 900, 1000, 1100)
../gate_screen_20261119/run.py:77:def setup(leg, provenance):
../ratio_sweep_20261118/sweep.py:13:SNRS = (4.5, 5.5, 6.5, 7.5, 8.5, 10.)
../ratio_sweep_20261118/phase1b.py:138:        def observed(kernel):
../ratio_sweep_20261118/forced_miss.py:21:SNRS = (4.5, 5.5, 6.5, 7.5, 8.5)
../ratio_sweep_20261118/forced_miss.py:89:def f0_state(study, obs, excluded_delay):
../ratio_sweep_20261118/paired_scores.py:48:    def observed(*args, **opts):
../tf_research_discovery_pack_20260923/export_pack.py:104:def observed_geometry(raw: dict) -> tuple[list | None, list | None]:
../tf_e3_sbl_20261017/test_e3_agg.py:17:SNRS = (800, 900, 1000)
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_feedback_run.py:39:SNRS = (7, 8, 9)
../oamp_ldpc_20261109/replay.py:106:def observed_replay(out, evidence, system, code):
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:214:        def observed_scorer(Phi_t,y_t,S,candidates,sigma2):
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_s01.py:38:SNRS = (7, 8, 9)
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_detectors.py:37:def inputs(y,H,sigma,constellation,device):
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_scene_candidates.py:42:SNRS = (7, 8, 9)
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_h01.py:39:SNRS = (7, 8, 9)
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

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA.py | sed -n '20,85p'; nl -ba ../cstate_codelay_sbl_stage3_20261118/run.py | sed -n '62,104p'; nl -ba ../tf_cstate_e1_20261017/e1_driver.py | sed -n '165,215p'; nl -ba ../sp_afdm_native_joint_reviewed_20260921/src/twofft.py | sed -n '75,145p'; nl -ba stageA2.py | sed -n '169,189p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
    20	sys.path.insert(0, str(EXP / 'sp_afdm_frozen_20260920' / 'src'))
    21	
    22	FRAMES = range(41000, 41400)
    23	SCENARIOS = ('U', 'G')
    24	RHOS = (50, 100, 150, 200, 250, 300)
    25	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    26	ARMS = ('base', 'delay')
    27	FRAMES_PER_SHARD = 5
    28	WORKERS = 32
    29	TAU = 0.2
    30	BOOT, SEED, GATE_DB = 2000, 20261121, 0.3
    31	_C = None
    32	
    33	
    34	def setup():
    35	    global _C
    36	    if _C is None:
    37	        import cstate
    38	        from physical import regressors
    39	        ctx, full, cd, _ = cstate.context()
    40	        s = ctx.system; lmax = int(s.l_max_cap)
    41	        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
    42	        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
    43	        _C = dict(stage3=cstate.stage3, ctx=ctx, cd=cd, U=U / np.linalg.norm(U, axis=0, keepdims=True),
    44	                  lmax=lmax, orig_front=ctx.native.pilot_front)
    45	    return _C
    46	
    47	
    48	def f0(C, obs, inject=None):
    49	    """F0 with an optional round-0 support override; the native module's pilot_front is restored afterwards."""
    50	    ctx, orig = C['ctx'], C['orig_front']
    51	    if inject is None:
    52	        return C['stage3'].e1.f0_state(ctx, obs)
    53	
    54	    def front(observed, system, code):
    55	        s = orig(observed, system, code)
    56	        ls, ks, gs = inject
    57	        gs = np.ones(len(ls), complex) if gs is None else np.asarray(gs, complex)
    58	        return dict(s, delays=np.asarray(ls, int), dopplers=np.asarray(ks, float), gains=gs)
    59	    ctx.native.pilot_front = front
    60	    try:
    61	        return C['stage3'].e1.f0_state(ctx, obs)
    62	    finally:
    63	        ctx.native.pilot_front = orig
    64	
    65	
    66	def support_stats(delays, dopplers, truth, sigma2):
    67	    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.abs(np.asarray(truth['g_i'])) ** 2
    68	    rel = g >= TAU * sigma2
    69	    have = set(int(d) for d in delays)
    70	    miss = float(sum(g[i] for i in range(len(l)) if rel[i] and l[i] not in have))
    71	    err, wsum = 0.0, 0.0
    72	    for i in range(len(l)):
    73	        if l[i] in have:
    74	            cand = [float(dopplers[k]) for k, d in enumerate(delays) if int(d) == l[i]]
    75	            err += g[i] * min(abs(c - nu[i]) for c in cand); wsum += g[i]
    76	    return dict(missing_power=miss, doppler_err=err / wsum if wsum else None,
    77	                support_right=bool(all(l[i] in have for i in range(len(l)) if rel[i])))
    78	
    79	
    80	def one_arm(C, obs, truth, inject):
    81	    ctx, stage3 = C['ctx'], C['stage3']
    82	    dec, arrays, syndrome, _ = f0(C, obs, inject)
    83	    s2 = float(obs['sigma2'])
    84	    rec = dict(syndrome=int(syndrome),
    85	               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
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
   101	    if not syndrome:
   102	        return f0, None
   103	    branch = e1.run_branch(ctx, kernel, obs, arrays, 'A1')
   104	    return decoded(ctx, branch['decoder'], truth), branch
   165	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   166	    return dec, arrays, syn, time.perf_counter() - t0
   167	
   168	
   169	def f0_state(ctx, obs):
   170	    return receive_state(ctx, obs, 2)
   171	
   172	
   173	def run_a7(ctx, obs, arrays_ref):
   174	    """A7 = literal third F0 round (rounds=3 from scratch).  G5: every r0_*/r1_* array it exposes must equal the captured
   175	    rounds=2 state bitwise (r1_delays, r1_dopplers, r1_gains, r1_app, r1_check, r1_decoded, r1_input_llr, ce gains, moments, traces)."""
   176	    dec3, arrays3, syn3, seconds = receive_state(ctx, obs, 3)
   177	    keys = sorted(k for k in arrays_ref if k.startswith(('r0_', 'r1_')))
   178	    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
   179	    missing = sorted((required | set(keys)) - set(arrays3))
   180	    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
   181	            e1_lib.deep_equal({k: arrays_ref[k] for k in keys}, {k: arrays3[k] for k in keys}))
   182	    if not diff and gd.bits_sha(arrays3['r2_decoded']) != gd.bits_sha(dec3['decoded']):
   183	        diff = ['rounds=3 returned decoder differs from r2_decoded']
   184	    return dict(result=None, detector=None, decoder=dec3, arrays=arrays3, syndrome=syn3, seconds=seconds, g5_diff=diff, g5_keys=keys)
   185	
   186	
   187	def run_arm(ctx, kvar, obs, arrays, arm):
   188	    return run_a7(ctx, obs, arrays) if arm == 'A7' else run_branch(ctx, kvar, obs, arrays, arm)
   189	
   190	
   191	def run_branch(ctx, kvar, obs, arrays, arm):
   192	    """run_validation._branch (CSTATE20) with per-arm parameters; exclusive-stage timing kept.  A5 skips geometry entirely."""
   193	    from messages import moments
   194	    from physical import Channel, daft
   195	
   196	    spec, system, native = ARM_SPECS[arm], ctx.system, ctx.native
   197	    stamp = time.perf_counter()
   198	    app = np.clip(arrays['r1_app'], -20, 20)
   199	    check = np.clip(arrays['r1_check'], -20, 20)
   200	    if spec is None:
   201	        if len(arrays['r1_delays']) != len(arrays['r1_gains']):
   202	            raise ValueError('native physical slot count differs')
   203	        message_end = time.perf_counter()
   204	        channel = Channel(len(obs['y']), system.c1, system.c2, arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains'])
   205	        channel_end = time.perf_counter()
   206	        result, initial = None, None
   207	        stages = dict(message_handling=message_end - stamp, y_transform=0., **{k: 0. for k in GEOMETRY_STAGES},
   208	                      geometry_wrapper_overhead=0., wrapper_validation=0., channel_construction=channel_end - message_end)
   209	        mu = v = None
   210	    else:
   211	        mu, v, _ = moments(app, 1 - system.rho)
   212	        initial = [kvar.Path(int(delay), float(nu)) for delay, nu in zip(arrays['r1_delays'], arrays['r1_dopplers'])]
   213	        if len(initial) != len(arrays['r1_gains']):
   214	            raise ValueError('native physical slot count differs')
   215	        message_end = time.perf_counter()
    75	                          gain_precision_floor=bool(gain_precision<=1e-12),
    76	                          fft_count=2 if observation_domain=='time' else 4))
    77	        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    78	    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,fft_count=2*iterations+1 if observation_domain=='time' else 4*iterations)
    79	    if record_states:out['states']=states
    80	    return out
    81	
    82	def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
    83	    """Same frozen-q variable-projection objective, evaluated entirely in time.
    84	    Two fixed transforms per call. All candidate gains/Dopplers remain nonoracle.
    85	    """
    86	    n=len(y);ls=np.asarray(ls,int);ks=np.asarray(ks,float);gs=np.asarray(gs,complex)
    87	    unique=np.unique(ls);energy=np.array([np.sum(abs(gs[ls==d])**2) for d in unique]);l=unique[np.argsort(-energy)[:max_paths]]
    88	    centers=np.array([ks[np.flatnonzero(ls==d)[np.argmax(abs(gs[ls==d]))]] for d in l]);nu=centers.copy();k=np.arange(n)
    89	    xt=daft(np.asarray(pilot)+mu,c1,c2,True);Y=daft(y,c1,c2,True);wrap=k[:,None]-l
    90	    base=xt[wrap%n]*np.where(wrap<0,np.exp(2j*np.pi*c1*(n*n+2*n*wrap)),1.)
    91	    if mode not in ('mean','scalar','soft'):raise ValueError('mode')
    92	    vv=np.zeros(n) if mode=='mean' else np.full(n,np.mean(v)) if mode=='scalar' else np.asarray(v)
    93	    dl=l[None,:]-l[:,None];gv=np.exp(2j*np.pi*c1*(l[:,None]**2-l[None,:]**2))*np.fft.fft(vv)[dl%n];calls=0
    94	    def ev(nu):
    95	        nonlocal calls
    96	        calls+=1;B=base*np.exp(2j*np.pi*k[:,None]*nu/n)
    97	        G=gv*dkernel(nu[None,:]-nu[:,None]+2*n*c1*dl,n);G=(G+G.conj().T)*.5
    98	        Q=B.conj().T@B+G+noise*np.eye(len(l));b=B.conj().T@Y;h=np.linalg.solve(Q,b)
    99	        return float((np.vdot(Y,Y)-np.vdot(b,h)).real),h,G
   100	    val,h,G=ev(nu);history=[val]
   101	    for _ in range(rounds):
   102	        for j,z in enumerate(centers):
   103	            lo=max(-3.,z-.75);hi=min(3.,z+.75)
   104	            def f(z):
   105	                t=nu.copy();t[j]=z;return ev(t)[0]
   106	            opt=minimize_scalar(f,bounds=(lo,hi),method='bounded',options={'xatol':.002,'maxiter':16})
   107	            if opt.fun<val:nu[j]=opt.x;val,h,G=ev(nu);history.append(val)
   108	    val,h,G=ev(nu)
   109	    return Channel(n,c1,c2,l,nu,h),dict(history=history,objective=val,gamma=G,evaluations=calls,fft_count=3)
   169	
   170	def load(out, arms, rhos, snrs):
   171	    fi = {f: i for i, f in enumerate(FRAMES)}
   172	    fail = np.zeros((len(FRAMES), len(arms), len(SCENARIOS), len(rhos), len(snrs)), bool); seen = np.zeros_like(fail)
   173	    diag = []
   174	    for p in sorted(Path(out).glob('rows_shard*.jsonl.gz')):
   175	        with gzip.open(p, 'rt') as fh:
   176	            for line in fh:
   177	                r = json.loads(line)
   178	                if r['rho'] not in rhos or r['snr'] not in snrs:
   179	                    continue
   180	                for a, arm in enumerate(arms):
   181	                    j = (fi[r['frame']], a, SCENARIOS.index(r['scenario']), rhos.index(r['rho']), snrs.index(r['snr']))
   182	                    fail[j] = r['arms'][arm]['errors'] > 0; seen[j] = True
   183	                if 'full' in arms and r['arms']['full']['errors'] > 0:
   184	                    f = r['arms']['full']['final']
   185	                    diag.append(dict(support_right=f['support_right'], doppler_err=f['doppler_err'] or 0.,
   186	                                     r0_fail=r['arms']['full']['r0_errors'] > 0))
   187	    if not seen.all():
   188	        raise ValueError(f'incomplete grid in {out}')
   189	    return fail, diag

exec
/bin/zsh -lc "rg -n 'def core|import .*twofft|native=' ../cstate_codelay_sbl_stage3_20261118/run.py ../tf_cstate_e1_20261017/e1_driver.py; rg -n 'def .*raw|def .*draw|QPSK|constellation|sqrt\\(1["'^)]*rho|data ='"' ../cstate_codelay_sbl_stage3_20261118 ../tf_cstate_e1_20261017 -g '*.py' | head -45; nl -ba ../../.trellis/workflow.md | sed -n '1,115p'; cat ../../.trellis/tasks/11-21-data-pilot-fer/task.json" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
../cstate_codelay_sbl_stage3_20261118/run.py:116:def input_record(raw, obs):
     1	# Development Workflow
     2	
     3	---
     4	
     5	## Core Principles
     6	
     7	1. **Plan before code** — figure out what to do before you start
     8	2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
     9	3. **Persist everything** — research, decisions, and lessons all go to files; conversations get compacted, files don't
    10	4. **Incremental development** — one task at a time
    11	5. **Capture learnings** — after each task, review and write new knowledge back to spec
    12	
    13	---
    14	
    15	## Trellis System
    16	
    17	### Developer Identity
    18	
    19	On first use, initialize your identity:
    20	
    21	```bash
    22	python3 ./.trellis/scripts/init_developer.py <your-name>
    23	```
    24	
    25	Creates `.trellis/.developer` (gitignored) + `.trellis/workspace/<your-name>/`.
    26	
    27	### Spec System
    28	
    29	`.trellis/spec/` holds coding guidelines organized by package and layer.
    30	
    31	- `.trellis/spec/<package>/<layer>/index.md` — entry point with **Pre-Development Checklist** + **Quality Check**. Actual guidelines live in the `.md` files it points to.
    32	- `.trellis/spec/guides/index.md` — cross-package thinking guides.
    33	
    34	```bash
    35	python3 ./.trellis/scripts/get_context.py --mode packages   # list packages / layers
    36	```
    37	
    38	**When to update spec**: new pattern/convention found · bug-fix prevention to codify · new technical decision.
    39	
    40	### Task System
    41	
    42	Every task has its own directory under `.trellis/tasks/{MM-DD-name}/` holding `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, optional `research/`, and context manifests (`implement.jsonl`, `check.jsonl`) for sub-agent-capable platforms.
    43	
    44	```bash
    45	# Task lifecycle
    46	python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]
    47	python3 ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
    48	python3 ./.trellis/scripts/task.py current --source      # show active task and source
    49	python3 ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
    50	python3 ./.trellis/scripts/task.py archive <name>        # move to archive/{year-month}/
    51	python3 ./.trellis/scripts/task.py list [--mine] [--status <s>]
    52	python3 ./.trellis/scripts/task.py list-archive
    53	
    54	# Code-spec context (injected into implement/check agents via JSONL).
    55	# `implement.jsonl` / `check.jsonl` are seeded on `task create` for sub-agent-capable
    56	# platforms; the AI curates real spec + research entries during planning when needed.
    57	python3 ./.trellis/scripts/task.py add-context <name> <action> <file> <reason>
    58	python3 ./.trellis/scripts/task.py list-context <name> [action]
    59	python3 ./.trellis/scripts/task.py validate <name>
    60	
    61	# Task metadata
    62	python3 ./.trellis/scripts/task.py set-branch <name> <branch>
    63	python3 ./.trellis/scripts/task.py set-base-branch <name> <branch>    # PR target
    64	python3 ./.trellis/scripts/task.py set-scope <name> <scope>
    65	
    66	# Hierarchy (parent/child)
    67	python3 ./.trellis/scripts/task.py add-subtask <parent> <child>
    68	python3 ./.trellis/scripts/task.py remove-subtask <parent> <child>
    69	
    70	# PR creation
    71	python3 ./.trellis/scripts/task.py create-pr [name] [--dry-run]
    72	```
    73	
    74	> Run `python3 ./.trellis/scripts/task.py --help` to see the authoritative, up-to-date list.
    75	
    76	**Current-task mechanism**: `task.py create` creates the task directory and (when session identity is available) auto-sets the per-session active-task pointer so the planning breadcrumb fires immediately. `task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`. State is stored under `.trellis/.runtime/sessions/`. If no context key is available from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable, there is no active task and `task.py start` fails with a session identity hint. `task.py finish` deletes the current session file (status unchanged). `task.py archive <task>` writes `status=completed`, moves the directory to `archive/`, and deletes any runtime session files that still point at the archived task.
    77	
    78	### Workspace System
    79	
    80	Records every AI session for cross-session tracking under `.trellis/workspace/<developer>/`.
    81	
    82	- `journal-N.md` — session log. **Max 2000 lines per file**; a new `journal-(N+1).md` is auto-created when exceeded.
    83	- `index.md` — personal index (total sessions, last active).
    84	
    85	```bash
    86	python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash" --summary "Summary"
    87	```
    88	
    89	### Context Script
    90	
    91	```bash
    92	python3 ./.trellis/scripts/get_context.py                            # full session runtime
    93	python3 ./.trellis/scripts/get_context.py --mode packages            # available packages + spec layers
    94	python3 ./.trellis/scripts/get_context.py --mode phase --step <X.Y>  # detailed guide for a workflow step
    95	```
    96	
    97	---
    98	
    99	<!--
   100	  WORKFLOW-STATE BREADCRUMB CONTRACT (read this before editing the tag blocks below)
   101	
   102	  The [workflow-state:STATUS] blocks embedded in the ## Phase Index section
   103	  below are the SINGLE source of truth for the per-turn `<workflow-state>`
   104	  breadcrumb that every supported AI platform's UserPromptSubmit hook
   105	  reads. inject-workflow-state.py (Python platforms) and
   106	  inject-workflow-state.js (OpenCode plugin) only parse them — there is no
   107	  fallback dict baked into the scripts after v0.5.0-rc.0.
   108	
   109	  STATUS charset: [A-Za-z0-9_-]+. When the hook can't find a tag, it
   110	  degrades to a generic "Refer to workflow.md for current step." line —
   111	  intentionally visible so users notice and fix a broken workflow.md.
   112	
   113	  INVARIANT (test/regression.test.ts):
   114	    Every workflow-walkthrough step marked `[required · once]` must have a
   115	    matching enforcement line in its phase's [workflow-state:*] block. The
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
codex
已发现主跑后的归档读取会被信噪比网格不一致卡住。我再核对增益求解和截尾边界，确认还有哪些问题会阻止启动。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba ../sameframe_cd2_20261125/sameframe_cd2.py | sed -n '695,760p'; sed -n '1,65p' out/stageA/RUN_CONFIG.json; sed -n '1,65p' out/stageA2/RUN_CONFIG.json; ls -l /opt/anaconda3/bin/python; sed -n '1,75p' ../../.trellis/tasks/11-21-data-pilot-fer/implement.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   695	
   696	    # Load new Part A (CD2, optional CD2e8)
   697	    new_arms = ('CD2',) + (('CD2e8',) if include_cd2e8 else ())
   698	    pA_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in new_arms}
   699	    pA_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
   700	    for (s, rho, snr, f), b in stageA_base.items():
   701	        if b['syndrome'] == 0:
   702	            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
   703	            ef = b['f0_errors'] > 0
   704	            for a in new_arms:
   705	                pA_fail[a][ix] = ef
   706	            pA_seen[ix] = True
   707	
   708	    diag_acc = {a: dict(triggered=0, pass1_early_stop=0, pass2_ran=0, pass2_rescued=0, p1_edits=[], p2_edits=[]) for a in new_arms}
   709	    trig_count = 0
   710	    for idx in range(N_SHARDS):
   711	        sp = raw_dir / f'partA_shard{idx:03d}.jsonl.gz'
   712	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   713	            for line in fh:
   714	                r = json.loads(line)
   715	                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
   716	                if pA_seen[ix]:
   717	                    raise RuntimeError(f'Duplicate PartA key {r}')
   718	                for a in new_arms:
   719	                    rec = r['arms'][a]
   720	                    pA_fail[a][ix] = int(rec['errors']) > 0
   721	                    d = diag_acc[a]
   722	                    d['triggered'] += 1
   723	                    d['p1_edits'].append(int(rec['pass1_edits']))
   724	                    if int(rec['passes_used']) == 1:
   725	                        d['pass1_early_stop'] += 1
   726	                    else:
   727	                        d['pass2_ran'] += 1
   728	                        d['p2_edits'].append(int(rec['pass2_edits']))
   729	                        if int(rec['pass1_errors']) > 0 and int(rec['errors']) == 0:
   730	                            d['pass2_rescued'] += 1
   731	                pA_seen[ix] = True
   732	                trig_count += 1
   733	    if not pA_seen.all():
   734	        raise RuntimeError(f'Incomplete PartA grid: missing {int((~pA_seen).sum())}')
   735	
   736	    diag_stats = {
   737	        a: dict(
   738	            triggered=d['triggered'],
   739	            pass1_early_stop=d['pass1_early_stop'],
   740	            pass2_ran=d['pass2_ran'],
   741	            pass2_rescued=d['pass2_rescued'],
   742	            mean_pass1_edits=float(np.mean(d['p1_edits'])) if d['p1_edits'] else 0.0,
   743	            mean_pass2_edits_when_ran=float(np.mean(d['p2_edits'])) if d['p2_edits'] else 0.0,
   744	        )
   745	        for a, d in diag_acc.items()
   746	    }
   747	
   748	    fail_by_arm = {
   749	        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
   750	        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
   751	        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
   752	        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
   753	    }
   754	    for i, a in enumerate(stageA3.ARMS):
   755	        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
   756	    for a in hg_arms:
   757	        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, hg_fail[a])
   758	    for a in new_arms:
   759	        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, pA_fail[a])
   760	
{
 "_argv": [
  "stageA.py",
  "run",
  "--out",
  "out/stageA"
 ],
 "frames": [
  41000,
  41399
 ],
 "scenarios": [
  "U",
  "G"
 ],
 "rhos": [
  50,
  100,
  150,
  200,
  250,
  300
 ],
 "snrs": [
  300,
  400,
  450,
  500,
  550,
  600,
  650,
  700,
  800,
  900,
  1000,
  1100,
  1200
 ],
 "arms": [
  "base",
  "delay"
 ],
 "workers": 32
}{
 "_argv": [
  "stageA2.py",
  "run",
  "--out",
  "out/stageA2"
 ],
 "frames": [
  41000,
  41399
 ],
 "scenarios": [
  "U",
  "G"
 ],
 "rhos": [
  50,
  100,
  150,
  200
 ],
 "snrs": [
  200,
  250,
  300,
  400,
  450,
  500,
  550,
  600,
  650,
  700,
  800,
  900,
  1000,
  1100,
  1200
 ],
 "arms": [
  "full",
  "ldop"
 ],
 "workers": 32
}lrwxr-xr-x  1 guoyikun  staff  10 Sep 19  2025 /opt/anaconda3/bin/python -> python3.13
# Implementation plan（v2，待 Eric 批）

代码放 `experiments/data_pilot_fer_<date>/`，复用 `rho_sweep_20261119` 与 `data_autocorr_acq_20261121/calc2.py` 的已有实现；需要整份复制时，文件开头写一行来源、改动和不能直接调用的原因。

1. **读管线**：确认 ρ 扫描里 F0 + CSTATE 的入口、物理 ρ 的归一化，以及 `pilot_front` → `time_refine` 的接口。检查：能在旧键上复现 ρ 扫描行（G1）。
2. **注入点**：写一个包装函数，替换第 0 轮送进 `time_refine` 的 (ls, ks, gs)。A-delay 用真时延（多普勒中心取可观测量）；B-rank、B-challenge 用自相关候选。下游一律不改。检查：注入"`pilot_front` 原样输出"时与基线逐位相同（G2）。
3. **候选生成 + 阶段 0 预检（零接收机）**〔Astra〕：写只用观测量的候选选择器（先按峰值排序，再看真值；消镜像；去重；K = 8）。在第二步读数用过的帧上，统计两个量：(a) 基线第 0 轮实际漏掉的有效弱径中，有多少进了候选表；(b) 候选表里有多少是真时延。判读冻结后再算；(a) < .25 就停，不进入改接收机的步骤。
4. **选帧**：用存档帧扫描器选一块未用过的 400 帧（G4）。
5. **冒烟与成本**：16 帧 × 全部格子，外推核时，加 30% 余量。
6. **冻结**：PROTOCOL.md（判读、预测、premortem），Astra 审后提交，再运行（research-checkpoint 第 1 时刻）。
7. **阶段 0 预检 → 阶段 A 运行与读数** → 按冻结规则决定是否进入阶段 B。
8. **阶段 B 运行与读数**；预测打分；STATE、台账；结论由 Eric 定。

审查节点：第 6 步前给 Astra 审一次；第 7 步的读数报给 Eric 后再进入第 8 步。

exec
/bin/zsh -lc "sed -n '1,60p' stageA.py; rg -n 'def context|native|frozen' ../cstate_codelay_sbl_stage3_20261118/cstate.py ../tf_cstate_e1_20261017/e1_driver.py; rg -n 'def time_refine|np.argsort\\(-energy\\)|time_refine\\(' ../sp_afdm_frozen_20260920/src -g '*.py'; rg -n 'def observe|def score|def base\\(' ../tf_cstate_e1_20261017/e1_driver.py ../cstate_codelay_sbl_stage3_20261118/*.py; sed -n '120,142p' stageA5.py; sed -n '15,70p' ../sameframe_hg_20261124/sameframe.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
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
rg: ../cstate_codelay_sbl_stage3_20261118/cstate.py: No such file or directory (os error 2)
../tf_cstate_e1_20261017/e1_driver.py:4:--mode select  scan the frozen P1 ledger (arms.B.triggered) for the given SNRs and write triggered_keys.json (the unit list).
../tf_cstate_e1_20261017/e1_driver.py:6:               (native_twofft.receive rounds=2 iterations=20 soft/joint), assert G4a (syndrome != 0), then run arms A1..A6 from that
../tf_cstate_e1_20261017/e1_driver.py:18:  A7 literal third F0 round: native_twofft.receive(rounds=3, ...) from scratch on the same observation (PROTOCOL.md section 10, O2);
../tf_cstate_e1_20261017/e1_driver.py:20:Nothing frozen is edited; the Gamma variant lives in geometry_*_variant.py.
../tf_cstate_e1_20261017/e1_driver.py:57:A7_SPEC = 'native_twofft.receive rounds=3 iterations=20 ce_mode=soft gain_mode=joint from scratch; G5 compares all r0_*/r1_* arrays with the rounds=2 state'
../tf_cstate_e1_20261017/e1_driver.py:70:def check_frozen_md5(ctx):
../tf_cstate_e1_20261017/e1_driver.py:94:        raise RuntimeError(f'frozen source md5 mismatch: {bad}')
../tf_cstate_e1_20261017/e1_driver.py:110:               schedule='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint; branch: scalar_joint iterations=20 damping=.3 '
../tf_cstate_e1_20261017/e1_driver.py:115:               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment)
../tf_cstate_e1_20261017/e1_driver.py:164:    dec, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=rounds, iterations=20, ce_mode='soft', gain_mode='joint')
../tf_cstate_e1_20261017/e1_driver.py:196:    spec, system, native = ARM_SPECS[arm], ctx.system, ctx.native
../tf_cstate_e1_20261017/e1_driver.py:202:            raise ValueError('native physical slot count differs')
../tf_cstate_e1_20261017/e1_driver.py:214:            raise ValueError('native physical slot count differs')
../tf_cstate_e1_20261017/e1_driver.py:242:    detector = native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - system.rho, prior=check,
../tf_cstate_e1_20261017/e1_driver.py:245:    decoder = native.decoder_messages(ctx.code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
../tf_cstate_e1_20261017/e1_driver.py:267:        top5 = [dict(rank=int(t['rank']), slot=int(t['slot']), replacement=t['replacement'], score=float(t['frozen_score']))
../tf_cstate_e1_20261017/e1_driver.py:414:                    # G1 (real state): frozen production branch vs variant A1 (full), triggered AND untriggered states
../tf_cstate_e1_20261017/e1_driver.py:415:                    prod = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
../sp_afdm_frozen_20260920/src/physical.py:33:    unique=np.unique(lq);energy=np.array([np.sum(abs(gq[lq==d])**2) for d in unique]);ls=unique[np.argsort(-energy)[:max_paths]]
../cstate_codelay_sbl_stage3_20261118/run.py:74:def observed(ctx, base, rho, snr):
# --------------------------------------------------------------------------- Core math & estimators
def precompute_delay_geometry(delays: np.ndarray, n: int, c1: float) -> dict[str, Any]:
    """Precompute delay-dependent chirp phase cp_i[k] and shifted column indices matching stageA4.model."""
    k = np.arange(n, dtype=np.int64)
    l_arr = np.asarray(delays, dtype=np.int64)
    p = len(l_arr)
    cols = np.empty((p, n), dtype=np.int64)
    cp = np.empty((p, n), dtype=np.complex128)
    for i, li in enumerate(l_arr):
        cols[i] = (k - li) % n
        cp[i] = np.where(k < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (k - li))), 1.0 + 0j)
    # Cross-index shift for T @ T^H: entry (k, (k - l_i + l_j) % n)
    cross_col = np.empty((p, p, n), dtype=np.int64)
    for i in range(p):
        for j in range(p):
            cross_col[i, j] = (k - l_arr[i] + l_arr[j]) % n
    return dict(n=n, p=p, k=k, k_norm=2j * np.pi * k / float(n), delays=l_arr, cols=cols, cp=cp, cross_col=cross_col)


def doppler_vectors(geom: dict[str, Any], nu: np.ndarray) -> np.ndarray:
    """Return c[p, n] where c[i, k] = cp_i[k] * exp(2j*pi*k*nu_i/n), exact match to stageA4.model."""
    nu_arr = np.asarray(nu, dtype=np.float64)
    return geom['cp'] * np.exp(nu_arr[:, None] * geom['k_norm'][None, :])
import resource
import shutil
import sys
import time
from types import FunctionType, SimpleNamespace
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
DATA_PILOT_DIR = EXP / 'data_pilot_fer_20261121'
HUANG_DIR = EXP / 'huang_steelman_20261124'
RHO_SWEEP_DIR = EXP / 'rho_sweep_20261119'

sys.path.insert(0, str(DATA_PILOT_DIR))
sys.path.insert(0, str(HUANG_DIR))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402

PART1_RHOS = (100, 150, 200, 250)
PART1_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
PART1_FRAMES = tuple(range(41000, 41400))
PART1_BOOT_DRAWS = 2000
PART1_BOOT_SEED = 20261124
P1_THRESHOLD_DB = 0.5
P2_THRESHOLD_DB = 0.2

ARCHIVE_MANIFESTS = {
    'stageA': (DATA_PILOT_DIR / 'out' / 'stageA', '30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68'),
    'stageA2': (DATA_PILOT_DIR / 'out' / 'stageA2', '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354'),
    'stageA3': (DATA_PILOT_DIR / 'out' / 'stageA3', '6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a'),
    'rho_sweep': (RHO_SWEEP_DIR / 'out' / 'main_20261119', ar.RHO_ARCHIVE_MD5_SHA256),
    'huang': (HUANG_DIR / 'out', 'b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc'),
}
OWN_FILES = ('PROTOCOL.md', 'sameframe.py', 'test_sameframe.py', 'launch.sh')
WORKERS = 24
BUDGET_CAP_HOURS = 16.0
BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.25
BUDGET_EXIT_CODE = 124
N_SHARDS = 24
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_manifest(name: str) -> dict[str, str]:
    base_dir, expected_sha = ARCHIVE_MANIFESTS[name]
    manifest = base_dir / 'REMOTE_ROWS_MD5.txt'
    got_sha = ar.sha256_file(manifest)
    if got_sha != expected_sha:

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'snrs|by_snr|by_rho' out/stageA5/results.json | head -25; rg -n 'def (observe|base)\\(' ../tf_cstate* ../tf_e3b_offgrid_20261017 ../headroom_ladder_20261008 -g '*.py' | head -40; nl -ba ../sameframe_cd2_20261125/sameframe_cd2.py | sed -n '30,41p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
27:    "snrs": [
72:      "snrs": [
92:    "snrs": [
../tf_e3b_offgrid_20261017/e3b_driver.py:210:def observe(ctx, base, scenario, rho_pm, snr, frame, gen_seconds):
../headroom_ladder_20261008/unit_check_c1A.py:55:        def observe(value, *args, **kwargs):
../headroom_ladder_20261008/unit_check_c1ACC.py:40:    def observe(step):
../headroom_ladder_20261008/driver.py:227:def observe(raw, rho, snr_db):
    30	
    31	import hs_analysis as an  # noqa: E402
    32	import hs_arms as ar  # noqa: E402
    33	import sameframe as sf  # noqa: E402
    34	
    35	PARTA_RHOS = sf.PART1_RHOS
    36	PARTA_SNRS = sf.PART1_SNRS
    37	PARTA_FRAMES = sf.PART1_FRAMES
    38	BOOT_DRAWS = 2000
    39	BOOT_SEED = 20261125
    40	P1P_THRESHOLD_DB = 0.5
    41	WORKERS = 24

exec
/bin/zsh -lc "rg -n 'def context|native|load|stage3' ../unified_cov_prospective_20261119/cstate.py | head -40; sed -n '20,47p' ../tf_cstate_e1_20261017/e1_driver.py; rg -n 'def time_refine|energy=np|energy =' ../sp_afdm_native_joint_20260921/src/twofft.py ../sp_afdm_frozen_20260920 -g '*.py' | head -28; rg -n 'def observe\\(|def base\\(|def score\\(|time_refine\\(' ../tf_cstate_e1_20261017 ../sp_afdm_native_joint_20260921 ../sp_afdm_native_joint_reviewed_20260921 --glob '*.py' | head -42; rg -n 'THREADS =|set_num_threads' ../huang_steelman_20261124/hs_arms.py ../unified_cov_prospective_20261119/cstate.py ../tf_cstate_e1_20261017/e1_driver.py; sed -n '365,386p' stageA5.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
15:STAGE3 = Path(__file__).resolve().parents[1] / 'cstate_codelay_sbl_stage3_20261118'
17:spec = importlib.util.spec_from_file_location('stage3_codelay_run', STAGE3 / 'run.py')
18:stage3 = importlib.util.module_from_spec(spec)
19:spec.loader.exec_module(stage3)
25:def context():
26:    return stage3.context()
255:                           gains_sha=stage3.digest(result.gains), gamma_sha=stage3.digest(result.diagnostics['gamma']),
339:    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
341:    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
343:    f0 = stage3.decoded(ctx, dec, truth)
361:        br = stage3.e1.run_branch(ctx, kernel, obs, arrays, 'A2' if name == 'A2' else 'A1')
364:        rows[name] = dict(**stage3.decoded(ctx, br['decoder'], truth),
378:               truth=stage3.truth_record(obs, truth), inputs=stage3.input_record(raw, obs), arms=rows)
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
../sp_afdm_native_joint_20260921/src/twofft.py:82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../sp_afdm_native_joint_20260921/src/twofft.py:87:    unique=np.unique(ls);energy=np.array([np.sum(abs(gs[ls==d])**2) for d in unique]);l=unique[np.argsort(-energy)[:max_paths]]
../sp_afdm_frozen_20260920/src/physical.py:33:    unique=np.unique(lq);energy=np.array([np.sum(abs(gq[lq==d])**2) for d in unique]);ls=unique[np.argsort(-energy)[:max_paths]]
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_trainer.py:104:    ce_energy = y_ce_labels.pow(2)
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/drce_baseline/drce_receiver.py:101:      Total pilot energy = rho*N (spread); total data energy = (1-rho)*N.
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/drce_baseline/drce_receiver.py:107:      Total pilot energy = rho*N (matches SP);
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/drce_baseline/drce_receiver.py:108:      Total data energy = (1-rho)*N (matches SP);
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/drce_baseline/drce_receiver.py:109:      Total frame energy = N (matches SP).
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py:1063:        mean_col_energy = np.real(np.sum(np.abs(H_d) ** 2)) / max(n_d, 1)
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/bandlimited_estimation.py:63:    energy = float(np.vdot(h,h).real)
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/representation_ledger.py:89:    energy = H.abs().square()
../sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_g1.py:55:    kept_energy = 0.
../sp_afdm_native_joint_20260921/src/native_twofft.py:20:        c,detail=time_refine(observation['y'],observation['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,observation['sigma2'],mode=ce_mode,max_paths=8,rounds=2)
../sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:20:        c,detail=time_refine(observation['y'],observation['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,observation['sigma2'],mode=ce_mode,max_paths=8,rounds=2)
../sp_afdm_native_joint_20260921/src/twofft.py:82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
../sp_afdm_native_joint_20260921/src/native_controls.py:34:        channel, detail = time_refine(
../sp_afdm_native_joint_reviewed_20260921/src/native_controls.py:34:        channel, detail = time_refine(
../sp_afdm_native_joint_20260921/tests/screen_fair_controls.py:24:  t=time.perf_counter();c,det=time_refine(obs['y'],obs['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,obs['sigma2'],mode=ce);tc=time.perf_counter()-t;t=time.perf_counter()
../sp_afdm_native_joint_reviewed_20260921/tests/screen_fair_controls.py:24:  t=time.perf_counter();c,det=time_refine(obs['y'],obs['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,obs['sigma2'],mode=ce);tc=time.perf_counter()-t;t=time.perf_counter()
../sp_afdm_native_joint_20260921/tests/test_twofft.py:54: c1,r1=time_refine(y,p,mu,v,c.delays,np.rint(c.dopplers),c.gains,c.c1,c.c2,.18,mode=mode,rounds=2)
../sp_afdm_native_joint_reviewed_20260921/tests/test_twofft.py:54: c1,r1=time_refine(y,p,mu,v,c.delays,np.rint(c.dopplers),c.gains,c.c1,c.c2,.18,mode=mode,rounds=2)
../huang_steelman_20261124/hs_arms.py:33:THREADS = (
        method='L-BFGS-B',
        jac=True,
        bounds=bounds,
        options={'maxiter': maxiter, 'ftol': ftol, 'gtol': 1e-6},
    )
    nu = np.asarray(res.x[:p], dtype=np.float64)
    g = np.asarray(res.x[p:2 * p] + 1j * res.x[2 * p:3 * p], dtype=np.complex128)
    if not (np.isfinite(nu).all() and np.isfinite(g).all()):
        raise FloatingPointError('Nonfinite output in SB estimator')
    return nu, g


def doppler_metric(nu_hat: np.ndarray, nu_true: np.ndarray, g_true: np.ndarray) -> tuple[float, float, list[float]]:
    """A3/A4 power-weighted capped MAE + outlier (>0.25 bin) path fraction."""
    abs_err = np.abs(np.asarray(nu_hat, dtype=np.float64) - np.asarray(nu_true, dtype=np.float64))
    pw = np.abs(np.asarray(g_true, dtype=np.complex128)) ** 2
    val = float(np.sum(pw * np.minimum(abs_err, CAP)) / np.sum(pw))
    out_frac = float(np.mean(abs_err > OUTLIER_THRESH))
    return val, out_frac, abs_err.tolist()


# --------------------------------------------------------------------------- File-IPC worker helper

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba stageA6.py | sed -n '413,429p'; rg -n 'cleanup|trap|TMPDIR|TORCH' stageA5_launch.sh ../sameframe_cd2_20261125/*.sh; sed -n '1,60p' ../sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py; git -c core.fsmonitor=false rev-parse --show-toplevel" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   413	        geom = stageA5.precompute_delay_geometry(truth['l_i'], len(y), c1)
   414	        nu_pw, g_pw = stageA5.estimate_pw(geom, p_t, r_td)
   415	        nu_sb, _ = stageA5.estimate_sb(geom, p_t, r_td, float(np.mean(np.abs(d) ** 2)), float(raw['sigma2']), nu_pw, g_pw)
   416	        m_sb, _, e_sb = stageA5.doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
   417	        ref = a5_ref[(frame, s, rho, snr)]
   418	        max_abs_diff = float(np.max(np.abs(np.asarray(e_sb) - np.asarray(ref['abs_err']['SB']))))
   419	        metric_diff = float(abs(m_sb - float(ref['metric']['SB'])))
   420	        ok = bool(max_abs_diff < 1e-6 and metric_diff < 1e-6)
   421	        g2_rows.append(dict(
   422	            key=[frame, s, rho, snr],
   423	            passed=ok,
   424	            max_abs_err_diff=max_abs_diff,
   425	            metric_diff=metric_diff,
   426	        ))
   427	    g2_pass = bool(len(g2_rows) == 4 and all(x['passed'] for x in g2_rows))
   428	    print(f'G2 {"PASS" if g2_pass else "FAIL"} max_diff={max(x["max_abs_err_diff"] for x in g2_rows):.2e}', flush=True)
   429	
stageA5_launch.sh:38:export TMPDIR="/data/guoyikun/tmp"
stageA5_launch.sh:48:    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
stageA5_launch.sh:63:    cleanup() {
stageA5_launch.sh:68:    trap cleanup EXIT
../sameframe_cd2_20261125/launch.sh:37:export TMPDIR="/data/guoyikun/tmp"
../sameframe_cd2_20261125/launch.sh:47:    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
../sameframe_cd2_20261125/launch.sh:62:    cleanup() {
../sameframe_cd2_20261125/launch.sh:67:    trap cleanup EXIT
"""Complete observed-input native pipeline using an existing frozen pilot initializer.
No truth accepted. The initial 515-column dictionary is NOT charged as O(NP) memory.
No I1 outer loop is used. Code construction is an amortized static operation.
"""
import time
import numpy as np
from receiver import pilot_front,decoder_messages
from messages import moments
from twofft import time_refine,scalar_joint

def receive(observation,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint',checkpoint_sink=None,record_states=False):
    if len(observation['y'])!=1024 or system.rho!=.5:raise ValueError('frozen native interface: N=1024, rho=0.5')
    if rounds<1:raise ValueError('at least one coded round required')
    if checkpoint_sink is not None and not callable(checkpoint_sink):raise TypeError('checkpoint_sink must be callable')
    if set(observation)-{'y','pilot','sigma2'}:raise ValueError('Only observed inputs are accepted')
    st=time.perf_counter();s=pilot_front(observation,system,code);tp=time.perf_counter()-st
    arrays={};events=[]
    for r in range(rounds):
        t=time.perf_counter()
        c,detail=time_refine(observation['y'],observation['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,observation['sigma2'],mode=ce_mode,max_paths=8,rounds=2)
        tc=time.perf_counter()-t;t=time.perf_counter()
        o=scalar_joint(observation['y'],observation['pilot'],c,observation['sigma2'],pd=1-system.rho,prior=s['prior'],iterations=iterations,gain_mode=gain_mode,record_states=record_states)
        ti=time.perf_counter()-t;t=time.perf_counter()
        dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50)
        td=time.perf_counter()-t;s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20)
        s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),1-system.rho)
        s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o['gains']
        events.append(dict(round=r,ce=tc,inference=ti,decoder=td,ready=time.perf_counter()-st,decoder_iterations=int(dec['iterations']),inference_iterations=iterations,ce_evaluations=detail['evaluations'],inference_fft_count=o['fft_count'],ce_fft_count=detail['fft_count']))
        round_arrays={'decoded':dec['decoded'],'input_llr':dec['incoming_llr'],'app':dec['raw_app'],
                      'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,
                      'gains':o['gains'],'gain_variance':o['gain_variance'],'ce_gains':c.gains,
                      'mu':o['mu'],'variance':o['variance'],'ce_history':np.array(detail['history']),
                      'ce_gamma':detail['gamma'],'inference_trace':o['trace']}
        if record_states:round_arrays['inference_states']=o['states']
        arrays.update({f'r{r}_{k}':v for k,v in round_arrays.items()})
        # Optional caller-owned checkpoint capture survives a later numerical failure.
        # It must not change decisions; any callback cost remains in complete time.
        if checkpoint_sink is not None:
            checkpoint_sink(dict(events[-1],snapshot=round_arrays), dec['decoded'].copy())
    return dec,arrays,dict(seconds=time.perf_counter()-st,pilot_seconds=tp,events=events)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-iJ9X3biR' (errno=Operation not permitted)
/Users/guoyikun/Downloads/share/claode_birain/my-vault

exec
/bin/zsh -lc "rg -n 'def context|native|code' ../cstate_codelay_sbl_stage3_20261118/run.py | head -26; rg -n 'def observe|def score|native|raw\\[' ../tcom_genie_support_20261016/gs_driver.py | head -45; rg -n 'def base|native|generate' ../tcom_reference_frame_20261015/*.py | head -45; rg -n 'def generate|constellation|data =|data=' ../sp_afdm_native_joint_reviewed_20260921/src ../sp_afdm_frozen_20260920/src --glob '*.py' | head -55; rg -n '40|A6' ../../research-assets/prediction-ledger.md | tail -23" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
12:import codelay
27:              native_twofft='d47af1373b2f0052e6de078de40711ba',
49:def context():
57:    route = codelay.load(full)
82:    h.update(str(a.dtype).encode())
83:    h.update(repr(a.shape).encode())
94:def decoded(ctx, output, truth):
95:    bits = output['decoded']
97:    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))
104:    return decoded(ctx, branch['decoder'], truth), branch
118:                coded=digest(raw['coded']), noise=digest(raw['noise']), data=digest(raw['data']))
124:    f0 = decoded(ctx, dec, truth)
126:    b, codelay_branch = arm(ctx, route, obs, truth, arrays, syndrome, f0)
130:                codelay_geometry=path_records(codelay_branch))
174:        f0 = decoded(ctx, dec, truth)
175:        assert syndrome and syndrome == unit['f0_syndrome'] and f0['decoded_sha'] == unit['f0_sha']
177:        assert legacy['errors'] == unit['b_info_errors'] and legacy['decoded_sha'] == unit['b_sha']
183:                           final_objective_delta=discrepancy, decoded_sha=got['decoded_sha']))
8:Both run native_twofft.receive (rounds=2, iterations=20, soft CE, joint gains) through interventions._instrumented with only
53:    return ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm=arm, rounds=2, iterations=20,
57:def observe(ctx, raw_base, diag_base, rho, snr_centi):
62:def score(ctx, decoded, truth):
135:                  schedule='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint; no CSTATE',
155:                        n = len(raw['y'])
160:                                   snr_db=snr_centi / 100, frame=int(frame), sigma2=float(raw['sigma2']),
../tcom_reference_frame_20261015/p2b_driver.py:104:        bases[rho] = P.generate(ctx, FLAGS_S, rho, snr_centis[0] / 100, frame, seed_fn)
../tcom_reference_frame_20261015/p1_gates.py:152:        raw_base, diag_base = P.generate(ctx, flags, .5, 4.5, frame, seed_fn)
../tcom_reference_frame_20261015/p1_gates.py:254:                raw_base, diag_base = P.generate(ctx, scenario, .3, 4.5, frame, seed_fn)
../tcom_reference_frame_20261015/p1_gates.py:262:                cells.append(dict(scenario=scenario, snr=snr, frame=frame, generate_seconds=gen_seconds, cell_seconds=cell,
../tcom_reference_frame_20261015/p1_gates.py:275:                generate_seconds_mean=float(np.mean([c['generate_seconds'] for c in sel])),
../tcom_reference_frame_20261015/p1_gates.py:286:        cost = np.interp(grid, [G4_SNR[0], G4_SNR[1]], [lo['cell_seconds_mean'] + lo['generate_seconds_mean'] / len(grid),
../tcom_reference_frame_20261015/p1_gates.py:287:                                                       hi['cell_seconds_mean'] + hi['generate_seconds_mean'] / len(grid)])
../tcom_reference_frame_20261015/p1_gates.py:354:        L.append(f"| {k} | {v['n']} | {v['cell_seconds_mean']:.3f} | {v['generate_seconds_mean']:.3f} | " + ' | '.join(f"{a[x]:.3f}" for x in P.ALL_ARMS)
../tcom_reference_frame_20261015/gen_fixed.py:4:  headroom_ladder_20261008/driver.py::generate_base
../tcom_reference_frame_20261015/gen_fixed.py:6:       -> AFDMEnvMixin.generate_channel_matrix / generate_uwa_channel   (afdm_env.py:285-359, 505-674)
../tcom_reference_frame_20261015/gen_fixed.py:14:  * ``system._P_actual`` is not written (the shim copy in ``generate_base`` would discard it anyway).
../tcom_reference_frame_20261015/gen_fixed.py:46:# generate_uwa_channel; value rounded to 3 decimals, MC error recorded in numax.json / GATES.md).
../tcom_reference_frame_20261015/gen_fixed.py:141:    """One pass of the draw loop of generate_uwa_channel (afdm_env.py:311-340); same call order on ``rs``."""
../tcom_reference_frame_20261015/gen_fixed.py:166:    """Copy of generate_uwa_channel (afdm_env.py:285-359) with the D1/D2 options.
../tcom_reference_frame_20261015/gen_fixed.py:214:# --------------------------------------------------------------------------- channel (copy of generate_channel_matrix)
../tcom_reference_frame_20261015/gen_fixed.py:216:    """Copy of AFDMEnvMixin.generate_channel_matrix (afdm_env.py:527-674) after the path draw, minus H_time."""
../tcom_reference_frame_20261015/gen_fixed.py:292:def generate_channel(system, channel_seed, flags):
../tcom_reference_frame_20261015/gen_fixed.py:307:    h, params, extras = generate_channel(system, channel_seed, flags)
../tcom_reference_frame_20261015/gen_fixed.py:320:def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
../tcom_reference_frame_20261015/gen_fixed.py:321:    """Copy of headroom driver.generate_base (driver.py:209-224).  rho shim as in the frozen driver.
../tcom_reference_frame_20261015/p2b_gates.py:81:    raw, diag = P.generate(ctx, D.FLAGS_S, .5, 6.0, frame, seed_fn)
../tcom_reference_frame_20261015/p2b_gates.py:107:            a, da = ref.generate_base(ctx, .5, 6.0, frame, seed_fn, ref_flags)
../tcom_reference_frame_20261015/p2b_gates.py:108:            b, db = gen_fixed.generate_base(ctx, .5, 6.0, frame, seed_fn, new_flags)
../tcom_reference_frame_20261015/p2b_gates.py:237:            raw, diag = P.generate(ctx, D.FLAGS_S, rho, 6.0, fr, seed_fn)
../tcom_reference_frame_20261015/p1_driver.py:9:  F0     native TF_J20_R2 (native_twofft.receive, rounds=2, iterations=20, soft/joint)
../tcom_reference_frame_20261015/p1_driver.py:12:  C      F1 frozen NOMP front + the same TF_J20_R2 schedule (cstate_necessity_stageA_20260928/native_f1.receive_f1)
../tcom_reference_frame_20261015/p1_driver.py:44:# New 256-bit OS entropy (os.urandom(32).hex(), generated 2026-10-15 before any P1 data); never used by an earlier stream.
../tcom_reference_frame_20261015/p1_driver.py:55:    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
../tcom_reference_frame_20261015/p1_driver.py:58:    C='cstate_necessity_stageA_20260928/native_f1.receive_f1 (frozen NOMP front + TF_J20_R2)',
../tcom_reference_frame_20261015/p1_driver.py:94:    """Frozen headroom context (system, code, native, kernel, branch, wrappers, arms) + the Stage-A F1 receiver."""
../tcom_reference_frame_20261015/p1_driver.py:96:    args = hd.parse_args(['--mode', 'generate', '--out', str(HERE / 'out' / 'p1_ctx'), '--project', str(PROJECT)])
../tcom_reference_frame_20261015/p1_driver.py:99:    from native_f1 import receive_f1
../tcom_reference_frame_20261015/p1_driver.py:146:        dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
../tcom_reference_frame_20261015/p1_driver.py:163:                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, mode)['decoder']
../tcom_reference_frame_20261015/p1_driver.py:177:    """F1 front + the same native schedule (C); CSTATE20 branch iff C's final syndrome != 0 (D)."""
../tcom_reference_frame_20261015/p1_driver.py:194:                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arraysC, 'CSTATE20')['decoder']
../tcom_reference_frame_20261015/p1_driver.py:242:def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
../tcom_reference_frame_20261015/p1_driver.py:244:    return gen_fixed.generate_base(ctx, rho, snr_db, frame, seed_fn, flags)
../tcom_reference_frame_20261015/p1_driver.py:349:                    raw_base, diag_base = generate(ctx, scenario, rho, snr_cells[0] / 100, frame, seed_fn)
../tcom_reference_frame_20261015/p1_driver.py:364:                                   generate_seconds=gen_seconds if snr_centi == todo[0] else 0.,
../tcom_reference_frame_20261015/zport_driver.py:205:                    raw_base, diag_base = P.generate(ctx, scenario, rho, snr_cells[0] / 100, frame, seed_fn)
../tcom_reference_frame_20261015/s0_gates.py:6:         generate_uwa_channel); the value is then frozen as gen_fixed.UWA_NU_MAX_99.
../tcom_reference_frame_20261015/s0_gates.py:7:  a      G-S0a  flags off: frames 0..999 bit-identical to the frozen headroom driver.generate_base  (sharded).
../tcom_reference_frame_20261015/s0_gates.py:34:# any 256-bit test entropy; generated 2026-10-15 with secrets.token_hex(32); used for S0 only (never for P1)
../tcom_reference_frame_20261015/s0_gates.py:78:    args = hd.parse_args(['--mode', 'generate', '--out', str(OUT), '--project', str(PROJECT)])
../sp_afdm_native_joint_reviewed_20260921/src/fast_bilinear.py:56:    Shifted constellation x=p+d implements SP without treating p as noisy data.
../sp_afdm_frozen_20260920/src/run_local.py:292:        cell_metadata = {
../sp_afdm_frozen_20260920/src/structured_ep.py:3:covariances to their marginals; constellation/LDPC factors remain in AF domain.
../sp_afdm_frozen_20260920/src/receiver.py:66:        events.append(dict(stage='fresh_decoder',iterations=int(dec['iterations']),metadata=dec['metadata']));arrays.update(refresh_input=dec['incoming_llr'],refresh_app=dec['raw_app'],refresh_check=dec['raw_check_extrinsic'])
../sp_afdm_frozen_20260920/src/receiver.py:105:    events.extend(o['trace']);events.append(dict(stage='final_decoder',iterations=int(dec['iterations']),decode_ok=bool(dec['decode_ok']),metadata=dec['metadata']))
500:| EB-6 | Claude | agy: CD6 crossing gain ≥ 2.5 dB at ρ .15 | .20 | Did not occur (0.77 dB). Score 0, Brier 0.0400 |
504:| EB-A1 | Astra | On the original draft labels: direction only / upper < 3 pp only / both / neither | .40 / .29 / .06 / .25 | Mapped to the original labels: "direction only" occurred (Astra .40) |
523:| GE-A4 | Astra | Joint | .20 | Did not occur. Score 0, Brier 0.0400 |
531:| G0-1 | Claude | Z P-A SUPPORTED | .80 | Occurred (1.84% [0.99, 2.80]). Score 1, Brier 0.0400 |
536:| G0-F1 | Fable | Z (Γ = 0) phantom rate < 10% | .80 | Occurred. Score 1, Brier 0.0400 |
557:| GM-A2 | Astra | P-D: EQUIVALENT / Z_HIGHER / Z_LOWER / INCONCLUSIVE (anchors passing) | .47 / .12 / .03 / .38 | EQUIVALENT occurred (Astra .47). Multiclass Brier 0.4406 |
578:| SR-1 | Claude | R1: PHENOMENON / INCONCLUSIVE / NOISE_EXPLAINS | .70 / .20 / .10 | PHENOMENON occurred (4.4% [3.5, 5.5]). Multiclass Brier 0.140 |
613:| SE-2 | Claude | P2 BETTER / NOT_BETTER / INCONCLUSIVE | .45 / .15 / .40 | BETTER occurred (+0.93 [0.65, 1.39] dB). Multiclass Brier 0.49 |
624:| DA-2 | Claude | R2 COMPLEMENT / NO / INCONCLUSIVE | .40 / .30 / .30 | COMPLEMENT occurred (.919). Multiclass Brier 0.54 |
646:| DP-0 | Claude | PASS / INCONCLUSIVE / STOP | .40 / .35 / .25 | PASS occurred (recall .653, precision .192). Multiclass Brier 0.545 |
654:| DP-0b | Claude | ADOPT | .40 | Did not occur (FALLBACK; recall .32, precision ~.10) |
696:| DP-A4 | Claude | PILOT-ENOUGH / SB-REACHABLE / ALPHABET-ONLY / CLOSED | .10 / .40 / .45 / .05 | SB-REACHABLE occurred (semiblind .037 at rho .15, 4 dB; pilot .060). Multiclass Brier 0.575 |
716:Forecasts frozen before main execution in [PROTOCOL.md §6](../experiments/huang_steelman_20261124/PROTOCOL.md) (`4772365c`; Claude's four entries carried unchanged from [DRAFT](../.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md)). 62,400 keys / 18,009 archived F0 triggers on `rho_sweep_20261119` frames `5400–5799`, full 6-$\rho$ grid, `HG` recipe `B0-p2-s0.5`, `HGint` retained; 9.84 core-hours cumulative (within 12.0 core-hour cap).
724:| HS-G1 | agy (Gemini 4 Neon) | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .25 / .15 / .35 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9400 |
726:| HS-G3 | agy (Gemini 4 Neon) | Quiet per-trigger median latency: `CD` < `HG` | .80 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0400 |
734:Forecasts committed before running `experiments/sameframe_hg_20261124/sameframe.py` ([PROTOCOL.md](../experiments/sameframe_hg_20261124/PROTOCOL.md), freeze `918a2474`). Part 1 evaluates `HG`/`HGint` on `stageA` frames `41000–41399` ($\rho \in \{100,150,200,250\}$) paired against archived `stageA`/`stageA2`/`stageA3` (`s100` primary, 95% paired frame bootstrap, 2000 draws, seed `20261124`). Part 2 evaluates two-pass `CD2` (`max_edits=2`) and `CD2e8` (`max_edits=8`) on `rho_sweep_20261119` frames `5400–5799` (18,009 triggers, 98.33% 36-pair projected CI). Total runtime: 10.87 core-hours (cap 16.0 h).
738:| SF-C1 | Claude | P1 (`min HG − min s100`): `DOPPLER-LINE` / `INCONCLUSIVE` / `WRITE-A` | .35 / .40 / .25 | `INCONCLUSIVE` occurred (+0.7333 dB, 95% CI [+0.4549, +1.0396]). Multiclass Brier 0.5450 |
754:| CD2-C2 | Claude | Quiet timing ($\rho=.20, 4.5\text{ dB}$): `CD2` mean per-trigger time < `HG` mean time | .80 | Occurred (`CD2` 189.02 ms < `HG` 639.99 ms; also at $\rho=.30, 5.0\text{ dB}$: 172.80 vs 572.38 ms). Brier 0.0400 |
758:Readout [READOUT.md](../experiments/sameframe_cd2_20261125/READOUT.md) · [RESULTS.md](../experiments/sameframe_cd2_20261125/out/RESULTS.md). Both forecasters calibrated well across both `P1'` and timing. Notably, `CD2` strictly beat both `HG` (−0.1569 dB [−0.2976, −0.0137]) and `HGint` (−0.2121 dB [−0.3588, −0.0622]) on the fresh `41000–41399` cohort while running faster than both (`189.0` vs `640.0` / `199.1 ms` at $\rho=.20, 4.5\text{ dB}$).
763:Forecasts committed before running `experiments/data_pilot_fer_20261121/stageA5.py` ([STAGEA5_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA5_PROTOCOL.md), freeze `75530d4d`). Given true delays $l_i$, evaluates `PW` (pilot-only, data as white noise), `SB` (semi-blind Gaussian ML, exact-gradient joint L-BFGS-B from `PW`), and `KD` (known-data ceiling) on frames `41000–41099` × U/G (200 draws; paired 100-frame cluster bootstrap, `2000` draws, seed `20261125`), $\rho \in \{100,150,200\}$, SNR = `400` (4 dB; G4 selected `[400]` under 6.0 core-h cap; actual `1.97` core-hours). Primary $E = \min_{\rho \in \{.10, .15\}} \overline{M}_{\mathrm{SB}}(4\text{ dB})$: `PASS` if CI upper $\le 0.08$ bin, `FAIL` if CI lower $> 0.08$, else `BORDERLINE`.
767:| A5-C1 | Claude | Primary verdict: `PASS` / `BORDERLINE` / `FAIL` | .30 / .35 / .35 | `PASS` occurred (`0.0430` bin at $\rho=.15$, 95% CI `[0.0408, 0.0455]`). Multiclass Brier 0.7350 |
769:| A5-G1 | agy (Gemini 4 Neon) | Primary verdict: `PASS` / `BORDERLINE` / `FAIL` | .40 / .30 / .30 | `PASS` occurred (`0.0430` bin at $\rho=.15$, 95% CI `[0.0408, 0.0455]`). Multiclass Brier 0.5400 |
772:Readout [STAGEA5_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA5_READOUT.md) · [RESULTS.md](../experiments/data_pilot_fer_20261121/out/stageA5/RESULTS.md). Both forecasters expected a harder finite-sample efficiency penalty at 4 dB and placed only .30/.40 on `PASS`; in fact exact-gradient joint `SB` hit `1.32× / 1.17× / 1.09×` of `SB-CRB` (`0.0527 / 0.0430 / 0.0376` bin), passing well below `0.08` bin at both $\rho = 0.10$ and $0.15$. Both efficiency-band forecasts (`A5-C2`, `A5-G2`) hit (`1.3245 ∈ [1.3, 2.5]`).

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "sed -n '1,36p' out/stageA5/results.json; sed -n '115,133p' ../huang_steelman_20261124/hs_arms.py; rg -n 'A6|Stage A6' ../../.trellis/tasks/11-21-data-pilot-fer/{design.md,prd.md} ../../research-assets/prediction-ledger.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 exited 1 in 0ms:
{
  "_argv": [
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA5.py",
    "run",
    "--gate",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/out/stageA5_gate.json",
    "--out",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/out/stageA5",
    "--freeze-commit",
    "75530d4d2a953a9efc54c5d0771d840c2134a0af",
    "--workers",
    "24"
  ],
  "_config": {
    "freeze_commit": "75530d4d2a953a9efc54c5d0771d840c2134a0af",
    "freeze_commit_git_verified": false,
    "python_executable": "/home/guoyikun/.conda/envs/AFDM/bin/python",
    "own_md5": {
      "STAGEA5_PROTOCOL.md": "a9e7a6e42b13c1f7f0997549eadacc3c",
      "stageA5.py": "073b76973298fbd58ecb0ef38953c97d",
      "test_stageA5.py": "24e76d8ca61c876df4d74197a8623277",
      "stageA5_launch.sh": "f7bab24cef93241baff4e4a9d1183c64"
    },
    "stageA_py_md5": "17be1c3e75e07fb9a4dec1b3774c54aa",
    "stageA4_py_md5": "38790432341fc7dc68dfe3153405c48b",
    "gate_md5": "2fe1980cf261d4037cb6ebf152f0348e",
    "snrs": [
      400
    ],
    "rhos": [
      100,
      150,
      200
    ],
    "frames": [
      41000,
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

exec
/bin/zsh -lc "sed -n '22,61p' ../cstate_codelay_sbl_stage3_20261118/run.py; sed -n '45,75p' ../tcom_genie_support_20261016/gs_driver.py; rg -n 'native|def context' ../headroom_ladder_20261008/driver.py | head -32; rg -n 'def base\\(' ../tcom_reference_frame_20261015 ../tcom_genie_support_20261016 -g '*.py'; sed -n '296,322p' ../tcom_reference_frame_20261015/gen_fixed.py; rg -n 'class Channel|def __init__|sort' ../sp_afdm_frozen_20260920/src/physical.py | head -24; rg -n 'set_num_threads|\\.Queue\\(|\\.Pool\\(|SemLock|tempfile' stageA6.py stageA5.py ../unified_cov_prospective_20261119/cstate.py ../cstate_codelay_sbl_stage3_20261118/run.py ../headroom_ladder_20261008/driver.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 exited 1 in 0ms:
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


def write_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def read_rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def context():
    ctx = e1.p1ctx.load()
    checked = e1.check_frozen_md5(ctx)
    if any(r['status'] != 'ok' for r in checked.values()):
        raise AssertionError('E-1 source inventory did not pass')
    if {name: ctx.source_md5[name] for name in P1_MD5} != P1_MD5:
        raise AssertionError('P1 imports differ from the historical SBL archives')
    full = e1.load_variant()
    route = codelay.load(full)
    return ctx, full, route, checked


def key_of(row):
    g2 = np.abs(np.asarray(truth['g_i'])) ** 2
    u = np.unique(l)
    energy = np.array([g2[l == d].sum() for d in u])
    return u[np.argsort(-energy, kind='stable')]


def run_gs(ctx, obs, refine, gain_mode='joint', arm='genie_support'):
    """Production schedule with the refit replaced by ``refine``; front, detector and decoder unchanged."""
    return ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm=arm, rounds=2, iterations=20,
                                      gain_mode=gain_mode, refine_override=refine)


def observe(ctx, raw_base, diag_base, rho, snr_centi):
    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
    return raw, ctx.hd.observe(raw, rho, snr_centi / 100), ctx.hd.truth_from_raw(raw, diag)


def score(ctx, decoded, truth):
    return int(np.count_nonzero(ctx.extract_info(ctx.code, np.asarray(decoded)) != truth['info']))


def paths(delays, dopplers, gains):
    return dict(delays=[int(x) for x in np.asarray(delays)], dopplers=[float(x) for x in np.asarray(dopplers)],
                gains=np.asarray(gains, complex))


def gs_arm(ctx, obs, truth, arm, n):
    delays = genie_delays(truth, arm)
    log = []
    t0 = time.perf_counter()
    res = run_gs(ctx, obs, ctx.arms.make_a1_refine(delays, log))
52:RECEIVER_CONFIG = dict(native_rounds=2, native_iterations=20, native_ce_mode='soft',
53:                       native_gain_mode='joint', trigger='final native syndrome!=0',
57:SOURCE_MODULES = ('native_twofft', 'twofft', 'receiver', 'physical', 'messages', 'evidence',
74:    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
142:    paths = [exp / args.native_dir / 'src', exp / args.baseline_dir / 'src', HERE,
156:    import native_twofft as native
170:    ctx.native, ctx.kernel, ctx.branch, ctx.wrappers, ctx.evidence = native, kernel, _branch, wrappers, evidence
429:    """Production B: two native rounds, CSTATE20 continuation iff final syndrome != 0."""
431:    dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
438:        branch = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
454:        ctx.native, obs, ctx.system, ctx.code, arm='genie_delays_a1', rounds=2, iterations=20,
466:    result = ctx.wrappers.run_true_geometry(obs, ctx.system, ctx.code, ctx.native,
478:    result = ctx.wrappers.run_fixed_channel(obs, ctx.system, ctx.code, ctx.native,
    h_eff, params = paths_to_channel(system, d, flags, channel_seed)
    extras = dict(flags=flags.tag(), attempts=int(d['attempts']), redraws=int(d['attempts']) - 1,
                  fallback_clip=bool(d['fallback']), delay_index=np.asarray(d['delay_index']))
    return h_eff, params, extras


# --------------------------------------------------------------------------- frame (copy of make_frame)
def make_frame(system, code, replicate, index, snr, flags, *, split, rng_factory, encode, qpsk_map):
    """Copy of budgeted_support_eval.make_frame (lines 114-129), coded frames only."""
    n = system.N_total
    channel_seed = int(rng_factory(replicate, index, 1, split=split).integers(0, 2**31))
    h, params, extras = generate_channel(system, channel_seed, flags)
    info = rng_factory(replicate, index, 2, split=split).integers(0, 2, size=code['k']).astype(np.uint8)
    coded = encode(code, info)
    data = np.sqrt(1 - system.rho) * qpsk_map(coded, scale=1)
    pilot = np.sqrt(system.rho) * system._zc_seq
    rng = rng_factory(replicate, index, 3, split=split)
    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
    sigma2 = 10 ** (-snr / 10)
    y = h @ (pilot + data) + np.sqrt(sigma2) * noise
    return dict(y=y, H=h, params=params, info=info, coded=coded, data=data, pilot=pilot, noise=noise,
                sigma2=sigma2, channel_seed=channel_seed, uncoded=False, split_id=split, gen_fixed=extras)


def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
    """Copy of headroom driver.generate_base (driver.py:209-224).  rho shim as in the frozen driver.

33:    unique=np.unique(lq);energy=np.array([np.sum(abs(gq[lq==d])**2) for d in unique]);ls=unique[np.argsort(-energy)[:max_paths]]
93:class Channel:
155:        e=self.energies(v);order=np.lexsort((np.arange(self.n),-e));maximum=min(maximum,self.n);m=maximum
159:        keep=np.sort(order[:m]);tail=max(float(e.sum()-e[keep].sum()),0.)

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'std::|Parallel|[Tt]hread|/dev/shm|cache|Tmp' ../headroom_ladder_20261008/driver.py ../tcom_reference_frame_20261015/p1ctx.py ../tf_cstate_e1_20261017/e1_driver.py | head -55; nl -ba stageA6.py | sed -n '50,60p;873,900p;919,941p;984,994p;1017,1026p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
rg: ../tcom_reference_frame_20261015/p1ctx.py: No such file or directory (os error 2)
../headroom_ladder_20261008/driver.py:13:Run one process per shard, single thread (see launch.sh).  Nothing frozen is edited.
../headroom_ladder_20261008/driver.py:153:    """Import frozen modules (unchanged), bind single-thread CPU runtime, build system/code."""
    50	    (200, 250, 300, 400, 450, 500, 550),
    51	    (200, 250, 300, 400, 450, 500),
    52	    (250, 300, 400, 450, 500),
    53	)
    54	FULL_SNRS = CANDIDATE_SNRS[0]
    55	CD2_RHOS = (100, 150, 200, 250)
    56	CD2_SNRS = (300, 350, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1200)
    57	A2_RHOS = (50, 100, 150, 200)
    58	A3_RHOS = (100, 150, 200)
    59	A23_SNRS = (200, 250) + CD2_SNRS
    60	
   873	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   874	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   875	    ar.check_thread_env()
   876	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   877	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   878	    if not 1 <= args.workers <= 32:
   879	        raise ValueError('workers must be in 1..32')
   880	
   881	    pinned_md5 = verify_pinned_code()
   882	    live_own = own_md5()
   883	    freeze_git_ok = verify_freeze_commit_if_git(args.freeze_commit, live_own)
   884	    manifests = verify_all_archives(('stageA', 'stageA2', 'stageA3', 'sameframe_cd2'))
   885	
   886	    gate_path = args.gate.resolve()
   887	    gate_bytes = gate_path.read_bytes()
   888	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   889	    gate = json.loads(gate_bytes.decode('utf-8'))
   890	    if not gate.get('all_passed') or not gate.get('selected'):
   891	        raise RuntimeError('Refusing to run without passing stageA6_gate.json')
   892	    if gate['_config']['own_md5'] != live_own:
   893	        raise RuntimeError('stageA6_gate.json own_md5 mismatch; re-run gates')
   894	    if gate['_config']['pinned_code_md5'] != pinned_md5:
   895	        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA6_gate.json')
   896	
   897	    snrs = tuple(int(s) for s in gate['selected']['snrs'])
   898	    out_dir = args.out.resolve()
   899	    raw_dir = out_dir / 'raw'
   900	    raw_dir.mkdir(parents=True, exist_ok=True)
   919	            running[p.sentinel] = (idx, p)
   920	        while running:
   921	            ready = wait(running, timeout=5.0)
   922	            for r in ready:
   923	                idx, p = running.pop(r)
   924	                p.join()
   925	                code = p.exitcode
   926	                p.close()
   927	                if code != 0:
   928	                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
   929	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   930	            if live_cpu >= BUDGET_CAP_SEC - 480.0:
   931	                budget_hit = True
   932	                break
   933	    finally:
   934	        for _, p in running.values():
   935	            p.terminate()
   936	        for _, p in running.values():
   937	            p.join()
   938	            p.close()
   939	    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
   940	        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   941	        sys.exit(BUDGET_EXIT_CODE)
   984	        's050': (A3_RHOS, A23_SNRS, fa3[:, stageA3.ARMS.index('s050')]),
   985	        's100': (A3_RHOS, A23_SNRS, fa3[:, stageA3.ARMS.index('s100')]),
   986	    }
   987	    diagnostics = summarize_diagnostics(rows, snrs)
   988	    analysis = analyze_stageA6(fail_by_arm, stageA2.crossing, diagnostics)
   989	
   990	    total_cpu_h = _used_cpu_seconds() / 3600.0
   991	    if total_cpu_h >= BUDGET_CAP_HOURS:
   992	        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
   993	        sys.exit(BUDGET_EXIT_CODE)
   994	
  1017	        runtime=dict(
  1018	            total_core_hours=total_cpu_h,
  1019	            wall_seconds=time.monotonic() - wall_start,
  1020	            cpu_cap_core_hours=BUDGET_CAP_HOURS,
  1021	        ),
  1022	        analysis=analysis,
  1023	    )
  1024	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
  1025	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
  1026	    p = analysis['primary']

exec
/bin/zsh -lc "nl -ba ../headroom_ladder_20261008/driver.py | sed -n '220,249p'; rg -n 'def truth_from_raw|g_i.*=|np.argsort|sort\\(' ../tcom_reference_frame_20261015/gen_fixed.py ../headroom_ladder_20261008/driver.py | head -45; nl -ba ../sp_afdm_frozen_20260920/src/physical.py | sed -n '90,137p'; rg -n 'def pilot_front|return dict\\(' ../sp_afdm_frozen_20260920/src/receiver.py | head -18; sed -n '28,43p' ../huang_steelman_20261124/hs_arms.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
   220	        raise AssertionError('channel stream does not match its registered descriptor')
   221	    if not np.array_equal(raw['pilot'], np.sqrt(shim.rho) * ctx.system._zc_seq):
   222	        raise AssertionError('pilot law differs')
   223	    raw, diag = ctx.physical_observation(raw, shim, prefix_length=shim.l_max_cap)
   224	    return raw, diag
   225	
   226	
   227	def observe(raw, rho, snr_db):
   228	    """Normalise to the frozen internal convention (data power .5); assert the rho shim."""
   229	    scale = np.sqrt(2. * (1. - rho))
   230	    obs = dict(y=np.asarray(raw['y']) / scale, pilot=np.asarray(raw['pilot']) / scale,
   231	               sigma2=float(raw['sigma2']) / scale**2)
   232	    assert set(obs) == {'y', 'pilot', 'sigma2'} and np.isfinite(obs['y']).all()
   233	    pilot_power = float(np.mean(np.abs(obs['pilot'])**2))
   234	    assert np.isclose(pilot_power, rho / (2. * (1. - rho)), rtol=1e-9, atol=0), \
   235	        f'observed pilot power {pilot_power} != rho/(2(1-rho))'
   236	    assert np.allclose(np.abs(obs['pilot']), np.abs(obs['pilot'][0]), rtol=1e-9, atol=0)
   237	    assert np.isclose(obs['sigma2'], 10**(-snr_db / 10) / (2. * (1. - rho)), rtol=1e-9, atol=0), \
   238	        'observed sigma2 != sigma2/(2(1-rho))'
   239	    data_power = float(np.mean(np.abs(np.asarray(raw['data']) / scale)**2))
   240	    assert np.isclose(data_power, .5, rtol=1e-9, atol=0), f'observed data power {data_power} != .5'
   241	    return obs
   242	
   243	
   244	def truth_from_raw(raw, diag):
   245	    p = raw['params']
   246	    return dict(coded=np.asarray(raw['coded']), info=np.asarray(raw['info']),
   247	                l_i=np.asarray(p['l_i']), k_real=np.asarray(p['k_real']), g_i=np.asarray(p['g_i']),
   248	                channel_seed=int(raw['channel_seed']),
   249	                physical_gains_sha256=diag['physical_gains_sha256'],
../tcom_reference_frame_20261015/gen_fixed.py:25:                        depends on the Doppler draw).  g_i = unit-norm Rayleigh amplitude x phase, so sum|g_i|^2 = 1 per
../tcom_reference_frame_20261015/gen_fixed.py:221:    delays, g_i_raw, delay_idx_bar = d['delay_bar'], d['gain_tap'], d['delay_idx_bar']
../tcom_reference_frame_20261015/gen_fixed.py:273:    g_i = g_i_raw * scale
../headroom_ladder_20261008/driver.py:244:def truth_from_raw(raw, diag):
../headroom_ladder_20261008/driver.py:247:                l_i=np.asarray(p['l_i']), k_real=np.asarray(p['k_real']), g_i=np.asarray(p['g_i']),
../headroom_ladder_20261008/driver.py:320:    return dict(l_i=ls, k_real=nus, g_i=gs, rays_per_tap=[int(x) for x in rays],
../headroom_ladder_20261008/driver.py:356:               params=dict(l_i=l, k_real=nu, g_i=g), cluster=dict(paths, config=config,
../headroom_ladder_20261008/driver.py:403:                     g_i=np.asarray(tr['g_i']), channel_seed=int(tr['channel_seed']),
../headroom_ladder_20261008/driver.py:498:    order = np.argsort(-g2, kind='stable')
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
   109	    def apply(self,x):
   110	        n=self.n;k=np.arange(n);t=daft(x,self.c1,self.c2,True);z=np.zeros(n,complex)
   111	        for l,nu,h in zip(self.delays,self.dopplers,self.gains):
   112	            cp=np.where(k<l,np.exp(2j*np.pi*self.c1*(n*n+2*n*(k-l))),1)
   113	            z+=h*cp*np.exp(2j*np.pi*k*nu/n)*t[(k-l)%n]
   114	        return daft(z,self.c1,self.c2)
   115	    def adjoint(self,y):
   116	        n=self.n;k=np.arange(n);t=daft(y,self.c1,self.c2,True);z=np.zeros(n,complex)
   117	        for l,nu,h in zip(self.delays,self.dopplers,self.gains):
   118	            cp=np.where(k<l,np.exp(2j*np.pi*self.c1*(n*n+2*n*(k-l))),1)
   119	            z[(k-l)%n]+=h.conjugate()*cp.conjugate()*np.exp(-2j*np.pi*k*nu/n)*t
   120	        return daft(z,self.c1,self.c2)
   121	    def gamma(self,v):return projected_variance(v,self.delays,self.dopplers,self.c1)
   122	    def energies(self,v):return diagonal_energies(self.delays,self.dopplers,self.gains,v,self.c1)
   123	    def diagonals(self,shifts):return selected_diagonals(self.delays,self.dopplers,self.gains,shifts,self.n,self.c1,self.c2)
   124	    def row_variance(self,v,keep=()):
   125	        """diag(R diag(v) R^H), R contains cyclic diagonals NOT in keep.
   126	        P(P+1)/2 FFT convolutions. Does not assert independence of R(d-mu).
   127	        """
   128	        v=np.asarray(v,float);n=self.n;k=np.arange(n)
   129	        if v.shape!=(n,) or np.any(v<0) or not np.isfinite(v).all():raise ValueError('Invalid variance')
   130	        D=dkernel(self.dopplers[None,:]+2*n*self.c1*self.delays[None,:]-k[:,None],n)
   131	        mask=np.ones(n);mask[np.asarray(keep,int)%n]=0;out=np.zeros(n,complex)
   132	        for i in range(self.p):
   133	            for j in range(i,self.p):
   134	                a=mask*D[:,i]*D[:,j].conj();r=int(self.delays[i]-self.delays[j])
   135	                b=v*np.exp(-2j*np.pi*r*k/n)
   136	                z=self.gains[i]*self.gains[j].conjugate()*np.exp(2j*np.pi*self.c1*(self.delays[j]**2-self.delays[i]**2))*np.fft.ifft(np.fft.fft(a)*np.fft.fft(b))
   137	                out+=z if i==j else 2*z.real
61:        return dict(decoded=r['decoded'],info_hat=r['info_hat'],llr=r['llr'],seconds=complete,refit_seconds=0.,detector_seconds=detector_seconds,decoder_seconds=decoder_seconds,instrumentation_seconds=instrumentation_seconds,decoder_records=decoder_records,events=events,arrays=arrays,configuration=cfg)
106:    return dict(decoded=dec['decoded'],info_hat=extract_info(code,dec['decoded']),llr=llr,seconds=time.perf_counter()-start,refit_seconds=refit_seconds,detector_seconds=det_seconds,decoder_seconds=decoder_seconds,instrumentation_seconds=0.,decoder_records=decoder_records,events=events,arrays=arrays,configuration=cfg)
122:def pilot_front(observed,system,code):
129:    return dict(delays=ls[ids],dopplers=ks[ids],gains=gs,mu=np.zeros(n,complex),v=np.full(n,.5),x_soft=np.zeros(n,complex),prior=np.zeros(2*n),channel_llr=np.zeros(2*n),sigma_final=float(observed['sigma2']),decoder_records=[],seconds=time.perf_counter()-start,source='observed_pilot_only')
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
LOW_SNRS = (300, 400)
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

codex
先修再启动。按当前代码，主跑完成后会在读取归档时失败。另有真增益参与路径排序，以及截尾判读可能崩溃的问题。

1. **归档网格必错。** `CD2` 和 A2/A3 归档有 `1100`（11 dB），代码却填了 `350`（3.5 dB）。`CD2` 读取时会报错，A2/A3 即使单独读取也会因缺格退出。直接复用各归档定义的网格，并在起工作进程前校验可读性和完整性。 [Stage A6 网格](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:55) · [冻结网格](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:37)
2. **两臂仍读取真增益。** 多普勒注入、校验失败后走 `A1`、用真实信息位计分，都与 A3 一致。复增益由导频最小二乘求得，但 A2 的公共入口仍把真增益传给接收机，用于第 0 轮路径排序。严格的“只给真时延”与当前 A3 路径复用在这里冲突。冻结前须明确排序约定，再核对四键 G1。 [A2 注入](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA2.py:29) · [接收机排序](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82)
3. **截尾判读有崩溃路径。** 1% 帧错误率交叉点、U/G 等权平均、最优导频比例之差、2,000 次同帧重采样和判定阈值均对齐。但参考实现输出 `'+inf'`，A6 只接受 `'inf'`，置信区间上界无穷时会抛异常。若某组没有 F0 成功或失败帧，报告也会对 `None` 做乘法。现有测试未覆盖这两个入口。 [截尾解析](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:539) · [报告渲染](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:823)
4. **门禁与诊断还有缺口。** G1 比对三项结果，G2 在指定四键比对逐径误差和加权指标，但 G2 复制了估计流程，未直接覆盖主跑入口。G3 按 `550 → 200` 降档并记录选择。主跑启动时漏验 A5，所谓 A5 子集核对只列 A6 均值。应在相同 200 个样本上列出 A5 存档值及差值。逐导频比例交叉点、指定对照差值、弱径离群和单键计时已有实现。 [门禁](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:366) · [A5 诊断](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:697)
5. **启动脚本的锁清理注册过晚。** 环境、六个单线程设置、禁用 GPU、最多 32 个工作进程、项目临时目录、原子写入及提前 480 核秒停止均有实现。切目录或激活环境失败会留下锁，应在取锁成功后立即注册清理。 [启动脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6_launch.sh:17)

本地五份归档清单的 SHA-256 均匹配。此次为静态审查，远端分片 MD5、门禁实跑及共享目录零写入未验证。

VERDICT: FIX
hook: Stop
hook: Stop Completed
tokens used
119,362
先修再启动。按当前代码，主跑完成后会在读取归档时失败。另有真增益参与路径排序，以及截尾判读可能崩溃的问题。

1. **归档网格必错。** `CD2` 和 A2/A3 归档有 `1100`（11 dB），代码却填了 `350`（3.5 dB）。`CD2` 读取时会报错，A2/A3 即使单独读取也会因缺格退出。直接复用各归档定义的网格，并在起工作进程前校验可读性和完整性。 [Stage A6 网格](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:55) · [冻结网格](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:37)
2. **两臂仍读取真增益。** 多普勒注入、校验失败后走 `A1`、用真实信息位计分，都与 A3 一致。复增益由导频最小二乘求得，但 A2 的公共入口仍把真增益传给接收机，用于第 0 轮路径排序。严格的“只给真时延”与当前 A3 路径复用在这里冲突。冻结前须明确排序约定，再核对四键 G1。 [A2 注入](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA2.py:29) · [接收机排序](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82)
3. **截尾判读有崩溃路径。** 1% 帧错误率交叉点、U/G 等权平均、最优导频比例之差、2,000 次同帧重采样和判定阈值均对齐。但参考实现输出 `'+inf'`，A6 只接受 `'inf'`，置信区间上界无穷时会抛异常。若某组没有 F0 成功或失败帧，报告也会对 `None` 做乘法。现有测试未覆盖这两个入口。 [截尾解析](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:539) · [报告渲染](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:823)
4. **门禁与诊断还有缺口。** G1 比对三项结果，G2 在指定四键比对逐径误差和加权指标，但 G2 复制了估计流程，未直接覆盖主跑入口。G3 按 `550 → 200` 降档并记录选择。主跑启动时漏验 A5，所谓 A5 子集核对只列 A6 均值。应在相同 200 个样本上列出 A5 存档值及差值。逐导频比例交叉点、指定对照差值、弱径离群和单键计时已有实现。 [门禁](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:366) · [A5 诊断](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:697)
5. **启动脚本的锁清理注册过晚。** 环境、六个单线程设置、禁用 GPU、最多 32 个工作进程、项目临时目录、原子写入及提前 480 核秒停止均有实现。切目录或激活环境失败会留下锁，应在取锁成功后立即注册清理。 [启动脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6_launch.sh:17)

本地五份归档清单的 SHA-256 均匹配。此次为静态审查，远端分片 MD5、门禁实跑及共享目录零写入未验证。

VERDICT: FIX
