# Citation Audit — Full Reviewer Trace

- **Thread**: `019dc2d6-e94f-7630-9e2d-dd3183657104`
- **Model**: `gpt-5.5` (reasoning effort `xhigh`)
- **Sandbox**: read-only
- **Date**: 2026-04-25
- **Inputs**: `references.bib` (37 entries) + `.aris/citation-audit/contexts.txt` (36 cited keys)
- **Independence**: fresh thread, no `codex-reply`, no prior audit context shared.

```text
=== stojanovic2009uwa ===
EXISTENCE: YES  url=https://doi.org/10.1109/MCOM.2009.4752682
METADATA:
  authors: correct
  title:   correct
  year:    correct
  venue:   correct
  ids:     correct
CONTEXT:
  - sections/Section1.tex:9 - SUPPORTS - The paper supports low sound speed, wideband UWA behavior, time-varying multipath, Doppler, and sparse impulse response; the "hundreds of bins" part is arithmetic from delay spread times bandwidth.
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Keep.
```

```text
=== preisig2007uwa ===
EXISTENCE: YES  url=https://doi.org/10.1145/1347364.1347370
METADATA:
  authors: correct if "James Preisig"; wrong if "Josko C. Preisig"
  title:   correct
  year:    correct
  venue:   wrong: should be ACM SIGMOBILE Mobile Computing and Communications Review, 11(4), 2-10, Oct. 2007
  ids:     wrong: DOI should be 10.1145/1347364.1347370, not 10.1109/JOE.2007.892637
CONTEXT:
  - sections/Section1.tex:9 - SUPPORTS - The paper discusses propagation, latency, multipath, waveguide effects, and acoustic-channel constraints relevant to the claim.
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Correct the venue, pages, DOI, and author name spelling.
```

```text
=== berger2010uwasparse ===
EXISTENCE: YES  url=https://doi.org/10.1109/TSP.2009.2038424
METADATA:
  authors: correct
  title:   correct
  year:    correct
  venue:   correct
  ids:     correct
CONTEXT:
  - sections/Section1.tex:10 - WEAK - Supports sparse UWA multicarrier channels and Doppler scale/ICI, but "almost always fractional Doppler in the chirp/sub-carrier domain" is stronger and more AFDM-specific than this source.
  - sections/Section1.tex:75 - SUPPORTS - It is a foundational UWA sparse/channel-estimation reference.
  - sections/Section2.tex:314 - SUPPORTS - OMP/sparse-recovery single-pass lineage is reasonable, especially paired with Tropp.
VERDICT: FIX
AXIS_FAILURES: [CONTEXT]
NOTE: Soften the fractional-Doppler sentence or add a direct AFDM fractional-Doppler source.
```

```text
=== huang2010uwamimoofdm ===
EXISTENCE: YES  url=https://doi.org/10.1155/2010/460379
METADATA:
  authors: correct
  title:   correct
  year:    correct
  venue:   correct
  ids:     correct
CONTEXT:
  - sections/Section1.tex:10 - WEAK - Supports UWA iterative sparse CE and Doppler compensation, but not the AFDM/chirp-domain fractional-Doppler wording directly.
  - sections/Section1.tex:75 - SUPPORTS - It is a UWA sparse iterative CE/decoding reference.
VERDICT: FIX
AXIS_FAILURES: [CONTEXT]
NOTE: Keep for UWA sparse CE; avoid using it alone for AFDM fractional-Doppler claims.
```

```text
=== bemani2023afdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/TWC.2023.3260906
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:13 - SUPPORTS
  - sections/Section1.tex:41 - WEAK - "original AFDM paper" defensible only relative to this TWC paper, not all affine-Fourier prior art.
  - sections/Section2.tex:22 - SUPPORTS
  - sections/Section4.tex:74 - WEAK - exact "EP, 2-path, BER ~1e-3 at 20 dB" needs figure-specific verification.
  - sections/Section4.tex:98 - SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [CONTEXT]
NOTE: Keep, but qualify "original" and verify the exact BER figure before using the numeric claim.
```

```text
=== li2002channelestimationofdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/7693.975446
METADATA: all correct
CONTEXT: NO CONTEXT FOUND - present in references.bib but not cited in any sections/*.tex.
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Bibliographically clean but currently uncited.
```

```text
=== hadani2017otfs ===
EXISTENCE: YES  url=https://doi.org/10.1109/WCNC.2017.7925924
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:14 - SUPPORTS
  - sections/Section1.tex:74 - SUPPORTS
  - sections/Section2.tex:22 - SUPPORTS
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Keep.
```

```text
=== raviteja2018otfs ===
EXISTENCE: YES  url=https://doi.org/10.1109/TWC.2018.2860011
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:14 - SUPPORTS
  - sections/Section1.tex:74 - SUPPORTS
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Keep.
```

```text
=== wei2021otfspromising ===
EXISTENCE: YES  url=https://doi.org/10.1109/MWC.001.2000408
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:14 - SUPPORTS
  - sections/Section1.tex:74 - SUPPORTS
  - sections/Section2.tex:22 - SUPPORTS
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Keep.
```

```text
=== benzine2023sparseafdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/GLOBECOM54140.2023.10437010
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:15 - SUPPORTS
  - sections/Section1.tex:41 - SUPPORTS
  - sections/Section4.tex:77 - SUPPORTS
  - sections/Section4.tex:99 - SUPPORTS
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Keep.
```

```text
=== rou2024otfstoafdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/MSP.2024.3422653
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:15 - WEAK - It supports OTFS/AFDM comparative sparse/effective-channel structure, but it is not primarily a sparse-recovery CE paper.
  - sections/Section1.tex:41 - WRONG - It is an SPM ISAC/comparative survey, not "subsequent channel-estimation literature" assuming EP.
VERDICT: REPLACE
AXIS_FAILURES: [CONTEXT]
NOTE: Use Rou for waveform comparison only; replace in the EP-CE literature sentence with direct AFDM CE papers.
```

```text
=== yin2024drceafdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/TWC.2024.3408458
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:41 - SUPPORTS
  - sections/Section1.tex:69 - SUPPORTS
  - sections/Section4.tex:102 - WRONG - DRCE is a low-complexity diagonal-reconstruction / linear-algebra CE method, NOT a learned estimator.
VERDICT: FIX
AXIS_FAILURES: [CONTEXT]
NOTE: Remove "learned" from the Yin table row or split learned attention-based work into a separate citation.
```

```text
=== yin2022fractionaldopplerafdm ===
EXISTENCE: NO  url=https://arxiv.org/abs/2206.12822
METADATA:
  authors: wrong - claimed arXiv ID corresponds to Yin/Wei/Tang/Yang DRCE; the actual "Pilot-Aided Channel Estimation..." paper is by Haoran Yin and Yanqun Tang
  title:   wrong - arXiv:2206.12822 is the DRCE paper, not the pilot-aided one
  year:    wrong/ambiguous - pilot-aided conf paper is 2022; arXiv item became TWC 2024 DRCE
  venue:   wrong - pilot-aided paper should be IEEE/CIC ICCC 2022, pp. 308-313
  ids:     wrong - use DOI 10.1109/ICCC55456.2022.9880774 for the pilot-aided paper
CONTEXT:
  - sections/Section2.tex:37 - WEAK
  - sections/Section1.tex:69 - SUPPORTS (for the intended 2022 pilot-aided paper)
  - sections/Section1.tex:88 - SUPPORTS
  - sections/Section4.tex:102 - WRONG
VERDICT: REPLACE
AXIS_FAILURES: [EXISTENCE, METADATA, CONTEXT]
NOTE: Split into two entries: Yin & Tang ICCC 2022 for pilot-aided CE, and Yin et al. TWC 2024 for DRCE.
```

```text
=== qing2024spafdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/TVT.2024.3469380
METADATA:
  authors: wrong - should be Kai Zheng, Miaowen Wen, Tianqi Mao, Lixia Xiao, Zhaocheng Wang
  title:   correct
  year:    wrong - formal version is 2025
  venue:   wrong - should be IEEE TVT 74(2):3389-3394, 2025
  ids:     wrong/incomplete - add DOI 10.1109/TVT.2024.3469380; arXiv:2404.10232 is preprint
CONTEXT: all SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Rename the key from Qing to Zheng or correct all author metadata and formal venue.
```

```text
=== zhao2024gifreeafdm ===
EXISTENCE: YES  url=https://arxiv.org/abs/2404.01088
METADATA:
  authors: wrong - should be Yu Zhou, Haoran Yin, Nanhao Zhou, Yanqun Tang, Xiaoying Zhang, Weijie Yuan
  title:   correct
  year:    correct
  venue:   correct as arXiv preprint; no formal migration found
  ids:     wrong - subject is eess.SP (not cs.IT); arXiv DOI is 10.48550/arXiv.2404.01088
CONTEXT:
  - sections/Section1.tex:46 - SUPPORTS
  - sections/Section4.tex:79 - SUPPORTS
  - sections/Section4.tex:101 - WEAK - "GI-free SP-like" is imprecise: it is pilot-aided GI-free, not superimposed-pilot in the Zheng/Qing sense.
VERDICT: FIX
AXIS_FAILURES: [METADATA, CONTEXT]
NOTE: Correct authors and label it "GI-free pilot-aided", not "SP-like".
```

```text
=== afdm2025jointcesd ===
EXISTENCE: NO  url=https://www.sciencedirect.com/science/article/abs/pii/S187449072400315X
METADATA:
  authors: wrong - should be Pengfei Huang, Qiang Li, Dong Huang, Junfeng Wang
  title:   wrong - should be "Channel estimation and symbol detection for AFDM over doubly selective fading channels"
  year:    correct: 2025
  venue:   wrong/incomplete - Physical Communication, vol. 69, article 102597
  ids:     wrong - DOI should be 10.1016/j.phycom.2024.102597; PII S187449072400315X is correct
CONTEXT:
  - sections/Section1.tex:52 - SUPPORTS
  - sections/Section1.tex:88 - SUPPORTS
  - sections/Section4.tex:105 - WRONG - "Wang et al.", title, and "none/no learning" are wrong; the paper includes a DNN receiver and GI-free iterative receiver.
VERDICT: REPLACE
AXIS_FAILURES: [EXISTENCE, METADATA, CONTEXT]
NOTE: Replace the BibTeX with the Huang et al. Physical Communication article and revise the table row.
```

```text
=== ma2024oversampledafdm ===
EXISTENCE: YES  url=https://arxiv.org/abs/2410.05088
METADATA:
  authors: wrong - should be K. R. R. Ranasinghe, Yao Ge, Giuseppe T. F. de Abreu, Yong Liang Guan
  title:   wrong - "Low Complexity Joint Channel Estimation and Data Detection for AFDM Receivers With Oversampling"
  year:    correct
  venue:   correct as arXiv preprint
  ids:     correct arXiv ID; add DOI 10.48550/arXiv.2410.05088
CONTEXT: all SUPPORTS (with author label "Ma et al." being wrong)
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Correct title/authors and avoid "Ma et al."
```

```text
=== zhou2024msmlafdm ===
EXISTENCE: YES  url=https://doi.org/10.1109/GLOBECOM52923.2024.10901055
METADATA:
  authors: wrong - should be Rongyou Cao, Yuheng Zhong, Jiangbin Lyu, Deqing Wang, Liqun Fu
  title:   wrong - should be "AFDM Channel Estimation in Multi-Scale Multi-Lag Channels"
  year:    correct
  venue:   wrong - presented at IEEE GLOBECOM 2024 (arXiv:2405.02660 v2 also exists)
  ids:     correct arXiv ID; add DOI 10.1109/GLOBECOM52923.2024.10901055
CONTEXT: all SUPPORTS (with author label "Zhou et al." being wrong)
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Correct title/authors and cite the GLOBECOM DOI.
```

```text
=== kaleh2005zadoffchu ===
EXISTENCE: YES  url=https://doi.org/10.1109/18.144727
METADATA:
  authors: correct (Popović)
  title:   wrong - actual Popović 1992 title is "Generalized chirp-like polyphase sequences with optimum correlation properties"
  year:    correct (1992) — the cite-key prefix "kaleh2005" is misleading
  venue:   correct
  ids:     correct
CONTEXT: SUPPORTS - Popović 1992 is a valid CAZAC/Zadoff-Chu/GCL sequence reference.
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Rename the key and fix the title; consider citing Chu 1972 for the original Zadoff-Chu sequence.
```

```text
=== tropp2007signal ===
EXISTENCE: YES  url=https://doi.org/10.1109/TIT.2007.909108
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:75 - SUPPORTS
  - sections/Section2.tex:314 - SUPPORTS
VERDICT: KEEP
AXIS_FAILURES: []
NOTE: Keep.
```

```text
=== candes2006cs ===
EXISTENCE: YES  url=https://doi.org/10.4171/022-3/69
METADATA:
  authors/title/year/venue: correct
  ids: incomplete — add DOI 10.4171/022-3/69
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Add the DOI.
```

```text
=== wymeersch2007iterativereceiver ===
EXISTENCE: YES  url=https://doi.org/10.1017/CBO9780511619199
METADATA: ids incomplete — add book DOI 10.1017/CBO9780511619199
CONTEXT:
  - sections/Section1.tex:24 - SUPPORTS
  - sections/Section1.tex:77 - SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Add the Cambridge book DOI.
```

```text
=== donoho2009amp ===
EXISTENCE: YES  url=https://doi.org/10.1073/pnas.0909892106
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:24 - WRONG - AMP for compressed sensing does not generally support "iterate between channel estimation and symbol detection."
  - sections/Section1.tex:77 - WEAK - It supports approximate message passing for CS, not generic MP-BP/factor-graph detection.
VERDICT: REPLACE
AXIS_FAILURES: [CONTEXT]
NOTE: Replace with Wymeersch / factor-graph / turbo-equalization or a direct iterative CE+SD receiver paper.
```

```text
=== orozco2011superimposed ===
EXISTENCE: NO  url=UNCERTAIN
METADATA: title/authors/venue/ids unverified — DOI 10.1109/TSP.2011.2159595 did not resolve in lookup
CONTEXT: WEAK across all three uses — claims true in SP literature but this exact citation appears unverified
VERDICT: REMOVE
AXIS_FAILURES: [EXISTENCE, METADATA, CONTEXT]
NOTE: Replace with verified superimposed-training references (e.g. Tugnait & Luo 2003 IEEE TSP, or Hoeher & Tufvesson 1999).
HUMAN-REVIEW FLAG: Likely a real paper with bad metadata — verify Orozco-Lugo et al. before removing wholesale.
```

```text
=== tugnait2006superimposed ===
EXISTENCE: NO  url=UNCERTAIN
METADATA: title/authors/venue/ids unverified — DOI 10.1109/TWC.2006.05139 did not resolve in lookup
CONTEXT: WEAK across all three uses
VERDICT: REMOVE
AXIS_FAILURES: [EXISTENCE, METADATA, CONTEXT]
NOTE: Replace with a verifiable Tugnait superimposed-training paper.
HUMAN-REVIEW FLAG: Tugnait has many SP papers; the bib-key may target a real paper with wrong DOI.
```

```text
=== monga2021unrolling ===
EXISTENCE: YES  url=https://doi.org/10.1109/MSP.2020.3016905
METADATA: all correct
CONTEXT: SUPPORTS
VERDICT: KEEP
NOTE: Keep.
```

```text
=== he2020modeldrivenmimo ===
EXISTENCE: YES  url=https://doi.org/10.1109/TSP.2020.2976585
METADATA: all correct
CONTEXT:
  - sections/Section1.tex:76 - WEAK - It is MIMO-detection-focused, but it also explicitly investigates joint MIMO CE+SD; blanket "detection-only" overstates the case.
VERDICT: FIX
AXIS_FAILURES: [CONTEXT]
NOTE: Phrase as "mostly MIMO-focused; some include joint CE+SD" rather than detection-only.
```

```text
=== he2020oampnet ===
EXISTENCE: NO  url=https://arxiv.org/abs/1907.09439
METADATA:
  authors: wrong - actual paper authors are He, Wen, Jin, Li (4 authors), not 6
  title:   wrong - actual title is "Model-Driven Deep Learning for MIMO Detection" (this is a DUPLICATE of he2020modeldrivenmimo)
  year:    correct
  venue:   wrong - should be IEEE TSP 68:1702-1715, NOT IEEE JSTSP 14(1):5-20
  ids:     wrong - DOI 10.1109/JSTSP.2019.2962214 was not verified
CONTEXT:
  - sections/Section1.tex:76 - WRONG - This is a duplicate/misdescribed entry; the citation contradicts itself because OAMP-Net would be an exception to "detection-only".
VERDICT: REMOVE
AXIS_FAILURES: [EXISTENCE, METADATA, CONTEXT]
NOTE: Remove this duplicate entry. If OAMP-Net is intended, locate the actual OAMP-Net paper (He et al. 2018 GlobalSIP / 2020 TSP) and re-cite.
HUMAN-REVIEW FLAG: The bib title "Model-Driven Deep Learning for Joint MIMO Channel Estimation and Signal Detection" matches a real He et al. JSTSP 2020 paper (DOI 10.1109/JSTSP.2019.2962214) — the reviewer may have failed to resolve the DOI. Verify manually before removal.
```

```text
=== balatsoukasstimming2019deepunfolding ===
EXISTENCE: YES  url=https://doi.org/10.1109/SiPS47522.2019.9020494
METADATA:
  venue: should be inproceedings entry, IEEE Workshop on Signal Processing Systems (SiPS) 2019, pp. 266-271
  others: correct
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Change entry type/venue fields and add pages.
```

```text
=== shlezinger2021deepsic ===
EXISTENCE: YES  url=https://doi.org/10.1109/TWC.2020.3032663
METADATA:
  authors: ordering issue noted by reviewer (Nir Shlezinger, Rong Fu, Yonina C. Eldar) — the bib's "Fu, Rong" is BibTeX-correct family-first; verify final-name rendering in main.bbl
  others: correct
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: The "Fu, Rong" entry is BibTeX-canonical; the reviewer's flag may be a false positive but worth a visual check of the rendered bibliography.
```

```text
=== khani2020mmnet ===
EXISTENCE: YES  url=https://doi.org/10.1109/TWC.2020.2996144
METADATA:
  venue: wrong - should be IEEE TWC 19(8):5635-5648, NOT a conference "ICMLC"
  ids:   wrong - DOI should be 10.1109/TWC.2020.2996144 (NOT 10.1109/TWC.2020.2991166 currently in bib)
  others: correct
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Convert from inproceedings to TWC journal article and fix DOI/pages.
```

```text
=== xu2024detecttolearn ===
EXISTENCE: YES  url=https://doi.org/10.1109/TCOMM.2023.3292468
METADATA: all correct
CONTEXT: SUPPORTS
VERDICT: KEEP
NOTE: Keep.
```

```text
=== kschischang2001factorgraph ===
EXISTENCE: YES  url=https://doi.org/10.1109/18.910572
METADATA: all correct
CONTEXT: SUPPORTS
VERDICT: KEEP
NOTE: Keep.
```

```text
=== elfwing2018silu ===
EXISTENCE: YES  url=https://doi.org/10.1016/j.neunet.2017.12.012
METADATA: venue field — should be @article journal=Neural Networks, NOT @inproceedings booktitle=Neural Networks
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Change entry type to @article and use journal field.
```

```text
=== loshchilov2019adamw ===
EXISTENCE: YES  url=https://openreview.net/forum?id=Bkg6RiCqY7
METADATA: all correct/acceptable
CONTEXT: SUPPORTS
VERDICT: KEEP
NOTE: Keep; optionally add OpenReview URL.
```

```text
=== clopper1934ci ===
EXISTENCE: YES  url=https://doi.org/10.1093/biomet/26.4.404
METADATA: ids incomplete — add DOI 10.1093/biomet/26.4.404
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Add the DOI.
```

```text
=== mcnemar1947paired ===
EXISTENCE: YES  url=https://doi.org/10.1007/BF02295996
METADATA: ids incomplete — add DOI 10.1007/BF02295996
CONTEXT: SUPPORTS
VERDICT: FIX
AXIS_FAILURES: [METADATA]
NOTE: Add the DOI.
```

```text
=== SUMMARY ===
KEEP: 13
FIX: 18
REPLACE: 4
REMOVE: 3
TOP_RISKS:
- afdm2025jointcesd is a wrong-attribution entry (real paper is Huang et al. 2025, not Wang et al.); the table cell "no learning" is also factually wrong because the actual paper includes a DNN receiver. Highest credibility risk.
- yin2022fractionaldopplerafdm uses an arXiv ID that resolves to a different paper (the DRCE paper), creating a self-conflict with yin2024drceafdm.
- Five recent AFDM bib entries (qing/zhao/ma/zhou/yin22) attribute the work to the wrong authors. The author labels in Section 4 tables propagate the error visibly.
- donoho2009amp is wrong-context: cited under "iterate CE and SD" and "MP-BP building block", but AMP is a CS algorithm, not a generic factor-graph receiver primitive.
- he2020oampnet appears to be a duplicate/mis-described entry of he2020modeldrivenmimo; possibly redirects to the wrong paper. Manual verification needed before removal.
- orozco2011superimposed and tugnait2006superimposed could not be web-verified; the reviewer flagged REMOVE but they are likely real refs with wrong metadata — manual lookup recommended before deletion.
```
