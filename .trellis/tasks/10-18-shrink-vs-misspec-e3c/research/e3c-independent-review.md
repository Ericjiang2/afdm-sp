# E-3c independent review (2026-10-18, draft)

Reviewer: `forensic_audit`, gpt-6.1-sol/high. User reprioritized E-3c completion ahead of broad E1/E2/E3 audit. This review is confined to the new E3c implementation and its immediate frozen interfaces. No receiver was launched by this reviewer, no remote files were written, and no implementation or frozen source/output was changed.

## Current conclusion

Current six-arm receiver paths, strict readers and statistics have no identified blocking numerical defect. The reviewed frozen-source relocation fix is strict: expected MD5 is unchanged, actual bytes and any recorded loaded-module MD5 must match, and resolved paths are retained. The initial missing canonical path was an engineering provenance failure before receiver execution; it was not evidence of incorrect receiver results.

**READY for final engineering gates and, if they pass, frozen production launch.** Launcher, protocol and final freeze integration have now been reviewed. This is an implementation-readiness conclusion; it does not claim that the engineering gates or full production matrix have already passed.

## Findings (fixed)

- File: `experiments/tf_e3c_shrink_20261018/e3c_arms.py::gamma_consistency`, with regression in `test_e3c.py` and protocol clarification.
  Issue: two final-gate keys failed the checker's relative diagonal test after computing `Q - B^H B - sigma2 I`. Subtracting Gram-scale quantities to recover very small uncertainty loses significant digits; division by the tiny uncertainty scale amplified this rounding. Main reported Gram-normalized error `4.25e-17` alongside relative diagonal error `9.04e-12` (another key `1.007e-12`). These real-key figures were supplied by main, not independently rerun here.
  Fix reviewed: compare `_system`'s directly returned gamma plus the declared extra ridge against SBL gamma. Independently check actual Q against the Hermitian `B^H B + Gamma_var + sigma2 I` closure. Check both direct gamma diagonals against the expected uncertainty scale. Both component/closure and relative diagonal thresholds remain **1e-12**. This changes only diagnostics, with no change to SBL, selected atoms, refinement, gain solve, detector or decoder. No failed root or budget charge is discarded.
  Independent verification: AST-loaded the exact frozen `_system` and path/operator definitions with a NumPy Cholesky fixture (explicitly not a SciPy/receiver replay). At `v_i=1e-15`, all six arms reproduced old relative diagonal errors `.13849`–`.16516`; stable diagonal errors were zero and Gram-normalized closure errors <=`1.68e-16`. A 1% scaling error in tiny SBL gamma, corrupted Q and corrupted directly returned gamma were all rejected. Reviewed regression additionally covers wrong extra-ridge bookkeeping. Current Python AST parse passed. **READY for a new same-source unit/20-key gate/smoke qualification; prior 18/20 is not promoted to a passing final gate.** Full SciPy regression and actual final engineering receipts remain main-owned verification before freeze/production.
- File: `experiments/tf_e3c_shrink_20261018/e3c_provenance.py`.
  Issue: direct canonical source paths do not exist on the server for the frozen/native `*_reviewed_*` layouts.
  Fix reviewed: implementer added documented aliases plus actual loaded-module path resolution. Digest mismatch, loaded digest mismatch, or absent files raise; no `unchecked` success path. Resolved actual paths are recorded in config. Independent local relocation test passed. The reviewer did not make this implementation edit.

## Verified interfaces

- `e3c_arms.py`: scalar/full matrices, oracle profile selection and additional `sum(v) I` are consistent between SBL, continuous refinement and the fixed-geometry `_system` solve. In `cov+ridge`/`diag2`, only additional ridge counts toward the uncertainty matrix; the existing `sigma2 I` remains the noise ridge. SBL gamma is restricted with the selected candidate positions in energy order. `gamma_consistency` symmetrizes the selected full matrix consistently with frozen SBL.
- `e3c_driver.py`: six arms reuse the same observation, decoder APP means, prior, candidate set and starting soft precision. Truth enters named profile-oracle/calibration/scoring paths only; baseline dictionaries and gamma do not consume the oracle profile. The fixed-refit baseline solves at the selected SBL geometry and decodes it with the same round-1 check prior; continuous results use the frozen refinement solver. On-grid reuse joins the original E3 atoms and retains its provenance.
- Input power is correct: physical rho=.3 observations/data are divided by `sqrt(2(1-rho))`, so the internal QPSK data power is .5. `moments`, hard decisions and oracle alphabet assertions use this internal power. There must be no further factor `.7` in gamma. Independent dense/operator and QPSK checks already saved in `experiments/tf_covariance_audit_20261018/forensic_synthetic_local.json` support this interface, without constituting a real-frame receiver replay.
- G1 compares stage-1 atoms, round-1 decode hash, candidate count, both on-grid/off-grid baseline atoms, output decode hash, information errors and NMSE against the same old E3b key. G3 repeats all six arms and compares every non-timing field. A mismatch raises and is persisted as an error row.
- `e3c_lib.py`: both E3/E3b joins verify old manifests and reject requested duplicates, failed requested rows and missing requested keys. No permissive replacement is used.
- `e3c_agg.py`: rows/config SHA must agree, shard keys and global keys must be complete, sources must match across shards, all six arms must exist, smoke cannot mix into main, and baseline/G3/refinement constraints are enforced. Independent randomness is entropy/domain/frame jointly across scenarios/SNR; shared noise/gain/code/info hashes must agree. This corrects the previous scenario-separated clustering contract.
- `sampling.py`: pooled row means are the estimand; one multinomial cluster draw is shared by all metrics and arms. Fraction confidence intervals are conditional on positive denominators with an explicit <=1% failure gate. Sh/Or classifications are descriptive recovery labels, not a mutually exclusive causal verdict. Oracle noninferiority is reported separately.
- `e3c_budget.py`: all leases charge the shared 15-core-hour ledger; reservations and writes are file-locked. Startup, successful/failed work, and killed unclosed leases are charged. The receiver driver requires single-thread environment and hidden GPU, and lease expiration propagates to a persisted failure. Production must use the same budget directory and bounded launch concurrency.
- `launch_e3c.sh`: gate mode uses a new root, one shared budget directory, <=20 gate processes and <=12 smoke processes, each within the requested <=24 process limit. Chain mode performs freeze/gate/budget checking before creating main output, divides remaining reserved time among <=24 workers, propagates worker failure, aggregates only after all workers succeed, and retains raw/config/summary SHA receipts before compression. Main owns tmux and pre-launch resource checks.
- Freeze is checked twice: launcher verifies gates, budget-directory identity, main-owned FREEZE receipt and full CODE_MD5 coverage; each production driver requires `--freeze-root`, matching gate/FREEZE source hashes and a commit receipt. Unit, gate, smoke and production have one strict source identity, including all local Python/shell sources, protocol and shared sampling source. No source-hash waiver is present. Final zero-variance synthetic test now explicitly checks all six arms reduce to the same zero-Gamma Q/gains/objective.

## Findings (not fixed)

- None identified in the final reviewed implementation. Main must still obtain actual final engineering receipts on exactly these source bytes, commit/write the freeze receipt, and preserve source bytes during the run. No old-receiver rerun is required by this review.

## Verification

- Independent local `test_e3c_agg.py`: **pass**, 4 tests (classification boundaries, denominator failures, shared scenario clusters and strict row reader).
- Independent local `test_e3c_provenance.py`: **pass**, 1 test with both relocation aliases and negative cases.
- Independent temporary-directory budget smoke: **pass** for success charging, exception charging, timeout propagation and over-budget reservation rejection; no receiver or production ledger touched.
- Syntax: all currently present E3c Python files AST-parse successfully.
- Shell syntax: `bash -n launch_e3c.sh` **pass**. Final launcher/freeze changes were read directly; no receiver was launched by the reviewer.
- Lint/type-check: no configured package-wide command established for this standalone experiment; not claimed. No implementation changes were made by this reviewer.
- Six-arm Gamma synthetic test and real-frame gate: main reports execution in AFDM; **not independently rerun by reviewer**. Main owns receipts and pass/fail interpretation.
- Not independently recomputed: remote/all-shard source bytes, actual original observation arrays, old raw-row recount, full E3c receiver output, engineering gate, smoke cost, 1200-key completion or final scientific results.

## 最终科学解释审查（全量完成后，2026-10-18）

本节只读核对 `experiments/tf_e3c_shrink_20261018/out/qualified_v3/main/summary.json` 和 `experiments/tf_covariance_audit_20261018/out/e3c-final-check/e3c_result_check.{md,json}`。冻结提交为 `e1bfd013873a81cf1a6f3c2754a6e871726fa0c1`。独立复核收据报告：1200 个完整键、100 个 RNG 帧簇、零错误/重复行，318227 个数值叶子及 507 个布尔/null 叶子复核通过，44 个来源文件及输入哈希在复核前后不变。复核复用了已审查的 `sampling.py`，是保存行的数值重算；不是另一个 bootstrap 算法，也不是旧 E3b 接收机的独立重跑。本审查人阅读了这些收据及完整分格摘要，没有再次执行原始行重计数或接收机。

### 可以说

1. **在这套冻结、最多 100 次 SBL 迭代的接收机中，额外各向同性惩罚能恢复大部分 diag/cov FER 差距。** 六臂 FER 依次为 diag-off 3.25%、cov-off 15.75%、cov+ridge 4.25%、diag2 2.333%、cov-oracle 18.667%、diag-oracle 2.167%。预登记的描述性恢复份额 Sh=.92，95% CI [.8493,1]；分母失败率为零，满足“recovered”标签。这个结论对应所执行的有限计算管线，而不是收敛后的最优解。
2. **恢复大部分差距不等于已追平标量基线。** cov+ridge 比 diag-off 仍高 1 个百分点，配对 CI [0,2] 个百分点；未建立等效或 1pp 非劣。cov+ridge 比相同额外剂量的 diag2 高 1.917pp，CI [.998,2.917]pp，因此“补上标量 ridge 后完整结构就没有剩余影响”也不成立。diag2 是这批已测非 oracle 臂中 FER 点估计最低者；摘要没有提供 diag2−diag-off 的配对差值区间，不能仅凭点估计或边际 CI 宣称它显著优于基线。
3. **所测试的 realized-error-energy-profile 干预没有救回完整 Γ，反而恶化。** cov-oracle 的 FER 比 cov-off 高 2.917pp，Or=−.2333，CI [−.3435,−.1419]；描述为“small”时必须同时说明它实际为负。cov-oracle 比 diag-oracle 高 16.5pp，CI [14.167,18.833]pp，显然未达到预设的 1pp 非劣检查。
4. **固定几何增益对照定位了原比较中的关键混杂。** 在本次 100 帧子集中，cov 的 FER 从 SBL 增益 11.583% 变为固定几何 refit 16.75%，增加 5.167pp，CI [4,6.417]pp；随后连续细化降至 15.75%，相对固定 refit 改善 1pp，CI [−1.833,−.25]pp。diag 的三个阶段为 4.25%→3.833%→3.25%，其逐步 FER 差值 CI 均含零。两臂点估计差距从 SBL 的 7.333pp 扩大到固定 refit 的 12.917pp，连续细化后为 12.5pp。因此，这个子集的差距扩大主要发生在增益估计器切换；连续细化没有制造 cov 的恶化，反而在 refit 基础上改善它。该分解直接适用于本次 100 帧子集，不能未经核对推广成旧 200 帧 E3b 全集的精确数值分解。
5. **APP 代理分布在本批数据上有明显经验误差能量失配。** 实际平方误差之和/APP 方差之和 κ=2.149，且约 23.17% 的判错符号落在所定义的“自信错误”集合。它们是样本内诊断量，没有在摘要中提供抽样区间。可报告失配现象；不能由这些总量指定唯一的后验误设类型或解释全部 FER 差距。

### 不可以说

- 不能给出互斥的“SHRINKAGE 获胜、MISSPEC 被排除”因果判定。ridge 同时影响优化路径、选出的支持、增益与后续译码；`v_o=|x−mu|²` 不是条件后验协方差，也不恢复跨符号误差结构。两种干预的反应只识别所测试干预的效果。
- 不能说“正确方差仍然失败”“精确后验不如标量 Γ”或“APP 校准无关”。数学投影身份对所给定的独立符号方差是精确的，所给定的统计代理和真实联合后验是否一致是另一问题。负 Or 与 κ>2 可以同时成立，二者没有逻辑矛盾。
- 不能保留“脱栅格伤害 cov，所以插值解释已被完全排除”的旧措辞。新固定几何对照将增益切换与连续运动分开：前者恶化 cov，后者在同一 refit 接口上改善 cov。它仍未证明某个更广义、匹配其他增益估计器的脱栅格方案无效。
- 不能称 cov+ridge 的恢复是“收敛后的收缩解”：1191/1200 次 SBL 未达到停止准则（99.25%）。其他臂亦需保留实际状态：diag-off 739、cov-off 1101、diag2 361、cov-oracle 1123、diag-oracle 76 次未收敛。旧 baseline 的 100→400 次 R-iter 不覆盖新 ridge 臂，不能替新臂排除迭代预算依赖。
- 不能把 Sh=.92 称为“92% 的机制贡献”或推广为逐格普遍结论。6 dB 的 U/G 两格 Sh CI 下界均未到 .8；高 SNR 多个分格因零/稀少 FER 差的分母失败率超过 1% 而不可评估，即使条件 CI 恰为 [1,1] 也不能认证。
- 不能声称得到新样本预测、部署规则、全 rho/全场景最优方法或独立确认。主样本复用了 E3b 帧，仅限 rho=.3、U/G、6–11 dB、100 个独立随机帧。oracle 使用真值；非 oracle 臂的观测排名本身也不是预登记的样本外选择规则。

### 异常及审查结论

未从最终摘要与通过的保存行复核收据发现新的数值自洽性异常或运行无效证据。高 ridge 非收敛率、oracle-profile 恶化、经验 κ>2，以及增益切换的反向影响均应显式报告；它们是有限迭代/统计代理/估计接口的实测限制，不能自动登记成代码 bug，也不需要为本节审查擅自新增实验。前两次来源路径与相消检查器失败保留历史和成本；它们不证明最终接收机路径错误。

建议最终表述：**“在冻结的 100 次迭代管线上，增加各向同性惩罚恢复了约 92% 的标量/完整 Γ FER 差距；realized-error-profile oracle 未改善完整 Γ。固定几何对照表明，本子集差距的扩大主要出现在增益估计器切换，连续细化本身反而改善 cov。结果支持正则化敏感性，尚未识别唯一机制，且新 ridge 臂大多未收敛。”** 科学结论保持 draft，不自动替换旧已接受主张或完成研究父任务。
