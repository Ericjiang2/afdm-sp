# Citation audit — AFDM final report (UoG/UESTC MS)

**Role**: You are an external bibliographic auditor. A senior IEEE-trained reviewer is about to read this paper. Your job is to find every error in the bibliography and every wrong-context citation BEFORE that reviewer does. You have web access. Use it. Do not pattern-match from training memory; do real DBLP / arXiv / IEEE Xplore / DOI / publisher lookups for every entry.

**Domain**: Underwater acoustic (UWA) channel estimation; AFDM (Affine Frequency Division Multiplexing); sparse recovery (OMP, AMP); deep unfolding receivers; iterative joint channel-estimation + symbol-detection.

## Inputs attached

1. `references.bib` — the bib file with 37 entries.
2. `contexts.txt` — for each cited key, every (file, line) where it appears, plus the surrounding sentence so you can judge whether the cite supports the claim.

## What I need from you (three layers per entry)

For **every** bib entry — including the uncited ones at the end of `contexts.txt`, mark uncited entries as `UNCITED` and skip context check — answer:

### 1. EXISTENCE
Does this paper actually exist at the claimed DOI / arXiv ID / venue? Verify with a real lookup. Output one of:
- `EXISTS` — found at the claimed location, give the verifying URL
- `WRONG_LOCATION` — paper exists but the claimed DOI/arXiv ID resolves to a different paper; give what the claimed ID actually resolves to AND where the intended paper lives
- `HALLUCINATED` — cannot find any paper matching this metadata anywhere
- `UNCERTAIN` — could not verify online

### 2. METADATA (per field)
For each of `author`, `title`, `year`, `journal/booktitle`, `volume/number/pages`, `doi`:
- `correct` — matches canonical record
- `wrong: should be ...` — gives the correct value
- `typo: ...` — minor diacritic/spelling issue
- `missing` — field absent and should be present (e.g., DOI for an IEEE journal article)

Be especially careful with **author lists** for the recent AFDM cluster (qing2024spafdm, zhao2024gifreeafdm, ma2024oversampledafdm, zhou2024msmlafdm, afdm2025jointcesd, yin2022fractionaldopplerafdm). The cite-key prefix (e.g., `qing2024spafdm`) does NOT necessarily match the actual first author.

### 3. CONTEXT (per use)
For each `(file, line)` invocation listed in `contexts.txt`, judge whether the cited paper actually establishes the claim that the surrounding sentence is making. Output one of:
- `SUPPORTS` — the cited paper directly establishes this claim
- `WEAK` — the cited paper is loosely related but not the primary source for this claim
- `WRONG` — the cited paper does not establish this claim or argues something different; give a one-sentence reason

This is the most important axis. A real paper used to support a wrong claim is more dangerous than a typo in author name.

## Per-entry verdict

After all three layers, give:
- `KEEP` — entry is clean, all uses appropriate
- `FIX` — metadata needs correction; uses are appropriate (no context errors)
- `REPLACE` — at least one wrong-context use; either rewrite the cite OR rewrite the surrounding sentence
- `REMOVE` — entry is hallucinated or fundamentally unsupportable

If the entry is `UNCITED`, just give EXISTENCE + METADATA + verdict (KEEP / FIX / REMOVE) and skip CONTEXT.

## Output format — STRICT

Produce a single Markdown document with this structure:

```
# Citation Audit Verdict — AFDM final report

## Top-level summary
- Total entries: 37 (34 cited, 3 uncited)
- Counts: KEEP=?, FIX=?, REPLACE=?, REMOVE=?
- Top-level verdict: PASS / WARN / FAIL
- One-line summary

## Critical findings (REMOVE / REPLACE)
[ranked by danger to credibility]

## Per-entry verdicts
[one section per bib key — give every one of the 37 keys]

### `<key>`
- VERDICT: KEEP/FIX/REPLACE/REMOVE
- EXISTENCE: ... (with verifying URL)
- METADATA: ...
- CONTEXT (per use):
  - Section1.tex:14 — SUPPORTS/WEAK/WRONG: ...
- ACTION: ...

## Author cluster — recent AFDM (qing2024spafdm, zhao2024gifreeafdm, ma2024oversampledafdm, zhou2024msmlafdm, afdm2025jointcesd, yin2022fractionaldopplerafdm)
[explicit confirmation that you actually verified each first-author name via web lookup, not from memory]
```

## Known traps (this audit was run once before; these are landmines from last time)

The previous audit found the following — **independently verify each one with fresh web lookups; don't take my word for it**:

1. `afdm2025jointcesd` — the bib used to claim authors "Wang/Zhou/Chen". The actual paper at PII `S187449072400315X` was reported as Pengfei Huang, Qiang Li, Dong Huang, Junfeng Wang, "Channel Estimation and Symbol Detection for AFDM Over Doubly Selective Fading Channels", Physical Communication v69 article 102597, DOI 10.1016/j.phycom.2024.102597. **Verify this is correct now.** Also: the paper allegedly includes a DNN-aided receiver and a GI-free iterative receiver — verify, because Section 4.tex:59 says "DNN-aided" in a comparison table.

2. `yin2022fractionaldopplerafdm` — the bib used to claim arXiv:2206.12822. **arXiv:2206.12822** allegedly resolves to the DRCE paper (Yin/Wei/Tang/Yang) which is also in the bib as `yin2024drceafdm`. The intended paper is supposedly Yin & Tang, IEEE/CIC ICCC 2022 pp. 308-313, DOI 10.1109/ICCC55456.2022.9880774. **Verify both directions** — what does arXiv:2206.12822 actually resolve to? Does the ICCC 2022 paper exist?

3. `qing2024spafdm` — bib used to claim authors "Qing/Yu/Wang/Gui", arXiv preprint. Reportedly the actual paper is Kai Zheng, Miaowen Wen, Tianqi Mao, Lixia Xiao, Zhaocheng Wang, IEEE TVT 74(2):3389-3394 2025, DOI 10.1109/TVT.2024.3469380. **Verify on IEEE Xplore.**

4. `zhao2024gifreeafdm` — bib used to claim authors "Zhao/Yuan/Li/Yuan". Reportedly the actual paper is Yu Zhou, Haoran Yin, Nanhao Zhou, Yanqun Tang, Xiaoying Zhang, Weijie Yuan, eess.SP arXiv preprint 2404.01088. **Verify on arXiv abstract page.**

5. `ma2024oversampledafdm` — bib used to claim "Ma/Chen/Chen". Reportedly Ranasinghe / Ge / de Abreu / Guan, arXiv 2410.05088. **Verify.**

6. `zhou2024msmlafdm` — bib used to claim "Zhou/Wang/Chen/Xiao". Reportedly Cao / Zhong / Lyu / Wang / Fu, IEEE GLOBECOM 2024 DOI 10.1109/GLOBECOM52923.2024.10901055. **Verify.**

7. `kaleh2005zadoffchu` — the cite-key year (2005) is misleading; the real entry is supposedly Popović 1992 IEEE TIT 38(4):1406-1409, DOI 10.1109/18.144727. **Verify.**

8. `khani2020mmnet` — venue. Real venue is supposedly IEEE TWC 19(8):5635-5648, 2020, DOI 10.1109/TWC.2020.2996144. **Verify.**

9. `balatsoukasstimming2019deepunfolding` — supposedly `@inproceedings` IEEE SiPS 2019 pp. 266-271, not `@article`. **Verify.**

10. `elfwing2018silu` — supposedly `@article` Neural Networks v107 pp 3-11, not inproceedings. **Verify.**

The current `references.bib` claims to have already applied many of these fixes. **Do not trust the current state — re-verify everything from scratch.**

## Other things to check critically

- **Wrong-context candidates**: any cite where the cited paper does not establish the surrounding claim. Pay particular attention to:
  - sparse-recovery references (tropp2007signal, berger2010uwasparse) used in places that need a different primitive
  - rou2024otfstoafdm (a survey of ISAC waveforms) used as a primary citation for embedded-pilot or waveform-design claims
  - wymeersch2007iterativereceiver and kschischang2001factorgraph used together: are both needed, or is one redundant?
  - Section 4.tex Table 1 (`tab:priorart`) — every row claims a specific axis ("EP", "SP", "GI-free", "Sparse DD", "DNN-aided", etc.). For each cited paper in the table, does the actual paper cover that axis?

- **Section 4 author labels**: every "Author et al." in Section4.tex must match the bib `author = {...}` field's first author. Flag any mismatch.

- **DOI format / resolvability**: every IEEE / Elsevier / ACM DOI should resolve. Spot-check resolvability for the recent AFDM entries.

## Reasoning effort

This is a **nightmare-difficulty** audit. Take your time. Use web search aggressively. If you can find a published version (IEEE Xplore, ACM DL, ScienceDirect), prefer it over arXiv. If arXiv only, use the abstract page.

Be honest. If you cannot verify online, say UNCERTAIN — do not guess.

When you finish, give the per-entry table for ALL 37 entries (no skipping the obvious ones — I want a complete ledger).


---

# `references.bib` (verbatim)

```bibtex
%% ----- Foundational UWA + sparse channel estimation -----

@article{stojanovic2009uwa,
  title   = {Underwater Acoustic Communication Channels: Propagation Models and Statistical Characterization},
  author  = {Stojanovic, Milica and Preisig, Josko},
  journal = {IEEE Communications Magazine},
  volume  = {47},
  number  = {1},
  pages   = {84--89},
  year    = {2009},
  doi     = {10.1109/MCOM.2009.4752682}
}

@article{preisig2007uwa,
  title   = {Acoustic Propagation Considerations for Underwater Acoustic Communications Network Development},
  author  = {Preisig, Josko C.},
  journal = {IEEE Journal of Oceanic Engineering},
  volume  = {32},
  number  = {1},
  pages   = {228--254},
  year    = {2007},
  doi     = {10.1109/JOE.2007.892637}
}

@article{huang2010uwamimoofdm,
  title   = {Iterative Sparse Channel Estimation and Decoding for Underwater {MIMO-OFDM}},
  author  = {Huang, Jie and Huang, Jianzhong and Berger, Christian R. and Zhou, Shengli and Willett, Peter},
  journal = {EURASIP Journal on Advances in Signal Processing},
  volume  = {2010},
  pages   = {1--11},
  year    = {2010},
  doi     = {10.1155/2010/460379}
}

@article{berger2010uwasparse,
  title   = {Sparse Channel Estimation for Multicarrier Underwater Acoustic Communication: From Subspace Methods to Compressed Sensing},
  author  = {Berger, Christian R. and Zhou, Shengli and Preisig, James C. and Willett, Peter},
  journal = {IEEE Transactions on Signal Processing},
  volume  = {58},
  number  = {3},
  pages   = {1708--1721},
  year    = {2010},
  doi     = {10.1109/TSP.2009.2038424}
}

%% ----- Sparse recovery / compressed sensing -----

@article{tropp2007signal,
  title   = {Signal Recovery From Random Measurements Via Orthogonal Matching Pursuit},
  author  = {Tropp, Joel A. and Gilbert, Anna C.},
  journal = {IEEE Transactions on Information Theory},
  volume  = {53},
  number  = {12},
  pages   = {4655--4666},
  year    = {2007},
  doi     = {10.1109/TIT.2007.909108}
}

@article{donoho2009amp,
  title   = {Message-Passing Algorithms for Compressed Sensing},
  author  = {Donoho, David L. and Maleki, Arian and Montanari, Andrea},
  journal = {Proceedings of the National Academy of Sciences},
  volume  = {106},
  number  = {45},
  pages   = {18914--18919},
  year    = {2009},
  doi     = {10.1073/pnas.0909892106}
}

@article{candes2006cs,
  title   = {Compressive Sampling},
  author  = {Cand{\`e}s, Emmanuel J.},
  journal = {Proceedings of the International Congress of Mathematicians},
  volume  = {3},
  pages   = {1433--1452},
  year    = {2006},
  doi     = {10.4171/022-3/69}
}

%% ----- OFDM / OTFS / AFDM waveforms -----

@article{li2002channelestimationofdm,
  title   = {Simplified Channel Estimation for {OFDM} Systems With Multiple Transmit Antennas},
  author  = {Li, Ye (Geoffrey)},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {1},
  number  = {1},
  pages   = {67--75},
  year    = {2002},
  doi     = {10.1109/7693.975446}
}

@inproceedings{hadani2017otfs,
  title     = {Orthogonal Time Frequency Space Modulation},
  author    = {Hadani, Ronny and Rakib, Shlomo and Tsatsanis, Michail and Monk, Anton and Goldsmith, Andrea J. and Molisch, Andreas F. and Calderbank, Robert},
  booktitle = {IEEE Wireless Communications and Networking Conference (WCNC)},
  pages     = {1--6},
  year      = {2017},
  doi       = {10.1109/WCNC.2017.7925924}
}

@article{raviteja2018otfs,
  title   = {Interference Cancellation and Iterative Detection for Orthogonal Time Frequency Space Modulation},
  author  = {Raviteja, Patchava and Phan, Khoa T. and Hong, Yi and Viterbo, Emanuele},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {17},
  number  = {10},
  pages   = {6501--6515},
  year    = {2018},
  doi     = {10.1109/TWC.2018.2860011}
}

@article{wei2021otfspromising,
  title   = {Orthogonal Time-Frequency Space Modulation: A Promising Next-Generation Waveform},
  author  = {Wei, Zhiqiang and Yuan, Weijie and Li, Shuangyang and Yuan, Jinhong and Bharatula, Ganesh and Hadani, Ronny and Hanzo, Lajos},
  journal = {IEEE Wireless Communications},
  volume  = {28},
  number  = {4},
  pages   = {136--144},
  year    = {2021},
  doi     = {10.1109/MWC.001.2000408}
}

@article{bemani2023afdm,
  title   = {Affine Frequency Division Multiplexing for Next Generation Wireless Communications},
  author  = {Bemani, Ali and Ksairi, Nassar and Kountouris, Marios},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {22},
  number  = {11},
  pages   = {8214--8229},
  year    = {2023},
  doi     = {10.1109/TWC.2023.3260906}
}

@inproceedings{benzine2023sparseafdm,
  title     = {Affine Frequency Division Multiplexing for Communications on Sparse Time-Varying Channels},
  author    = {Benzine, Wissal and Bemani, Ali and Ksairi, Nassar and Slock, Dirk},
  booktitle = {IEEE Global Communications Conference ({GLOBECOM})},
  pages     = {4921--4926},
  year      = {2023},
  doi       = {10.1109/GLOBECOM54140.2023.10437010}
}

@article{rou2024otfstoafdm,
  title   = {From Orthogonal Time-Frequency Space to Affine Frequency-Division Multiplexing: A Comparative Study of Next-Generation Waveforms for Integrated Sensing and Communications in Doubly Dispersive Channels},
  author  = {Rou, Hyeon Seok and {de Abreu}, Giuseppe T. F. and Choi, Junil and Gonz{\'a}lez G., David and Kountouris, Marios and Guan, Yong Liang and Gonsa, Osvaldo},
  journal = {IEEE Signal Processing Magazine},
  volume  = {41},
  number  = {5},
  pages   = {71--86},
  year    = {2024},
  doi     = {10.1109/MSP.2024.3422653}
}

@article{yin2024drceafdm,
  title   = {Diagonally Reconstructed Channel Estimation for {MIMO-AFDM} With Inter-Doppler Interference in Doubly Selective Channels},
  author  = {Yin, Haoran and Wei, Xizhang and Tang, Yanqun and Yang, Kai},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {23},
  number  = {10},
  pages   = {14066--14079},
  year    = {2024},
  doi     = {10.1109/TWC.2024.3408458}
}

%% ----- Recent AFDM references from Oracle-R1 review (new in Loop-13) -----

@inproceedings{yin2022fractionaldopplerafdm,
  title     = {Pilot-Aided Channel Estimation for {AFDM} in Doubly Dispersive Channels},
  author    = {Yin, Haoran and Tang, Yanqun},
  booktitle = {Proc. IEEE/CIC International Conference on Communications in China ({ICCC})},
  pages     = {308--313},
  year      = {2022},
  doi       = {10.1109/ICCC55456.2022.9880774},
  note      = {arXiv:2206.12822 originally indexes the related Diagonally Reconstructed CE work; pilot-aided AFDM CE was published at ICCC 2022.}
}

@article{qing2024spafdm,
  title   = {Channel Estimation for {AFDM} With Superimposed Pilots},
  author  = {Zheng, Kai and Wen, Miaowen and Mao, Tianqi and Xiao, Lixia and Wang, Zhaocheng},
  journal = {IEEE Transactions on Vehicular Technology},
  volume  = {74},
  number  = {2},
  pages   = {3389--3394},
  year    = {2025},
  doi     = {10.1109/TVT.2024.3469380},
  note    = {Earlier preprint: arXiv:2404.10232 [eess.SP]; cite-key prefix retained from initial preprint indexing.}
}

@article{zhao2024gifreeafdm,
  title   = {{GI-Free} Pilot-Aided Channel Estimation for Affine Frequency Division Multiplexing Systems},
  author  = {Zhou, Yu and Yin, Haoran and Zhou, Nanhao and Tang, Yanqun and Zhang, Xiaoying and Yuan, Weijie},
  journal = {arXiv preprint arXiv:2404.01088},
  year    = {2024},
  doi     = {10.48550/arXiv.2404.01088},
  note    = {arXiv:2404.01088 [eess.SP]; cite-key prefix retained from initial preprint indexing.}
}

@article{afdm2025jointcesd,
  title   = {Channel Estimation and Symbol Detection for {AFDM} Over Doubly Selective Fading Channels},
  author  = {Huang, Pengfei and Li, Qiang and Huang, Dong and Wang, Junfeng},
  journal = {Physical Communication},
  volume  = {69},
  pages   = {102597},
  year    = {2025},
  doi     = {10.1016/j.phycom.2024.102597},
  note    = {ScienceDirect PII S187449072400315X; includes a DNN-aided receiver and a GI-free iterative receiver.}
}

@article{ma2024oversampledafdm,
  title   = {Low Complexity Joint Channel Estimation and Data Detection for {AFDM} Receivers With Oversampling},
  author  = {Ranasinghe, Kuranage Roche Rayan and Ge, Yao and {de Abreu}, Giuseppe Thadeu Freitas and Guan, Yong Liang},
  journal = {arXiv preprint arXiv:2410.05088},
  year    = {2024},
  doi     = {10.48550/arXiv.2410.05088},
  note    = {arXiv:2410.05088 [eess.SP]; cite-key prefix retained from initial preprint indexing.}
}

@inproceedings{zhou2024msmlafdm,
  title     = {{AFDM} Channel Estimation in Multi-Scale Multi-Lag Channels},
  author    = {Cao, Rongyou and Zhong, Yuheng and Lyu, Jiangbin and Wang, Deqing and Fu, Liqun},
  booktitle = {Proc. IEEE Global Communications Conference ({GLOBECOM})},
  year      = {2024},
  doi       = {10.1109/GLOBECOM52923.2024.10901055},
  note      = {Companion arXiv:2405.02660; cite-key prefix retained from initial preprint indexing.}
}

%% ----- Deep-unfolding / model-driven receivers -----

@article{monga2021unrolling,
  title   = {Algorithm Unrolling: Interpretable, Efficient Deep Learning for Signal and Image Processing},
  author  = {Monga, Vishal and Li, Yuelong and Eldar, Yonina C.},
  journal = {IEEE Signal Processing Magazine},
  volume  = {38},
  number  = {2},
  pages   = {18--44},
  year    = {2021},
  doi     = {10.1109/MSP.2020.3016905}
}

@article{he2020modeldrivenmimo,
  title   = {Model-Driven Deep Learning for {MIMO} Detection},
  author  = {He, Hengtao and Wen, Chao-Kai and Jin, Shi and Li, Geoffrey Ye},
  journal = {IEEE Transactions on Signal Processing},
  volume  = {68},
  pages   = {1702--1715},
  year    = {2020},
  doi     = {10.1109/TSP.2020.2976585}
}

@article{he2020oampnet,
  title   = {Model-Driven Deep Learning for Joint {MIMO} Channel Estimation and Signal Detection},
  author  = {He, Hengtao and Jin, Shi and Wen, Chao-Kai and Gao, Feifei and Li, Geoffrey Ye and Xu, Zongben},
  journal = {IEEE Journal of Selected Topics in Signal Processing},
  volume  = {14},
  number  = {1},
  pages   = {5--20},
  year    = {2020},
  doi     = {10.1109/JSTSP.2019.2962214}
}

@article{shlezinger2021deepsic,
  title   = {{DeepSIC}: Deep Soft Interference Cancellation for Multiuser {MIMO} Detection},
  author  = {Shlezinger, Nir and Fu, Rong and Eldar, Yonina C.},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {20},
  number  = {2},
  pages   = {1349--1362},
  year    = {2021},
  doi     = {10.1109/TWC.2020.3032663}
}

@inproceedings{balatsoukasstimming2019deepunfolding,
  title     = {Deep Unfolding for Communications Systems: A Survey and Some New Directions},
  author    = {Balatsoukas-Stimming, Alexios and Studer, Christoph},
  booktitle = {Proc. IEEE International Workshop on Signal Processing Systems ({SiPS})},
  pages     = {266--271},
  year      = {2019},
  doi       = {10.1109/SiPS47522.2019.9020494}
}

@article{xu2024detecttolearn,
  title   = {Detect to Learn: Structure Learning With Attention and Decision Feedback for {MIMO-OFDM} Receive Processing},
  author  = {Xu, Jiarui and Li, Lianjun and Zheng, Lizhong and Liu, Lingjia},
  journal = {IEEE Transactions on Communications},
  volume  = {72},
  number  = {1},
  pages   = {146--161},
  year    = {2024},
  doi     = {10.1109/TCOMM.2023.3292468}
}

@article{khani2020mmnet,
  title   = {Adaptive Neural Signal Detection for Massive {MIMO}},
  author  = {Khani, Mehrdad and Alizadeh, Mohammad and Hoydis, Jakob and Fleming, Phil},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {19},
  number  = {8},
  pages   = {5635--5648},
  year    = {2020},
  doi     = {10.1109/TWC.2020.2996144},
  note    = {{MMNet}.}
}

%% ----- Factor graphs and iterative receivers -----

@book{wymeersch2007iterativereceiver,
  title     = {Iterative Receiver Design},
  author    = {Wymeersch, Henk},
  publisher = {Cambridge University Press},
  address   = {Cambridge, UK},
  year      = {2007},
  doi       = {10.1017/CBO9780511619199}
}

@article{kschischang2001factorgraph,
  title   = {Factor Graphs and the Sum-Product Algorithm},
  author  = {Kschischang, Frank R. and Frey, Brendan J. and Loeliger, Hans-Andrea},
  journal = {IEEE Transactions on Information Theory},
  volume  = {47},
  number  = {2},
  pages   = {498--519},
  year    = {2001},
  doi     = {10.1109/18.910572}
}

%% ----- Superimposed pilots in OFDM / SC -----

@article{orozco2011superimposed,
  title   = {Optimum Training for Channel Estimation With Superimposed Pilots in {OFDM}},
  author  = {Orozco-Lugo, Aldo G. and Lara, Mauricio M. and McLernon, Desmond C.},
  journal = {IEEE Transactions on Signal Processing},
  volume  = {59},
  number  = {9},
  pages   = {4434--4438},
  year    = {2011},
  doi     = {10.1109/TSP.2011.2159595}
}

@article{tugnait2006superimposed,
  title   = {Single-User Channel Estimation and Equalization With Superimposed Training},
  author  = {Tugnait, Jitendra K. and Luo, Weilin},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {5},
  number  = {9},
  pages   = {2495--2506},
  year    = {2006},
  doi     = {10.1109/TWC.2006.05139}
}

@article{kaleh2005zadoffchu,
  title   = {Generalized Chirp-Like Polyphase Sequences with Optimum Correlation Properties},
  author  = {Popovi{\'c}, Branislav M.},
  journal = {IEEE Transactions on Information Theory},
  volume  = {38},
  number  = {4},
  pages   = {1406--1409},
  year    = {1992},
  doi     = {10.1109/18.144727},
  note    = {Foundational Zadoff--Chu / generalized-chirp-like CAZAC sequence reference; cite-key prefix retained for back-compatibility.}
}

%% ----- Statistics used in evaluation -----

@article{clopper1934ci,
  title   = {The Use of Confidence or Fiducial Limits Illustrated in the Case of the Binomial},
  author  = {Clopper, Charles J. and Pearson, Egon S.},
  journal = {Biometrika},
  volume  = {26},
  number  = {4},
  pages   = {404--413},
  year    = {1934},
  doi     = {10.1093/biomet/26.4.404}
}

@article{mcnemar1947paired,
  title   = {Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages},
  author  = {McNemar, Quinn},
  journal = {Psychometrika},
  volume  = {12},
  number  = {2},
  pages   = {153--157},
  year    = {1947},
  doi     = {10.1007/BF02295996}
}

%% ----- Optimisation / training recipes cited in methods -----

@inproceedings{loshchilov2019adamw,
  title     = {Decoupled Weight Decay Regularization},
  author    = {Loshchilov, Ilya and Hutter, Frank},
  booktitle = {International Conference on Learning Representations ({ICLR})},
  year      = {2019}
}

@article{elfwing2018silu,
  title   = {Sigmoid-Weighted Linear Units for Neural Network Function Approximation in Reinforcement Learning},
  author  = {Elfwing, Stefan and Uchibe, Eiji and Doya, Kenji},
  journal = {Neural Networks},
  volume  = {107},
  pages   = {3--11},
  year    = {2018},
  doi     = {10.1016/j.neunet.2017.12.012}
}

```

---

# `contexts.txt` (verbatim)

# Citation contexts for AFDM final report

Total \cite{} invocations: 72
Unique cite-keys used: 34

Each entry below: cite-key, then every place it is used (file:line) with the surrounding sentence.

---

## `afdm2025jointcesd` (3 uses)

- **sections/Section1.tex:119** — m} reach a structurally similar conclusion via a guard-interval-free pilot-aided design with iterative interference cancellation; their formulation, however, departs from SP rather than addressing the pilot-data interference inside it, so the SP-specific estimation-limited floor at mid-to-high SNR is not part of the problem they solve. Adjacent to these CE-focused works, Huang \emph{et al.}~\cite{afdm2025jointcesd} propose a joint AFDM receiver that combines a guard-interval-free iterative loop with a DNN-aided detector --- demonstrating that learning-augmented joint AFDM receivers are tractable --- but their learning element is placed at the detector rather than at the channel-support-selection step, and the work targets neither an SP frame nor a UWA-style channel model.

- **sections/Section1.tex:166** — lation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn} --- and combines learned blocks with classical iterative receivers in a way that preserves the model-based skeleton. Within AFDM specifically, learned components have so far appeared at the detector~\cite{afdm2025jointcesd} rather than at the channel-support-selection step, leaving the OMP support-refinement slot inside an SP-AFDM joint receiver untouched.

- **sections/Section4.tex:59** — Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\ Huang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & GI-free pilot & Sparse DD & Joint CE+SD / DNN-aided & no & different axis (no SP, no UWA focus) \\ \textbf{This work} & AFDM & \textbf{SP} & \textbf{Sparse DD + Dirichlet} & \textbf{OMP-once + LS/MP-BP + learned top-$\Kadd$ ranker} & \textbf{yes (paired-frame McNemar, 3-seed pooled)} & --- \\ \bottomrule \end{tabular} } \end{table} \subsection{Limitations} \label{ssec:weaknesses} The c


## `balatsoukasstimming2019deepunfolding` (1 use)

- **sections/Section1.tex:158** — At the architectural level, the proposed learned head sits within the deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}.


## `bemani2023afdm` (4 uses)

- **sections/Section1.tex:25** — Affine Frequency Division Multiplexing (AFDM)~\cite{bemani2023afdm} was designed for precisely such doubly dispersive channels.

- **sections/Section1.tex:88** — AFDM was introduced by Bemani \emph{et al.}~\cite{bemani2023afdm} for next-generation wireless links over doubly dispersive channels, and was shown to recover the diversity advantages of OTFS via a one-dimensional chirp transform.

- **sections/Section2.tex:17** — e doubly dispersive UWA channel detailed in \S\ref{ssec:channel}, yields a chirp-domain received vector $\mby \in \C^{\Nsub}$ governed by \begin{equation} \mby \;=\; \Heff\, \mbx + \mbn, \qquad \mbn \sim \mathcal{CN}(\mathbf{0}, \sigma_n^2 \mathbf{I}_{\Nsub}), \label{eq:afdm_model} \end{equation} where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel. Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, delivering on a one-dimensional transform the same time--frequency diversity that OTFS~\cite{hadani2017otfs,wei2021otfspromising} achieves through its two-dimensional delay--Doppler grid.

- **sections/Section4.tex:52** — n records whether the present work covers a narrower, different, or complementary regime relative to each cited work; no numerical superiority is claimed against any external receiver.} \label{tab:priorart} \footnotesize \resizebox{\linewidth}{!}{\begin{tabular}{lllllll} \toprule Work & Waveform & Pilot & Channel & Iterative / learned & Stat.\ disc. & vs this work \\ \midrule Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-ai


## `benzine2023sparseafdm` (4 uses)

- **sections/Section1.tex:35** — ured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce. The resulting sparsity is what makes sparse-recovery channel estimation with orthogonal matching pursuit (OMP)~\cite{tropp2007signal} tractable~\cite{benzine2023sparseafdm,rou2024otfstoafdm}, and is the starting point of every receiver considered in this report.

- **sections/Section1.tex:93** — AFDM was introduced by Bemani \emph{et al.}~\cite{bemani2023afdm} for next-generation wireless links over doubly dispersive channels, and was shown to recover the diversity advantages of OTFS via a one-dimensional chirp transform. Subsequent work established the sparse-recovery side of AFDM channel estimation under embedded pilots: Benzine \emph{et al.}~\cite{benzine2023sparseafdm} develop a sparse-recovery AFDM receiver under EP guard intervals, and Yin \emph{et al.}~\cite{yin2024drceafdm} derive a diagonal-reconstruction estimator that explicitly addresses inter-Doppler interference in MIMO-AFDM.

- **sections/Section4.tex:40** — The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature.

- **sections/Section4.tex:53** — superiority is claimed against any external receiver.} \label{tab:priorart} \footnotesize \resizebox{\linewidth}{!}{\begin{tabular}{lllllll} \toprule Work & Waveform & Pilot & Channel & Iterative / learned & Stat.\ disc. & vs this work \\ \midrule Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024dr


## `berger2010uwasparse` (2 uses)

- **sections/Section1.tex:19** — cite{stojanovic2009uwa,preisig2007uwa}. The propagation speed of $c \approx 1500$~m/s, combined with platform motion of even a few~m/s, yields a relative Doppler of order $v / c \sim 10^{-3}$~--- three to four orders of magnitude larger than in a typical RF link --- and produces both strong inter-carrier interference and fractional Doppler offsets relative to the underlying multicarrier grid~\cite{berger2010uwasparse,huang2010uwamimoofdm}.

- **sections/Section2.tex:274** — Four receivers are compared head-to-head in Chapter~\ref{sec:results}. The \Serial{} arm is the closest single-pass realisation of the classical sparse-recovery literature~\cite{tropp2007signal,berger2010uwasparse} and makes the SP estimation-limited floor explicit.


## `clopper1934ci` (1 use)

- **sections/Section2.tex:267** — Reported BERs are observed frequencies $\hat{p} = \text{bit errors}/\text{bits}$. For the headline numbers at $\fs = 4B$, two-sided Clopper--Pearson~\cite{clopper1934ci} 95\% confidence intervals are quoted from the exact binomial distribution.


## `elfwing2018silu` (1 use)

- **sections/Section2.tex:221** — \paragraph{Architecture.} The head consists of a shared pair encoder followed by a per-candidate scorer. The pair encoder, denoted $f_{\text{pair}}: \R^{6} \to \R^{16} \to \R^{16}$ with SiLU activation~\cite{elfwing2018silu} after each linear layer, is applied element-wise to every pair feature $\mathbf{v}_{i,s}$, contributing $(6 \cdot 16 + 16) + (16 \cdot 16 + 16) = 384$ parameters.


## `hadani2017otfs` (2 uses)

- **sections/Section1.tex:32** — crete affine Fourier transform (DAFT), and choosing the two chirp coefficients $(c_1, c_2)$ to align with the channel's delay--Doppler geometry, AFDM folds every physical delay--Doppler pair into a single sparse structured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce.

- **sections/Section2.tex:17** — equation} where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel. Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, delivering on a one-dimensional transform the same time--frequency diversity that OTFS~\cite{hadani2017otfs,wei2021otfspromising} achieves through its two-dimensional delay--Doppler grid.


## `he2020modeldrivenmimo` (1 use)

- **sections/Section1.tex:160** — At the architectural level, the proposed learned head sits within the deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}. The bulk of this literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn} --- and combines learned blocks with classical iterative receivers in a way that preserves the model-based skeleton.


## `he2020oampnet` (1 use)

- **sections/Section1.tex:160** — At the architectural level, the proposed learned head sits within the deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}. The bulk of this literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn} --- and combines learned blocks with classical iterative receivers in a way that preserves the model-based skeleton.


## `huang2010uwamimoofdm` (1 use)

- **sections/Section1.tex:19** — cite{stojanovic2009uwa,preisig2007uwa}. The propagation speed of $c \approx 1500$~m/s, combined with platform motion of even a few~m/s, yields a relative Doppler of order $v / c \sim 10^{-3}$~--- three to four orders of magnitude larger than in a typical RF link --- and produces both strong inter-carrier interference and fractional Doppler offsets relative to the underlying multicarrier grid~\cite{berger2010uwasparse,huang2010uwamimoofdm}.


## `kaleh2005zadoffchu` (1 use)

- **sections/Section2.tex:51** — preserve spectral efficiency, every chirp-domain sub-carrier simultaneously carries data and pilot energy under a fixed superimposed-pilot (SP) frame \begin{equation} \mbx \;=\; \sqrt{\rhop}\; \xp \;+\; \sqrt{1 - \rhop}\; \xd, \qquad \rhop \in (0, 1), \label{eq:sp_frame} \end{equation} where $\xp$ is a deterministic Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector.


## `khani2020mmnet` (1 use)

- **sections/Section1.tex:162** — {et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}. The bulk of this literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn} --- and combines learned blocks with classical iterative receivers in a way that preserves the model-based skeleton.


## `kschischang2001factorgraph` (1 use)

- **sections/Section2.tex:145** — \paragraph{MP-BP messages on the sparse chirp-domain factor graph.} The data-detection block of Algorithm~\ref{alg:joint} follows the iterative-receiver framework of Wymeersch~\cite{wymeersch2007iterativereceiver} and the factor-graph paradigm surveyed by Kschischang~\emph{et~al.}~\cite{kschischang2001factorgraph}, and is implemented as Gaussian message passing on a bipartite factor graph derived from the pilot-subtracted observation.


## `loshchilov2019adamw` (1 use)

- **sections/Section2.tex:235** — nd a pairwise ranking hinge, \begin{equation} \mathcal{L}(\theta) \;=\; \mathcal{L}_{\text{BCE}}(\theta) \;+\; \lambda_{\text{rank}} \cdot \max\bigl(0,\; 1 - \min_{y_i=1} s_i(\theta) + \max_{y_j=0} s_j(\theta)\bigr), \qquad \lambda_{\text{rank}} = 0.5, \label{eq:loss} \end{equation} where $s_i(\theta)$ is the scorer logit for candidate $i$ and $\theta$ are the head parameters. Training uses AdamW~\cite{loshchilov2019adamw} with learning rate $10^{-3}$, weight decay $10^{-4}$, batch size $512$ cached frames, for 8 epochs with early stopping on the validation BCE (patience = 2).


## `ma2024oversampledafdm` (4 uses)

- **sections/Section1.tex:131** — A second cluster investigates physical-layer refinements to the AFDM receiver pipeline. Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} show that observing the chirp-domain signal at twice the Nyquist rate yields tangible channel-estimation improvement independent of any learned component; this directly motivates the $\fs = 4B$ operating point adopted in the present report, although their result is established in a non-SP, non-learning configuration and does not address either pilot-data interference or the residual fractio

- **sections/Section4.tex:35** — 4B$ operating point the serial-receiver NMSE saturates at $-11.3$~dB at $\snr = 15$~dB, which is low enough that the iterative joint recipe has sufficient SNR margin to descend two to three orders of magnitude in BER below the serial floor (Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}). The oversampling choice is consistent with the oversampled AFDM joint CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}, where oversampling is shown to help channel estimation independently of any learning component.

- **sections/Section4.tex:40** — is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows Yin and Tang~\cite{yin2022fractionaldopplerafdm} and the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, both of which target the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}.

- **sections/Section4.tex:57** — er.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\ Huang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & GI-free pilot & Sparse DD & Joint CE+SD / DNN-aided & no & different axis (no SP, no UWA focus) \\ \


## `mcnemar1947paired` (1 use)

- **sections/Section2.tex:267** — Reported BERs are observed frequencies $\hat{p} = \text{bit errors}/\text{bits}$. For the headline numbers at $\fs = 4B$, two-sided Clopper--Pearson~\cite{clopper1934ci} 95\% confidence intervals are quoted from the exact binomial distribution. Significance between the classical joint and the learned receiver is tested with the continuity-corrected paired McNemar $\chi^2$~\cite{mcnemar1947paired} on bit-level discordant counts $(n_{10}, n_{01})$; the reported $p$-values are the two-sided asymptotic values, with the within-frame independence assumption, the one-sided exact-binomial complement, and the degenerate-discordants edge case discussed in Appendix~\ref{app:mcnemar}.


## `monga2021unrolling` (2 uses)

- **sections/Section1.tex:157** — At the architectural level, the proposed learned head sits within the deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}.

- **sections/Section4.tex:40** — : per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver.


## `orozco2011superimposed` (2 uses)

- **sections/Section1.tex:43** — Pilot overhead nonetheless remains a first-order constraint on spectral efficiency in UWA contexts where the bandwidth budget is only a few kilohertz. To preserve the data-carrying capacity that an AFDM frame would otherwise lose to dedicated pilots, this work adopts a superimposed-pilot (SP) transmission~\cite{orozco2011superimposed,tugnait2006superimposed} in which every chirp sub-carrier simultaneously carries data and pilot energy under a fixed power split $\rhop$.

- **sections/Section2.tex:51** — \qquad \rhop \in (0, 1), \label{eq:sp_frame} \end{equation} where $\xp$ is a deterministic Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector. The canonical pilot power fraction is $\rhop = 0.5$; higher $\rhop$ strengthens the pilot observation at the cost of data energy, and lower $\rhop$ does the converse~\cite{orozco2011superimposed,tugnait2006superimposed}.


## `preisig2007uwa` (1 use)

- **sections/Section1.tex:14** — Their physical layer is shaped by two channel pathologies that, taken together, are harder to handle than almost any terrestrial radio-frequency link. The multipath between the sea surface, the water column, and the sea bed produces delay spreads of several to tens of milliseconds, which at the 4--12~kHz bandwidth budgets typical of UWA modems translates to hundreds of resolvable delay bins~\cite{stojanovic2009uwa,preisig2007uwa}.


## `qing2024spafdm` (5 uses)

- **sections/Section1.tex:107** — The most directly relevant line of work targets AFDM under non-orthogonal pilot regimes that share the joint estimation--detection challenge of SP. Zheng \emph{et al.}~\cite{qing2024spafdm} develop an SP-AFDM channel estimator that interleaves estimation and detection; their work establishes that an iterative loop is unavoidable once the pilot is no longer pilot-only, but it re-executes the sparse-recovery step on every outer iteration and contains no learning component, leaving open the question of whether OMP must be re-run each iteration or whether the support recovered by t

- **sections/Section4.tex:40** — The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data.

- **sections/Section4.tex:54** — h}{!}{\begin{tabular}{lllllll} \toprule Work & Waveform & Pilot & Channel & Iterative / learned & Stat.\ disc. & vs this work \\ \midrule Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary

- **sections/Section4.tex:77** — No head-to-head numerical reproduction of a published AFDM-SP or AFDM-JCEDD baseline is performed on the present channel realisations; all comparisons are against internally constructed baselines, and the structural mapping in Table~\ref{tab:priorart} remains qualitative. A direct re-implementation of the SP-AFDM estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} on the present seed blocks is the natural follow-up to convert this structural mapping into a quantitative comparison.

- **sections/Section5.tex:23** — The most immediate is a multi-seed retraining study, with three to five independent training seeds per SNR cell, which would convert the present single-checkpoint observation into a learning-variance statement and place error bars on the pooled $\approx 2$~dB headline. A direct re-implementation of the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} on the present $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks would convert the qualitative structural comparison of Table~\ref{tab:priorart} into a quantitative prior-art comparison and resolve whether the OMP-once design loses, matches, or surpasses an SP-AFDM receiver that re-runs the sparse step.


## `raviteja2018otfs` (1 use)

- **sections/Section1.tex:32** — crete affine Fourier transform (DAFT), and choosing the two chirp coefficients $(c_1, c_2)$ to align with the channel's delay--Doppler geometry, AFDM folds every physical delay--Doppler pair into a single sparse structured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce.


## `rou2024otfstoafdm` (2 uses)

- **sections/Section1.tex:35** — ured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce. The resulting sparsity is what makes sparse-recovery channel estimation with orthogonal matching pursuit (OMP)~\cite{tropp2007signal} tractable~\cite{benzine2023sparseafdm,rou2024otfstoafdm}, and is the starting point of every receiver considered in this report.

- **sections/Section1.tex:97** — ed the sparse-recovery side of AFDM channel estimation under embedded pilots: Benzine \emph{et al.}~\cite{benzine2023sparseafdm} develop a sparse-recovery AFDM receiver under EP guard intervals, and Yin \emph{et al.}~\cite{yin2024drceafdm} derive a diagonal-reconstruction estimator that explicitly addresses inter-Doppler interference in MIMO-AFDM. The comparative survey of Rou \emph{et al.}~\cite{rou2024otfstoafdm} situates AFDM alongside OTFS within an integrated sensing-and-communication context.


## `shlezinger2021deepsic` (1 use)

- **sections/Section1.tex:161** — d sits within the deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}. The bulk of this literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn} --- and combines learned blocks with classical iterative receivers in a way that preserves the model-based skeleton.


## `stojanovic2009uwa` (1 use)

- **sections/Section1.tex:14** — Their physical layer is shaped by two channel pathologies that, taken together, are harder to handle than almost any terrestrial radio-frequency link. The multipath between the sea surface, the water column, and the sea bed produces delay spreads of several to tens of milliseconds, which at the 4--12~kHz bandwidth budgets typical of UWA modems translates to hundreds of resolvable delay bins~\cite{stojanovic2009uwa,preisig2007uwa}.


## `tropp2007signal` (2 uses)

- **sections/Section1.tex:35** — pair into a single sparse structured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce. The resulting sparsity is what makes sparse-recovery channel estimation with orthogonal matching pursuit (OMP)~\cite{tropp2007signal} tractable~\cite{benzine2023sparseafdm,rou2024otfstoafdm}, and is the starting point of every receiver considered in this report.

- **sections/Section2.tex:274** — Four receivers are compared head-to-head in Chapter~\ref{sec:results}. The \Serial{} arm is the closest single-pass realisation of the classical sparse-recovery literature~\cite{tropp2007signal,berger2010uwasparse} and makes the SP estimation-limited floor explicit.


## `tugnait2006superimposed` (2 uses)

- **sections/Section1.tex:43** — Pilot overhead nonetheless remains a first-order constraint on spectral efficiency in UWA contexts where the bandwidth budget is only a few kilohertz. To preserve the data-carrying capacity that an AFDM frame would otherwise lose to dedicated pilots, this work adopts a superimposed-pilot (SP) transmission~\cite{orozco2011superimposed,tugnait2006superimposed} in which every chirp sub-carrier simultaneously carries data and pilot energy under a fixed power split $\rhop$.

- **sections/Section2.tex:51** — \qquad \rhop \in (0, 1), \label{eq:sp_frame} \end{equation} where $\xp$ is a deterministic Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector. The canonical pilot power fraction is $\rhop = 0.5$; higher $\rhop$ strengthens the pilot observation at the cost of data energy, and lower $\rhop$ does the converse~\cite{orozco2011superimposed,tugnait2006superimposed}.


## `wei2021otfspromising` (2 uses)

- **sections/Section1.tex:32** — crete affine Fourier transform (DAFT), and choosing the two chirp coefficients $(c_1, c_2)$ to align with the channel's delay--Doppler geometry, AFDM folds every physical delay--Doppler pair into a single sparse structured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce.

- **sections/Section2.tex:17** — equation} where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel. Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, delivering on a one-dimensional transform the same time--frequency diversity that OTFS~\cite{hadani2017otfs,wei2021otfspromising} achieves through its two-dimensional delay--Doppler grid.


## `wymeersch2007iterativereceiver` (3 uses)

- **sections/Section1.tex:57** — The natural response to a structured estimation residual is to iterate between channel estimation and symbol detection~\cite{wymeersch2007iterativereceiver}: each detection pass produces tentative data estimates that can be subtracted from the pilot observation, sharpening the next channel estimate.

- **sections/Section2.tex:145** — \paragraph{MP-BP messages on the sparse chirp-domain factor graph.} The data-detection block of Algorithm~\ref{alg:joint} follows the iterative-receiver framework of Wymeersch~\cite{wymeersch2007iterativereceiver} and the factor-graph paradigm surveyed by Kschischang~\emph{et~al.}~\cite{kschischang2001factorgraph}, and is implemented as Gaussian message passing on a bipartite factor graph derived from the pilot-subtracted observation.

- **sections/Section2.tex:165** — \frac{\mu_{j \to i}^{(T_\text{mp})}}{v_{j \to i}^{(T_\text{mp})}}, \label{eq:mpbp_post} \end{equation} followed by a Gray-coded QPSK projection $\hat{x}_{d,i} \mapsto \mathrm{QPSK\text{-}demap}(\hat{x}_{d,i})$ that returns the hard-decision data symbol. The Gaussian approximation maintained throughout the inner loop is the standard soft-Gaussian belief-propagation form for finite-alphabet symbols~\cite{wymeersch2007iterativereceiver}, with the QPSK constraint enforced only at the final projection.


## `xu2024detecttolearn` (1 use)

- **sections/Section1.tex:163** — latsoukasstimming2019deepunfolding}. The bulk of this literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn} --- and combines learned blocks with classical iterative receivers in a way that preserves the model-based skeleton.


## `yin2022fractionaldopplerafdm` (4 uses)

- **sections/Section1.tex:147** — ork, however, is non-SP and contains no learning component, and therefore does not engage with the SP-induced estimation floor or with the Dirichlet-leakage support residual that motivates the present design. The fractional-Doppler problem itself has been addressed directly by Yin \emph{et al.}~\cite{yin2024drceafdm} via a diagonal-reconstruction estimator for MIMO-AFDM, and by Yin and Tang~\cite{yin2022fractionaldopplerafdm} via a pilot-aided estimator, both of which target the Dirichlet leakage that single-pass OMP fails to capture; neither work, however, operates under an SP frame or embeds the leakage repair inside an iterative joint receiver.

- **sections/Section2.tex:29** — align} l_p &= \mathrm{round}(\tau_p \, \fs), \qquad k_p^{\text{real}} = \frac{v_p \, \fc \, \Nsub}{c \, \fs}, \label{eq:delaydoppler_mapping} \end{align} with $c \approx 1500$~m/s the speed of sound. The delay index $l_p$ is integer by construction, but $k_p^{\text{real}}$ is typically fractional: the residual fractional Doppler is absorbed via a discrete-Dirichlet-kernel (aliased-sinc) expansion~\cite{yin2022fractionaldopplerafdm} of half-width $\kleak = 2$, so that path $p$ is decomposed into $2\kleak + 1 = 5$ virtual integer-bin taps with magnitude \begin{equation} |\tilde{h}_{p,j}| \;=\; |h_p| \cdot \left| \frac{\sin\bigl(\pi (k_p^{\text{real}} - k_p - j)\bigr)}{\Nsub \, \sin\bigl(\pi (k_p^{\text{real}} - k_p - j)/\Nsub\bigr)} \right|, \qquad j \in \{-\kleak, \dots, \kleak\}, \label{eq:dirichlet} \end{equation} with $k_

- **sections/Section4.tex:40** — rative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows Yin and Tang~\cite{yin2022fractionaldopplerafdm} and the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, both of which target the leakage that OMP fails to capture in a single pass.

- **sections/Section4.tex:56** — e \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\


## `yin2024drceafdm` (4 uses)

- **sections/Section1.tex:94** — eration wireless links over doubly dispersive channels, and was shown to recover the diversity advantages of OTFS via a one-dimensional chirp transform. Subsequent work established the sparse-recovery side of AFDM channel estimation under embedded pilots: Benzine \emph{et al.}~\cite{benzine2023sparseafdm} develop a sparse-recovery AFDM receiver under EP guard intervals, and Yin \emph{et al.}~\cite{yin2024drceafdm} derive a diagonal-reconstruction estimator that explicitly addresses inter-Doppler interference in MIMO-AFDM.

- **sections/Section1.tex:145** — e AFDM sparse-recovery primitive transfers to a more physically faithful UWA channel model; their work, however, is non-SP and contains no learning component, and therefore does not engage with the SP-induced estimation floor or with the Dirichlet-leakage support residual that motivates the present design. The fractional-Doppler problem itself has been addressed directly by Yin \emph{et al.}~\cite{yin2024drceafdm} via a diagonal-reconstruction estimator for MIMO-AFDM, and by Yin and Tang~\cite{yin2022fractionaldopplerafdm} via a pilot-aided estimator, both of which target the Dirichlet leakage that single-pass OMP fails to capture; neither work, however, operates under an SP frame or embeds the leakage repair inside an iterative joint receiver.

- **sections/Section4.tex:40** — mph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows Yin and Tang~\cite{yin2022fractionaldopplerafdm} and the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, both of which target the leakage that OMP fails to capture in a single pass.

- **sections/Section4.tex:56** — e \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\


## `zhao2024gifreeafdm` (3 uses)

- **sections/Section1.tex:113** — stimation and detection; their work establishes that an iterative loop is unavoidable once the pilot is no longer pilot-only, but it re-executes the sparse-recovery step on every outer iteration and contains no learning component, leaving open the question of whether OMP must be re-run each iteration or whether the support recovered by the first pass is already sufficient. Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} reach a structurally similar conclusion via a guard-interval-free pilot-aided design with iterative interference cancellation; their formulation, however, departs from SP rather than addressing the pilot-data interference inside it, so the SP-specific estimation-limited floor at mid-to-high SNR is not part of the problem they solve.

- **sections/Section4.tex:40** — gn ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data.

- **sections/Section4.tex:55** — \midrule Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & c


## `zhou2024msmlafdm` (6 uses)

- **sections/Section1.tex:138** — t twice the Nyquist rate yields tangible channel-estimation improvement independent of any learned component; this directly motivates the $\fs = 4B$ operating point adopted in the present report, although their result is established in a non-SP, non-learning configuration and does not address either pilot-data interference or the residual fractional-Doppler support errors. Cao \emph{et al.}~\cite{zhou2024msmlafdm} extend AFDM-OMP to multi-scale multi-lag (MSML) UWA channels in which each physical path carries an independent time-scale factor, establishing that the AFDM sparse-recovery primitive transfers to a more physically faithful UWA channel model; their work, however, is non-SP and contains no learning component, and therefore does not engage with the SP-induced estimation floor or with the Diric

- **sections/Section4.tex:40** — iagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, both of which target the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}.

- **sections/Section4.tex:40** — of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}.

- **sections/Section4.tex:58** — & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\ Huang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & GI-free pilot & Sparse DD & Joint CE+SD / DNN-aided & no & different axis (no SP, no UWA focus) \\ \textbf{This work} & AFDM & \textbf{SP} & \textbf{Sparse DD + Dirichlet} & \textbf{OMP-once + LS/MP-BP + learned top-$\Kadd$ ranker} & \textbf{yes (paired-frame

- **sections/Section4.tex:75** — r by drawing per-path velocities $v_p$, producing per-path scaling factors $a_p = v_p / c$ that yield both a per-path delay rescaling $\tau_p \mapsto \tau_p / (1+a_p)$ and a per-path constant Doppler frequency shift $f_{D,p} = a_p \fc$. What is not modelled is full broadband per-path waveform resampling within a symbol or per-frame Doppler jitter, both of which are present in real UWA propagation~\cite{zhou2024msmlafdm}.

- **sections/Section5.tex:25** — Extending the simulator from the first-order per-path MSML approximation (per-path constant Doppler shift plus delay rescaling) to full broadband per-path waveform resampling and per-frame Doppler jitter, following Cao \emph{et al.}~\cite{zhou2024msmlafdm}, would bring the physical-layer model closer to real UWA propagation and test whether the mechanism-level conclusions identified here transfer to a more realistic propagation regime.


## Uncited bib entries (3)

- `donoho2009amp`
- `candes2006cs`
- `li2002channelestimationofdm`


