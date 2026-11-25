---
name: idea-funnel
description: "Research-problem funnel: deep-think idea cards one by one, screen in cheap layers, stop when ~10 merit long simulation; triggers: idea funnel, 跑一轮idea, 看板"
---

# Idea funnel

Purpose: find research problems worth a paper (unsolved or unnoticed, and valuable). The AI thinks ideas through one at a
time with full effort, keeps going, screens everything it has together at intervals with cheap checks, grows promising
ideas into variants (a tree), and stops a round when about ten ideas merit a long simulation. Eric reads only those.
Any agent tool can run it: this file is the whole protocol; the data are plain markdown cards in a project folder.

Design reasons and sources: [DESIGN.md](DESIGN.md) (read only when changing this protocol).

## Files

- This skill folder: `METHODS.md` (idea-generation methods with sources; read before every round), this protocol,
  templates and scripts.
- Funnel folder (one per project, e.g. `<project>/ideas/`): `ABSTRACTION.md` (first-principles map: layers, analogous
  fields, open problems, premises worth doubting), `FUNNEL.md` (project settings: domain, must-read files,
  what is already being worked, budgets, where to run), `cards/I-YYYYMMDD-NN.md` (one card per idea, the only source of
  truth), `BOARD.md` (generated, never hand-edited), `runs.md` (one line per round, plus dropped drafts).
- Helper: `python3 <this skill>/scripts/funnel.py init|new|board|import <funnel folder>` (no dependencies). `new` reserves
  the next id and writes the card template (`--parent` for a child); `board` validates every card and regenerates
  `BOARD.md`; `import` copies cards produced elsewhere (e.g. a cloud run) without overwriting Eric's marks. Run `board`
  after every screening; fix any card it rejects.
- Native CLI helpers (lightweight, zero new state stores):
  - Fast zero-dependency IEEE / journal search (~2–3 s, Python 3 stdlib only, works locally and in cloud `.sync/idea-funnel/`): `python3 <this skill>/scripts/search_papers.py --query "<operator / subproblem>" --start-year 2022 --end-year 2026 --max-papers 10 --sources open_alex crossref` (append `arxiv` when preprint recall is needed).
  - Clean PDF full-text extraction to scratch cache: `CLAUDE_PROJECT_DIR="$HOME/.cache/idea-funnel/pdf_cache" bash ~/.codex/skills/scoop-check/scripts/fetch_paper.sh "<PDF_URL>" "<slug>"` (cloud fallback: `pypdf` / `pdftotext` into scratch).
  - Targeted constructive evolution (`openevolve 0.4.1` over subscription CLIs, zero API keys): `~/.local/share/uv/tools/openevolve/bin/python <this skill>/scripts/evolve_cli.py <initial.py> <eval.py> -i 10 -o <cache_dir> --backend agy|codex|claude` — **mandatory before L2** whenever a card claims a discrete algebraic sequence, switching schedule or degree profile beats heuristics (optimize the **exact target objective** such as $\operatorname{Tr}((\mathbf{A}^H\mathbf{A})^{-1})$ or $\sigma_{\min}$ without artificial column-weight/variance locks; never use for blind topic hunting).
- Card template: [templates/card.md](templates/card.md). Write the 白话 and 去壳 sections in plain Chinese a smart
  non-specialist can follow; technical names, citations and identifiers stay exact.

## Layers (each has a cost cap; never exceed it)

| Layer | What | Cap per idea | Who decides |
|---|---|---|---|
| L1 深想 | One idea thought through with full effort: derivation + ≤30 s NumPy sanity probe, closest works, 去壳, cheapest decisive check | full effort, about an hour of agent time | AI: write the card or drop the draft |
| 查新初筛 | Cross-family novelty (by math form) + intrinsic-value vs prior-art screen before L2 | one batched call per screening | other-family reviewer: (1) to L2 / (2) kill or park / (3) gap child |
| L2 便宜证据 | One decisive cheap check on novelty survivors (oracle upper-bound first when constructible) | about 30 minutes agent time, ≤1 CPU core-hour (unless `FUNNEL.md` overrides) | AI: kill / candidate / park |
| 放行 | Cross-model gate auditing L2 evidence, baselines and discipline | one batched call per screening | other-family reviewer: pass / kill / revise |
| L3 值得长仿真 | Ready for Eric: worth a long simulation | Eric | Eric: 继续 / 停 / 改 |
| L4 正式研究 | A Trellis task with a frozen protocol (outside the funnel) | per task | Eric |

Authority: AI may kill at any layer. Promotion to L3 needs a pass from a reviewer of a different model family than the
generator (same-family generation is fine, same-family acquittal is not; adopted from ARIS `idea-creator`). Only Eric's
继续 promotes past L3. Eric can revive any card by writing in its `eric:` field. Anything whose next check costs more
than the next layer's cap is parked with the check and its cost written down; it is never run inside the funnel. (L0 is
the older quick-batch mode; cards from it are screened like L1 cards.)

## A round

Before starting, read [METHODS.md](METHODS.md) (a toolbox of ways to generate ideas, with sources), `FUNNEL.md`,
every existing card (killed ones included, so nothing is proposed twice) and the must-read files it lists. Then, before
opening the project's `ABSTRACTION.md`, write your own first-principles decomposition of the project (METHODS §F: what
the code names do physically and mathematically, the layers, what is scarce or limiting at each, the abstract problem
class, which other fields share it, which premises look doubtful) into `ideas/abstractions/<runner>-<date>.md`. Only
then read `ABSTRACTION.md`, which is one earlier author's reference map, not a starting point, and append to your file
where you disagree with it and why; the next reflection may revise the map from these notes. One generator per round
(e.g. one external generator) never reads the map at all. State the budget and the rough track mix you aim for.

The round ends on the first of: (1) `target_ready` mutually distinct cards (default 10) at L3 — children of one root
count once unless the gate judged them distinct problems (IDEAgent's "yield") — or, for a runner that cannot run the
gate, `cloud_target` new gate candidates produced in this round (default 15; candidates left over from earlier rounds do
not count); (2) the time budget in `FUNNEL.md` is spent (hours; time, not idea
count, is the budget); (3) pivots are exhausted: `max_pivots` pivots (default 4) have each been followed by
`stall_limit` deep ideas (default 8) without a new L2 candidate, and at least `min_hours` (default 4) of work have
passed; (4) the safety valve `max_deep_ideas` (default 60 audited deep ideas) is reached. A stall alone is never a
reason to stop; it is a reason to pivot (below). Then stop and report. Ending a round is not a verdict on the field:
before reporting that a battlefield is mined out, check which ledgers and layers the round's drafts actually covered,
and calibrate the gates once against 15–20 recent target-venue papers (which gate would each have died at; AFDM
2026-11-24: 0/20 survived, half on taste bans, and pure receiver work was 1 of 12 TWC/TCOM/JSAC papers). Only if both
point to exhaustion, say that this battlefield — not the field — is exhausted. (First AFDM cloud round with an idea-count
budget, 2026-11-21: 40 "deep ideas" in 16 minutes, about 24 seconds each; a count budget rewards shallow ideas.)

Depth floor: a deep idea counts toward any budget or stall only if its card passes the depth audit at screening —
it contains a derivation or estimate with this project's numbers (formula and substitution), at least three closest
works that were actually opened (with links or identifiers) and how each differs, and a named cheapest decisive check.
A card that fails is sent back to L1 for the missing part, not counted.

Run without pausing: a round is meant to run for hours. Do not stop to report, summarise or ask for confirmation; after
each screening start the next cycle at once. Commit after every screening (a cloud runner also pushes) so the work
survives an interrupted session.

Out-of-quota calls never stop a round (Eric 2026-11-21). An external model is unavailable when its call errors with
credits, quota, usage limit, rate limit or login, or returns nothing with a non-zero exit. Then skip that call: for a
review, set each affected card's `next_cost` to `未审核（<step>：<model> 无额度）`; for a generator slot, give the slot
to another family or think the idea yourself. Add the item to a `待审` list in the round's `runs.md` line (card, step,
model, prompt file) so Eric can rerun it after switching accounts, and retry once at the next screening. Only the main
runner's own quota ends a round. Fallback for steps 7–8: at most two fresh-context reviews per screening, batched, by a
model of the runner's or the generator's own family (e.g. agy Neon), recorded as `兜底评审（同家族）`. A fallback review
may KILL or REVISE; its PASS does not promote: the card stays at L2 with `next_cost: 未审核（跨家族放行）` until a
cross-family reviewer passes it.

Tracks, so the round does not circle inside one pit (rough targets for the round's mix, not quotas to fill;
`FUNNEL.md` may override; every card sets `track:`):
- **core** (about 50%): this project's own problems.
- **adjacent** (about 25%): the same abstract problem class in another system or waveform (`ABSTRACTION.md` §3).
- **explore** (about 15%): outside the project but within the owner's reach (for Eric: physical-layer signal processing,
  estimation, coding); judged by its value as a standalone Transactions paper.
- **pit** (at most about 10%): questions the premises of the problem itself (`ABSTRACTION.md` §5: the channel model,
  the problem setting, whether the claimed bottleneck is real): if the pit is bad, this is how the funnel finds out.
  Auditing the manuscript (claims stronger than evidence, unfair comparison tables, attribution sentences) is paper
  self-review, not an idea: hand it to a paper-audit task, not a card. The reflection rule "do more of what produced
  survivors" never raises the pit share, because premise checks pass review more easily than new ideas. A pit L3 does
  not count toward `target_ready` or any idea tally. A pit card gets no free pass at step 6: no paper can contain our
  own code, so its novelty question is instead "does the field already treat this premise as a known convention or
  known caveat?" (for example per-frame channel normalisation, or fixed-gain detectors in benchmarks); if yes, KILL. It
  must also name, before any check, which design decision or direction (not a sentence in the paper) flips if the
  premise is wrong, with a pre-registered size threshold; a premise that changes only wording or a headline's size
  is a paper-audit note, not a card.
One idea in five is a wildcard: the generator chooses its own method, anchor and track (within the tracks and ledgers
left open by `FUNNEL.md`, never reopening closed ones or banned topics).

Value ledgers (Eric 2026-11-23; replaces "net dB headroom" as the only entry ticket). A Transactions-level idea crosses a
clear step on at least one ledger; dB is one ledger, not the target. `FUNNEL.md` says which ledgers are open and their
mix. Every card names its ledger in the first 筛选记录 line (`账本：…`), and its PREDICTIONS file tests that ledger's
threshold. The thresholds below are the only place these numbers live:
- **Compute** (exact structure, e.g. Thaj–Viterbo TWC 2020): accuracy within 0.2 dB (or 0.02 bit/sym MI) of the
  **fastest published algorithm of the same accuracy** (never a naive matrix inversion or a strawman), and either a lower
  complexity order or ≥10× measured speed-up on the same machine, language and thread count. Truncating iterations or
  dropping terms does not count. When either side runs on a GPU, the rival is batched and vectorised on the same device,
  and per-frame multiply-accumulate counts are reported next to wall time.
- **Floor-breaking** (e.g. Nazer–Gastpar TIT 2011): in a setting where the strongest existing combination sits on an
  error floor (FER stays ≥ 1e-2 across ≥5 dB of SNR) or loses lock, remove the floor (FER one decade lower at the same
  SNR) or win ≥1.0 dB, with no added pilot, guard or preamble overhead.
- **Cross-layer inversion** (e.g. ten Brink TCOM 2004, `21-l02`): a component that is better when tested alone loses
  ≥0.5 dB inside the closed loop, and the loop-matched design beats the best standalone-optimal combination by ≥0.8 dB
  (≥0.05 bit/sym MI for coupled cards).
- **Overhead / hardware / prior** (e.g. Alamouti JSAC 1998): at equal FER (within 0.2 dB), remove ≥15% of pilot, guard
  or prefix overhead; or run on cheaper hardware (fewer ADC bits, saturated PA) within 0.5 dB; or drop an unrealistic
  prior (known path count, known noise variance, known Doppler spread) within 0.5 dB of the receiver given that prior,
  where the strongest existing prior-free method loses ≥1 dB.
- **Boundary law / tight bound** (e.g. Hassibi–Hochwald TIT 2003): either a closed-form criterion with zero fitted
  parameters, pre-registered and then tested on parameter points not used to derive it (the predicted flip lands within
  20% (or 1 dB) and the two sides differ by ≥1 dB in total swing), or a bound that tightens the best known one by ≥30%
  (or ≥1 dB). Anti-fake locks (Eric 2026-11-24): the final formula or criterion matches Monte Carlo at ≥3 finite,
  realistic settings (several paths, fractional dispersion) within 0.5 dB, flip point within 20% — asymptotic or
  single-path derivations may be steps, but a result that holds only there is not a card; a claimed lower bound is not
  crossed by any of ≥2 legal estimators or detectors tested, and a small-scale numerical optimum (exhaustive or
  high-precision search) comes within 1.5 dB of it.
- **Performance**: ≥0.8 dB over the strongest matched-harness baseline (≥1.0 dB for neural/unfolding cards; ≥0.05 bit/sym
  MI for soft-output loops; or domain-specific high-SNR slope / multi-objective trade-off bars explicitly defined in `FUNNEL.md`).

Neural attribution (black-box and end-to-end networks, Eric 2026-11-24): pre-register three arms. (1) A genie-channel
ceiling (classical near-optimal detection given the true channel) sizes the pool — the unknown channel or mismatch must
leave ≥0.8 dB — and is never a bar the network must beat. (2) The strongest classical pipeline (best closed-form
estimator plus best detector) is the rival the network must beat by its ledger threshold. (3) A same-size modular neural
arm (e.g. a small network for channel estimation feeding the classical detector); if it captures ≥80% of the gain, the
claim narrows to that module and is re-validated once on fresh seeds before any Step-8 review. One set of weights must
keep its advantage over a continuous SNR range, random Doppler spreads and at least one power-delay profile or mismatch
level not seen in training. Physics-driven unfolding cards keep the channel-MSE-supervised ablation instead.

Public-pain check (all ledgers): the obstacle must appear in published settings (≥2 independent groups by default, or
grounded in published failure figures / complexity tables / explicit open models under the cited paper's own parameters
when specified in `FUNNEL.md`; cite paper and section or figure). A problem that exists only inside this project's receiver, its private interface
constants or its own simulator setup is not a card, however clean it looks.

Each cycle:

1. **Inspiration / deep read** (about 10 minutes): if the funnel folder has a domain landscape map (e.g.
   `AFDM_LANDSCAPE.md`, used as a reference map, never an exclusive whitelist), consult it and read 1–2 core papers on
   the target subproblem in full (plus an occasional far-field paper from `ABSTRACTION.md` §3) rather than shallowly
   skimming random preprints; otherwise skim 3–5 recent papers from `ABSTRACTION.md` §3. Note in `runs.md` where a
   direct port stalls, the sparks and which open problem (§4) each bears on (METHODS M1). This is reading for ideas, not
   checking novelty.
2. **Think one idea through (L1).** Pick track, anchor and lens; use any method from METHODS that helps, or your own,
   and write `方法：<id 或 自己的>` in the first 筛选记录 line. Name the layer the idea attacks and its abstract problem
   class from your own decomposition, and look at how other fields with the same class handle it (G12). Then work it like a research conversation, not a list item: state the
   problem precisely; derive the key relation or an estimate with this project's numbers (formula and substitution), and
   verify degrees of freedom, dimensionless effect size and the simplest sane baseline across 2–3 valid operating points
   (not a single greenhouse point, nor artificial 5× extremes) with a ≤30 s read-only `/opt/anaconda3/bin/python -c`
   NumPy probe (import project transforms when applicable; never guess closed-form gains by eye, and write no project
   files). Align the probe metric with the mechanism so short probes do not false-kill coupled ideas: use mutual
   information (MI/GMI, e.g. ≥0.05 bit/sym) or EXIT threshold rather than raw uncoded MSE for soft-output/coding loops,
   and bound-tightening (≥1 dB) or a closed-form regime-flip boundary for bound/diagnostic cards (plus any domain-specific
   evaluation regime explicitly enabled in `FUNNEL.md`).
   When an analogous method already exists in another system/basis, include a `naive_port` arm (direct basis/operator
   substitution without target-specific structural redesign, equipped with matched outer harness and textbook zero-order
   calibrations) in the probe; run a cross-architecture replacement check **only** when the draft claims the target
   architecture outperforms that alternative (never kill an in-architecture design merely because switching to another
   system architecture in a simplified regime would sidestep the obstacle, provided the card states why the target
   architecture is used);
   search the 3–5 closest works (`python3 <this skill>/scripts/search_papers.py --sources open_alex crossref`, `fetch_paper.sh`,
   `scoop-check`, `literature-search`, `comm-lit-review` or plain web search) by abstract mathematical form as well as domain terms and
   say how each differs; write the three 去壳 sentences — if the method couples two known modules `A ⇄ B` to break an
   interface deadlock where unmodified cascade `A → B` fails, sentence 3 must state that interface deadlock and why both
   `A-only` and `B-only` fail (equip baselines with matched outer loops/budgets and textbook calibrations, while keeping
   core baseline modules to published methods or unmodified cascades `A → B` rather than newly invented cross-paper `A ⇄ B`
   hybrids) — and name the cheapest check that could kill it; set
   `value` (3 = would change a design decision across a subfield, 2 = changes one system's design or a standard
   parameter, 1 = incremental) and `next_cost`. **Drop immediately without creating a card** if the probe shows that the
   draft cannot reach any open ledger's threshold (above) against the strongest existing combination, if it fails the
   public-pain check, or if a single-component ablation (including the channel-MSE-supervised ablation on physics-driven
   unfolding) already captures ≥80% of the gain — except for black-box/end-to-end networks, where if arm 3 of the neural
   attribution rule captures ≥80% of the gain *and* itself clears an open ledger against the strongest classical pipeline,
   narrow the draft and create the card for that modular neural component instead of the end-to-end wrapper (drop if the
   narrowed module fails the ledger, public-pain or prior-art check). Keep the card
   `title` ≤26 Chinese characters (≤32 total characters) in plain signal-processing words ("setting + change + problem", at most two technical modifiers;
   enforced by both `funnel.py new` and `funnel.py board`). Before dropping a draft, name its smallest plausible repair (G15), and if
   it failed due to a hard structural obstruction (unitary equivalence, rank ceiling, protocol mismatch), check in one
   minute whether that obstruction itself tightens a known bound by ≥1 dB or flips a published design rule (**converse /
   diagnostic rescue**, CCF `frontier-ideation`). Only then
   create the card (`layer: L1`, `generator:` the model that did the thinking, `track:`). If it still dies (already
   solved, already being worked per `FUNNEL.md`, on a killed list, or a 去壳 sentence cannot be written plainly), add the
   title and reason to `runs.md` as a dropped draft.
3. **Learn from every death — log and commit immediately.** For every dropped probe/draft or killed card, append one lesson
   line to `runs.md` (`runs-g.md` on `g`) **in the same cycle** (never accumulate silent probe failures in scratch cache for
   hours) and `git commit` at the end of each cycle. Every **6 consecutive dropped probe directions** without a surviving L1
   card count as 1 stall unit toward `stall_limit` (triggering a mandatory Pivot diagnosis when `stall_limit` is reached).
4. **Grow the tree (gap-driven only, no child quota).** Write a child (`funnel.py new --parent <id>`) only when a
   card's review (step 6 or step 8) or L2 check explicitly names an open gap whose resolution would change a design
   decision. Never spawn children to fill a percentage quota (natural generalisations of a parent theorem and extra
   control arms belong as an added line in the parent's 筛选记录, not as new cards). A child states its one decisive
   change from the parent in its first 筛选记录 line (attack the named objection, remove a blocking hidden cost, or
   bring a non-trivial structure from another field). Whenever one idea builds on another, record it as `parent:`. Kill
   a parent when a child subsumes it. A child that only varies a parameter is allowed only when the parent's claim
   predicts a threshold or reversal across it (written before running), and at most two in a row on one branch (Eric
   2026-11-21 / 11-22).
5. **Screen together and reflect** every `screen_every` new cards (default `3` when pre-card gates are active) **or every
   2 hours elapsed since the last screening, whichever comes first** (whenever ≥1 unscreened L1 card exists, plus once
   60–90 minutes before the round's time cap so surviving L1 cards never starve before L2). Rank all active L1 cards by pairwise
   comparison ("which of these two is more worth a long simulation, and why"), once by the runner and once in one
   batched call by a judge from a family other than most of the cards' generators; where the two rankings disagree
   strongly, keep both cards (the best LLM judges match expert pairwise preference only about 73% of the time, worst on
   feasibility: Ideation Arena, EMNLP 2026). Run the depth audit (above) and send failing cards back. Kill
   duplicates and dominated cards; pick at most `l2_per_screen` (default 3) top cards, keeping variety, to enter step 6
   (cross-family novelty & importance pre-screen); spawn children only on parents with a concrete named gap (step 4).
   Then write a reflection line in `runs.md`: death reasons counted; draft counts across `ABSTRACTION.md` layers/open
   problems and open ledgers, and which produced survivors (if ≥60% of drafts sit in one layer while other open layers are
   at zero, the next cycles or pivot move to an untouched open layer first); whether a failure pattern from METHODS §X is
   showing; and an explicit decision for the next cycles (track, method, layer or field). Act on it.
6. **Novelty and why-unsolved pre-screen (before L2 simulation)**, batched per reviewer family for the candidates picked
   at step 5 (by a model of another family than the generator; Claude/GPT cards → Gemini 4 Neon; Gemini cards → GPT-6.2
   Sol or Claude so Astra quota is saved for step 8): search ≥5 closest works across fields by **abstract mathematical
   operator/structure**, not scenario keywords; score **intrinsic importance** ("if nobody had done this before, would
   it merit a strong Transactions paper?") separately from **prior-art occupancy** (a high-intrinsic-value card killed
   by prior art is noted as a positive taste reference and its diagnostic numbers harvested, without running L2);
   restate the claim in plain words with one everyday analogy, calling out common practice disguised in jargon; check the
   **public-pain** condition (≥2 independent groups' published settings show the obstacle; a problem private to this
   project's receiver is killed here) and name the card's **ledger** and whether its threshold is reachable; then:
   - If the abstract operator is **unoccupied**, decide why — **(1a)** nobody noticed, **(2)** noticed but unimportant in
     real systems (e.g. default protocol parameters or a 5-minute 1D parameter sweep already avoid it), or **(3)** noticed
     but blocked or carrying a hidden system cost — with evidence and real-system effect size.
   - If the operator **has prior art in another regime/architecture** **but not in the target setting**, do not kill by
     abstract operator name alone: apply the **Target-Structure Coupling & `naive_port` Test**. Classify as **(1b)
     structural adaptation** when direct basis/operator substitution (`naive_port`, equipped with matched outer harness and
     textbook zero-order calibration) or unmodified module cascade (`A → B`) breaks down due to target-specific structural
     coupling (losing ≥0.8 dB / ≥0.05 bit/sym MI, suffering a complexity-order blow-up, or flipping a design ranking) and
     the redesigned method clears an open ledger (including domain-specific ledgers enabled by `FUNNEL.md`); classify as
     **(2) trivial port ("硬套 / 纯改符号")** if direct substitution works at matched accuracy and complexity order without
     structural redesign.
   - **Anti-false-kill symmetry**: when a card provides executed `naive_port` / MI / complexity numbers, the reviewer may
     NOT kill it before L2 with a hand-waving "adapting from X looks straightforward"; to kill at step 6, the reviewer
     must either cite prior art that already solved the same obstacle in an isomorphic setting or name the concrete
     standard outer/calibration component omitted from `naive_port` (when uncertain, advance to step 7 L2).
   Only **(1a)** and **(1b)** (collectively `(1)`) advance to step 7 (L2 simulation); **(2)** is killed or parked
   immediately (saving L2 compute; in AFDM round 3, 12 of 27 kills died at novelty after an hour of L2 work); **(3)**
   becomes a gap child only if net headroom remains clear. Template: `prompts/novelty-importance.md`.
7. **L2 cheap evidence** on step-6 survivors, within the cap (`FUNNEL.md` may override CPU/GPU caps, e.g. ≤15 min
   lightweight training on `deinlab` for model-driven neural/unfolding cards): **run an oracle (white-box truth) upper-
   bound check first whenever constructible** — if gifting exact auxiliary truth still fails to beat the cost or the
   simplest sane baseline under same total energy/duration, kill at once without patching (re-verify only when strict
   theory strongly contradicts the data, indicating an implementation bug; Eric 2026-11-22). Otherwise run a readout of
   existing data, an estimate/bound, or a small simulation. For a gate candidate, have another family re-derive its key
   number independently. A runner without the project's simulation environment parks the card with `next_cost:
   需本地仿真：<what, estimated cost>`.
   A simulation check follows four rules (first blind cross-family review, 2026-11-21, sent every simulated card back for
   breaking one of them): write the decision rule and any threshold before running; never pick a threshold on the same
   frames you report (hold frames out, or confirm on fresh frames); compare against the reference that matches the
   claim's setting (e.g. a true-delay claim against the true-delay arm); for a "these cases benefit" claim, run the
   alternative action on the same cases to rule out "they were easy anyway". Report counts with an interval when the
   sample is small.
   Result: kill, park with the heavier check and its cost, or gate candidate.
   - **Two-tier pre-registration (`PREDICTIONS_*.md`) — four iron rules**:
     1. *Starting-line & known-channel attribution*: cross-waveform cards MUST include and inspect **first** both a **known-channel (`True-H`) arm** (if tied, scope claim strictly to channel estimation, never data detection/erasure) and an **unimpaired (`clean` / `C=0`) blind arm**; subtract any unimpaired baseline gap via Difference-in-Differences **`DiD = (err_base - err_new)|_impaired - (err_base - err_new)|_clean >= margin`** (and bound clean false-alarm loss against the unmodified same-waveform receiver — never use two-sided `|clean_diff| <= c` bombs nor blind one-sided passes that hide baseline offsets).
     2. *Dev-calibrated thresholds, never below the card's ledger*: measure physical ceilings/floors and per-dB error slopes (and, for compute cards, same-machine runtimes of the fastest same-accuracy rival) on dev/smoke seeds before freezing constants (never guess `+2.0 dB` under a `-23.5 dB` perturbation ceiling); the primary threshold is at least the card's ledger threshold (Value ledgers above) — never water it down.
     3. *Explicit hypothesis & broken-baseline hygiene*: every `PASS_PRIMARY` clause (≤2 clauses) states *which hypothesis it tests* and *what failing it means*, separating rival baselines (`New - Rival >= margin`) from positive instances of a sufficiency law (any failing instance refutes the law); secondary slices go into `SCOPE_READOUTS`; remove or fix broken baselines (`NMSE > 0 dB` or `FER > 50%` on unimpaired data).
     4. *`PASS_PRIMARY == false` never enters Step 8*: when `verdicts.PASS_PRIMARY` in `summary*.json` is `false`, the runner MUST set `status: killed` or `status: parked` (enforced by `funnel.py board` inspecting `summary*.json`, and verified directly in `summary*.json` at Step 8 merge) — never narrow the title on the same seeds and mark `cross-model review` (salvaging a real sub-effect that still meets the card's ledger threshold requires a fresh pre-registration on unseen seeds `+10000`, at most once).
   - **Pre-run static script & Steelman baseline audit (≤3 min, before any >2 min `deinlab` / M4 Pro run)**: pass the smoke-tested L2
     script and `PREDICTIONS_*.md` to a cross-family read-only reviewer (`gpt-6.2-sol`, `Claude Opus`, or `agy Neon`) checking five items:
     (i) **Matched-harness published & naive-cascade baselines present** — does the script include the strongest **published** baseline in the target setting and the unmodified `naive_port` / `A → B` cascade, all equipped with **matched outer harness, iteration/retry budget, and textbook zero-order calibrations** (never an unpublished cross-paper `A ⇄ B` interface hybrid newly invented by the runner or reviewer; single-pass/uncoded claims use single-pass/uncoded baselines), plus single-stage / coarse-stride checks on multi-stage speed claims and equal-net-throughput baselines on overhead-saving claims? Add missing ones before running;
     (ii) no broken strawman baselines (`clean` `NMSE > 0 dB` or `FER > 50%`);
     (iii) zero side-information leaks (`sigma2`, noise-type labels, true bit-error handoff gating, reading true tx symbols);
     (iv) RNG stream alignment across switches and **true two-block linear convolution** (never single-block circular wrap-around) whenever path delays exceed the cyclic/chirp prefix; and
     (v) sign/energy normalization invariants — **verify any claimed sign or formula bug on a 5-line numerical toy vector before changing code** (round 5 `g02`: existing subtraction left `6.34e-18` bias vs `0.095` flipped).
8. **Cross-model gate** (two-beat `kill-argument` protocol), one batched call per reviewer family for step-7 survivors: send each card and its L2 scripts/
   numbers to a reviewer of a family different from its `generator` (Claude and Gemini cards → `codex exec --sandbox read-only -m
   gpt-6.2-astra` if the card is not `pit` (it would reach L3 and the owner), `gpt-6.2-sol` if it is `pit`, the two
   standing in for each other, then Claude (not for Claude cards) or Neon; GPT cards → Gemini 4 Neon via agy). For every
   non-`pit` candidate, require two explicit beats in the same review: **Beat 1 — ≤200-word Hostile Rejection Memo** (the
   sharpest reviewer-2 kill case attacking novelty, unrun cheap baselines, and attribution leaks) followed by **Beat 2 —
   Code & Executed-Data Audit** (checking source lines, RNG pairing, numerical invariants, and the four simulation rules
   without inventing unexecuted numbers), ending in `VERDICT: PASS / KILL / REVISE`. Cards finishing mid-cycle wait for the next screening batch. Record reviewer, model and verdict in the
   card. PASS → L3 (a `pit` premise check reports a one-line boundary note to Eric rather than masquerading as a new
   algorithm idea, and is not counted as an idea L3); KILL → killed; REVISE → gap child or back to L2. With no second family available, follow the out-of-
   quota rule above. (If a card's L2 was already pure arithmetic completed before step 6, steps 6 and 8 may merge into
   one call.)
9. Run `board`; append progress to the round's line in `runs.md`; commit; continue.

**Pivot** when `stall_limit` deep ideas in a row produce no new L2 candidate. Do not stop. Write a pivot note in
`runs.md`: diagnose the stall with METHODS §X (crowded neighbourhood, circling, self-made problem), then make one change
bigger than switching lenses: move up or down an abstraction layer (your decomposition, or `ABSTRACTION.md` §2); go to an analogous field (yours or §3)
and bring back how it solves the problem; switch track (adjacent, explore, pit); take an open problem from §4 not touched
this round; harvest anchors from the limitations sections of 10–20 recent papers; or revisit killed cards for a clearly
different angle (a new child, not a revival). Reset the stall count and count the pivot. If a pivot teaches something
about the project's structure, revise `ABSTRACTION.md` and say so in the pivot note.

Context and subagents. Long rounds outgrow any context window, so the harness will compact; recall also degrades in very
long contexts, and ideas written next to all earlier ideas drift toward them. Two rules:
- **Memory lives in files.** After a compaction or restart, do not continue from a vague memory: re-read `FUNNEL.md`,
  `BOARD.md` and the last reflection, pivot and lesson lines in `runs.md`, then go on.
- **Fresh-context workers only when they pay.** By default the runner thinks its own ideas in its own context (cheaper:
  it reuses the prompt cache). Hand one idea to a fresh worker only when one of these holds: the runner has thought eight
  or more ideas in its current context; the last reflection flagged circling or a crowded neighbourhood; or the idea is
  a pivot into a new field where fresh eyes matter. Hand literature reading to a cheap worker when a check needs more
  than three papers read. Caps per round (`FUNNEL.md`): `max_idea_workers` (default 10) and `max_lit_workers`
  (default 10); never nest workers; at most two running at once. Stop-loss: if the first four worker ideas of a round
  all die at L1 or are dropped, stop using idea workers for the rest of the round. Give workers a short brief with a
  fixed opening (so repeated briefs share a cached prefix) and the variable assignment last. Log every worker use in
  `runs.md` (profile, purpose, outcome) so the next round can judge whether they paid.

External models: criticism & Steelman baselines, not stateless one-shot idea generation. Across AFDM rounds 5–6, stateless
single-turn external generation went `0/23` (`0/20` blind in round 5 + `0/3` gap-seeded in round 6: `Astra` and `Opus` all
`DROPPED`), because a single-turn call cannot iteratively pivot after hitting a strong baseline, yet proved lethal at
assembling strongest prior-art combinations (`Zhidkov + Nassar EM`, `0.75` Rician weighting, unconstrained bit-flip
hill-climbing). Therefore:
- **Scarce external models (`GPT-6.2 Astra / Sol`, `Claude Opus`) do NOT run stateless one-shot idea generation.** Spend their
  quota strictly on: (a) per-draft zero-jargon prior-art checks (`Sol`, ≤10/round on a Gemini runner), (b) Step 6 novelty &
  importance pre-screens, (c) Step 7 pre-L2 **Steelman `naive_port` baseline construction + static code audit**, and (d) Step 8
  final gates.
- **Cross-family diversity comes from isolated parallel runners (`l` Claude + `g` Gemini)**, or, when a non-Gemini runner runs
  solo without `g`, one optional sandboxed `agy` Gemini Neon/Carbon slot (`~/.local/bin/agy -p "<prompt>" --model gemini-4-neon-high --sandbox --add-dir <skill dir> --output-format json --print-timeout 0`, resuming via `--conversation <id>` if needed).
  When `l` and `g` run in parallel, disable `l`'s background `agy` generator and skip mid-round cross-imports so each family
  explores independently without context pollution or diversity collapse ("Diversity Collapse in Multi-Agent LLM Systems",
  arXiv 2604.18005); merge and inspect `summary*.json` `verdicts.PASS_PRIMARY` at round end.

Model roles (defaults; `FUNNEL.md` may override). Use each model where it is strong, and keep every verdict in a family
other than the card's generator:

| Step | Default | Why |
|---|---|---|
| Main runner `l`: choosing problems, cross-layer & closed-form framing, Step 8 gate | Claude (`Devin` Fable 5.2 Fusion high) | sets direction and tone; owns `BOARD.md` |
| Parallel runner `g` (or solo `l`'s external slot): cross-domain analogies, physics-driven unfolding | Gemini 4 Carbon / Neon high (`agy`) | broadest world knowledge, fast NumPy/PyTorch probes |
| Pre-card zero-jargon prior-art gate (on `g` drafts) | GPT-6.2 Sol high (≤10/round, then Claude Opus) | per-draft check before card creation |
| Step 6 pre-L2 novelty + intrinsic-value screen | Claude / GPT cards → Gemini 4 Neon high; Gemini cards → GPT-6.2 Sol high (or Claude Opus) | catches prior art and unconstrained-climb baselines before L2; saves Astra for step 8 |
| Step 7 pre-L2 Steelman baseline & static code audit | GPT-6.2 Sol high (or Claude Opus); `agy` Neon on GPT cards | adds missing strongest prior-art combo, blocks broken baselines & leaks |
| Step 7 L2 small code runs | the runner, or GPT-6.2 Sol | cheap execution |
| Pairwise ranking pass (volume) | Gemini 4 Hydrogen high; GPT-6.2 Sol when most cards are Gemini's | cheap; the ranking is advisory (judges match experts about 73%) |
| Step 8 post-L2 gate | Claude and Gemini cards → GPT-6.2 Astra high if not `pit`, GPT-6.2 Sol high if `pit` (each other's fallback, then Claude for non-Claude cards, then Neon); GPT cards → Gemini 4 Neon high; unknown family → the same GPT choice plus Neon | cross-family audit of L2 scripts, baselines and attribution; Astra only where a card may reach the owner |
| 白话与类比 on L3 cards (the ones Eric reads) | Gemini 4 Hydrogen high | plain language is a Gemini strength and Hydrogen is cheaper |

Reasoning effort: high by default; xhigh only for a judgement-heavy call that could swing the round.

Anchors (every card needs at least one, with its source): **A** a limitation or open gap triangulated across ≥2 recent
papers — or 1 recent paper plus an executed ≥0.8 dB probe — found with a search tool in this round, never from memory or
a single throwaway "future work" line alone (CCF `literature-grounded-evolution`); **B** a number and file path from this
project's results (an anomaly, a genie or ceiling gap); **C** an assumption most papers make plus evidence of the real
condition (standard, measurement, hardware); **D** two works or communities holding halves of an answer that do not cite
each other. At most three cards per anchor; cover at least three anchor types per round.

Lenses: ARIS's five structural-gap lenses — method-transfer (works in A, untried in B), contradiction, untested
assumption, scaling regime, diagnostic (a question nobody asked) — plus the toy-setting lens: where the problem is easy,
which one ingredient makes it easy, and what could replace that ingredient in the real setting. Optional: the patterns
in `~/.claude/skills/idea-spark/references/ideation-patterns/` when installed.

## Eric's marks and after

He writes in `eric:` one of `继续`, `停`, `改：<what>`. On the next session, apply the marks: 停 → `status: killed`
(reason: Eric); 改 → child card or back to L2; 继续 → `status: promoted`, then (optionally tightening the method and
ablation matrix via `research-refine` / `experiment-plan`) propose a Trellis task (ask before creating
it, following the project's own rules) and write the task link in the card.

## Where it runs

- **One agent, locally**: any tool with file access runs a whole round in the project folder.
- **Several runners at once** (e.g. local and cloud): each runner uses its own `--runner` letter for new cards and works
  only its share of anchors and lenses as `FUNNEL.md` assigns; it edits only cards carrying its own letter, plus any
  older cards `FUNNEL.md` hands to it. After an import, the next joint screening compares all runners' cards and merges
  duplicates. Prefer a different model family per runner: generators fail differently and the union keeps one model's
  taste from capping the pool (ARIS `idea-creator` Phase 2 brainstorms with two external models for this reason); the
  gate then sends each card to a family other than the one that generated it.
- **Cloud and local together** (when `FUNNEL.md` sets `cloud_repo`): a cloud agent (e.g. Devin Cloud) clones that repo,
  reads this protocol from the copy the sync puts at `.sync/idea-funnel/`, runs steps 1–4 and 6 on its own machine
  (L2 small runs on its CPU with the project code), commits only files under the funnel folder to the branch
  `funnel/<round-id>` and pushes; it never edits other files and never pushes elsewhere. It leaves gate candidates at L2
  with `next_cost: cross-model review`. The local side imports the branch with
  `scripts/import_branch.sh <bare repo> <branch> <local funnel folder>`, runs the gate (step 5), runs anything that needs
  machines only reachable locally, applies Eric's marks and handles promotion. The repo must be refreshed from the
  local state at the start of each round, under whatever sync rule the project sets.

## Phrases and reporting

Phrases Eric may use in any tool: "idea funnel 跑一轮" (run a round), "看板" (run `board` and summarise), "我看完了"
(apply marks), "导入云端结果" (import a cloud branch). Report in plain Chinese: ideas thought through, dropped drafts and
kills grouped by reason, cards at L3 with one line each, parked cards with the heavier check and its cost, budget used.
Never present a card as validated beyond its layer. Tools without file access (web chat): paste this file, `FUNNEL.md`
and `BOARD.md`; ask for complete cards in the template format; save them into `cards/` and run `board` locally.
