# TVT_PLAN.md — IEEE Trans. on Vehicular Technology backup venue plan

**Status**: BACKUP — only execute this plan if [TMLCN_PLAN.md](./TMLCN_PLAN.md) primary path rejects or stalls.
**Branch**: `trans/tvt-main` (to fork from `trans/tcom-main` HEAD if activated)
**Target venue**: IEEE Transactions on Vehicular Technology
**Effort delta from TMLCN plan**: ~3 days of LaTeX reframing + 1 figure regen; **no new experiments**.

---

## 0. When to activate this plan

Activate TVT only if **any one** of the following triggers fires:

1. TMLCN editor's pre-screening rejects on "out of scope" (unlikely given TMLCN scope explicitly names "physical layer design using deep learning", but possible if reviewer requests stronger ML methodology).
2. TMLCN page limit (verified at submission time) is too tight for the §V-A 3-subsection waterfall + §V-E complexity table; TVT's ~13-page limit gives more room.
3. TMLCN review yields critical reviewer-2 attack "this is mostly comm engineering, not enough ML novelty" — TVT reviewers won't pose this attack.

---

## 1. Headline claim (TVT-reframed)

> For doubly dispersive doubly selective channels common to underwater acoustic (UWA) modems and high-mobility vehicular wireless links, we develop a faithful differentiable unrolling of the SP-AFDM joint OMP + DA-LS + sparse MP-BP receiver and augment it with a 1 041-parameter learned support-refinement head. The result is paired BER reduction across multiple training seeds, complexity in the same arithmetic class as the unrolled receiver, and an explicit non-linear support-ranking mechanism. We position the work as a vehicular-technology contribution to receiver design under extreme Doppler regimes, validated on a UWA-style 8-path channel representative of relative Doppler `v/c ~ 10^{-3}` and applicable, with reduced delay spread, to high-mobility wireless.

**Δ from TMLCN headline**: traded "complexity-honest ML methodology" framing for "extreme-Doppler vehicular/UWA receiver design". UWA becomes the empirical test bed *and* the application domain (TVT is friendly to UWA submissions). Learned-receiver methodology stays in but is positioned as the means, not the contribution.

---

## 2. Structure delta vs TMLCN

Same 5 main experimental contributions (E1–E8 carried unchanged). Only the **outer framing** flips:

| TMLCN section | TVT version (delta) |
|---|---|
| §I Intro: lead with ML methodology gap | §I Intro: lead with **high-Doppler / UWA channel pathology** gap; ML methodology is the solution |
| §II Related Work: 2B learned/unrolled receivers central | §II Related Work: **2A vehicular high-mobility channel estimation** central; 2B learned receivers as one approach among several |
| §III–IV: faithful unrolling + training | §III–IV: same content, but headings reordered to emphasize "receiver design" over "learned methodology" |
| §V-E Complexity table: TMLCN-grade complexity audit | §V-E Complexity: keep, less load-bearing for TVT (TVT reviewers won't demand MAC accounting as hard); demote QA #44 audit to appendix |
| §VI Conclusion: ML methodology contribution | §VI Conclusion: **UWA / high-mobility wireless** applications; ML methodology mentioned in "future work" |

**Page budget**: TVT regular paper ~13 pages double-column; submit at 12, leave 1 page for revision response.

---

## 3. Risks (TVT-specific)

- **R1 (medium)**: TVT reviewer pool for UWA submissions is small and inconsistent — a UWA-skeptical reviewer may demand vehicular wireless validation. Mitigation: §V add a brief subsection arguing the AFDM + learned-receiver framework transfers to vehicular high-mobility (citation-only, no new experiments — point at the existing AFDM-for-V2X literature).
- **R2 (low)**: TVT is single-blind; verify cover letter does not over-claim novelty (typical for TVT pre-screen).

---

## 4. Pipeline (operational, only on activation)

```
Trigger: TMLCN reject or pre-screen rebuff received
Phase 0  git worktree add ../AFDM-channel-estimation-tvt trans/tvt-main from trans/tmlcn-main HEAD
         (Inherit the TMLCN paper as starting point — most content carries over.)
Phase 1  Reframe §I / §II / §VI per the delta table in §2 above
         Promote UWA application context in §I and §VI; demote ML methodology subsection
Phase 2  Demote §V-D (mechanism attribution) + QA #44 audit → appendix to free 0.5-1 page
Phase 3  /paper-compile under IEEEtran TVT style (single-blind, no anonymization)
Phase 4  /citation-audit + /paper-claim-audit + /kill-argument (re-run)
Phase 5  Submit
```

**Estimated total: 3 working days** if TMLCN paper is already polished.

---

## 5. Cross-references

- [TMLCN_PLAN.md](./TMLCN_PLAN.md) — primary venue plan (activate this first)
- [TCOM_PLAN.md](./TCOM_PLAN.md) — original venue plan, second backup
- [CONTENT_INVENTORY.md](./CONTENT_INVENTORY.md) — content map (shared across all three venue plans)
