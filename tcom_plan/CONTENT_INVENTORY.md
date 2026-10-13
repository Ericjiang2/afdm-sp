# CONTENT_INVENTORY.md — FYP + post-FYP material → TMLCN sections

**Purpose**: Single source of truth mapping every piece of existing content (LaTeX, markdown drafts, results JSON, commits) to the **TMLCN target paper sections** (per [TMLCN_PLAN.md](./TMLCN_PLAN.md) §5).

**Status as of 2026-05-16**: FYP closed (tag `fyp-final`, weighted 86.7 / A5). Post-FYP work merged onto `trans/tcom-main` HEAD = `7e886a3`. **No new GPU experiments needed for TMLCN submission** — all data exists.

---

## A. Source-of-truth catalog

### A.1 FYP committed LaTeX (`paper/`)

| File | Lines | TMLCN dest | Reuse fraction | Notes |
|---|---:|---|---:|---|
| `paper/main.tex` | 200 | `paper-tmlcn/main.tex` | 10% | Header (class, geometry, hyperref, GUID, supervisor) is FYP-specific — **rewrite from scratch** as IEEEtran. Body `\input{sections/...}` skeleton carries over |
| `paper/sections/Abstract.tex` | 44 | `paper-tmlcn/sections/Abstract.tex` | 30% | Rewrite for TMLCN: lead with ML methodology contribution, shrink to ~200 words |
| `paper/sections/Section1.tex` | 365 | `paper-tmlcn/sections/Section1.tex` (Intro+Related Work) | 70% | Strong base — UWA pathology + AFDM motivation + SP framing all carry over. Add: 2B subsection on learned/unrolled receivers; rewrite Contributions bullet list per TMLCN_PLAN.md §1 |
| `paper/sections/Section2.tex` | 276 | `paper-tmlcn/sections/Section2.tex` (System & Classical Algorithm) | 90% | System model + classical OMP-MP-BP algorithm — minimal edits, just notation polish |
| `paper/sections/Section3.tex` | 224 | `paper-tmlcn/sections/Section3.tex` (Differentiable Unrolling + Learned Head) | 85% | Method description carries over. Add: 1-paragraph "initialization-faithful theorem" (C9) pointing at `verify_classical_unrolled_matches_numpy.py` |
| `paper/sections/Section4.tex` | 142 | `paper-tmlcn/sections/Section4.tex` (Experiments — base content) | 50% | E1 waterfall + support recall + gap-closed carry over; need to integrate post-FYP additions (E2 Cao, E6 OMP-(P+K), E7 K-ablation, E8 fs sweep, E3 5-seed envelope) |
| `paper/sections/Section5.tex` | 25 | `paper-tmlcn/sections/Section5.tex` (Discussion + Conclusion) | 40% | Skeleton OK, rewrite for TMLCN positioning |
| `paper/Appendices/Appendix.tex` | — | `paper-tmlcn/Appendix.tex` (optional) | 80% | Move mechanism-attribution + QA #44 audit detail here if main paper overflows |

**Total FYP LaTeX carry-over**: ~70% of body text, ~10% of preamble.

### A.2 Post-FYP markdown drafts (`tcom_plan/`)

| File | Status | TMLCN dest |
|---|---|---|
| `tcom_plan/TCOM_PLAN.md` | living plan, 80% executed | Reference only (TMLCN_PLAN.md supersedes for venue framing) |
| `tcom_plan/TMLCN_PLAN.md` | **THIS PLAN (primary)** | — |
| `tcom_plan/TVT_PLAN.md` | backup plan | — |
| `tcom_plan/CONTENT_INVENTORY.md` | **THIS FILE** | — |
| `tcom_plan/draft_section_IV_B_listwise_capacity.md` | draft | Folded into §V-B (multi-seed envelope) — width-MLP replaced listwise as primary, see commit `eb75db8` |
| `tcom_plan/draft_section_IV_E_attribution.md` | draft | §V-D (mechanism attribution) — **demoted to appendix** for TMLCN per TMLCN_PLAN.md §5 |
| `tcom_plan/draft_section_IV_F_complexity.md` | strong draft (incl. wall-clock table, analytical MACs) | §V-E (complexity audit) — promoted; integrate QA #44 audit |
| `tcom_plan/W8_complexity_reduction_plan.md` | plan | reference for §V-E narrative |
| `tcom_plan/W8_1_distillation_results.md` | negative result | §V-D or appendix (W8 #1 distillation iter=10→3 KILL) |
| `tcom_plan/W8D_round0_results.md` | negative result | §V-D or appendix (learnable c1/c2 negative — Bemani chirp locally optimal) |
| `tcom_plan/E2E_phase{1,2,3,4}_*.md` | results | §V-C depth-ablation source material |
| `tcom_plan/E2E_phase4_2B_results.md` | strong result | §V-A.3 fs sensitivity subsection |
| `tcom_plan/A2_crossN_results.md` | result | §V-D asymmetric generalization (or appendix) |
| `tcom_plan/E2E_ladder_results.md` | negative result | mechanism analysis context (§V-D appendix) |
| `tcom_plan/TCOM_RESPONSE_TEMPLATE.md` | response template | future rebuttal (not for submission) |

### A.3 Post-FYP commits (`trans/tcom-main` branch, since `fyp-final` tag)

Grouped by content area:

**Group 1: Phase 3 — width-MLP / learned-head SOTA (Phase 3 closure)**
- `eb75db8` Phase 3 closure: width-MLP dominates, attention not additive, BER 0.0355 SOTA
- `430e1a4` Phase 3 amendment +Path H softsort top-K (F11 negative)
- **TMLCN dest**: §IV training; §V-B 5-seed envelope claim C1; §V-D attribution (optional)

**Group 2: Phase 4 — fs sensitivity (paper-defensibility)**
- `aee25ae` Phase 4 2B sweep: fs=2B is 2.4× WORSE than 4B
- **TMLCN dest**: §V-A.3 fs sensitivity subsection

**Group 3: Path F — unrolled OMP-Net depth (single-pass ceiling)**
- `865e7ea` Path F+ K=20 ablation — confirms K=O(sparsity) ≈ 10
- `ec5bd08` E2E Path F: Unrolled OMP-Net K=10 + curriculum breaks ceiling
- `7420d18` E2E phase 2: matched-filter inductive bias + curriculum
- **TMLCN dest**: §V-C depth ablation; supports C9 initialization-faithful (unrolled = classical at K large)

**Group 4: Complexity audit (QA #44 reviewer-attack-proof)**
- `7e886a3` QA #44 recv complexity audit: eq (23) omits DA-LS, fair P=18 worse than P=10, tau_lookup free 11% MAC
- **TMLCN dest**: §V-E complexity table + claim C8

**Group 5: Baseline integration**
- `61a5429` integrate Cao/DRCE/LMMSE/PBiGaBP baselines
- `0253e09` profiling: §IV-F runtime evidence (50 frames × 3 receivers × 3 N)
- `d77de48` profiling: integrate Zheng 2025 receiver
- **TMLCN dest**: §V-A waterfall + §V-E runtime table

**Group 6: Threshold-gate / hard-decision route**
- `8c5beaf` threshold-gate: --use-hard finds real BER improvement (SNR=20, p=0.046)
- **TMLCN dest**: §V-A waterfall (one extra arm) or §V-D mechanism

**Group 7: Forensic reproducibility (CLAUDE.md QA #23-26 lessons)**
- `ff81141` paired_learned_eval: capture _argv + full head-config flags in results.json
- `8ebf798` verify scripts + 3seed POOL summary
- `ba81864` forensic: paper iter=5 -48% fully reproducible (F2-P flags from bash_history)
- **TMLCN dest**: not in paper directly; supports reproducibility statement in §V-A setup paragraph

**Group 8: FYP archive + paper TCOM rewrite scaffold**
- `fe8aa49` paper TCOM rewrite + FYP archive + memory log catch-up
- **TMLCN dest**: scaffold for the new `paper-tmlcn/` worktree

### A.4 Results JSON sources (paper-cited numbers)

All `paper_figure_code/` + `outputs_*/` JSONs are committed (CLAUDE.md `.gitignore` whitelist). For each headline number in the TMLCN paper, the source JSON must be traceable via the per-result `_argv` + `_config` reproducibility fingerprint enforced by `paired_learned_eval.py` (QA #26 patch).

Key paper-cited JSONs (must remain immutable through submission):
- `afdm_sp_joint_unrolled/outputs_loop13_4B_retrain27k_snr25_eval/results.json` — Phase 3 SOTA BER 0.0355
- `outputs_omp_extended_4B_big/results.json` — E6 OMP-(P+K) negative result
- `outputs_loop13_headroom_4B_big_v2/results.json` — oracle headroom reference
- `paper_figure_code/outputs_phase4_2B/*.json` — fs=2B-vs-4B comparison
- `paper_figure_code/outputs_pathF_K*/*.json` — depth ablation
- `paper_figure_code/runtime_table.csv` (or JSON) — §V-E complexity table

→ **No new GPU runs needed for TMLCN** unless E2 (Cao baseline) paired pool finishes after submission deadline.

---

## B. TMLCN section → source-content map (reverse index)

For each TMLCN section, the **complete list** of input sources:

### §I Introduction (~1.5 pp)
- FYP `Section1.tex` lines 1–~100 (background, motivation, gap)
- TMLCN_PLAN.md §1 (Headline claim) → contributions paragraph
- Claims C1–C9 (TMLCN_PLAN.md §4) → 5-bullet contribution list

### §II Related Work (~1 pp)
- FYP `Section1.tex` lines ~100–~365 (literature survey)
- **NEW writing**: 2B learned/unrolled receivers (cite DetNet, OAMPNet, GENIUS, MMNet — 4–5 new bib entries needed); 2C sparse-recovery unrolling (LISTA, ALISTA — 2 new bib entries)

### §III System & Differentiable Unrolling (~2 pp)
- FYP `Section2.tex` (system model + classical OMP-MP-BP algorithm) — 90% reuse
- FYP `Section3.tex` (learned head architecture, feature design) — 85% reuse
- **NEW writing**: initialization-faithful theorem subsection (~0.3 pp); points at `verify_classical_unrolled_matches_numpy.py`

### §IV Training Objective & Protocol (~1 pp)
- FYP `Section3.tex` end (BCE + ranking loss)
- Post-FYP commits Group 1 (Phase 3 width-MLP findings) — width dominates, attention not additive
- W8 ablation findings: SNR-weighted training is regime-dependent (commit `853307e`)
- **NEW writing**: combine FYP training + Phase 3 width-MLP best-practices into single coherent section

### §V Experiments (~5 pp, biggest writing load)

**§V-A Waterfall and baselines (~1.5 pp)**
- E1 (FYP `Section4.tex` waterfall) — base content
- E2 Cao 2024 SP-AFDM baseline (commits Group 5, 95% done; E2 paired pool pending)
- **§V-A.2 same-budget classical heuristic**: E6 OMP-(P+K) result (commit `8c5beaf` and related)
- **§V-A.3 fs sensitivity**: Phase 4 fs=2B vs fs=4B (commit `aee25ae`, draft `E2E_phase4_2B_results.md`)
- TABLE: 4-arm comparison + paired McNemar p-values

**§V-B Multi-seed retraining envelope (~0.7 pp)**
- Phase 3 5-seed width-MLP retrains (commits Group 1)
- 95% CI from bootstrap
- FIGURE: BER envelope across 5 seeds, error bars

**§V-C Depth ablation (~0.7 pp)**
- Path F K ∈ {5, 10, 20} (commits Group 3)
- Path F+ K=20 negative result (commit `865e7ea`)
- FIGURE: BER vs K, dashed line at oracle headroom

**§V-D Mechanism attribution (~0.5 pp, optional)**
- Draft `tcom_plan/draft_section_IV_E_attribution.md`
- Commit `be65eed` (per-candidate mechanism classification)
- Demote to appendix if main paper overflows

**§V-E Complexity audit (~1 pp, load-bearing)**
- Draft `tcom_plan/draft_section_IV_F_complexity.md` (already strong)
- Commit Group 4 (QA #44 audit) — eq (23) omits DA-LS, fair P=18 worse than P=10, tau_lookup free 11%
- TABLE: wall-clock N ∈ {512, 1024, 2048} × 3 receivers
- TABLE: analytical MAC count

**§V Setup paragraph (~0.3 pp at start of §V)**
- Reproducibility: per-result `_argv` + `_config` fingerprint (commit `ff81141`)
- Channel: UWA-style 8-path, doubly selective
- Hardware: deinlab RTX 4090

### §VI Discussion + Conclusion (~1 pp)
- FYP `Section5.tex` (existing skeleton)
- Limitations (UWA simulator family; no real-data; single GPU class)
- Future work (MSML, real-data, terrestrial high-mobility)

### Bibliography
- FYP `references.bib` (no edits) — 60+ entries already
- **NEW**: ~5 entries for §II 2B (learned receivers) + ~2 entries for §II 2C (sparse unrolling)

---

## C. Writing-load estimate

| Phase | Lines of new LaTeX (est.) | Reused LaTeX (est.) | Effort |
|---|---:|---:|---|
| Preamble + main.tex template swap | ~100 | 0 | 0.5 day |
| §I Intro | ~80 | ~270 (from `Section1.tex`) | 0.5 day |
| §II Related Work | ~100 (NEW) | ~95 (lit survey from `Section1.tex`) | 1 day |
| §III System & Unrolling | ~50 (initialization-faithful) | ~500 (`Section2.tex` + `Section3.tex`) | 0.5 day |
| §IV Training | ~80 (Phase 3 width-MLP findings) | ~80 (from `Section3.tex` end) | 0.5 day |
| §V-A Waterfall + baselines | ~200 | ~140 (`Section4.tex`) | 1.5 days |
| §V-B Multi-seed envelope | ~80 | 0 | 0.5 day |
| §V-C Depth ablation | ~80 | 0 | 0.5 day |
| §V-D Mechanism (or appendix) | ~50 | 0 | 0.3 day |
| §V-E Complexity audit | ~150 (incl. tables, integrate QA #44) | ~50 (from `draft_section_IV_F_complexity.md`) | 1 day |
| §VI Discussion + Conclusion | ~80 | ~25 (`Section5.tex`) | 0.3 day |
| Bibliography additions | ~7 entries | ~60 entries | 0.3 day |
| Figure regen (single-col → double-col) | — | — | 1 day |
| **Total writing-only** | **~1 050 new LaTeX lines** | **~1 220 reused** | **~7.5 days** |

Plus audits (Phase 4) + kill-argument (Phase 5): ~2 days.

**Total: 9–10 working days** from kick-off to submission-ready PDF.

---

## D. Risk register (content-level)

- **D.1**: §V-A.2 same-budget classical heuristic narrative is currently strong in `TCOM_PLAN.md` §5 (§IV-D-prime sketch); needs to be ported into TMLCN's §V-A.2 framing — easy port but don't lose the mechanism paragraph (frame 0 / 5 SNR=15 phantom-path analysis).
- **D.2**: §V-D mechanism attribution is the weakest currently-evidenced section. If E4 (commit `be65eed` per-candidate classification) doesn't yield a clean ≥60% Dirichlet-sidelobe number on a paired pool, **demote to appendix and remove claim C4**. TMLCN does not require this for headline.
- **D.3**: Initialization-faithful theorem (C9) is currently a **bit-exact numerical verification** (`verify_classical_unrolled_matches_numpy.py`), not an analytical proof. Frame as "computational reproducibility theorem"; cite the verifier file path in caption. Don't over-claim.
- **D.4**: TMLCN page limit unverified at plan time. If hard cap is < 12 pages, the §V-D mechanism subsection is the first to cut.

---

## E. Cross-references

- [TMLCN_PLAN.md](./TMLCN_PLAN.md) — primary venue plan
- [TVT_PLAN.md](./TVT_PLAN.md) — backup venue plan
- [TCOM_PLAN.md](./TCOM_PLAN.md) — original venue plan (reference)
- FYP LaTeX root: `paper/`
- Post-FYP commits: `trans/tcom-main` branch since tag `fyp-final` (5056b7b)
- Results JSON whitelist: `.gitignore` lines with `!` prefix
