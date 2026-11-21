# SOURCES — blind redo (2026-10-17)

Repo root `R = /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Hard-wall paths were not opened, listed or grepped (the 10-17 task directory name was seen only in the top-level `ls` of
`.trellis/tasks/` and in the git status header; nothing inside it was read).
"Read" = full or substantial reading; "partial" = header/section/grep-level reading.

## Repository files read

| File | Depth |
|---|---|
| R/STATE.md | full (two pages) |
| R/research-assets/index.md | full |
| R/research-assets/res-20261015-02.md, res-20261015-03.md, res-20261016-01.md, res-20261016-02.md, res-20261016-03.md | full |
| R/research-assets/res-20261009-01.md, res-20261010-01.md, res-20261010-02.md, res-20261013-01.md | full |
| R/research-assets/res-20261008-01.md, res-20261008-02.md | full |
| R/research-assets/res-20261014-01.md, res-20261014-02.md, res-20261014-03.md, res-20261015-01.md | full |
| R/research-assets/res-20260509-01.md, res-20260509-02.md, res-20260516-01.md, res-20260610-01.md, res-20260613-01.md | full |
| R/research-assets/res-20260727-01.md (first ~80 lines) | partial |
| R/research-assets/res-20261006-01.md (first 2 KB), -02, -03, -04 (first 2.6 KB), -05, -06 (first 2.2 KB) | partial |
| R/research-assets/res-20261007-01 … -09.md (first 2–3 KB each) | partial |
| R/research-assets/res-20260914-01.md (first 1.5 KB) | partial |
| R/.trellis/tasks/09-22-tf-production-gap-audit/prd.md (first 6 KB) | partial |
| R/results/cstate_method_closure_20260928/FINAL_CLOSURE_PACKET.md (first 9 KB), MANUSCRIPT_THEOREM_TEXT.md | partial / full |
| R/results/tf_cstate_prospective_20260923/FINAL_CSTATE_REPORT.md (first 7 KB) | partial |
| R/results/tf_geometry_reopen_20260922/RESULTS.md (first 6 KB) | partial |
| R/_archive/20260921_22_sp_afdm_pro_documents/Manuscript_First_Draft.md (lines 1–65 + heading outline) | partial |
| R/.trellis/tasks/10-08-doppler-cluster/research/manuscript-skeleton-20261014.md (first 12 KB) | partial |
| R/.trellis/tasks/10-08-doppler-cluster/research/mainline-first-principles-20261014.md | full |
| R/.trellis/tasks/10-08-doppler-cluster/research/remaining-directions-idea-review.md (first 14 KB) | partial |
| R/.trellis/tasks/10-08-doppler-cluster/research/lit-v3.md (heading/ID grep + packets A5–A13) | partial |
| R/.trellis/tasks/10-05-method-advantage/research/20261006-continuous/RESEARCH_REPORT.md (first 6 KB) | partial |
| R/experiments/tcom_channel_crb_20261016/out/analysis/CRB_RESULTS.md | full |
| R/experiments/tcom_channel_crb_20261016/out/analysis/crb_results.json | parsed (missed_energy_mean, curve_db, FER per cell) |
| R/experiments/tcom_genie_support_20261016/out/analysis/GS_RESULTS.md | grep (FER-by-SNR lines) |
| R/experiments/headroom_ladder_20261008/out/e_rho/ANALYSIS.md | partial (ρ .2–.5, 4.5–8 dB rows) |
| R/experiments/headroom_ladder_20261008/arms.py | first 40 lines |
| R/experiments/tcom_reference_frame_20261015/gen_fixed.py | lines 1–200 (channel law) |
| R/afdm_sp_joint_unrolled/afdm_env.py | grep of channel constants |
| R/experiments/sp_afdm_native_joint_20260921/src/native_twofft.py | lines 1–40 |
| R/experiments/sp_afdm_frozen_20260920/src/receiver.py | `pilot_front` |
| R/afdm_sp_joint_unrolled/supplement_baselines.py | lines 20–60, 122–175 (`BaselineInitializer`, OMP budget 24) |
| R/novelty/ | listing only (4 PDFs: Deep Ideation, AI co-scientist 2502.18864, Scideator 2409.14634, Alon 2009 Mol Cell); not read — used as method vocabulary from prior knowledge |
| ~/.claude/skills/idea-spark/SKILL.md, references/ideation-patterns/overview.md (+4 pattern cards, anti-patterns head) | partial (pattern vocabulary only; the multi-agent pipeline was not run) |
| ~/.claude/skills/scoop-check/SKILL.md, ~/.claude/skills/paper-search/SKILL.md | read (procedure) |

## Own computations (scripts in blind_redo/checks/)

| Script | Purpose | Result |
|---|---|---|
| checks/miss_law.py | one-threshold interference-limited detection model vs F0-pilot missed energy (crb_results.json), channel law re-implemented from gen_fixed.py | T = 7.39 calibrated on U ρ.3 6.5 dB; 16 U cells within \|ln\| ≤ .141; noise-only model fails |
| checks/floor_check.py | does missed energy as additive noise produce the F0 floor? | no (predicts ≈0 floor vs observed 3–6.5e-3) |
| checks/tail_check.py | per-frame missed-energy tail under the model | P(e>.05) = .074 (ρ.3, 6.5 dB); implied effective amplification κ ≈ 1.7–2 |

## Literature checked (this session)

V = verified by reading the source page/HTML body (partial body); A = abstract/metadata page only; S = search-snippet only;
R = model recall, not verified this session; P = taken from project notes (lit-v3 / cards), not re-verified.

| ID | Item | Level |
|---|---|---|
| arXiv:2607.18881 | Luo, Guan, Ge, Jiang, Meng, González G., Data-aided CE and sensing with SBL for AFDM-ISAC (accepted IEEE TCOM per arXiv comments) | V (HTML, first 100 k chars) |
| arXiv:2501.15935 | Kanazawa, Iimori, Pradhan, Malomsoky, Ishikawa, Superimposed pilot-based OTFS – will it work? | V (HTML v1) |
| arXiv:2010.15066 | Mishra, Singh, Prasad, Budhiraja, OTFS CE and data detection designs with superimposed pilots | A (TWC 2022 venue: P) |
| arXiv:2404.10232 | Zheng, Wen, Mao, Xiao, Wang, Channel estimation for AFDM with superimposed pilots | A (TVT venue: P) |
| DOI 10.1109/GLOBECOM59602.2025.11432016 | Zheng et al., SP-AFDM JCED, GLOBECOM 2025 | P (card res-20261016-01) |
| arXiv:2610.09970 | Wang, Pan, Ren, Li, Wang, Model-order-adaptive CE for AFDM with fractional delay/Doppler | A (+P quotes) |
| arXiv:2506.14756 | Wiame, Duffy, Médard, Joint error correction and fading CE enhancement leveraging GRAND | A |
| arXiv:1412.6223 | Takeuchi, Iterative LMMSE CE, MUD and decoding via spatial coupling | A |
| DOI 10.1109/TIT.2011.2177757 | Takeuchi, Vehkaperä, Tanaka, Müller, Large-system analysis of joint channel and data estimation, IEEE TIT 58(3) 2012 | S |
| DOI 10.1214/10-AOS793 | Rosenbaum, Tsybakov, Sparse recovery under matrix uncertainty, Ann. Statist. 38(5) 2010 | S |
| arXiv:2202.04793 | Low ambiguity zone: theoretical bounds and Doppler-resilient sequence design | S |
| arXiv:2502.03289, 2410.00313, 2406.14064 | chirp-permuted AFDM; pre-chirp-domain IM; pre-chirp selection for PAPR | S |
| arXiv:1901.05409 | Low-complexity joint channel estimation and list decoding of short codes | S |
| arXiv:2504.13762, 2503.17565, 1104.0419, 2507.10074; Fang–Rugini–Leus EURASIP JASP 2010 | from lit-v3 packets | P |
| Bemani–Ksairi–Kountouris IEEE TWC 22(11) 2023; Sayeed–Aazhang IEEE TCOM 47(1) 1999 | from lit-v3 | P |
| Médard IEEE TIT 46(3) 2000; Hassibi–Hochwald IEEE TIT 49(4) 2003; Jindal–Lozano IEEE TCOM 58(10) 2010; Raheli–Polydoros–Tzou IEEE TCOM 43 1995 (PSP); Herzet et al. Proc. IEEE 95(6) 2007; Kabashima et al. IEEE TIT 62(7) 2016; Ben-Haim–Eldar IEEE TSP 58(6) 2010; Fortunati et al. IEEE SPM 34(6) 2017; Alltop IEEE TIT 26(3) 1980; Ghogho et al. DDST 2005; Zemen–Mecklenbräuker IEEE TSP 2005 | R |

Venues confirmed by paper-search (OpenAlex/Crossref metadata, level A/S): Yuan, Li, Wei, Yuan, Ng, IEEE WCL 10(9):1954–1958, 2021,
DOI 10.1109/LWC.2021.3088836 (abstract page also read, A); Zheng et al. IEEE TVT 2024, DOI 10.1109/TVT.2024.3469380; Mishra et al. IEEE TWC,
DOI 10.1109/TWC.2021.3110659; Cao, Wen, Huang, ICCT 2024, DOI 10.1109/ICCT62411.2024.10946599; Upadhya, Vorobyov, Vehkaperä, IEEE TSP 2017,
DOI 10.1109/TSP.2017.2675859; pre-chirp-domain IM, IEEE TWC 2025, DOI 10.1109/TWC.2025.3559997; pre-chirp selection PAPR, IEEE WCL 2024,
DOI 10.1109/LWC.2024.3521464; chirp-parameter selection with MMSE, IEEE TCOM 2024, DOI 10.1109/TCOMM.2024.3519521; Dörpinghaus et al.(?) "On the
gain of joint processing of pilot and data symbols in stationary Rayleigh fading channels", IEEE TIT 2012, DOI 10.1109/TIT.2011.2181818
(authors not checked); "Joint estimation and decoding for sparse channels via relaxed belief propagation", Asilomar 2010, DOI
10.1109/ACSSC.2010.5757563; "An improved analysis for support recovery with OMP under general perturbations", IEEE Access 2018,
DOI 10.1109/ACCESS.2018.2820804. Kanazawa et al. v3 HTML (arXiv:2501.15935v3) read for threshold eq. (24) and error-floor attribution (V).
Luo et al. 2607.18881 HTML read to the end (V): optimum σp² ≈ .2 at 0/5 dB, uncoded, no EP, no missed-path analysis, no FER.

Note: the harness refused writing `REPORT.md` from this sub-agent ("return findings as text"); the full report is in the hand-back
message instead.

paper-search CLI runs (scoop logs in blind_redo/scoop/): Semantic Scholar returned HTTP 429 throughout; arXiv/OpenAlex/Crossref/DBLP results
are what the scoop verdicts rely on, plus the WebSearch/WebFetch checks above. No PDF was downloaded (deep dives used arXiv HTML pages).
