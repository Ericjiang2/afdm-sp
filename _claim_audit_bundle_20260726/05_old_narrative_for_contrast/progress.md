# Progress Log — 裁决实验 (2×2 ablation, t=0)

## 2026-06-06 — Session 1: 规划 + 代码摸底

**目标**: 按置顶方案规划 "为什么要学" 裁决实验 (Conclusions §11 最高优先承重).

**做了**:
- 读 3 份 tcom_plan/ 参考文档 (Architecture / Theory / Conclusions). 确认修正视图:
  t=0 一次性打分为核, turbo 是可选扩展.
- 摸底现有代码: 定位 head (`CandidateActiveRelationHead`), baseline (`joint_omp_mp_iterative`),
  cache harvester (`loop9_cache_features.py`), 现有 recall 探针 (`loop13_support_recall_probe.py`).
- 确认 Prop.2 feature↔Bayes-factor 映射在代码里坐实 (u=自特征/证据, v=对特征/几何先验).
- 确认 SNR 工作点 {15,20,25} dB ↔ 用户引的 61/81/98% gap-closed.
- 识别 step-1 logging 缺口: 现有 cache 缺 `r⁰`、`channel_params`(重建 H_eff)、head logits、calib split.
- 写 task_plan.md (8 phases + 判决规则 + risk register) + findings.md (代码锚点+红线).

**关键判断**:
- Phase 5 (ranking + ground-truth recall) 是最便宜的决定性步, PASS/FAIL 大概率在此见分晓;
  BER 分解 (Phase 6) 用于量化/说服, 非决策.
- 决定性量 = [head − (E0,P1) white-Λ 强基线], 不是 [head − 纯几何].

**待用户决策** (Phase 0): 见 task_plan.md "Open Decisions" — 4 项.

**Next**: 锁定 Phase 0 决策 → Phase 1 harvest 扩展.

---

## 2026-06-06 — Session 1 续: Phase 0 锁定 + Phase 1 受阻 (deinlab down)

### 完成
- **Phase 0 决策锁定** (用户答): ranking-first 决定性切 · 3-seed pool · 固定 pilot-MF top-M 候选池 · Python.
  原选"全程远程 deinlab", 后因 box 宕改本地, 本地又受阻 (见下) → **下次 box 修好回远程**.
- **代码已写** (2 个本地文件):
  1. `afdm_sp_joint_unrolled/mp_detect_bp_torch.py` — **LOCAL SHIM** (loud-fail). remote 有真版.
     ⚠️ **绝不 scp 到 remote** (会覆盖真 BP 检测器). 仅解本地 import.
  2. `afdm_sp_joint_unrolled/decision_harvest.py` — 决定性切 harvester. 含:
     - `whitened_suffstats(C,r,Phi)` — genie-Λ 充分统计 (T,q) via Cholesky, 不显式求逆.
     - `harvest_frame(...)` — 每帧 dump: u,v,cand_cols,y(genie missed),r⁰, T_genie/q_genie,
       T_white/q_white, white_mf, bin_id(几何 bin), genie_gain_sq(校准用), seed.
     - `_self_test()` — Prop.1 退化检查 (C→σ²I ⇒ 白化统计=白MF, 排序同) + Cholesky vs 显式逆对照.
     - **状态: 代码写完, self-test 未跑通** (import 链断, 见 Blocker).

### Blocker (双堵)
1. **deinlab 宕**: Jun3 能登, Jun6 起 box down (你我都连不上). traceroute 进校园内网到
   `10.253.0.62` 还活, 再往 box 死 → **box 本身关机/崩/网口**, 非 VPN/SSH-客户端问题.
   (我 Bash sandbox 也够不着, 但你交互也连不上 → 确认 box 端.)
2. **本地自包含 harvest 不可行**: 具体 env 类 `AFDMSystem` 在 `prepare_teacher_sparse.py` —
   **remote-only, 未 git 跟踪**, 真信道生成不可桩. 本地缺件: `mp_detect_bp_torch`(已桩) +
   `verify_oamp` + `prepare_teacher_sparse.AFDMSystem`(真 env, 无法补).
   decision_harvest import 链 `loop9_cache_features→eval_classical_joint_unrolled→
   run_classical_baselines_python→verify_oamp(缺)` 断在 verify_oamp.

### 下次无缝衔接 (RESUME 步骤)
1. 验 box 活: `! ssh -o ConnectTimeout=8 deinlab hostname`. 不活 → 找 lab 管理员看电源/网口.
2. box 活后 (回**远程**路线, remote 有真 env + 真 ckpts + 真 mp_detect_bp_torch):
   a. `scp afdm_sp_joint_unrolled/decision_harvest.py deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/`
      ⚠️ **只传 decision_harvest.py, 不传 mp_detect_bp_torch.py shim**.
   b. 远程跑 self-test 验 genie-Λ 数学: `ssh deinlab "bash -lc 'conda activate AFDM && cd /data/guoyikun/00inbox/AFDM-channel-estimation && python afdm_sp_joint_unrolled/decision_harvest.py --self-test'"`
      (远程真 env → import 链通; 本地链断只因 verify_oamp/prepare_teacher_sparse 缺.)
   c. self-test PASS → smoke harvest (小 N, SNR=20): `--out outputs_decision_smoke --snr 20 --n-frames 150`.
      验 shape + missed-atom 频率 (对齐 FYP ~recall 95%) + Cholesky 不炸.
   d. 通 → 扩 3 SNR {15,20,25} × ≥2000 帧 → Phase 3 校准 (π_bin/σ²_h,bin held-out) →
      Phase 4 5-scorer 插件 → Phase 5 τ/recall 裁决 (PASS/FAIL 在此).
3. **若想本地跑**: 需先 `scp deinlab:.../prepare_teacher_sparse.py .../verify_oamp.py 本地`
   (取真 AFDMSystem), 且把 decision_harvest 的 env import 改 lazy (使 --self-test 不依赖 env).

### 关键数 (复用)
- 决定性量 = [head − (E0,P1) white-Λ], 非 [head − 纯几何].
- SNR 工作点 {15,20,25} ↔ 61/81/98% gap-closed. ρ=0.5. head=CandidateActiveRelationHead(1041).
- canonical ckpt: `outputs_loop13_4B_train_27k_with_snr25/ckpt_c2rel_force_topk.pt` (+3-seed pool).

**Next (box 修好后)**: RESUME 步骤 1→2.

---

## 2026-06-09 — Session 2: box 恢复, 远程跑通 Phase 1-5 全管线 + 严格审查

### 完成 (远程 deinlab, conda AFDM)
- box 活 (`liunxgpu`, GPU 全空). 我 Bash 有 VPN 路由 (之前全因 box 宕).
- scp `decision_harvest.py` `decision_metrics.py` `decision_review.py` 上远程 (**未传 shim**).
- self-test PASS (genie-Λ Cholesky + Prop.1). smoke harvest 150 帧 @SNR20 OK.
- 决定性 metrics + review 全跑通. 修了 ckpt key 前缀 `cand_active_rel.` strip.

### 审查结论 (详见 findings.md 2026-06-09 段)
- **无 bug, 机制自洽 theory-confirming**: rec@1 干净阶梯
  white_mf(.04)≈white_Λ(.11)<pure_geom(.22)<genie_Λ(.44)<head(.56). C1 stat 层坐实 (genie AUC .84>white .67).
- **自动 "PASS hero" 不可信**: rec@4 饱和误导; white-Λ 基线坍塌(straw); genie-Λ 4-bin prior 太松.
- **待修 F1-F4** (verdict 前): 主指标换 rec@1; 紧化 genie-Λ 边界(PASS/FAIL 真 pivot); 重定义强基线;
  restricted-τ 判 head≈Λ. 然后 scale 3 SNR × 3-seed × ≥2000 帧.

### 产出文件 (远程 + 本地都有)
- `afdm_sp_joint_unrolled/decision_harvest.py` (harvest+suffstats+self-test) ✓验
- `afdm_sp_joint_unrolled/decision_metrics.py` (calib+Λ ladder+verdict) ✓跑通, **auto-verdict 逻辑需改** (F1)
- `afdm_sp_joint_unrolled/decision_review.py` (诊断: leakage/saturation/rec@1/AUC) ✓
- 远程 cache: `afdm_sp_joint_unrolled/outputs_decision_smoke/cache_snr20.pt` + `metrics_snr20.json`

**Next**: 实现 F1-F4 (尤 F2 紧化边界), 再 scale.

---

## 2026-06-09 — Session 2 续: F2 紧化 genie-Λ 边界 (PIVOTAL)

### 做了
- `decision_harvest.py` 加 dump 可观测 dl_nn/dk_nn(signed)/g_nn(最近原子LS增益). re-harvest 600帧@SNR20.
- 写 `decision_bound.py`: 层次 fine prior (条件 dl,dk,gain-tercile, held-out, shrinkage). 修了 2D flatten + list-key bug.
- 跑通, min_count{15,30,60} 完全稳定.

### 结果 (详见 findings.md 2026-06-09 F2 段)
- 紧化成功: genie-Λ rec@1 0.378→0.475, head=0.550, gap 缩到 +0.074 (CI 重叠但 McNemar p=2.4e-3 仍显著).
- **PIVOTAL: 白化证据冗余** — pure_geom_FINE 0.462 ≈ genie_Λ_FINE 0.475; 证据 rec@2/4 反伤.
  → Λ 价值在几何 prior 不在白化 → **挑战 C1**. 叙事须转"细增益感知几何", 非"detection-theoretic 白化".
- head 仍小幅(+0.07)paired-显著超紧边界, 不靠 genie 证据.

### 待用户决策
接受"几何 prior"重定向 (head amortize 细几何, C2 hero 但非 C1), 还是去找白化有价值的 regime
(ρ-sweep/低SNR) 救 C1? 然后 scale 3 SNR × 3-seed × ≥2000 帧.

**Next**: 用户定方向 → ρ-sweep/SNR 找白化 regime, 或直接 scale 确认几何叙事.

### 2026-06-09 续: 用户选"诊断 C1" → 加 white_Lam_FINE + 启动 ρ×SNR sweep
- decision_bound 加 `white_Lam_FINE` (白证据+细几何 prior), run() 返回数值. harvest 加 `--rho` 覆盖.
- **两-Δ 分解 (SNR20/ρ0.5)**: pure_geom_FINE=0.462, white_Lam_FINE=**0.134**(失配白证据**摧毁**几何),
  genie_Lam_FINE=0.475. → **Δ_whitening=+0.341(巨)** 但 **Δ_evidence=+0.013(无)**.
  解读: **C1 "OMP失配" 强成立**(白证据灾难), 但 **"白化解锁增益"不成立**(正确白化只拉回纯几何水平).
  whitening 在修一个几何本可绕开的问题.
- `decision_c1_sweep.py`: ρ∈{0.3,0.5,0.7}×SNR∈{5,10,15,20}, 测 Δ_evidence/Δ_whitening 随 regime 变化.
  远程 tmux `g_c1sweep` 跑 (~16min). 假设: 低ρ/高SNR (数据干扰强且colored) → Δ_whitening 最大;
  Δ_evidence 是否在某 regime 转正 = C1 "白化证据有价值" 生死.
- 产出: `outputs_c1_sweep/c1_sweep_summary.json` + per-cell `bound.json`.

### 2026-06-09 sweep 结果: C1 复活, regime-dependent (详见 findings.md 同日 C1 sweep 段)
- **C1 活**: Δ_whitening 随 SNR 增长 (ρ0.5: +.06→+.18→+.24→+.32) — "OMP 失配"强成立, regime-dependent
  (低 SNR 噪声主导→白化无关; 高 SNR colored 干扰主导→白证据灾难). Δ_evidence 在 **mid-SNR(10-15)
  干净为正** (peak +.185 @ρ0.7/SNR15) — 白化证据真解锁增益.
- **C2 hero 干净**: 良态区(mid-SNR/高ρ) head ≤ genie-Λ_FINE → 阶梯 white_Λ<geom<head<genie_Λ.
- **SNR=20 是病态角** (C≈(1−ρ)HH^H 病态): Δ_evid 转负, head>bound. 早前单 cell smoke 误踩此角 → 误判.
- 修正叙事: ~~C1 死~~ → **C1 活 regime-dependent**, 这正是检测理论卖点; C2 hero 成立.

**Next**: scale mid-SNR(10-15) × 3-seed × ≥2000帧 firm-up; 查 SNR20 conditioning (cond(C)/diag-loading);
重核 FYP 61/81/98% 工作点 vs mid-SNR 对齐.

### 2026-06-09 续: firm-up 启动 (tmux g_firmup), box 又 flap 掉线
- `decision_firmup.py`: 2000帧×SNR{10,15,20}×ρ0.5×**3 training-seed** (canonical_grid s07/08/09,
  已确认 in-distribution: head_config{top_m48,k_add4}, 训练 cache=loop13_4B). 修了 `cdir/"%d"%snr` 优先级 bug.
  报告 rec@1 紧 CI 阶梯 + Δ_evid/Δ_whiten bootstrap CI + per-seed spread + paired McNemar (head vs geom, head vs bound).
- 启动后 **box 第3次 flap 掉线** (Jun6宕 / waiter idle断 / 现 timeout×3). firm-up 已跑 >22min (job~20min)
  → **大概率已完成存盘** `outputs_decision_firmup/firmup_summary.json`+`firmup.log`. box 回来一条命令取.
- ⚠️ **box 不稳定**: 长 job 靠存盘+重连取, 别依赖 hold-open ssh waiter (idle 会断).

**Next (box 回来)**: 取 `firmup_summary.json` 判读 mid-SNR 阶梯/Δ/3-seed robustness/paired 检验.
  retrieve: `ssh deinlab "grep -E '=====|rec@1=|Delta_|head-' /data/.../outputs_decision_firmup/firmup.log"`

### 2026-06-09 续: firm-up 取回 + verdict 钉死 (详见 findings.md 同日 FIRM-UP 段)
box 回来取到结果. 钉死:
- **head 跨 3 seed 极稳 (spread .005)** → 闭合 FYP training-seed gap.
- **"why learn"=YES**: head 显著>强几何基线 全 SNR (+.05~.06 rec@1, p<1e-3, CI 排除0). 但 margin modest
  (rec@4 操作相关只 +.03). 对 naive(white) 碾压, 对新构强几何 prior 小幅.
- **C1 regime-dependent 确认**: Δ_whiten +.14→.30→.37(随SNR), Δ_evid +.10/.07 在 SNR10/15 排除0, SNR20 含0(病态角).
- **C2 hero**: SNR10 head<genie bound (.51<.55, sig) 教科书阶梯; SNR15 head≈bound; SNR20 病态角 bound 退化.
- Verdict: **偏 HERO + C1 regime-dependent, 诚实 modest margin**. low-complexity/2dB headline 出局.

**Next 选项**: (a) Phase 6 BER 翻译 (rec 增益→BER? margin 小可能 marginal); (b) SNR20 diag-loading 修病态 bound;
(c) ρ-mechanism 正控制 (SP 制造 gap); (d) 开始写 (理论+amortized achiever 框架). 待用户定.

### 2026-06-09 续: 用户选 (a) Phase 6 BER 翻译
- `decision_ber.py`: 复用 `joint_omp_mp_iterative(oracle_support=s_omp∪additions, n_outer_iter=N)` 注入点
  (afdm_baselines:459), 同下游只换 scorer 的 top-K_add. Ladder: OMP/white_mf/geom/genie_Λ/head(3seed)/oracle.
  增量存盘 per-SNR (box flaps). 加 harvest_frame return_raw.
- **关键修正**: n_outer_iter=1 时 BER~9% (检测未成熟, 误); 改 **n_outer=5** (support 冻 t=0 = scorer 选一次不重选,
  但数据检测照常迭代) → BER 正常.
- **SMOKE (50帧/SNR, n_outer=5) 验证 BER 翻译 SNR 依赖**:
  - SNR15: OMP 1.66e-2, head 1.65e-2, oracle 1.52e-2 → headroom 小, head≈OMP (washes out, 同 FYP).
  - **SNR20: OMP 5.47e-4, head 3.52e-4 (−35.7%!), geom 4.59e-4 (head −23.4% vs geom), white_mf 8.89e-4(更差).
    head 甚至 ≤ oracle (噪声, 36 vs 40 errs).** → **recall 边际在高 SNR 真落到 BER, 对齐 FYP −37.7%@SNR20 headline.**
  - white_mf BER 更差 = 失配白证据伤 BER (理论一致). counts 小 → full run firm CI.
- 全量 run 启动 tmux `g_ber`: SNR{15,20,25}×800帧×3seed×n_outer5, ~45-60min.

**Next (box回来)**: 取 `outputs_decision_ber/ber_rho0.5.json` 判读高 SNR head vs OMP/geom 的 BER 增益 + CP CI.

### 2026-06-10: Phase 6 BER 结果 — PIVOTAL sobering (详见 findings.md 同日段)
- **SNR20 BER (600帧 稳定): head 6.10e-4 ≈ OMP 6.36e-4 ≈ geom 6.29e-4 (CI 重叠). recall 边际不落 BER.**
  仅 oracle −32% + white_mf 更差(+62%). 50帧 smoke 的 −35.7% 是噪声.
- **机制钉死**: 91% missed atoms 在 dl0/|dk|≤2 = 接收机 cluster-expand(±k_leak=2) 已覆盖 → head recover 它们
  对 BER **冗余**. recall 指标看不到(不跑接收机), BER 看到. oracle −32% 来自 9% 落 cluster-expand 外的.
- **verdict 重定**: head support-recall 优势 operationally 冗余于 cluster-expand (4B/t=0), 倾向 THEORY 版.
- **⚠️ FYP −37.7% 张力**: 我 4B, FYP pooled 是 2B (config 不同, 绝对 BER 不同) → 不能直接反驳, 须 reconcile
  (跑原生 head pipeline 在 FYP config 看 −37.7% 是否复现 + cluster-expand/select_additions diff).

**Next 待用户定**: (a) reconcile FYP (原生 pipeline 复现 −37.7%?) — 推荐先做; (b) head 重瞄 cluster-expand 外 9%;
(c) 转 THEORY 版. BER run (SNR20-800+SNR25) tmux g_ber 仍跑, 增量存盘 outputs_decision_ber_2025.

### 2026-06-10: FYP reconcile 完成 + 跑 faithful F2-P (详见 findings.md 同日 reconcile 段)
- 用户提示 "FYP 特殊命令, 复现不出来" → 找到 `REPRODUCTION.md`:
  - **特殊命令 = F2-P deployment** `--refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2`.
    无此 = plain C2-rel single-pass = **我 Phase-6 跑的弱变体** → 这就是 head≈OMP 的原因.
  - **复现不出来 = 4B 3-seed 绝对 BER 无源 JSON** (2B delta −37.7% 可复现, 4B 绝对追不到, REPRODUCTION.md 记为 open).
- 原生 3-seed F2P_iter10 (4B,P=8,n_outer=10): classical 1.2e-4 → learned 5.4/3.9/2.9e-5 @SNR20 = **−55~76%**.
  head BER 价值真实但**来自 F2-P engineering (refine+protect-prune), 非检测理论 recall**. counts 小(~12-49)→噪声.
- **整合**: 无 F2-P → head recall 冗余于 cluster-expand(我 Phase-6 证实); F2-P 机制才榨出 cluster-expand 外价值.
  C1 理论解释 recall, BER 靠 F2-P — framing 张力.
- **用户选**: 跑 faithful F2-P Phase-6. 启动 tmux `g_f2p`: paired_learned_eval F2-P, seed s07, fresh data seed
  20260601, SNR{15,20}, target-errors120/max1200, n_outer10. 复现 −55-76% + firm CP CI. 输出 outputs_f2p_firm_s07.
- ⚠️ paired_learned_eval 只末尾存盘 (无增量), 但 tmux 抗 ssh drop (firm-up/c1_sweep 都在 tmux 跑完), 仅 box reboot 才丢.

**Next (g_f2p 完)**: 取 outputs_f2p_firm_s07/results.json 判 head-vs-classical BER + CP CI 是否坐实 −55-76%@SNR20.

### 2026-06-10 (cont.) — g_f2p 完成
- `outputs_f2p_firm_s07/results.json` 落盘 (~11.5 min, early-stop 200帧/SNR)。
- SNR15: −35.6% (6491 vs 4180 errs, McNemar p≈0)。SNR20: −28.2% 含灾难帧 / −49.4% 剔除 (273 vs 196; McNemar 85/8, p=1.1e-17)。
- 结论: F2-P BER 增益 fresh-data 复现, 但 SNR20 headline 应改报 −30~50% 区间, 弃 −55~76% 旧点估计。
- **Next (待用户定)**: (a) F2-P 部件拆解 (refine/protect/prune 哪个给 BER); (b) 3-seed F2-P firm (s08/s09 同 flags); (c) framing 重写 (C1 理论解释 recall vs F2-P engineering 兑现 BER)。

### 2026-06-10 (cont.) — 3-seed F2-P firm 完成
- s08/s09 顺序跑完 (tmux g_f2p23, ~25 min), 与 s07 同 data seed 配对。
- 终局: SNR15 −35.7% (±0.1pp), SNR20 −28.9% (±0.7pp), CP CI 完全分离, McNemar ≤5.5e-17 ×3。剔灾难帧 SNR20 −49.4%。
- Headline 定稿, 弃 −55~76%。裁决实验链全部闭合。
- 待办: framing 重写 (C1 理论 vs F2-P engineering); commit checkpoint。
