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
| L1 深想 | One idea thought through with full effort: derivation or estimate, closest works, 去壳, cheapest decisive check | full effort, about an hour of agent time | AI: write the card or drop the draft |
| L2 便宜证据 | One decisive cheap check, at least one facing outside the project | about 30 minutes agent time, at most 1 CPU core-hour, no GPU, existing code only | AI: kill / candidate / park |
| 放行 | Cross-model gate on L2 candidates | one batched call per screening | other-family reviewer: pass / kill / revise |
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

Tracks, so the round does not circle inside one pit (rough targets for the round's mix, not quotas to fill;
`FUNNEL.md` may override; every card sets `track:`):
- **core** (about 50%): this project's own problems.
- **adjacent** (about 25%): the same abstract problem class in another system or waveform (`ABSTRACTION.md` §3).
- **explore** (about 15%): outside the project but within the owner's reach (for Eric: physical-layer signal processing,
  estimation, coding); judged by its value as a standalone Transactions paper.
- **pit** (about 10%): questions the project's own premises (`ABSTRACTION.md` §5): if the pit is bad, this is how the
  funnel finds out.
One idea in five is a wildcard: the generator chooses its own method, anchor and track.

Each cycle:

1. **Inspiration read** (about 10 minutes): skim 3–5 recent papers from the field rotation in `ABSTRACTION.md` §3, one
   of them from a far field; note in `runs.md` the sparks and which open problem (§4) each bears on (METHODS M1). This
   is reading for ideas, not checking novelty.
2. **Think one idea through (L1).** Pick track, anchor and lens; use any method from METHODS that helps, or your own,
   and write `方法：<id 或 自己的>` in the first 筛选记录 line. Name the layer the idea attacks and its abstract problem
   class from your own decomposition, and look at how other fields with the same class handle it (G12). Then work it like a research conversation, not a list item: state the
   problem precisely; derive the key relation or an estimate with this project's numbers (formula and substitution);
   search the 3–5 closest works (`scoop-check`, `paper-search`, `literature-search`, `comm-lit-review` or plain web
   search) and say how each differs; write the three 去壳 sentences; name the cheapest check that could kill it; set
   `value` (3 = would change a design decision across a subfield, 2 = changes one system's design or a standard
   parameter, 1 = incremental) and `next_cost`. Before dropping it, name its smallest plausible repair (G15). Only then
   create the card (`layer: L1`, `generator:` the model that did the thinking, `track:`). If it still dies (already
   solved, already being worked per `FUNNEL.md`, on a killed list, or a 去壳 sentence cannot be written plainly), add the
   title and reason to `runs.md` as a dropped draft.
3. **Learn from every death.** For each dropped draft or killed card, write one lesson line in `runs.md`: why it died,
   which assumption failed, and what that suggests trying instead.
4. **Grow the tree.** Children are the main way to go deep, and they do not wait for the gate. Write a child
   (`funnel.py new --parent <id>`) when a card passes L2, gets REVISE, is picked for deepening at screening (step 5), or
   the derivation suggests a sharper or more general version. A child states its one change from the parent in its
   first 筛选记录 line (change one condition, generalise, attack the strongest objection, or bring a method from another
   field). Whenever one idea builds on another, record it as `parent:`, even if the link was only noticed afterwards.
   Kill a parent when a child subsumes it.
5. **Screen together and reflect** every `screen_every` new cards (default 5). Rank all active cards by pairwise
   comparison ("which of these two is more worth a long simulation, and why"), once by the runner and once in one
   batched call by a judge from a family other than most of the cards' generators; where the two rankings disagree
   strongly, keep both cards (the best LLM judges match expert pairwise preference only about 73% of the time, worst on
   feasibility: Ideation Arena, EMNLP 2026). Run the depth audit (above) and send failing cards back. Kill
   duplicates and dominated cards; pick at most `l2_per_screen` (default 3) for L2, keeping variety. Then deepen
   best-first: the top `deepen_per_screen` cards of the ranking (default 2) each get one child before any new root is
   started; across the round at least `child_share` of deep ideas (default 40%) are children. Then write a reflection line in `runs.md`: death reasons counted; which tracks,
   methods and layers were used and which produced survivors; whether a failure pattern from METHODS §X is showing; and
   an explicit decision for the next cycles (track, method, layer or field). Act on it.
6. **L2 cheap evidence** within the cap: a readout of existing data, an estimate or bound, a small run of existing code,
   or reading the closest 5–10 papers in full to confirm the gap. At least one check per card faces outside the project
   (literature, standard or real-system evidence): internal simulations alone favour problems we created ourselves. For
   a gate candidate, have a model of another family re-derive its key number independently. Use the cap: a check that
   only reads files and does arithmetic is fine when it is decisive, but when the decisive check is a simulation, run
   it. A runner that cannot run the project's simulations (e.g. a cloud runner without the receiver's environment)
   parks the card with `next_cost: 需本地仿真：<what, estimated cost>`; local runners take such cards first in their L2.
   A simulation check follows four rules (first blind cross-family review, 2026-11-21, sent every simulated card back for
   breaking one of them): write the decision rule and any threshold before running; never pick a threshold on the same
   frames you report (hold frames out, or confirm on fresh frames); compare against the reference that matches the
   claim's setting (e.g. a true-delay claim against the true-delay arm); for a "these cases benefit" claim, run the
   alternative action on the same cases to rule out "they were easy anyway". Report counts with an interval when the
   sample is small.
   Result: kill, park with the heavier check and its cost, or gate candidate.
7. **Cross-model gate**, one batched call per reviewer family for the candidates of this screening: send each card to a
   reviewer of a family different from its `generator` (e.g. `codex exec --sandbox read-only -m <model>` with the prompt
   on stdin, or `devin -p --model <GPT model>`, from a Claude-family generator; Claude from a GPT-family generator),
   asking per card for the strongest objection, whether the anchor and closest-work notes hold, and PASS / KILL /
   REVISE. Record reviewer, model and verdict in the card. PASS → L3 (a `pit` card at L3 is a decision for Eric, shown in
   its own board section); KILL → killed; REVISE → child card or back to L2. With no second family available, leave
   candidates at L2 with `next_cost: cross-model review`.
8. Run `board`; append progress to the round's line in `runs.md`; commit; continue.

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
union). A runner that can call other models — `codex --search exec --sandbox read-only -m gpt-6.2-astra` (prompt on stdin),
`~/.local/bin/agy -p "<prompt>" --model gemini-4-neon-high --mode plan --add-dir <skill dir>` (read-only; slow, minutes per
call; use `--output-format json` and, if the response has no final result, ask again with `--conversation <id>` — plan
mode sometimes stops after reading files), `devin -p --model <id>` — should, each cycle, have one or two of them think an idea
through independently, in parallel with its own, using the fill-in prompt in the project's funnel folder
(`prompts/external-idea.md`). Each result that is not DROPPED becomes a card with `generator:` set to that model; never
pre-filter a card for looking weak, the joint screening decides. While generating, runners and external generators read
the screened history (cards, killed lists) but not other runners' unscreened work; merging happens at screening, because
coupled agents converge ("Diversity Collapse in Multi-Agent LLM Systems", arXiv 2604.18005).

Model roles (defaults; `FUNNEL.md` may override). Use each model where it is strong, and keep every verdict in a family
other than the card's generator:

| Step | Default | Why |
|---|---|---|
| Main runner: choosing problems, framing, the story | Claude Opus 5.5 high (or Fable) | sets direction and tone |
| Generator: cross-domain analogies, world knowledge (method-transfer, toy-setting, anchor D) | Gemini 4 Neon high | Eric 2026-11-21: Gemini is the most inventive, with the broadest world knowledge |
| Generator: derivation-heavy ideas (GPT family vote) | GPT-6.2 Astra high | rigorous mathematics (about-eric §6); weaker at choosing direction, so it gets an assigned anchor |
| L1 novelty search | Gemini 4 Neon high, or the runner | broad literature knowledge; Gemini found prior work the others missed on 2026-11-21 ("data as pilot") |
| L2 derivation, estimate, hole-finding | GPT-6.2 Astra high | rigour and auditing |
| L2 small code runs | the runner, or GPT-6.2 Sol | cheap execution |
| Pairwise ranking pass (volume) | Gemini 4 Hydrogen high; GPT-6.2 Sol when most cards are Gemini's | cheap; the ranking is advisory (judges match experts about 73%) |
| Cross-model gate | Claude or Gemini cards → GPT-6.2 Astra high; GPT cards → Claude Opus 5.5 high | auditing strength, family crossing |
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
