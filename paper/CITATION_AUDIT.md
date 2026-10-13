# Citation Audit Report — run02

**Date**: 2026-04-27T11:08:08Z
**Bib file**: references.bib
**Total entries**: 49 (46 cited, 3 uncited)
**Reviewer**: GPT-5.4 Pro (browser, oracle CLI 0.9.0)
**Thread**: https://chatgpt.com/c/69ef3cda-cd9c-8333-a46e-f5da4846fcd2
**Trace**: `.aris/traces/citation-audit/2026-04-27_run02/`

## Summary

| Verdict | Count |
|---------|-------|
| KEEP | 45 |
| FIX | 1 |
| REPLACE | 3 |
| REMOVE | 0 |

**Top-level**: `FAIL` (wrong_context)

> Note: Oracle reported top-level WARN; per the citation-audit skill decision table any REPLACE escalates to FAIL until addressed. Verdict is FAIL pending the 3 REPLACE-class fixes below.

## Critical Fixes (must apply before submission)

### 1. REPLACE: `afdm2025jointcesd` — wrong-context (compresses two designs into one)

- **Where**: `sections/Section1.tex:160` (prose) + `sections/Section4.tex:59` (table row)
- **Issue**: The Huang/Li/Huang/Wang Phys. Comm. 2025 paper presents *two* receiver designs — a DNN-based receiver and a GI-free iterative receiver. The current prose says *"a joint AFDM receiver that combines a guard-interval-free iterative loop with a DNN-aided detector"*, which fuses the two into one design that doesn't exist in the paper.
- **Fix**: Rewrite Section1.tex:160 prose to e.g. *"Huang et al. propose AFDM CE/SD receiver designs including a DNN-based receiver and a separate GI-free iterative receiver, demonstrating that learning-augmented joint AFDM receivers are tractable in principle, but [...]"*. Split the Section4.tex:59 table row's *"Iterative / learned"* column into two distinct axes if the table can accommodate it; otherwise keep the row but soften the label to e.g. *"GI-free iter. **OR** DNN-aided"*.

### 2. REPLACE: `he2020oampnet` — bib record duplicates `he2019modeldrivensurvey`

- **Where**: `references.bib` (the bib entry); `sections/Section1.tex:244` (the cite call inside the MIMO-detector list)
- **Issue**: The bib entry for `he2020oampnet` has the same DOI/title/venue as `he2019modeldrivensurvey` (10.1109/MWC.2019.1800447) — they are the same paper. But Section 1's MIMO-detector list cites `he2020oampnet` as a model-driven detector, which the survey paper is not. `he2020modeldrivenmimo` (IEEE TSP 2020) already covers the detector slot in the same sentence.
- **Fix (recommended)**: Drop `\cite{he2020oampnet}` from Section1.tex:244 — the sentence already cites `he2020modeldrivenmimo` for the detector, so the duplicate cite is redundant. Also delete the `he2020oampnet` bib entry from references.bib. Alternative: replace the bib record with a real OAMP-Net source (e.g. He, Wen, Jin, Li *"A Model-Driven Deep Learning Network for MIMO Detection"*, IEEE GlobalSIP 2018, DOI 10.1109/GlobalSIP.2018.8646357 — verify on Xplore before adopting).

### 3. REPLACE: `tugnait2006superimposed` — wrong author name + wrong-context attribution

- **Where**: `sections/Section1.tex:124` (prose)
- **Issue**: Two problems on the same line. (a) Prose says *"Tugnait and Luo"* but the bib's author field is *"Tugnait, Jitendra K. and Meng, Xiaohong"* — the prose has the wrong second-author surname. (b) The CRB / equispaced-equipowered placement claim attributed to this Tugnait paper is actually established by Cui & Tellambura (cui2007superimposed); Tugnait & Meng covers SP-training performance/power-allocation/synchronisation, not the CRB result.
- **Fix**: Rewrite Section1.tex:124 to attribute the ML/MMSE/CRB/equispaced result to Cui & Tellambura alone, and cite Tugnait & Meng separately (e.g. one sentence later) for SP-training power allocation. Suggested rewrite: *"Cui and Tellambura~\cite{cui2007superimposed} derived ML and MMSE iterative estimators for SP-OFDM and proved that the equispaced equipowered placement minimises the Cramér–Rao bound, while Tugnait and Meng~\cite{tugnait2006superimposed} characterised SP-training power-allocation tradeoffs and frame-synchronisation behaviour. Orozco-Lugo et al.~\cite{orozco2011superimposed} established the optimality of the equipowered training pattern under the spectral-efficiency constraint."*

## Metadata Fix (recommended; verify on IEEE Xplore first)

### FIX: `yin2025afdmoverview`

- **Where**: `references.bib`
- **Issue**: Oracle reports the AFDM overview is now in print; current entry has `note = {in press}` and is missing `volume`/`number`/`pages`. Oracle proposes vol 32 / no 6 / pp 200–208.
- **Fix**: Add `volume = {32}, number = {6}, pages = {200--208}, month = dec`, remove `note = {in press}`. **Confirm vol/no/pages on IEEE Xplore (DOI 10.1109/MWC.2025.3600081) before applying** — IEEE WCM in 2025 typically reaches around vol 32 but the exact page range needs Xplore confirmation, since Oracle's verifying URL chain didn't include Xplore directly.

## All-Clean Entries (no action needed)

45 entries verified KEEP — see `details.per_entry` in `CITATION_AUDIT.json` for per-entry notes (DOI, citation-context judgement, cite-key-prefix mismatch where applicable).

Cite-key prefix mismatches (accepted, no fix required):
- `qing2024spafdm` → first author Zheng (Kai)
- `zhao2024gifreeafdm` → first author Zhou (Yu)
- `ma2024oversampledafdm` → first author Ranasinghe
- `zhou2024msmlafdm` → first author Cao (Rongyou)
- `cui2007superimposed` → year 2011
- `liang2011iterativesp` → year 2006
- `kaleh2005zadoffchu` → Popović 1992

## Uncited entries (live in bib but never used; KEEP optional)
- `donoho2009amp` — AMP background, not currently cited
- `candes2006cs` — CS background, not currently cited
- `li2002channelestimationofdm` — OFDM CE background, not currently cited

## Trace artifacts
- `.aris/traces/citation-audit/2026-04-27_run02/oracle_response_full.md` — full Oracle Pro response
- `.aris/traces/citation-audit/2026-04-27_run02/sent_bundle.md` — exact prompt + bib + contexts that were sent to Oracle Pro
- `.aris/traces/citation-audit/2026-04-27_run02/oracle_session.log` — verbose CLI session log
---

## Applied Fixes (post-audit)

**Applied at**: 2026-04-27T11:21:35Z

**4 of 4 audit findings resolved** (3 REPLACE + 1 FIX). All bibliographic issues addressed.

### ✅ afdm2025jointcesd — REWROTE_PROSE_AND_TABLE
- `sections/Section1.tex:159-165` — Huang et al. sentence rewritten to attribute the paper's two independent designs (DNN-based + separate GI-free iterative) instead of one fictional combined design.
- `sections/Section4.tex:59` — table cell softened from "Joint CE+SD / DNN-aided" to "GI-free iter. **or** DNN-aided".
- `sections/Section4.tex:44` — table caption gained a footnote explaining the two-design collapse.

### ✅ he2020oampnet — DELETED_BIB_ENTRY_AND_DROPPED_CITE
- `references.bib` — deleted the `@article{he2020oampnet, ...}` block (was a duplicate of `he2019modeldrivensurvey` at DOI 10.1109/MWC.2019.1800447).
- `sections/Section1.tex:244` — removed `,he2020oampnet` from the joint cite, leaving `\cite{he2020modeldrivenmimo}` alone (the real TSP 2020 detector paper).

### ✅ tugnait2006superimposed — REWROTE_PROSE_TO_FIX_AUTHOR_NAME_AND_ATTRIBUTION
- `sections/Section1.tex:122-128` — one sentence split into three: (a) Cui+Tellambura own ML/MMSE/CRB/equispaced-equipowered, (b) Tugnait & Meng (was wrongly written as "Tugnait and Luo") own SP-training power-allocation/frame-sync, (c) Orozco-Lugo owns equipowered-pattern optimality.

### ✅ yin2025afdmoverview — FIXED_METADATA
- `references.bib` — added `volume = {32}, number = {6}, pages = {200--208}, month = dec`, removed `note = {in press}`.
- Verified independently via **Crossref API** (Xplore returned 418): title, container, vol 32, issue 6, page 200-208, published Dec 2025, 14 authors — all Oracle claims confirmed.
- PDF reference list now renders [17] as *"vol. 32, no. 6, pp. 200--208, Dec. 2025"*.

## Post-fix build state
- 45 `bibitem` entries (was 46; −1 from `he2020oampnet` deletion)
- 61 PDF pages (unchanged)
- Zero `Citation undefined` / `Reference undefined` warnings
- PDF metadata title preserved: "AFDM Transceiver Design for Underwater Acoustic Communication System"

## Verdict status
Top-level `verdict` field remains **FAIL** in `CITATION_AUDIT.json` because the audit found 3 REPLACE-class issues. Per-entry `post_audit` fields record their resolution. The deferred FIX is metadata-only and does not regress paper credibility — "in press" is a valid bib state.