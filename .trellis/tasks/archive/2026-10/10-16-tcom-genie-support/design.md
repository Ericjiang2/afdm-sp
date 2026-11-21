# Design — genie-support audit

规则与判定以 `protocol.md` 为准；本文件只写代码结构。

- 目录：`experiments/tcom_genie_support_20261016/`（新文件；冻结代码不改）。
- `gs_driver.py`：每个 (场景, ρ, SNR, 帧) 一行 JSONL。复用 `p1ctx.load/base` 与 `ctx.reuse_at_snr/hd.observe/hd.truth_from_raw`
  构造与 P1 相同的观测。入口 `run_gs(ctx, obs, refine, gain_mode)` = `ctx.wrappers._instrumented(native, obs, ..., rounds=2,
  iterations=20, gain_mode, refine_override=refine)`；GS-set / GS-multi 的 refine 为 `ctx.arms.make_a1_refine(delays, log)`。
  行内容：两臂 FER、decoded_sha256、syndrome、r0/r1 时延与 Doppler、r1_gains 与 r1_ce_gains 的 NMSE（`crb.channel_nmse`）、
  refit 日志（n_missing_slots、q_min）、秒数；帧 < 500 时额外写 NMSE。断言 S4。
- `gs_gates.py --stage s1|s2s3|smoke`：S1 捕获 F0 refit 输入并比较 `refine_fixed_delays` 与 `twofft.time_refine`；
  S2 用 `run_gs` + 真 Channel 透传 refine + gain_mode='fixed' 对 P1 账本 A3；S3 生产 F0 对 P1 账本 F0；smoke 读 20 帧行做 S5、S6。
- `gs_agg.py`（远程）：读 GS 行、CRB 行（`tcom_channel_crb_20261016/out/main/rows_shard*.jsonl.gz`）与 P1 账本
  （`tcom_reference_frame_20261015/out/p1/rows_shard*.jsonl.gz`），按键连接（S5 断言），算 protocol §3 统计；
  交叉点复用 `p1_agg.crossing` 与 `p2b_agg.crossing_calibration`。
- 运行：`launch_gates.sh`、`launch_gs.sh`（单线程分片，tmux `g_gs`）。
