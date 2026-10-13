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
