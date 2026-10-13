# TMLCN_PLAN.md — IEEE Trans. on Machine Learning in Communications and Networking submission plan

**Branch**: target `trans/tmlcn-main` (to fork from `trans/tcom-main` HEAD)
**Started from**: tag `fyp-final` (commit 5056b7b, weighted 86.7 / A5) + post-FYP commits through 7e886a3 (QA #44 recv complexity audit)
**Target venue**: IEEE Transactions on Machine Learning in Communications and Networking
**Status**: PLAN draft — venue retargeted from TCOM; experiment matrix unchanged (E1–E6 + post-FYP additions); framing rewritten to emphasize learned/unfolded receiver as primary contribution.

> Sibling plan: [TCOM_PLAN.md](./TCOM_PLAN.md) (original venue, 80% done). This file shares the experiments and claims but re-positions for TMLCN's "ML+comm" scope. The TCOM plan stays as the backup-of-backup if the TMLCN/TVT route fails.

---

## 0. Why TMLCN (over TCOM)

| Criterion | TCOM | **TMLCN** | TVT (backup) |
|---|---|---|---|
| Scope fit for learned/unfolded receiver | Marginal — receivers OK but learned-receivers still adjusting in reviewer pool | **Direct hit — "physical layer design using deep learning" is named scope** | Adjacent — high-Doppler / V2X / UWA framing works but ML angle is secondary |
| Reviewer expertise on deep unfolding | Mixed (signal-processing reviewers may want pure model-based comparison) | **ML+comm specialists; unfolding evaluation criteria are well understood** | Mixed (vehicular focus; UWA is fine but ML/unfolding less central) |
| Acceptance rate (rough) | ~25% | **~35–40% (newer journal, friendlier)** | ~30% |
| Time to first decision | ~3–4 mo | **~2–3 mo (newer journal, faster pipeline)** | ~3 mo |
| Format | IEEEtran double-column | **IEEEtran double-column** | IEEEtran double-column |
| Co-sponsors | ComSoc | ComSoc + Computer Society + Signal Processing Society | VTS |

**Decision**: TMLCN primary, TVT backup (see [TVT_PLAN.md](./TVT_PLAN.md)). TCOM retained as second backup only if both reject.

---

## 1. Headline claim (TMLCN-reframed)

> A faithful differentiable unrolling of the classical SP-AFDM joint OMP + DA-LS + sparse MP-BP receiver, augmented with a 1 041-parameter learned support-refinement head, achieves consistent paired BER reduction across multiple training seeds, operates in the same arithmetic complexity class as the unrolled receiver while staying empirically faster than dense-MMSE alternatives, and exposes a non-linear support-ranking mechanism that linear-correlation greedy cannot replicate. We position the work as a methodology contribution for learned receivers on doubly dispersive channels: the unrolling guarantees parity with the classical algorithm at initialization, the learned head exploits per-candidate features unavailable to OMP, and the complexity audit is honest about MACs/wall-clock/memory in a way the deep-receiver literature often skips.

**Δ from TCOM headline**: kept the experimental load-bearing pieces (multi-seed retraining envelope, external-baseline reproduction, measured complexity) but lifted the "ML methodology contribution" framing to the front; added the explicit "complexity audit honest about MACs/wall-clock/memory" hook that resonates with TMLCN's ML-systems audience and addresses a reviewer-2 attack frequent at TMLCN-style venues.

---

## 2. Novelty axes (TMLCN-reframed)

Same six axes as TCOM_PLAN, with **framing changes only** — experiments unchanged. The §-numbers below map to the **TMLCN paper** structure (see §5), not TCOM's.

| Axis | Feature branch | TMLCN section it supports | Effort (GPU·h) | Status (carry-over from TCOM_PLAN) |
|---|---|---|---|---|
| A — Cao 2024 SP-AFDM external baseline | `trans/tcom-main` (cao_baseline subdir) | §V-A (matched-budget comparison), §IV-A waterfall | ~12 total | **95%** — algorithm implemented; consistency test reproduces Fig 3 + Fig 4 slopes. Remaining: integrate `--baseline cao_isp`, run E2 paired pool on UWA regime |
| B1 — Listwise top-K loss (NeuralSort/SoftSort) replacing BCE+rank-hinge | `trans/listwise-mechanism` | §III-D (training objective), §V-B (5-seed envelope) | ~24 | **W8 already addressed via width-MLP path**: commit `eb75db8` Phase 3 closure: width-MLP dominates, attention not additive, BER 0.0355 SOTA. Re-classified as ablation, no longer load-bearing for headline |
| B2 — Per-candidate mechanism attribution | `trans/listwise-mechanism` | §V-D (mechanism analysis) | ~6 | not started; lower priority for TMLCN (TMLCN reviewers care more about complexity-aware learning than per-atom attribution) |
| C — Wall-clock + MAC + memory profiling | `trans/complexity` | §V-E (complexity table) | ~3 | **70% — measure_runtime + analytical_macs landed** + draft `tcom_plan/draft_section_IV_F_complexity.md` already written |
| D — Same-budget classical heuristic OMP-(P+K) | `trans/tcom-main` | §V-A.2 (NEW: isolates "is the gain just budget?") | ~1 | **DONE** — 250 frames × 3 SNR × K∈{2,4,8,16}, all 4 verification checks pass |
| **NEW E (post-FYP)** — Unrolled OMP-Net K=10 + curriculum (E2E Path F) | `trans/tcom-main` | §V-C (depth ablation, K=O(sparsity)) | ~6 (DONE) | **DONE** — commits `865e7ea`, `ec5bd08` confirm K=10 is the right unrolled depth; ablation K∈{5,10,20} shows K=20 marginal returns |
| **NEW F (post-FYP)** — Phase 4 fs=4B Nyquist sweep | `trans/tcom-main` | §V-A.3 (sampling-rate sensitivity, paper-defensibility) | ~4 (DONE) | **DONE** — commit `aee25ae` confirms fs=4B is paper-defensible (Nyquist fs=2B is 2.4× worse); justifies the operating point against reviewer-2 attack |
| **NEW G (post-FYP)** — QA #44 receiver complexity audit | `trans/tcom-main` | §V-E (cross-check on §V-E complexity table) | 0 (audit only) | **DONE** — commit `7e886a3` confirms eq (23) omits DA-LS, fair P=18 worse than P=10, tau_lookup free 11% MAC. Reviewer-attack-proof complexity story |

Total post-FYP additional effort: **0 GPU·h pending** (everything done). TMLCN-specific work is **packaging only** (framing + figure regen + LaTeX rewriting).

---

## 3. Experiment matrix (carried over from TCOM_PLAN, no new experiments)

Same E1–E6 from TCOM_PLAN.md §3. The TMLCN figure pack uses the **same JSON sources** as the TCOM version — only LaTeX template + figure layout (single-column → TMLCN double-column) changes.

| Experiment ID | Receiver | Channel | SNR (dB) | Frames | Seeds | Output | Status |
|---|---|---|---|---|---|---|---|
| E1 (FYP) | unrolled + classical | UWA-style 8-path | 0/5/10/15/20/25/30 | 600/773/1300 pooled | 3 seeds | `outputs_loop12_*` | ✓ |
| E2 | Cao 2024 SP-AFDM | UWA-style 8-path | 15/20/25/30 | 300 paired | 3 seeds | `outputs_cao_baseline_*` | 95% (integrate + run) |
| E3 | unrolled + width-MLP (5-seed envelope) | UWA-style 8-path | 15/20/25/30 | 300 paired | 5 seeds | `outputs_width_seed{0..4}_*` | ✓ (post-FYP, Phase 3) |
| E4 | width-MLP best | UWA-style 8-path | 15/20/25 | 250 paired | 1 | `outputs_attribution_*` | not started (low priority) |
| E5 | classical / Cao / unrolled best | UWA-style 8-path (N ∈ {512,1024,2048}) | 20 | 50 | 1 | `outputs_complexity_*` | ✓ (draft IV-F written) |
| E6 | OMP-(P+K), K∈{2,4,8,16} | UWA-style 8-path, v=2.0, fs=4B | 15/20/25 | 250 paired | 1 | `outputs_omp_extended_4B_big/` | ✓ |
| **E7 (NEW)** | unrolled OMP-Net depth ablation | UWA-style 8-path | 20/25 | 250 paired | 1 | `outputs_pathF_K{5,10,20}_*` | ✓ |
| **E8 (NEW)** | Phase 4 fs sweep | UWA-style 8-path | 25 | 250 | 1 | `outputs_fs_sweep_*` | ✓ |

**No new GPU-time-expensive experiments**. The TMLCN paper is entirely a **rewrite + recompile** task from existing artifacts.

---

## 4. Claim → evidence map (TMLCN, no new claims)

C1–C7 carried over from TCOM_PLAN.md §4. Added two TMLCN-positioning claims that emphasize the ML methodology contribution:

- **C1**: 5-seed mean BER reduction at 20/25/30 dB ≥ existing single-seed Δ; 95% CI from width-MLP retrains. → E3 ✓
- **C2**: Reproduced Cao 2024 SP-AFDM baseline within ±10% of published BER. → E2 (95% done)
- **C3**: Unrolled+head beats Cao 2024 by paired McNemar p < 1e-3 at 25/30 dB. → E1+E2 (pending E2 run)
- **C4**: Per-candidate attribution shows ≥60% of added atoms are Dirichlet sidelobes. → E4 (deprioritized for TMLCN)
- **C5**: Wall-clock at N=1024 within 2× of classical-unrolled; MAC count in same asymptotic class. → E5 ✓
- **C6** (FYP carry-over): support recall ≥95%, gap-closed 61/81/98% across SNR. → ✓
- **C7**: OMP-(P+K) regresses monotonically; learned head is non-linear support-refinement, not budget. → E6 ✓
- **NEW C8** (TMLCN-specific): The 1 041-parameter head is **complexity-honest** — eq-(23) accounting omits DA-LS, fair P=18 unrolled is worse than P=10 unrolled, tau_lookup gives a free 11% MAC reduction. → QA #44 audit ✓
- **NEW C9** (TMLCN-specific): The unrolled receiver is **initialization-faithful** — at random init, end-to-end output matches the classical NumPy implementation bit-exactly (per `verify_classical_unrolled_matches_numpy.py`). The learned head adds expressivity over a classical-equivalent baseline. → standing verifier ✓

---

## 5. Paper structure (TMLCN, ~12 pages double-column)

TMLCN journal page budget: typical 12 pages with overlength fee allowed (verify against current TMLCN information-for-authors page before submission — the published page limit may have shifted since journal launch in 2023).

### Top-level structure

1. **Introduction** (~1.5 pp)
   - Motivation: doubly dispersive channels (UWA + high-mobility wireless); SP-AFDM trade-off.
   - **Gap (TMLCN-positioned)**: existing learned receivers for AFDM are not initialization-faithful to the classical algorithm, do not honestly account for MACs/wall-clock/memory, and conflate "more atoms in support" with "better support ranking."
   - Approach: faithful differentiable unrolling + 1 041-parameter learned support-refinement head + complexity audit + same-budget classical heuristic comparator.
   - Contributions (5 bullets — see §1 above).
2. **Related Work** (~1 pp)
   - **2A**: AFDM modulation, SP-AFDM channel estimation, OMP/MP joint receivers (Bemani 2023, Benzine 2023, Cao 2024).
   - **2B**: Learned/unrolled receivers for OFDM/OTFS (DetNet, OAMPNet, GENIUS, MMNet) — emphasize: most do not preserve initialization-classical-equivalence and do not report comparable complexity audits.
   - **2C**: Sparse-recovery + deep unrolling (LISTA et al.) — emphasize: our head is not LISTA-style end-to-end matrix learning; it is a per-candidate attribution head over a frozen OMP-derived candidate pool.
3. **AFDM SP receiver setting & differentiable unrolling** (~2 pp)
   - System model (signal, channel, sparse delay-Doppler representation).
   - Classical joint OMP + DA-LS + MP-BP iteration.
   - Differentiable unrolling: per-iteration operations are vectorized in PyTorch; initialization-faithful theorem (bit-exact match at random init).
   - Learned head: feature definition (C2-rel, F2-P), 1 041 parameters, plug-in slot after each OMP atom-selection step.
4. **Training objective and protocol** (~1 pp)
   - BCE on per-candidate active/inactive labels + ranking auxiliary (current).
   - Width-MLP architecture choice (Phase 3 finding: width dominates, attention not additive).
   - 5-seed envelope protocol; data generation per-seed; SNR-weighted training pitfalls (W8 ablation finding).
5. **Experiments** (~5 pp)
   - **5-A. Waterfall and baselines**: 4-arm comparison (serial-OMP / classical-joint / Cao 2024 SP-AFDM / learned head); SNR sweep with paired McNemar p-values. **5-A.2** same-budget classical heuristic OMP-(P+K) — confirms learned-head gain is not a budget effect. **5-A.3** fs sensitivity (fs=4B vs fs=2B).
   - **5-B. Multi-seed retraining envelope** (5 seeds): the FYP single-seed gain replicates across seeds; bootstrap 95% CI.
   - **5-C. Depth ablation**: K ∈ {5, 10, 20} for unrolled OMP-Net (Path F K=20 negative result — K=10 = O(sparsity) is right).
   - **5-D. Mechanism attribution** (lightweight, optional): per-candidate attribution showing ≥60% added atoms are Dirichlet sidelobes (if E4 lands; else demote to appendix).
   - **5-E. Complexity audit**: wall-clock table (N ∈ {512,1024,2048}) + analytical MACs + QA #44 reviewer-attack-proofing.
6. **Discussion & Conclusion** (~1 pp)
   - Limitations: UWA simulator family, no real-data, single GPU class.
   - Future work: MSML, real-data UWA, transfer to terrestrial high-mobility.

### What we cut from TCOM structure for TMLCN

- TCOM had a separate "axis B per-candidate mechanism attribution" as a §IV-E section (~0.5 pp). For TMLCN we demote this to optional/appendix since the ML methodology contribution (faithful unrolling + complexity-honest) is more central.
- TCOM §IV-F complexity table is **promoted** to a dedicated §5-E in TMLCN — TMLCN reviewers expect rigorous complexity audits for learned receivers.

---

## 6. Content integration map (FYP `paper/sections/Section{1..5}.tex` + post-FYP results → TMLCN sections)

| TMLCN section | Source content | New writing needed |
|---|---|---|
| §I Intro | FYP `Section1.tex` lines 1–~100 (background, motivation, gap) | Rewrite contributions paragraph for TMLCN scope; add C8/C9 to bullet list |
| §II Related Work | FYP `Section1.tex` lines ~100–~365 (lit survey) | Add 2 sub-paragraphs: learned/unrolled receivers, sparse-recovery unrolling (LISTA & co.) |
| §III System & Unrolling | FYP `Section2.tex` + `Section3.tex` (system model + OMP-MP algorithm) | Add "initialization-faithful theorem" subsection (1 paragraph, points at `verify_classical_unrolled_matches_numpy.py`) |
| §IV Training | FYP `Section3.tex` end (training protocol) + Phase 3 width-MLP findings | New section combining FYP training + width-MLP best-practices |
| §V-A Waterfall + baselines | FYP `Section4.tex` waterfall + post-FYP Cao baseline + OMP-(P+K) heuristic + Phase 4 fs sweep | Substantial — merge 4 sources into single coherent §V-A with 3 subsections |
| §V-B Multi-seed envelope | Post-FYP Phase 3 5-seed envelope | New — currently lives in commits `eb75db8`, `430e1a4` only, not in `paper/sections/` |
| §V-C Depth ablation | Post-FYP Path F K=10 + K=20 ablation | New — currently in commits `865e7ea`, `ec5bd08` |
| §V-D Mechanism attribution | `tcom_plan/draft_section_IV_E_attribution.md` (if used) | Move from markdown to LaTeX; optional |
| §V-E Complexity | `tcom_plan/draft_section_IV_F_complexity.md` + QA #44 audit | Move from markdown to LaTeX + add QA #44 audit results |
| §VI Discussion + Conclusion | FYP `Section5.tex` | Mostly carry-over; rewrite conclusion for TMLCN-positioning |
| Bibliography | FYP `references.bib` (no edits) | Add learned/unrolled receiver references (cf. §II 2B) — ~5 new entries |

---

## 7. Pipeline (operational)

```
Phase 0  Branch + venue template setup
  ├─ git worktree add ../AFDM-channel-estimation-tmlcn trans/tmlcn-main
  ├─ Copy paper/ → ./paper/ (under new worktree)
  ├─ Swap paper/main.tex header from FYP article class → IEEEtran TMLCN style
  └─ Verify compile (no FYP-specific commands like \thesistitle, \GUID)

Phase 1  /paper-plan (anchored on this TMLCN_PLAN.md)
  └─ Generate PAPER_PLAN.md scoped to TMLCN structure (§5)

Phase 2  /paper-write per-section
  ├─ §I Intro (rewrite contributions)
  ├─ §II Related Work (add 2B learned receivers, 2C sparse-unrolling)
  ├─ §III System (add initialization-faithful theorem)
  ├─ §IV Training (combine FYP + width-MLP)
  ├─ §V Experiments (5 subsections — biggest writing load)
  └─ §VI Conclusion

Phase 3  /paper-figure regen
  ├─ Convert single-column FYP figures → double-column TMLCN layout
  ├─ Add new figures: Phase 4 fs sweep, Path F K ablation, multi-seed envelope
  └─ TABLE 1 complexity (from draft_section_IV_F_complexity.md)

Phase 4  /paper-compile + audits
  ├─ /paper-claim-audit (every number must trace to outputs_*/results.json)
  ├─ /citation-audit (every cite must check out)
  ├─ /proof-checker --restatement-check (initialization-faithful claim is the only theorem)
  └─ /kill-argument (adversarial pre-submission)

Phase 5  /overleaf-sync push (if user wants Overleaf collaboration)
```

---

## 8. Risks (TMLCN-specific)

- **R1 (medium)**: TMLCN is a newer journal; the reviewer pool is still calibrating standards for "what counts as enough" novelty for learned-receiver work. Mitigation: lean hard on the complexity-honest narrative (C5, C8, C9), which addresses the most common reviewer-2 attack ("did you measure MACs honestly?").
- **R2 (medium)**: TMLCN page limit verification — published "preferred" length may have shifted since 2023 launch. Mitigation: pre-submission check via TMLCN information-for-authors URL (`https://www.comsoc.org/publications/journals/ieee-tmlcn`) + author portal info.
- **R3 (low)**: Cao 2024 SP-AFDM baseline reproduction (E2) is 95% done but the paired McNemar pool has not finished. Mitigation: allocate 6–8 GPU·h on deinlab to close E2; this is the only experimental gap before submission.
- **R4 (low)**: Initialization-faithful theorem (C9) is currently empirical (per-frame bit-exact match) not analytical. Mitigation: write the theorem as a "computational reproducibility" claim, not a formal proof — TMLCN accepts this framing for systems-style contributions.

---

## 9. Acceptance gate before submission

All must be green:

- [ ] `verify_classical_unrolled_matches_numpy.py` passes — initialization-faithful claim is bit-exact verifiable
- [ ] E2 paired pool finished (Cao baseline) and McNemar p < 1e-3 confirmed
- [ ] PAPER_CLAIM_AUDIT.json: PASS (every number traces to a results.json)
- [ ] CITATION_AUDIT.json: PASS or WARN-soft-only (no fabricated citations)
- [ ] PROOF_CHECK_STATE.json: NOT_APPLICABLE or PASS (only "theorem" is the initialization-faithful one)
- [ ] EXPERIMENT_AUDIT.json: PASS (no fake ground truth, no normalization fraud)
- [ ] KILL_ARGUMENT.json: no `still_unresolved` critical findings
- [ ] Compile cleanly under TMLCN IEEEtran style; page count ≤ 12 (or ≤ 14 with overlength acceptance)
- [ ] Anonymity scan: PASS (assume TMLCN is single-blind by IEEE default; verify before submission)

---

## 10. Timeline

Target submission: **2026-06-20** (5 weeks from 2026-05-16).

- W1 (this week): Phase 0 branch+template setup; finalize TMLCN_PLAN + content-inventory; run E2 paired pool in background.
- W2: Phase 1 /paper-plan; Phase 2 §I + §II + §III writing (3 sections).
- W3: Phase 2 §IV + §V-A + §V-B writing.
- W4: Phase 2 §V-C, §V-D, §V-E, §VI; Phase 3 figure regen.
- W5: Phase 4 audits + Phase 5 kill-argument + final compile + submit.

If E2 (Cao baseline) doesn't close in W1, push submission by 1 week and run in W2.

---

## 11. Cross-references

- [TCOM_PLAN.md](./TCOM_PLAN.md) — original venue plan, kept as second backup
- [TVT_PLAN.md](./TVT_PLAN.md) — first backup venue plan
- [CONTENT_INVENTORY.md](./CONTENT_INVENTORY.md) — file-level map of FYP + post-FYP material → TMLCN sections
- FYP paper: `paper/sections/Section{1..5}.tex` + `paper/Appendices/Appendix.tex`
- Post-FYP material: commits `aee25ae`, `eb75db8`, `865e7ea`, `7e886a3`, etc. on `trans/tcom-main`
- Draft sections: `tcom_plan/draft_section_IV_*.md`
