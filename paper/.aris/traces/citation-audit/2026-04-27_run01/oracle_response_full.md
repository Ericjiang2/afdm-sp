# Citation Audit Verdict — AFDM final report

Audited against the attached reviewer bundle and its required existence/metadata/context rules. 

## Top-level summary

* Total entries: 37 (34 cited, 3 uncited)
* Counts: KEEP=30, FIX=4, REPLACE=1, REMOVE=2
* Top-level verdict: FAIL
* One-line summary: Most AFDM “known trap” fixes are now correct, but two superimposed-training/SP references are not verifiable as written, one fractional-Doppler citation is being used for a claim it does not establish, and four entries still need metadata correction.

## Critical findings (REMOVE / REPLACE)

1. **REMOVE — `orozco2011superimposed` and `tugnait2006superimposed`:** both are used as the main support for SP transmission and pilot/data power tradeoff, but I could not verify the exact title/DOI/venue combinations in the bib. The Orozco DBLP record shows related but different works, such as *Symbol-Blanking Superimposed Training for OFDM systems* and *Widely Linear System Estimation Using Superimposed Training*, not the cited IEEE TSP paper. For Tugnait/Luo, I found related superimposed-training work, including a 2003 ICASSP paper, and a 2006 TSP paper by Tugnait and Meng, not the cited TWC paper. ([DBLP][1])

2. **REPLACE — `yin2022fractionaldopplerafdm`:** the ICCC 2022 paper exists and is correctly identified as Yin & Tang, *Pilot-Aided Channel Estimation for AFDM in Doubly Dispersive Channels*, DOI `10.1109/ICCC55456.2022.9880774`; however, it is being used in several contexts as support for a discrete Dirichlet-kernel fractional-Doppler leakage model. The arXiv ID mentioned in the note, `2206.12822`, resolves to the later DRCE MIMO-AFDM paper, not the 2022 pilot-aided paper. ([Researchr][2])

3. **FIX — `preisig2007uwa`:** the cited UWA propagation paper exists, but the bib points to an IEEE Journal of Oceanic Engineering record/DOI that I could not verify. The 2007 record I found is *ACM SIGMOBILE Mobile Computing and Communications Review*, 11(4), pp. 2–10, DOI `10.1145/1347364.1347370`; the author is James/J. Preisig, not Josko Preisig. ([Academia][3])

4. **FIX — `stojanovic2009uwa`:** the paper and DOI are correct, but the second author is James/J. Preisig, not Josko Preisig. ([CoLab][4])

5. **FIX — `he2020oampnet`:** the cited title exists as the model-driven joint MIMO channel-estimation/signal-detection work, but the bib’s JSTSP DOI/volume/pages combination could not be verified as written and appears to conflate records. ([arXiv][5])

6. **FIX — `zhou2024msmlafdm`:** the GLOBECOM 2024 record is real and the first author is Cao, but the conference pages are missing; use pp. 1569–1574. ([arXiv][6])

## Per-entry verdicts

### `stojanovic2009uwa`

* VERDICT: FIX
* EXISTENCE: EXISTS — IEEE Communications Magazine paper verified at DOI `10.1109/MCOM.2009.4752682`. ([CoLab][4])
* METADATA:

  * author: wrong: should be **Milica Stojanovic and James Preisig** / **James C. Preisig**, not “Josko Preisig”.
  * title: correct.
  * year: correct.
  * journal/booktitle: correct.
  * volume/number/pages: correct.
  * doi: correct.
* CONTEXT:

  * Section1.tex:14 — SUPPORTS: establishes UWA multipath, low acoustic propagation speed, time variation, and bandwidth/channel impairments relevant to the delay-spread claim.
* ACTION: Correct the second author name; keep the citation.

### `preisig2007uwa`

* VERDICT: FIX
* EXISTENCE: WRONG_LOCATION — the intended propagation-considerations paper exists, but I verified it as an ACM SIGMOBILE Mobile Computing and Communications Review / ACM record, not the claimed IEEE JOE DOI. The likely correct 2007 record is *Acoustic Propagation Considerations for Underwater Acoustic Communications Network Development*, ACM SIGMOBILE Mobile Computing and Communications Review 11(4):2–10, DOI `10.1145/1347364.1347370`. ([Academia][3])
* METADATA:

  * author: wrong: should be **James Preisig** / **J. Preisig**, not “Josko C. Preisig”.
  * title: correct.
  * year: correct.
  * journal/booktitle: wrong: should be **ACM SIGMOBILE Mobile Computing and Communications Review** for the 2007 article record.
  * volume/number/pages: wrong: should be **11(4):2–10**.
  * doi: wrong: should be **10.1145/1347364.1347370** for the 2007 ACM MCCR article record.
* CONTEXT:

  * Section1.tex:14 — SUPPORTS: the paper is an appropriate UWA acoustic-propagation source for delay spread and channel-development constraints.
* ACTION: Replace the bibliographic record with the ACM/MCCR metadata above; keep the contextual use.

### `huang2010uwamimoofdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — EURASIP Journal on Advances in Signal Processing record verified at DOI `10.1155/2010/460379`. ([Springer][7])
* METADATA: author/title/year/journal/volume-pages/doi: correct.
* CONTEXT:

  * Section1.tex:19 — SUPPORTS: the paper treats UWA MIMO-OFDM, sparse channel estimation, iterative decoding/detection, and Doppler/multicarrier channel impairments.
* ACTION: Keep.

### `berger2010uwasparse`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Signal Processing 58(3):1708–1721, DOI `10.1109/TSP.2009.2038424`, verified. ([Frontiers][8])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:19 — SUPPORTS: directly relevant to sparse UWA multicarrier channel estimation and Doppler-induced multicarrier issues.
  * Section2.tex:274 — SUPPORTS: appropriate as the UWA sparse-recovery anchor for the serial sparse-estimation baseline.
* ACTION: Keep.

### `tropp2007signal`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Information Theory 53(12):4655–4666, DOI `10.1109/TIT.2007.909108`, verified. ([SciSpace][9])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:35 — SUPPORTS: primary OMP recovery reference.
  * Section2.tex:274 — SUPPORTS: appropriate for “classical sparse-recovery” but should be paired with UWA-specific Berger, as currently done.
* ACTION: Keep.

### `donoho2009amp`

* VERDICT: KEEP
* EXISTENCE: EXISTS — PNAS article *Message-Passing Algorithms for Compressed Sensing*, DOI `10.1073/pnas.0909892106`, verified. ([PNAS][10])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT: UNCITED.
* ACTION: Keep only if AMP is discussed elsewhere; otherwise optional pruning for bibliography economy.

### `candes2006cs`

* VERDICT: KEEP
* EXISTENCE: EXISTS — ICM/EMS record for *Compressive Sampling*, DOI `10.4171/022-3/69`, verified. ([EMS Press][11])
* METADATA: author/title/year/booktitle/volume/pages/doi: correct.
* CONTEXT: UNCITED.
* ACTION: Keep only if broad compressed-sensing background is desired; otherwise optional pruning.

### `li2002channelestimationofdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Wireless Communications 1(1):67–75, DOI `10.1109/7693.975446`, verified. ([SciSpace][12])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT: UNCITED.
* ACTION: Keep only if OFDM channel-estimation background is needed; otherwise optional pruning.

### `hadani2017otfs`

* VERDICT: KEEP
* EXISTENCE: EXISTS — WCNC 2017 paper verified at DOI `10.1109/WCNC.2017.7925924`. ([Scholars@Duke][13])
* METADATA: author/title/year/booktitle/pages/doi: correct.
* CONTEXT:

  * Section1.tex:32 — SUPPORTS: establishes OTFS as a two-dimensional delay-Doppler modulation framework.
  * Section2.tex:17 — SUPPORTS: appropriate OTFS baseline citation for the delay-Doppler grid comparison.
* ACTION: Keep.

### `raviteja2018otfs`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Wireless Communications 17(10):6501–6515, DOI `10.1109/TWC.2018.2860011`, verified. ([Monash University][14])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:32 — SUPPORTS: directly relevant OTFS detection/interference-cancellation source.
* ACTION: Keep.

### `wei2021otfspromising`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Wireless Communications 28(4):136–144, DOI `10.1109/MWC.001.2000408`, verified. ([Scinapse][15])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:32 — SUPPORTS: survey/tutorial support for OTFS as a next-generation delay-Doppler waveform.
  * Section2.tex:17 — SUPPORTS: appropriate support for OTFS time-frequency diversity framing.
* ACTION: Keep.

### `bemani2023afdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Wireless Communications 22(11):8214–8229, DOI `10.1109/TWC.2023.3260906`, verified. ([arXiv][16])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:25 — SUPPORTS: primary AFDM source.
  * Section1.tex:88 — SUPPORTS: supports AFDM for doubly dispersive channels and DAFT/chirp-transform framing.
  * Section2.tex:17 — SUPPORTS: supports the effective-channel/chirp-parameter description and AFDM’s diversity motivation.
  * Section4.tex:52 — WEAK: the table’s “EP / 2-path, integer Doppler / non-iterative” shorthand is directionally consistent with examples in the AFDM paper, but it compresses the paper’s broader AFDM contribution too narrowly.
* ACTION: Keep; optionally soften the table row to “AFDM / embedded-pilot CE examples / integer Doppler examples.”

### `benzine2023sparseafdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — GLOBECOM 2023 paper verified at DOI `10.1109/GLOBECOM54140.2023.10437010`. ([EURECOM][17])
* METADATA: author/title/year/booktitle/pages/doi: correct.
* CONTEXT:

  * Section1.tex:35 — SUPPORTS: directly supports sparse AFDM recovery over sparse time-varying channels.
  * Section1.tex:93 — SUPPORTS: supports sparse-recovery AFDM under embedded-pilot/guard structure.
  * Section4.tex:40 — SUPPORTS: appropriate prior-art anchor for the AFDM-OMP skeleton.
  * Section4.tex:53 — SUPPORTS: table row “AFDM / EP / sparse DD / OMP / none” is consistent.
* ACTION: Keep.

### `rou2024otfstoafdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Signal Processing Magazine 41(5):71–86, DOI `10.1109/MSP.2024.3422653`, verified. ([DBLP][18])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:35 — WEAK: appropriate as a comparative AFDM/OTFS survey, but not the primary source for OMP tractability; Benzine should carry that claim.
  * Section1.tex:97 — SUPPORTS: directly supports the claim that Rou et al. situate AFDM alongside OTFS in an ISAC/doubly dispersive waveform comparison.
* ACTION: Keep; in Section1.tex:35, phrase it as “survey context” rather than primary evidence for sparse-recovery tractability.

### `yin2024drceafdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Wireless Communications 23(10):14066–14079, DOI `10.1109/TWC.2024.3408458`, verified. ([CoLab][19])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:94 — SUPPORTS: directly supports diagonal-reconstructed CE for MIMO-AFDM with inter-Doppler interference.
  * Section1.tex:145 — SUPPORTS: supports fractional/inter-Doppler leakage and diagonal-reconstruction framing.
  * Section4.tex:40 — SUPPORTS: appropriate support for leakage beyond single-pass OMP.
  * Section4.tex:56 — SUPPORTS: table row’s “MIMO-AFDM / fractional Doppler / diagonal reconstruction” part is correct.
* ACTION: Keep.

### `yin2022fractionaldopplerafdm`

* VERDICT: REPLACE
* EXISTENCE: EXISTS — the ICCC 2022 paper exists at DOI `10.1109/ICCC55456.2022.9880774`, pp. 308–313. Also verified that arXiv `2206.12822` resolves to the related DRCE MIMO-AFDM work, not this ICCC pilot-aided paper. ([Researchr][2])
* METADATA:

  * author: correct.
  * title: correct.
  * year: correct.
  * booktitle: correct.
  * volume/number/pages: correct.
  * doi: correct.
  * note: correct in warning spirit, but should also mention the actual preprint for the ICCC paper is arXiv `2203.05781`, not `2206.12822`.
* CONTEXT:

  * Section1.tex:147 — WRONG: the paper supports pilot-aided AFDM CE, but the sentence claims it targets Dirichlet leakage that single-pass OMP fails to capture; that claim is better supported by the DRCE/inter-Doppler paper or by a derivation in the manuscript.
  * Section2.tex:29 — WRONG: the discrete Dirichlet-kernel/aliased-sinc expansion is not established by this citation as written.
  * Section4.tex:40 — WRONG: “The fractional-Doppler Dirichlet expansion follows Yin and Tang” is too specific for the verified ICCC record.
  * Section4.tex:56 — WEAK: the combined table row is defensible only because it also cites `yin2024drceafdm`; the 2022 citation alone should not be presented as “Diag. recon.”
* ACTION: Keep the entry as a pilot-aided AFDM CE reference, but replace the Dirichlet/leakage uses with `yin2024drceafdm` or a more precise fractional-Doppler/Dirichlet source; revise the table to separate Yin & Tang 2022 from DRCE 2024.

### `qing2024spafdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — verified as Kai Zheng et al., IEEE Transactions on Vehicular Technology 74(2):3389–3394, DOI `10.1109/TVT.2024.3469380`; earlier arXiv preprint also exists. ([DBLP][20])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:107 — SUPPORTS: the paper is specifically SP-AFDM CE with iterative CE/signal detection and no learning component.
  * Section4.tex:40 — SUPPORTS: appropriate for iterative joint estimation-detection under SP contamination.
  * Section4.tex:54 — SUPPORTS: table row “Zheng et al. / AFDM / SP / sparse DD / iterative CE+SD / none” is correct.
  * Section4.tex:77 — SUPPORTS: appropriate prior-art target for a future direct reimplementation.
  * Section5.tex:23 — SUPPORTS: same; correct as a future quantitative baseline.
* ACTION: Keep.

### `zhao2024gifreeafdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — verified as Yu Zhou et al., arXiv `2404.01088`, DOI `10.48550/arXiv.2404.01088`. ([arXiv][21])
* METADATA: author/title/year/arXiv journal field/doi: correct for an arXiv-only entry.
* CONTEXT:

  * Section1.tex:113 — SUPPORTS: paper is GI-free pilot-aided AFDM CE and describes iterative interference cancellation / CE / symbol detection.
  * Section4.tex:40 — SUPPORTS: supports the iterative-loop claim for a contaminated GI-free pilot setting.
  * Section4.tex:55 — SUPPORTS: table row “Zhou et al. / GI-free pilot-aided / sparse DD / iterative IC / none” is correct.
* ACTION: Keep.

### `afdm2025jointcesd`

* VERDICT: KEEP
* EXISTENCE: EXISTS — verified as Pengfei Huang, Qiang Li, Dong Huang, Junfeng Wang, *Physical Communication* 69, article 102597, DOI `10.1016/j.phycom.2024.102597`, PII `S187449072400315X`. ([ScienceDirect][22])
* METADATA: author/title/year/journal/volume-pages/doi: correct.
* CONTEXT:

  * Section1.tex:119 — SUPPORTS: the paper includes a DNN receiver and a GI-free iterative CE/SD/IC receiver, and is non-SP.
  * Section1.tex:166 — SUPPORTS: learned component appears at the detector/receiver side, not as an OMP support-refinement block.
  * Section4.tex:59 — SUPPORTS: table row “Joint CE+SD / DNN-aided / no SP” is supported.
* ACTION: Keep.

### `ma2024oversampledafdm`

* VERDICT: KEEP
* EXISTENCE: EXISTS — verified as Kuranage Roche Rayan Ranasinghe, Yao Ge, Giuseppe T. F. de Abreu, Yong Liang Guan, arXiv `2410.05088`, DOI `10.48550/arXiv.2410.05088`. ([arXiv][23])
* METADATA: author/title/year/arXiv journal field/doi: correct.
* CONTEXT:

  * Section1.tex:131 — SUPPORTS: supports oversampling as an AFDM receiver/CE-DD improvement independent of learning.
  * Section4.tex:35 — SUPPORTS: appropriate physical-layer motivation for using oversampling.
  * Section4.tex:40 — SUPPORTS: supports consistency with oversampled AFDM CE/DD.
  * Section4.tex:57 — SUPPORTS: table row “Oversampled AFDM / pilot-aided / sparse DD / iterative CE+DD / none” is consistent.
* ACTION: Keep.

### `zhou2024msmlafdm`

* VERDICT: FIX
* EXISTENCE: EXISTS — verified as Rongyou Cao et al., GLOBECOM 2024 paper on AFDM channel estimation in MSML UWA channels, DOI `10.1109/GLOBECOM52923.2024.10901055`; pages verified as 1569–1574. ([arXiv][6])
* METADATA:

  * author: correct.
  * title: correct.
  * year: correct.
  * booktitle: correct.
  * volume/number/pages: missing: should include **pp. 1569–1574**.
  * doi: correct.
* CONTEXT:

  * Section1.tex:138 — SUPPORTS: directly supports AFDM-OMP/channel estimation in MSML UWA channels.
  * Section4.tex:40 — SUPPORTS: supports the MSML/per-path time-scaling reference point.
  * Section4.tex:40 — SUPPORTS: second invocation supports the full broadband/per-path formulation contrast.
  * Section4.tex:58 — SUPPORTS: table row “Cao et al. / AFDM / pilot-aided / MSML / AFDM-OMP / none” is correct.
  * Section4.tex:75 — WEAK: the “real UWA propagation” sentence is directionally supported by MSML UWA modeling, but “per-frame Doppler jitter” is broader than the title/abstract-level evidence.
  * Section5.tex:25 — SUPPORTS: appropriate future-work direction toward the MSML formulation.
* ACTION: Add pages `1569--1574`; consider softening “per-frame Doppler jitter” unless the body of the paper explicitly models it.

### `monga2021unrolling`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Signal Processing Magazine 38(2):18–44, DOI `10.1109/MSP.2020.3016905`, verified. ([ScienceGate][24])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:157 — SUPPORTS: directly surveys algorithm unrolling/deep unfolding.
  * Section4.tex:40 — SUPPORTS: appropriate architectural template citation.
* ACTION: Keep.

### `he2020modeldrivenmimo`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Signal Processing 68:1702–1715, DOI `10.1109/TSP.2020.2976585`, verified. ([IEEE Signal Processing Society][25])
* METADATA: author/title/year/journal/volume-pages/doi: correct.
* CONTEXT:

  * Section1.tex:160 — SUPPORTS: correct example of model-driven deep learning for MIMO detection.
* ACTION: Keep.

### `he2020oampnet`

* VERDICT: FIX
* EXISTENCE: WRONG_LOCATION — the model-driven joint MIMO channel-estimation/signal-detection work exists as an arXiv/model-driven OAMP-Net2 line, but I could not verify the bib’s JSTSP `14(1):5–20` / DOI `10.1109/JSTSP.2019.2962214` combination as the canonical record for this exact title. ([arXiv][5])
* METADATA:

  * author: uncertain/wrong as written: the arXiv record I verified lists **Hengtao He, Chao-Kai Wen, Shi Jin, Geoffrey Ye Li** for the joint CE/SD title; the bib adds Gao and Xu.
  * title: correct for the intended arXiv work.
  * year: uncertain/wrong as written for the claimed JSTSP record.
  * journal/booktitle: wrong/uncertain: claimed IEEE JSTSP record not verified.
  * volume/number/pages: wrong/uncertain: claimed `14(1):5–20` not verified for this exact paper.
  * doi: wrong/uncertain: DOI did not verify for this exact title.
* CONTEXT:

  * Section1.tex:160 — SUPPORTS in substance: the intended work is a model-driven deep-learning MIMO/JCESD example, but the bibliography metadata must be corrected.
* ACTION: Replace with the verified arXiv metadata or find the exact published record and update all fields.

### `shlezinger2021deepsic`

* VERDICT: KEEP
* EXISTENCE: EXISTS — DeepSIC / deep soft interference-cancellation paper verified as a TWC MIMO detection work with DOI `10.1109/TWC.2020.3032663`. ([Weizmann Institute of Science][26])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:161 — SUPPORTS: correct example of learned/iterative soft interference cancellation for MIMO detection.
* ACTION: Keep.

### `balatsoukasstimming2019deepunfolding`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE SiPS 2019 paper pp. 266–271, DOI `10.1109/SiPS47522.2019.9020494`, verified. ([Eindhoven Tech Research Portal][27])
* METADATA: author/title/year/booktitle/pages/doi: correct.
* CONTEXT:

  * Section1.tex:158 — SUPPORTS: directly surveys deep unfolding for communications systems.
* ACTION: Keep.

### `xu2024detecttolearn`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Communications 72(1):146–161, DOI `10.1109/TCOMM.2023.3292468`, verified. ([NSF Public Access Repository][28])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:163 — SUPPORTS: correct example of attention/decision-feedback MIMO-OFDM receive processing.
* ACTION: Keep.

### `khani2020mmnet`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Wireless Communications 19(8):5635–5648, DOI `10.1109/TWC.2020.2996144`, verified. ([SciSpace][29])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section1.tex:162 — SUPPORTS: correct example of adaptive neural signal detection / MMNet for massive MIMO.
* ACTION: Keep.

### `wymeersch2007iterativereceiver`

* VERDICT: KEEP
* EXISTENCE: EXISTS — Cambridge University Press book *Iterative Receiver Design*, DOI `10.1017/CBO9780511619199`, verified. ([Cambridge University Press & Assessment][30])
* METADATA: author/title/year/publisher/address/doi: correct.
* CONTEXT:

  * Section1.tex:57 — SUPPORTS: appropriate general reference for iterative receiver design.
  * Section2.tex:145 — SUPPORTS: appropriate framework reference for iterative receiver/factor-graph-style detection.
  * Section2.tex:165 — WEAK: supports soft iterative receiver/BP-style approximations generally, but the exact Gaussian finite-alphabet projection details should be derived or cited more specifically if central.
* ACTION: Keep.

### `kschischang2001factorgraph`

* VERDICT: KEEP
* EXISTENCE: EXISTS — IEEE Transactions on Information Theory 47(2):498–519, DOI `10.1109/18.910572`, verified. ([University of Toronto Communication][31])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section2.tex:145 — SUPPORTS: primary factor-graph/sum-product reference.
* ACTION: Keep.

### `orozco2011superimposed`

* VERDICT: REMOVE
* EXISTENCE: HALLUCINATED — I could not verify a paper with the exact title *Optimum Training for Channel Estimation With Superimposed Pilots in OFDM*, authors Orozco-Lugo/Lara/McLernon, IEEE TSP 59(9):4434–4438, DOI `10.1109/TSP.2011.2159595`. DBLP shows related Orozco-Lugo superimposed-training papers, but not this record. ([DBLP][1])
* METADATA:

  * author: wrong/unverified.
  * title: wrong/unverified.
  * year: wrong/unverified.
  * journal/booktitle: wrong/unverified.
  * volume/number/pages: wrong/unverified.
  * doi: wrong/unverified.
* CONTEXT:

  * Section1.tex:43 — WRONG: the SP transmission claim is plausible, but this cited paper cannot be verified as written.
  * Section2.tex:51 — WRONG: the pilot/data power-split tradeoff needs a real SP/OFDM or superimposed-training source.
* ACTION: Remove and replace with verified superimposed-training references, e.g., a real OFDM superimposed-training paper and/or Tugnait-Meng/Yang-Kwak-style sources.

### `tugnait2006superimposed`

* VERDICT: REMOVE
* EXISTENCE: HALLUCINATED — I could not verify the exact title *Single-User Channel Estimation and Equalization With Superimposed Training*, authors Tugnait and Luo, IEEE TWC 5(9):2495–2506, DOI `10.1109/TWC.2006.05139`. I found related Tugnait superimposed-training works, including a 2003 ICASSP Tugnait/Luo paper and a 2006 IEEE TSP Tugnait/Meng paper, but not this record. ([Researchr][32])
* METADATA:

  * author: wrong/unverified.
  * title: wrong/unverified.
  * year: wrong/unverified.
  * journal/booktitle: wrong/unverified.
  * volume/number/pages: wrong/unverified.
  * doi: wrong/unverified.
* CONTEXT:

  * Section1.tex:43 — WRONG: cannot support the SP-transmission claim with this invalid record.
  * Section2.tex:51 — WRONG: cannot support the pilot/data power tradeoff with this invalid record.
* ACTION: Remove and replace with verified superimposed-training literature.

### `kaleh2005zadoffchu`

* VERDICT: KEEP
* EXISTENCE: EXISTS — Popović 1992 IEEE Transactions on Information Theory 38(4):1406–1409, DOI `10.1109/18.144727`, verified. ([Mindat][33])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct. Cite-key year is misleading but the bib note explains why.
* CONTEXT:

  * Section2.tex:51 — SUPPORTS: appropriate foundational generalized chirp-like/CAZAC/Zadoff-Chu-style sequence reference.
* ACTION: Keep; consider renaming the key in a future cleanup, but not required.

### `clopper1934ci`

* VERDICT: KEEP
* EXISTENCE: EXISTS — Biometrika 26(4):404–413, DOI `10.1093/biomet/26.4.404`, verified. ([OUP Academic][34])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section2.tex:267 — SUPPORTS: primary source for Clopper-Pearson exact binomial intervals.
* ACTION: Keep.

### `mcnemar1947paired`

* VERDICT: KEEP
* EXISTENCE: EXISTS — Psychometrika 12(2):153–157, DOI `10.1007/BF02295996`, verified. ([Springer][35])
* METADATA: author/title/year/journal/volume-number-pages/doi: correct.
* CONTEXT:

  * Section2.tex:267 — SUPPORTS: primary source for McNemar’s paired correlated-proportions test.
* ACTION: Keep.

### `loshchilov2019adamw`

* VERDICT: KEEP
* EXISTENCE: EXISTS — ICLR 2019 OpenReview record verified for *Decoupled Weight Decay Regularization*. ([OpenReview][36])
* METADATA:

  * author/title/year/booktitle: correct.
  * volume/number/pages: not applicable.
  * doi: correct as absent; canonical ICLR/OpenReview record does not require one.
* CONTEXT:

  * Section2.tex:235 — SUPPORTS: primary AdamW/decoupled weight-decay source.
* ACTION: Keep.

### `elfwing2018silu`

* VERDICT: KEEP
* EXISTENCE: EXISTS — Neural Networks 107:3–11, DOI `10.1016/j.neunet.2017.12.012`, verified. ([ScienceDirect][37])
* METADATA: author/title/year/journal/volume-pages/doi: correct.
* CONTEXT:

  * Section2.tex:221 — SUPPORTS: primary SiLU / sigmoid-weighted linear unit reference.
* ACTION: Keep.

## Author cluster — recent AFDM (`qing2024spafdm`, `zhao2024gifreeafdm`, `ma2024oversampledafdm`, `zhou2024msmlafdm`, `afdm2025jointcesd`, `yin2022fractionaldopplerafdm`)

I explicitly verified the first-author names via fresh web lookups rather than relying on cite-key prefixes:

* `qing2024spafdm`: first author is **Kai Zheng**, not Qing; the Section 4 label “Zheng et al.” is correct. ([DBLP][20])
* `zhao2024gifreeafdm`: first author is **Yu Zhou**, not Zhao; the Section 4 label “Zhou et al.” is correct. ([arXiv][21])
* `ma2024oversampledafdm`: first author is **Kuranage Roche Rayan Ranasinghe**, not Ma; the Section 4 label “Ranasinghe et al.” is correct. ([arXiv][23])
* `zhou2024msmlafdm`: first author is **Rongyou Cao**, not Zhou; the Section 4 label “Cao et al.” is correct, but pages should be added. ([arXiv][6])
* `afdm2025jointcesd`: first author is **Pengfei Huang**; the paper is not Wang/Zhou/Chen. The Section 4 label “Huang et al.” is correct. ([ScienceDirect][38])
* `yin2022fractionaldopplerafdm`: first author is **Haoran Yin**, with **Yanqun Tang** as coauthor; the ICCC 2022 record exists, but the contexts overclaim what that paper establishes about Dirichlet leakage. ([Researchr][2])

[1]: https://dblp.org/pid/56/6882 "https://dblp.org/pid/56/6882"
[2]: https://researchr.org/publication/YinT22-1 "https://researchr.org/publication/YinT22-1"
[3]: https://www.academia.edu/97745294/Underwater_acoustic_communication_channels_Propagation_models_and_statistical_characterization "https://www.academia.edu/97745294/Underwater_acoustic_communication_channels_Propagation_models_and_statistical_characterization"
[4]: https://colab.ws/articles/10.1109%2Fmcom.2009.4752682 "https://colab.ws/articles/10.1109%2Fmcom.2009.4752682"
[5]: https://arxiv.org/pdf/1907.09439v1 "https://arxiv.org/pdf/1907.09439v1"
[6]: https://arxiv.org/abs/2405.02660 "https://arxiv.org/abs/2405.02660"
[7]: https://link.springer.com/article/10.1155/2010/460379 "https://link.springer.com/article/10.1155/2010/460379"
[8]: https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2024.1460388/full "https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2024.1460388/full"
[9]: https://scispace.com/papers/signal-recovery-from-random-measurements-via-orthogonal-5adhd8dwmq "https://scispace.com/papers/signal-recovery-from-random-measurements-via-orthogonal-5adhd8dwmq"
[10]: https://www.pnas.org/doi/pdf/10.1073/pnas.0909892106 "https://www.pnas.org/doi/pdf/10.1073/pnas.0909892106"
[11]: https://ems.press/books/standalone/24/561 "https://ems.press/books/standalone/24/561"
[12]: https://scispace.com/papers/simplified-channel-estimation-for-ofdm-systems-with-multiple-9cuuc3o75z "https://scispace.com/papers/simplified-channel-estimation-for-ofdm-systems-with-multiple-9cuuc3o75z"
[13]: https://scholars.duke.edu/publication/1259298 "https://scholars.duke.edu/publication/1259298"
[14]: https://research.monash.edu/en/publications/interference-cancellation-and-iterative-detection-for-orthogonal-/ "https://research.monash.edu/en/publications/interference-cancellation-and-iterative-detection-for-orthogonal-/"
[15]: https://www.scinapse.io/papers/3189209457 "https://www.scinapse.io/papers/3189209457"
[16]: https://arxiv.org/abs/2204.12798 "https://arxiv.org/abs/2204.12798"
[17]: https://www.eurecom.org/en/publication/7338 "https://www.eurecom.org/en/publication/7338"
[18]: https://dblp.org/rec/journals/spm/RouACGKGG24 "https://dblp.org/rec/journals/spm/RouACGKGG24"
[19]: https://colab.ws/articles/10.1109%2Ftwc.2024.3408458 "https://colab.ws/articles/10.1109%2Ftwc.2024.3408458"
[20]: https://dblp.org/rec/journals/tvt/ZhengWMXW25 "https://dblp.org/rec/journals/tvt/ZhengWMXW25"
[21]: https://arxiv.org/abs/2404.01088 "https://arxiv.org/abs/2404.01088"
[22]: https://www.sciencedirect.com/science/article/pii/S187449072400315X "https://www.sciencedirect.com/science/article/pii/S187449072400315X"
[23]: https://arxiv.org/abs/2410.05088 "https://arxiv.org/abs/2410.05088"
[24]: https://www.sciencegate.app/document/10.1109/msp.2020.3016905 "https://www.sciencegate.app/document/10.1109/msp.2020.3016905"
[25]: https://signalprocessingsociety.org/publications-resources/blog/model-driven-deep-learning-mimo-detection "https://signalprocessingsociety.org/publications-resources/blog/model-driven-deep-learning-mimo-detection"
[26]: https://www.weizmann.ac.il/math/yonina/sites/math.yonina/files/publications/09242305.pdf "https://www.weizmann.ac.il/math/yonina/sites/math.yonina/files/publications/09242305.pdf"
[27]: https://research.tue.nl/en/publications/deep-unfolding-for-communications-systems-a-survey-and-some-new-d/ "https://research.tue.nl/en/publications/deep-unfolding-for-communications-systems-a-survey-and-some-new-d/"
[28]: https://par.nsf.gov/biblio/10559076-detect-learn-structure-learning-attention-decision-feedback-mimo-ofdm-receive-processing "https://par.nsf.gov/biblio/10559076-detect-learn-structure-learning-attention-decision-feedback-mimo-ofdm-receive-processing"
[29]: https://scispace.com/papers/mimo-detection-methods-how-they-work-lecture-notes-14dux17alj "https://scispace.com/papers/mimo-detection-methods-how-they-work-lecture-notes-14dux17alj"
[30]: https://www.cambridge.org/core/books/iterative-receiver-design/07CB3BF39FBB7F62C827FBEEF2D7FACD "https://www.cambridge.org/core/books/iterative-receiver-design/07CB3BF39FBB7F62C827FBEEF2D7FACD"
[31]: https://www.comm.utoronto.ca/~frank/PUBgraphs.html "https://www.comm.utoronto.ca/~frank/PUBgraphs.html"
[32]: https://researchr.org/publication/TugnaitL03-0 "https://researchr.org/publication/TugnaitL03-0"
[33]: https://www.mindat.org/reference.php?id=14585996 "https://www.mindat.org/reference.php?id=14585996"
[34]: https://academic.oup.com/biomet/article-abstract/26/4/404/291538 "https://academic.oup.com/biomet/article-abstract/26/4/404/291538"
[35]: https://link.springer.com/article/10.1007/BF02295996 "https://link.springer.com/article/10.1007/BF02295996"
[36]: https://openreview.net/forum?id=Bkg6RiCqY7 "https://openreview.net/forum?id=Bkg6RiCqY7"
[37]: https://www.sciencedirect.com/science/article/pii/S0893608017302976 "https://www.sciencedirect.com/science/article/pii/S0893608017302976"
[38]: https://www.sciencedirect.com/journal/physical-communication/vol/69/suppl/C "https://www.sciencedirect.com/journal/physical-communication/vol/69/suppl/C"
