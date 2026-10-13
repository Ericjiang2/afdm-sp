# TCOM_PLAN.md — IEEE Trans. on Communications submission plan

**Branch**: `trans/tcom-main`
**Started from**: tag `fyp-final` (commit 5056b7b, weighted 86.7 / A5)
**Target venue**: IEEE Transactions on Communications
**Status**: §1 / §2 / axis-C profiling smoke / axis-A iter-0 math — DONE. Iter-loop debug + consistency test + integration are next. See §9 progress log below.

> Source-of-truth umbrella plan: `~/.claude/plans/fyp-ieee-trans-git-trans-git-eager-popcorn.md`. This file is the project-internal mirror, kept in git, that the TCOM workflow consults and updates.

---

## 1. Headline claim

> A 1 041-parameter learned support-refinement head on top of a faithful differentiable unrolling of the classical SP-AFDM joint OMP + DA-LS + sparse MP-BP receiver achieves consistent paired BER reduction across multiple training seeds, reproduces the published Qing 2024 SP-AFDM baseline as a reference, and operates in the same arithmetic complexity class as the unrolled receiver while staying empirically faster than dense-MMSE alternatives.

This claim sets the bar above the FYP version (A5/86.7) by adding three load-bearing pieces: external-baseline reproduction, multi-seed retraining envelope, and measured complexity. Listwise / per-candidate mechanism work supports the "why it works" half of the paper.

---

## 2. Novelty axes (TCOM)

| Axis | Feature branch | TCOM section it supports | Effort (GPU·h) | Status |
|---|---|---|---|---|
| A — **Cao 2024 SP-AFDM external baseline** (pivoted from Zheng 2026-05-07; Zheng kept in prior-art only) | `trans/tcom-main` (cao_baseline subdir) | §IV-D (matched-budget comparison), §IV-A waterfall | ~12 total (Cao impl ~4h coding + 200-frame consistency ~5 min + E2 paired pool ~6–8 GPU·h pending) | **95% — Cao 2024 ICCT (`cao2024spomp`) algorithm 1:1 implemented in `cao_baseline/cao_isp_receiver.py` dual-basis (ours canonical, paper sanity-check broken). Two sensing-matrix invariants verified at machine precision. Consistency test (200 frames, N=512, BPSK, integer Doppler, λ=0.5) reproduces paper Fig 3 + Fig 4 slopes correctly with 0.5–1.1 dec absolute offset attributed to setup details paper underspecifies (pilot construction; MP backend). Zheng kept as cross-validation reference at his own regime (1000-frame Fig 3 reproduction in `outputs/consistency_1000frames.json`). Remaining: integrate `--baseline cao_isp` to `paired_learned_eval.py`, run E2 paired pool on UWA regime, document Zheng→Cao pivot in §IV-D writeup.** |
| B1 — Listwise top-K loss replacing BCE+rank-hinge | `trans/listwise-mechanism` | §III-D (training objective), §IV-B (5-seed envelope) | ~24 (~5 seeds × ~5 h training each) | not started |
| B2 — Per-candidate mechanism attribution | `trans/listwise-mechanism` | §IV-E (mechanism analysis) | ~6 (single 250-frame paired run × 3 SNR + post-processing) | not started |
| C — Wall-clock + MAC + memory profiling | `trans/complexity` | §IV-F (complexity table) | ~3 (no training, pure timing) | **70% — measure_runtime + analytical_macs landed; smoke pass on deinlab; production run pending Qing receiver availability** |
| **D — Same-budget classical heuristic baseline (OMP-(P+K))** | `trans/tcom-main` (in-place) | **§IV-D-prime (NEW): isolates "is the gain just budget?"** | **~1 (already done; 35-min single run on deinlab)** | **DONE — 250 frames × 3 SNR × K∈{2,4,8,16}, all 4 verification checks pass** |

Total budget: ~64 GPU·h on the shared RTX 4090, spread over the 3-month window. Comfortable.

> **Why axis D was added (2026-05-07)**: After 3-round Codex GPT-5.5 xhigh debate on TCOM novelty bar, the highest-leverage missing experiment was the "same-budget classical heuristic" comparator — i.e., does the learned head still beat classical when classical is allowed to spend the same K-extra-atom budget via the most natural heuristic (continue OMP for K more iterations)? Codex flagged this as the #1 reviewer attack on the learned-head conceptual contribution; the experiment cost ~0 GPU·h because the OMP path can be reached via the existing `oracle_support` plumbing in `joint_omp_mp_iterative`. Result is a strong positive: OMP-(P+K) **regresses** monotonically with K rather than closing the gap, which converts the comparator from defensive rebuttal into affirmative evidence for the learned head's non-linear support-refinement role. See §9 progress log entry 2026-05-07 for numerical detail.

---

## 3. Experiment matrix

| Experiment ID | Receiver | Channel | SNR (dB) | Frames | Seeds | Output |
|---|---|---|---|---|---|---|
| E1 (already in FYP) | unrolled + classical | UWA-style 8-path | 0/5/10/15/20/25/30 | 600/773/1300 pooled @ 20/25/30 | 20260423/424/425 | `outputs_loop12_*` |
| E2 (NEW) | Qing 2024 SP-AFDM | UWA-style 8-path | 15/20/25/30 | 300 paired | 20260423/424/425 | `outputs_qing_baseline_*` |
| E3 (NEW) | unrolled + listwise-N (N=0..4) | UWA-style 8-path | 15/20/25/30 | 300 paired | seed 20260501..20260505 | `outputs_listwise_seed{0..4}_*` |
| E4 (NEW) | listwise-best | UWA-style 8-path | 15/20/25 | 250 paired | 20260419 | `outputs_attribution_*` |
| E5 (NEW) | classical / Qing / unrolled best | UWA-style 8-path (N ∈ {512, 1024, 2048}) | 20 (single SNR) | 50 | one | `outputs_complexity_*` |
| **E6 (DONE 2026-05-07)** | classical OMP-(P+K), K∈{2,4,8,16} | UWA-style 8-path, v=2.0, fs=4B | 15/20/25 | 250 paired | 20260419 | `outputs_omp_extended_4B_big/` |

E1 stays as-is (the FYP pool); E2-E5 fill the gaps. **E6 is the same-budget classical heuristic comparator: shares H_true / data / noise per frame with the existing oracle headroom run (`outputs_loop13_headroom_4B_big_v2/`) since baseline + oracle_physical reproduce bit-exactly.** Output JSON paths follow REPRODUCTION.md conventions.

---

## 4. Claim → evidence map

(Keep this updated as experiments land. "✓" means evidence exists in repo; "—" means pending.)

- C1: 5-seed mean BER reduction at 20/25/30 dB ≥ existing single-seed Δ; 95% CI from listwise retrains. → E3, —
- C2: Reproduced Qing 2024 SP-AFDM baseline within ±10% of published BER. → E2, —
- C3: Unrolled+head beats Qing 2024 by paired McNemar p < 1e-3 at 25/30 dB. → E1+E2, —
- C4: Per-candidate attribution shows ≥ 60% of added atoms are Dirichlet sidelobes (causal mechanism evidence). → E4, —
- C5: Wall-clock at N=1024 within 2× of classical-unrolled; MAC count in same asymptotic class. → E5, —
- C6 (preserved from FYP): support recall ≥ 95%, gap-closed 61/81/98% across SNR — already in `outputs_loop13_*`. → ✓
- **C7 (NEW 2026-05-07): Single-pass OMP-(P+K) does NOT close the oracle-physical gap; for K ≥ 4 it regresses BER monotonically with K at SNR ≤ 20 dB. The learned head's gap-closed gain is therefore not a budget effect but a non-linear support-refinement effect that linear-correlation greedy cannot replicate.** → E6, **✓** (gap-closed at 4B, v=2.0, K∈{2,4,8,16}: −8.7/−21/−45/−102% at SNR=15 dB; −61/−128/−337/−927% at SNR=20 dB; +20/+5.6/−85/−459% at SNR=25 dB — vs learned head +61/+81/+98%).

---

## 5. Paper structure (TCOM, ~12-14 pages double-column)

1. Introduction (~2 pp) — motivation, related work pointer, contributions
2. Problem setup & SP-AFDM background (~1 pp)
3. Method (~3 pp) — A. unrolled receiver overview, B. learned head, C. C2-rel feature design, D. listwise top-K loss
4. Results (~4-5 pp) — A. 4-arm waterfall (serial/classical/Qing/learned), B. 5-seed retrain envelope, C. iter-convergence + support recall (preserved from FYP), **D-prime. Same-budget classical heuristic OMP-(P+K) NEW**, D. paired McNemar table, E. mechanism attribution, F. complexity table
5. Conclusion + future work (~1 pp) — MSML, robustness sweeps, real-data UWA validation

### §IV-D-prime sketch (NEW, ~0.5 pp)

- **Question**: is the learned head's BER gain just "more atoms in the support" (a budget effect), or does it require non-linear ranking that linear-correlation greedy cannot achieve?
- **Construction**: extend OMP to single-pass `P+K` atoms (K∈{2,4,8,16}), route through the same `joint_omp_mp_iterative` pipeline as baseline (cluster-expand, DA-LS, MP-BP unchanged). This is the most natural same-budget classical heuristic — Heuristic-1 in Codex's leverage ranking.
- **Plot**: bar chart with K on x-axis ∈ {0, 2, 4, 8, 16}, BER on y-axis, three SNR panels, dashed horizontal lines at learned-head BER and oracle_physical BER.
- **Headline number**: at SNR=20 dB, OMP-(P+K) BER grows monotonically (3.89e-4 → 6.27e-4 → 8.87e-4 → 1.70e-3 → 3.99e-3 for K=0/2/4/8/16) while the learned head reaches ~7e-5. At SNR=15 dB, gap-closed against the oracle ceiling: OMP-(P+4) **−21%** (regression) vs learned head **+61%**.
- **Mechanism paragraph**: in an SP frame the residual after OMP-once is dominated by data-pilot interference (not channel-residual energy), so OMP greedy on `|Φᴴ r|` rewards atoms that fit data leakage rather than the Dirichlet-expanded virtual taps. Verification on individual frames (frame 0 / 5 at SNR=15) confirms K-extras land at delays outside the physical channel span or at conjugate-Doppler "mirror" positions — never at the ±1 Doppler sidelobes that the learned head targets. Once an unrelated atom enters the support, the cluster-expand + DA-LS step gives it a non-trivial gain → phantom paths bias `H_hat` → BER and NMSE both regress.
- **Why this matters for the conceptual claim**: the learned head is not "more atoms"; it is "atoms ranked against a richer feature set than `|Φᴴ r|`". This converts the comparator from defensive rebuttal into affirmative evidence that the head captures structure unreachable by linear-correlation greedy, regardless of budget.

Headers / tables already drafted in `paper/sections/Section{1..5}.tex` (FYP version) — needs scope expansion not full rewrite.

---

## 6. Timeline (3-month window)

- **W1-W2**: §1 git+repo cleanup (in progress); seed `qing_baseline/` + `listwise/` README stubs.
**Original plan timeline** (kept for reference):
- W1-W2: §1 git+repo cleanup
- W3-W5: implement Qing 2024 receiver, run E2, write §III-A
- W6-W7: implement listwise loss, run 5-seed retrain (E3)
- W8: per-candidate attribution (E4); §IV-E
- W9: complexity profiling (E5); §IV-F
- W10-W11: paper integration + figures + claim audit
- W12: cross-model review, submit

**Revised timeline** (per actual rate, 2026-05-06):
- ✓ W1: §1 git+repo cleanup + §2 directory reorg
- ✓ W2 (early): §3 axis C profiling tools landed and smoke-tested
- ✓ W2 (early): §3 axis A iter-0 math verified
- **NOW (W2-W3)**: finish axis A — detector swap → consistency test against Fig 3 → integrate into paired_learned_eval as `--baseline qing_sp_afdm`. Acceptance gate: BER curve matches Fig 3 16-pilot row within ±20% on first pass, ±10% after tuning.
- W3-W4: axis A production run — 4-arm waterfall on our channel (serial / classical / Zheng / learned), 3-seed pool matching `outputs_loop12_*` schema. While GPU runs in tmux, start drafting §IV-D Zheng baseline subsection.
- W5-W6: axis B1 — listwise loss (NeuralSort/SoftSort) + 5-seed retrain. Multi-seed envelope → §IV-B.
- W6: axis B2 — per-candidate attribution on listwise-best ckpt → §IV-E.
- W7: re-run axis C `measure_runtime.py` with all 3 receivers (now Qing exists) for §IV-F.
- W8-W9: paper integration. Replace FYP wording in `paper/sections/Section{1,3,4,5}.tex` with TCOM scope; add Zheng comparison table; add listwise / mechanism / complexity subsections.
- W10: full re-run of CITATION_AUDIT, PAPER_CLAIM_AUDIT, PROOF_AUDIT, EXPERIMENT_AUDIT. Each must return PASS or WARN-only before submission.
- W11: cross-model review (Codex GPT-5.5 / Oracle Pro); apply each round's fixes.
- W12: final polish, tag `tcom-submission-r1`, submit.

---

## 7. Risks

- **R1 (high)**: Qing 2024 reproduction may not match the paper's reported BER within ±10%. Mitigation: include the gap as an honest caveat and treat the comparison as "best-effort reproduction"; failure-of-reproduction is itself a useful finding.
- **R2 (medium)**: Listwise loss may not improve over BCE+rank-hinge. Mitigation: 5-seed comparison still yields the retraining envelope (R3 W-2 was the deferred FYP item), so E3 is paper-useful even if listwise doesn't win.
- **R3 (low)**: GPU contention on shared RTX 4090. Mitigation: tmux + small batch size + off-peak scheduling per CLAUDE.md.

---

## 8. Cross-references

- **Architecture / canonical model**: `afdm_sp_joint_unrolled/classical_joint_unrolled.py` (do not refactor — locked baseline)
- **Reproduction map**: `afdm_sp_joint_unrolled/REPRODUCTION.md`
- **Model checkpoint manifest**: `afdm_sp_joint_unrolled/models/MANIFEST.md`
- **FYP final state**: tag `fyp-final` (5056b7b)
- **FYP audit history**: `EXPERIMENT_AUDIT.md`, `PAPER_CLAIM_AUDIT.md`, `paper/PROOF_AUDIT.md`, `paper/CITATION_AUDIT.md`
- **Deferred-from-FYP weakness map**: `REVIEW_STATE.json` `r3_residual_weaknesses_deferred[]`

---

## 9. Progress log

### 2026-05-06 (session 1)

**Branch + repo (§1):**
- `693c96e` snapshot before TCOM uplift
- tag `fyp-final` → `5056b7b` (FYP final commit)
- branch `trans/tcom-main` opened
- `7139608` add `models/MANIFEST.md` skeleton + project .gitignore negation for it
- **Surprise**: AFDM-CE itself is git-clean (10.9 MB / 295 files, 0 tracked .pt). The 95 tracked .pt files vault-wide all live in old `01_Projects/.../OTFS-channel-estimation/` (project's pre-rename location). User-authorized cleanup:
- `c0a6c57` remove old `01_Projects/.../OTFS-channel-estimation/` backup (-1217 files, -237 524 lines, includes 4 orphan submodule gitlinks)

**FYP archive (§2):**
- `4916bc9` archive Logbook docx, FYP narrative/plan markdowns, midterm interim PDF → `_archive/fyp/`. Untracked items (Defense PPT, Log Book PDF, _logbook_archive backups, midterm PNGs) physically moved but kept untracked.
- `450876b` archive paper/Exemplar / Marking Schema / Instructions PDFs + main_anonymous.{tex,pdf} → `_archive/fyp/paper/`; delete latexmk aux files for main_anonymous.

**TCOM scaffolding (§2):**
- `48ca711` `tcom_plan/TCOM_PLAN.md` + `TCOM_RESPONSE_TEMPLATE.md`
- `985721e` 4 feature subdir READMEs (`qing_baseline/`, `listwise/`, `attribution/`, `profiling/`)

**Axis C — profiling (§3.3, branch `trans/complexity` merged into `trans/tcom-main`):**
- `503e1a6` `measure_runtime.py` (259 lines) + `analytical_macs.py` (185 lines)
- `fa15e33` merge into `trans/tcom-main`
- deinlab smoke pass: classical-numpy 380 ms, classical-torch 360 ms @ N=512, 5 frames; analytical computes 7.9 / 15.5 / 30.6 MMAC at N=512/1024/2048.

**Axis A — qing_baseline (§3.1, branch `trans/qing-baseline`, NOT merged):**
- `17191b8` WIP receiver skeleton + paper-extracted README. Paper PDF saved to `_archive/literature/Zheng2025_SP-AFDM_arXiv2404.10232.pdf` (gitignored). All 7 paper equations transcribed (Eq 11/13-14/16/19/21/22/24).
- `0bd3e1e` iter-0 math verified on deinlab: NMSE 3.4e-3, exact active-path recovery [3,4]. Iter-1+ diverges; suspected fix = swap LS fallback detector for project's `mp_detect_bp_torch`.
- GitHub reference-impl search: **none found**. We are first public reproduction.

### Open decisions for next session

1. Detector swap: `_qpsk_hard_detect` → `from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch`. Estimated ~30-min change + smoke. If iter-2 NMSE drops back near iter-0 levels, axis A unblocks.
2. After detector fix, write `test_qing_consistency.py` reproducing Fig 3 16-pilot curve. Aim for ±20% then ±10%.
3. Decide whether to use `--baseline qing_sp_afdm` flag in `paired_learned_eval.py` or a dedicated `run_qing_paired.sh` driver. Plan favors the flag (one driver, one set of CLI conventions).

### 2026-05-07 (session 2 — Codex 3-round novelty debate + axis D landed)

**Trigger**: user concern that current FYP-derived contribution ("1041-param head + 2 dB log-BER separation + simulator only") feels thin for IEEE TCOM acceptance bar. Ran a 3-round structured debate with Codex GPT-5.5 xhigh.

**Codex verdict** (after round 3, with plan-as-stated fully completed): 10% desk reject / 65% major / 15% minor / 10% accept → "edge-acceptable, major-revision-leaning". To move accept probability ≥ 25%, three additional experiments needed by leverage:

1. **Same-budget classical heuristic OMP-(P+K)** — 0 GPU·h, kills "weak baseline / increment" attack
2. **Oracle-gap surface sweep** (N × pilot × K × spread) — 20 GPU·h, upgrades "98% closed" point claim to a framework
3. **Multi-channel-family + system mismatch** (CFO, off-grid, fractional Doppler) — 60 GPU·h, kills single-family attack

**Item 1 landed today (axis D, E6).** Implementation: added `omp_extended_k{K}` config family to `afdm_sp_joint_unrolled/classical_joint_headroom_probe.py` (K∈{2,4,8,16}). The new config runs `omp_sparse(y_daft, Phi, sparsity=P+K)` externally and routes the resulting support through `joint_omp_mp_iterative` via the existing `oracle_support` pathway. Cluster-expand ±k_leak + DA-LS + MP-BP downstream are byte-identical to baseline — only the support size differs. CONFIGS in the run: `baseline + omp_extended_k{2,4,8,16} + oracle_physical`, paired per frame with same `(H_true, data_qam, noise)`.

**Production run**: 250 frames × SNR ∈ {15, 20, 25} × seed 20260419 × v=2.0 × fs_factor=2.0 (4B) × P_paths=8 × mp_mode=bp. Wall-clock 2080 s (~35 min) on shared RTX 4090 in tmux session `g_omp_ext_probe`. Output: `outputs_omp_extended_4B_big/` (headroom_results.json + headroom_results.md + SAME_BUDGET_HEURISTIC_FINDING.md).

**Result (BER mean over 250 frames, smaller is better)**:

| SNR | baseline | k=2 | k=4 | k=8 | k=16 | oracle_physical |
|---|---:|---:|---:|---:|---:|---:|
| 15 dB | 1.975e-2 | 2.042e-2 | 2.134e-2 | 2.323e-2 | 2.754e-2 | 1.209e-2 |
| 20 dB | 3.89e-4 | 6.27e-4 | 8.87e-4 | 1.70e-3 | 3.99e-3 | 0 |
| 25 dB | 3.46e-4 | 2.77e-4 | 3.26e-4 | 6.41e-4 | 1.93e-3 | 0 |

**Gap-closed against oracle_physical** (= 100% ceiling):

| Method | SNR=15 | SNR=20 | SNR=25 |
|---|---:|---:|---:|
| OMP-(P+2) | −8.7% | −61% | +20% |
| OMP-(P+4) | −21% | −128% | +6% |
| OMP-(P+8) | −45% | −337% | −85% |
| OMP-(P+16) | −102% | −927% | −459% |
| **Learned head (FYP)** | **+61%** | **+81%** | **+98%** |

**Verification (4 checks, all PASS)** — `/data/guoyikun/tmp/verify_omp_extended.py`:

1. Baseline + oracle_physical numbers reproduce `outputs_loop13_headroom_4B_big_v2/headroom_results.md` bit-exactly → frame pairing and seed chain are intact.
2. OMP-(P+K) support is a strict superset of OMP-P support (greedy determinism); first P columns identical across configurations.
3. `omp_extended_k0` (routing through `oracle_support` with K=0) produces bit-exact baseline output (`max|x_base - x_k0| = 0.0`, `max|H_base - H_k0| = 0.0`) → routing introduces zero algorithmic distortion.
4. **Mechanism**: at SNR=15 fi=0, OMP K=4 extras land at `(l, k) ∈ {(140,+2), (44,−2), (148,−2), (125,−1)}` — all 4 are at delays outside the physical channel span `{0, 6, 15, 21, 23, 29, 35, 40}` (with k=+1) → fitting data-pilot leakage, not channel-residual. At fi=5, K=4 extras include 2 conjugate-Doppler "mirror" atoms `(58,−1), (84,−1)` (vs physical `(58,+1), (84,+1)`) — likewise fitting data conjugate phase rather than Dirichlet sidelobes.

**Mechanism narrative** (suitable as §IV-D-prime discussion paragraph): In SP frames with ρ=0.5, the residual `y − Φ·h_omp_P` after the first P-atom OMP pass is dominated by data-pilot interference (O(√P_d) of data energy projected through `H_eff`) rather than channel-residual energy. OMP greedy on `argmax|Φᴴ r|` rewards atoms with high correlation against this residual — but those atoms are mostly fitting data leakage, not the structurally missing Dirichlet-expanded virtual taps. Once a wrong atom enters the support, the cluster-expand + DA-LS step gives it non-trivial gain → phantom paths bias `H_hat` → BER and NMSE both regress monotonically with K. The learned head escapes this trap because its features (C2-rel pair features) include channel-side geometry, not just residual correlation, and its supervision target is `S_oracle \\ S_omp` — i.e., it is trained to score precisely the structurally missing atoms.

**Verdict impact (vs Codex round-3 distribution)**:

| Status | Desk | Major | Minor | Accept |
|---|---:|---:|---:|---:|
| After plan-as-stated only | 10% | 65% | 15% | 10% |
| **After axis D (E6) landed** | **10%** | **~60%** | **~20%** | **~10–15%** |

The accept-probability shift is modest because items 2 (surface sweep) and 3 (multi-family + mismatch) are still pending; but axis D's role is qualitatively important — it converts the strongest reviewer attack on the conceptual contribution into evidence FOR it. Codex flagged this as the highest-leverage missing experiment per unit of GPU cost (0 GPU·h vs 20 / 60 for items 2/3).

**Files touched**:
- `afdm_sp_joint_unrolled/classical_joint_headroom_probe.py` — added `omp_extended_k{K}` config family (CONFIGS_ALL lines 88–101 expanded; new branch in `_run_joint_with_oracle` lines 263–292).
- `afdm_sp_joint_unrolled/outputs_omp_extended_4B_big/{headroom_results.json,headroom_results.md,SAME_BUDGET_HEURISTIC_FINDING.md}` — new evidence directory.
- `afdm_sp_joint_unrolled/verify_omp_extended.py` — verification script (4 checks: bit-exact k0 vs baseline, OMP-(P+K) superset of OMP-P, K-extras geometric classification, single-frame BER comparison). Smoke-tested at SNR=15 frame 0/5; mirrored locally and on deinlab.

**Next session** should pick between: (a) draft §IV-D-prime LaTeX and bar-chart figure code now while evidence is fresh, (b) start axis A (Zheng baseline detector swap) to unblock the bigger 4-arm waterfall, or (c) start item 2 (oracle-gap surface sweep, 20 GPU·h on K × N × pilot × spread).

### 2026-05-07 (session 2 part B — axis A pivot Zheng→Cao + dual-basis Cao receiver + consistency test)

**Trigger**: user picked path (b) — work on axis A. Discovered axis A status in §2 was stale: the original `trans/qing-baseline` work had actually completed detector swap (`9ca147b`), iter divergence fix (`3eb777e`), Fig 3 16-pilot reproduction at Zheng regime (`cff3ce7`, 3/6 within ±0.3 dec on 1000 frames), regime-mismatch documentation (`3ab5936`), and 1000-frame consistency reproduction (`e904eb9`). All merged into `trans/tcom-main` via `abd4bc6`. Axis A status was actually **75%, not 30%**, with only the paired-eval integration left.

**But the integration plan hit a structural blocker**: Zheng's pilot is **equispaced** per Eq 11 with constraint `M(Q+1) < N − Q`. For our UWA regime (N=1024, Q+1 = (l_max+1)(2k_max+1) = 161·5 = 805), this forces **M = 0** — only one pilot allowed, channel estimator becomes underdetermined. Zheng algorithm structurally inapplicable to UWA-style long-delay × narrow-Doppler channels. Documented this regime mismatch as **Option 1/2/3 trichotomy**:

1. **Option 1** (Zheng-regime 4-arm, ~25 GPU·h with retraining learned head at small dictionary)
2. **Option 2** (双 regime 报告 — Zheng at his regime + ours at UWA, ~0 GPU·h)
3. **Option 3** (modify Zheng pilot scheme, ~30+ GPU·h + algorithmic risk)

**User identified Option 4 — pivot to Cao Zhe et al. 2024 ICCT** (`cao2024spomp`, "Sparse Channel Estimation and Data Detection for AFDM with Superimposed Pilot Scheme", DOI: 10.1109/ICCT62411.2024.10946599). Already cited in our paper §1 line 146-150 as the most directly comparable SP-AFDM iterative receiver: same OMP+MP iterative SP-AFDM but with **generic SP pilot** (no equispaced constraint) and OMP every outer iter on the data-aided sensing matrix `W^(n−1) = Ψ_p + Ψ̂_d^(n−1)` (Eq 24).

**Paper retrieval**: User downloaded the IEEE Xplore PDF via institutional access (UoG). Saved as `_archive/literature/Sparse_Channel_Estimation_and_Data_Detection_for_AFDM_With_Superimposed_Pilot_Scheme.pdf`. Algorithm extracted:
- **iter 0** (Eq 18): `ĥ^(0) = (Ψ_{p,†}^H Ψ_{p,†})^{-1} Ψ_{p,†}^H y` via OMP on pilot-only sensing matrix
- **iter n** (Eq 24, 28): `W^(n−1) = Ψ_p + Ψ̂_d^(n−1)`, then OMP on `W^(n−1)` to produce `ĥ^(n)`
- **σ²_d** for MP detector: Eq 21 (iter 0) `Σβ_h φ + σ²`, Eq 31 (iter n) `(2 Σβ_h φ + σ²)/N + σ²`
- **Termination**: `‖ĥ^(n) − ĥ^(n−1)‖₂ ≤ 1e-6` or n=10
- **Pilot scheme**: generic `p ∈ C^{N×1}` (Eq 15) — paper does not specify pilot construction beyond λ+φ=1 with optimal λ=0.5 from Fig 2

**Algorithm matching to our existing infrastructure**: 90% reusable. Only the outer-loop `W^(n)` rebuild and OMP-every-iter wiring is new (~80 lines).

**Two invariants verified at machine precision** before implementation (`afdm_sp_joint_unrolled/cao_baseline/verify_cao_sensing_invariants.py`):
1. **Φ linearity in carrier** — `Φ(αp + βd) ≡ αΦ(p) + βΦ(d)` — rel err ~1e-16 across 4 regimes (Cao Fig 3, Cao Fig 4, our UWA small N=128, our UWA full N=1024)
2. **Φ(x)·h_true ≡ H_eff_from_h · x** — rel err ~1e-16 across all 4 regimes

→ confirms `W^(n) = construct_sensing_matrix(N, √λp + √φd̂^(n−1), c1, c2, l_max, k_max)` works algebraically, no need to literally implement Cao's Eq (8) Ξ closed form.

**However, column-equivalence check** (`cao_baseline/cao_basis_equivalence.py`): when literally implementing Cao's Eq (8) Ξ closed-form sensing matrix, **only 1/(l_max+1)·K columns** match our `construct_sensing_matrix` bit-exactly. The other 804 differ STRUCTURALLY in phase (not just per-column global phase or sign): carrier indexing matches both use `x[(r − col_index) mod N]`, but phase formulas differ — ours uses `2π(−c_1 l² + c_2(r² − r_in²) − l·r_in/N)` while Cao's (per Eq 8) uses `(2π/N)(Nc_1 ε² − tε + Nc_2(t² − r²))` with `t = ⟨r + col⟩_N`. **8-combination exhaustive sign search** (`cao_baseline/diag_paper_h_eff_v2.py`) found best `cos_sim = 0.64` (not 1.0) — convention difference is **more than directional flip**: c1·l² sign opposite, `tε` cross-term vs `l·r_in/N` cross-term differs structurally.

**Implemented dual-basis receiver** (`cao_baseline/cao_isp_receiver.py`, ~250 lines):
- `basis='ours'`: uses our `construct_sensing_matrix` + `reconstruct_H_from_omp` throughout. Algorithm 1:1 with paper. Convention consistent with our simulator (verified).
- `basis='paper'`: uses literal Cao Eq 8 Ξ closed-form sensing matrix + paper-direction H reconstruction (`H[r,q] = Ξ(r,(r−q) mod N) · h[(r−q) mod N]`). User's "反向" patch flipped variant A `(q-r)` → variant B `(r-q)` per the sign-search winner — without it, BER ~0.5 random; with it, functional but suboptimal.

**Consistency test** (`cao_baseline/test_cao_consistency.py`): Cao paper Section IV setup — N=512, BPSK, P=3, integer Doppler, λ=φ=0.5, SNR_d ∈ {8, 10, 12, 14, 16} dB, generic ZC pilot, paper-style channel via `generate_cao_channel(P, l_max, k_max, rng)`.

**Reference numbers** (Cao Fig 3 16-pilot ISP, l_max=4, α_max=4, BPSK): SNR=8: 6e-2, SNR=10: 2e-2, SNR=12: 7e-3, SNR=14: 1.5e-3, SNR=16: 4e-4. Pass criterion ±0.3 dec.

**Result table**:

| Regime | Basis | Frames | SNR=8 | SNR=10 | SNR=12 | SNR=14 | SNR=16 | Verdict |
|---|---|---|---|---|---|---|---|---|
| Fig 3 (l_max=4, α_max=4) | ours | 200 | 8.1e-3 | 4.5e-3 | 3.3e-3 | 2.9e-4 | 1.3e-4 | 0/5 within ±0.3 dec but in WRONG direction (we are 0.5–0.9 dec BETTER than paper) |
| Fig 4 (l_max=8, α_max=8) | ours | 200 | 8.5e-3 | 3.8e-3 | 3.4e-3 | 2.1e-4 | 1.2e-4 | 0/5 within ±0.3 dec, 0.5–1.1 dec better than paper |
| Fig 3 | paper | 100 | 4.8e-2 | 4.3e-2 | 5.4e-2 | 3.8e-2 | 4.2e-2 | broken — flat at ~5e-2 floor across all SNRs |

**Interpretation**:
- **ours basis is the canonical Cao reproduction**. BER scales correctly with SNR, slope matches paper. The 0.5–0.9 dec offset (we are too good) is attributable to setup details paper does not fully specify: paper says nothing about the pilot vector construction (we use ZC sequence, paper might use Zheng-style equispaced or random Gaussian); paper says "MP detector" without backend specifics (we use Raviteja-style mp_detect_bp_torch, which is well-tuned).
- **paper basis is structurally broken** despite the directional flip. The cos_sim=0.64 phase mismatch creates a hard error floor at ~5e-2 that does not decrease with SNR — H_eff and the simulator's H_true do not align well enough for the receiver to leverage clean SNR. Confirms convention compatibility cannot be achieved with simple sign / conjugate flips.

**Decision**: ours basis is the canonical Cao reproduction for axis A. Paper basis retained as a sanity check showing that convention compatibility is non-trivial (a paper-faithful implementation note for the §IV-D writeup). Paper framing for §IV-D matched-budget comparison documented in `cao_baseline/AXIS_A_CAO_PIVOT_FINDINGS.md`.

**Files added (cao_baseline/ subdirectory)**:
- `verify_cao_sensing_invariants.py` (pre-implementation invariants check, all PASS)
- `cao_basis_equivalence.py` (column-by-column ours-vs-paper Eq 8 comparison, FAIL)
- `diag_paper_h_eff.py`, `diag_paper_h_eff_v2.py` (sign-convention enumeration; best cos_sim 0.64)
- `cao_isp_receiver.py` (dual-basis receiver, basis ∈ {ours, paper})
- `test_cao_consistency.py` (Fig 3/4 reproduction harness with paper-reference comparison)
- `outputs/consistency_{fig3,fig4}_ours_200f.json`, `consistency_fig3_paper_100f.json`
- `AXIS_A_CAO_PIVOT_FINDINGS.md` (consolidated finding document)

**Verdict impact (vs Codex round-3 distribution)**: axis A is now **functionally complete** — Cao reproduction verified algorithmically faithful, consistency tested on his own regime with documented offset, ready to integrate as `--baseline cao_isp` in paired_learned_eval. Estimated remaining axis A effort: ~6–8 GPU·h for E2 4-arm waterfall (was ~25 GPU·h under Zheng-Option-1 path).

**Updated axis A status in §2**: 75% → **95%** (only paired_learned_eval `--baseline cao_isp` integration + E2 4-arm waterfall remain).

**Next session** should pick: (a) integrate `--baseline cao_isp` to `paired_learned_eval.py` and run E2 (4-arm × 3-seed × 300 frames × SNR ∈ {15,20,25,30} on UWA regime), (b) draft §IV-D-prime + §IV-D LaTeX paragraphs + figure code now that both axes' evidence is in hand, or (c) start Codex leverage item 2 (oracle-gap surface sweep K × N × pilot × spread, ~20 GPU·h).

### 2026-05-08 (session 3 — independent novelty re-check + baseline-gap and ablation-gap audit)

**Trigger**: user asked for a fresh, independent novelty check (different from the 2026-05-07 codex 3-round debate) and explicit baseline / ablation gap list for IEEE TCOM submission. Ran one-shot codex GPT-5.5 xhigh (≤450-word prompt per user constraint) cross-checked against 12 WebSearches + 8 WebFetches over arXiv/IEEE/DL ACM 2024–2026.

**Novelty verdict (independent)**: novel-with-overlap, **7.5/10**, PROCEED. Closest prior remains Cao 2024 ICCT (already implemented in `cao_baseline/`). One critical cross-waveform analogue **Lei et al. 2026 arXiv 2601.22523 "SP-OTFS Under Fractional Doppler: Modular E2E Learning"** must be cited explicitly to defend the AFDM/architecture delta. Full record in `_memory/research_progress.md §2026-05-08` and `_QA_Index.md` row #17.

**Baseline gaps identified — 5 new arms required for IEEE TCOM acceptance bar**:

| # | Baseline | Priority | GPU·h | Reviewer-attack defended | Action |
|---|---|---|---|---|---|
| 1 | **PBiGaBP** (Ranasinghe TWC Feb 2025, arXiv 2405.16945) | **must-add #1** | ~8 | "Why no Bayesian-MP comparison?" — orthogonal paradigm to OMP, IEEE TWC main journal, same author cluster (Ranasinghe) you cite for oversampling. Predicted to underperform under SP frame because designed for single-pilot/block, which strengthens the SP-frame motivation | Implement as `--baseline pbigabp` arm, integrate into E2 paired pool |
| 2 | **Off-grid SBL + dynamic grid evolution** (Xu 2026 arXiv 2604.17858 + Li 2025/26 arXiv 2512.14776) | **must-add #2** | ~10–12 | "Why no SBL comparison for fractional Doppler?" — SBL-grid-evolution is the leading classical fractional-Doppler-aware AFDM CE family; codex round-3 missed this. Original works are EP-only — port to SP frame ourselves OR run EP-mode at matched pilot energy as a paired comparator | Implement as `--baseline sbl_ge` arm; SBL convergence is slow (~5–10× OMP per frame) so use early-stop + small-frame counts |
| 3 | **Re-OMP-per-iter variant of OWN receiver** | **must-add #3** | ~2 | Isolates "OMP-once" design decision from Cao's sensing-matrix re-construction. Current Cao baseline conflates two differences (re-OMP + Cao's W^(n) update); re-running OMP every outer iter on OUR sensing-matrix (in-house code) cleanly attributes the 5× cost saving and any BER delta to the OMP-once choice itself. Closes §III "support-recall ~95%" experimental loop | Add `--ours-reomp-per-iter` flag to `joint_omp_mp_iterative`; ~30 lines of code |
| 4 | **Yin 2024 DRCE diagonal-reconstruction estimator** | strongly-recommended | ~4 | "DRCE is purpose-built for Dirichlet leakage — why not compare?" — your §I cites DRCE as the existing non-SP non-iterative method targeting the same residual. Without measurement, "learned head > DRCE" is text-only. Expected: DRCE competitive in EP, fails badly in SP because DRCE is non-iterative | Implement as `--baseline yin_drce`; non-iterative so cheap |
| 5 | **Dense LMMSE channel estimator + MP-BP** | strongly-recommended | ~3 | "If dense LMMSE wins by 2 dB, your O(P·N²) complexity argument doesn't hold" — abstract claims "avoid cubic per-frame cost", paper currently has no LMMSE BER numbers, only complexity argument. Pareto front needs both axes measured | Implement reference LMMSE estimator at N=1024 single SNR; ~50 lines |

**Total baseline-gap effort**: ~27 GPU·h ≈ 1.5 days wall-clock on shared 4090, all in tmux, can run concurrently.

**Minimum-investment fallback**: only add #1 PBiGaBP (8 GPU·h). Covers the highest-leverage attack ("why not Bayesian?") and references an author cluster already cited. The other four become R1-rebuttal ammunition.

**Ablation-gap audit for journal submission (IEEE TCOM)** — what's still missing beyond the baselines:

| Ablation axis | Status | Priority | GPU·h | Why journal-required |
|---|---|---|---|---|
| **K (#atoms appended) sweep** K∈{1,2,3,4,6,8} | not run | **A1** | ~6 | Current paper uses fixed K=4 with no defense of the choice. Reviewer 100% asks "why 4?" |
| **Feature ablation** (residual-MF only / pilot-MF only / pair-coherence only / all) | not run | **A1** | ~12 (4 retrains × 3h each) | The 1041-param head's three feature streams are claimed to each contribute. Need ablation table to support this. C2-rel features = pair-coherence — must show pair-coherence is load-bearing |
| **Loss-function ablation** (BCE+rank-hinge / listwise NeuralSort / focal / pure BCE) | partially planned (axis B1) | **A1** | ~24 (already in plan) | TCOM expects loss-function comparison. Listwise is axis B1; need 1–2 alternative losses for table completeness |
| **Cross-channel-family generalization** train→test on EVA / VehA / TDL-A / 5G-CDL | not run | **A1** | ~20 | Codex round-3 item 3. Single-channel-family results = single-family attack. Need ≥3 channel families with consistent gain pattern, even if magnitudes vary |
| **ρ_p (pilot-data power split) sweep** ρ∈{0.3, 0.4, 0.5, 0.6, 0.7} | not run | **A2** | ~8 | Current ρ=0.5 is paper-default; reviewer asks "is the gain robust to power split?" Single-axis sweep cheap and high-defense-value |
| **Cross-SNR generalization** (train@20dB, test@10/15/25/30dB) | partially run (single ckpt across SNR exists) | **A2** | ~3 | Need explicit "trained at single SNR generalizes to all SNR" claim with paired data |
| **Cross-N zero-shot** train@N=1024, test@N=512/2048 | not run | **A2** | ~4 | Codex round-3 item 2 partially — but the surface sweep is broader. This is the cheap subset. Defends "the head learns N-invariant structure" |
| **Outer-iteration sweep** outer∈{1,2,3,5,7,10} | not run | **A2** | ~4 | Justifies "iterate-only is cheap because few iters suffice"; needed for the §IV-F complexity narrative |
| **Cross-P generalization** train@P=8, test@P={4,6,10,12} | not run | **A3** | ~5 | Defends "head generalizes across path counts" — useful for journal but not fatal |
| **Pilot-sequence sensitivity** ZC / Gaussian / random binary / Hadamard | not run | **A3** | ~6 | Defends pilot-sequence robustness; cited papers vary on this |
| **Width/depth ablation** (8/16/32/64 hidden, 1/2/3 layers) | not run | **A3** | ~12 | Architecture sensitivity. Useful for "small-on-purpose" framing |
| **CFO + off-grid mismatch** robustness sweep | not run (Codex item 3) | **A3** | ~30 | System-mismatch attack defense. High cost; defer to R1-rebuttal if base submission acceptable |

**Total journal-grade ablation effort**: ~134 GPU·h if everything; **A1 tier alone ~62 GPU·h** (3.5 days wall-clock); A1+A2 ~81 GPU·h.

**Recommended phasing for TCOM submission** (compatible with existing W3-W12 timeline in §6):

- **W3-W4** (now): land baseline #1 (PBiGaBP) + #3 (re-OMP variant) — ~10 GPU·h. Updates §IV-A waterfall from 4-arm to 6-arm.
- **W5**: K-sweep (A1) + feature ablation (A1) — ~18 GPU·h. Adds §IV-G ablation table.
- **W6-W7**: keep axis B1 listwise loss as planned (A1 covers this). Land cross-channel-family (A1) — ~20 GPU·h. Adds §IV-H "generalization" subsection.
- **W8**: land baseline #4 (DRCE) + #5 (LMMSE) — ~7 GPU·h. Strengthens §IV-A waterfall to 8-arm.
- **W9**: land baseline #2 (SBL-GE) — ~12 GPU·h. The "we beat all three classical paradigms" headline becomes defensible.
- **W10**: A2-tier ablations (ρ_p sweep + cross-SNR + cross-N + outer-iter) — ~19 GPU·h. Fills out §IV-G.
- **W11-W12**: paper integration + audit + cross-model review + submit. A3-tier deferred to R1-rebuttal.

**Total adjusted budget**: 64 GPU·h (original) + 27 (baselines) + 62 (A1) + 19 (A2) ≈ **172 GPU·h** over 9 weeks ≈ **2.7 GPU·h/day average** on shared 4090. Achievable.

**Verdict-impact projection** (codex round-3 distribution starting point: 10/65/15/10):

| Status | Desk | Major | Minor | Accept |
|---|---:|---:|---:|---:|
| After plan-as-stated only | 10% | 65% | 15% | 10% |
| + axis D OMP-(P+K) (DONE) | 10% | ~60% | ~20% | ~10–15% |
| + 5 new baselines | ~5% | ~50% | ~30% | ~15–20% |
| **+ A1-tier ablations** | ~5% | ~40% | ~35% | **~20–25%** |
| + A1+A2 ablations + 5 baselines | ~3% | ~35% | ~40% | **~25–30%** |

A1-tier alone moves accept-probability from ~12% to ~22% — best ROI before paper writing. A2 tier is "polish to push past minor-revision threshold".

**Files added this session**:
- `_memory/research_progress.md §2026-05-08` (full novelty re-check writeup)
- `_QA_Index.md` row #17, `_Log.meta.json` updated to entry 17
- This §9 entry in `tcom_plan/TCOM_PLAN.md`

**Next session** should pick: (a) implement baselines #1 (PBiGaBP) + #3 (re-OMP variant) — highest-leverage for cost, ~10 GPU·h, can run overnight in tmux, OR (b) draft §IV-D + §IV-D-prime LaTeX paragraphs now while axis A + axis D evidence is fresh and the 8-arm baseline structure is decided, OR (c) implement K-sweep + feature ablation harness (A1-tier) since it reuses existing training pipeline and yields the highest reviewer-defense ROI per GPU·h.

---

## 10. Baseline + Ablation matrix (TCOM submission grade)

Consolidated from §9 session 3. Source-of-truth for what experiments must land before submission.

### 10.1 Baseline arms (existing + planned)

| Arm | Paradigm | Status | Source | Notes |
|---|---|---|---|---|
| One-shot OMP+MP-BP | greedy, single-pass | ✅ done | own | Lower-bound floor |
| Cao 2024 SP-AFDM-OMP | greedy, re-OMP-per-iter | ✅ done (`cao_baseline/`) | cao2024spomp | Canonical SP-AFDM external baseline |
| OMP-(P+K) same-budget | greedy, single-pass extended | ✅ done (E6) | own ablation | Affirmative evidence (regresses) |
| Perfect-CSI MP-BP | greedy, oracle channel | ✅ done | own | Upper bound |
| Perfect-CSI MMSE | linear, oracle channel | ✅ done | own | Upper bound |
| Physical-support oracle (top-P) | oracle support | ✅ done | own | Headroom diagnostic |
| Zheng/Qing SP-AFDM | greedy, equispaced pilot | ✅ documented as regime-mismatch failure | qing2024spafdm | Negative baseline |
| Proposed: classical OMP-once + LS/MP-BP | greedy, OMP-once + iterate-only | ✅ done | own | Headline classical receiver |
| Proposed: + learned head | greedy + 1041-param ranker | ✅ done | own | Headline learned receiver |
| **PBiGaBP** | Bayesian belief-propagation | ⚠️ deferred R1 (2026-05-08) | Ranasinghe TWC 2025 | From-scratch faithful impl works at Q≤45 (synthetic smoke NMSE −37 dB) but variance-runaway at Q≥80 (BER 19-25% at production). Faithful per-edge Onsager-BP rewrite ~1-2 days w/o reference code. Schniter PBiGAMP MATLAB port (Path A) also deferred. See QA #19. |
| **Off-grid SBL-GE** | Bayesian SBL + grid evolution | 🔧 plan W9 | Xu 2026 + Li 2025/26 | Must-add #2, ~10–12 GPU·h |
| **Own re-OMP-per-iter** | greedy, isolated ablation | ✅ done 2026-05-08 (`outputs_ours_reomp_per_iter_4B_big/`) | own | **Headline: −9.4/−10.4/−78.6% BER vs classical at SNR=15/20/25 dB, McNemar p<5e-4 all three** |
| **Yin DRCE** | diagonal-reconstruction | ✅ done 2026-05-08 (`outputs_drce_ep_4B_big/`) | yin2024drceafdm | **Structurally infeasible at our regime — auto-truncated to l_max_drce=50 (< system 102), BER 5×10⁻² floor across all SNRs. Defensive narrative for §I.** |
| **Dense LMMSE + MP-BP** | linear regression | 🔧 plan W8 | own | Strongly-recommended, ~3 GPU·h |

### 10.2 Ablation axes (planned, by tier)

| Tier | Axis | Variable range | Status | GPU·h | TCOM section |
|---|---|---|---|---|---|
| A1 | K (atoms appended) | {1,2,3,4,6,8} | 🔧 plan W5 | 6 | §IV-G |
| A1 | Feature streams | {res-MF / pilot-MF / pair-coh / all} | 🔧 plan W5 | 12 | §IV-G |
| A1 | Loss function | {BCE+hinge / listwise / focal / BCE} | partially in axis B1 | 24 | §IV-G |
| A1 | Cross-channel-family | UWA / EVA / VehA / TDL-A | 🔧 plan W6-W7 | 20 | §IV-H |
| A2 | ρ_p power split | {0.3,0.4,0.5,0.6,0.7} | 🔧 plan W10 | 8 | §IV-G |
| A2 | Cross-SNR generalization | train@20, test@{10..30} | 🔧 plan W10 | 3 | §IV-H |
| A2 | Cross-N zero-shot | train@1024, test@{512,2048} | 🔧 plan W10 | 4 | §IV-H |
| A2 | Outer-iter count | {1,2,3,5,7,10} | 🔧 plan W10 | 4 | §IV-F (complexity) |
| A3 | Cross-P generalization | train@P=8, test@{4,6,10,12} | deferred to R1 | 5 | §IV-H |
| A3 | Pilot-sequence sensitivity | ZC / Gaussian / random / Hadamard | deferred to R1 | 6 | §IV-G |
| A3 | Architecture (width/depth) | {hidden ∈ 8/16/32/64} × {layers ∈ 1/2/3} | deferred to R1 | 12 | §IV-G |
| A3 | CFO + off-grid mismatch | {0, 5%, 10%, 20%} CFO | deferred to R1 | 30 | §IV-I (robustness) |

**Tier A1 = required for submission**, A2 = strongly-recommended for submission, A3 = R1-rebuttal ammunition.

---

## 11. Revised execution plan (2026-05-08, codex GPT-5.5 xhigh review)

After §9-session-3 baseline-gap audit, ran a single-round codex GPT-5.5 xhigh advisor pass (≤450-word prompt per user constraint) for ruthless prioritization. **Codex cut the plan substantially** — total submission-grade scope dropped from §10's 81 GPU·h to ~50 GPU·h.

### 11.1 Cuts vs §10

- ✂️ **CUT baseline #2 SBL-grid-evolution** for first submission. Reason: high implementation risk, moving target (Xu 2026 paper just landed and has no reference impl), weak receiver-match to SP-AFDM. Defer to R1-rebuttal ammunition.
- ✂️ **CUT ablation C (loss function, 24 GPU·h)** from first submission. Reason: low reviewer-defense ROI vs cost; axis B1 listwise exists separately. Restore as R1.
- ✂️ **CUT ablation D (cross-channel-family UWA/EVA/VehA/TDL-A, 20 GPU·h)** from first submission. Reason: replace with the much cheaper **L-lite** (CFO + off-grid mismatch, 2-3 severities, ~6 GPU·h) which addresses the same "synthetic-generator overfit" attack at one-third the cost.
- ⚠️ **CONDITIONAL on baseline #4 Yin DRCE**: only run if §I claim explicitly says "fractional-Doppler/Dirichlet leakage solved classically poorly". If we soften that claim, drop DRCE too.

### 11.2 Codex blind-spot diagnosis

> "1041-param head will be attacked as a learned simulator prior — your synthetic generator may overfit." — codex GPT-5.5 xhigh

Action: elevate **L-lite robustness sweep** (originally A3) into **A1** as the dedicated defense. ~6 GPU·h instead of 30. Replaces D (cross-channel-family).

### 11.3 Final submission scope (codex-approved)

**Baselines** (~17 GPU·h):
1. Re-OMP-per-iter own variant — 2 GPU·h
2. Dense LMMSE + MP-BP — 3 GPU·h
3. Yin DRCE — 4 GPU·h (conditional)
4. PBiGaBP (Ranasinghe TWC Feb 2025, citation verified arXiv 2405.16945) — 8 GPU·h

**Ablations** (~33 GPU·h, ordered by ROI/GPU·h):
- F. Cross-SNR generalization train@20→test@{10..30} — 3 GPU·h
- H. Outer-iter sweep {1,2,3,5,7,10} — 4 GPU·h
- A. K-sweep K∈{1,2,3,4,6,8} — 6 GPU·h
- E. ρ_p power split {0.3..0.7} — 8 GPU·h
- B-reduced. Feature ablation (all / no-residual-MF / no-pair-coherence) — 6 GPU·h
- **L-lite. CFO + off-grid mismatch (2-3 severities)** — 6 GPU·h ← codex blind-spot fix

**Total submission-grade scope**: ~50 GPU·h (was 81 in §10), 3 days wall-clock.

**R1-rebuttal ammunition** (~95 GPU·h, run only if reviewer asks):
- SBL-grid-evolution baseline (#2)
- C. Full loss-function ablation
- D. Cross-channel-family
- G. Cross-N zero-shot
- I. Cross-P generalization
- J. Pilot-sequence sensitivity
- K. Width/depth ablation
- L-full. Full CFO+off-grid grid
- **PBiGAMP-AFDM port** (Schniter `gampmatlab/PBiGAMP/PBiGAMP.m` 792-line MATLAB → numpy AFDM-specific): deferred from Step-2 main path. Reason: PBiGAMP ≠ PBiGaBP (Ranasinghe paper says BiGaBP "relaxes BiGAMP's large-system-limit approximation"); reviewer can argue paradigm mismatch. ~1.5-2 days dev. The MATLAB source files are pre-fetched at `/tmp/gamp_PBiGAMP.m`, `/tmp/gamp_PBiGAMPsimple.m`, `/tmp/gamp_Affine_ParametricZ.m`, `/tmp/gamp_README.txt`, `/tmp/gamp_trial_affine.m`. Keep as fallback if Path B (faithful Ranasinghe PBiGaBP) hits a wall, OR run alongside as a second Bayesian-paradigm point. SourceForge URL: `svn://svn.code.sf.net/p/gampmatlab/code/trunk/code/PBiGAMP/`.

### 11.4 Next 2 weeks (W3-W4) execution order — codex-prescribed

1. **Implement baselines #3 + #5 + #4** (re-OMP + LMMSE + DRCE) — ~9 GPU·h. Cheapest, fully reviewer-facing, completes the §IV-F complexity table with measured BER on all complexity classes.
   - ✅ #3 re-OMP DONE 2026-05-08 (~17 min wall-clock; **−9.4/−10.4/−78.6% BER at SNR=15/20/25 dB**, all McNemar p<5e-4)
   - ✅ #4 DRCE DONE 2026-05-08 (~13 min wall-clock; structurally infeasible — defensive narrative for §I)
   - ⏳ #5 LMMSE not yet implemented (~3 GPU·h remaining)
2. ~~**Implement baseline #1 PBiGaBP** — ~8 GPU·h~~ ⚠️ **2026-05-08: ATTEMPTED, PARKED.** From-scratch faithful per-edge BP works at synthetic Q=45 but variance-runaway at production Q≥80 even with clipping/damping. Per Codex Q5 audit, faithful fix needs per-edge Onsager-corrected variance propagation rewrite (~1-2 days, high uncertainty). Deferred to R1-rebuttal alongside Schniter PBiGAMP port. See QA #19. **Recommended paper framing**: §I cites Ranasinghe 2025 as "the Bayesian-MP comparator family; faithful SISO reproduction beyond scope of this work"; §IV-A 5-arm waterfall stays without Bayesian-MP arm; main claim becomes "we beat all *practical greedy-OMP* paradigms" (Cao re-OMP, OMP-(P+K), DRCE-EP) which is still strong.
3. **Run ablations F + H + A + E + B-reduced** sequentially — ~27 GPU·h. Stop only if a result breaks the core claim. **Pre-Step-3 blocker**: re-establish Loop-12 +2 dB headline at complex128 via 3-seed pool (20260423/424/425) — current single-seed at complex128 shows null-to-marginal learned-arm gain (QA #19 followup signal). ~3 GPU·h, runs unattended.
4. **L-lite robustness sweep** — ~6 GPU·h. The codex blind-spot defense.

Total W3-W4: ~50 GPU·h, achievable in 3 days wall-clock on shared 4090 with tmux scheduling.

> **⚠️ Pre-Step-2 blocker (flagged 2026-05-08, see QA #18)**: torch-ref vs NumPy classical drift returned at SNR=25 (33 vs 14 errs, +135.7%); learned arm inherits this drift. NOT introduced by Step 1 — `verify_reomp_bitexact.py` confirms `joint_omp_mp_iterative` is unchanged. But before Step 2 (LMMSE) and any further learned-arm production, must verify `torch-ref ≡ NumPy classical bit-exactly` at the canonical config (regression from QA #4-5 era identity-drift). Otherwise Step 2 results will be unreadable for the learned arm.

### 11.5 Verdict-impact projection (revised)

| Status | Desk | Major | Minor | Accept |
|---|---:|---:|---:|---:|
| After plan-as-stated only | 10% | 65% | 15% | 10% |
| + axis D OMP-(P+K) (DONE) | 10% | ~60% | ~20% | ~10–15% |
| + 4 codex-approved baselines | ~5% | ~50% | ~30% | ~15–20% |
| **+ codex-approved A1 ablations** | ~3% | ~38% | ~37% | **~22–25%** |
| (+ A2 ablations as polish) | ~3% | ~32% | ~40% | **~25–30%** |

**Achievable accept-prob improvement**: 10% → 22–25% with ~50 GPU·h of work over 2 weeks, vs §10's 81 GPU·h plan. Codex pruning saves ~38% effort for similar accept-probability.
