# Paper Plan — TMLCN submission

**Title**: Faithful Differentiable Unrolling of Joint OMP--MP Receivers for Superimposed-Pilot AFDM: A Complexity-Honest Learned Support-Refinement Head
**Venue**: IEEE_JOURNAL (IEEE TMLCN — Trans. on Machine Learning in Communications and Networking)
**Type**: empirical methodology paper with theory cross-check (initialization-faithful theorem)
**Date**: 2026-05-16
**Page budget**: 12 pages double-column IEEEtran journal (with overlength allowed up to ~14)
**Section count**: 6 main sections + appendix
**Plan source**: `tcom_plan/TMLCN_PLAN.md` (full venue rationale, risk register)
**Content inventory**: `tcom_plan/CONTENT_INVENTORY.md` (FYP + post-FYP source map)
**Base paper**: FYP at `paper/` (carry-over: ~70% of body, ~10% of preamble; READ-ONLY)
**Backup venue**: TVT (see `tcom_plan/TVT_PLAN.md`)

---

## Constraints (binding)

- **No new experiments** — all results live in `outputs_*/results.json` + `paper_figure_code/` JSONs. Per-result `_argv` + `_config` reproducibility fingerprint enforced (QA #26 patch).
- **Bibliography extend-only** — `paper/references.bib` has 49 entries. Add ~7 new entries for learned/unrolled receivers (DetNet, OAMPNet, GENIUS, MMNet) and sparse-recovery unrolling (LISTA, ALISTA). Never modify existing entries.
- **Submission assurance level** — gated by `tools/verify_paper_audits.sh`; the 3 mandatory audits (proof-checker, paper-claim-audit, citation-audit) must each emit `verdict ∈ {PASS, NOT_APPLICABLE}` before the Final Report.
- **Page compression** — current FYP carry-over compiles to 24 pages single-column IEEEtran journal. Twocolumn re-flow + section restructuring + figure regen targets 12 pages.

---

## Claims-Evidence Matrix

| Claim | Evidence | Status | Section |
|---|---|---|---|
| **C1** 5-seed mean BER reduction at 20/25/30 dB is paired-significant (paired bootstrap, 95% CI excludes 0) | Phase 3 width-MLP 5-seed retrains (commits `eb75db8`, `430e1a4`) | Supported | §V-B |
| **C2** Cao 2024 SP-AFDM baseline reproduced within ±10% of published BER on UWA-style channel | E2 (Cao baseline, 95% impl done; paired pool pending) | Partial — pending E2 finish | §V-A |
| **C3** Unrolled receiver + learned head beats Cao 2024 by paired McNemar p < 1e-3 at SNR=25/30 dB | E1 + E2 | Pending E2 | §V-A |
| **C4** Per-candidate attribution shows ≥60% of added atoms target Dirichlet sidelobes (causal mechanism) | E4 mechanism attribution (commit `be65eed`, draft `_IV_E_attribution.md`) | Optional / appendix | §V-D or appendix |
| **C5** Wall-clock at N=1024 within 2× classical-unrolled; analytical MAC in same asymptotic class | E5 complexity table (`draft_section_IV_F_complexity.md`, profiling commits) | Supported | §V-E |
| **C6** Support recall ≥95%, gap-closed 61/81/98% across SNR=15/20/25 dB (FYP carry-over) | `outputs_loop13_*` results JSON | Supported | §V-A, §V-C |
| **C7** Single-pass OMP-(P+K) does NOT close oracle-physical gap; for K≥4 regresses monotonically — learned head's gain is non-linear support-refinement, not budget | E6 OMP-(P+K) sweep `outputs_omp_extended_4B_big/` | Supported | §V-A.2 |
| **C8** Complexity audit is reviewer-attack-proof: eq (23) actually omits DA-LS; fair P=18 unrolled is worse than P=10 unrolled; tau_lookup yields free 11% MAC reduction | QA #44 audit (commit `7e886a3`) | Supported | §V-E |
| **C9** Differentiable unrolling is **initialization-faithful**: at random init, end-to-end output matches classical NumPy implementation bit-exactly | `verify_classical_unrolled_matches_numpy.py` (verifier, deterministic) | Supported (computational, not analytical) | §III + Theorem 1 |

---

## Structure (12-page IEEEtran double-column target)

### §I Introduction (~1.5 pp)
- **Opening hook**: doubly dispersive doubly selective channels (UWA + high-mobility wireless) defeat conventional OFDM; AFDM with superimposed pilots restores spectral efficiency but the one-shot OMP-MP receiver is estimation-limited at mid-to-high SNR.
- **Gap (TMLCN-positioned)**: existing learned receivers for AFDM are (a) not initialization-faithful to the classical algorithm (random init does not recover classical behavior), (b) do not honestly account for MACs/wall-clock/memory, and (c) conflate "more atoms in support" with "better support ranking."
- **Approach**: faithful differentiable unrolling of joint OMP + DA-LS + sparse MP-BP + 1 041-parameter learned support-refinement head; same-budget classical heuristic comparator (OMP-(P+K)) confirms gain is non-linear.
- **Contributions** (5 bullets):
  1. Faithful differentiable unrolling with initialization-faithful theorem (C9)
  2. 1 041-parameter learned support-refinement head, complexity-class-preserving (C5, C8)
  3. 5-seed retraining envelope with paired McNemar significance (C1)
  4. Same-budget classical heuristic comparator OMP-(P+K) (C7)
  5. Reviewer-attack-proof complexity audit (C8)
- **Hero figure**: 4-arm waterfall (serial / classical / Cao 2024 / learned head) with oracle headroom dashed line.
- **Source**: FYP `paper/sections/Section1.tex` lines 1–~100 (motivation + AFDM background); rewrite contributions paragraph.

### §II Related Work (~1 pp)
- **2A** AFDM modulation, SP-AFDM channel estimation, OMP/MP joint receivers (Bemani 2023, Benzine 2023, Cao 2024) — FYP lit-survey carry-over
- **2B** **NEW** Learned / unrolled receivers for OFDM/OTFS (DetNet, OAMPNet, GENIUS, MMNet) — emphasize: most do not preserve initialization-classical-equivalence and do not report comparable complexity audits
- **2C** **NEW** Sparse-recovery deep unrolling (LISTA, ALISTA) — emphasize: our head is per-candidate attribution over a frozen OMP-derived candidate pool, not LISTA-style end-to-end matrix learning
- **Source**: FYP `Section1.tex` lines ~100–~365 (literature survey) + ~7 new bib entries

### §III System Model & Differentiable Unrolling (~2 pp)
- **§III-A** Signal + channel model (SP-AFDM frame, doubly selective channel, Dirichlet-expanded virtual taps, sparse representation)
- **§III-B** Classical joint OMP + DA-LS + sparse MP-BP iteration (algorithm box)
- **§III-C** Differentiable unrolling: PyTorch vectorization, autograd-friendly atom selection, candidate pool construction
- **§III-D** **NEW (Theorem 1, computational)** Initialization-faithful theorem: at random head init, end-to-end output ≡ classical NumPy output bit-exactly. **Proof**: deferred to appendix; sketch references `verify_classical_unrolled_matches_numpy.py` as the verifier
- **§III-E** Learned support-refinement head: architecture (1041 params), C2-rel + F2-P feature design, plug-in slot after each OMP step
- **Source**: FYP `Section2.tex` (system + classical algorithm) + `Section3.tex` (head architecture); add ~0.3 pp for Theorem 1

### §IV Training Objective & Protocol (~1 pp)
- **§IV-A** BCE on per-candidate active/inactive labels + ranking auxiliary loss
- **§IV-B** Width-MLP architecture choice (Phase 3 finding: width dominates, attention not additive; SoftSort top-K not additive)
- **§IV-C** Multi-seed training protocol (5 seeds, paired-frame data generation); SNR-weighted training pitfalls (W8 ablation finding `853307e`)
- **Source**: FYP `Section3.tex` end + Phase 3 commits

### §V Experiments (~5 pp, biggest writing load)
- **§V-A Waterfall and baselines** (~1.5 pp)
  - §V-A.1 4-arm waterfall: serial-OMP / classical-joint / Cao 2024 SP-AFDM / learned head; SNR sweep with paired McNemar p-values
  - §V-A.2 Same-budget classical heuristic OMP-(P+K): K ∈ {2,4,8,16} regresses monotonically — gain is non-linear (C7)
  - §V-A.3 Sampling-rate sensitivity: fs=4B paper-defensible (fs=2B 2.4× worse, commit `aee25ae`)
  - TABLE: 4-arm BER + McNemar p-values
- **§V-B Multi-seed retraining envelope** (~0.7 pp)
  - 5-seed width-MLP retrains; bootstrap 95% CI
  - FIGURE: BER envelope across 5 seeds, error bars
- **§V-C Depth ablation** (~0.7 pp)
  - Path F K ∈ {5, 10, 20}: K=10 = O(sparsity) is right; K=20 marginal returns
  - FIGURE: BER vs K, oracle headroom dashed line
- **§V-D Mechanism attribution** (~0.5 pp, optional / appendix)
  - Per-candidate atom classification: ≥60% target Dirichlet sidelobes (if E4 lands; else demote)
- **§V-E Complexity audit** (~1 pp, load-bearing)
  - Wall-clock table N ∈ {512, 1024, 2048} × 3 receivers (`draft_section_IV_F_complexity.md`)
  - QA #44 audit: eq (23) omits DA-LS, fair P=18 worse than P=10, tau_lookup free 11% MAC
  - TABLE: wall-clock + memory; TABLE: analytical MACs
- **Setup paragraph** (start of §V, ~0.3 pp): reproducibility (per-result `_argv` + `_config`), channel parameters, hardware

### §VI Discussion & Conclusion (~1 pp)
- Limitations: UWA simulator family; no real-data; single GPU class; UWA channel-model specifics not validated against real hydrophone traces
- Future work: MSML, real-data UWA, transfer to terrestrial high-mobility wireless
- **Source**: FYP `Section5.tex` (skeleton carry-over, rewrite conclusion for TMLCN-positioning)

### Appendix
- Initialization-faithful theorem (Theorem 1) proof outline
- Mechanism attribution detail (if demoted from §V-D)
- QA #44 complexity audit full breakdown
- **Source**: FYP `Appendix.tex` carry-over + new content

---

## Figure Plan

Per `CONTENT_INVENTORY.md` §C — figure regen is **single-column → double-column re-layout**, plus 3 new figures from post-FYP results.

| # | Figure | Type | Source data | Status |
|---|---|---|---|---|
| 1 | 4-arm BER waterfall (Hero, §V-A.1) | Plot | `outputs_loop13_*/results.json` + `outputs_cao_baseline_*` | regen for 2-col |
| 2 | OMP-(P+K) same-budget heuristic (§V-A.2) | Bar chart | `outputs_omp_extended_4B_big/results.json` | regen for 2-col |
| 3 | fs sensitivity (§V-A.3) | Plot | `paper_figure_code/outputs_phase4_2B/*.json` | NEW |
| 4 | 5-seed BER envelope (§V-B) | Plot w/ CI | Phase 3 5-seed retrains | NEW |
| 5 | Depth ablation K∈{5,10,20} (§V-C) | Plot | `paper_figure_code/outputs_pathF_K*/*.json` | NEW |
| 6 | Mechanism attribution (§V-D, optional) | Pie/bar | `commit be65eed` outputs | regen |
| T1 | 4-arm BER + McNemar p-values | Table | from waterfall data | regen |
| T2 | Wall-clock + memory (§V-E) | Table | `draft_section_IV_F_complexity.md` | regen |
| T3 | Analytical MACs (§V-E) | Table | QA #44 audit | NEW |

**No architecture diagrams needed** — §III-B has algorithm pseudocode block; no system-block figure required for TMLCN brevity.

---

## Citation Scaffolding

Existing `paper/references.bib`: 49 entries. **Extend-only** addition (~7 entries):

- **Learned receivers (§II-2B)**:
  - DetNet (Samuel & Diskin & Wiesel 2017 / 2019)
  - OAMPNet (He, Wen, Jin 2018 / 2020)
  - GENIUS (deep unfolding receivers — fill with primary AFDM/OTFS-learning paper)
  - MMNet (Khani, Alizadeh 2020)
- **Sparse-recovery unrolling (§II-2C)**:
  - LISTA (Gregor & LeCun 2010)
  - ALISTA (Liu, Chen, Wang, Yin 2019)

Cross-validate at Phase 5.8 `/citation-audit`.

---

## Stale-file cleanup (before Phase 3)

The FYP carry-over in `paper-tmlcn/sections/` contains thesis-specific subsections that will not survive IEEEtran rewriting:
- Long `\subsection{Background and motivation}` headings (collapse to `\IEEEPARstart{}` lead paragraph)
- FYP-specific bibliographic style references to UoG/UESTC supervisors (already excluded — they live in `paper/main.tex` only, not in section files)
- Section5 FYP conclusion structure (bullet list of grade-relevant achievements) → rewrite as TMLCN-style discussion

---

## Pipeline output expectations

After full pipeline:
- `paper-tmlcn/main.pdf` — ≤12-14 pages, IEEEtran twocolumn journal
- `paper-tmlcn/PAPER_PLAN.md` — this file (kept for audit trail)
- `paper-tmlcn/sections/*.tex` — TMLCN-rewritten (§I–§VI)
- `paper-tmlcn/figures/*.pdf` — regenerated double-column figures
- `paper-tmlcn/references.bib` — original 49 + ~7 new entries (extend-only)
- `paper-tmlcn/PROOF_AUDIT.{md,json}` — initialization-faithful theorem check (NOT_APPLICABLE if no other theorems)
- `paper-tmlcn/PAPER_CLAIM_AUDIT.{md,json}` — every numeric claim traces to results.json
- `paper-tmlcn/CITATION_AUDIT.{md,json}` — bib entry existence/metadata/context check
- `paper-tmlcn/KILL_ARGUMENT.{md,json}` — adversarial gate (scope hint = "across regime shifts" present)
- `paper-tmlcn/.aris/audit-verifier-report.json` — submission verifier final report (must exit 0)
- `paper-tmlcn/PAPER_IMPROVEMENT_LOG.md` — round 0/1/2 improvement loop log
- `paper-tmlcn/main_round{0,1,2}.pdf` — pre/post-improvement comparison PDFs

---

## Cross-references
- [tcom_plan/TMLCN_PLAN.md](../tcom_plan/TMLCN_PLAN.md) — full venue rationale
- [tcom_plan/CONTENT_INVENTORY.md](../tcom_plan/CONTENT_INVENTORY.md) — source-content map
- [tcom_plan/TVT_PLAN.md](../tcom_plan/TVT_PLAN.md) — backup venue plan
- [paper/sections/Section{1..5}.tex](../paper/sections/) — FYP carry-over LaTeX (READ-ONLY)
