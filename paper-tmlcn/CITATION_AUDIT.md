# Citation Audit Report

**Date**: 2026-05-16
**Method**: Manual key/metadata inspection (Codex MCP unavailable for web/DBLP lookup)
**Scope**: 7 new bib entries added by writing agent (existing 49 FYP entries treated as pre-audited)
**Verdict**: WARN — 1 REMOVE (fabricated phantom), 1 FIX (key-author mismatch), 5 KEEP (plausible, unable to web-verify)

## Issues Found

### REMOVE — `karpathy2025initfaithful`
- **Problem**: Citation key contains "karpathy" but listed authors are Brugiapaglia, Mohammad-Taheri, Colbrook — no Karpathy. Entry claims to be a "companion" to arXiv:2505.15661 but that IS the mohammadtaheri entry. Phantom/fabricated citation.
- **Action taken**: Removed from references.bib and from Section1.tex cite command. ✓

## New Entries Kept (5 / status PASS or WARN-unverifiable)

| Key | Title | Venue | Status | Notes |
|---|---|---|---|---|
| `samuel2019detnet` | Learning to Detect | IEEE Trans. Signal Process. | WARN | DetNet is real (Samuel, Diskin, Wiesel); venue may be JSTSP not TSP — unable to web-verify |
| `he2018oampnet` | Model-Driven Deep Learning for Joint MIMO | IEEE Trans. Signal Process. | WARN | OAMPNet-family paper; title/venue not verifiable without DBLP |
| `liu2019alista` | ALISTA: Analytic Weights | ICLR 2019 | PASS | High confidence — well-known paper |
| `chen2018theoreticallinearconv` | Theoretical Linear Convergence of Unfolded ISTA | NeurIPS 2018 | PASS | High confidence — known Chen et al. NeurIPS paper |
| `mohammadtaheri2025deepgreedyunfolding` | Deep greedy unfolding | arXiv:2505.15661 | PASS | DOI consistent; directly relevant to initialization-faithful claim |
| `shlezinger2022modelbasedsurvey` | Model-Based Deep Learning | Proc. IEEE | PASS | Shlezinger & Eldar Proc. IEEE paper is well-known |

## Recommendation

Re-run with Codex MCP + web/DBLP lookup when auth is restored to verify `samuel2019detnet` and `he2018oampnet` venue details. Final submission should confirm these two entries against IEEE Xplore.
