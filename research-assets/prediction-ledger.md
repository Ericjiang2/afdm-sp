# Prediction ledger（编排者校准记录）

这是一份**校准日志**，不是结果卡，也不是已接受的结论。规则见 `.trellis/spec/research-protocol.md` 的 "Prediction ledger"。
- 概率必须在主跑之前写下，事后不得修改。
- 标注 `retrospective` 的条目是事后补记，概率为重构值，不计入校准分。


### 2026-11-23 (before six-point C1 CRC closed-loop acceptance)

| # | Study | Forecast | p | Source | Outcome | Brier |
|---|---|---|---|---|---|---|
| ML6 | CRC on the original C1 matched graph | Short-report closure passes | .80 | [Frozen protocol](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS_CRC_CLOSED_LOOP.md) | Yes | .0400 |
| ML7 | CRC on the original C1 matched graph | Receive-SNR point or bound meets 0.8 dB | .35 | [Frozen protocol](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS_CRC_CLOSED_LOOP.md) | Yes, 0.9375 dB point gain | .4225 |

### 2026-11-23 (before the first-round forest-code input swap)

| # | Study | Forecast | p | Source | Outcome | Brier |
|---|---|---|---|---|---|---|
| ML4 | Forest LDPC added failures | Incoming log-loss is WORSE | .25 | [Frozen predictions](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS_FOREST_INPUT.md) | Yes | .5625 |
| ML5 | Forest LDPC added failures | Held-input gap is WORSE under both sources | .40 | [Frozen predictions](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS_FOREST_INPUT.md) | No | .1600 |

### 2026-11-23 (before the two-point forest-code C1 replay)

| # | Study | Forecast | p | Source | Outcome | Brier |
|---|---|---|---|---|---|---|
| ML3 | Forest LDPC on C1 | Two-point 0.8 dB gate | PASS .30, BELOW .60, UNRESOLVED .10 | [Frozen predictions](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS_FOREST_MINIMAL.md) | BELOW | .2600 |

### 2026-11-22 (before the matched-LDPC C1 kill test)

| # | Study | Forecast | p | Source | Outcome | Brier |
|---|---|---|---|---|---|---|
| ML1 | Matched LDPC on C1 | Primary L28 decision, conditional on a resolved verdict | KILL .45, MIDDLE .30, CONTINUE .25 | [Frozen predictions](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS.md#forecasts) | MIDDLE | .7550 |
| ML2 | Matched LDPC on C1 | Matched beats AWGN on primary L28 crossing | .65 | [Frozen predictions](../.trellis/tasks/11-22-matched-ldpc-kill-test/PREDICTIONS.md#forecasts) | Yes, by 1.4833 dB | .1225 |

### 2026-11-18 (before the Stage 3 CODELAY run)

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| CD3 | 2026-11-18 | Stage 3 CODELAY | Both frozen FER and four-cell crossing acceptance gates pass | .45 | [Protocol](../experiments/cstate_codelay_sbl_stage3_20261118/PROTOCOL.md) | Joint gate not met. FER passed and 3/4 crossing cells passed. U rho .3 was inconclusive under left censoring. | 0 | .2025 |

### 2026-11-18 (before the F0 round-budget screen)

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| F0K | 2026-11-18 | Native F0 round budget | Neither scenario passes the frozen depth-bottleneck criterion | .70 | [Protocol](../experiments/f0_round_budget_20261118/PROTOCOL.md) | True under the frozen criterion. U and G both inconclusive. | 1 | .09 |

### 2026-11-18 (after the 10-19 pilots, before the slot-mismatch main run)

Forecast author: Sol (`gpt-6.2-sol`).

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| SMQ2 | 2026-11-18 | Paired cap-8/cap-12 Q2 | PERSISTENT .70, MIXED .19, DISPLACEMENT-COMPATIBLE .05, NO-BASELINE or UNINFORMATIVE .06 | — | [Revised protocol](../experiments/slot_mismatch_20261019/PROTOCOL.md) and 10-19 common-trigger pilots | MIXED (r = 0.762712) | — | 1.1522 |
| SMQ1 | 2026-11-18 | Known-noise M | Cap 12 meets ROBUST in at least 3 of 4 cells | .45 | Same. Pilot frames informed the forecast. | 4/4 cap-12 cells ROBUST | 1 | 0.3025 |
| SMN | 2026-11-18 | Unknown-noise G rho .3 cell | Cap-8 estimated-noise crossing is bracketed and no more than .25 dB above the known-noise crossing on the same frames | .55 | Same. Before smoke and all main outcomes. | Bracketed at 6.339 dB, shift +1.189 dB | 0 | 0.3025 |
| SMQ2A | 2026-11-18 | Paired cap-8/cap-12 Q2 | Conditional on passing the D8 gate: r <= .5: .10, .5 < r < .8: .25, r >= .8: .65 | — | [gpt-6.2-astra](../.trellis/tasks/10-19-slot-mismatch/research/astra-q2-prediction.md#prediction-for-the-ledger) | .5 < r < .8 (r = 0.762712) | — | 0.9950 |
| SMR1A | 2026-11-18 | Paired cap-8/cap-12 Q2 | Same-trigger CODELAY (full-block) rescue is lower at cap 12 than at cap 8 | .75 | gpt-6.2-astra, same source | 1,796/7,462 → 1,388/7,462 | 1 | 0.0625 |
| SMR2A | 2026-11-18 | Paired cap-8/cap-12 Q2 | Same-trigger scalar A2 rescue is lower at cap 12 than at cap 8 | .65 | gpt-6.2-astra, same source | 675/7,462 → 533/7,462 | 1 | 0.1225 |
| SMQ2C | 2026-11-18 | Paired cap-8/cap-12 Q2 | PERSISTENT .65, MIXED .27, DISPLACEMENT-COMPATIBLE .04, NO-BASELINE or UNINFORMATIVE .04 | — | [Claude §6](../.trellis/tasks/10-19-slot-mismatch/research/claude-design-review.md#6-claude-当前预测看过-10-19-试跑后主跑前供分歧表使用) | MIXED (r = 0.762712) | — | 0.9586 |
| SMQ1C | 2026-11-18 | Known-noise M | Cap 12 meets ROBUST in at least 3 of 4 cells | .55 | Claude, same source | 4/4 cap-12 cells ROBUST | 1 | 0.2025 |
| SMNC | 2026-11-18 | Unknown-noise G rho .3 cell | Cap-8 estimated-noise crossing is bracketed and no more than .25 dB above the known-noise crossing on the same frames | .50 | Claude, same source | Bracketed at 6.339 dB, shift +1.189 dB | 0 | 0.2500 |

Q2 scoring. For SMQ2 and SMQ2C, sum the squared errors of the four probabilities against the one-hot frozen verdict (unscaled multiclass Brier), pooling NO-BASELINE and UNINFORMATIVE as one outcome. For SMQ2A, score the same sum over the three forecast ratio bands using the observed point ratio r, only if the D8 gate passes (95% lower bound > .05) and r is defined.

| # | 日期 | 实验 | 预测 | p | 来源 | 结果 | 得分 | Brier |
|---|---|---|---|---|---|---|---|---|
| R1 | 2026-10-17 | E-3 | 判定为 MECHANISM-ONLY | ~.6（"大概率"） | 跑前，`external-sbl-e3/research/expectation-before-run.md` | MECHANISM-ONLY | 1 | retrospective（概率措辞未量化） |
| R2 | 2026-10-17 | E-3 | 在 SBL 中，标量 Γ 产生的幻影对 FER 无害（FER 不变） | ~.6 | 同上 | 标量 Γ 的 FER 明显**更好** | 0 | retrospective |
| R3 | 2026-10-17 | E-3b | 加入连续细化后，标量 Γ 的优势消失（on-grid 插值解释） | ~.6 | 事后重构（res-20261017-03 第 3 条） | PERSISTS | 0 | retrospective |
| R4 | 2026-10-18 | GSO | 只用 Γ 选原子、再用无 Γ 的 LS 解增益，结果优于 C-sbl（Berkson 解释） | ~.6 | 事后重构（res-20261018-02 第 4 条） | VARIANCE-SUPPORTED（反向） | 0 | retrospective |
| R5 | 2026-10-18 | 前瞻检验 | 决策/估计划分在新帧上成立（CONFIRMED 或 PARTIAL） | ~.7（对用户说"能解释所有主要结果"） | 事后重构 | REFUTED | 0 | retrospective |
| R6 | 2026-10-18 | 前瞻检验 | P4：完整 Γ 的交换决策优于对角 Γ（复现 E-1） | ~.9 | 事后重构 | 成立（+.18） | 1 | retrospective |

事后补记的小结（只作参考，不计分）：6 条里中了 2 条。我给的把握在 .6–.7 的 4 条事后解释全部落空；只有站在已有预注册证据上的两条命中。这说明我在"提出新解释"时系统性地过度自信，此后此类解释的默认措辞应降为"低置信"。

### 2026-10-19（跑前写下；前瞻）

| # | 日期 | 实验 | 预测 | p | 来源 | 结果 | 得分 | Brier |
|---|---|---|---|---|---|---|---|---|
| P1 | 2026-10-19 | 排序反转检验 | R1 CI 下界 ≥ .85 | .50 | `posthoc_rank_inversion_20261019/PROTOCOL.md` | 成立（但功效检查显示无区分力） | 1 | .25 |
| P2 | 2026-10-19 | 排序反转检验 | ΔAUC CI 下界 > 0 | .55 | 同上 | 不成立（−.067） | 0 | .30 |
| P3 | 2026-10-19 | 排序反转检验 | 判定 CONSISTENT .35 / PARTIAL .40 / INCONSISTENT .25 | — | 同上 | PARTIAL | — | .55（多类） |
| P4 | 2026-10-19 | 试跑 3 | D₄/D₂ ≥ .9 | .55 | `slot_mismatch_20261019/POSTHOC_CHECKS.md` | 成立（1.00） | 1 | .20 |
| P5 | 2026-10-19 | 试跑 3 | 4 次交换后完整 Γ 救回率上升 | .70 | 同上 | 实质不成立（+.005） | 0 | .49 |
| P6 | 2026-10-19 | 生成器/SNR 审计 | H0：定义与算子一致 | .80 | Codex 写的 `generator_snr_audit_20261019/PROTOCOL.md`（非编排者预测） | 成立 | 1 | .04 |

小结：编排者 5 条（P1–P5）里，二元预测命中 2/4；对"新机制会改善结果"类预测（P2、P5）再次落空，与 10-18 的事后小结一致。
| P7 | 2026-10-19 | 检测器增益线索零仿真检验（10-18 K 族行） | 固定增益的净提升（K-diag-fullfix 救回而 K-diag 失败，减去反向）在 K-diag 几何最大 \|D_N\| ≥ .8 层大于"无同时延对"层，且两层 95% CI 不重叠（检测器假说被支持） | .45 | 本行（跑前提交 7240fe71） | 成立：有对层 +.068 [.055, .082]，无对层 −.010 [−.030, 0]（`experiments/detector_gain_lead_20261019/result.json`） | 1 | .30 |
| P8 | 2026-10-19 | 检测器线索 CSTATE 侧小仿真（试跑 2 键，上限 8，A2 含同时延对的单元） | A2 失败单元中，A2-fix（同原子、增益固定为完整 Γ 解）的救回率 ≥ .05 | .65 | 本行（跑前提交 1b6e2426） | 成立：.184 [.139, .232]（52/283） | 1 | .12 |
| P9 | 2026-10-19 | 同上 | 同一批 A2 失败单元上，A2-merge（每个时延合并为一个原子，Doppler 取 \|gain\|² 加权均值，检测器照常联合重估）的救回率 ≥ A2-fix | .45 | 同上 | 不成立：merge .127 < fix .184，差 −.057 [−.093, −.021] | 0 | .20 |
| P10 | 2026-10-19 | 同上 | A2 成功且含同时延对的单元上，fix 与 merge 各自弄坏的比例都 ≤ .05 | .70 | 同上 | 点估计成立（fix .039、merge .013；fix 的 CI 上界 .085） | 1 | .09 |
| P11 | 2026-10-19 | 检测器线索 SBL 侧小试跑（E-3 on-grid SBL；ρ .3，U+G，7/8 dB，新帧 9100–9299；同一 SBL 输出接 fixed / joint 两种检测器） | 联合重估对标量 Γ 的伤害大于对完整 Γ：[FER(diag,joint)−FER(diag,fixed)] − [FER(cov,joint)−FER(cov,fixed)] > 0 且 CI 下界 > 0 | .65 | 本行（跑前提交 cd8d5cd8） | 成立：+.148 [.116, .179] | 1 | .12 |
| P12 | 2026-10-19 | 同上 | 标量 Γ 的优势至少减半：A_joint ≤ .5·A_fixed，A_m = FER(cov,m) − FER(diag,m) | .50 | 同上 | 成立（但因符号翻转而平凡成立：A_fixed +.064 → A_joint −.084） | 1 | .25 |
| P13 | 2026-10-19 | 同上（退化预检） | 两种 Γ 在 joint 下 FER 都 ≥ .9（联合重估在 ~20 个原子的基上整体崩溃，试跑无区分力） | .20 | 同上 | 未发生（joint FER：diag .101，cov .018） | 0 | .04 |

### 2026-10-20 (before the three-mode exploratory replay)

Old-data exploratory pilot, not independent confirmation: frames 9100..9149, U/G, rho .3, 7/8 dB, 200 keys / 50 shared-frame clusters. No point-mode outcomes had been inspected at registration. The known full Pilot-5 fixed/joint outcomes motivated the design. Protocol (task archived after the readout): `.trellis/tasks/archive/2026-10/10-20-sbl-detector-three-mode/protocol.md`.

| # | Date | Experiment | Prediction | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| P14 | 2026-10-20 | SBL fixed/point/joint pilot | Scalar-Gamma point FER lies between scalar fixed and joint FER (inclusive; point estimates) | .55 | This entry, before execution (d3e4a468) | False: fixed .020, point .200, joint .115 | 0 | .3025 |
| P15 | 2026-10-20 | Same | Scalar FER(point)-FER(fixed) has a paired frame-cluster 95% CI lower bound > 0 | .50 | Same | True: +.180 [.130, .235] | 1 | .2500 |
| P16 | 2026-10-20 | Same | Scalar FER(joint)-FER(point) has a paired frame-cluster 95% CI lower bound > 0 | .45 | Same | False, reversed: -.085 [-.130, -.045] | 0 | .2025 |

Non-significance will not be called equivalence. Mode effects do not establish a Gram/Onsager mechanism. No sample extension is conditional on these outcomes.

Readout: `experiments/sbl_three_mode_20261020/SUMMARY.md`. Two of three expectations failed; point was worse than joint rather than intermediate. Receiver rows were complete and replay-qualified before an aggregation-only path fix; no new receiver run or sample extension.

### 2026-10-20 (before final-gain freeze replay)

User-approved follow-up, scalar Gamma only, same 200 keys / 50 old frame clusters. Previous fixed20/point20/joint20 outcomes are known; no RF/P40 outcome has been inspected. RF is saved point20 gains followed by fresh fixed20 with the original check prior; P40 is continuous point40 from h0. This is exploratory, and RF combines state reset with freezing. Protocol: `.trellis/tasks/10-20-sbl-freeze-replay/protocol.md`.

| # | Date | Experiment | Prediction | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| P17 | 2026-10-20 | SBL freeze replay | FER(RF)-FER(point20) has paired frame-cluster 95% CI upper < 0 | .60 | This entry before execution (feffc7ed; source-only recovery 50d79546) | True: -.100 [-.155, -.055] | 1 | .1600 |
| P18 | 2026-10-20 | Same | FER(P40)-FER(point20) has paired frame-cluster 95% CI upper < 0 | .45 | Same | False: +.005 [-.025, .035] | 0 | .2025 |
| P19 | 2026-10-20 | Same | FER(RF)-FER(P40) has paired frame-cluster 95% CI upper < 0 | .55 | Same | True: -.105 [-.150, -.065] | 1 | .2025 |

Pointwise exploratory intervals; no non-significance-as-equivalence, new sample, automatic arm or tuning follows a result.

Readout: `experiments/sbl_freeze_replay_20261020/SUMMARY.md`. RF combines reset and freeze and recovers 21 old point20 failures while breaking 1; continuous P40 rescues 6 and breaks 7. No equivalence, new-frame confirmation or isolated mechanism claim.

### 2026-10-20 (before the user-approved restart-point addendum)

Known RF/P40 outcomes motivated this single-arm exploratory addition. No RP outcome has been inspected. Same 200 keys / 50 old frame clusters; full cohort, not selected failures. Protocol: `.trellis/tasks/10-20-sbl-freeze-replay/protocol.md`, prospective restart-point addendum.

| # | Date | Experiment | Prediction | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| P20 | 2026-10-20 | SBL restart point20 | FER(RP)-FER(RF) has paired frame-cluster 95% CI lower > 0 | .50 | This entry before execution (99f918be) | True: +.055 [.015, .095] | 1 | .2500 |
| P21 | 2026-10-20 | Same | FER(RP)-FER(P40) has paired frame-cluster 95% CI upper < 0 | .55 | Same | True: -.050 [-.085, -.015] | 1 | .2025 |

No equivalence conclusion from a null-spanning interval; no automatic arm or sample extension follows.

Readout: `experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md`. RP 31 failures versus RF20/P4041. Both conditional operational contrasts pass their registered directional interval criteria; no additive mechanism or new-frame confirmation is claimed.

### 2026-10-20 (before saved-trajectory analysis; analysis-informed)

Known endpoint MSE/variance, FER and channel-NMSE means motivated these checks. Full time-average E/V/gap contrasts were not inspected. This is exploratory analysis of old data, not a new experiment; keep these forecasts separate from uninformed prospective experimental calibration. Protocol: current freeze-replay task, trajectory analysis addendum.

| # | Date | Analysis | Pattern forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| T1 | 2026-10-20 | Saved six-arm trajectories | Scalar point-fixed time-average E CI lower>0 AND V CI upper<0 | .60 | This entry before analysis (ef324633), informed by known endpoints | True: DeltaE +.015084 [.012952,.017219], DeltaV -.018177 [-.019337,-.017032] | 1 | .1600 |
| T2 | 2026-10-20 | Same | Time-average gap interaction (point-fixed)_scalar minus (point-fixed)_full has CI lower>0 | .55 | Same | True: +.003528 [.001783,.005318] | 1 | .2025 |

Neither pattern check is a causal mechanism verdict; no window/iteration is selected after the readout.

Readout 2026-10-21: `experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md`. Both directional checks pass, but the moment mismatch is shared by both Gamma variants and is not a variance-causality or unified-mechanism verdict. Forecasts remain analysis-informed, separate from uninformed prospective experimental calibration.

### 2026-10-21 (before duplicate-representation numerical qualification)

Code-derived engineering forecasts, not new FER or mechanism hypotheses. One fixed synthetic fixture and one predetermined old real key only. Algebra is recorded before outcomes in the active task research/representation-invariance.md.

| # | Date | Probe | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| I1 | 2026-10-21 | Uniform2x duplicates | Original/duplicate fixed20 outputs and first point symbol outputs pass rtol1e-10/atol1e-12 parity in both predetermined cases | .95 | This entry before execution (c4635b24) | True: fixed/first-symbol differences at floating precision in both cases | 1 | .0025 |
| I2 | 2026-10-21 | Same | First aggregate point-gain update matches the derived formula and changes physical channel action above relative1e-8 in both cases | .90 | Same | True: formula residual <=1.12e-16; physical differences .062906/1.380326 | 1 | .0100 |

A structural approximation probe; exclude from independent experimental mechanism/performance calibration. No sample replacement if the case is uninformative.

Readout: `experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md`. Both engineering checks pass. Exact working-prior equivalence and first native point-update non-invariance are established within the stated construction; no Gamma-reversal causal or FER trend claim.

### 2026-10-21 (before matched soft-Gram block qualification)

Engineering forecasts after algebraic design, not independent performance/mechanism calibration. Minimal synthetic fixture + one fixed old real key only; no 200-key run. Protocol and research/full-gram-gain-block.md in the current task define the surrogate and schedule.

| # | Date | Gate | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| G1 | 2026-10-21 | Soft-Gram block gate | Native prototype replays original point and full-block trajectories preserve uniform2x duplicate aggregation/LLRs within rtol1e-10/atol1e-12 in both cases | .90 | This entry before execution (5d2feb6e) | True: native bit-exact replay, full20 states and all-step LLR duplicate invariance; observer completion62f70a16 | 1 | .0100 |
| G2 | 2026-10-21 | Same | Diagonal block has relative physical first-update representation difference>1e-8 in both predetermined cases | .85 | Same | True: first relative physical difference .976126/.990782 | 1 | .0225 |

A gate pass establishes implementation/invariance, not a useful FER gain or a proof that actual SBL near-duplicates cause reversal.

Readout: `experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md`. Both engineering forecasts pass after the same-case observer completion; this is not independent replication. Real single-key full/diag error counts0/351 (native point42; old fixed0) are descriptive, not FER improvement or a mechanism verdict. No automatic200-key extension.

### 2026-10-21 (before actual-support soft-Gram cohort)

Informed screening forecasts: old native cohort outcomes and the predetermined single new real-key result are known. Neither the new200-key endpoints nor contrasts have been inspected. Same old samples, no independent confirmation. Current task protocol defines pointwise paired frame-cluster criteria.

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| C1 | 2026-10-21 | Soft-Gram actual support | Full-minus-diag FER CI upper<0 for BOTH upstream variants | .75 | Before execution (ee5882ce) | True: scalar -1[-1,-1]; full -.990[-1,-.970] | 1 | .0625 |
| C2 | 2026-10-21 | Same | L-diag new-full minus L-diag native-point FER CI upper<0 | .65 | Same | True: -.200[-.255,-.150] | 1 | .1225 |
| C3 | 2026-10-21 | Same | L-cov new-full has <=2 failed keys (descriptive screening only) | .35 | Same, pre-freeze power correction below | True:0 failures; descriptive only | 1 | .4225 |

These forecasts do not define post-hoc success, equivalence or a Gamma-reversal mechanism verdict. No automatic cohort extension.

Pre-freeze correction, before any cohort call: the initially drafted C3 forecast was CI upper<0 (p=.20). With only2 best-reference failures, negative differences occupy<=2 frame clusters; bootstrap probability of selecting neither is at least(48/50)^50=.1299, so the95% percentile upper bound cannot credibly be negative even for a perfect candidate. Replace that infeasible statistical forecast with the stated raw-count forecast (p=.35); do not call <=2 failures noninferiority. All reference contrasts and intervals remain reported unchanged. No new outcome was inspected.

Readout: `experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md`. Independent raw/primary-bootstrap audit passes. Both new full arms0/200, best native2/200; benchmark CI[-.025,0] remains inconclusive. Mean log-loss improvement and added instrumented compute are reported. No independent confirmation, noninferiority, Gamma mechanism verdict or automatic extension.


### 2026-10-21 (before Gamma-only off-diagonal ablation)

Informed screening forecasts on the same old cohort; all prior full/whole-Gram-diag outcomes known, no gamma_diag receiver outcomes inspected. The current task protocol fixes primary logloss(new gamma_diag)-logloss(saved full), paired50frame bootstrap10000draws seed20261027, pointwise95% intervals. No equivalence or native-failure mechanism criterion.

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| GA1 | 2026-10-21 | Full-BHB / Gamma-only ablation | L-diag upstream primary logloss difference CI lower>0 | .65 | Before gate/main execution (1198b266) | True: +.045642 [.042346,.048891] | 1 | .1225 |
| GA2 | 2026-10-21 | Same | L-cov upstream primary logloss difference CI lower>0 | .55 | Same | True: +.012258 [.010382,.014279] | 1 | .2025 |

Confidence in a useful engineering discrimination is M; confidence in explaining the original Gamma reversal from this test is L. An inconclusive or reversed result ends this run without selecting cells, adding arms or changing predictions.

Readout: `experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md`. Both informed forecasts pass; independent raw/count/bootstrap audit passes. Removing only Gamma off-diagonals increases logloss under both saved upstreams; scalar-upstream decoding loses6keys, full-upstream has0failures either way. Same old samples, no native-failure mechanism or generalization claim and no automatic extension.


### 2026-10-21 (before prospective new-frame full-block validation)

Frozen-method validation on uninspected P1 frames2000000..2000049, same4cells; design informed by old cohorts, all new outcomes unseen. Two candidates compared with fixed L-cov/native-joint reference using primary logloss(candidate-reference), paired50frame bootstrap10000draws seed20261028. No FER equivalence or mechanism criterion.

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| NF1 | 2026-10-21 | Fresh-frame full-block validation | L-diag/full minus L-cov/native-joint pooled logloss CI upper<0 | .70 | Before any fresh receiver outcome (73882cff) | True: -.027495 [-.032228,-.022813] | 1 | .0900 |
| NF2 | 2026-10-21 | Same | L-cov/full minus L-cov/native-joint pooled logloss CI upper<0 | .75 | Same | True: -.027480 [-.030561,-.024581] | 1 | .0625 |

These evaluate prospective score improvement under the same model, not zero population FER, global CAVI, upstream equivalence or method novelty. Confidence in transferable score benefit within this model M; original native-failure mechanism remains L. No tuning or extension follows automatically.

Readout: `experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md`. NF1/NF2 pass on the reserved fresh frame streams; both full candidates have about12.7%lower logloss,1/200failures versus4/200 reference. FER intervals still include zero; no equivalence/noninferiority or unique-mechanism verdict. Independent raw/count/bootstrap audit passes, no automatic extension.

### 2026-10-21 (before uniform-symbol-variance Gamma comparison)

Informed forecasts on the original50frames/200keys; saved full and Gamma-only-diagonal outcomes known, no new uniform-Gamma outcome inspected. Frozen criterion: T=mean(.1D+.9F-U), joint50frame bootstrap10000seed20261029. PASS requires95%CI lower>=0 with eligible positive baseline denominator;90% retained benefit is a user-approved practical threshold, not equivalence or a mechanism claim.

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| UG1 | 2026-10-21 | Uniform-symbol-variance Gamma | L-diag pooled90%retention criterion PASS | .70 | Before gate/main execution (de5926fa) | True: T=+.004564 [.004243,.004892], R=.999996 | 1 | .0900 |
| UG2 | 2026-10-21 | Same | L-cov pooled90%retention criterion PASS | .65 | Same | True: T=+.001225 [.001041,.001422], R=.999945 | 1 | .1225 |

Confidence M. Synthetic identity is known; adequacy through20hybrid iterations is untested. Mixed/inconclusive/adverse outcomes end this bounded run without threshold changes or automatic extension.

Readout: `experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md`. Both forecasts pass; independent raw/count/bootstrap audit passes. Replacing per-symbol variances by their average, while retaining atom geometry, preserves essentially all of the full-versus-diagonal Gamma logloss benefit (retention ~.99999/.99994; all four cells pointwise pass). The same-delay block projection is sufficient on this old cohort; no FER difference, new frames, mechanism/novelty, or optimization claim follows.

### 2026-11-09 (before fixed-channel OAMP/LDPC replay)

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| OA1 | 2026-11-09 | Fixed-channel OAMP/LDPC replay | OAMP recovers at least 17 of 34 archived CSTATE rescues and uses at most 2× the matched fixed-TF median continuation time | .25 | [Protocol](../experiments/oamp_ldpc_20261109/PROTOCOL.md), frozen at `cd24f670` | False: 9/34 and 7.309×. Fixed TF recovered 14/34. | 0 | .0625 |

Readout: [compact results](../afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/results.json), [sealed decision hashes](../afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/observed_seal.json), [run log](../afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/run.log). The 40 raw decision artifacts remain at `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/`. Offline compact-row recount and protocol/source hash checks passed. The result is a development screen on reused frames.

Correction after the user challenged fairness: OA1 scores the original two-call screen only. Same-adapter continuation recovers15frames at round20 versus9 at round2, with24frames still changing hard decisions. A one-step exact structured-solver benchmark also reduces dense setup/update time. Neither the initial prediction score nor its failed gate eliminates OAMP as a converged/efficient baseline. See the parent-task [correction and Opus5.5 review](../.trellis/tasks/09-22-tf-production-gap-audit/research/oamp-ldpc-screen-20261109.md).


### 2026-11-09 (before structured solver and syndrome stopping)

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| OS1 | 2026-11-09 | Structured OAMP-form turbo-LMMSE plus early stop | Structured and dense adapters each rescue15/40, TF14/40, no undetected stops | .80 | [Frozen plan](../experiments/oamp_ldpc_20261109/STRUCTURED_STOP_PLAN.md), initial freeze974596a6 | True:15/15/14, undetected0 | 1 | .04 |

Readout: [structured and early-stop comparison](../experiments/oamp_ldpc_20261109/STRUCTURED_STOP_RESULTS.md). Structured/dense/TF median complete continuations2.877/1.108/.0858s. Same-input linear qualification passes; autonomous trajectories are not bit-identical. V1/v2 qualification failures and amendments precede timed outcomes and remain explicit.

### 2026-11-11 (before zero-simulation readouts on the saved block-rescue and J4-width rows; Fable idea dialogue, round 9)

Analysis-informed forecasts on saved rows; no receiver, detector or decoder call. Known before registration: both
RESULTS.md aggregates (error counts; 255 triggers changed delay set; FULL/SCALAR differ in one support), one raw row of
each run (block rescue U/4.5 dB/frame 0; J4 width frame 0/rho .3/8 dB), and the round-8 per-frame readout of the rho .5
narrow arm on the same J4 channels. Not inspected: per-cell `groups` of the block arms, per-cell `selected` tap and ONE
outcomes. Not committed (the ledger carries another session's uncommitted OS1 scoring); the pre-readout file hash is
recorded in `.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md`, round 9.

Definitions. Block rescue: `experiments/dpss_block_rescue_20261110/out/rows-*.jsonl`, delay of a group = group // 5,
truth delays from `experiments/dpss_p1_pilot_20261110/out/rows-*.jsonl`. J4 width:
`experiments/dpss_j4_width_20261110/out/rows-*.jsonl`, rho .3 cells with a narrow trigger; ray geometry redrawn with the
frozen generator (`draw_cluster_geometry`, `cluster_paths`, pilot entropy). e_t = share of total channel energy carried
by rays of true tap t lying more than .75 bin from the integer nearest to that tap's strongest ray (definition fixed in
round 8). L = sum of e_t over true taps other than the selected delay. Bootstrap: 4000 frame-cluster draws.

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| BR1 | 2026-11-11 | Block rescue rows (zero-sim) | Of the delays newly admitted by FULL (in its final set, absent from LOCAL's), the share that are true delays is >= .80 | .60 | This entry, before the readout | True: 385/438 = .879 [.841, .913] | 1 | .16 |
| BR2 | 2026-11-11 | Same | P(FULL final set misses >= 1 true delay) is higher by >= .20 in cells where B decodes and FULL fails than in triggered cells where both decode | .55 | Same | False: .566 (n 53) vs .476 (n 168), diff +.090 | 0 | .3025 |
| JW1 | 2026-11-11 | J4 width rows + redrawn geometry (zero-sim) | At rho .3 the selected delay is the true tap with the largest e_t in >= .50 of triggered cells (chance .25 among four taps) | .55 | Same | True: .634 [.537, .728], 232 cells | 1 | .2025 |
| JW2 | 2026-11-11 | Same | At rho .3, AUC of L for ONE failure (pooled over the three SNRs) is >= .70 | .55 | Same | True: AUC .800 [.707, .875] | 1 | .2025 |

Reading rule fixed now. BR1 false: the block delay exchange does not mainly add true delays. BR2 false: the shortfall to
path B is not located in the delay support. JW1 false: the observed-residual ranking does not find the tap that needs
widening. JW2 false: left-over out-of-block energy does not explain the one-tap failures. None of these is a mechanism
or FER claim; no run, arm or sample follows from the outcome.

Readout 2026-11-11 (zero receiver calls; script inline in the session, inputs as defined above). BR1: FULL's exchange
admits true delays (385 of 438) and drops 11 true ones of 438. BR2: the frozen threshold fails; FULL-fail/B-ok cells
still miss a true delay only slightly more often than rescued cells, so the remaining shortfall to path B is not
located in the delay support by this readout. JW1/JW2: the residual ranking picks the max-e_t tap in .634 of cells
(chance .25); ONE failure rises with left-over out-of-block energy (.05 / .43 / .61 / .85 across L bins). All four are
analysis-informed descriptions on development rows; no mechanism, FER or population claim.

### 2026-11-11 (deinlab receiver screens)

The forecast probabilities below were frozen in the transferred experiment protocols before main execution. This entry records their readout.

| # | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---:|---|---|---:|---:|
| DB1 | Fresh block receiver screen | All three FER .1 crossing point contrasts are within +.2 dB | .25 | [Protocol](../experiments/dpss_paired_screen_20261111/PROTOCOL.md) | False. P1 U/G +.064/+.105 dB; J4 is unbracketed and is at 98/160 failures at 8.5 dB versus WIDE 4/160. | 0 | .0625 |
| DA1 | CSTATE score × update replay | Full scoring has a positive FER point advantage under the matched expected-Gram gain mean | .55 | [Protocol](../experiments/cstate_score_update_20261111/PROTOCOL.md) | True. Conditional advantage +37.85 pp [32.11, 43.75], 251 P1 triggers. | 1 | .2025 |

[Experiment readout](../.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md).

### 2026-11-11 (before the phantom-admission law readout on saved slot-mismatch pilot-2 rows; Fable dialogue round 10)

Derived law (integer delays, uniform symbol variance vbar, unit symbol power, E = ||pilot + soft mean||^2, lam = N*vbar +
sigma2): under the scalar model a duplicate of an occupied path of gain h_s lowers the ridge objective by
|c|^2*lam/((2E+lam)(E+lam)), so it outscores a missing true path of gain h_w iff |h_w|^2/|h_s|^2 < theta_sc =
lam/(2E+lam) ~ vbar/(2-vbar); under the full Gamma the threshold is sigma2/(2N+sigma2). Closed forms were checked
against direct ridge solves on an exact N=256 operator model before this entry (no receiver). vbar is not saved per
unit, so only shape and threshold range are tested.

Data: `experiments/slot_mismatch_20261019/out/pilot2/rows_shard*` (rho .3, 4.5–5.5 dB, frames 7800–7999, U/G), cap 8,
triggered units, first edit (step 0). Zero receiver calls. Known before registration: one raw row (schema), the
POSTHOC_CHECKS aggregates of this pilot (rescue rates, edit classes for edits 3–4), and the E-1/E-2/rank-inversion
readouts (A2 first edits ~95% phantoms; post hoc power-ratio AUC .812 on E-2). Not inspected: per-unit first-edit
classes joined with truth gains on these rows. Definitions: occupied true delay = true delay present in F0 r1_delays;
missed = true delay absent; phantom = first-edit new delay already occupied; h_s = largest |gain| among occupied true
delays; h_w = largest |gain| among missed true delays; r = |h_w|^2/|h_s|^2.

| # | Date | Study | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---|---|---|---|---|---|
| PL1 | 2026-11-11 | Phantom law, scalar arm A2 (zero-sim) | Among phantom first edits, the phantom's delay is the strongest occupied true delay in >= .60 of units | .65 | This entry, before the readout | True: .924 (n 357) | 1 | .1225 |
| PL2 | 2026-11-11 | Same | Among units with >= 1 missed true delay, phantom share at r < .08 minus phantom share at r > .30 is >= .40 (needs >= 10 units in each bin, else unscorable) | .50 | Same | Unscorable: r > .30 bin has 3 units (r < .08: .987, n 227) | — | — |
| PL3 | 2026-11-11 | Same | Same units: AUC of -log r for "first edit is a phantom" versus "first edit adds a missed true delay" >= .75 | .55 | Same | True: AUC .806, but only 10 non-phantom units | 1 | .2025 |
| PL4 | 2026-11-11 | Phantom law, full arm A1 (zero-sim) | Same units: phantom share of A1 first edits <= .05 | .70 | Same (informed by E-1's 1.5%) | True: .014 (n 362) | 1 | .09 |

Reading rule fixed now: PL1 or PL2 false means the closed form does not describe the receiver's decisions and stays a
toy identity. All four true supports the shape only; it is not a mechanism verdict, and a per-unit test needs vbar.

Readout 2026-11-11 (zero receiver calls). 373 triggered cap-8 units. Scalar first edits: 357 phantom / 10 add a missed
true delay; full: 5 / 342. Phantom share by r: 1.00 (<.03, n 55), .98 (.03–.08, n 172), .98 (.08–.15, n 103), .87
(.15–.30, n 30), .67 (>=.30, n 3). The sample is saturated below the predicted threshold (90% of units have r < .15),
so the shape is consistent and the threshold itself is untested. Analysis-informed, development rows, no mechanism verdict.

### 2026-11-18 — Decision-directed noise variance, before the fresh cohort

The historical N-cap-8 loss (+1.189 dB), the A3 shift (+.321 dB) and the proposed DRAFT were available. Sol expects partial recovery because DD replaces the noisy single-frame moment, while the first-round fit and same-observation APP can create residual bias near the crossing. The hypothesis probabilities are judgments over the three candidate explanations. For scoring use the bracketed B crossing point estimates, with censored events scored only when the bounds settle them. The protocol's paired interval still determines the scientific verdict.

| # | Author | Forecast | p | Source | Outcome | Score | Brier |
|---|---|---|---:|---|---|---:|---:|
| SD1-C | Claude | H-good, absolute DD-minus-known crossing shift ≤ .25 dB | .40 | [Claude draft §4](../.trellis/tasks/11-18-sigma2-dd/research/protocol-DRAFT.md#4-竞争假设与预测claude跑前) | False | 0 | 0.1600 |
| SD2-C | Claude | H-bias, DD remains > .25 dB behind known and improves over SF | .35 | Claude draft §4 | False | 0 | 0.1225 |
| SD3-C | Claude | H-none, absolute SF-minus-DD shift ≤ .25 dB | .25 | Claude draft §4 | False | 0 | 0.0625 |
| SD4-C | Claude | SF-minus-DD recovery > .5 dB | .60 | Claude draft §4 | False | 0 | 0.3600 |
| SD1-S | Sol | H-good, absolute DD-minus-known crossing shift ≤ .25 dB | .25 | This entry | False | 0 | 0.0625 |
| SD2-S | Sol | H-bias, DD remains > .25 dB behind known and improves over SF | .50 | This entry | False | 0 | 0.2500 |
| SD3-S | Sol | H-none, absolute SF-minus-DD shift ≤ .25 dB | .25 | This entry | False | 0 | 0.0625 |
| SD4-S | Sol | SF-minus-DD recovery > .5 dB | .55 | This entry | False | 0 | 0.3025 |

### 2026-11-18 — Phantom-admission law, before per-unit inspection

Semi-blind replay of 8,106 cap-8 triggered M-family units. Aggregate rescue and phantom shares were available. Astra's rule and forecasts were pre-registered at `5190b7ab`. Claude's forecasts were pre-registered at `0d670661`. Protocol freeze `d864c65f`. [Astra's archived rule](../.trellis/tasks/11-18-admission-law-test/research/astra-prediction-rule.md) · [Claude's original DRAFT §5](../.trellis/tasks/11-18-admission-law-test/research/protocol-DRAFT.md#5-预测claude本稿提交时看数据前)

| ID | Author | Forecast | Point [judgment interval] or probability | Outcome |
|---|---|---|---|---|
| AL-a | Astra | A2 three-class accuracy on the admitted subset | .95 [.88, .99] | 99.63% (above range) |
| AL-b | Astra | A2 margin AUC, observed phantom vs. observed missing-true-delay edit | .79 [.60, .92] | AUC .999385 (above range) |
| AL-c | Astra | A2 phantom-first share inside and outside W | Inside .98 [.93, .995], outside .50 [.20, .85] | Inside 100.00% (above range), outside 78.02% (in range) |
| AL-d | Astra | A1c phantom-first share inside W | .02 [.003, .08] | 2.78% (in range) |
| AL-coverage | Astra | Coverage of cap-8 triggered units | 25% [5%, 50%] | 94.58% (above range) |
| AL-C1 | Claude | Coverage ≥ 5% | .80 | 94.58% ≥ 5%. Score 1, Brier 0.0400 |
| AL-C2 | Claude | M1 SUPPORTED | .70 | M1 SUPPORTED. Score 1, Brier 0.0900 |
| AL-C3 | Claude | AUC point estimate ≥ .70 | .55 | AUC .999385 ≥ .70. Score 1, Brier 0.2025 |
| AL-C4 | Claude | M2 SUPPORTED | .65 | M2 SUPPORTED. Score 1, Brier 0.1225 |
| AL-C5 | Claude | Calibration Spearman ≥ .80 | .55 | Pooled Spearman .8688 ≥ .80. Score 1, Brier 0.2025 |
| AL-C6 | Claude | Calibration median relative error ≤ .25 | .50 | Pooled median relative error .06992 ≤ .25. Score 1, Brier 0.2500 |
| AL-C7 | Claude | A2 accuracy gain over the same-subset always-phantom baseline > 0 | .55 | Gain +5.31 pp > 0. Score 1, Brier 0.2025 |

Readout 2026-11-18. Astra had 2/6 forecast intervals containing the points. Claude scored 7/7, with mean Brier 0.1586. Calibration used pooled values for Claude’s two scalar forecasts. Per-arm diagnostics were A2 .9991 Spearman and 0.80% median relative error, A1c −.0452 and 90.03%. [Frozen readout](../experiments/admission_law_20261118/out/RESULTS.md)

### 2026-11-19 — Forced-miss ratio sweep v2, before the main run (scored)

Forecasts committed in [protocol v2 §6.4](../.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md) before the frozen run; audit
forecasts were written in the process log before each audit. Result card [res-20261119-01](res-20261119-01.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| RS2-P1 | Claude | P1 SUPPORTED | .85 | NOT_SUPPORTED. Score 0, Brier 0.7225 |
| RS2-P2s | Claude | P2 SUPPORTED | .50 | REFUTED. Score 0, Brier 0.2500 |
| RS2-P2r | Claude | P2 REFUTED | .20 | REFUTED. Score 1, Brier 0.6400 |
| RS2-P3 | Claude | P3 SUPPORTED | .80 | SUPPORTED. Score 1, Brier 0.0400 |
| RS2-P4 | Claude | P4 SUPPORTED | .40 | REFUTED. Score 0, Brier 0.1600 |
| RS2-A1 | Claude | Audit 1: phantom-side model consistent | .70 | Consistent (median error 0.4–1.0%). Score 1, Brier 0.0900 |
| RS2-A2 | Claude | Audit 1: weak-side measured/model median < .5 | .70 | .27–.45 at R ≤ 12. Score 1, Brier 0.0900 |
| RS2-A3 | Claude | Audit 1: aliasing share > 20% | .15 | 0 units. Score 0, Brier 0.0225 |

### 2026-11-19 — SBL spectral split, before the main run (scored)

Forecasts committed in [protocol §6 and §7.4](../experiments/sbl_spectral_split_20261119/PROTOCOL.md) (`2d4c660b`). Result card
[res-20261119-02](res-20261119-02.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| SS-1 | Claude | R0/R1/R2 reproduce E-3c bit-exactly | .95 | G1 PASS. Score 1, Brier 0.0025 |
| SS-2 | Claude | STAGE = SBL | .55 | SBL. Score 1, Brier 0.2025 |
| SS-3 | Claude | f_lo lower bound ≥ .5 | .55 | 1.016. Score 1, Brier 0.2025 |
| SS-4 | Claude | f_hi lower bound ≥ .5 | .20 | −.080. Score 0, Brier 0.0400 |
| SS-5 | Claude | §7.4 intervention-level support | .25 | Occurred. Score 1, Brier 0.5625 |
| SS-6 | Claude | §7.4 "low-half-only" account fails | .35 | Did not occur. Score 0, Brier 0.1225 |
| SS-7 | Claude | §7.4 not established | .40 | Did not occur. Score 0, Brier 0.1600 |

The unified-covariance prospective test (task `11-19-unified-cov-prospective`) has forecasts committed in its protocol DRAFT §7 and
§9 (`89313c87`, `27a23bd7`). They will be scored here when the result card is written.

### 2026-11-19 — Unified covariance prospective test, before the fresh-frame run (scored)

Forecasts committed in the protocol DRAFT §7 (`89313c87`) and §9 (`27a23bd7`), before any fresh-frame row. The C-hi/C-lo forecasts
predate the old-key leverage replay that later made them near-certain (freeze record). Result card
[res-20261119-03](res-20261119-03.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| UC-1 | Claude | Both crossover premises | .85 | Occurred. Score 1, Brier 0.0225 |
| UC-2 | Claude | V1 low half carries | .70 | Occurred. Score 1, Brier 0.0900 |
| UC-3 | Claude | V1 high half insufficient | .75 | Occurred. Score 1, Brier 0.0625 |
| UC-4 | Claude | V1 shape: projector superior | .45 | Occurred. Score 1, Brier 0.3025 |
| UC-5 | Claude | V1 prospective support | .35 | Occurred. Score 1, Brier 0.4225 |
| UC-6 | Claude | V2 recovers | .60 | Occurred. Score 1, Brier 0.1600 |
| UC-7 | Claude | V3 equivalent / non-inferior | .80 | Occurred. Score 1, Brier 0.0400 |
| UC-8 | Claude | V4 superior | .85 | Occurred. Score 1, Brier 0.0225 |
| UC-9 | Claude | C-hi carries | .70 | Occurred. Score 1, Brier 0.0900 |
| UC-10 | Claude | C-lo insufficient | .65 | Occurred. Score 1, Brier 0.1225 |
| UC-11 | Claude | V5 mirror support | .55 | Occurred. Score 1, Brier 0.2025 |
| UC-12 | Claude | (i) mechanism layer supported | .25 | Occurred. Score 1, Brier 0.5625 |
| UC-13 | Claude | Joint claim supported | .40 | Occurred. Score 1, Brier 0.3600 |
| UC-14 | Claude | Unified claim not supported | .25 | Did not occur. Score 0, Brier 0.0625 |

Calibration note: every forecast event occurred, and most were given under .9, so Claude was under-confident on this test.

### 2026-11-19 — Doublet conflict check, before the fresh-frame run (scored)

Forecasts committed in the DRAFT §5 (`9628a393`). Result card [res-20261119-04](res-20261119-04.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DC-1 | Claude | Compatible | .65 | Did not occur (uncertain). Score 0, Brier 0.4225 |
| DC-2 | Claude | Conflict | .15 | Did not occur. Score 0, Brier 0.0225 |
| DC-3 | Claude | Uncertain | .20 | Occurred. Score 1, Brier 0.6400 |
| DC-4 | Claude | U two-atom rate on 0.35-bin doublets below CD | .55 | Occurred (−4.17 pp). Score 1, Brier 0.2025 |

### 2026-11-19 — SBL residual gap, before the fresh-frame runs (scored)

Forecasts committed in the DRAFT §5 (`c29359e5`) and, for K′, in §8 (`3ae1abcd`). Result card [res-20261119-05](res-20261119-05.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| RG-1 | Claude | Premise holds | .85 | Occurred. Score 1, Brier 0.0225 |
| RG-2 | Claude | K′ recovers at least half | .45 | Did not occur (uncertain, κ .66). Score 0, Brier 0.2025 |
| RG-3 | Claude | H-cap | .40 | Did not occur. Score 0, Brier 0.1600 |
| RG-4 | Claude | M recovers at least half | .20 | Did not occur (uncertain, κ .52). Score 0, Brier 0.0400 |
| RG-5 | Claude | Co-delay share of trimmed part > .8 | .60 | Occurred (known from smoke before the main run). Score 1, Brier 0.1600 |

### 2026-11-19 — ρ sweep, before the fresh-frame run (scored)

Forecasts committed in the DRAFT §7 (`0e83b132`). The §5 V1–V4 forecasts were superseded by §7 before freeze; they are kept as
exploratory records and not scored. Result card [res-20261119-06](res-20261119-06.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| RS-P1 | Claude | P1 supported | .75 | Occurred. Score 1, Brier 0.0625 |
| RS-P2 | Claude | P2 supported | .75 | Occurred. Score 1, Brier 0.0625 |
| RS-P3 | Claude | P3 CD ahead | .80 | Occurred. Score 1, Brier 0.0400 |
| RS-X1 | Claude | Exploratory: CD at ρ = .15 not worse than .30 | .40 | Did not occur. Score 0, Brier 0.1600 |

### 2026-11-19 — Identifiability gate on archived states (scored)

Astra's qualitative forecasts were recorded before the screen. [Forecasts](../.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md) · [Screen](../experiments/gate_screen_20261119/SCREEN.md)

| Forecast | Outcome |
|---|---|
| Most triggered 0.35-bin MIXED8 contrasts would be spared | Occurred. 0/398 were floored, and the frozen rule passed the screen. |
| Initial SBL grid overlap would be below 90% | Occurred for the median block at each signal-to-noise ratio. |
| Full SBL blocks would have about 15 floored modes versus 18 for S-lo | Matched the median at all six signal-to-noise ratios. |

### 2026-11-19 — Gate SBL test, before the fresh-frame run (scored)

Claude's forecasts committed in DRAFT §6 (`a0aafef4`) before review or Phase 1; Astra's in its design review (`16183992`), recorded in §8.10. [Protocol](../experiments/gate_sbl_test_20261119/PROTOCOL.md) · Result card [res-20261119-07](res-20261119-07.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| GS-1 | Claude | S leg pass | .25 | Occurred (pass). Score 1, Brier 0.5625 |
| GS-2 | Claude | S leg fail | .35 | Did not occur. Score 0, Brier 0.1225 |
| GS-3 | Claude | S leg uncertain | .40 | Did not occur. Score 0, Brier 0.1600 |
| GS-4 | Claude | Δ_S point estimate > 0 | .75 | Occurred (+0.458 pp). Score 1, Brier 0.0625 |
| GS-5 | Claude | Gate fires on no X trial in any frame | .75 | Already contradicted before the main run: Phase 1 G5 found 187 firings in 9 of 20 archived MIXED8 frames (`d3e37f5a`). Did not occur (5,265 trial firings in the main run). Score 0, Brier 0.5625; no prospective weight. |
| GS-6 | Claude | X leg pass | .90 | Occurred (0/116). Score 1, Brier 0.0100 |
| GS-7 | Claude | Joint supported | .23 | Occurred. Score 1, Brier 0.5929 |
| GS-8 | Claude | G − R0 lower bound > 0 | .90 | Occurred (+3.92 pp [3.31, 4.52]). Score 1, Brier 0.0100 |
| GS-9 | Claude | Median full-block gate rank 15 on fresh keys | .80 | Occurred (15 at every SNR). Score 1, Brier 0.0400; weak, since the archived screen already showed 15. |
| GS-A1 | Astra | S leg pass / fail / uncertain | .40 / .23 / .37 | Occurred (pass). Three-way Brier 0.5498 |
| GS-A2 | Astra | X leg pass | .93 | Occurred. Score 1, Brier 0.0049 |
| GS-A3 | Astra | Joint supported | .37 | Occurred. Score 1, Brier 0.3969 |

### 2026-11-19 — Edit budget at low pilot fraction, before the fresh-frame run (scored)

Claude: DRAFT §5 (`cf900a99`) and, under the revised §7 rules, §7.8 (`f565269e`); Astra: design review (`f565269e`), stated on the original draft labels. [Protocol](../experiments/edit_budget_lowrho_20261119/PROTOCOL.md) · Result card [res-20261119-08](res-20261119-08.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| EB-1 | Claude | Direction supported (§7.2) | .45 | Occurred. Score 1, Brier 0.3025 |
| EB-2 | Claude | Practical size: g(.15) lower bound ≥ 3 pp | .40 | Occurred (lower bound 3.22). Score 1, Brier 0.3600 |
| EB-3 | Claude | ".30 unchanged": g(.30, matched) within ±3 pp | .45 | Occurred. Score 1, Brier 0.3025 |
| EB-4 | Claude | Astra subgroup ≥ 10% rescued at ρ .15 | .55 | Occurred (32.3% vs 14.9%). Score 1, Brier 0.2025 |
| EB-5 | Claude | agy: CD6 crossing gain ≥ 0.8 dB at ρ .20 | .30 | Did not occur (0.62 dB). Score 0, Brier 0.0900 |
| EB-6 | Claude | agy: CD6 crossing gain ≥ 2.5 dB at ρ .15 | .20 | Did not occur (0.77 dB). Score 0, Brier 0.0400 |
| EB-7 | Claude | agy: CD6 optimal ρ below .25 | .25 | Did not occur (optimum .30). Score 0, Brier 0.0625 |
| EB-8 | Claude | A2-6 gain smaller than CD6 gain | .70 | Did not occur (frozen label missed). Score 0, Brier 0.4900 |
| EB-9 | Claude | CD4 rescue ≥ .90 at ρ .15, 6–8 dB triggered | .45 | Did not occur (88.98%). Score 0, Brier 0.2025 |
| EB-A1 | Astra | On the original draft labels: direction only / upper < 3 pp only / both / neither | .40 / .29 / .06 / .25 | Mapped to the original labels: "direction only" occurred (Astra .40) |

### 2026-11-19 — Grid fineness η, before the fresh-frame run (scored)

Claude: DRAFT §5 (`cf900a99`) and §7.10 (`f565269e`); Astra: design review (`f565269e`), recorded in §7.9. [Protocol](../experiments/grid_eta_dual_20261119/PROTOCOL.md) · Result card [res-20261119-09](res-20261119-09.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| GE-1 | Claude | X directional support (§7.2, incl. A2's own rise) | .55 | Occurred. Score 1, Brier 0.2025 |
| GE-2 | Claude | X quantitative support (interaction LB ≥ 10 pp) | .35 | Did not occur. Score 0, Brier 0.1225 |
| GE-3 | Claude | X quantitative rejection (UB < 10 pp) | .35 | Occurred (upper bound 2.5 pp). Score 1, Brier 0.4225 |
| GE-4 | Claude | S strict monotonic support | .45 | Did not occur. Score 0, Brier 0.2025 |
| GE-5 | Claude | S insensitive to η | .15 | Did not occur. Score 0, Brier 0.0225 |
| GE-6 | Claude | S significant decrease (reverse) | .10 | Occurred (driven by R0 non-convergence at η = 8). Score 1, Brier 0.8100 |
| GE-7 | Claude | S-lo slope smaller than R1's | .55 | Did not occur (slopes −6.08 vs −6.00 pp per η). Score 0, Brier 0.3025 |
| GE-8 | Claude | Joint: X direction and S monotone | .30 | Did not occur. Score 0, Brier 0.0900 |
| GE-A1 | Astra | X directional support | .55 | Occurred. Score 1, Brier 0.2025 |
| GE-A2 | Astra | X 10 pp: support / rejection / inconclusive | .20 / .50 / .30 | Rejection occurred |
| GE-A3 | Astra | S strict monotone / endpoint equivalence / neither | .35 / .05 / .60 | Neither occurred (reversal) |
| GE-A4 | Astra | Joint | .20 | Did not occur. Score 0, Brier 0.0400 |

### 2026-11-20 — Γ = 0 exchange test, before the fresh-frame run (scored)

Claude: DRAFT §5 (`815b3c36`), written for the final-pair endpoint and kept unchanged for the frozen first-edit endpoint (§7.1); Fable: round 1 (`61fdab96`); Astra: design review §7 (`29865c41`), recorded in PROTOCOL §7.7. [Protocol](../experiments/gamma0_exchange_20261120/PROTOCOL.md) · [Freeze record](../.trellis/tasks/11-20-gamma0-exchange/research/freeze-20261120.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| G0-1 | Claude | Z P-A SUPPORTED | .80 | Occurred (1.84% [0.99, 2.80]). Score 1, Brier 0.0400 |
| G0-2 | Claude | Z P-B: EQUIVALENT / CD_BETTER / Z_BETTER / INCONCLUSIVE | .50 / .25 / .10 / .15 | EQUIVALENT occurred (−0.31 pp [−0.74, +0.10]). Multiclass Brier 0.3450 |
| G0-3 | Claude | H P-A SUPPORTED | .75 | Occurred (2.56% [1.56, 3.69]). Score 1, Brier 0.0625 |
| G0-4 | Claude | H rescue ≥ 3 pp below CD (H − CD upper bound < −3 pp) | .55 | Did not occur (H − CD +0.31 pp [−0.26, +0.89]). Score 0, Brier 0.3025 |
| G0-5 | Claude | Both anchors pass (S lower ≥ 80%, CD upper ≤ 5%) | .90 | Occurred (S 86.72%, CD 2.89%). Score 1, Brier 0.0100 |
| G0-F1 | Fable | Z (Γ = 0) phantom rate < 10% | .80 | Occurred. Score 1, Brier 0.0400 |
| G0-F2 | Fable | Z rescue within 3 pp of CD | .50 | Occurred (interval inside ±3 pp). Score 1, Brier 0.2500 |
| G0-A1 | Astra | P-A SUPPORTED, first-edit endpoint: Z / H | .74 / .60 | Both occurred. Brier 0.0676 / 0.1600 |
| G0-A2 | Astra | Z P-B: EQUIVALENT / CD_BETTER / Z_BETTER / INCONCLUSIVE | .32 / .39 / .06 / .23 | EQUIVALENT occurred (Astra .32). Multiclass Brier 0.6710 |

Result card [res-20261120-01](res-20261120-01.md). Gemini's step-2 forecast was not saved before the results commit (`9d649845`); if it arrives, it is recorded as post-results and not scored.

### 2026-11-20 — Γ = 0 on MIXED8 (leg 2), before the fresh-frame run (scored)

Claude: DRAFT §5 (`835d29bb`; its rationale withdrawn in §7.5, numbers unchanged); Fable: round 3 (`80c63809`); Astra: design review, PROTOCOL §7.8 (`f613b625`). [Protocol](../experiments/gamma0_mixed8_20261120/PROTOCOL.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| GM-1 | Claude | P-F: EQUIVALENT / Z_WORSE / Z_BETTER / INCONCLUSIVE | .60 / .15 / .05 / .20 | INCONCLUSIVE occurred (+1.00 pp [−0.33, +2.43]). Multiclass Brier 1.0250 |
| GM-2 | Claude | P-D: EQUIVALENT / Z_HIGHER / Z_LOWER / INCONCLUSIVE | .70 / .15 / .10 / .05 | EQUIVALENT occurred (−1.33 pp [−2.83, +0.16]). Multiclass Brier 0.1250 |
| GM-3 | Claude | Singleton phantoms: Z ≤ CD + 1 | .75 | Occurred (0 vs 0). Score 1, Brier 0.0625 |
| GM-F1 | Fable | Z 0.35-bin two-atom rate within 3 pp of CD | .70 | Occurred (interval inside ±3 pp). Score 1, Brier 0.0900 |
| GM-F2 | Fable | Z − CD FER within ±1.5 pp | .65 | Point estimate +1.00 pp inside, interval not; scored on the point estimate as stated. Score 1, Brier 0.1225 |
| GM-F3 | Fable | H worse than CD by ≥ 1.5 pp | .30 | Did not occur (+1.00 pp). Score 0, Brier 0.0900 |
| GM-F4 | Fable | A2g clearly worse than Z | .85 | Occurred (+48.67 pp). Score 1, Brier 0.0225 |
| GM-A1 | Astra | P-F: EQUIVALENT / Z_WORSE / Z_BETTER / INCONCLUSIVE (anchors passing) | .35 / .09 / .02 / .54 | INCONCLUSIVE occurred (Astra .54). Multiclass Brier 0.3426 |
| GM-A2 | Astra | P-D: EQUIVALENT / Z_HIGHER / Z_LOWER / INCONCLUSIVE (anchors passing) | .47 / .12 / .03 / .38 | EQUIVALENT occurred (Astra .47). Multiclass Brier 0.4406 |

Result card [res-20261120-02](res-20261120-02.md).

### 2026-11-20 — Γ = 0 MIXED8 FER replication (leg 3), before the fresh-frame run (scored)

Claude: DRAFT §5 (`5317b683`). No other model was asked for this leg. [Protocol](../experiments/gamma0_mixed8_rep_20261120/PROTOCOL.md).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| GR-1 | Claude | Q1 = CD_BETTER (Newcombe lower bound > 0) | .50 | Did not occur (NO_DIFFERENCE_SHOWN, [−0.03, +1.13]). Score 0, Brier 0.2500 |
| GR-2 | Claude | Q2 = EQUIVALENT (inside ±1.5 pp) | .55 | Occurred. Score 1, Brier 0.2025 |

Result card [res-20261120-03](res-20261120-03.md).

### 2026-11-20 — Low-pilot support-right failures, zero-simulation readout (scored)

Claude: [RULES.md](../experiments/lowpilot_support_right_20261120/RULES.md) (`17ff4f94`), committed before computing. No other model was asked.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| SR-1 | Claude | R1: PHENOMENON / INCONCLUSIVE / NOISE_EXPLAINS | .70 / .20 / .10 | PHENOMENON occurred (4.4% [3.5, 5.5]). Multiclass Brier 0.140 |
| SR-2 | Claude | R2: SUPPORTS_H_C / INCONCLUSIVE / NO_EVIDENCE | .35 / .45 / .20 | SUPPORTS_H_C occurred (OR 3.07 [1.30, 11.0]). Multiclass Brier 0.665 |
| SR-3 | Claude | R3: DOPPLER_CARRIES / INCONCLUSIVE / NOT | .25 / .45 / .30 | DOPPLER_CARRIES occurred (AUC .816 [.733, .894]). Multiclass Brier 0.855 |

Readout [READOUT.md](../experiments/lowpilot_support_right_20261120/READOUT.md).

### 2026-11-20 — Candidate 1 step 0, first-round pilot acquisition calculation (scored)

Claude: [RULES.md](../experiments/pilot_acquisition_calc_20261120/RULES.md) (`944f49e7`), committed before computing. No other model was asked.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| PA-1 | Claude | R1 crossing location passes | .45 | Did not occur (fail, too hard) |
| PA-2 | Claude | R2 association passes | .55 | Did not occur (RR 1.16 [1.03, 1.32]) |
| PA-3 | Claude | R3 sidelobe-dominated | .25 | Occurred (80%) |

Readout [READOUT.md](../experiments/pilot_acquisition_calc_20261120/READOUT.md).

### 2026-11-20 — External Stein sigma² formula, zero-cost readout (scored)

Claude: [RULES.md](../experiments/stein_sigma2_readout_20261120/RULES.md) (`c2e842d2`), committed before computing.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| ST-1 | Claude | supported / refuted / inconclusive (pooled median) | .10 / .70 / .20 | Supported occurred (0.94); pooled rule defect stated in the readout. Multiclass Brier 1.30 |

Readout [READOUT.md](../experiments/stein_sigma2_readout_20261120/READOUT.md).

### 2026-11-21 — Stein sigma² end-to-end FER (scored)

Claude: [PROTOCOL.md](../experiments/sigma2_stein_20261121/PROTOCOL.md), frozen before the run.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| SE-1 | Claude | P1 ROBUST / DEGRADED / INCONCLUSIVE | .10 / .60 / .30 | INCONCLUSIVE occurred (+0.31 [0.17, 0.48] dB). Multiclass Brier 0.86 |
| SE-2 | Claude | P2 BETTER / NOT_BETTER / INCONCLUSIVE | .45 / .15 / .40 | BETTER occurred (+0.93 [0.65, 1.39] dB). Multiclass Brier 0.49 |

Readout [READOUT.md](../experiments/sigma2_stein_20261121/READOUT.md).

### 2026-11-21 — Data-as-pilot autocorrelation capture, real setting (scored)

Claude: [RULES.md](../experiments/data_autocorr_acq_20261121/RULES.md) (`968c734f`), frozen after Astra's design review and before computing. R3 was written after reading the review.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DA-1 | Claude | R1 PASS / FAIL / INCONCLUSIVE | .30 / .45 / .25 | PASS occurred (.948 [.932, .961]). Multiclass Brier 0.755 |
| DA-2 | Claude | R2 COMPLEMENT / NO / INCONCLUSIVE | .40 / .30 / .30 | COMPLEMENT occurred (.919). Multiclass Brier 0.54 |
| DA-3 | Claude | R3 ATTRIBUTED / NOT / INCONCLUSIVE | .55 / .20 / .25 | ATTRIBUTED occurred (control .042). Multiclass Brier 0.305 |

Readout [READOUT.md](../experiments/data_autocorr_acq_20261121/READOUT.md).

### 2026-11-21 — Data-as-pilot step 2, pilot-estimated anchor and mirror choice (scored)

Claude: [RULES2.md](../experiments/data_autocorr_acq_20261121/RULES2.md) (`5fd45ed6`), committed before computing.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DA-4 | Claude | R4 PASS / INCONCLUSIVE / FAIL | .70 / .20 / .10 | PASS occurred (1.000). Multiclass Brier 0.14 |
| DA-5 | Claude | R5 PASS / INCONCLUSIVE / FAIL | .35 / .35 / .30 | PASS occurred (.832). Multiclass Brier 0.635 |

Readout [READOUT2.md](../experiments/data_autocorr_acq_20261121/READOUT2.md).

### 2026-11-21 — data-pilot-fer stage 0, observable selector pre-check (scored)

Claude: [STAGE0_RULES.md](../experiments/data_pilot_fer_20261121/STAGE0_RULES.md) (`9ff87be1`), committed before computing.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DP-0 | Claude | PASS / INCONCLUSIVE / STOP | .40 / .35 / .25 | PASS occurred (recall .653, precision .192). Multiclass Brier 0.545 |

### 2026-11-21 — data-pilot-fer stage 0b, multi-anchor scoring (scored)

[STAGE0B_RULES.md](../experiments/data_pilot_fer_20261121/STAGE0B_RULES.md) (`d36c58b8`).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DP-0b | Claude | ADOPT | .40 | Did not occur (FALLBACK; recall .32, precision ~.10) |
| DP-0b-x | outside model via Eric | ADOPT | .60 | Did not occur |

### 2026-11-21 — data-pilot-fer stage A, genie true-delay upper bound (scored)

[STAGEA_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA_PROTOCOL.md) (`9f69ebb9`).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DP-A | Claude | CONTINUE / INCONCLUSIVE / STOP | .35 / .30 / .35 | CONTINUE occurred (gain 0.55 [0.39, 0.76] dB). Multiclass Brier 0.635 |
| DP-A-x | outside model via Eric | gain > 0.3 dB | .55 | Occurred |

### 2026-11-21 — data-pilot-fer stage A2, fully true round-0 channel upper bound

[STAGEA2_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA2_PROTOCOL.md), committed before running.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DP-A2 | Claude | CONTINUE / INCONCLUSIVE / STOP | .45 / .25 / .30 | CONTINUE occurred (gain vs delay 0.95 [0.79, 1.07] dB). Multiclass Brier 0.455 |
| DP-A2-rho | Claude | full-arm best rho <= .10 | .45 | Occurred (rho .10). Brier 0.3025 |
| DP-A2-x | outside model via Eric | best crossing <= 4.3 dB (stated for CRB-sized errors, a weaker arm) | .50 | Occurred for the exact arm (3.45 dB); the CRB-error arm is not run. Brier 0.25 |
| DP-A2-x-rho | outside model via Eric | best rho <= .10 | .55 | Occurred. Brier 0.2025 |

Readout [STAGEA2_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md).

### 2026-11-21 — data-pilot-fer stage A3, round-0 Doppler-error tolerance

[STAGEA3_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA3_PROTOCOL.md), committed before running.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DP-A3 | Claude | EASY / MIDDLE / HARD | .35 / .45 / .20 | MIDDLE occurred (R(.1) = 0.59 [0.33, 0.85]; R(.05) = 1.00). Multiclass Brier 0.465 |
| DP-A3-anchor | Claude | sigma .2 arm at rho .10 within 6.36 +- 0.5 dB (delay arm) | .45 | Did not occur (sigma .2 never reaches 1% at rho .10; Gaussian error hurts more than the pilot error of the same mean). Brier 0.2025 |

Readout [STAGEA3_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md).

### 2026-11-21 — data-pilot-fer stage A4, round-0 Doppler bounds

[STAGEA4_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA4_PROTOCOL.md), committed before running.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| DP-A4 | Claude | PILOT-ENOUGH / SB-REACHABLE / ALPHABET-ONLY / CLOSED | .10 / .40 / .45 / .05 | SB-REACHABLE occurred (semiblind .037 at rho .15, 4 dB; pilot .060). Multiclass Brier 0.575 |

Readout [STAGEA4_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md).

### 2026-11-21 — low-pilot tail, read-only checks on stage A rows

[RULES.md](../experiments/tail_check_20261121/RULES.md), committed before reading.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| TC-1 | outside model via Eric | T1 PASS (base FER at rho .10 / 12 dB in [1%, 10%]) | .70 | Occurred (U 1.25%, G 2.0%). Brier 0.09 |
| TC-1c | Claude | T1 PASS | .65 | Occurred. Brier 0.1225 |
| TC-2 | outside model via Eric | T2 PASS (overlap > .80; non-discriminating, shared noise) | .75 | Occurred (13/13). Brier 0.0625 |
| TC-2c | Claude | T2 PASS | .90 | Occurred. Brier 0.01 |

Readout [READOUT.md](../experiments/tail_check_20261121/READOUT.md). Claude's descriptive expectation (delay arm fixes > .7 of tail keys) missed on the pooled value (.29, dominated by rho .05); .97-1.00 at rho .10-.20.


### 2026-11-24 — Huang-2010-style steelman (CD vs global OMP HG vs Γ=0 Z, scored)

Forecasts frozen before main execution in [PROTOCOL.md §6](../experiments/huang_steelman_20261124/PROTOCOL.md) (`4772365c`; Claude's four entries carried unchanged from [DRAFT](../.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md)). 62,400 keys / 18,009 archived F0 triggers on `rho_sweep_20261119` frames `5400–5799`, full 6-$\rho$ grid, `HG` recipe `B0-p2-s0.5`, `HGint` retained; 9.84 core-hours cumulative (within 12.0 core-hour cap).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| HS-C1 | Claude | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .30 / .15 / .30 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9350 |
| HS-C2 | Claude | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .65 / .15 / .05 / .15 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1700 |
| HS-C3 | Claude | Quiet per-trigger median latency: `CD` < `HG` | .75 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0625 |
| HS-C4 | Claude | Optimal $\rho$ (point argmin): `HG` < `CD` | .35 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.4225 |
| HS-G1 | agy (Gemini 4 Neon) | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .25 / .15 / .35 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9400 |
| HS-G2 | agy (Gemini 4 Neon) | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .70 / .15 / .05 / .10 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1250 |
| HS-G3 | agy (Gemini 4 Neon) | Quiet per-trigger median latency: `CD` < `HG` | .80 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0400 |
| HS-G4 | agy (Gemini 4 Neon) | Optimal $\rho$ (point argmin): `HG` < `CD` | .25 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.5625 |

Readout [READOUT.md](../experiments/huang_steelman_20261124/READOUT.md) · [RESULTS.md](../experiments/huang_steelman_20261124/out/RESULTS.md). Both forecasters strongly underestimated global OMP (`HS-C1`/`HS-G1` assigned only .15 to `HG_AHEAD` and .35/.25 to `HG` shifting optimal $\rho$ down) and calibrated well on `Z_EQUIVALENT` and `CD` < `HG` latency. Note also the secondary surprise: coarse integer-grid 2-pass `HGint` beat `CD` by −0.5587 dB [−0.8494, −0.2677] at 1.066× median per-trigger latency (168.34 vs 158.76 ms).


### 2026-11-24 — Same-frame decisive check: HG vs round-0 Doppler headroom & two-pass CD (scored)

Forecasts committed before running `experiments/sameframe_hg_20261124/sameframe.py` ([PROTOCOL.md](../experiments/sameframe_hg_20261124/PROTOCOL.md), freeze `918a2474`). Part 1 evaluates `HG`/`HGint` on `stageA` frames `41000–41399` ($\rho \in \{100,150,200,250\}$) paired against archived `stageA`/`stageA2`/`stageA3` (`s100` primary, 95% paired frame bootstrap, 2000 draws, seed `20261124`). Part 2 evaluates two-pass `CD2` (`max_edits=2`) and `CD2e8` (`max_edits=8`) on `rho_sweep_20261119` frames `5400–5799` (18,009 triggers, 98.33% 36-pair projected CI). Total runtime: 10.87 core-hours (cap 16.0 h).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| SF-C1 | Claude | P1 (`min HG − min s100`): `DOPPLER-LINE` / `INCONCLUSIVE` / `WRITE-A` | .35 / .40 / .25 | `INCONCLUSIVE` occurred (+0.7333 dB, 95% CI [+0.4549, +1.0396]). Multiclass Brier 0.5450 |
| SF-C2 | Claude | P2 (`min CD2 − min HG`): `STILL_BEHIND` / `MIXED` / `CATCHES_UP` | .65 / .25 / .10 | `CATCHES_UP` occurred (−0.1246 dB, 98.33% proj CI [−0.5520, +0.0822]). Multiclass Brier 1.2950 |
| SF-G1 | agy (Gemini 4 Neon) | P1 (`min HG − min s100`): `DOPPLER-LINE` / `INCONCLUSIVE` / `WRITE-A` | .25 / .45 / .30 | `INCONCLUSIVE` occurred (+0.7333 dB, 95% CI [+0.4549, +1.0396]). Multiclass Brier 0.4550 |
| SF-G2 | agy (Gemini 4 Neon) | P2 (`min CD2 − min HG`): `STILL_BEHIND` / `MIXED` / `CATCHES_UP` | .45 / .45 / .10 | `CATCHES_UP` occurred (−0.1246 dB, 98.33% proj CI [−0.5520, +0.0822]). Multiclass Brier 1.2150 |
| SF-G3 | agy (Gemini 4 Neon) | P2 (`min CD2e8 − min HG`): `STILL_BEHIND` / `MIXED` / `CATCHES_UP` | .20 / .45 / .35 | `CATCHES_UP` occurred (−0.1851 dB, 98.33% proj CI [−0.5810, −0.0121]). Multiclass Brier 0.6650 |

Readout [READOUT.md](../experiments/sameframe_hg_20261124/READOUT.md) · [RESULTS.md](../experiments/sameframe_hg_20261124/out/RESULTS.md). Both forecasters strongly underestimated two-pass `CD2` (only .10 on `CATCHES_UP`): matching continuation passes (4 total rounds) closed the entire prior `CD` vs `HG` gap and put `CD2` numerically ahead of `HG` (−0.125 dB, 242 vs 86 paired rescues) and ahead of `HGint` (−0.219 dB [−0.521, −0.012]). On P1, both forecasters calibrated well on `INCONCLUSIVE`.


### 2026-11-25 — Low-pilot round-0 Doppler headroom after CD2 & quiet dual-panel timing (scored)

Forecasts committed before running `experiments/sameframe_cd2_20261125/sameframe_cd2.py` ([PROTOCOL.md](../experiments/sameframe_cd2_20261125/PROTOCOL.md), freeze `e3bf93f6`). Part A ran `CD2` + `CD2e8` on `stageA` frames `41000–41399` ($\rho \in \{100,150,200,250\}$), joint paired frame bootstrap (`2000` draws, seed `20261125`, 95% percentile CI) for `P1' = min CD2 (100..250) − min s100 (100..200)`. Part B ran quiet single-core timing (`CD`, `CD2`, `CD2e8`, `HG`, `HGint`) on CPU 0 (0.0% util) at $(\rho=.20, 4.5\text{ dB})$ and $(\rho=.30, 5.0\text{ dB})$. Total runtime: `3.25` core-hours (cap `6.0 h`).

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| CD2-C1 | Claude | `P1'` (`min CD2 − min s100`): `DOPPLER-LINE` / `INCONCLUSIVE` / `STOP-LINE` (point ~0.6 dB) | .25 / .50 / .25 | `INCONCLUSIVE` occurred (+0.5765 dB, 95% CI [+0.3168, +0.8372]). Multiclass Brier 0.3750 |
| CD2-C2 | Claude | Quiet timing ($\rho=.20, 4.5\text{ dB}$): `CD2` mean per-trigger time < `HG` mean time | .80 | Occurred (`CD2` 189.02 ms < `HG` 639.99 ms; also at $\rho=.30, 5.0\text{ dB}$: 172.80 vs 572.38 ms). Brier 0.0400 |
| CD2-G1 | agy (Gemini 4 Neon) | `P1'` (`min CD2 − min s100`): `DOPPLER-LINE` / `INCONCLUSIVE` / `STOP-LINE` | .20 / .65 / .15 | `INCONCLUSIVE` occurred (+0.5765 dB, 95% CI [+0.3168, +0.8372]). Multiclass Brier 0.1850 |
| CD2-G2 | agy (Gemini 4 Neon) | Quiet timing ($\rho=.20, 4.5\text{ dB}$): `CD2` mean per-trigger time < `HG` mean time | .90 | Occurred (`CD2` 189.02 ms < `HG` 639.99 ms; also faster than `HGint` 199.05 ms). Brier 0.0100 |

Readout [READOUT.md](../experiments/sameframe_cd2_20261125/READOUT.md) · [RESULTS.md](../experiments/sameframe_cd2_20261125/out/RESULTS.md). Both forecasters calibrated well across both `P1'` and timing. Notably, `CD2` strictly beat both `HG` (−0.1569 dB [−0.2976, −0.0137]) and `HGint` (−0.2121 dB [−0.3588, −0.0622]) on the fresh `41000–41399` cohort while running faster than both (`189.0` vs `640.0` / `199.1 ms` at $\rho=.20, 4.5\text{ dB}$).


### 2026-11-25 — data-pilot-fer stage A5, semi-blind round-0 Doppler proxy check (scored)

Forecasts committed before running `experiments/data_pilot_fer_20261121/stageA5.py` ([STAGEA5_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA5_PROTOCOL.md), freeze `75530d4d`). Given true delays $l_i$, evaluates `PW` (pilot-only, data as white noise), `SB` (semi-blind Gaussian ML, exact-gradient joint L-BFGS-B from `PW`), and `KD` (known-data ceiling) on frames `41000–41099` × U/G (200 draws; paired 100-frame cluster bootstrap, `2000` draws, seed `20261125`), $\rho \in \{100,150,200\}$, SNR = `400` (4 dB; G4 selected `[400]` under 6.0 core-h cap; actual `1.97` core-hours). Primary $E = \min_{\rho \in \{.10, .15\}} \overline{M}_{\mathrm{SB}}(4\text{ dB})$: `PASS` if CI upper $\le 0.08$ bin, `FAIL` if CI lower $> 0.08$, else `BORDERLINE`.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| A5-C1 | Claude | Primary verdict: `PASS` / `BORDERLINE` / `FAIL` | .30 / .35 / .35 | `PASS` occurred (`0.0430` bin at $\rho=.15$, 95% CI `[0.0408, 0.0455]`). Multiclass Brier 0.7350 |
| A5-C2 | Claude | 4 dB, $\rho=.10$ `SB` efficiency (`SB mean / SB-CRB`) in `[1.3, 2.5]` | .60 | Occurred (`1.3245` = `0.0527 / 0.0398`). Score 1, Brier 0.1600 |
| A5-G1 | agy (Gemini 4 Neon) | Primary verdict: `PASS` / `BORDERLINE` / `FAIL` | .40 / .30 / .30 | `PASS` occurred (`0.0430` bin at $\rho=.15$, 95% CI `[0.0408, 0.0455]`). Multiclass Brier 0.5400 |
| A5-G2 | agy (Gemini 4 Neon) | 4 dB, $\rho=.10$ `SB` efficiency (`SB mean / SB-CRB`) in `[1.3, 2.5]` | .55 | Occurred (`1.3245` = `0.0527 / 0.0398`). Score 1, Brier 0.2025 |

Readout [STAGEA5_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA5_READOUT.md) · [RESULTS.md](../experiments/data_pilot_fer_20261121/out/stageA5/RESULTS.md). Both forecasters expected a harder finite-sample efficiency penalty at 4 dB and placed only .30/.40 on `PASS`; in fact exact-gradient joint `SB` hit `1.32× / 1.17× / 1.09×` of `SB-CRB` (`0.0527 / 0.0430 / 0.0376` bin), passing well below `0.08` bin at both $\rho = 0.10$ and $0.15$. Both efficiency-band forecasts (`A5-C2`, `A5-G2`) hit (`1.3245 ∈ [1.3, 2.5]`).


### 2026-11-25 — data-pilot-fer stage A6, end-to-end FER ceiling of semi-blind round-0 Doppler (scored)

Forecasts committed before running `experiments/data_pilot_fer_20261121/stageA6.py` ([STAGEA6_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA6_PROTOCOL.md), freeze `c8c2e5fe`). Given true delays $l_i$, evaluates `SBdop` (`stageA5.estimate_sb`) and `PWdop` (`stageA5.estimate_pw`) via `stageA2.f0_true(..., 'ls')` + `A1` on frames `41000–41399` × U/G, $\rho \in \{100, 150\}$, SNR grid `[300, 400, 450, 500]` (6,400 keys; 4-SNR option 1 approved by Eric before freeze under 40.0 core-h cap; actual `26.01` core-hours), paired against frozen `CD2` (`sameframe_cd2_20261125`) and `stageA2`/`stageA3` archives (`2000` joint physical-frame bootstrap draws, seed `20261125`, 95% CI). Primary $D = \min_{\rho \in \{100..250\}} C_{\mathrm{CD2}} - \min_{\rho \in \{100,150\}} C_{\mathrm{SBdop}}$: `GO` if CI lower $\ge 0.5$ dB, `STOP` if CI upper $< 0.3$ dB, else `ERIC`.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| A6-C1 | Claude | Primary verdict: `GO` / `ERIC` / `STOP` | .45 / .45 / .10 | `STOP` occurred (`+0.0386 dB`, 95% CI `[-0.1890, +0.2327]`). Multiclass Brier 1.2150 |
| A6-C2 | Claude | `SBdop` best 1% FER crossing in `[3.50, 3.80] dB` | .55 | Did not occur (`4.3769 dB` at $\rho=.15$, 95% CI `[4.1737, 4.5615]`). Score 0, Brier 0.3025 |
| A6-G1 | agy (Gemini 4 Neon) | Primary verdict: `GO` / `ERIC` / `STOP` | .50 / .42 / .08 | `STOP` occurred (`+0.0386 dB`, 95% CI `[-0.1890, +0.2327]`). Multiclass Brier 1.2728 |
| A6-G2 | agy (Gemini 4 Neon) | `SBdop` best 1% FER crossing in `[3.50, 3.80] dB` | .60 | Did not occur (`4.3769 dB` at $\rho=.15$, 95% CI `[4.1737, 4.5615]`). Score 0, Brier 0.3600 |

Readout [STAGEA6_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA6_READOUT.md) · [RESULTS.md](../experiments/data_pilot_fer_20261121/out/stageA6/RESULTS.md). Major miss by both forecasters (both gave `STOP` only .08–.10 and extrapolated directly from Stage A5's capped mean `0.043` bin $\approx$ `s050`): in the actual receiver, 100% (`38/38`) of high-SNR (`4.5–5.0 dB`) `SBdop` final failures had gross `2–4.4` bin sidelobe-jump outliers inherited from `PW` (masked by A5's `0.375` cap and unrecoverable by local L-BFGS-B or round-1 `time_refine`), leaving `SBdop` `+0.92 dB` worse than `s050` and tied with `PWdop` (`4.3501 dB`) and `CD2` (`4.4156 dB`).


### 2026-11-25 — data-pilot-fer stage A7, decisive diagnosis of round-0 semi-blind Doppler sidelobe lock (scored)

Forecasts committed before running `experiments/data_pilot_fer_20261121/stageA7.py` on the unseen 38 confirmation keys ([STAGEA7_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA7_PROTOCOL.md), freeze `161de2e5`). Dev exploration used strictly `4.0 dB` (`snr == 400`, 69 failures + 24 controls; `snr in {450, 500}` untouched prior to freeze). Evaluates exact `stageA5` Gaussian semi-blind NLL (`f_SB`: truth-basin box vs A6 `SB`), truth-free global semi-blind search `SBGdop` over identical bounds `[-3, 3]^P x [-10, 10]^{2P}` (`f_SBG_rescue`), known-data profile NLL (`f_KD`), and coded valid-LDPC ML (`f_code`) on the 38 Stage A6 `4.5–5.0 dB` `SBdop` final failures (`2000` physical-frame ratio cluster bootstrap draws, seed `20261125`; actual `0.29` core-hours). Claude's prior was fixed in the task brief before dev exploration; agy's forecast was informed by the `4.0 dB` dev readout (`68/69` `SB` prefers truth, `63/69` `SBGdop` rescued) before touching `4.5–5.0 dB`.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| A7-C1 | Claude | Primary diagnosis verdict: `SEARCH` / `MODEL` / `INFO` / `UNCLEAR` | .35 / .35 / .10 / .20 | `SEARCH` occurred (`f_SB = 38/38`, `f_SBG_rescue = 38/38`, 95% CI `[100%, 100%]`). Multiclass Brier 0.5950 |
| A7-G1 | agy (Gemini 4 Neon, dev-informed) | Primary diagnosis verdict: `SEARCH` / `MODEL` / `INFO` / `UNCLEAR` | .80 / .05 / .03 / .12 | `SEARCH` occurred (`38/38` `SB` prefers truth by +25.4..+140.0 nats; `38/38` rescued). Multiclass Brier 0.0578 |
| A7-G2 | agy (Gemini 4 Neon, dev-informed) | Confirmation truth-free rescue share $f_{\mathrm{SBG\text{-}rescue}} \ge 0.75$ ($\ge 29/38$) | .75 | Occurred (`38/38 = 100.00%`). Score 1, Brier 0.0625 |

Readout [STAGEA7_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA7_READOUT.md) · [RESULTS.md](../experiments/data_pilot_fer_20261121/out/stageA7/RESULTS.md). Decisive `38/38` (`100%`) confirmation of `SEARCH`: on every single high-SNR Stage A6 failure, the unmodified Gaussian semi-blind likelihood preferred the truth basin over A6's `PW`-seeded sidelobe by `+25.44` to `+139.98` nats (median `+74.32` nats), and truth-free global search `SBGdop` rescued `38/38` frames to zero bit errors.


### 2026-11-25 — data-pilot-fer stage A8, full-frame 1% FER recovery of global semi-blind round-0 Doppler vs CD2 (scored)

Forecasts committed before running `experiments/data_pilot_fer_20261121/stageA8.py` ([STAGEA8_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA8_PROTOCOL.md), freeze `856e6401`). Directly reuses frozen `stageA7.estimate_sb_global` (true delays $l_i$, zero truth peeking, identical Gaussian semi-blind NLL and domain `[-3, 3]^P x [-10, 10]^{2P}`) on all Stage A6 frames `41000–41399` × U/G, $\rho \in \{100, 150\}$, full 4-SNR grid `[300, 400, 450, 500]` (`6,400` keys; actual `5.90` core-hours, cumulative task total `7.03 / 10.0` core-hours), paired against verified frozen archives (`CD2`, `SBdop`, `PWdop`, `s050`, `s100`, `ldop`; `2000` joint physical-frame bootstrap draws, seed `20261125`). Primary $D = \min_{\rho \in \{100..250\}} C_{\mathrm{CD2}} - \min_{\rho \in \{100,150\}} C_{\mathrm{SBGdop}}$: `GO` (worth continuing) iff 95% CI lower bound $\ge 0.50\text{ dB}$, else `STOP`.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| A8-G1 | agy (Gemini 4 Neon) | Primary verdict `GO` ($\mathrm{LB}_{95}(D) \ge 0.50\text{ dB}$) | .78 | Occurred (`GO`: `+0.9492 dB`, 95% CI `[+0.8063, +1.0254]`). Score 1, Brier 0.0484 |
| A8-G2 | agy (Gemini 4 Neon) | `SBGdop` best 1% FER crossing $\le 3.75\text{ dB}$ | .75 | Occurred (`3.4664 dB` at $\rho=.10$, `0/800` errors at `4.0 dB`). Score 1, Brier 0.0625 |
| A8-G3 | agy (Gemini 4 Neon) | Direct global-vs-local search gain `min SBdop − min SBGdop` 95% CI lower bound $\ge 0.50\text{ dB}$ | .75 | Occurred (`+0.9106 dB`, 95% CI `[+0.7086, +1.0957]`). Score 1, Brier 0.0625 |

Readout [STAGEA8_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA8_READOUT.md) · [RESULTS.md](../experiments/data_pilot_fer_20261121/out/stageA8/RESULTS.md). Full recovery confirmed (`GO`): truth-free global semi-blind search `SBGdop` reached `3.4664 dB` at $\rho = 0.10$ (`0/2,400` errors across `4.0–5.0 dB`; `+306` rescued vs `-8` regressed across all `6,400` keys), beating `CD2` by `+0.9492 dB` `[+0.8063, +1.0254]` (`98.5%` of the `+0.9638 dB` true-Doppler `ldop` ceiling) at `4.67×` lower per-key CPU cost than Stage A6 `SB`. *(Audit note: because `(300, 400, 450, 500)` lacks grid points inside `(3.0, 4.0) dB`, `3.4664 dB` and the `+0.0145 dB` residual rely on `stageA2.crossing`'s `10^{-4}` zero-floor at `4.0 dB`; Stage A8b below tests `[3.50, 3.75] dB` directly.)*


### 2026-11-25 — data-pilot-fer stage A8b, `3.50 / 3.75 dB` densified 1% FER verification vs zero-floor interpolation (scored)

Forecasts committed before running `experiments/data_pilot_fer_20261121/stageA8b.py` ([STAGEA8B_PROTOCOL.md](../experiments/data_pilot_fer_20261121/STAGEA8B_PROTOCOL.md), freeze `7481d3c8`, Sol static review [stageA7_A8_A8b_sol_review.md](../experiments/data_pilot_fer_20261121/out/stageA7_A8_A8b_sol_review.md)). Evaluates frozen `SBGdop` (`stageA7.estimate_sb_global`, zero hyperparameter changes) and archived-definition `ldop` on frames `41000–41399` × U/G at $\rho = 100$, new SNRs `[350, 375]` (`1,600` keys; merged 6-SNR grid `[300, 350, 375, 400, 450, 500]`; actual `1.85` core-hours, cumulative task total `8.90 / 10.0` core-hours), paired against verified frozen `CD2` (`2,000` joint physical-frame bootstrap draws, seed `20261125`). Primary $D_{\mathrm{dens}} = \min_{\rho \in \{100..250\}} C_{\mathrm{CD2}} - \min_{\rho \in \{100,150\}} C_{\mathrm{SBGdop\_dens}}$: `GO` iff 95% CI lower bound $\ge 0.50\text{ dB}$, else `STOP`.

| ID | Author | Forecast | Probability | Outcome |
|---|---|---|---|---|
| A8B-R1 | agy (reviewer, pre-3.5/3.75 dB) | Primary densified verdict `GO` ($\mathrm{LB}_{95}(D_{\mathrm{dens}}) \ge 0.50\text{ dB}$) | .72 | Occurred (`GO`: `+0.7045 dB`, 95% CI `[+0.5615, +0.7977]`; Haldane floor `+0.7023 [+0.5814, +0.7986]`). Score 1, Brier 0.0784 |
| A8B-R2 | agy (reviewer, pre-3.5/3.75 dB) | Densified gap $C_{\mathrm{SBGdop\_dens}}(100) - C_{\mathrm{ldop\_dens}}(100) > 0.05\text{ dB}$ (Stage A8's `+0.0145 dB` underestimated true gap due to `4.0 dB` `10^{-4}` floor) | .70 | Occurred (`+0.1395 dB`, 95% CI `[+0.0603, +0.2072]`; `SBGdop_dens = 3.7111` vs `ldop_dens = 3.5716 dB`). Score 1, Brier 0.0900 |

Readout [STAGEA8B_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA8B_READOUT.md) · [RESULTS.md](../experiments/data_pilot_fer_20261121/out/stageA8b/RESULTS.md). Both audit forecasts hit: measuring `3.50 dB` (`6.25%` `SBGdop` FER vs `2.50%` `ldop` FER) and `3.75 dB` (`1.12%` vs `0.12%`) directly proved that Stage A8's `3.4664 dB` crossing and `+0.0145 dB` (`98.5%`) residual were `10^{-4}` zero-floor underestimates (`3.7111 dB` actual crossing, `+0.1395 dB` true gap to `ldop_dens`, `83.5%` recovery of the `+0.8440 dB` `CD2 − ldop_dens(100)` headroom), while decisively confirming `GO` without zero-floor dependence (`+0.7045 dB`, 95% CI `[+0.5615, +0.7977] >= 0.50 dB`).
