# Journal - guoyikun (Part 1)

> AI development session journal
> Started: 2026-07-26

---



## Session 1: OMP初始支撑与准增益BER：小型并行探索归档

**Date**: 2026-09-07
**Task**: OMP初始支撑与准增益BER：小型并行探索归档
**Branch**: `trans/tcom-main`

### Summary

deinlab三流并行完成144条配对记录；区分初始增益误差、支撑遗漏和最终sigma影响，保存源码、原始证据与结论。

### Main Changes

### Scope and execution

User authorized a small exploratory probe, explicitly on deinlab with parallel processes. No large Trellis task was created; this journal is the Trellis entry for the completed exploration. No training, LDPC, Dtest, paper claim change or unrelated task closure.

- Three concurrent streams, 48 independent exogenous frames at SNR8/12/16; 144 records, 98,304 uncoded bits per SNR/arm. GPU packet completed in 162.17 seconds; all three exit codes zero.
- Initial S0: full OMP output before repair/extension. Current direct40 A0, N1024, P_phys8, rho0.5; generator leakage preserved.
- Compared estimated/accurate gains and OMP/truth-assisted support, with same-capacity and compact-support controls. Three detection stages use one BER endpoint. Terminal oracle keeps A sigma; thermal-noise controls are separately labelled.

### Results and limits

- Initial true-atom recall 69.10%/71.21%/72.23%; lost channel energy 1.3100%/1.0950%/1.0122%.
- At 16dB, initial LS BER 9.0617% -> 0.3265% with exact gains on the same S0 -> 0.0682% with complete true support. Gain error and missed support each matter.
- At 16dB, after 10 normal outer iterations, original S0 BER 1.4038% -> same-40 truth-assisted initial support 0.4679%. Terminal gain-only correction at original final sigma gives 1.2278%, a distinct intervention.
- Six tests, compilation and CUDA smoke passed; nine production observer repeats were H-bit-exact. All input identities, raw hashes and error counts validated. Pointwise paired bootstrap10000 within fixed streams; exploratory, not formal generalization.

### Evidence and reproduction

- [Chinese conclusion](../../../afdm_sp_joint_unrolled/outputs_omp_initial_probe_20260907/结论.md)
- [Protocol](../../../afdm_sp_joint_unrolled/outputs_omp_initial_probe_20260907/protocol.md)
- [Full tables and confidence intervals](../../../afdm_sp_joint_unrolled/outputs_omp_initial_probe_20260907/results.md)
- [Evidence hashes](../../../afdm_sp_joint_unrolled/outputs_omp_initial_probe_20260907/MANIFEST.sha256)
- Raw rows/status/logs: same directory, rep90700/90701/90702. Code, tests, results and logs committed together in eb47764.
- Server execution snapshot: /data/guoyikun/00inbox/AFDM-channel-estimation/outputs_omp_initial_probe_20260907/source. Executed source hashes are in each status.json. This reuses the pre-existing server dependency snapshot; the work commit does not absorb unrelated dirty dependency changes from other work.
- Output directory is generally gitignored; this experiment's selected evidence files were explicitly added. Unrelated work remains untouched. No remote git push requested or performed.


### Git Commits

| Hash | Message |
|------|---------|
| `eb47764` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: DET additional runner provenance checkpoint

**Date**: 2026-09-10
**Task**: DET additional runner provenance checkpoint
**Branch**: `trans/tcom-main`

### Summary

Bound DET-01 additional runner admission/ledger/block identity; recorded Trellis resume gates. 400T and COST-02 formal timing not admitted.

### Main Changes

- Added supplement_detector_extension and rebound additional qualification provenance
- Development records now use real block identities 16/17

### Git Commits

| Hash | Message |
|------|---------|
| `bdaa6b1857ecc14ba3044e62894ead172596896e` | (see git log) |

### Testing

- [OK] 100 local tests and remote Python 3.10 CPU fixtures passed

### Status

[OK] **Completed**

### Next Steps

- Independent review of P2 before 400T admission; COST-02 formal n still blocked on 7/9 dB priors


## Session 3: A-01 harvest ready; S-01 3456F launched beside A-01

**Date**: 2026-09-10
**Task**: A-01 harvest ready; S-01 3456F launched beside A-01
**Branch**: `trans/tcom-main`

### Summary

Continued the comprehensive-supplement CSV from Grok session 01a08989. A-01 remains on GPU; S-01 3456F admitted on the same 4090. G1 blocked. 16T not rerun. Trellis checkpoint supersedes the DET-additional resume for current next-step.

### Main Changes

- Implemented supplement_s01 single-factor units (integer/overlap/P4/P12/rho25/rho75) without changing G0 protocol SHA
- Admitted and launched S-01 tmux g_afdm_supp_s01_scene_v1 PID 285270 beside A-01
- Wrote Trellis checkpoint supplement-progress-20260910-a01-s01.md and updated execution.md

### Git Commits

| Hash | Message |
|------|---------|
| `839a492f1366c5874ddad9a376e1a2a571a47c76` | (see git log) |
| `f8f2c7757efe0db7d1d02a49f564ad7b661fb29d` | (see git log) |
| `4647c33868c11303a2819ed95c4e490f97b875f9` | (see git log) |

### Testing

- [OK] Local unittest S-01+data 17 PASS; remote AFDM CPU fixtures PASS log SHA e6b35d8609f4baa7b16e1755b37c1ee6f6e64bacbbfcb7db57b85bcce52392d5

### Status

[OK] **Completed**

### Next Steps

- Harvest A-01 when a01-mechanism-queue-v1.exit==0
- Harvest S-01 when s01-counterexample-queue-v1.exit==0; keep G1 blocked
- Do not start COST-02 official timing while A-01/S-01 occupy the 4090


## Session 4: I1瓶颈pilot收尾与结果后第一性原理重分析

**Date**: 2026-09-12
**Task**: I1瓶颈pilot收尾与结果后第一性原理重分析
**Branch**: `trans/tcom-main`

### Summary

已完成64独立块两SNR瓶颈仿真、全量原始审计、HTML及Git交付；新证据支持先判别信道/可靠消息缺口，成本作为约束。

### Main Changes

- consumer直接路由与默认回放有证据；完整报告、CSV和Trellis指针同步。
- 更新DERIVATION_PACKAGE.md：精确码字MAP温度不变性、局部Schur精度、共享信道误差及固定支撑诊断；新增事后描述和合成代数核验。

### Git Commits

| Hash | Message |
|------|---------|
| `bd9c9a77` | (see git log) |
| `a56424e9` | (see git log) |
| `1bc5a4e4` | (see git log) |
| `b8a8aee6` | (see git log) |
| `638b9052` | (see git log) |
| `d505e992` | (see git log) |

### Testing

- [OK] 536F/668T，779.09秒；1411NPZ/11020数组审计通过；本地31、远端30、统计4项通过。
- [OK] HTML/Markdown31行表格一致、5链接有效；研究文档9行结果与23个链接核对；新代数核验通过，未新增接收仿真。

### Status

[OK] **Completed**

### Next Steps

- 独立review三个通道均报高负载；CSV仅REVIEW-02等待能力恢复。保留child与父研究active，不归档。
- 下一实验先隔离内部方差/末端LLR，再做固定支撑内信道误差诊断；尚未启动或冻结新预算。


## Session 5: I1轻量诊断与总账交付

**Date**: 2026-09-13
**Task**: I1轻量诊断与总账交付
**Branch**: `trans/tcom-main`

### Summary

完成CPU轻量诊断、新鲜开发、失败保留及自包含中文报告。新算法优势未确认，REFRESH4保留强经典对照；研究任务待用户验收归档。

### Main Changes

- 交付 results.md、逐轮推导及九类条件后续登记；连续估计排除。

### Git Commits

| Hash | Message |
|------|---------|
| `0e974e42` | (see git log) |
| `eada93f2` | (see git log) |
| `4ffbd280` | (see git log) |
| `73e6b6b3` | (see git log) |

### Testing

- [OK] 26阶段9940个状态文件总账通过；224行报告数字从原始记录摘要重新汇总。

### Status

[OK] **Completed**

### Next Steps

- 按本批CSV完成主会话最终自审与handoff；正式确认、COST及GPU项保持后置。

### 最终交接收尾（2026-09-13）

- 最终主会话自审与施工交工单已生成；39个绑定证据哈希一致，实际handoff合同通过。
- 补齐报告/交接证据与精确提交清单；最终Git闭环以本批CSV和提交后核查为准。
- 自审结论为limited_review，独立性weak；按用户要求不启用子代理或独立CLI reviewer。
- Trellis保持in_progress待用户验收归档；科学优势未确认，正式确认、COST及GPU项仍按条件后置。

- 收尾审计修正：共享父任务新增其他子任务引发首次Git闭环检查失败，失败证据保留。本批只核父子登记和既有字段，允许有效追加兄弟任务；7项回归与真实父子链接核验通过，其他任务的改动原样保留。


## Session 6: A/B阶段零候选裁决与交接

**Date**: 2026-09-14
**Task**: A/B阶段零候选裁决与交接
**Branch**: `trans/tcom-main`

### Summary

完成获授权的N256未编码A/B阶段，0合格候选；STAGE-REVIEW主会话自审weak。七个后置行及总研究仍开放，Trellis保持in_progress。

### Main Changes

- 固定带限表示完成分层资格与3328F完整开发；强普通小支撑参考仍占优，B历史代理诊断不确定。
- EDGE按条件N/A，B03/B04按前置STOP，0校准/新留出/新编码；新增阶段交接及需求覆盖5/12、阶段适用7/7。
- 只核验远端源码、元数据及进程；未重跑旧实验、修改旧raw或扩大科学范围。

### Git Commits

| Hash | Message |
|------|---------|
| `5d157fe4` | (see git log) |
| `4112ff69` | (see git log) |
| `d488126a` | (see git log) |
| `6cc9a29c` | (see git log) |
| `f690b009` | (see git log) |
| `fbbfdb7f` | (see git log) |
| `181be4a4` | (see git log) |
| `1468bee1` | (see git log) |
| `b88bf601` | (see git log) |
| `cf3e12fa` | (see git log) |

### Testing

- [OK] 复用已通过的分批raw审计、A03工程回放、B02拟合与A04统计核验；本次远端2475文件哈希及6270保存记录数量对账通过。
- [OK] 本次本地8来源、36映射、16历史行、111引用、34链接及阶段合同通过；handoff结构和claim ledger机器检查通过。

### Status

[OK] **Completed**

### Next Steps

- G1/COST/CONF/SCENE/CODE/PAPER/REVIEW保持开放；需要新的合格候选及科学范围/预算决定，不自动扩展C或归档父研究。


## Session 7: CE与导频开发阶段闭环：43/50

**Date**: 2026-09-15
**Task**: CE与导频开发阶段闭环：43/50
**Branch**: `trans/tcom-main`

### Summary

当前用户确认后完成O3剩余60F与导频240CE。O3合计64F审计通过；导频四冻结对比无晋级，PILOT03条件排除0F。只读纠正辅助gamma缺/K并补O2/旧FULL机制，7定向测试及阶段审查通过。CSV43已闭环/7原后置未开始，任务保持in_progress。

### Git Commits

| Hash | Message |
|------|---------|
| `638dd511` | (see git log) |
| `c2c8599f` | (see git log) |
| `60c52944` | (see git log) |

### Status

[OK] **Completed**

### Next Steps

- 原G1/COST/CONF/SCENE/CODE/PAPER/REVIEW01仍需合格候选及对应科学和预算门，不自动启动。


## Session 8: Frozen SP-AFDM small-scale delivery

**Date**: 2026-09-21
**Task**: Frozen SP-AFDM small-scale delivery
**Branch**: `trans/tcom-main`

### Summary

Recovered wrong-project task; verified migration, corrected evidence contracts, completed 59-arm single-observation screen and ten memory probes. User chose small-scale delivery; full development remains unstarted.

### Git Commits

| Hash | Message |
|------|---------|
| `70dd0077` | (see git log) |
| `31d5ec0d` | (see git log) |
| `d9254cc6` | (see git log) |

### Status

[OK] **Completed**

### Next Steps

- Await explicit continuation of full development; report at results/sp_afdm_frozen/RESULTS.md. Research parent remains open.


## Session 9: Minimal staged SP-AFDM development completed

**Date**: 2026-09-21
**Task**: Minimal staged SP-AFDM development completed
**Branch**: `trans/tcom-main`

### Summary

Completed 260+256 calls on 20+64 fresh observations; stop/defer after failed prospective continuation heuristic. RESULTS answers six requested questions. No full grid or confirmation.

### Main Changes

- Retained I1_BP8_r1, P_M24_I20, EP2/r2 and PBiGaBP8/r2; saved compact evidence plus fixed heavy audit subset.

### Git Commits

| Hash | Message |
|------|---------|
| `2f69125c` | (see git log) |

### Testing

- [OK] 9 focused synthetic tests; 516 decision recounts; 34 heavy arm-cell NMSE/hash audits; 610 returned files hash matched; four numerical processes exit 0.

### Status

[OK] **Completed**

### Next Steps

- Await user acceptance. Do not start more experiments, retune, run full grid or confirmation.


## Session 10: Stage B stopped at numerical equivalence gate

**Date**: 2026-09-28
**Task**: Stage B stopped at numerical equivalence gate
**Branch**: `trans/tcom-main`

### Summary

F1 profile completed; 409 full-wrapper attempts stopped at f197 exact counter mismatch (408 ok). One fixed four-acquisition trace did not reproduce it. F2 primary algebra and 9 synthetic tests complete, no F2 receiver admitted. F1/CSTATE UNRESOLVED, disposition D; no new observations, no truth analysis, no restart. Evidence, independent metadata recount, 70 local links and 7 reviewer routes archived. Parent research task remains open.

### Git Commits

| Hash | Message |
|------|---------|
| `a8aaa5de` | (see git log) |
| `ac0ced8d` | (see git log) |
| `d203207a` | (see git log) |
| `0b12c8b1` | (see git log) |

### Status

[OK] **Completed**


## Session 11: 结构化推断四路线研究闭环

**Date**: 2026-10-03
**Task**: 结构化推断四路线研究闭环
**Branch**: `trans/tcom-main`

### Summary

完成最新Mission CSV共19项；四路线数学/学习判别、默认关闭原型与真实N1024迁移均已执行。49合同测试和独立14项审查通过；29次真实接收调用复算。候选在3簇6观测中6/6错帧、原joint0/6，依预登记门不运行同预算确认；634证据文件保留。只归档当前执行任务，未晋级生产或论文主张。

### Git Commits

| Hash | Message |
|------|---------|
| `83e7454e` | (see git log) |
| `979c4487` | (see git log) |
| `80c8ee8b` | (see git log) |
| `36e3f4a3` | (see git log) |
| `11a4ca6c` | (see git log) |
| `e9fccde0` | (see git log) |
| `e8be5baf` | (see git log) |

### Status

[OK] **Completed**


## Session 12: 共享信道后续研究执行与独立交接

**Date**: 2026-10-04
**Task**: 共享信道后续研究执行与独立交接
**Branch**: `trans/tcom-main`

### Summary

完成恢复会话的九项目标：实际 PDP/G0 先验核验、96 行概率比较、碰撞与完整有限消息、六旧观测36次接收诊断。独立逐项审查通过，57项测试通过，交工单合同通过；保留科学边界及来源偏差，父研究任务不关闭。

### Main Changes

- 本轮CSV和研究报告为执行/证据入口；实际生产先验不同于受控球面，未晋级论文主张。

### Git Commits

| Hash | Message |
|------|---------|
| `b9eeb3a9` | (see git log) |
| `406621a7` | (see git log) |

### Testing

- [OK] 57 tests; 1997 artifact and 1639 source snapshot hashes; independent raw recomputation and handoff contract passed.

### Status

[OK] **Completed**

### Next Steps

- 按本轮CSV与交工单检索已交付工作；归档须用户接受交接，研究方向与生产确认另行决策。


## Session 13: Higher-order AFDM exploration: independent review and closure

**Date**: 2026-10-05
**Task**: Higher-order AFDM exploration: independent review and closure
**Branch**: `trans/tcom-main`

### Summary

Completed all 15 CSV rows and 10 research outcomes; independent strong review, 49 tests and saved-data/hash replay passed. Controlled fourth-order information is positive; actual-prior zero-information platform and divergent-moment counterexamples retained. Estimation and LLR candidates show no stable advantage. 36,876 development observations, zero new production receiver/decoder calls. Child archived, parent and paper promotion remain open.

### Main Changes

- Canonical report: results/afdm_higher_order_information/RESEARCH_REPORT.md; final CSV and handoff: .mission/20261004_21-37-05-afdm-higher-order-information/.

### Git Commits

| Hash | Message |
|------|---------|
| `7f2d7b61` | (see git log) |

### Testing

- [OK] 49 tests; independent raw replay; 169 baseline, 1409 snapshot, 3712 success-artifact and 482 failed-artifact hashes; claim ledger and handoff contract pass.

### Status

[OK] **Completed**

### Next Steps

- No remaining work in this CSV. Parent research acceptance, broader novelty and any production promotion are separate decisions.


## Session 14: 实际先验与有效信息：完整探索及独立交工

**Date**: 2026-10-05
**Task**: 实际先验与有效信息：完整探索及独立交工
**Branch**: `trans/tcom-main`

### Summary

Mission 18/18闭环，12目标独立复审通过；两项原计划缺口以零观测reader补齐。12stage、82176新开发观测、7440预约秒，92测试及11子测试通过，原33278及补充126429复算检查均零失败。保留P2条件范围、统计未定和无稳定算法优势；父研究与论文主张不升级。报告与交工入口已写入STATE，仅提交本轮新增段落。

### Git Commits

| Hash | Message |
|------|---------|
| `c073fc07` | (see git log) |
| `ba9a1945` | (see git log) |
| `d03c3ba9` | (see git log) |

### Status

[OK] **Completed**


## Session 15: Collision density and effective-information exploration closed

**Date**: 2026-10-05
**Task**: Collision density and effective-information exploration closed
**Branch**: `trans/tcom-main`

### Summary

完成实际G0/P2/N4碰撞密度与单侧局部实验、未知参数有效信息正性证明；8192观测、112距离/336传播，独立10239项复算零失败，10行CSV与9目标独立验收闭环。仅归档本子任务并恢复开放父研究。

### Main Changes

- Added collision theory, observation-only teacher, fixed moment study, bounded-distance reader and independent raw audit.

### Git Commits

| Hash | Message |
|------|---------|
| `f37be16e` | (see git log) |
| `d1403212` | (see git log) |
| `7ca10862` | (see git log) |
| `133281eb` | (see git log) |
| `44d0f50f` | (see git log) |
| `da2dafd1` | (see git log) |
| `52aa4fcd` | (see git log) |
| `0e2fe170` | (see git log) |

### Testing

- [OK] 27 targeted fixture tests plus 12 audit tests in a separate process passed; 10239 registered audit comparisons passed; all 8669 protected old-file hashes unchanged.

### Status

[OK] **Completed**

### Next Steps

- Future separately planned work: unknown-nuisance local estimator/test and finite-separation validity; no automatic production or confirmation expansion.


## Session 16: 碰撞信息到未知参数方法与优势

**Date**: 2026-10-05
**Task**: 碰撞信息到未知参数方法与优势
**Branch**: `trans/tcom-main`

### Summary

已实现观测式未知参数方法；限定点同14矩J检出优势成立，独立补充性能与成本有潜力但一次GMM失败使完整优势未通过。原始审计一致，父研究保持开放，最终交工和逐项状态见本轮Mission CSV。

### Main Changes

- 完成14维矩检验、完整观测参考、分支和失败诊断；1837056新开发观测，5460预约秒，0receiver/decoder/新生产确认流。

### Git Commits

| Hash | Message |
|------|---------|
| `66422eb5` | (see git log) |
| `4573ce71` | (see git log) |
| `9d77e2ea` | (see git log) |
| `e552bba1` | (see git log) |
| `c84a2db2` | (see git log) |

### Testing

- [OK] 主52、补充52、审计14项既有定向测试收据保留（集合有重叠）；登记raw审计1283414项零不一致，8862旧文件不变。

### Status

[OK] **Completed**

### Next Steps

- 用户验收本轮限定结论后再决定是否归档子任务；父研究和论文主张保持开放。


## Session 17: C1 mechanism closure and round-1 loop law

**Date**: 2026-10-09
**Task**: C1 mechanism closure and round-1 loop law
**Branch**: `trans/tcom-main`

### Summary

Codex route implemented: T2 scalar closure failed (dropped); code threshold universal in MI (I*=.577); frozen EXIT staircase predicts cliffs 6/6; round-1 loop law I_1(K) derived with coherent self-absorption (bracket 56/56; kappa=w post hoc); V1-V5 spec and frozen V3 predictions; HTML brief published; draft card res-20261009-01.

### Main Changes

- research/c1-round1-loop-theory.md: derivation + verification spec (canonical)
- c1r1_model.py + out/c1r1: retrodiction and frozen V3 fresh-cell predictions
- research/c1-overview.html: reader brief (https://claude.ai/artifact/DRksCUG1sNMpKVBWi61prv, private)
- Draft card res-20261009-01; STATE.md section; task RESULTS.md section

### Git Commits

| Hash | Message |
|------|---------|
| `d79a578d` | (see git log) |
| `1dfb182c` | (see git log) |
| `ac08735a` | (see git log) |
| `bdad1a06` | (see git log) |
| `9473a774` | (see git log) |
| `6b3ebda9` | (see git log) |
| `2d0a2f90` | (see git log) |
| `bf35001e` | (see git log) |

### Testing

- [OK] Retro: eps_det1 bracket 56/56; I_1 max error .036 on 12 points (post hoc); Kc_R1 |ln| .03-.21 in 7 groups

### Status

[OK] **Completed**

### Next Steps

- User decision: run V1 (zero new frames), V2 (loop-gain probe), V3 (blind fresh cells)
- User decision: accept or revise draft card res-20261009-01; Codex audit before promotion


## Session 18: C1 fold, round-1 law tests, joint-FP theory, inner-budget lever

**Date**: 2026-10-10
**Task**: C1 fold, round-1 law tests, joint-FP theory, inner-budget lever
**Branch**: `trans/tcom-main`

### Summary

Task 10-08-doppler-cluster (research parent stays open).
- A4/A5: mean return map bistable from K~224; long-run (10-round) cliff Kc~180 set by per-frame heterogeneity; closed own map never decodes (0/459); start dependence under genie starts.
- Round-1 law: V3 blind 20 cells I_1 within .042 (P3c on the bar); V1 link clause failed; V2 rejected the self-absorption mechanism; kappa = effective constant (~.7w).
- Reviewed both Codex derivations (correct, reproducible); accepted his corrections (FP identity conditional, probe != joint detector, A_B needs extra assumption; scope narrowed: 10-round cliff, start dependence).
- Joint-FP theory round 1 (J run) and round 2 (R2): noise absorption vs channel-error image explain the size of kappa_eff; J12 puts the excess in own-symbol error structure; scalar closures fail; kappa-mechanism derivation stopped.
- Inner budget (IB, IB2): 40 vs 20 inner updates move cliffs x1.08-1.40 in 6 conditions, saturate at 30-40; 10-round cliff 180->214; R10/T20 dominated by R4/T30 at ~55% compute. Draft card res-20261010-01.
- Direction review (ccf-idea rubric) plus correction: inner-budget result is configuration, not a Trans-level contribution on its own; Trans-level needs a generalising predictive method, an analysis-derived scheduling mechanism with realistic acquisition, or an AFDM-specific waveform finding. Next decision with the user: portfolio-level choice of the paper centre.

### Git Commits

| Hash | Message |
|------|---------|
| `fdb2b382` | (see git log) |
| `4d517d17` | (see git log) |
| `5d9d24a6` | (see git log) |
| `882e676f` | (see git log) |
| `d7d2d0a7` | (see git log) |
| `6966ca78` | (see git log) |
| `12a6338c` | (see git log) |
| `f006b0ad` | (see git log) |
| `8d26126c` | (see git log) |
| `3fe96318` | (see git log) |
| `cae5f3d2` | (see git log) |
| `773b2139` | (see git log) |
| `f7425f7e` | (see git log) |
| `272a0304` | (see git log) |
| `4c933d10` | (see git log) |
| `4f3563fa` | (see git log) |
| `c242c36f` | (see git log) |
| `3a45be5e` | (see git log) |
| `9c3f8a45` | (see git log) |
| `52df712c` | (see git log) |
| `7e49125d` | (see git log) |
| `d1698c72` | (see git log) |
| `dfa18ce8` | (see git log) |
| `4569b034` | (see git log) |
| `c2658539` | (see git log) |
| `e94d0464` | (see git log) |
| `dd4cfa22` | (see git log) |
| `1bc119df` | (see git log) |

### Status

[OK] **Completed**


## Session 19: Bounds screens and F0+CSTATE TCOM reference frame

**Date**: 2026-10-16
**Task**: Bounds screens and F0+CSTATE TCOM reference frame
**Branch**: `trans/tcom-main`

### Summary

Upper-bound screen (res-20261015-01, UNINFORMATIVE; bracket with LB too wide). Mainline switched to F0+CSTATE. Child task 10-15-tcom-reference-frame: generator fixes (D1/D2/A1), P1 fresh confirmation (H1 INCONCLUSIVE by one point, H3 PASS, near genie at rho .5), P2b embedded pilots (infeasible in main channel; SP better at rho .3), P2a Zheng 2025 (printed constants do not reproduce; port incl. Z-OMP never reaches 1e-2 by 8 dB, H5 PASS). Three cards accepted; res-20261015-02 supersedes SCOPED items 11-12. Task archived; BCRB follow-up started in its own session.

### Git Commits

| Hash | Message |
|------|---------|
| `2ba31064` | (see git log) |
| `7895315a` | (see git log) |
| `4f0ebe56` | (see git log) |
| `f5e1cafe` | (see git log) |
| `8c9e96da` | (see git log) |
| `edd06d27` | (see git log) |
| `f36047d8` | (see git log) |
| `afa4c039` | (see git log) |
| `2cd61b7c` | (see git log) |
| `1f28139e` | (see git log) |
| `5313e43f` | (see git log) |
| `06935d42` | (see git log) |
| `d727b09e` | (see git log) |
| `6c1f0815` | (see git log) |
| `1234b71f` | (see git log) |
| `6bb5fa3b` | (see git log) |
| `6c20abf0` | (see git log) |
| `f2e35c46` | (see git log) |
| `43baf559` | (see git log) |
| `7b908e8a` | (see git log) |
| `0cfbd43b` | (see git log) |
| `09eedc33` | (see git log) |
| `6ff70752` | (see git log) |

### Status

[OK] **Completed**


## Session 20: E3c completed: ridge recovery and gain-refit control

**Date**: 2026-10-18
**Task**: E3c completed: ridge recovery and gain-refit control
**Branch**: `trans/tcom-main`

### Summary

E3c-first milestone completed; full research task remains in progress.

### Main Changes

- 1200 paired keys completed; six-arm result card remains draft.
- Fixed-geometry gain control corrects E3b causal interpretation; broad audit deferred.

### Git Commits

| Hash | Message |
|------|---------|
| `e1bfd013` | (see git log) |

### Testing

- [OK] Qualification gates passed; independent result check verified 318227 numeric leaves and all 1200 keys.
- [OK] Frozen source unchanged; summary SHA256 matched; total charged budget 9.507352 core-hours.

### Status

[OK] **Completed**

### Next Steps

- Await user interpretation/acceptance; old-campaign audit and fresh predictions remain deferred.


## Session 21: Audits, P correction and slot-mismatch pilots

**Date**: 2026-10-19
**Task**: Audits, P correction and slot-mismatch pilots
**Branch**: `trans/tcom-main`

### Summary

Generator/SNR audit and saved-row recount clean; P-known correction; slot and edit-budget pilots show the full/scalar gap does not depend on spare slots or edits. Full ledger: .trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md

### Main Changes

- Gemini Deep Research reviewed: no new direction; cheap items and citation fixes recorded
- Rank-inversion check (Gemini report 2): PARTIAL, rho factor has the wrong sign (exploratory)
- res-20261016-01 explicit correction: receivers cap paths at max_paths=8 = true P
- Independent recount of E-1/E-2/E-3/E-3b reproduces 212 frozen scalars; Codex generator/SNR audit: no BLOCKER/MAJOR
- Slot-mismatch pilots 1-3 and zero-sim checks: gap ratio .90 (spare slots), 1.00 (doubled edits); raising the edit budget is not a weak-path route

### Git Commits

| Hash | Message |
|------|---------|
| `56e3874f` | (see git log) |
| `5f268d65` | (see git log) |
| `5adff9c7` | (see git log) |
| `0c2e09c9` | (see git log) |
| `3f5d2b83` | (see git log) |
| `1975541a` | (see git log) |

### Testing

- [OK] Gates: variant receive 40/40, E-2 reproduction 58/58, edit-kernel variant 48/48 bit-exact; independent recounts match

### Status

[OK] **Completed**

### Next Steps

- Detector gain re-estimation hypothesis (possible unification of the SBL reversal): zero-sim check first, after an independent model's direction review
- Slot-mismatch confirmation on frames 10000-10999 after protocol fixes
- Paired Luo-style SBL baseline with timing; pending acceptances listed in the ledger


## Session 22: Detector-gain lead: zero-sim check, CSTATE and SBL pilots

**Date**: 2026-10-19
**Task**: Detector-gain lead: zero-sim check, CSTATE and SBL pilots
**Branch**: `trans/tcom-main`

### Summary

Pilots 4-5 and a zero-sim check support the detector-interface lead: near-duplicate co-delay atoms hurt when the detector re-estimates gains jointly; in SBL the scalar/full ordering flips with the detector interface. Records consolidated; staged-look tip added to the rules repo (722c0f0).

### Main Changes

- Zero-sim on 10-18 K rows: fixed-gain benefit only in units with near-collinear co-delay pairs (+.068 vs -.010), P7 held
- Pilot 4 (CSTATE side): fixed gains rescue .184 and merging .127 of scalar-Gamma phantom failures; ~80% unrescued
- Pilot 5 (SBL side): fixed detector scalar .024 vs full .088; joint detector scalar .101 vs full .018; interaction +.148
- Findings placement: open leads in STATE, killed leads in the negative-results ledger, predictions in the prediction ledger; audit card res-20261019-01 (draft); AGENTS.md points Codex to the record table

### Git Commits

| Hash | Message |
|------|---------|
| `14db22de` | (see git log) |
| `01521088` | (see git log) |
| `9c244fb9` | (see git log) |
| `d8dd854a` | (see git log) |
| `1090a270` | (see git log) |

### Testing

- [OK] Gates bit-exact against saved 10-18 and E-3 rows; independent recounts match

### Status

[OK] **Completed**

### Next Steps

- Prospective confirmation of the detector-interface unification on fresh frames (rho .5, more SNRs, E-3b off-grid), after an independent model's direction review
- Then decide whether the paper main line adopts the unified Claim B


## Session 23: Bounded SBL detector diagnostic: mean-only harm, joint mitigation

**Date**: 2026-10-20
**Task**: Bounded SBL detector diagnostic: mean-only harm, joint mitigation
**Branch**: `trans/tcom-main`

### Summary

Delivered the user-requested first small result and stopped: 200 paired keys/50 old frame clusters, scalar FER fixed .020, point .200, joint .115. Mean-only mode harms decoding despite improved average channel NMSE; joint mode mitigates point harm. No mechanism claim promotion or expansion.

### Main Changes

- Added frozen-pipeline three-mode driver, trajectory observer, strict replay and frame-cluster analysis; preserved original aggregation failure and analysis-only repair.

### Git Commits

| Hash | Message |
|------|---------|
| `d3e4a468` | (see git log) |
| `f7d5d4a8` | (see git log) |
| `2b856d2a` | (see git log) |

### Testing

- [OK] Real gate, all 200 old-result replays, six-arm independent raw counts and 12 raw hashes verified; 3 aggregation regression tests pass; local independent code and evidence review.

### Status

[OK] **Completed**

### Next Steps

- User evaluates the small exploratory result before deciding any further study; parent remains open.


## Session 24: Bounded SBL final-gain restart readout

**Date**: 2026-10-20
**Task**: Bounded SBL final-gain restart readout
**Branch**: `trans/tcom-main`

### Summary

Approved RF/P40 replay finished on 200 old paired keys; RF 20 failures, P40 41 versus point20 40 and fixed20 4. Reset/freeze remains combined; awaiting user assessment.

### Main Changes

- Recorded the source-gate collision and minimal alias fix; preserved failed run1 and successful run2 receipts.
- Scored P17-P19, linked the exploratory readout in STATE, retained scientific acceptance and task archive as pending.
- User delegation preference persisted in canonical personal-ai-workflow source and installed across three clients; no new sub-agent was spawned.

### Git Commits

| Hash | Message |
|------|---------|
| `feffc7ed` | (see git log) |
| `50d79546` | (see git log) |
| `0ca77870` | (see git log) |

### Testing

- [OK] Two aggregation tests, compilation and shell syntax; real receiver/source/prefix gates; direct 200-key raw recount and source/hash bindings.

### Status

[OK] **Completed**

### Next Steps

- User assesses this bounded result; no automatic extra arm, sample extension, claim promotion or archive.


## Session 25: Matched SBL restart-point addendum

**Date**: 2026-10-20
**Task**: Matched SBL restart-point addendum
**Branch**: `trans/tcom-main`

### Summary

User-approved RP single arm completed on all 200 old keys: RP31 failures versus RF20 and continuous P4041; both directional paired cluster criteria pass. Conditional operational effects only.

### Main Changes

- Added only new entry/aggregate/tests/launcher; reused saved h20/prior with no SBL rerun and preserved original results.
- Reused one existing latest-Sol agent, qualified real RF replay and first-update equality, scored P20/P21 and linked bounded readout in STATE.

### Git Commits

| Hash | Message |
|------|---------|
| `99f918be` | (see git log) |
| `1081e27a` | (see git log) |

### Testing

- [OK] Seven aggregate tests and syntax checks; full source/input/hash gates; independent raw recount. EXIT0, 14.50s wall, about .0284 core-hours.

### Status

[OK] **Completed**

### Next Steps

- User assesses the result; no automatic additional arm, scientific claim promotion or archive.


## Session 26: Zero-simulation SBL trajectory analysis

**Date**: 2026-10-21
**Task**: Zero-simulation SBL trajectory analysis
**Branch**: `trans/tcom-main`

### Summary

All200 old keys/six arms analyzed with no receiver calls. Scalar point-fixed full20 E increases and V decreases; positive gap interaction, but mismatch shared by full Gamma and not a unique causal explanation.

### Main Changes

- Delivered four-panel PNG/editableSVG, paired time-average/endpoint statistics and complete provenance; preserved original raw and scripts.
- Used pre-update h alignment and common internal symbol units, scored informed T1/T2 checks, and reported generic mismatch plus cell/time-average limitations.

### Git Commits

| Hash | Message |
|------|---------|
| `ef324633` | (see git log) |
| `ef8f09fe` | (see git log) |

### Testing

- [OK] Thirteen combined tests, compile, actual raw/config/helper/endpoint qualification, independent raw-average recomputation, source/derived hashes and visual inspection. EXIT0, one CPUthread, 4.16s wall.

### Status

[OK] **Completed**

### Next Steps

- User assesses this bounded diagnostic; no automatic causal intervention, new frames, claim promotion or archive.


## Session 27: Matched physical-prior duplicate representation probe

**Date**: 2026-10-21
**Task**: Matched physical-prior duplicate representation probe
**Branch**: `trans/tcom-main`

### Summary

Exact H0 and working Gaussian prior preserved under uniform2x duplication; fixed/first-symbol invariant, first point aggregate update differs by a verified closed form in one synthetic and one predetermined old real case.

### Main Changes

- Recorded independently reviewed derivation, frozen native two-case probe and source/input receipts; no SBL rerun or old source modification.
- Located sensitivity at first point gain update, with exact Gaussian posterior controls invariant. Real final LLR max difference9.53; no population FER or actual Gamma-reversal attribution.

### Git Commits

| Hash | Message |
|------|---------|
| `c4635b24` | (see git log) |
| `e7b55f97` | (see git log) |

### Testing

- [OK] Seventeen tests, compilation, native physical/prior/fixed/first-symbol gates, baseline/h20 replay, formula residual<1.2e-16, independent recorded posterior/formula/hash verification. OneCPU, EXIT0,4.73s.

### Status

[OK] **Completed**

### Next Steps

- User assesses bounded structural result; no automatic near-duplicate sweep, new cohort, receiver modification, claim promotion or archive.


## Session 28: Matched soft-Gram block derivation and minimal qualification

**Date**: 2026-10-21
**Task**: Matched soft-Gram block derivation and minimal qualification
**Branch**: `trans/tcom-main`

### Summary

Full local gain block preserves uniform-duplicate physical/state/LLR invariance; diagonal does not. Same two predetermined cases only; no population claim.

### Main Changes

- Derived matched full/diagonal expected-log Gaussian gain solves with alpha=noise*P and the same pre-symbol snapshot; preserved all original sources/results.
- Completed missing all-step LLR observation using a return-preserving wrapper on the same cases. Numerical outputs match gate1 exactly; real errors full0/diag351/native42, old fixed0.

### Git Commits

| Hash | Message |
|------|---------|
| `5d2feb6e` | (see git log) |
| `62f70a16` | (see git log) |
| `86e20c09` | (see git log) |

### Testing

- [OK] Twenty-two NumPy tests, four-module compilation, native bit-exact clone and saved h20/score replay, dense mixed-delay Gamma, full20 state/covariance/LLR aggregation, independent saved-system/source/SHA verification. Two oneCPU runs EXIT0, total10.11s wall.

### Status

[OK] **Completed**

### Next Steps

- User evaluates bounded candidate; do not launch200-key study, promote claims or archive without scientific acceptance.


## Session 29: Actual-support soft-Gram200-key screening and independent audit

**Date**: 2026-10-21
**Task**: Actual-support soft-Gram200-key screening and independent audit
**Branch**: `trans/tcom-main`

### Summary

Both full-block arms decode all200 old keys; log loss lower versus best native, with higher instrumented cost and inconclusive low-event FER superiority.

### Main Changes

- Reused both frozen upstream support/h0 outputs and saved priors; ran800 new block calls plus1200 native matched replays, zero SBL fits. Preserved old sources/results.
- Corrected an infeasible low-event forecast before freeze. Reported all ten arms/cells, paired contrasts, diagnostic compute and explicit non-claims; no new frames or Gemini transmission.

### Git Commits

| Hash | Message |
|------|---------|
| `ee5882ce` | (see git log) |
| `9ffa2efd` | (see git log) |

### Testing

- [OK] Thirty-two contract tests, compilation/shell syntax, all native replays, source/prior/raw/primitive gates; independent zero-call raw/primary-bootstrap recount and local/remote hashes pass. Main2000/2000 plus gate16/10 calls; DONE EXIT0,32.77s wall.

### Status

[OK] **Completed**

### Next Steps

- Independent Gemini assessment is now useful before user decides new-frame validation; no claim promotion or archive.


## Session 30: Independent Opus5.5 high review of soft-Gram disputes

**Date**: 2026-10-21
**Task**: Independent Opus5.5 high review of soft-Gram disputes
**Branch**: `trans/tcom-main`

### Summary

Completed one explicitly authorized Claude Opus5.5 high review; it supports five bounded objections and differs on experiment priority. Independently qualified reviewer assumptions; no new receiver experiments or claim changes.

### Main Changes

- Archived the complete prompt, original Gemini text, untouched Claude CLI reply, authorization chronology and hash manifest; preserved original source whitespace.
- Recorded agreements, useful matrix construction cost reminder, goal-dependent ablation priority and corrected reviewer assumptions in the active Trellis task.

### Git Commits

| Hash | Message |
|------|---------|
| `7100551f` | (see git log) |

### Testing

- [OK] CLI success, canonical model claude-opus-5-5, explicit effort high; all twelve archive manifest hashes pass. Saved-prior moment calculation falsifies the uniform initial variance assumption without receiver calls.

### Status

[OK] **Completed**

### Next Steps

- Present the reviewed opinion to the user; do not automatically launch experiments or further model debate.


## Session 31: Audited Gamma-only off-diagonal ablation on saved SBL cohort

**Date**: 2026-10-21
**Task**: Audited Gamma-only off-diagonal ablation on saved SBL cohort
**Branch**: `trans/tcom-main`

### Summary

Keeping full BHB but deleting Gamma offdiagonals raises logloss under both saved upstreams; independent raw and bootstrap audit passes. Existing old cohort only, no SBL/newframes or claim promotion.

### Main Changes

- Added narrow covariance facade and reused immutable full-loop/ref results; pre-run protocol and informed GA1/GA2 forecasts frozen before real calls. Fixed original-Gamma PSD projection and actual gate-full schema gaps before launch.
- Archived compact results/receipts and kept7745248raw bytes remote with hashes; cleaned only this runs disposable cache directories. User clarified context/cache reuse priority: reuse existing agents with incremental handoffs; actual cache hits require usage evidence.

### Git Commits

| Hash | Message |
|------|---------|
| `1198b266` | (see git log) |
| `03b6be16` | (see git log) |

### Testing

- [OK] Eight focused tests, compilation/shell syntax, gate8full replay and8observer assertions pass. DONE EXIT0 in32.20s,0.04869corehours;400/400main plus24/16gate calls. Independent zero-call raw/count/source/bootstrap verification passes, maximum CI/point deviation2.08e-17.

### Status

[OK] **Completed**

### Next Steps

- Keep full Gamma as candidate pending user decision on prospective new-frame validation; no automatic experiment, external discussion, mainline switch or archive.


## Session 32: Prospective fresh-frame soft-Gram score validation

**Date**: 2026-10-21
**Task**: Prospective fresh-frame soft-Gram score validation
**Branch**: `trans/tcom-main`

### Summary

Frozen full-block logloss benefit reproduces on50reserved fresh P1 frames/200keys: about12.7percent lower versus preselected native reference,1failure each versus4;FER unresolved. Independent saved-raw/source/count/bootstrap audit passes.

### Main Changes

- Refit both frozen SBL upstreams and shared round1 prior; evaluated only2full candidates and the fixed L-cov/native-joint reference. Reserved newframe IDs before outcomes, froze NF1/NF2, and qualified old-key inputs/endpoints before fresh generation.
- Reused existing implement/review contexts with incremental handoffs. Fixed shared-loader and gate-config provenance before launch; kept20,276,050raw bytes remote with hashes and cleaned only verified run caches. No further study, tuning, novelty claim, deployment or archive.

### Git Commits

| Hash | Message |
|------|---------|
| `73882cff` | (see git log) |
| `31bd1ee6` | (see git log) |

### Testing

- [OK] Nine focused synthetic tests plus affected corruption regression, compilation/shell syntax, old-key exact gate and complete fresh cohort pass.603SBL/804receiver/804decoder,101base generations,DONE EXIT0 in148.37s/.369611corehours. Independent zero-call bootstrap matches within2.08e-17; saved-vector/source qualification boundaries documented.

### Status

[OK] **Completed**

### Next Steps

- User evaluates prospective same-model score result before choosing further reliability/cost/novelty evidence; do not automatically extend or promote claims.


## Session 33: AFDM web publication screening and Opus design opinion

**Date**: 2026-10-28
**Task**: AFDM web publication screening and Opus design opinion
**Branch**: `workbuddy/monetization`

### Summary

Planning only: screened committed evidence and reviewed a minimal shared-AgentDock design. Keep free-form conversation outside learning; prevent wrong-project file writes without OS isolation.

### Main Changes

- Created 10-28-afdm-web-evidence planning artifacts and reproducible coarse inventory: 897 initial files/23.46 MiB from 20172; retain all 49 cards, defer older tests/snapshots, no source deletion.
- One tools-disabled claude-opus-5-5 high review, USD0.147915; simplify exchange to unsealed learning, identity and release pointer; evidence only in read-only drop.

### Git Commits

Planning artifacts are committed in the Git log; no deployment commit.

### Testing

- [OK] Inventory counts/bytes and seeds, safe paths, no default exam/source snapshots, reviewer model/effort/packet hashes and curated manifests checked; no deployment, runtime closure or web E2E.

### Status

[OK] **Planning/review deliverables complete; task remains planning**

### Next Steps

- User reviews latest design before any implementation/deployment; no GitHub/VPS project push or AFWDM changes.


## Session 34: Deploy scoped AFDM web evidence and learning exchange

**Date**: 2026-10-28
**Task**: Deploy scoped AFDM web evidence and learning exchange
**Branch**: `workbuddy/monetization`

### Summary

Published 909 selected evidence files and a five-file learning exchange on existing jgw AgentDock; AFWDM existing dirty work and refs unchanged. Updated canonical optional-delegation/GPT-6.1 Sol rule. Web acceptance remains with Eric; task stays in_progress.

### Main Changes

- Source/hash and effective-user read/write checks pass; shared service restart occurred once under explicit approval; host records committed/pushed to verified private host-jgw.

### Git Commits

| Hash | Message |
|------|---------|
| `820630b6` | (see git log) |

### Testing

- [OK] Eight targeted temporary-Git tests, Ruff and compilation passed; live payload/identity and AFWDM fingerprint checks passed; rule installer consistency passes. No actual web interaction, official test note or scientific calls.

### Status

[OK] **Completed**

### Next Steps

- Eric manually verifies ChatGPT reading/learning. Do not archive until human acceptance; automatic approval rejected premature archive.


## Session 35: Close AFDM web access after manual acceptance

**Date**: 2026-10-28
**Task**: Close AFDM web access after manual acceptance
**Branch**: `workbuddy/monetization`

### Summary

Eric explicitly reported 我验收了 on 2026-10-28. Recorded user-reported web acceptance and archived only afdm-web-evidence; no repeated tests, deployment, source deletion or scientific calls.

### Main Changes

- Closed the manual acceptance gate and retained original deployment receipts; task archived under 2026-10.

### Git Commits

| Hash | Message |
|------|---------|
| `e31661d9` | (see git log) |

### Testing

- [OK] Record-only change: explicit acceptance verified against user message; no new web test claimed.

### Status

[OK] **Completed**

### Next Steps

- Completed; normal use and future updates follow tools/web_access/README.md.

## 2026-11-09 — Fixed-channel OAMP/LDPC screen

User-authorized deinlab replay is complete. On the 40 archived 6.5 dB syndrome-triggered frames, OAMP recovers 9 after two LDPC calls versus fixed-TF 14, at median continuation times 0.629/0.086 s. Frozen screen fails. Separate raw recount checks 160 decoded checkpoints with no receiver reruns. Code/protocol `cd24f670`, initial result `a4af3f2e`. Scope and evidence are in `.trellis/tasks/09-22-tf-production-gap-audit/research/oamp-ldpc-screen-20261109.md`. No open follow-up was added.

User-challenged fairness/cost follow-up completed the same adapter through20rounds (6/9/12/14/15rescues at1/2/5/10/20;24frames still changing at20). Exact cyclic-band LE parity on one real frame passes and reduces one-step dense setup/update median from0.573s to0.107s. Opus5.5 supplied-material review confirms LE correctness but limits naming to an isotropic turbo-LMMSE adapter. Original budget counts stand, previous implication of OAMP elimination is explicitly corrected. Authorized reviewer packet, response, and synthesis are under the parent task's `research/oamp-review-20261109/`.

User-requested complete cost comparison now measured serially on deinlab with alternating arm order. OAMP20 versus TF2 continuation medians1.114289/.086183s (12.929×); setup .578938s, OAMP decoder .480448s. All880 saved checkpoints reproduce exactly, compact timing aggregation passed locally. Source `f6bc287a`, output `outputs_oamp_ldpc_20261109/timing20_v1/timing_results.json`. Common native prefix excluded, dense implementation and fixed rounds without early termination.
