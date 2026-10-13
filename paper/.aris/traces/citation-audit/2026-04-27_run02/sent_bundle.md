# oracle_prompt.md (sent)

# Citation audit — AFDM final report (UoG/UESTC MS, run02)

**Role**: You are an external bibliographic auditor. A senior IEEE-trained reviewer is about to read this paper. Your job is to find every error in the bibliography and every wrong-context citation BEFORE that reviewer does. You have web access. Use it. Do not pattern-match from training memory; do real DBLP / arXiv / IEEE Xplore / Wiley / IET / ACM / DOI / publisher lookups for every entry.

**Domain**: Underwater acoustic (UWA) channel estimation; AFDM (Affine Frequency Division Multiplexing); sparse recovery (OMP, AMP, SBL); deep unfolding receivers; iterative joint channel-estimation + symbol-detection; superimposed-pilot transmission; OTFS / OTSM detector lineage.

**Run metadata**: This is run02 of the audit (same date as run01 2026-04-27). The bibliography was substantially expanded between runs: a critical-literature-survey rewrite added 14 new entries (cui2007superimposed, liang2011iterativesp, mishra2022otfssp, neelam2023otsmsp, cao2024spomp, junejo2018labomp, yuan2022uampotfs, pu2024epotfs, zhuang2024amgnnotfs, gregor2010lista, he2019modeldrivensurvey, mohammadtaheri2025deepgreedyunfolding, yin2025afdmoverview, zhou2025afdmicsc). Section 1 was completely rewritten, so even previously-checked entries (bemani2023afdm, benzine2023sparseafdm, etc.) now have new citation contexts that must be re-judged from scratch. **Do not assume run01 verdicts carry over** — fresh review of all 49 entries.

## Inputs attached

1. `references.bib` — bib file with 49 entries (46 cited, 3 uncited: `candes2006cs`, `donoho2009amp`, `li2002channelestimationofdm`).
2. `contexts.txt` — for each cited key, every (file, line) where it appears, plus the surrounding sentence so you can judge whether the cite supports the claim. Total: 89 invocations across 46 unique cited keys.

## What I need from you (three layers per entry)

For **every** bib entry — including the 3 uncited ones — answer:

### 1. EXISTENCE
Does this paper actually exist at the claimed DOI / arXiv ID / venue? Verify with a real lookup. Output one of:
- `EXISTS` — found at the claimed location, give the verifying URL
- `WRONG_LOCATION` — paper exists but the claimed DOI/arXiv ID resolves to a different paper; give what the claimed ID actually resolves to AND where the intended paper lives
- `HALLUCINATED` — cannot find any paper matching this metadata anywhere
- `UNCERTAIN` — could not verify online (give what you tried)

### 2. METADATA (per field)
For each of `author`, `title`, `year`, `journal/booktitle`, `volume/number/pages`, `doi`:
- `correct` — matches canonical record
- `wrong: should be ...` — give the correct value
- `typo: ...` — minor diacritic/spelling issue
- `missing` — field absent and should be present (e.g., DOI for an IEEE journal article)

Be especially careful with **author lists** for the recent AFDM cluster (qing2024spafdm, zhao2024gifreeafdm, ma2024oversampledafdm, zhou2024msmlafdm, afdm2025jointcesd, yin2022fractionaldopplerafdm, yin2025afdmoverview, zhou2025afdmicsc, cao2024spomp). The cite-key prefix does NOT necessarily match the actual first author — see "Known traps" below.

### 3. CONTEXT (per use)
For each `(file, line)` invocation listed in `contexts.txt`, judge whether the cited paper actually establishes the claim that the surrounding sentence is making. Output one of:
- `SUPPORTS` — the cited paper directly establishes this claim
- `WEAK` — the cited paper is loosely related but not the primary source for this claim
- `WRONG` — the cited paper does not establish this claim or argues something different; give a one-sentence reason

This is the most important axis. **A real paper used to support a wrong claim is more dangerous than a typo in author name.**

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
# Citation Audit Verdict — AFDM final report (run02)

## Top-level summary
- Total entries: 49 (46 cited, 3 uncited)
- Counts: KEEP=?, FIX=?, REPLACE=?, REMOVE=?
- Top-level verdict: PASS / WARN / FAIL
- One-line summary

## Critical findings (REMOVE / REPLACE)
[ranked by danger to credibility]

## Per-entry verdicts
[one section per bib key — give every one of the 49 keys, no skipping]

### `<key>`
- VERDICT: KEEP/FIX/REPLACE/REMOVE
- EXISTENCE: ... (with verifying URL)
- METADATA: ...
- CONTEXT (per use):
  - sections/Section1.tex:14 — SUPPORTS/WEAK/WRONG: ...
  - ...
- ACTION: ...

## Author-cluster confirmation block — recent AFDM
For each of {qing2024spafdm, zhao2024gifreeafdm, ma2024oversampledafdm, zhou2024msmlafdm, afdm2025jointcesd, yin2022fractionaldopplerafdm, yin2025afdmoverview, zhou2025afdmicsc, cao2024spomp}, state explicitly:
- the verified first author (from a fresh DBLP / IEEE Xplore / arXiv lookup, NOT memory)
- the verifying URL
This serves as your auditable signature that the high-risk cluster was not pattern-matched from training.
```

## Known traps (this audit was run once before; these are landmines from THIS run's recent edits)

The previous audit (run01, same date) found a set of issues that have been resolved (orozco2011superimposed, preisig2007uwa, kaleh2005zadoffchu, khani2020mmnet, balatsoukasstimming2019deepunfolding, elfwing2018silu, qing2024spafdm, zhao2024gifreeafdm, ma2024oversampledafdm, zhou2024msmlafdm, afdm2025jointcesd, yin2022fractionaldopplerafdm). **Do not trust the current bib state for those — re-verify from scratch.** In addition, this run was preceded by a critical-literature-survey rewrite that added 14 new entries; below are the specific claims this session's lit-survey work made about each new entry. **The reviewer MUST independently verify each one with a fresh web lookup; do not take any of these claims as ground truth.**

### New-entry trap list (14 entries added this session)

1. **`cui2007superimposed`** — bib year is recorded as **2011**, not 2007 (the cite-key suffix "2007" is misleading; user explicitly chose to keep the misleading suffix for cite-stability). Claim: Tao Cui & Chintha Tellambura, "OFDM channel estimation and data detection with superimposed pilots", *European Transactions on Telecommunications* 22(3):125–136, 2011, DOI 10.1002/ett.1461. **Verify on Wiley Online Library that this paper exists at this DOI with this exact author list and year.**

2. **`liang2011iterativesp`** — bib year is recorded as **2006**, not 2011 (cite-key suffix "2011" is misleading; kept for stability). Claim: Ting-Jung Liang & Wolfgang Rave & Gerhard P. Fettweis, "Iterative joint channel estimation and decoding using superimposed pilots in OFDM-WLAN", Proc. IEEE ICC 2006, pp. 3140–3145, DOI 10.1109/ICC.2006.255288. **Verify on IEEE Xplore that this paper exists at this DOI in the ICC 2006 proceedings, and that the first author's given name is "Ting-Jung" (NOT "Yangyang", which an earlier version of the bib had wrong).**

3. **`mishra2022otfssp`** — Claim: Himanshu B. Mishra & Prem Singh & Abhishek K. Prasad & Rohit Budhiraja, "OTFS channel estimation and data detection designs with superimposed pilots", *IEEE Transactions on Wireless Communications* 21(4):2258–2274, 2022, DOI 10.1109/TWC.2021.3110659. **Verify on IEEE Xplore that the first author's given name is "Himanshu B." (NOT "Harshit Kumar", which an earlier draft had).**

4. **`neelam2023otsmsp`** — Claim: Sapta Girish Neelam & P. R. Sahu (only **two** authors), "Iterative channel estimation and data detection of OTSM with superimposed pilot scheme and PAPR analysis", *IEEE Communications Letters* 27(8):2147–2151, 2023, DOI 10.1109/LCOMM.2023.3281575. **Verify on IEEE Xplore that the author list is exactly these two names. The paper was previously misattributed to "Sinha et al." in an earlier session draft — confirm that mistake has been undone, and that the cite-key matches the actual first author surname.** Also check Section1.tex:140 says "Neelam and Sahu" (no "et al." — only 2 authors); flag if it says anything else.

5. **`cao2024spomp`** — Claim: Zhe Cao & Miaowen Wen & Yu Huang, "Sparse channel estimation and data detection for AFDM with superimposed pilot scheme", Proc. IEEE ICCT 2024, pp. 1540–1544, DOI 10.1109/ICCT62411.2024.10946599. **Verify on IEEE Xplore (or DBLP `dblp.org/rec/conf/icct/CaoWH24`) that this is a real ICCT 2024 entry with this author list.** Note the SP-OMP-AFDM topic is the closest direct competitor to this report, so context-correctness is paramount.

6. **`junejo2018labomp`** — Claim: Naveed Ur Rehman Junejo & Hamada Esmaiel & Mingzhang Zhou & Haixin Sun & Jie Qi & Junfeng Wang, "Sparse channel estimation of underwater TDS-OFDM system using look-ahead backtracking orthogonal matching pursuit", *IEEE Access* 6:74389–74399, 2018, DOI 10.1109/ACCESS.2018.2881766. **Verify on IEEE Xplore.**

7. **`yuan2022uampotfs`** — Claim: Zhengdao Yuan & Fei Liu & Weijie Yuan & Qinghua Guo & Zhongyong Wang & Jinhong Yuan, "Iterative detection for orthogonal time frequency space modulation with unitary approximate message passing", *IEEE Transactions on Wireless Communications* 21(2):714–725, 2022, DOI 10.1109/TWC.2021.3097173. **Verify on IEEE Xplore. Confirm the title's "with unitary approximate message passing" is exact (not "with UAMP" or some abbreviation).**

8. **`pu2024epotfs`** — Claim: Xumin Pu & Zhinan Sun & Wanli Wen & Qianbin Chen & Shi Jin, "A low-complexity expectation propagation detector for OTFS", *IET Signal Processing* 2024(1) article 3256977, 2024, DOI 10.1049/2024/3256977. **Verify on the Wiley/IET DOI page; IET Signal Processing now uses Wiley's article-ID volume convention so the volume is the year (2024), and the article number 3256977 is a Wiley/IET hybrid open-access record.**

9. **`zhuang2024amgnnotfs`** — Claim: Wenhao Zhuang & Yuyi Mao & Hengtao He & Lei Xie & Shenghui Song & Yao Ge & Zhi Ding, "Approximate message passing-enhanced graph neural network for OTFS data detection", *IEEE Wireless Communications Letters* 13(7):1913–1917, 2024, DOI 10.1109/LWC.2024.3395700. **Verify on IEEE Xplore that the first author is Zhuang (NOT Zou, which an earlier draft of this session had wrong). Verify the cite-key prefix `zhuang` matches the actual first-author surname.**

10. **`gregor2010lista`** — Claim: Karol Gregor & Yann LeCun, "Learning fast approximations of sparse coding", Proc. 27th ICML 2010, pp. 399–406, Haifa, Israel. **Verify on the ICML 2010 proceedings (icml.cc) and DBLP `conf/icml/GregorL10`. This is the seminal LISTA paper; its citation context here at sections/Section1.tex says "rooted in the seminal Learned ISTA architecture of Gregor and LeCun" — confirm the paper is actually about LISTA.**

11. **`he2019modeldrivensurvey`** — Claim: Hengtao He & Shi Jin & Chao-Kai Wen & Feifei Gao & Geoffrey Ye Li & Zongben Xu (**six** authors), "Model-driven deep learning for physical layer communications", *IEEE Wireless Communications* 26(5):77–83, October 2019, DOI 10.1109/MWC.2019.1800447. **Verify on IEEE Xplore that the author list has all six names (a previous draft of this session was missing the 6th author Zongben Xu).**

12. **`mohammadtaheri2025deepgreedyunfolding`** — Claim: Sina Mohammad-Taheri & Matthew J. Colbrook & Simone Brugiapaglia, "Deep greedy unfolding: Sorting out argsorting in greedy sparse recovery algorithms", arXiv:2505.15661, 2025, DOI 10.48550/arXiv.2505.15661. **Verify on arxiv.org that the arXiv ID resolves to this exact title and author list.** This is a 2025 preprint; it may or may not be in DBLP yet.

13. **`yin2025afdmoverview`** — Claim: Haoran Yin & Yanqun Tang & Ali Bemani & Marios Kountouris & Yu Zhou & Xingyao Zhang & Yuqing Liu & Gaojie Chen & Kai Yang & Fan Liu & Christos Masouros & Shuangyang Li & Giuseppe Caire & Pei Xiao (**14** authors), "Affine Frequency Division Multiplexing: Extending OFDM for Scenario-Flexibility and Resilience", *IEEE Wireless Communications*, in press 2025, DOI 10.1109/MWC.2025.3600081 (also arXiv:2502.04735). **Verify on IEEE Xplore (document 11204797) that the first author is Haoran Yin (NOT Shuangyang Li — Shuangyang Li is author #12 of 14; an earlier draft of this session had the cite-key as `li2025afdmoverview` and used the wrong first-author surname). Confirm the cite-key prefix `yin` matches the verified first author.**

14. **`zhou2025afdmicsc`** — Claim: Yu Zhou & Chao Zou & Nanhao Zhou & Yanqun Tang & Xiaoying Zhang & Haoran Yin & Xiaoran Liu & Ruisi He & Pan Tang & Weijie Yuan & Yong Zeng, "Affine Frequency Division Multiplexing for Communication and Channel Sounding: Requirements, Challenges, and Key Technologies", arXiv:2509.16643, 2025, DOI 10.48550/arXiv.2509.16643. **Verify on arxiv.org that this exact paper exists. Earlier this session, an attempted citation `wang2025afdmicsc` was found to be hallucinated (no Wang-first-authored AFDM-ICSC overview exists in 2025); it was replaced with this Zhou-first paper. Confirm there is no hallucination remaining.**

### Cross-cluster invariants to spot-check

- **Section1.tex line range 88–169** is the rewritten lit survey. Every `\cite{}` in this range was added or relocated this session. Pay heightened attention to context correctness in this block — the prose was substantially restructured, and cite-to-claim alignment may have drifted.
- **Section4.tex `tab:priorart`** (the comparison table in §4) was NOT rewritten this session, but several of its row-labels reference newly-renamed keys (e.g. `Cao \emph{et al.}~\cite{zhou2024msmlafdm}` — first author Cao, not Zhou; this is correct but the cite-key prefix is misleading). Confirm row-label "Author et al." matches the bib's `author = {...}` first author for every row.
- **Section2.tex paragraph at line 267** previously cited Clopper--Pearson 1934 (`clopper1934ci`) and McNemar 1947 (`mcnemar1947paired`). Both were removed earlier this session. Confirm those keys do NOT appear anywhere in `references.bib` or in any `.tex` source file. If they appear, that's a regression — flag REMOVE.
- **Section1.tex line range 180–185** is the rewritten UWA-OFDM lineage paragraph. It currently says "Bayesian variants based on sparse Bayesian learning" without a citation (the user explicitly chose to make this claim uncited). Confirm there is NO `\cite{qiao2019sblofdm}` or `\cite{qiao2017bemuwa}` regression — both were dropped this session because the papers couldn't be verified.

## Other things to check critically

- **Wrong-context candidates** — any cite where the cited paper does not establish the surrounding claim. Pay particular attention to:
  - sparse-recovery references (`tropp2007signal`, `berger2010uwasparse`) used in places that need a different primitive
  - `rou2024otfstoafdm` (a survey of ISAC waveforms) used as a primary citation for embedded-pilot or waveform-design claims
  - `wymeersch2007iterativereceiver` and `kschischang2001factorgraph` used together: are both needed, or is one redundant?
  - `gregor2010lista` cited at sections/Section1.tex inside the deep-unfolding paragraph — does the LISTA paper actually establish "iterations of a sparse-recovery algorithm are unrolled into trainable layers"? (It should, but verify against the 2010 ICML paper directly.)
  - `mohammadtaheri2025deepgreedyunfolding` cited at sections/Section1.tex with a specific claim that "the non-differentiable argsort operator is approached via softsort relaxations" — does the 2025 arXiv paper actually use softsort? (Verify against the abstract/paper directly.)
  - `yuan2022uampotfs`, `pu2024epotfs`, `zhuang2024amgnnotfs` cited in the Sparse message-passing detection paragraph as "unitary-AMP variants", "expectation-propagation formulations", and "graph-neural-network refinements" respectively — confirm each cited paper's primary contribution actually matches that one-word taxonomy.
  - `cui2007superimposed` and `tugnait2006superimposed` jointly cited at sections/Section1.tex line 130 for "ML and MMSE iterative estimators for SP-OFDM and proved that the equispaced equipowered placement minimises the Cramér–Rao bound" — verify this CRB claim is in BOTH papers (or at least one); if not, flag WRONG-CONTEXT.
  - `liang2011iterativesp` cited at sections/Section1.tex line 134 with the specific claim "superimposed pilots can match preamble-based channel estimation in OFDM-WLAN at the cost of an iterative receiver" — confirm the Liang/Rave/Fettweis ICC 2006 paper actually makes this exact comparison (preamble vs SP).
  - `mishra2022otfssp` and `neelam2023otsmsp` jointly cited at sections/Section1.tex line 140 — confirm both papers actually demonstrate "an iterative loop alternating pilot-data interference cancellation and channel re-estimation is unavoidable once the EP assumption is abandoned".
  - `cao2024spomp` cited at sections/Section1.tex line 152 — does the ICCT 2024 paper actually combine SP frame with OMP front-end specifically (as opposed to other sparse-recovery methods)?
  - `Section4.tex tab:priorart` (the comparison table in §4) — every row claims a specific axis ("EP", "SP", "GI-free", "Sparse DD", "DNN-aided", etc.). For each cited paper in the table, does the actual paper cover that axis?

- **Section 4 author labels**: every "Author et al." in Section4.tex must match the bib `author = {...}` field's first author. Flag any mismatch.

- **DOI format / resolvability**: every IEEE / Elsevier / ACM / IET / Wiley DOI should resolve. Spot-check resolvability for the 14 new entries in particular.

- **arXiv versioning drift**: for entries claiming an arXiv ID (`mohammadtaheri2025deepgreedyunfolding` 2505.15661, `zhou2025afdmicsc` 2509.16643, possibly others), confirm the title/author list matches the *current* arXiv version, not a v1 that has since been replaced with a different paper.

- **Cite-key prefix vs first-author surname** — for every cited entry, flag any mismatch between the cite-key prefix and the bib `author` field's first surname (e.g., `qing2024spafdm` first author is actually Zheng; `zhao2024gifreeafdm` first author is actually Zhou; `ma2024oversampledafdm` first author is actually Ranasinghe; `zhou2024msmlafdm` first author is actually Cao). The user has explicitly accepted these mismatches as a known cost of cite-key stability — do NOT mark FIX/REPLACE on prefix-vs-surname mismatch alone, but DO list each one in your report so the user has a complete ledger.

## Reasoning effort

This is a **nightmare-difficulty / max-effort** audit. Take your time. Use web search aggressively. If you can find a published version (IEEE Xplore, ACM DL, ScienceDirect, IET, Wiley, ICML proceedings), prefer it over arXiv. If arXiv only, use the abstract page directly — do not trust third-party mirrors.

Be honest. If you cannot verify online, say `UNCERTAIN` — do not guess. The downstream consumer (the human user, then the IEEE reviewer) is much better served by an honest UNCERTAIN than by a falsely-confident KEEP.

When you finish, give the per-entry table for ALL 49 entries (including the 3 uncited ones) — no skipping the obvious ones. The user wants a complete ledger, not just the items that triggered FIX/REPLACE/REMOVE.

---

**Final reminder**: a real paper used to support a wrong claim is more dangerous than any metadata typo. Spend most of your effort on the `CONTEXT` axis for the 89 invocations.


---

# references.bib (sent)

```bibtex
%% ----- Foundational UWA + sparse channel estimation -----

@article{stojanovic2009uwa,
  title   = {Underwater Acoustic Communication Channels: Propagation Models and Statistical Characterization},
  author  = {Stojanovic, Milica and Preisig, James},
  journal = {IEEE Communications Magazine},
  volume  = {47},
  number  = {1},
  pages   = {84--89},
  year    = {2009},
  doi     = {10.1109/MCOM.2009.4752682}
}

@article{preisig2007uwa,
  title   = {Acoustic Propagation Considerations for Underwater Acoustic Communications Network Development},
  author  = {Preisig, James C.},
  journal = {ACM SIGMOBILE Mobile Computing and Communications Review},
  volume  = {11},
  number  = {4},
  pages   = {2--10},
  year    = {2007},
  doi     = {10.1145/1347364.1347370}
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
  note      = {arXiv:2203.05781 is the ICCC 2022 preprint; arXiv:2206.12822 indexes the separate DRCE work cited as yin2024drceafdm.}
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
  pages     = {1569--1574},
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
  title   = {Model-Driven Deep Learning for Physical Layer Communications},
  author  = {He, Hengtao and Jin, Shi and Wen, Chao-Kai and Gao, Feifei and Li, Geoffrey Ye and Xu, Zongben},
  journal = {IEEE Wireless Communications},
  volume  = {26},
  number  = {5},
  pages   = {77--83},
  year    = {2019},
  doi     = {10.1109/MWC.2019.1800447},
  note    = {Cite-key prefix `he2020oampnet' retained from earlier draft; record corrected to the verified 6-author IEEE Wireless Comms 2019 survey by the same author team. The earlier (unverifiable) JSTSP record claimed to refer to the related JCESD/OAMP-Net2 paper.}
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
  title   = {Channel Estimation Using Implicit Training},
  author  = {Orozco-Lugo, Aldo G. and Lara, M. Mauricio and McLernon, Desmond C.},
  journal = {IEEE Transactions on Signal Processing},
  volume  = {52},
  number  = {1},
  pages   = {240--254},
  year    = {2004},
  doi     = {10.1109/TSP.2003.819993},
  note    = {Cite-key prefix `orozco2011' retained from earlier draft; record corrected to the canonical 2004 implicit-training paper.}
}

@article{tugnait2006superimposed,
  title   = {On Superimposed Training for Channel Estimation: Performance Analysis, Training Power Allocation, and Frame Synchronization},
  author  = {Tugnait, Jitendra K. and Meng, Xiaohong},
  journal = {IEEE Transactions on Signal Processing},
  volume  = {54},
  number  = {2},
  pages   = {752--765},
  year    = {2006},
  doi     = {10.1109/TSP.2005.861749},
  note    = {Cite-key suffix `superimposed' retained; co-author corrected from Luo to Meng to match the verified TSP 2006 record.}
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

%% ----- AFDM overviews / surveys (added Apr 2026) -----

@article{yin2025afdmoverview,
  title   = {Affine Frequency Division Multiplexing: Extending {OFDM} for Scenario-Flexibility and Resilience},
  author  = {Yin, Haoran and Tang, Yanqun and Bemani, Ali and Kountouris, Marios and Zhou, Yu and Zhang, Xingyao and Liu, Yuqing and Chen, Gaojie and Yang, Kai and Liu, Fan and Masouros, Christos and Li, Shuangyang and Caire, Giuseppe and Xiao, Pei},
  journal = {IEEE Wireless Communications},
  year    = {2025},
  note    = {in press},
  doi     = {10.1109/MWC.2025.3600081}
}

@article{zhou2025afdmicsc,
  title   = {Affine Frequency Division Multiplexing for Communication and Channel Sounding: Requirements, Challenges, and Key Technologies},
  author  = {Zhou, Yu and Zou, Chao and Zhou, Nanhao and Tang, Yanqun and Zhang, Xiaoying and Yin, Haoran and Liu, Xiaoran and He, Ruisi and Tang, Pan and Yuan, Weijie and Zeng, Yong},
  journal = {arXiv preprint arXiv:2509.16643},
  year    = {2025},
  doi     = {10.48550/arXiv.2509.16643}
}

%% ----- Superimposed pilots (OFDM lineage and delay--Doppler extensions) -----

@article{cui2007superimposed,
  title   = {{OFDM} channel estimation and data detection with superimposed pilots},
  author  = {Cui, Tao and Tellambura, Chintha},
  journal = {European Transactions on Telecommunications},
  volume  = {22},
  number  = {3},
  pages   = {125--136},
  year    = {2011},
  doi     = {10.1002/ett.1461}
}

@inproceedings{liang2011iterativesp,
  title     = {Iterative joint channel estimation and decoding using superimposed pilots in {OFDM}-{WLAN}},
  author    = {Liang, Ting-Jung and Rave, Wolfgang and Fettweis, Gerhard P.},
  booktitle = {Proc. IEEE International Conference on Communications ({ICC})},
  pages     = {3140--3145},
  year      = {2006},
  doi       = {10.1109/ICC.2006.255288}
}

@article{mishra2022otfssp,
  title   = {{OTFS} channel estimation and data detection designs with superimposed pilots},
  author  = {Mishra, Himanshu B. and Singh, Prem and Prasad, Abhishek K. and Budhiraja, Rohit},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {21},
  number  = {4},
  pages   = {2258--2274},
  year    = {2022},
  doi     = {10.1109/TWC.2021.3110659}
}

@article{neelam2023otsmsp,
  title   = {Iterative channel estimation and data detection of {OTSM} with superimposed pilot scheme and {PAPR} analysis},
  author  = {Neelam, Sapta Girish and Sahu, P. R.},
  journal = {IEEE Communications Letters},
  volume  = {27},
  number  = {8},
  pages   = {2147--2151},
  year    = {2023},
  doi     = {10.1109/LCOMM.2023.3281575}
}

@inproceedings{cao2024spomp,
  title     = {Sparse channel estimation and data detection for {AFDM} with superimposed pilot scheme},
  author    = {Cao, Zhe and Wen, Miaowen and Huang, Yu},
  booktitle = {Proc. IEEE International Conference on Communication Technology ({ICCT})},
  pages     = {1540--1544},
  year      = {2024},
  doi       = {10.1109/ICCT62411.2024.10946599}
}

%% ----- UWA-OFDM sparse channel estimation refinements -----

@article{junejo2018labomp,
  title   = {Sparse channel estimation of underwater {TDS-OFDM} system using look-ahead backtracking orthogonal matching pursuit},
  author  = {Junejo, Naveed Ur Rehman and Esmaiel, Hamada and Zhou, Mingzhang and Sun, Haixin and Qi, Jie and Wang, Junfeng},
  journal = {IEEE Access},
  volume  = {6},
  pages   = {74389--74399},
  year    = {2018},
  doi     = {10.1109/ACCESS.2018.2881766}
}

%% ----- OTFS detector lineage (sparse message passing) -----

@article{yuan2022uampotfs,
  title   = {Iterative detection for orthogonal time frequency space modulation with unitary approximate message passing},
  author  = {Yuan, Zhengdao and Liu, Fei and Yuan, Weijie and Guo, Qinghua and Wang, Zhongyong and Yuan, Jinhong},
  journal = {IEEE Transactions on Wireless Communications},
  volume  = {21},
  number  = {2},
  pages   = {714--725},
  year    = {2022},
  doi     = {10.1109/TWC.2021.3097173}
}

@article{pu2024epotfs,
  title   = {A low-complexity expectation propagation detector for {OTFS}},
  author  = {Pu, Xumin and Sun, Zhinan and Wen, Wanli and Chen, Qianbin and Jin, Shi},
  journal = {IET Signal Processing},
  volume  = {2024},
  number  = {1},
  pages   = {3256977},
  year    = {2024},
  doi     = {10.1049/2024/3256977}
}

@article{zhuang2024amgnnotfs,
  title   = {Approximate message passing-enhanced graph neural network for {OTFS} data detection},
  author  = {Zhuang, Wenhao and Mao, Yuyi and He, Hengtao and Xie, Lei and Song, Shenghui and Ge, Yao and Ding, Zhi},
  journal = {IEEE Wireless Communications Letters},
  volume  = {13},
  number  = {7},
  pages   = {1913--1917},
  year    = {2024},
  doi     = {10.1109/LWC.2024.3395700}
}

%% ----- Deep unfolding (LISTA, model-driven survey, OMP-unrolling) -----

@inproceedings{gregor2010lista,
  title     = {Learning fast approximations of sparse coding},
  author    = {Gregor, Karol and LeCun, Yann},
  booktitle = {Proceedings of the 27th International Conference on Machine Learning ({ICML})},
  pages     = {399--406},
  year      = {2010},
  address   = {Haifa, Israel}
}

@article{he2019modeldrivensurvey,
  title   = {Model-driven deep learning for physical layer communications},
  author  = {He, Hengtao and Jin, Shi and Wen, Chao-Kai and Gao, Feifei and Li, Geoffrey Ye and Xu, Zongben},
  journal = {IEEE Wireless Communications},
  volume  = {26},
  number  = {5},
  pages   = {77--83},
  year    = {2019},
  doi     = {10.1109/MWC.2019.1800447}
}

@article{mohammadtaheri2025deepgreedyunfolding,
  title   = {Deep greedy unfolding: Sorting out argsorting in greedy sparse recovery algorithms},
  author  = {Mohammad-Taheri, Sina and Colbrook, Matthew J. and Brugiapaglia, Simone},
  journal = {arXiv preprint arXiv:2505.15661},
  year    = {2025},
  doi     = {10.48550/arXiv.2505.15661}
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

# contexts.txt (sent)

# Citation contexts for AFDM final report (run02, 2026-04-27)

Total \cite{} invocations: 89
Unique cite-keys used: 46
Total bib entries: 49 (3 uncited)

Each entry below: cite-key, then every place it is used (file:line) with the surrounding sentence.

---

## `afdm2025jointcesd` (3 uses)

- **sections/Section1.tex:160** — data-to-pilot and pilot-to-data interference rather than the multiplicative pilot--data coupling that defines the SP frame. Huang \emph{et al.}~\cite{afdm2025jointcesd} propose a joint AFDM receiver that combines a guard-interval-free iterative loop with a DNN-aided detector, demonstrating that learning-augmented joint AFDM receivers are tractable in principle, but

- **sections/Section1.tex:249** — attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn}. Within AFDM specifically, learned components have so far appeared at the detector~\cite{afdm2025jointcesd} rather than at the channel-support-selection step, and within the broader sparse-recovery literature the unrolling of greedy-OMP iterations has been

- **sections/Section4.tex:59** — Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\ Huang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & GI-free pilot & Sparse DD & Joint CE+SD / DNN-aided & no & different axis (no SP, no UWA focus) \\ \textbf{This work} & AFDM & \textbf{SP} & \textbf{Sparse DD + Dirichlet (1st-order MSML)} & \textbf{OMP-once + LS/MP-BP + learned top-$\Kadd$ ranker} & \textbf{yes (paired-frame McNemar, 3-seed pooled)} & --- \\ \bottomrule

## `balatsoukasstimming2019deepunfolding` (1 use)

- **sections/Section1.tex:234** — deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}, and rooted in the seminal Learned ISTA architecture of Gregor and LeCun~\cite{gregor2010lista}, in which iterations of a sparse-recovery

## `bemani2023afdm` (4 uses)

- **sections/Section1.tex:25** — orthogonality in a way that a single-tap frequency-domain equaliser cannot repair. Affine Frequency Division Multiplexing (AFDM)~\cite{bemani2023afdm} was designed for precisely such doubly dispersive channels. By placing information on a chirp basis defined through the discrete affine Fourier transform (DAFT), and choosing

- **sections/Section1.tex:91** — \paragraph{AFDM as a doubly-dispersive waveform and its channel-estimation primitives.} AFDM was introduced by Bemani \emph{et al.}~\cite{bemani2023afdm} as a chirp-based multicarrier waveform whose two tunable DAFT parameters $(c_1, c_2)$ can be aligned with the delay--Doppler geometry of the underlying

- **sections/Section2.tex:17** — \mby \;=\; \Heff\, \mbx + \mbn, \qquad \mbn \sim \mathcal{CN}(\mathbf{0}, \sigma_n^2 \mathbf{I}_{\Nsub}), \label{eq:afdm_model} \end{equation} where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel. Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, delivering on a one-dimensional transform the same time--frequency diversity that OTFS~\cite{hadani2017otfs,wei2021otfspromising} achieves through its two-dimensional delay--Doppler grid. This is the property that makes OMP-type sparse support recovery effective on $\Heff$, and it is the starting point of every receiver considered in this report. \subsection{Doubly-dispersive simulator channel and effective-channel sparsity}

- **sections/Section4.tex:52** — Work & Waveform & Pilot & Channel & Iterative / learned & Stat.\ disc. & vs this work \\ \midrule Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\

## `benzine2023sparseafdm` (3 uses)

- **sections/Section1.tex:102** — channel estimator for the integer delay--Doppler grid, formalising the threshold-based recovery rule that later sparse and Bayesian extensions would refine. Benzine \emph{et al.}~\cite{benzine2023sparseafdm} reformulated AFDM channel estimation as a sparse-recovery problem under embedded-pilot (EP) guard intervals, importing OMP~\cite{tropp2007signal} into the AFDM

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:53** — \midrule Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\

## `berger2010uwasparse` (3 uses)

- **sections/Section1.tex:19** — than in a typical RF link --- and produces both strong inter-carrier interference and fractional Doppler offsets relative to the underlying multicarrier grid~\cite{berger2010uwasparse,huang2010uwamimoofdm}. A conventional OFDM receiver cannot absorb either pathology cleanly: a cyclic prefix long enough for the full delay spread costs a prohibitive fraction of spectral efficiency, while a residual

- **sections/Section1.tex:180** — which each physical path acts as a time-varying low-pass filter, while Preisig~\cite{preisig2007uwa} formalised the propagation considerations governing UWA system design. Berger \emph{et al.}~\cite{berger2010uwasparse} then established compressive sensing as the natural channel-estimation primitive for multicarrier UWA links, and Huang \emph{et

- **sections/Section2.tex:274** — \label{ssec:fairness} Four receivers are compared head-to-head in Chapter~\ref{sec:results}. The \Serial{} arm is the closest single-pass realisation of the classical sparse-recovery literature~\cite{tropp2007signal,berger2010uwasparse} and makes the SP estimation-limited floor explicit. The \ClassicalJoint{} arm is the strongest classical baseline for AFDM-SP that this report constructs; it shares every component with \LearnedHead{} except the head itself, which is precisely the asymmetry needed to attribute observed gains to the learned module. The \Oracle{} arm uses the true $\Heff$ with pilot cancellation and a dense MMSE equaliser as a reference rather than as an information-theoretic lower bound (\S\ref{ssec:weaknesses}). All four receivers use identical master seeds, identical pilot sequences, identical frame budgets, and identical hyperparameters where applicable: in particular, the classical joint arm is the ablated learned receiver with its head disabled (zero appended atoms and head-logits set to $-\infty$). The only training-time asymmetry is that \LearnedHead{} has seen cached frames at $\snr \in \{10, 15, 20, 25\}$~dB; evaluation points at $\snr \in \{0, 5\}$~dB therefore lie outside the training distribution and are read as out-of-distribution checks rather than in-distribution comparisons. This asymmetry is declared at every table and figure where low-SNR numbers appear.

## `cao2024spomp` (1 use)

- **sections/Section1.tex:146** — to the chirp domain and introduces an iterative SP-AFDM channel estimator and signal detector with optimised pilot placement. Cao \emph{et al.}~\cite{cao2024spomp} subsequently combined the SP frame with an OMP front-end, leveraging the chirp-domain sparsity to lower the per-iteration estimation cost. Both works establish that, under SP-AFDM, an iterative loop

## `cui2007superimposed` (1 use)

- **sections/Section1.tex:123** — carries data and pilot energy under a fixed power split, was developed for OFDM more than a decade before AFDM. Cui and Tellambura~\cite{cui2007superimposed} and Tugnait and Luo~\cite{tugnait2006superimposed} derived ML and MMSE iterative estimators for SP-OFDM and proved that the equispaced equipowered placement minimises

## `elfwing2018silu` (1 use)

- **sections/Section2.tex:221** — \paragraph{Architecture.} The head consists of a shared pair encoder followed by a per-candidate scorer. The pair encoder, denoted $f_{\text{pair}}: \R^{6} \to \R^{16} \to \R^{16}$ with SiLU activation~\cite{elfwing2018silu} after each linear layer, is applied element-wise to every pair feature $\mathbf{v}_{i,s}$, contributing $(6 \cdot 16 + 16) + (16 \cdot 16 + 16) = 384$ parameters. For each candidate $i$, the resulting set of $|\hat{S}|$ per-pair 16-vectors is aggregated into a 32-dimensional pair descriptor by concatenating the element-wise maximum and the element-wise mean across $s$, with no additional trainable parameters. The pooled descriptor is concatenated with the 7-dimensional self-feature $\mathbf{u}_i$ to form a 39-dimensional vector and passed through the scorer $f_{\text{score}}: \R^{39} \to \R^{16} \to \R^{1}$ (SiLU after the first linear; zero-initialised output weights; output bias initialised at $-8$), contributing $(39 \cdot 16 + 16) + (16 \cdot 1 + 1) = 657$ parameters. The total trainable parameter count is $384 + 657 = 1\,041$, of which $\approx 37\%$ sit in the pair encoder and $\approx 63\%$ in the scorer. \paragraph{Inference.}

## `gregor2010lista` (1 use)

- **sections/Section1.tex:236** — Studer~\cite{balatsoukasstimming2019deepunfolding}, and rooted in the seminal Learned ISTA architecture of Gregor and LeCun~\cite{gregor2010lista}, in which iterations of a sparse-recovery algorithm are unrolled into trainable layers. The model-driven survey of He \emph{et al.}~\cite{he2019modeldrivensurvey} situates this philosophy

## `hadani2017otfs` (2 uses)

- **sections/Section1.tex:96** — channel, yielding a sparse one-dimensional input--output relation that recovers the diversity advantages of the two-dimensional OTFS modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} on doubly dispersive links. Subsequent investigations established the receiver-side primitives that make this representation operational. Yin and

- **sections/Section2.tex:17** — \mby \;=\; \Heff\, \mbx + \mbn, \qquad \mbn \sim \mathcal{CN}(\mathbf{0}, \sigma_n^2 \mathbf{I}_{\Nsub}), \label{eq:afdm_model} \end{equation} where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel. Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, delivering on a one-dimensional transform the same time--frequency diversity that OTFS~\cite{hadani2017otfs,wei2021otfspromising} achieves through its two-dimensional delay--Doppler grid. This is the property that makes OMP-type sparse support recovery effective on $\Heff$, and it is the starting point of every receiver considered in this report. \subsection{Doubly-dispersive simulator channel and effective-channel sparsity}

## `he2019modeldrivensurvey` (1 use)

- **sections/Section1.tex:238** — LeCun~\cite{gregor2010lista}, in which iterations of a sparse-recovery algorithm are unrolled into trainable layers. The model-driven survey of He \emph{et al.}~\cite{he2019modeldrivensurvey} situates this philosophy within physical-layer communications, arguing that combining domain-derived structure with learned components reduces both the training-data demand and

## `he2020modeldrivenmimo` (1 use)

- **sections/Section1.tex:244** — of the resulting literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the

## `he2020oampnet` (1 use)

- **sections/Section1.tex:244** — of the resulting literature targets MIMO detection --- exemplified by the model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the

## `huang2010uwamimoofdm` (2 uses)

- **sections/Section1.tex:19** — than in a typical RF link --- and produces both strong inter-carrier interference and fractional Doppler offsets relative to the underlying multicarrier grid~\cite{berger2010uwasparse,huang2010uwamimoofdm}. A conventional OFDM receiver cannot absorb either pathology cleanly: a cyclic prefix long enough for the full delay spread costs a prohibitive fraction of spectral efficiency, while a residual

- **sections/Section1.tex:183** — then established compressive sensing as the natural channel-estimation primitive for multicarrier UWA links, and Huang \emph{et al.}~\cite{huang2010uwamimoofdm} extended the sparse-recovery toolkit to MIMO-OFDM-UWA with iterative channel estimation and decoding. Within the OFDM-UWA literature this lineage diversified into greedy variants such as

## `junejo2018labomp` (1 use)

- **sections/Section1.tex:186** — MIMO-OFDM-UWA with iterative channel estimation and decoding. Within the OFDM-UWA literature this lineage diversified into greedy variants such as backtracking OMP~\cite{junejo2018labomp} and Bayesian variants based on sparse Bayesian learning, all of which testify to the practical robustness of the sparse-recovery approach but operate within OFDM rather than within a

## `kaleh2005zadoffchu` (1 use)

- **sections/Section2.tex:51** — \mbx \;=\; \sqrt{\rhop}\; \xp \;+\; \sqrt{1 - \rhop}\; \xd, \qquad \rhop \in (0, 1), \label{eq:sp_frame} \end{equation} where $\xp$ is a deterministic Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector. The canonical pilot power fraction is $\rhop = 0.5$; higher $\rhop$ strengthens the pilot observation at the cost of data energy, and lower $\rhop$ does the converse~\cite{orozco2011superimposed,tugnait2006superimposed}. Under the model~\eqref{eq:afdm_model}, the pilot projection performed at the receiver yields \begin{equation} \xp^H \mby \;=\; \sqrt{\rhop}\; \xp^H \Heff \xp \;+\; \sqrt{1 - \rhop}\; \xp^H \Heff \xd \;+\; \xp^H \mbn, \label{eq:pilot_projection}

## `khani2020mmnet` (1 use)

- **sections/Section1.tex:246** — al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn}. Within AFDM specifically, learned

## `kschischang2001factorgraph` (1 use)

- **sections/Section2.tex:145** — \paragraph{MP-BP messages on the sparse chirp-domain factor graph.} The data-detection block of Algorithm~\ref{alg:joint} follows the iterative-receiver framework of Wymeersch~\cite{wymeersch2007iterativereceiver} and the factor-graph paradigm surveyed by Kschischang~\emph{et~al.}~\cite{kschischang2001factorgraph}, and is implemented as Gaussian message passing on a bipartite factor graph derived from the pilot-subtracted observation. Subtracting the estimated pilot contribution from~\eqref{eq:afdm_model} yields, for every $j \in \{0, \dots, \Nsub - 1\}$, \begin{equation} \tilde{y}_j \;:=\; y_j - \sqrt{\rhop}\, [\Heff(\hat{\mbh}^{(t)})\, \xp]_j \;=\; \sum_{i \in \mathcal{N}(j)} \tilde{H}_{j,i}\, x_{d,i} \;+\; n_j, \label{eq:mpbp_input}

## `liang2011iterativesp` (1 use)

- **sections/Section1.tex:129** — al.}~\cite{orozco2011superimposed} established the optimality of the equipowered training pattern under the spectral-efficiency constraint. Liang \emph{et al.}~\cite{liang2011iterativesp} subsequently demonstrated that superimposed pilots can match preamble-based channel estimation in OFDM-WLAN at the cost of an iterative receiver, isolating the regime in which the

## `loshchilov2019adamw` (1 use)

- **sections/Section2.tex:235** — \mathcal{L}(\theta) \;=\; \mathcal{L}_{\text{BCE}}(\theta) \;+\; \lambda_{\text{rank}} \cdot \max\bigl(0,\; 1 - \min_{y_i=1} s_i(\theta) + \max_{y_j=0} s_j(\theta)\bigr), \qquad \lambda_{\text{rank}} = 0.5, \label{eq:loss} \end{equation} where $s_i(\theta)$ is the scorer logit for candidate $i$ and $\theta$ are the head parameters. Training uses AdamW~\cite{loshchilov2019adamw} with learning rate $10^{-3}$, weight decay $10^{-4}$, batch size $512$ cached frames, for 8 epochs with early stopping on the validation BCE (patience = 2). The cache is split 90/10 frame-level into train/val at fixed seed $13\,579$. The training cache used for the deployed checkpoint is a 27\,k-frame 4-SNR cache at $\snr \in \{10, 15, 20, 25\}$~dB with per-SNR frame weights $\{0.2, 0.3, 0.3, 0.2\}$, harvested at the $\fs = 4B$ operating point. Covering $\snr = 25$~dB explicitly in the cache is necessary to avoid a slight regression in the head's high-SNR behaviour at the same operating point.

## `ma2024oversampledafdm` (4 uses)

- **sections/Section1.tex:193** — The closest physical-layer refinements to the AFDM-UWA setting considered here form a cluster of three threads. Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} show that observing the chirp-domain signal at twice the Nyquist rate yields a tangible channel-estimation improvement that is independent of any learned component; this directly motivates the

- **sections/Section4.tex:35** — \label{ssec:disc_oversampling} The choice $\fs = 4B$ adopted throughout the report has a physical rather than complexity-driven motivation. From~\eqref{eq:kmax}, $\kmax \propto 1/\fs$, so moving from $2B$ to $4B$ halves $\kmax$ from $4$ to $2$; simultaneously $\lmax = \lceil \tau_{\text{spread}} \fs \rceil$ doubles from $80$ to $160$. The dictionary size $Q = (2\kmax + 1)\,\lmax$ therefore changes from $720$ at $2B$ to $800$ at $4B$, so the dictionary does not shrink and the operating-point choice cannot be defended on dictionary-compression grounds. The actual benefit comes from two physical effects. First, with a finer integer Doppler grid the residual fractional offset $k^\text{real} - \mathrm{round}(k^\text{real})$ has a smaller expected magnitude, so the side-lobe energy in~\eqref{eq:dirichlet} is systematically smaller and the virtual-tap sparsity pattern is tighter. Second, the OMP matched-filter contrast between true atoms and data-interference atoms improves empirically at $4B$: both the OMP NMSE at $\snr = 15$~dB and the iterative joint BER at $\snr \geq 20$~dB are strictly better at $4B$ than at $2B$ (Fig.~\ref{fig:ber4b}). At the $4B$ operating point the serial-receiver NMSE saturates at $-11.3$~dB at $\snr = 15$~dB, which is low enough that the iterative joint recipe has sufficient SNR margin to descend two to three orders of magnitude in BER below the serial floor (Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}). The oversampling choice is consistent with the oversampled AFDM joint CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}, where oversampling is shown to help channel estimation independently of any learning component. \subsection{Position relative to prior AFDM and UWA work}

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:57** — Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2024drceafdm} & MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\ Huang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & GI-free pilot & Sparse DD & Joint CE+SD / DNN-aided & no & different axis (no SP, no UWA focus) \\

## `mishra2022otfssp` (1 use)

- **sections/Section1.tex:137** — and therefore produces a high-SNR error floor that single-pass estimation cannot remove. In delay--Doppler waveforms specifically, Mishra \emph{et al.}~\cite{mishra2022otfssp} extended the SP framework to OTFS, and Neelam and Sahu~\cite{neelam2023otsmsp} carried it to OTSM, in both cases confirming that an iterative loop alternating pilot-data interference cancellation and

## `mohammadtaheri2025deepgreedyunfolding` (1 use)

- **sections/Section1.tex:252** — rather than at the channel-support-selection step, and within the broader sparse-recovery literature the unrolling of greedy-OMP iterations has been studied only recently~\cite{mohammadtaheri2025deepgreedyunfolding}, where the non-differentiable argsort operator is approached via softsort relaxations. The OMP support-refinement slot inside an SP-AFDM joint

## `monga2021unrolling` (2 uses)

- **sections/Section1.tex:233** — At the architectural level, the proposed learned head sits within the deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} and Balatsoukas-Stimming and Studer~\cite{balatsoukasstimming2019deepunfolding}, and rooted in the seminal Learned ISTA architecture of Gregor and

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

## `neelam2023otsmsp` (1 use)

- **sections/Section1.tex:138** — cannot remove. In delay--Doppler waveforms specifically, Mishra \emph{et al.}~\cite{mishra2022otfssp} extended the SP framework to OTFS, and Neelam and Sahu~\cite{neelam2023otsmsp} carried it to OTSM, in both cases confirming that an iterative loop alternating pilot-data interference cancellation and channel re-estimation is unavoidable once the EP assumption is abandoned.

## `orozco2011superimposed` (3 uses)

- **sections/Section1.tex:43** — To preserve the data-carrying capacity that an AFDM frame would otherwise lose to dedicated pilots, this work adopts a superimposed-pilot (SP) transmission~\cite{orozco2011superimposed,tugnait2006superimposed} in which every chirp sub-carrier simultaneously carries data and pilot energy under a fixed power split $\rhop$. SP doubles the available data capacity relative to a

- **sections/Section1.tex:127** — for SP-OFDM and proved that the equispaced equipowered placement minimises the Cram\'er--Rao bound, while Orozco-Lugo \emph{et al.}~\cite{orozco2011superimposed} established the optimality of the equipowered training pattern under the spectral-efficiency constraint. Liang \emph{et al.}~\cite{liang2011iterativesp} subsequently demonstrated that

- **sections/Section2.tex:51** — \mbx \;=\; \sqrt{\rhop}\; \xp \;+\; \sqrt{1 - \rhop}\; \xd, \qquad \rhop \in (0, 1), \label{eq:sp_frame} \end{equation} where $\xp$ is a deterministic Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector. The canonical pilot power fraction is $\rhop = 0.5$; higher $\rhop$ strengthens the pilot observation at the cost of data energy, and lower $\rhop$ does the converse~\cite{orozco2011superimposed,tugnait2006superimposed}. Under the model~\eqref{eq:afdm_model}, the pilot projection performed at the receiver yields \begin{equation} \xp^H \mby \;=\; \sqrt{\rhop}\; \xp^H \Heff \xp \;+\; \sqrt{1 - \rhop}\; \xp^H \Heff \xd \;+\; \xp^H \mbn, \label{eq:pilot_projection}

## `preisig2007uwa` (2 uses)

- **sections/Section1.tex:14** — delay spreads of several to tens of milliseconds, which at the 4--12~kHz bandwidth budgets typical of UWA modems translates to hundreds of resolvable delay bins~\cite{stojanovic2009uwa,preisig2007uwa}. The propagation speed of $c \approx 1500$~m/s, combined with platform motion of even a few~m/s, yields a relative Doppler of order $v / c \sim 10^{-3}$~--- three to four orders of magnitude larger

- **sections/Section1.tex:179** — channel as severely doubly dispersive with a sparse impulse response in which each physical path acts as a time-varying low-pass filter, while Preisig~\cite{preisig2007uwa} formalised the propagation considerations governing UWA system design. Berger \emph{et al.}~\cite{berger2010uwasparse} then established compressive sensing as the natural channel-estimation

## `pu2024epotfs` (1 use)

- **sections/Section1.tex:223** — fractional Doppler shifts. Subsequent OTFS detector designs --- including unitary-AMP variants~\cite{yuan2022uampotfs}, expectation-propagation formulations~\cite{pu2024epotfs}, and graph-neural-network refinements~\cite{zhuang2024amgnnotfs} --- have refined the complexity--accuracy tradeoff but preserve the sparse-graph philosophy. The

## `qing2024spafdm` (5 uses)

- **sections/Section1.tex:143** — The most directly relevant SP-AFDM line is the recent cluster initiated by Zheng \emph{et al.}~\cite{qing2024spafdm}, which adapts the OFDM SP machinery to the chirp domain and introduces an iterative SP-AFDM channel estimator and signal detector with optimised pilot placement. Cao \emph{et

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:54** — Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\ Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2024drceafdm} & MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\

- **sections/Section4.tex:77** — The simulator is a block-fading sparse delay--Doppler channel with exponential power-delay profile and Dirichlet fractional-Doppler expansion. Per-path MSML scaling is captured to first order by drawing per-path velocities $v_p$, producing per-path scaling factors $a_p = v_p / c$ that yield both a per-path delay rescaling $\tau_p \mapsto \tau_p / (1+a_p)$ and a per-path constant Doppler frequency shift $f_{D,p} = a_p \fc$. What is not modelled is full broadband per-path waveform resampling within a symbol or per-frame Doppler jitter, both of which are present in real UWA propagation~\cite{zhou2024msmlafdm}. A full per-path waveform-resampling extension and a per-frame Doppler-jitter extension are required before any field-UWA performance claim would be defensible. No head-to-head numerical reproduction of a published AFDM-SP or AFDM-JCEDD baseline is performed on the present channel realisations; all comparisons are against internally constructed baselines, and the structural mapping in Table~\ref{tab:priorart} remains qualitative. A direct re-implementation of the SP-AFDM estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} on the present seed blocks is the natural follow-up to convert this structural mapping into a quantitative comparison. Several scope choices are fixed throughout the report and are not swept: a single-antenna (1T1R) configuration, QPSK modulation, a fixed pilot-power fraction $\rhop = 0.5$, and a fixed kinematic regime ($v_\text{mean} = 2$~m/s, $v_\text{std} = 0.5$~m/s). Extensions to MIMO / space-time AFDM, higher-order QAM, an SNR-dependent $\rhop$ sweep, and high-velocity scenarios above $5$~m/s are all natural follow-ups but lie outside the present scope.

- **sections/Section5.tex:23** — Four directions would sharpen the contribution and extend the design statement made here from a simulator-based observation toward an operational underwater acoustic modem claim. The most immediate is a multi-seed retraining study, with three to five independent training seeds per SNR cell, which would convert the present single-checkpoint observation into a learning-variance statement and place error bars on the pooled $\approx 2$~dB headline. A direct re-implementation of the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} on the present $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks would convert the qualitative structural comparison of Table~\ref{tab:priorart} into a quantitative prior-art comparison and resolve whether the OMP-once design loses, matches, or surpasses an SP-AFDM receiver that re-runs the sparse step. Extending the simulator from the first-order per-path MSML approximation (per-path constant Doppler shift plus delay rescaling) to full broadband per-path waveform resampling and per-frame Doppler jitter, following Cao \emph{et al.}~\cite{zhou2024msmlafdm}, would bring the physical-layer model closer to real UWA propagation and test whether the mechanism-level conclusions identified here transfer to a more realistic propagation regime. Finally, an engineering-deployability study measuring runtime, memory-hierarchy effects, and energy consumption on a reference embedded target such as a DSP or FPGA implementation would extend the low-complexity claim from per-frame arithmetic into deployment cost, completing the path from receiver design to operational specification.

## `raviteja2018otfs` (2 uses)

- **sections/Section1.tex:96** — channel, yielding a sparse one-dimensional input--output relation that recovers the diversity advantages of the two-dimensional OTFS modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} on doubly dispersive links. Subsequent investigations established the receiver-side primitives that make this representation operational. Yin and

- **sections/Section1.tex:218** — On the detection side, the proposed inner LS/MP-BP loop inherits from the sparse delay--Doppler message-passing literature pioneered by Raviteja \emph{et al.}~\cite{raviteja2018otfs}, in which a low-complexity factor-graph detector exploits the natural sparsity of the OTFS channel matrix and explicitly handles the inter-Doppler interference produced by

## `rou2024otfstoafdm` (1 use)

- **sections/Section1.tex:110** — diagonal-reconstruction estimator that explicitly addresses the inter-Doppler interference produced by fractional Doppler residuals, while the comparative survey of Rou \emph{et al.}~\cite{rou2024otfstoafdm} situated AFDM alongside OTFS and OCDM within an integrated sensing-and-communication context. Two practitioner-oriented overviews~\cite{yin2025afdmoverview,zhou2025afdmicsc}

## `shlezinger2021deepsic` (1 use)

- **sections/Section1.tex:245** — model-driven detectors of He \emph{et al.}~\cite{he2020modeldrivenmimo,he2020oampnet}, the soft interference cancellation network DeepSIC~\cite{shlezinger2021deepsic}, the adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et

## `stojanovic2009uwa` (2 uses)

- **sections/Section1.tex:14** — delay spreads of several to tens of milliseconds, which at the 4--12~kHz bandwidth budgets typical of UWA modems translates to hundreds of resolvable delay bins~\cite{stojanovic2009uwa,preisig2007uwa}. The propagation speed of $c \approx 1500$~m/s, combined with platform motion of even a few~m/s, yields a relative Doppler of order $v / c \sim 10^{-3}$~--- three to four orders of magnitude larger

- **sections/Section1.tex:176** — long line of evidence that UWA channels are well approximated by a sparse delay--Doppler representation. Stojanovic and Preisig~\cite{stojanovic2009uwa} characterised the underwater acoustic channel as severely doubly dispersive with a sparse impulse response in which each physical path acts as a time-varying low-pass filter, while

## `tropp2007signal` (4 uses)

- **sections/Section1.tex:35** — wei2021otfspromising} would produce. The resulting sparsity is what makes sparse-recovery channel estimation with orthogonal matching pursuit (OMP)~\cite{tropp2007signal} tractable~\cite{benzine2023sparseafdm,% rou2024otfstoafdm}, and is the starting point of every receiver considered in this report.

- **sections/Section1.tex:104** — refine. Benzine \emph{et al.}~\cite{benzine2023sparseafdm} reformulated AFDM channel estimation as a sparse-recovery problem under embedded-pilot (EP) guard intervals, importing OMP~\cite{tropp2007signal} into the AFDM literature and demonstrating that the sparsity of the chirp-domain effective channel makes greedy recovery a natural fit. Yin \emph{et

- **sections/Section2.tex:274** — \label{ssec:fairness} Four receivers are compared head-to-head in Chapter~\ref{sec:results}. The \Serial{} arm is the closest single-pass realisation of the classical sparse-recovery literature~\cite{tropp2007signal,berger2010uwasparse} and makes the SP estimation-limited floor explicit. The \ClassicalJoint{} arm is the strongest classical baseline for AFDM-SP that this report constructs; it shares every component with \LearnedHead{} except the head itself, which is precisely the asymmetry needed to attribute observed gains to the learned module. The \Oracle{} arm uses the true $\Heff$ with pilot cancellation and a dense MMSE equaliser as a reference rather than as an information-theoretic lower bound (\S\ref{ssec:weaknesses}). All four receivers use identical master seeds, identical pilot sequences, identical frame budgets, and identical hyperparameters where applicable: in particular, the classical joint arm is the ablated learned receiver with its head disabled (zero appended atoms and head-logits set to $-\infty$). The only training-time asymmetry is that \LearnedHead{} has seen cached frames at $\snr \in \{10, 15, 20, 25\}$~dB; evaluation points at $\snr \in \{0, 5\}$~dB therefore lie outside the training distribution and are read as out-of-distribution checks rather than in-distribution comparisons. This asymmetry is declared at every table and figure where low-SNR numbers appear.

- **Appendices/Appendix.tex:126** — \begin{algorithm}[t] \caption{Orthogonal Matching Pursuit on the chirp-domain pilot dictionary~\cite{tropp2007signal}.} \label{alg:omp} \begin{small}

## `tugnait2006superimposed` (3 uses)

- **sections/Section1.tex:43** — To preserve the data-carrying capacity that an AFDM frame would otherwise lose to dedicated pilots, this work adopts a superimposed-pilot (SP) transmission~\cite{orozco2011superimposed,tugnait2006superimposed} in which every chirp sub-carrier simultaneously carries data and pilot energy under a fixed power split $\rhop$. SP doubles the available data capacity relative to a

- **sections/Section1.tex:124** — OFDM more than a decade before AFDM. Cui and Tellambura~\cite{cui2007superimposed} and Tugnait and Luo~\cite{tugnait2006superimposed} derived ML and MMSE iterative estimators for SP-OFDM and proved that the equispaced equipowered placement minimises the Cram\'er--Rao bound, while Orozco-Lugo \emph{et

- **sections/Section2.tex:51** — \mbx \;=\; \sqrt{\rhop}\; \xp \;+\; \sqrt{1 - \rhop}\; \xd, \qquad \rhop \in (0, 1), \label{eq:sp_frame} \end{equation} where $\xp$ is a deterministic Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector. The canonical pilot power fraction is $\rhop = 0.5$; higher $\rhop$ strengthens the pilot observation at the cost of data energy, and lower $\rhop$ does the converse~\cite{orozco2011superimposed,tugnait2006superimposed}. Under the model~\eqref{eq:afdm_model}, the pilot projection performed at the receiver yields \begin{equation} \xp^H \mby \;=\; \sqrt{\rhop}\; \xp^H \Heff \xp \;+\; \sqrt{1 - \rhop}\; \xp^H \Heff \xd \;+\; \xp^H \mbn, \label{eq:pilot_projection}

## `wei2021otfspromising` (2 uses)

- **sections/Section1.tex:96** — channel, yielding a sparse one-dimensional input--output relation that recovers the diversity advantages of the two-dimensional OTFS modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} on doubly dispersive links. Subsequent investigations established the receiver-side primitives that make this representation operational. Yin and

- **sections/Section2.tex:17** — \mby \;=\; \Heff\, \mbx + \mbn, \qquad \mbn \sim \mathcal{CN}(\mathbf{0}, \sigma_n^2 \mathbf{I}_{\Nsub}), \label{eq:afdm_model} \end{equation} where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel. Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, delivering on a one-dimensional transform the same time--frequency diversity that OTFS~\cite{hadani2017otfs,wei2021otfspromising} achieves through its two-dimensional delay--Doppler grid. This is the property that makes OMP-type sparse support recovery effective on $\Heff$, and it is the starting point of every receiver considered in this report. \subsection{Doubly-dispersive simulator channel and effective-channel sparsity}

## `wymeersch2007iterativereceiver` (3 uses)

- **sections/Section1.tex:57** — The natural response to a structured estimation residual is to iterate between channel estimation and symbol detection~\cite{wymeersch2007iterativereceiver}: each detection pass produces tentative data estimates that can be subtracted from the pilot observation, sharpening the next channel estimate. Two naive

- **sections/Section2.tex:145** — \paragraph{MP-BP messages on the sparse chirp-domain factor graph.} The data-detection block of Algorithm~\ref{alg:joint} follows the iterative-receiver framework of Wymeersch~\cite{wymeersch2007iterativereceiver} and the factor-graph paradigm surveyed by Kschischang~\emph{et~al.}~\cite{kschischang2001factorgraph}, and is implemented as Gaussian message passing on a bipartite factor graph derived from the pilot-subtracted observation. Subtracting the estimated pilot contribution from~\eqref{eq:afdm_model} yields, for every $j \in \{0, \dots, \Nsub - 1\}$, \begin{equation} \tilde{y}_j \;:=\; y_j - \sqrt{\rhop}\, [\Heff(\hat{\mbh}^{(t)})\, \xp]_j \;=\; \sum_{i \in \mathcal{N}(j)} \tilde{H}_{j,i}\, x_{d,i} \;+\; n_j, \label{eq:mpbp_input}

- **sections/Section2.tex:165** — \frac{1}{\sigma_{d,i}^2} \;=\; \!\sum_{j \in \mathcal{M}(i)}\! \frac{1}{v_{j \to i}^{(T_\text{mp})}}, \qquad \frac{\hat{x}_{d,i}}{\sigma_{d,i}^2} \;=\; \!\sum_{j \in \mathcal{M}(i)}\! \frac{\mu_{j \to i}^{(T_\text{mp})}}{v_{j \to i}^{(T_\text{mp})}}, \label{eq:mpbp_post} \end{equation} followed by a Gray-coded QPSK projection $\hat{x}_{d,i} \mapsto \mathrm{QPSK\text{-}demap}(\hat{x}_{d,i})$ that returns the hard-decision data symbol. The Gaussian approximation maintained throughout the inner loop is the standard soft-Gaussian belief-propagation form for finite-alphabet symbols~\cite{wymeersch2007iterativereceiver}, with the QPSK constraint enforced only at the final projection. Because $|\mathcal{N}(j)|$ and $|\mathcal{M}(i)|$ are bounded by constants independent of $\Nsub$, each inner iteration evaluates $\mathcal{O}(\preal \cdot \Nsub)$ scalar updates across all factor and variable nodes, so the data-detection block costs $\mathcal{O}(T_\text{mp} \Nsub)$ per outer iteration. This is the source of the $\mathcal{O}(T_\text{mp} \Nsub)$ term in the per-frame budget of~\eqref{eq:classcomplex}, and it is two orders of magnitude cheaper than a chirp-domain dense MMSE equaliser's $\mathcal{O}(\Nsub^3)$ at $\Nsub = 1024$. Four design choices in Algorithm~\ref{alg:joint} are central to the receiver's behaviour, and each rejects a simpler or more expensive alternative on empirical or analytical grounds. The OMP-once choice rests on a stability observation: the empirical support Jaccard between successive OMP passes in a hypothetical full re-OMP schedule exceeds $0.94$ from iteration~2 onwards (Fig.~\ref{fig:iterconv}), so the atoms within the support are already stable after a single pass and the only quantity that continues to evolve is the per-path gain amplitude. Chapter~\ref{sec:results}~(\S\ref{ssec:probes}) confirms this independently: OMP-once recovers a mean $\approx 95\%$ recall against the effective Dirichlet-expanded virtual-tap oracle support across all training SNRs (Table~\ref{tab:supportrecall}), so a second OMP pass has nothing new to find. Re-running OMP across outer iterations therefore re-solves a near-identical atom-selection problem $T_\text{out} = 5$ times per frame at a constant-factor overhead of $\sim 5\times$~\eqref{eq:omp_cost} without any change in asymptotic class. Once the support is locked, the path gains are refined by a damped DA-LS update rather than a full LS solve: a full LS over the unrestricted dictionary would amplify noise from unexplored columns, whereas the DA-LS refit \eqref{eq:dals} on the locked support uses exactly the $\Ppath \approx 8$ physical (or $\approx 28$ virtual) taps from step~1 and keeps the gain-update cost at $\mathcal{O}(\Ppath^2 \Nsub)$.

## `xu2024detecttolearn` (1 use)

- **sections/Section1.tex:248** — adaptive-detection scheme MMNet~\cite{khani2020mmnet}, and the attention-augmented receiver of Xu \emph{et al.}~\cite{xu2024detecttolearn}. Within AFDM specifically, learned components have so far appeared at the detector~\cite{afdm2025jointcesd} rather than at the channel-support-selection step, and within the broader

## `yin2022fractionaldopplerafdm` (1 use)

- **sections/Section1.tex:99** — doubly dispersive links. Subsequent investigations established the receiver-side primitives that make this representation operational. Yin and Tang~\cite{yin2022fractionaldopplerafdm} developed the pilot-aided AFDM channel estimator for the integer delay--Doppler grid, formalising the threshold-based recovery rule that later sparse and Bayesian extensions would

## `yin2024drceafdm` (5 uses)

- **sections/Section1.tex:107** — literature and demonstrating that the sparsity of the chirp-domain effective channel makes greedy recovery a natural fit. Yin \emph{et al.}~\cite{yin2024drceafdm} extended this line to MIMO-AFDM by deriving a diagonal-reconstruction estimator that explicitly addresses the inter-Doppler interference produced by fractional Doppler residuals, while the comparative

- **sections/Section1.tex:207** — floor nor the Dirichlet-leakage support residual that motivates the present design. The fractional-Doppler problem itself has been treated directly by Yin \emph{et al.}~\cite{yin2024drceafdm} via a diagonal-reconstruction estimator targeting the very Dirichlet leakage that single-pass OMP fails to capture, but the formulation is non-SP and the leakage repair is not

- **sections/Section2.tex:29** — k_p^{\text{real}} = \frac{v_p \, \fc \, \Nsub}{c \, \fs}, \label{eq:delaydoppler_mapping} \end{align} with $c \approx 1500$~m/s the speed of sound. The delay index $l_p$ is integer by construction, but $k_p^{\text{real}}$ is typically fractional: the residual fractional Doppler is absorbed via a discrete-Dirichlet-kernel (aliased-sinc) expansion~\cite{yin2024drceafdm} of half-width $\kleak = 2$, so that path $p$ is decomposed into $2\kleak + 1 = 5$ virtual integer-bin taps with magnitude \begin{equation} |\tilde{h}_{p,j}| \;=\; |h_p| \cdot \left| \frac{\sin\bigl(\pi (k_p^{\text{real}} - k_p - j)\bigr)}{\Nsub \, \sin\bigl(\pi (k_p^{\text{real}} - k_p - j)/\Nsub\bigr)} \right|, \qquad j \in \{-\kleak, \dots, \kleak\}, \label{eq:dirichlet}

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:56** — Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2024drceafdm} & MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\

## `yin2025afdmoverview` (1 use)

- **sections/Section1.tex:112** — survey of Rou \emph{et al.}~\cite{rou2024otfstoafdm} situated AFDM alongside OTFS and OCDM within an integrated sensing-and-communication context. Two practitioner-oriented overviews~\cite{yin2025afdmoverview,zhou2025afdmicsc} now collect these threads. Across this body of work, the EP frame keeps the pilot observation pilot-only and yields analytically clean sparse-recovery

## `yuan2022uampotfs` (1 use)

- **sections/Section1.tex:222** — matrix and explicitly handles the inter-Doppler interference produced by fractional Doppler shifts. Subsequent OTFS detector designs --- including unitary-AMP variants~\cite{yuan2022uampotfs}, expectation-propagation formulations~\cite{pu2024epotfs}, and graph-neural-network refinements~\cite{zhuang2024amgnnotfs} --- have refined the

## `zhao2024gifreeafdm` (3 uses)

- **sections/Section1.tex:154** — captures the bulk of the channel energy and therefore makes per-iteration re-OMP redundant. Adjacent to these SP-focused works, Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} reach a structurally similar conclusion via a guard-interval-free pilot-aided AFDM design with iterative interference cancellation; their formulation, however, departs from SP in that it

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:55** — Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\ Zheng \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\ Zhou \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free pilot-aided & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\ Yin \emph{et al.}~\cite{yin2024drceafdm} & MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\

## `zhou2024msmlafdm` (6 uses)

- **sections/Section1.tex:199** — result is established in a non-SP, non-learning configuration and does not address either pilot-data interference or fractional-Doppler support residuals. Cao \emph{et al.}~\cite{zhou2024msmlafdm} extend AFDM-OMP to multi-scale multi-lag (MSML) UWA channels in which each physical path carries an independent time-scale factor, establishing that the AFDM

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:40** — \label{ssec:disc_priorart} The receiver developed in this report inherits design ingredients from several distinct lines of published work. The sparse-recovery channel-estimation skeleton follows Benzine \emph{et al.}~\cite{benzine2023sparseafdm} and the broader AFDM-OMP literature. The iterative joint estimation--detection structure follows the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} and the GI-free pilot-aided receiver of Zhou \emph{et al.}~\cite{zhao2024gifreeafdm}, both of which establish that an iterative loop is unavoidable once the pilot observation is contaminated by unknown data. The fractional-Doppler Dirichlet expansion follows the diagonal-reconstruction line of Yin \emph{et al.}~\cite{yin2024drceafdm}, which targets the leakage that OMP fails to capture in a single pass. The $4B$ operating point is consistent with the oversampled AFDM CE/DD receiver of Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm}. The MSML treatment is a first-order approximation of the per-path time-scaling formulation of Cao \emph{et al.}~\cite{zhou2024msmlafdm}: per-path velocities $v_p$ are drawn and converted into per-path Doppler scaling factors $a_p = v_p / c$ that produce a per-path delay rescaling $\tau_p \mapsto \tau_p / (1 + a_p)$ and a constant per-path Doppler frequency shift $f_{D,p} = a_p \fc$, in place of the full broadband per-path waveform resampling of~\cite{zhou2024msmlafdm}. The deep-unfolding tradition surveyed by Monga \emph{et al.}~\cite{monga2021unrolling} provides the architectural template for embedding the learned support-refinement block inside an otherwise model-based receiver. Table~\ref{tab:priorart} consolidates this design provenance along the axes that distinguish the receiver from each cited line of work. \begin{table}[t]

- **sections/Section4.tex:58** — Yin \emph{et al.}~\cite{yin2024drceafdm} & MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / none & no & complementary \\ Ranasinghe \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\ Cao \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (full MSML) \\ Huang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & GI-free pilot & Sparse DD & Joint CE+SD / DNN-aided & no & different axis (no SP, no UWA focus) \\ \textbf{This work} & AFDM & \textbf{SP} & \textbf{Sparse DD + Dirichlet (1st-order MSML)} & \textbf{OMP-once + LS/MP-BP + learned top-$\Kadd$ ranker} & \textbf{yes (paired-frame McNemar, 3-seed pooled)} & --- \\

- **sections/Section4.tex:75** — The complexity accounting is restricted to per-frame multiply-accumulate counts. Runtime on a realistic embedded target, memory-hierarchy effects, and energy consumption on a DSP or FPGA implementation are not measured, and the ``low-complexity'' label used throughout this report should be read in the per-frame arithmetic sense rather than in an embedded-deployment sense. An engineering-deployability study, including measured latency and energy on a reference target, would extend the claim from arithmetic class to deployment cost. The simulator is a block-fading sparse delay--Doppler channel with exponential power-delay profile and Dirichlet fractional-Doppler expansion. Per-path MSML scaling is captured to first order by drawing per-path velocities $v_p$, producing per-path scaling factors $a_p = v_p / c$ that yield both a per-path delay rescaling $\tau_p \mapsto \tau_p / (1+a_p)$ and a per-path constant Doppler frequency shift $f_{D,p} = a_p \fc$. What is not modelled is full broadband per-path waveform resampling within a symbol or per-frame Doppler jitter, both of which are present in real UWA propagation~\cite{zhou2024msmlafdm}. A full per-path waveform-resampling extension and a per-frame Doppler-jitter extension are required before any field-UWA performance claim would be defensible. No head-to-head numerical reproduction of a published AFDM-SP or AFDM-JCEDD baseline is performed on the present channel realisations; all comparisons are against internally constructed baselines, and the structural mapping in Table~\ref{tab:priorart} remains qualitative. A direct re-implementation of the SP-AFDM estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} on the present seed blocks is the natural follow-up to convert this structural mapping into a quantitative comparison.

- **sections/Section5.tex:25** — The most immediate is a multi-seed retraining study, with three to five independent training seeds per SNR cell, which would convert the present single-checkpoint observation into a learning-variance statement and place error bars on the pooled $\approx 2$~dB headline. A direct re-implementation of the SP-AFDM channel estimator of Zheng \emph{et al.}~\cite{qing2024spafdm} on the present $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks would convert the qualitative structural comparison of Table~\ref{tab:priorart} into a quantitative prior-art comparison and resolve whether the OMP-once design loses, matches, or surpasses an SP-AFDM receiver that re-runs the sparse step. Extending the simulator from the first-order per-path MSML approximation (per-path constant Doppler shift plus delay rescaling) to full broadband per-path waveform resampling and per-frame Doppler jitter, following Cao \emph{et al.}~\cite{zhou2024msmlafdm}, would bring the physical-layer model closer to real UWA propagation and test whether the mechanism-level conclusions identified here transfer to a more realistic propagation regime. Finally, an engineering-deployability study measuring runtime, memory-hierarchy effects, and energy consumption on a reference embedded target such as a DSP or FPGA implementation would extend the low-complexity claim from per-frame arithmetic into deployment cost, completing the path from receiver design to operational specification.

## `zhou2025afdmicsc` (1 use)

- **sections/Section1.tex:112** — survey of Rou \emph{et al.}~\cite{rou2024otfstoafdm} situated AFDM alongside OTFS and OCDM within an integrated sensing-and-communication context. Two practitioner-oriented overviews~\cite{yin2025afdmoverview,zhou2025afdmicsc} now collect these threads. Across this body of work, the EP frame keeps the pilot observation pilot-only and yields analytically clean sparse-recovery

## `zhuang2024amgnnotfs` (1 use)

- **sections/Section1.tex:224** — unitary-AMP variants~\cite{yuan2022uampotfs}, expectation-propagation formulations~\cite{pu2024epotfs}, and graph-neural-network refinements~\cite{zhuang2024amgnnotfs} --- have refined the complexity--accuracy tradeoff but preserve the sparse-graph philosophy. The present work transports this MP-BP machinery into the chirp-domain factor

---

## Uncited entries (still in bib but never used)

- `candes2006cs`
- `donoho2009amp`
- `li2002channelestimationofdm`
