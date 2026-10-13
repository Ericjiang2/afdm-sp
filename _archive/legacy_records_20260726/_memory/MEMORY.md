# Memory Index

## Current Status

- Date: `2026-05-17` (**paper-tmlcn IEEE Transactions style cleanup completed**)
- **最新论文状态**：`paper-tmlcn/main.pdf` 已重新编译为 14 页 letter PDF；最终快照为 `paper-tmlcn/main_round2_ieeetrans_20260517.pdf`。同时保留 `main_round0_ieeetrans_20260517_original.pdf` 和 `main_round1_ieeetrans_20260517.pdf` 作为对比版本。
- **本轮重点**：按 IEEE Transactions 风格清理 `paper-tmlcn` 正文、Appendix 和 bibliography。去掉论文可见的代码名、文件名、路径、CLI 参数、QA/内部 provenance、previous-draft 痕迹；把 initialization-faithful result 从 theorem/proof 风格改成 numerical verification claim；appendices 已移到 references 前。
- **引用状态**：`references.bib` 已清理 unused/duplicate/internal-note entries；最终 citation audit 为 46 cited, 0 unused, 0 missing。
- **编译状态**：`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` 成功；`main.log` 无 undefined references、undefined citations、missing BibTeX entries、overfull boxes。仅余 caption/hyperref/underfull 这类非阻断 warning。
- **外部审查**：按用户要求先尝试 Claude MCP `opus 4.7 high`，失败原因是模型 unavailable/no-access；已自动 fallback 到 Codex subagent review。pre-fix 约 5.5/10；post-fix 8.4/10，最后两个残留问题已修复。
- **记录文件**：本轮细节已写入 `paper-tmlcn/PAPER_IMPROVEMENT_LOG.md` 的 `2026-05-17 IEEE Transactions Style Cleanup` section。
- **git 状态提醒**：未 stage/commit。当前 paper 目录还有既有 dirty files：`PAPER_CLAIM_AUDIT.*`、`figures/latex_includes.tex` 等；本轮没有回滚这些已有改动。

- Date: `2026-04-21` (**Loop 4 auto-review 结案，codex 4.5/10 → rubric #1 fail，发现 N=1024 identity bug**)
- **Loop 4 目标：user 指定 N=1024 v=2 tau=10ms，先做 P=6 和 P=8 的 learned vs classical BP**。rubric #1 要求 learned 在整条 waterfall 稳定优于 classical，否则不算通过。
- **最大发现：`ClassicalJointUnrolled` 在 N=1024 有 identity drift**。同样 config 下 NumPy `joint_omp_mp_iterative` vs torch 无 heads、use_soft_decisions=False、complex128、update_sigma2=False，20 帧 SNR=20：classical 11 errs vs torch 117 errs（10.6x），max|H_diff|=0.133，max|x_diff|=0.96。N=256 identity 过，N=1024 坏。**Loop 2/3 里所有依赖 ClassicalJointUnrolled 的 learned-joint 对比都因此不可信**。
- **Learned joint 三次尝试都 fail**（S scalars、B3 final-only、B3+SNR 硬门）：SNR=10 有 5-8% gain，SNR=20+ 则 +25%~60% regression。这 regression 至少一部分来自 identity drift，而非 head 本身。
- **post-classical bit-flip corrector 也 fail**（Codex option B，bug-free 路径）：P=8 test AUC=0.812，P=6 AUC=0.830，但 τ∈[0.10,0.95] 扫过没有任何 τ 让 BER 低于 classical。低 base rate（≤3% @ SNR≤15，<0.1% @ SNR≥20）导致 top-ranked 错 bit 的 precision < 50%，flip 反而增加 BER。matches Loop 1 frozen_corrector pattern。
- **Classical baseline package 很干净**：P∈{6,8} × SNR∈{5,10,15,20,25} × 400 frames × Wilson 95% CI，monotone，never below perf-CSI BP，no cliffs。`figures/loop4/loop4_baseline_p{6,8}.png` 已出图并通过 plot-level sanity check。
- **P=6 canonical numbers (400 f)**：SNR=5/10/15/20/25 → 1.91e-1 / 9.33e-2 / 1.85e-2 / 5.58e-4 / 2.31e-4；perf-CSI BP SNR=25 = 2.44e-5
- **P=8 canonical numbers (400 f)**：SNR=5/10/15/20/25 → 1.91e-1 / 1.03e-1 / 2.78e-2 / 3.48e-3 / 9.56e-4；perf-CSI BP SNR=25 = 0
- **Codex single next step**: 修 N=1024 identity drift 是 highest-leverage blocker。建议 instrument `ClassicalJointUnrolled.forward` dump per-iter `{support_set, gains_S, H_hat, x_soft, sigma2_eff}`，与 NumPy 同帧对比，逐步 bisect（sparsification threshold / DA-LS reg / phase-c / DAFT numerics）。估计 2-4 小时。
- **完整记录**：`AUTO_REVIEW.md` Loop 4 section；`REVIEW_STATE.json` status=completed；`afdm_sp_joint_unrolled/outputs_loop4_{baseline,cache_train,cache_test,corrector}_p{6,8}/`。
- **Loop 4 脚本添加/打 patch**：classical_joint_unrolled.py (`b3_final_only`+`b3_diagnostic` cfg + SNR-gate on delta)、paired_learned_eval.py (`--b3-final-only`+`--use-soft`)、train_classical_joint_unrolled.py (同上 + `[LOOP4_CONFIG]` echo)、plot_loop4_ber_mse.py (whole-curve checks)、loop4_gen_cache.py + loop4_corrector.py (post-classical pipeline)。

---

## 历史 Status: Loop 3 (2026-04-21 早, 结案 6.5/10)

- Date: `2026-04-21` (**Loop 3 auto-review 结案，codex 6.5/10 → 可投 negative-result workshop 短文**)
- **Loop 3 关键转折：Loop 2 的"B1+B2 @ SNR=20 dB BER −90%"在严格 paired eval 下塌了**。训练时 20 帧 eval 的 mean_Δ=-2e-3 完全在噪声内；150 帧 paired eval 在 SNR=10 → +18% regression，SNR=15 → +390% regression。**Loop 4 回头看**：这些 regression 本身也可能被 N=1024 identity drift 污染，不一定是 head 的锅。
- **classical BP joint 在 MATLAB 对齐 (N=1024, v=2, P=5, τ=10ms) 已经几乎顶到 perfect-CSI BP**：SNR=20 classical=2.13e-4，perfect-CSI BP=0，perfect-CSI MMSE=3.6e-4。geom-mean classical/perf-CSI-BP gap 只有 1.97×（在 9 个 sweep 配置里排倒数第二）。
- **真正 headroom 在小 N / 高 Doppler / 高 P 的硬 regime**：N=128 有 33.4× gap，N=1024 v=2 P=15 有 2.97× gap，N=1024 v=4 有 6.94× gap。

---

## 历史 Status: Round 8+ (2026-04-20, 已被 Loop 3 的 paired eval 部分推翻)

- Date: `2026-04-20` (**Round 8+ BP/MATLAB align & re-eval — 未改分数，推翻旧结论之一**)
- **本轮（2026-04-20）关键转折**：重新审视 BP joint receiver，发现 4-way eval 里 "BP 烂" 的结论是 **P_paths=10 vs 5 config 错配** artifact。
  - Python 在 MATLAB 对齐 config (N=1024, P=5, rho=0.5, tau=10ms) 下 Joint BP @ SNR=20 = **7.81e-5** vs MATLAB 的 1.99e-4，**Python 反而赢 2.5x**。
  - MATLAB `MP_detection_optimized` 和 Python `mp_detect_bp_torch` **逐行一致**（docs/Algorithm_Details.md §3.6 原来"MATLAB 无 factor-of-2"说法已被推翻）。
  - **PIC damp=0.5 是 AFDM 上不稳定的 default**：40 paired frames perfect-CSI 下 3/40 catastrophic。换 damp=0.3 立刻零错。之前 "B1 on PIC d=0.5 大胜 classical" 的光环大部分是 **B1 在救 d=0.5 instability**，换 d=0.3 后 classical 自己就胜过老 learned。
  - **B1 on BP @ 真 UWA (N=1024 P=5 tau=10ms)** 有微弱提升（mean_Δ=−2.13e-3），主要在 SNR=10；高 SNR classical 已逼近下界，B1 无 headroom。
- **引入早停机制**：`--patience 3` + `--eval-every 30`，省 40% 训练时间。
- **新增 CLI arg**: `--p-paths`, `--tau-spread`, `--mp-mode`, `--pic-damp`（train/eval 脚本）
- **详细记录**: 见 `docs/Results.md` §EXP-20260420-matlab-align 和 §EXP-20260420-b1-bp-uwa; `docs/Knowledge.md` §pic-bp-damping; `_memory/research_progress.md` 2026-04-20 entry
- **Open questions**:
  1. B1 only 的 modest 改善（10% BER 在 SNR=10）够不够发论文？
  2. 推进 learned receiver 的下一步方向（CE-side head / multi-refiner / distillation loss）
  3. 小信道（N=64/128/256）场景 B1 帮不上（classical 已近最优）

---

## 历史 Status: Round 8 (2026-04-19, 已被 Round 8+ 部分推翻)

- Date: `2026-04-19` (**Round 8 已结案，从 7.5/10 → 8.4/10，Ready for submission**)
- **Round 8 核心转向**: 从"12-feature ceiling"叙事转向"teacher-margin privileged information gap"诊断。关键 insight：frozen corrector 在 actionable set (bits_pred != bits_teacher) 上 slice-AUC = 0.494 (纯随机)，即它只靠 prevalence 赢。teacher |mu| 在 actionable set 上近乎完美分离 beneficial/harmful（|mu|>0.3 → 94% beneficial；<0.1 → 33%）。
- **新方法**: 4-参数 logistic regression 融合 [|mu_teacher|, |LLR_model|, snr_db]，在 3-seed 未触测 cache 上得 +1.46e-2 BER gain（vs 原 corrector +1.11e-3，13×）。权重物理可解释（teacher confidence +，model confidence -，snr +）。
- **Round 8 验证链**：
  1. headroom decomposition probe: slice_AUC=0.494 → Bayes ceiling at 12-feat 确认
  2. 1-parameter gate τ=0.1: +1.36e-2 gain, 3-seed std 1.9e-4，rate-matched random control +4.33e-3 → 因果确认
  3. 4-parameter learned LR: +1.46e-2 gain, 权重符号与 physics 一致
- **Codex 8.4/10 Ready 评价**:  "mechanism-grounded learned method that is still tiny, interpretable, and reproducible; no experimental blocker remains"
- Codex thread `019da450-d14d-75a3-8dab-1a9c61ec919e` (本轮新开)
- Pre-Round-8 thread `019d9ef0-ebb4-7b11-adc8-b2ccbcfd68b2` 归档

## 历史 Status (Round 7, 2026-04-19 早)
- **注意**：Round 7 的 "12-feature ceiling / 7.5/10 capped" 结论已被 Round 8 superseded — 12-feat 信息上限本身仍成立，但 headroom 并非全部不可达；被 teacher-|mu| 这条独立轴捕获了一大块（+1.46e-2 学习融合 gain）。
- **Round 7 核心结论**:
  - **Task 1 ρ-trend 根因 = C3（OMP K）**: Python 之前把 `n_paths=5` 作为默认，远小于物理 `P_paths=10`，导致 OMP 严重欠参数化，无法 realize 低 ρ 下的 CE 质量退化。改为 K=10 后 3 seeds 验证呈现 **物理 crossover**：5-15 dB 噪声主导 → 低 ρ 赢（更多数据能量）；20-25 dB CE-limited → 低 ρ 输（导致 CE 差）。20 dB 处 ρ=0.5 BER 1.63e-4 < ρ=0.4 1.14e-3 < ρ=0.3 1.53e-3，清晰的 MATLAB-trend 符号。默认已改为 K=10；K=5 改为显式 ablation 标志。
  - **Task 1 过时的排除**：
    - C2 (pilot ZC vs random-QPSK) 不翻转 trend
    - C1 (禁用 adaptive sigma²) 不翻转 trend；MATLAB 本身也开启 adaptive sigma² (`UPDATE_SIGMA2_EACH_OUTER=true`，earlier explore 的"MATLAB 用 fixed sigma²"说法是错的)
    - MATLAB `power_levels = [data, pilot]` convention 正确无误，与 Python ρ 定义一致
  - **Task 2 D1 (focal/topk_bce/rank) 失败**: focal γ=2 只多出 3.4% BER gain（1.65e-3 vs BCE 1.60e-3，in seed noise）；rank 更差；topk_bce 有 bug
  - Codex 认定 12-feature + 小 MLP + 后验 corrector paradigm 已经 local Bayes 近最优，loss 调参无法抓到 3.15e-2 oracle gap；需要新信息源 / 新架构才有希望
  - **Task 3 (NN-sparsity-predictor) Codex 建议暂缓**: 先做 K 固定扫描诊断，如果 K=10 直接修好 mismatch，NN controller 多余

## 历史结论（保留）
- Round 6: 3 条 DNN 提升轴（residual-patch, F2 neighbour LLR, CJ hard-finetune on 10/15 dB）全部落地验证为 net-neutral 或 ceiling-shift（非扩张）
- 7.5/10 paper 正分在当前仿真族内本质上 capped
- 最新回路: **方法提升回路 Round 6 — 已完成**, Codex verdict: **stable but capped at 7.5/10 within this simulator family**
- 总分数仍然是 `7.5/10`（上一轮 FYP restructure 已经在 85.7/100 A1-A5）
- 当前项目状态：论文与方法系统已到达当前 AFDM 仿真族内信息上限，无强制性下一轮需要启动
- Round 6 核心结论（三个独立证据证明特征上限）：
  - T1 tail-precision probe: tail@0.4% = 0.64 ≈ corrector beneficial/total 0.63（Bayes 特征上限签名）
  - F2 邻居 |LLR|（Round 3）: 死路
  - Round 6 Part A: DAFT 残差-patch 特征（±4 邻居 + 自身 re/im）全局净负面
  - Round 6 Part B: 10/15 dB fixed-noise CJ fine-tune 仅 +1e-4 系统 BER 改善（ceiling 被在 CJ 和 corrector 之间重新分配，并未扩展）
- Codex 结束语：不要再花时间在更重的 CJ 重训或 loss 重构上，除非愿意改变论文 scope；7.5 是当前仿真族内的诚实上限
- 被 park 的方向：tail-aware loss 内部 CJ、跨信道族 transfer（需新仿真器）、coded-link（用户已否决为 unfair）
- Codex thread `019d9ef0-ebb4-7b11-adc8-b2ccbcfd68b2` 在本回路内活跃

## 之前的诊断回路 (2026-04-18) — 已 deprioritize

- rho sweep Matlab/Python 趋势不一致：Python adaptive-noise 使 rho 越低 BER 越低，MATLAB fixed-noise 趋势相反
- `awgn_reference="adaptive"|"fixed"` 已加到 add_awgn（Step 2）并贯穿 teacher-gen 链路（Round 6 Part B）
- ad-gpu SSH 在 Step 3 中断，rho=0.3 row 未取回。Round 6 Codex 明说 rho 诊断线边际价值低（因为跨 rho 历史 claim 已经在 adaptive-noise 下不安全），不再追赶

## 最新历史 Status（已归档）

- Date: `2026-03-30`
- Auto-review loop status: completed for the current target
- Latest external score: `7.5/10`
- Current framing: diagnostic-plus-method
- Main outcome: frozen direct-bit correction plus structural transfer and system-level packet/goodput evidence moved the project from `7.4/10` to an honest `7.5/10`
- The remaining gap above `7.5` is no longer “does the small BER gain matter?” but stronger deployment realism or evidence beyond the current AFDM research environment

## What Changed This Round

- Confirmed the decision-audit mechanism story
- Added observable decision-level baselines
- Upgraded the best baseline into a frozen train-once/test-on-many method
- Fixed the independent-cache evaluation chain to use the pure pilot template
- Added two regime-shift robustness packages:
  - higher Doppler severity
  - lower pilot-power fraction
- Recorded a clear failure boundary under severe path-count shift
- Checked the safest remaining calibration ideas and found:
  - frozen confidence gating collapses to threshold `0.5`, i.e. no gain over the current method
  - disabling correction at `5` dB only gives tiny uplifts (`<= 6.0764e-05`)
- Added a paired-bootstrap evidence package that cleanly separates positive regimes from the failure boundary
- Added feature-group ablation showing the full observable feature set is best and `LLR-only` is much weaker
- Added a dedicated structural-shift evaluator and confirmed a new positive integer-Doppler transfer axis
- Rebuilt the unified evidence package with five regimes, now including `integer_doppler_shift`
- Added a system-impact package translating BER gains into `64/256`-bit packet success and expected-transmission improvements
- Confirmed that the `P_paths=15` harsh failure remains explicit at BER level while packet-level utility becomes endpoint-dependent

## Key Files

- `AUTO_REVIEW.md`
- `REVIEW_STATE.json`
- `CLAIMS_FROM_RESULTS.md`
- `afdm_sp_joint_unrolled/decision_oracle_audit.py`
- `afdm_sp_joint_unrolled/observable_flip_baseline.py`
- `afdm_sp_joint_unrolled/observable_direct_bit_baseline.py`
- `afdm_sp_joint_unrolled/frozen_direct_bit_corrector.py`
- `afdm_sp_joint_unrolled/evaluate_frozen_direct_bit_corrector.py`
- `afdm_sp_joint_unrolled/evaluate_frozen_corrector_structural_shift.py`
- `afdm_sp_joint_unrolled/package_frozen_corrector_evidence.py`
- `afdm_sp_joint_unrolled/package_frozen_corrector_system_impact.py`

## Latest Best Result

- Frozen direct-bit corrector
- Dedicated train cache: `outputs_independent_decision_train_seed7777/train_cache_60frames_seed7777.pt`
- Untouched nominal test caches:
  - `outputs_independent_decision_seed12345/test_cache_30frames_seed12345.pt`
  - `outputs_independent_decision_seed2026/test_cache_30frames_seed2026.pt`
  - `outputs_independent_decision_seed4242/test_cache_30frames_seed4242.pt`
- Aggregate nominal-cache BER:
  - baseline mean: `6.3553e-02`
  - corrected mean: `6.2493e-02`
  - mean gain: `1.0590e-03`
- Shifted-cache highlights:
  - higher Doppler severity (`v_mean=4.0`, `v_std=1.0`): mean gain `8.4310e-04`
  - integer-Doppler structural shift (`use_frac_doppler=False`): mean gain `1.3249e-03`, `95% CI [1.1621e-03, 1.4958e-03]`
  - lower pilot power (`rho=0.4`): mean gain `1.6699e-03`
  - severe path-count shift (`P_paths=15`): BER regression `-7.9883e-03`
- System-level highlights:
  - `64`-bit nominal goodput gain: `+5.22%`
  - `64`-bit integer-Doppler goodput gain: `+5.72%`
  - `256`-bit nominal goodput gain: `+10.76%`
  - `256`-bit integer-Doppler goodput gain: `+11.33%`
  - `256`-bit `P_paths=15`: `0` gain

## Next Step If Continuing

- Keep the frozen corrector fixed
- The project has now reached the target `7.5/10`
- The next blocker above this level is stronger deployment realism or evidence beyond the current AFDM simulator family
- Skip revisiting simple confidence/SNR gating; that space now looks exhausted
- Highest-value upgrade paths:
  - a broader out-of-family frozen-transfer test outside the current AFDM simulator family
  - a coded-system or less toy packet endpoint beyond the current simple ARQ proxy
  - a setting where the same method yields a larger effect
