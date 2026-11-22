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
reason to stop; it is a reason to pivot (below). Then stop and report. (First AFDM cloud round with an idea-count
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
One idea in five is a wildcard: the generator chooses its own method, anchor and track.

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
   and bound-tightening (≥1 dB) or a closed-form regime-flip boundary for bound/diagnostic cards. When an analogous
   method already exists in another waveform/system, include a `naive_port` arm (direct basis/model substitution) in the
   probe; when claiming a waveform-unique structural advantage, run a matched-parameter reference waveform (e.g. OFDM/OTFS)
   and drop only if both accuracy (including tail/MI) and complexity order are identical (unitary equivalence);
   search the 3–5 closest works (`scoop-check`, `paper-search`, `literature-search`, `comm-lit-review` or plain web
   search) by abstract mathematical form as well as domain terms and say how each differs; write the three 去壳 sentences; name the cheapest check that could kill it; set
   `value` (3 = would change a design decision across a subfield, 2 = changes one system's design or a standard
   parameter, 1 = incremental) and `next_cost`. Before dropping it, name its smallest plausible repair (G15). Only then
   create the card (`layer: L1`, `generator:` the model that did the thinking, `track:`). If it still dies (already
   solved, already being worked per `FUNNEL.md`, on a killed list, or a 去壳 sentence cannot be written plainly), add the
   title and reason to `runs.md` as a dropped draft.
3. **Learn from every death.** For each dropped draft or killed card, write one lesson line in `runs.md`: why it died,
   which assumption failed, and what that suggests trying instead.
4. **Grow the tree (gap-driven only, no child quota).** Write a child (`funnel.py new --parent <id>`) only when a
   card's review (step 6 or step 8) or L2 check explicitly names an open gap whose resolution would change a design
   decision. Never spawn children to fill a percentage quota (natural generalisations of a parent theorem and extra
   control arms belong as an added line in the parent's 筛选记录, not as new cards). A child states its one decisive
   change from the parent in its first 筛选记录 line (attack the named objection, remove a blocking hidden cost, or
   bring a non-trivial structure from another field). Whenever one idea builds on another, record it as `parent:`. Kill
   a parent when a child subsumes it. A child that only varies a parameter is allowed only when the parent's claim
   predicts a threshold or reversal across it (written before running), and at most two in a row on one branch (Eric
   2026-11-21 / 11-22).
5. **Screen together and reflect** every `screen_every` new cards (default 5). Rank all active L1 cards by pairwise
   comparison ("which of these two is more worth a long simulation, and why"), once by the runner and once in one
   batched call by a judge from a family other than most of the cards' generators; where the two rankings disagree
   strongly, keep both cards (the best LLM judges match expert pairwise preference only about 73% of the time, worst on
   feasibility: Ideation Arena, EMNLP 2026). Run the depth audit (above) and send failing cards back. Kill
   duplicates and dominated cards; pick at most `l2_per_screen` (default 3) top cards, keeping variety, to enter step 6
   (cross-family novelty & importance pre-screen); spawn children only on parents with a concrete named gap (step 4).
   Then write a reflection line in `runs.md`: death reasons counted; which tracks,
   methods and layers were used and which produced survivors; whether a failure pattern from METHODS §X is showing; and
   an explicit decision for the next cycles (track, method, layer or field). Act on it.
6. **Novelty and why-unsolved pre-screen (before L2 simulation)**, batched per reviewer family for the candidates picked
   at step 5 (by a model of another family than the generator; Claude/GPT cards → Gemini 4 Neon; Gemini cards → GPT-6.2
   Sol or Claude so Astra quota is saved for step 8): search ≥5 closest works across fields by **abstract mathematical
   operator/structure**, not scenario keywords; score **intrinsic importance** ("if nobody had done this before, would
   it merit a strong Transactions paper?") separately from **prior-art occupancy** (a high-intrinsic-value card killed
   by prior art is noted as a positive taste reference and its diagnostic numbers harvested, without running L2);
   restate the claim in plain words with one everyday analogy, calling out common practice disguised in jargon; then:
   - If the abstract operator is **unoccupied**, decide why — **(1a)** nobody noticed, **(2)** noticed but unimportant in
     real systems (e.g. default protocol parameters or a 5-minute 1D parameter sweep already avoid it), or **(3)** noticed
     but blocked or carrying a hidden system cost — with evidence and real-system effect size.
   - If the operator **has prior art in another waveform/regime** (e.g. flat fading, OFDM, integer-grid OTFS) **but not in
     the target setting**, do not auto-kill by operator name alone: apply the **Direct-Port (`naive_port`) Test**. Classify
     as **(1b) non-trivial adaptation** when the L1 probe shows that directly porting the strongest prior-art baseline
     (with its standard companion parts, across a valid standard/physical operating range) either (i) breaks down by
     ≥0.8 dB (or ≥0.05 bit/sym MI) due to target-specific structure, (ii) suffers a complexity-order blow-up that the
     proposed structure removes at matched accuracy, or (iii) exhibits a quantitative ranking or design-rule reversal
     relative to the source regime (e.g. `21-l02`); otherwise classify as **(2) trivial port ("硬套")**. Bound/diagnostic
     cards pass as **(1a)/(1b)** when they tighten a known bound by ≥1 dB or establish a closed-form regime-flip boundary.
   - **Anti-false-kill symmetry**: when a card provides executed `naive_port` / MI / complexity numbers, the reviewer may
     NOT kill it before L2 with a hand-waving "adapting from X looks straightforward"; to kill at step 6, the reviewer
     must either cite prior art that already solved the same obstacle in an isomorphic setting or name the concrete
     standard component omitted from `naive_port` (when uncertain, advance to step 7 L2).
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
8. **Cross-model gate**, one batched call per reviewer family for step-7 survivors: send each card and its L2 scripts/
   numbers to a reviewer of a family different from its `generator` (Claude and Gemini cards → `codex exec --sandbox read-only -m
   gpt-6.2-astra` if the card is not `pit` (it would reach L3 and the owner), `gpt-6.2-sol` if it is `pit`, the two
   standing in for each other, then Claude (not for Claude cards) or Neon; GPT cards → Gemini 4 Neon via agy), asking
   per card for the strongest objection, whether baselines, attribution and the four simulation rules hold, and PASS /
   KILL / REVISE. Cards finishing mid-cycle wait for the next screening batch. Record reviewer, model and verdict in the
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

External generators (ARIS `idea-creator` Phase 2: generators of different families fail differently, so take the
union). A runner that can call other models — `codex --search exec --sandbox read-only -m gpt-6.2-sol` (prompt on stdin),
`~/.local/bin/agy -p "<prompt>" --model gemini-4-neon-high --sandbox --add-dir <skill dir>` (sandboxed: may run a ≤30 s
`/opt/anaconda3/bin/python -c` NumPy probe to stdout, never writing project files; use `--output-format json` and, if the
response has no final result, ask again with `--conversation <id>`), `devin -p --model <id>` — should, each cycle, have one or two of them think an idea
through independently, in parallel with its own, using the fill-in prompt in the project's funnel folder
(`prompts/external-idea.md`). Each result that is not DROPPED becomes a card with `generator:` set to that model; never
pre-filter a card for looking weak, the joint screening decides. While generating, runners and external generators read
the screened history (cards, killed lists) but not other runners' unscreened work; merging happens at screening, because
coupled agents converge ("Diversity Collapse in Multi-Agent LLM Systems", arXiv 2604.18005).

Model roles (defaults; `FUNNEL.md` may override). Use each model where it is strong, and keep every verdict in a family
other than the card's generator:

| Step | Default | Why |
|---|---|---|
| Main runner: choosing problems, framing, the story | Claude (Eric's local runner: Fable 5.2 Fusion high) | sets direction and tone |
| Generator: cross-domain analogies, world knowledge (method-transfer, toy-setting, anchor D) | Gemini 4 Neon / Carbon high | Eric 2026-11-21: Gemini is the most inventive, with the broadest world knowledge |
| Generator: derivation-heavy ideas (GPT family vote) | GPT-6.2 Astra high only, at most every other cycle and 4 per runner per round; Sol does not generate | Eric 2026-11-22: only Astra generates independently (Sol: 10 ideas in rounds 3–4, none survived); GPT models get an assigned anchor |
| L1 novelty search | Gemini 4 Neon high, or the runner | broad literature knowledge |
| Step 6 pre-L2 novelty + intrinsic-value screen | Claude / GPT cards → Gemini 4 Neon high; Gemini cards → GPT-6.2 Sol high (or Claude) | catches prior art and trivial-sweep non-problems before spending L2 compute; saves Astra quota for step 8 |
| Step 7 L2 derivation, estimate, hole-finding | GPT-6.2 Sol high; Astra only when a verdict hinges on a rigorous derivation Sol cannot settle | Eric 2026-11-22: Sol is enough for routine review and derivation; save Astra for what matters |
| Step 7 L2 small code runs | the runner, or GPT-6.2 Sol | cheap execution |
| Pairwise ranking pass (volume) | Gemini 4 Hydrogen high; GPT-6.2 Sol when most cards are Gemini's | cheap; the ranking is advisory (judges match experts about 73%) |
| Step 8 post-L2 gate | Claude and Gemini cards → GPT-6.2 Astra high if not `pit`, GPT-6.2 Sol high if `pit` (each other's fallback, then Claude for non-Claude cards, then Neon); GPT cards → Gemini 4 Neon high; unknown family → the same GPT choice plus Neon | cross-family audit of L2 scripts, baselines and attribution; Astra only where a card may reach the owner |
| 白话与类比 on L3 cards (the ones Eric reads) | Gemini 4 Hydrogen high | plain language is a Gemini strength and Hydrogen is cheaper |

Reasoning effort: high by default; xhigh only for a judgement-heavy call that could swing the round.

Anchors (every card needs at least one, with its source): **A** a specific recent paper that states the limitation or
leaves it open (found with a search tool in this round, never from memory alone); **B** a number and file path from this
project's results (an anomaly, a genie or ceiling gap); **C** an assumption most papers make plus evidence of the real
condition (standard, measurement, hardware); **D** two works or communities holding halves of an answer that do not cite
each other. At most three cards per anchor; cover at least three anchor types per round.

Lenses: ARIS's five structural-gap lenses — method-transfer (works in A, untried in B), contradiction, untested
assumption, scaling regime, diagnostic (a question nobody asked) — plus the toy-setting lens: where the problem is easy,
which one ingredient makes it easy, and what could replace that ingredient in the real setting. Optional: the patterns
in `~/.claude/skills/idea-spark/references/ideation-patterns/` when installed.

## Eric's marks and after

He writes in `eric:` one of `继续`, `停`, `改：<what>`. On the next session, apply the marks: 停 → `status: killed`
(reason: Eric); 改 → child card or back to L2; 继续 → `status: promoted`, then propose a Trellis task (ask before creating
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
