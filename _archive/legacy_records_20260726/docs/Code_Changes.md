# Code Changes — AFDM End-to-End Learning

改动详细记录。每次代码改动的完整记录，关联 commit。

---

## 格式模板

```markdown
### [ID] YYYY-MM-DD | 改动标题

**Commit:** [hash] (如果有)

**改动范围:**
- 新增文件:
- 修改文件:
- 删除文件:

**改动详情:**
```diff
# diff 或描述
```

**改动原因:**

**影响评估:**

**回滚方案:**

---
```

---

## 记录开始

### [cc-0613-01] 2026-06-13 | v1.1 | 补测三脚本 + integer-Doppler flag (§V/§VII/§IV)

**变更类型:** A — 当前版本内追加 (无新版本号)

**Commit:** `1a7001e` (bench + flag), `4b23f1b` (analyzer), `9731f33`/`f4c9a1a` (结果), `d41276d` (QA#48)
**分支:** `trans/tcom-main`

**改动范围:**
- 新增文件:
  - `afdm_sp_joint_unrolled/decision_complexity_bench.py` (215 行)
  - `afdm_sp_joint_unrolled/decision_mech_analyze.py` (177 行)
  - `afdm_sp_joint_unrolled/suppl_tests_report_20260613.html` (报告)
- 修改文件:
  - `afdm_sp_joint_unrolled/paired_learned_eval.py` (+8 行, 新增 `--integer-doppler`)
  - `.gitignore` (whitelist outputs_mech/ + outputs_selfsupp/)

**改动详情:**
- `decision_complexity_bench.py`: 基准 `whitened_suffstats` 三路成本 — dense Cholesky O(N³) vs P-diagonal matvec block-CG vs 下游 `joint_omp_mp_iterative`。DiagOp 类从 H 抽 ≤P 条 shift-diagonal 实现 O(NP) matvec；block_cg 解 HPD 复系统；输出 N×{512,1024,2048} 对比表。
- `decision_mech_analyze.py`: 两子命令复用 `decision_gateA_bootstrap` 的配对 block bootstrap — `rho` 模式算各 ρ 的 ratio(achievable/geom) + integer-Doppler 控制；`pool` 模式跨 seed-shard 合并 achievable/genie per-frame 数组算 ratio(achievable/genie)。
- `paired_learned_eval.py`: `--integer-doppler` → `sys_obj.use_frac_doppler=False`，硬取整 Doppler 到整数 k-bin，杀 Dirichlet 分数-Doppler 泄漏 (机制控制)。默认行为不变，向后兼容。

```diff
+ ap.add_argument('--integer-doppler', action='store_true', ...)
  sys_obj.v_mean = float(args.v_mean)
+ if args.integer_doppler:
+     sys_obj.use_frac_doppler = False  # mechanism control: no Doppler leakage
```

**改动原因:** 闭合 QA#47 留下的三处悬空 — (1) achievable-Λ 复杂度决定 cov-head 是 §V contribution 还是脚注；(2) §VII 机制曲线 (ρ-sweep + Doppler 控制) 未跑；(3) §IV SNR20 self-suppression 未测。

**结果摘要 (详见 QA #48):**
- T1: Λ scorer = receiver 的 1.6% (@N=1024) → **cov-head 降脚注**。
- T2: 优势随 ρ↓ 单调 (C_d∝1−ρ) **坐实 SP-covariance gap**；integer-Doppler 优势不减 **证伪 leakage-prior**。
- T3: 9200f pool ratio(ach/genie)=1.098 [0.979,1.357] → self-suppression **证伪**，genie 仍天花板。

**影响评估:** 纯追加 + 一个默认关闭的 flag，不碰 bit-exact 主干，不影响既有 eval。三项结论直接改写 §V/§VII/§IV 的论文框架。

**回滚方案:** `git revert 1a7001e 4b23f1b`；新脚本删除即可，flag 默认 off 无副作用。

---

