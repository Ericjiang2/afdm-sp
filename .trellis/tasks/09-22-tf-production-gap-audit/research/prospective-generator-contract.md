# Research: prospective generator contract

- Query: 固定 fresh prospective TF vs TF+CSTATE 的 observation generator、seed 域、误差口径、可复用 receiver API 与计时边界；目标为 6/6.5/7 dB 各 1024 个独立新 observation，禁止 GLOBAL、调参和调用生成器/接收器。
- Scope: internal
- Date: 2026-09-23

## Findings

### 已确认的最终 TF 口径

最终 Part-B 的主 FER 是 **information-frame error**：`decision_error` 判断终点 `info_errors != 0`，而 `info_errors` 用 `extract_info(code, decoded)` 与 truth `info` 比较（`results/sp_afdm_pd1q_part_b_20260921/campaign/analyze.py:68-74`、`campaign/run.py:280-299`）。冻结报告也把 6/6.5/7 dB TF 误差写作 206/43/14 个 information-frame errors（`results/sp_afdm_pd1q_part_b_20260921/RESULTS.md:5-11,42-45`）。新协议必须继续以 `info_errors > 0` 计 FER；同时保存并报告 `coded_errors`（2048 位 full coded-word error）和 `syndrome_weight`，两者是次要诊断量。不能用 coded-word error 替代主 FER；二者可因 parity-only 差异而不同。

Pilot 没有独立随机流。`make_frame` 的 pilot 是确定的 `sqrt(system.rho) * system._zc_seq`（`experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:114-129`）；随机流只有 channel、message/information bits、thermal noise。因而新 runner 应冻结 system/config，使每个 frame 的 pilot 完全由 system 的固定 ZC law 决定，并在 metadata 中明确 `pilot_rng = none/deterministic_zc`。

### 可复用 generator 与物理分布

现成入口是：

1. `make_frame(system, code, replicate, index, snr, uncoded=False, split=1, rng_factory=None)`（同上 `budgeted_support_eval.py:114-129`）。它要求 `rng_factory(replicate,index,component,split=...)`；component 1/2/3 分别请求 channel/message/noise。channel stream 先生成 `[0,2**31)` 的 `channel_seed`，然后旧实现用该 seed 调 `system.generate_channel_matrix()`；message stream 生成 `code['k']=1024` 个信息位，`encode` 后得到 `code['n']=2048` 个 coded bits；数据为 `sqrt(1-rho) * qpsk_map(coded, scale=1)`；noise 为 `(N(0,1)+jN(0,1))/sqrt(2)`；`sigma2=10**(-snr/10)`；raw `y=H@(pilot+data)+sqrt(sigma2)*noise`。
2. `physical_observation(raw, system, prefix_length=system.l_max_cap)`（`experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_g1.py:72-125`）用 raw params 的 `l_i/k_real/g_i` 构造 G1 physical channel，并以 CPP propagation 重算 `y`；保留 `pilot/data/noise/sigma2/info/coded`，同时保存 G0 reference、physical diagnostics。它检查 direct-vs-matrix relative error，因而是现有 TF physical-observation 路径的可复用入口。
3. Part-B 的实际封装 `frame_observation`（`results/sp_afdm_pd1q_part_b_20260921/campaign/run.py:64-89`）在 `make_frame` 后调用 `physical_observation`，再以 `unit=sqrt(2*(1-system.rho))` 返回 observed `{y: raw['y']/unit, pilot: raw['pilot']/unit, sigma2: raw['sigma2']/unit**2}`。truth 保留 `info,coded,data,noise,l_i,k_real,g_i,unit_scale`；旧 runner 的 heavy frame 另外保存 H/params。

新 runner 应一次生成 `(snr, frame)` observation，随后把同一个只读 observed/truth 传给 TF 与 TF+CSTATE 两臂；arm 名称绝不能进入任何 seed 坐标。推荐保存字段：

| 类别 | 字段 |
|---|---|
| receiver input | `y`, `pilot`, scalar `sigma2`，且输入键严格为这三项 |
| scoring truth | `info`(1024), `coded`(2048), `l_i`, `k_real`, `g_i`, `unit_scale` |
| audit/heavy（可选） | `H`, `params`, `data`, `noise`, `noiseless`, physical diagnostics |
| seed identity | namespace/version、`snr_centi_db`、frame、component digest/words、channel_seed、pilot law |

注意 `make_frame` 内部直接调用 `np.random.seed(channel_seed)`（line 118），会污染 process-global RNG。若沿用这个实现，runner 必须在调用周围保存/恢复 NumPy global state，并在 preflight 固定 NumPy 版本；否则同一 wrapper 的其他随机操作会被 channel generation 隐式改变。

### 旧 seed 域、ID 与 arm 关系

| 证据/用途 | seed contract / namespace | frame/arm ID |
|---|---|---|
| frozen confirmation/development generator | `SeedSequence([20260920,480017,phase_code,cell,frame,component])`，phase code development=1、confirmation=2；component channel=1, information=2, noise=3（`experiments/sp_afdm_frozen_20260920/src/evidence.py:30-87`） | 由 cell/frame 组织；TF native 输入 arm `TF_J20_R2` 等 |
| native exploratory stage A/B | `[20260921,940317,0,frame,component]` / `[20260921,940317,1,snr_centi,frame,component]`（旧 manifest `results/sp_afdm_native_joint_20260921/stage_A_manifest.json`、`stage_B_manifest.json`） | `TF_J20_R2`, `TF_POINT20_R2`, `TF_FIXED20_R2` 等；仅 exploratory |
| 最终 Part-B TF | `[20260921,941001,0,snr_centi,frame,component]`，component map 在 `results/sp_afdm_pd1q_part_b_20260921/campaign/common.py:63-77`：message=0, channel=1, noise=2；manifest 明确 3072 paired frames / 9696 calls（`campaign/plan.json:14-22`、`results/tf_production_gap_audit_20260922/existing/part_b_manifest.json`） | `s{snr}_f{frame:04d}`；主 TF arm `TF_J20_R2` |
| geometry reopening | 没有新 generator/seed；从最终 Part-B 的 6.5 dB `TF_J20_R2` 选择旧 input，ID 是 `s650_f{frame:04d}`（`experiments/tf_geometry_reopen_20260922/run_reopening.py:49-72`） | `LOCAL20` / `GLOBAL20` 共享同一 input |
| CSTATE validation | 没有独立 observation seed；`ARMS=('LOCAL20','GLOBAL20','CSTATE20')`，CSTATE 继续 replay 同一 75 个 `s650_f####` input（`experiments/tf_cstate_validation_20260922/run_validation.py:22-32,213-231`） | CSTATE20 是第三 arm 的 added branch，不是新 observation population |

因此 fresh study 必须另起 seed namespace；不能复用上述任何整数前缀，也不能把历史 `GLOBAL20/CSTATE20` replay ID 当成新 population。TF 与 TF+CSTATE 在新 study 中应共享每个 `(snr,frame)` 的 observation，只有 arm-specific receiver artifacts/outputs 分开保存。

### 建议的 prospective seed API

候选 contract（需在 runner 首次执行前冻结并写 manifest）：

```text
domain = "AFDM-TF-CSTATE-prospective-v1"
key = canonical_utf8(domain, snr_centi_db, frame, component)
digest = SHA256(key)
seed_words = eight little-endian uint32 words from digest[0:32]
rng = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(seed_words)))
```

建议 component labels 只允许 `channel`, `message`, `noise`，并使用 `(namespace, snr_centi_db, frame, component)` 的 canonical binary/JSON encoding；不要把 arm、receiver iteration 或 wall-clock 值放入 key。SNR 必须入 key，因为协议要求 6/6.5/7 dB 各自 1024 个独立 observations；若省略 SNR，就会把同一 channel/message stream 跨 SNR 配对复用，和“各 SNR independent”冲突。`PCG64`（不是 `PCG64DXSM`）和 NumPy 版本要写入 manifest；将 digest 明确展开为 256-bit words 可避免直接整数构造的端序歧义。

实现时让 `rng_factory` 映射 component 1→channel、2→message、3→noise，固定 `replicate=0, split=2`，并保留 `channel_seed`、digest/words 及实际 SNR/frame。生成后断言 3×1024 坐标唯一、channel seed 无重复、输入 hash 与 truth identity 一一对应。此域设计保持现有 message/channel/noise 物理分布与 G1 replacement，只替换随机坐标；它不应被称为已验证结果，直到 fresh run 完成。

### Receiver 接口与计时起点

- `receiver.context()` 返回 `(system, model, code, header)`（`experiments/sp_afdm_frozen_20260920/src/receiver.py:26`）；context/code/header、固定线程和 `system.P_paths=8` 应在每帧计时外初始化一次。
- `native_twofft.receive(observation, system, code, rounds=2, iterations=20, ce_mode='soft', gain_mode='joint', checkpoint_sink=..., record_states=...)`（`experiments/sp_afdm_native_joint_20260921/src/native_twofft.py:11-40`）只接受 `y/pilot/sigma2`，返回 `(decoded, arrays, timing)`；其内部计时从 `pilot_front` 调用前开始，`timing['seconds']` 包含两轮和 checkpoint callback 的 native wall time。
- 可复用 CSTATE continuation 是 `_branch(observation, system, code, native, kernel, arrays, arm)`（`experiments/tf_cstate_validation_20260922/run_validation.py:39-108`）：从 `arrays['r1_app']` 算 APP moments、从 `arrays['r1_check']` 取 check prior，调用 `kernel.reopen_geometry`，再用 `native.scalar_joint(... iterations=20, gain_mode='joint')` 与 `native.decoder_messages(... maxiter=50)`。`arm='CSTATE20'` 用 `strategy='compact'`, `max_edits=2`；LOCAL/GLOBAL 的参数来自同一 wrapper。它是 added branch continuation，不能把 truth path/gain 当输入。

建议记录四个互不重叠的时间域：`generation_seconds`（`make_frame + physical_observation + normalization`，起点在 `frame_observation` 前）、每臂 `receiver_seconds`（紧贴 `native.receive`/branch 调用）、artifact serialization、以及 full wrapper。TF+CSTATE 要单列 baseline replay 与 added branch；CSTATE 的 geometry nested timings已包含在 kernel exclusive stages，不能再加到 branch 总时长。现有 validation 的 `branch_origin`、`branch_exclusive_stages`、`added_complete_branch_seconds` 与 `wrapper_seconds` 划分可直接沿用（`run_validation.py:374-403`）。

## Related specs

- Part-B allocation/arm contract: `results/sp_afdm_pd1q_part_b_20260921/campaign/plan.json`。
- Native observed-only interface: `experiments/sp_afdm_native_joint_20260921/src/native_twofft.py`。
- CSTATE qualification boundary: `experiments/tf_cstate_validation_20260922/reference/CODEX_VALIDATION.md`；它明确禁止新 radio observations/调参，并要求 continuation 使用同一 frozen TF initialization 与 check-extrinsic。

## Caveats / Not Found

- 本次未调用 `make_frame`、`physical_observation`、`native.receive` 或 `_branch`，未读取新的 outcome/ledger，也未修改原代码。
- Part-B 的旧 generator seed 与输入/TF arm 可精确定位；GLOBAL20/CSTATE20 没有独立 seed，因为它们是对旧 6.5 dB TF input 的 observed-only replay。不能从这些 diagnostic IDs 推导新的 CSTATE population seed。
- `SHA256→PCG64 SeedSequence` 是待冻结的候选新域，尚未成为历史证据；必须在生成前把 canonical encoding、端序、NumPy 版本、namespace 和 channel-global-RNG guard 写进 manifest。
