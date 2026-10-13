# Citation Audit Verdict — AFDM final report (run02)

## Top-level summary

* Total entries: 49 (46 cited, 3 uncited)
* Counts: KEEP=45, FIX=1, REPLACE=3, REMOVE=0
* Top-level verdict: WARN
* One-line summary: the bibliography is mostly real and usable, but three wrong-context uses would be credibility-risky in review: `afdm2025jointcesd`, `he2020oampnet`, and `tugnait2006superimposed`; one metadata record, `yin2025afdmoverview`, needs final publication details.
* Audit basis: I followed the attached run02 oracle specification and checked the 89 citation invocations listed in the attached context ledger.
* Accepted cite-key-stability mismatches, not counted as errors by themselves: `qing2024spafdm` → first author Zheng; `zhao2024gifreeafdm` → first author Zhou; `ma2024oversampledafdm` → first author Ranasinghe; `zhou2024msmlafdm` → first author Cao; `cui2007superimposed` → year 2011; `liang2011iterativesp` → year 2006; `kaleh2005zadoffchu` → Popović 1992.

## Critical findings (REMOVE / REPLACE)

1. **`afdm2025jointcesd` — REPLACE.** The paper exists, but the report currently merges two distinct contributions into one: a DNN-based receiver and a GI-free iterative receiver. The Section1 and Section4 wording says or implies "GI-free iterative loop with a DNN-aided detector," which is not the clean canonical characterization. Rewrite as two designs, not one combined "GI-free / DNN-aided" design.

2. **`he2020oampnet` — REPLACE.** The bib record duplicates the 2019 survey paper already present as `he2019modeldrivensurvey`, but Section1 cites it as a model-driven MIMO detector. Use `he2020modeldrivenmimo` for the detector, or replace this key with a real distinct OAMP-Net/OAMP-Net2 source.

3. **`tugnait2006superimposed` — REPLACE.** Metadata is valid for Tugnait & Meng 2006, but Section1 says "Tugnait and Luo" and attributes the OFDM CRB/equispaced-pilot-placement result to that citation. That result is supported by Cui & Tellambura; Tugnait & Meng supports superimposed-training performance/allocation/synchronization, not the exact sentence as written.

## Per-entry verdicts

### `stojanovic2009uwa`
* VERDICT: KEEP
* EXISTENCE: EXISTS (DOI-indexed record for "Underwater Acoustic Communication Channels: Propagation Models and Statistical Characterization")
* METADATA: all correct
* CONTEXT: Section1.tex:14 SUPPORTS; Section1.tex:176 SUPPORTS
* ACTION: Keep unchanged.

### `preisig2007uwa`
* VERDICT: KEEP
* EXISTENCE: EXISTS (ACM DL DOI record for "Acoustic Propagation Considerations for Underwater Acoustic Communications Network Development")
* METADATA: all correct
* CONTEXT: Section1.tex:14 SUPPORTS; Section1.tex:179 SUPPORTS
* ACTION: Keep unchanged.

### `huang2010uwamimoofdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Springer/EURASIP MIMO-OFDM UWA iterative sparse CE/decoding paper)
* METADATA: all correct
* CONTEXT: Section1.tex:19 SUPPORTS; Section1.tex:183 SUPPORTS
* ACTION: Keep unchanged.

### `berger2010uwasparse`
* VERDICT: KEEP
* EXISTENCE: EXISTS (IEEE TSP 58(3):1708-1721, DOI 10.1109/TSP.2009.2038424)
* METADATA: all correct
* CONTEXT: Section1.tex:19 SUPPORTS; Section1.tex:180 SUPPORTS; Section2.tex:274 SUPPORTS
* ACTION: Keep unchanged.

### `tropp2007signal`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Tropp & Gilbert OMP recovery)
* METADATA: all correct
* CONTEXT: Section1.tex:35 SUPPORTS; Section1.tex:104 SUPPORTS; Section2.tex:274 SUPPORTS; Appendices/Appendix.tex:126 SUPPORTS
* ACTION: Keep unchanged.

### `donoho2009amp`
* VERDICT: KEEP
* EXISTENCE: EXISTS (PNAS, DOI 10.1073/pnas.0909892106)
* METADATA: all correct
* CONTEXT: UNCITED
* ACTION: Keep if retained for future AMP background; otherwise safe to remove as unused.

### `candes2006cs`
* VERDICT: KEEP
* EXISTENCE: EXISTS (EMS ICM 2006 Vol III, DOI 10.4171/022-3/69, pp. 1433-1452)
* METADATA: all correct
* CONTEXT: UNCITED
* ACTION: Keep if retained for compressed-sensing background; otherwise safe to remove as unused.

### `li2002channelestimationofdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Ye Li, IEEE TWC 1(1):67-75, DOI 10.1109/7693.975446)
* METADATA: all correct
* CONTEXT: UNCITED
* ACTION: Keep only if needed for OFDM CE background; otherwise remove as unused.

### `hadani2017otfs`
* VERDICT: KEEP
* EXISTENCE: EXISTS (WCNC 2017, DOI 10.1109/WCNC.2017.7925924)
* METADATA: all correct
* CONTEXT: Section1.tex:96 SUPPORTS; Section2.tex:17 SUPPORTS
* ACTION: Keep unchanged.

### `raviteja2018otfs`
* VERDICT: KEEP
* EXISTENCE: EXISTS (TWC/arXiv records for OTFS interference cancellation and iterative detection)
* METADATA: all correct
* CONTEXT: Section1.tex:96 SUPPORTS; Section1.tex:218 SUPPORTS
* ACTION: Keep unchanged.

### `wei2021otfspromising`
* VERDICT: KEEP
* EXISTENCE: EXISTS (IEEE Wireless Communications, DOI 10.1109/MWC.001.2000408)
* METADATA: all correct
* CONTEXT: Section1.tex:96 SUPPORTS; Section2.tex:17 SUPPORTS
* ACTION: Keep unchanged.

### `bemani2023afdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Bemani, Ksairi, Kountouris, DOI 10.1109/TWC.2023.3260906)
* METADATA: all correct
* CONTEXT: Section1.tex:25 SUPPORTS; Section1.tex:91 SUPPORTS; Section2.tex:17 SUPPORTS; Section4.tex:52 SUPPORTS
* ACTION: Keep unchanged.

### `benzine2023sparseafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (GLOBECOM/arXiv "Affine Frequency Division Multiplexing for Communications on Sparse Time-Varying Channels")
* METADATA: all correct
* CONTEXT: Section1.tex:102 SUPPORTS; Section4.tex:40 SUPPORTS; Section4.tex:53 SUPPORTS
* ACTION: Keep unchanged.

### `rou2024otfstoafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (IEEE Signal Processing Magazine 41(5):71-86, DOI 10.1109/MSP.2024.3422653)
* METADATA: all correct
* CONTEXT: Section1.tex:110 SUPPORTS (correctly used as comparative ISAC survey, not as primary EP citation)
* ACTION: Keep unchanged.

### `yin2024drceafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (MIMO-AFDM diagonal-reconstruction/fractional-Doppler paper)
* METADATA: all correct
* CONTEXT: Section1.tex:107 SUPPORTS; Section1.tex:207 SUPPORTS; Section2.tex:29 SUPPORTS; Section4.tex:40 SUPPORTS; Section4.tex:56 SUPPORTS
* ACTION: Keep unchanged.

### `yin2022fractionaldopplerafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Yin & Tang ICCC 2022, DOI 10.1109/ICCC55456.2022.9880774)
* METADATA: all correct
* CONTEXT: Section1.tex:99 SUPPORTS
* ACTION: Keep unchanged.

### `qing2024spafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (first author Kai Zheng, IEEE TVT 74(2):3389-3394, DOI 10.1109/TVT.2024.3469380)
* METADATA: all correct (cite-key prefix mismatch accepted)
* CONTEXT: Section1.tex:143 SUPPORTS; Section4.tex:40 SUPPORTS; Section4.tex:54 SUPPORTS; Section4.tex:77 SUPPORTS; Section5.tex:23 SUPPORTS
* ACTION: Keep unchanged; note cite-key prefix mismatch only.

### `zhao2024gifreeafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Yu Zhou et al., arXiv:2404.01088 "GI-Free Pilot-Aided Channel Estimation for AFDM Systems")
* METADATA: all correct (cite-key prefix mismatch accepted)
* CONTEXT: Section1.tex:154 SUPPORTS; Section4.tex:40 SUPPORTS; Section4.tex:55 SUPPORTS
* ACTION: Keep unchanged; note cite-key prefix mismatch only.

### `afdm2025jointcesd`
* VERDICT: REPLACE
* EXISTENCE: EXISTS (Huang, Li, Huang, Wang, *Physical Communication* 69, article 102597, DOI 10.1016/j.phycom.2024.102597)
* METADATA: all correct
* CONTEXT:
  * Section1.tex:160 — WRONG: source presents a DNN-based receiver and a GI-free iterative receiver as separate designs; sentence compresses them into "a joint AFDM receiver that combines a guard-interval-free iterative loop with a DNN-aided detector"
  * Section1.tex:249 — WEAK: supports "learned components at the detector" as one AFDM example, but not the exhaustive "so far" survey claim by itself
  * Section4.tex:59 — WRONG: row label "GI-free pilot / Joint CE+SD / DNN-aided" merges two axes that should be separated
* ACTION: Rewrite the prose and table row: "Huang et al. propose AFDM CE/SD receiver designs including a DNN-based receiver and a GI-free iterative receiver." Do not describe the paper as one GI-free DNN-aided receiver.

### `ma2024oversampledafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Ranasinghe et al., arXiv:2410.05088)
* METADATA: all correct (cite-key prefix mismatch accepted; first author is Ranasinghe)
* CONTEXT: Section1.tex:193 SUPPORTS; Section4.tex:35 SUPPORTS; Section4.tex:40 SUPPORTS; Section4.tex:57 SUPPORTS
* ACTION: Keep unchanged; note cite-key prefix mismatch only.

### `zhou2024msmlafdm`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Cao et al., GLOBECOM 2024, pp. 1569-1574, DOI 10.1109/GLOBECOM52923.2024.10901055)
* METADATA: all correct (cite-key prefix mismatch accepted; first author is Cao)
* CONTEXT: Section1.tex:199 SUPPORTS; Section4.tex:40 SUPPORTS x2; Section4.tex:58 SUPPORTS; Section4.tex:75 WEAK; Section5.tex:25 SUPPORTS
* ACTION: Keep unchanged; note cite-key prefix mismatch only.

### `monga2021unrolling`
* VERDICT: KEEP
* EXISTENCE: EXISTS (IEEE SPM "Algorithm Unrolling", DOI 10.1109/MSP.2020.3016905)
* METADATA: all correct
* CONTEXT: Section1.tex:233 SUPPORTS; Section4.tex:40 SUPPORTS
* ACTION: Keep unchanged.

### `he2020modeldrivenmimo`
* VERDICT: KEEP
* EXISTENCE: EXISTS (IEEE TSP "Model-Driven Deep Learning for MIMO Detection", DOI 10.1109/TSP.2020.2976585)
* METADATA: all correct
* CONTEXT: Section1.tex:244 SUPPORTS
* ACTION: Keep unchanged.

### `he2020oampnet`
* VERDICT: REPLACE
* EXISTENCE: EXISTS — but the claimed metadata resolves to the 2019 survey already represented by `he2019modeldrivensurvey`, not a distinct OAMP-Net detector entry
* METADATA: bib metadata is the 2019 survey duplicate; problem is duplication and wrong contextual intent, not metadata resolvability
* CONTEXT: Section1.tex:244 — WRONG: cited as a model-driven MIMO detector, but bib entry is a survey duplicate; `he2020modeldrivenmimo` already covers the detector
* ACTION: Remove this key from the detector list, or replace with a real distinct OAMP-Net/OAMP-Net2 record. Do not keep both this and `he2019modeldrivensurvey` with identical metadata.

### `shlezinger2021deepsic`
* VERDICT: KEEP
* EXISTENCE: EXISTS (DeepSIC IEEE TWC 20(2):1349-1362, DOI 10.1109/TWC.2020.3032663)
* METADATA: all correct
* CONTEXT: Section1.tex:245 SUPPORTS
* ACTION: Keep unchanged.

### `balatsoukasstimming2019deepunfolding`
* VERDICT: KEEP
* EXISTENCE: EXISTS ("Deep Unfolding for Communications Systems: A Survey and Some New Directions", SiPS 2019, DOI 10.1109/SiPS47522.2019.9020494)
* METADATA: all correct
* CONTEXT: Section1.tex:234 SUPPORTS
* ACTION: Keep unchanged.

### `xu2024detecttolearn`
* VERDICT: KEEP
* EXISTENCE: EXISTS ("Detect to Learn", DOI 10.1109/TCOMM.2023.3292468)
* METADATA: all correct
* CONTEXT: Section1.tex:248 SUPPORTS
* ACTION: Keep unchanged.

### `khani2020mmnet`
* VERDICT: KEEP
* EXISTENCE: EXISTS ("Adaptive Neural Signal Detection for Massive MIMO", DOI 10.1109/TWC.2020.2996144)
* METADATA: all correct
* CONTEXT: Section1.tex:246 SUPPORTS
* ACTION: Keep unchanged.

### `wymeersch2007iterativereceiver`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Cambridge book *Iterative Receiver Design*, DOI 10.1017/CBO9780511619199)
* METADATA: all correct
* CONTEXT: Section1.tex:57 SUPPORTS; Section2.tex:145 SUPPORTS; Section2.tex:165 SUPPORTS
* ACTION: Keep unchanged.

### `kschischang2001factorgraph`
* VERDICT: KEEP
* EXISTENCE: EXISTS ("Factor Graphs and the Sum-Product Algorithm", DOI 10.1109/18.910572)
* METADATA: all correct
* CONTEXT: Section2.tex:145 SUPPORTS
* ACTION: Keep unchanged.

### `orozco2011superimposed`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Orozco-Lugo, Lara, McLernon "Channel Estimation Using Implicit Training", IEEE TSP 52(1):240-254, DOI 10.1109/TSP.2003.819993)
* METADATA: all correct (cite-key year mismatch accepted)
* CONTEXT: Section1.tex:43 SUPPORTS; Section1.tex:127 WEAK; Section2.tex:51 SUPPORTS
* ACTION: Keep unchanged; optionally soften Section1:127 to "studied training-power/design tradeoffs under implicit training."

### `tugnait2006superimposed`
* VERDICT: REPLACE
* EXISTENCE: EXISTS (Tugnait & Meng "On Superimposed Training for Channel Estimation: Performance Analysis, Training Power Allocation, and Frame Synchronization", IEEE TSP 54(2):752-765, DOI 10.1109/TSP.2005.861749)
* METADATA: bib correctly says Tugnait and Meng
* CONTEXT:
  * Section1.tex:43 — SUPPORTS: valid generic superimposed-training citation
  * Section1.tex:124 — WRONG: text says "Tugnait and Luo" but bib is Tugnait and Meng; the equispaced/equipowered OFDM CRB placement claim is supported by Cui & Tellambura, not this Tugnait paper
  * Section2.tex:51 — SUPPORTS: valid for pilot/data power allocation and superimposed-training tradeoff
* ACTION: Rewrite Section1:124. Use Cui & Tellambura for SP-OFDM ML/MMSE/CRB/equispaced placement; cite Tugnait & Meng separately for superimposed-training performance, power allocation, and synchronization.

### `kaleh2005zadoffchu`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Popović "Generalized Chirp-Like Polyphase Sequences with Optimum Correlation Properties", IEEE TIT 38(4):1406-1409, DOI 10.1109/18.144727)
* METADATA: all correct (cite-key prefix/year mismatch accepted)
* CONTEXT: Section2.tex:51 SUPPORTS
* ACTION: Keep unchanged; cite-key is misleading but intentionally stable.

### `yin2025afdmoverview`
* VERDICT: FIX
* EXISTENCE: EXISTS (AFDM overview, first author Haoran Yin, IEEE Wireless Communications)
* METADATA: missing volume/number/pages — should be `volume = {32}`, `number = {6}`, `pages = {200--208}`; doi correct; note: remove stale `in press`
* CONTEXT: Section1.tex:112 SUPPORTS
* ACTION: Update final publication metadata and remove `in press` note.

### `zhou2025afdmicsc`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Zhou et al., arXiv:2509.16643)
* METADATA: all correct
* CONTEXT: Section1.tex:112 SUPPORTS
* ACTION: Keep unchanged.

### `cui2007superimposed`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Cui & Tellambura, *European Trans. Telecommunications* 22(3):125-136, DOI 10.1002/ett.1461)
* METADATA: all correct (cite-key year mismatch accepted)
* CONTEXT: Section1.tex:123 SUPPORTS — directly supports SP-OFDM iterative CE/DD, CRB behavior, and optimal equally spaced pilot placement (the co-cited Tugnait phrase is the problem, not this citation)
* ACTION: Keep unchanged.

### `liang2011iterativesp`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Liang, Rave, Fettweis, ICC 2006 pp 3140-3145, DOI 10.1109/ICC.2006.255288)
* METADATA: all correct (cite-key year mismatch accepted)
* CONTEXT: Section1.tex:129 SUPPORTS
* ACTION: Keep unchanged.

### `mishra2022otfssp`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Mishra, Singh, Prasad, Budhiraja, IEEE TWC 21(4):2258-2274, DOI 10.1109/TWC.2021.3110659)
* METADATA: all correct
* CONTEXT: Section1.tex:137 SUPPORTS
* ACTION: Keep unchanged.

### `neelam2023otsmsp`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Sapta Girish Neelam and P. R. Sahu, IEEE Communications Letters 27(8):2147-2151, DOI 10.1109/LCOMM.2023.3281575)
* METADATA: all correct
* CONTEXT: Section1.tex:138 SUPPORTS — correctly labels "Neelam and Sahu" with no et al.
* ACTION: Keep unchanged.

### `cao2024spomp`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Zhe Cao, Miaowen Wen, Yu Huang, ICCT 2024 pp 1540-1544, DOI 10.1109/ICCT62411.2024.10946599)
* METADATA: all correct
* CONTEXT: Section1.tex:146 SUPPORTS
* ACTION: Keep unchanged.

### `junejo2018labomp`
* VERDICT: KEEP
* EXISTENCE: EXISTS (IEEE Access 6:74389-74399, DOI 10.1109/ACCESS.2018.2881766)
* METADATA: all correct
* CONTEXT: Section1.tex:186 SUPPORTS
* ACTION: Keep unchanged.

### `yuan2022uampotfs`
* VERDICT: KEEP
* EXISTENCE: EXISTS ("Iterative detection for OTFS modulation with unitary approximate message passing", DOI 10.1109/TWC.2021.3097173)
* METADATA: all correct
* CONTEXT: Section1.tex:222 SUPPORTS
* ACTION: Keep unchanged.

### `pu2024epotfs`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Pu et al., IET Signal Processing 2024, DOI 10.1049/2024/3256977)
* METADATA: all correct
* CONTEXT: Section1.tex:223 SUPPORTS
* ACTION: Keep unchanged.

### `zhuang2024amgnnotfs`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Zhuang et al., IEEE WCL 13(7):1913-1917, DOI 10.1109/LWC.2024.3395700)
* METADATA: all correct
* CONTEXT: Section1.tex:224 SUPPORTS
* ACTION: Keep unchanged.

### `gregor2010lista`
* VERDICT: KEEP
* EXISTENCE: EXISTS (Gregor & LeCun "Learning fast approximations of sparse coding", ICML 2010 pp 399-406)
* METADATA: all correct
* CONTEXT: Section1.tex:236 SUPPORTS
* ACTION: Keep unchanged.

### `he2019modeldrivensurvey`
* VERDICT: KEEP
* EXISTENCE: EXISTS (six-author "Model-driven deep learning for physical layer communications", DOI 10.1109/MWC.2019.1800447)
* METADATA: all correct, including Zongben Xu
* CONTEXT: Section1.tex:238 SUPPORTS
* ACTION: Keep unchanged.

### `mohammadtaheri2025deepgreedyunfolding`
* VERDICT: KEEP
* EXISTENCE: EXISTS (arXiv:2505.15661)
* METADATA: all correct
* CONTEXT: Section1.tex:252 SUPPORTS
* ACTION: Keep unchanged.

### `loshchilov2019adamw`
* VERDICT: KEEP
* EXISTENCE: EXISTS (ICLR/OpenReview "Decoupled Weight Decay Regularization")
* METADATA: all correct
* CONTEXT: Section2.tex:235 SUPPORTS
* ACTION: Keep unchanged.

### `elfwing2018silu`
* VERDICT: KEEP
* EXISTENCE: EXISTS ("Sigmoid-Weighted Linear Units for Neural Network Function Approximation in Reinforcement Learning", DOI 10.1016/j.neunet.2017.12.012)
* METADATA: all correct
* CONTEXT: Section2.tex:221 SUPPORTS
* ACTION: Keep unchanged.

## Author-cluster confirmation block — recent AFDM

* `qing2024spafdm`: verified first author **Kai Zheng**
* `zhao2024gifreeafdm`: verified first author **Yu Zhou**
* `ma2024oversampledafdm`: verified first author **Kuranage Roche Rayan Ranasinghe**
* `zhou2024msmlafdm`: verified first author **Rongyou Cao**
* `afdm2025jointcesd`: verified first author **Pengfei Huang**
* `yin2022fractionaldopplerafdm`: verified first author **Haoran Yin**
* `yin2025afdmoverview`: verified first author **Haoran Yin**
* `zhou2025afdmicsc`: verified first author **Yu Zhou**
* `cao2024spomp`: verified first author **Zhe Cao**

## Source URLs (referenced in the original full-form Oracle response)

ScienceDirect S187449072400315X (afdm2025jointcesd); sites.google.com/site/chaokaiwen/research (he2019/2020 disambiguation); xplorestaging.ieee.org/document/1576999 (tugnait2006superimposed); SciSpace (stojanovic2009uwa); ACM DL 1347370 (preisig2007uwa); Springer 460379 (huang2010uwamimoofdm); Springer 11804-023-00358-2 (berger2010uwasparse); BPB sites.gatech.edu (tropp2007signal); PNAS pnas.0909892106 (donoho2009amp); EMS Press standalone/24 (candes2006cs); paperzz simplified-channel-estimation (li2002channelestimationofdm); Scholars Duke 1259298 (hadani2017otfs); Monash research (raviteja2018otfs); arXiv 2010.03344 (wei2021otfspromising); arXiv 2204.12798 (bemani2023afdm); arXiv 2306.07765 (benzine2023sparseafdm); KAIST AFDM/OTFS pure (rou2024otfstoafdm); CoLab DOI 10.1109/twc.2024.3408458 (yin2024drceafdm); CoLab ICCC55456.2022.9880774 (yin2022fractionaldopplerafdm); DBLP ZhengWMXW25 (qing2024spafdm); arXiv 2404.01088 (zhao2024gifreeafdm); arXiv 2410.05088 (ma2024oversampledafdm); arXiv 2405.02660 (zhou2024msmlafdm); Weizmann 09363511.pdf (monga2021unrolling); Imperial profiles geoffrey.li (he2020modeldrivenmimo); Weizmann 09242305.pdf (shlezinger2021deepsic); Eindhoven Research Portal (balatsoukasstimming2019deepunfolding); arXiv 2208.09287 (xu2024detecttolearn); SciSpace 14dux17alj (khani2020mmnet); Cambridge 07CB3BF39FBB7F62C827FBEEF2D7FACD (wymeersch2007iterativereceiver); Baidu Xueshu (kschischang2001factorgraph); SciSpace 3gch6mztcc (orozco2011superimposed); Academia 11414787 (cui2007superimposed via tugnait dependency); USPTO ptacts uspto downloads (kaleh2005zadoffchu); arXiv 2502.04735 (yin2025afdmoverview); arXiv 2509.16643 (zhou2025afdmicsc); DBLP 63/6952 (liang2011iterativesp); researchr MishraSPB22 (mishra2022otfssp); DBLP NeelamS23a (neelam2023otsmsp); xplorestaging conhome 1000099 (cao2024spomp); DBLP 204/7846 (junejo2018labomp); arXiv 2008.06688 (yuan2022uampotfs); ietresearch.onlinelibrary.wiley.com 3256977 (pu2024epotfs); arXiv 2402.10071 (zhuang2024amgnnotfs); yann.lecun.com gregor-icml-10.pdf (gregor2010lista); arXiv 2505.15661 (mohammadtaheri2025deepgreedyunfolding); OpenReview Bkg6RiCqY7 (loshchilov2019adamw); ScienceDirect S0893608017302976 (elfwing2018silu).
