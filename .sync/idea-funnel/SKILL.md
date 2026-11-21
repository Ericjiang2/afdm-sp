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

- Funnel folder (one per project, e.g. `<project>/ideas/`): `FUNNEL.md` (project settings: domain, must-read files,
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

A round ends when `target_ready` mutually distinct cards (default 10) are at L3 — children of one root count once unless
the gate judged them distinct problems (the "yield" of IDEAgent: the largest set of mutually diverse ideas above the bar) — or the round budget in `FUNNEL.md` is spent (deep ideas or hours), or
`stall_limit` deep ideas in a row (default 8) have produced no new L2 candidate after widening (below) — whichever comes
first. A runner that cannot run the gate (e.g. a cloud runner) stops instead at `cloud_target` gate candidates (default
15), since its cards cannot reach L3 on their own. Then stop and report.

Run without pausing: a round is meant to run for hours. Do not stop to report, summarise or ask for confirmation; after
each screening start the next cycle at once. Commit after every screening (a cloud runner also pushes) so the work
survives an interrupted session. End only on a stop condition.

Widen before counting a stall: when the assigned anchors and lenses seem used up, do not stop. In order: (a) switch to
the other lenses and anchors; (b) grow children of every L1 or L2 survivor and parked card, one stated change each;
(c) harvest anchors from the limitations and future-work sections of 10–20 recent papers in the area; (d) revisit killed
cards for a clearly different angle (a new child, not a revival). Only deep ideas that still produce nothing after these
count toward `stall_limit`. Before starting, read `FUNNEL.md`, every existing card (killed ones included, so nothing is proposed twice) and
the must-read files it lists, and state the round budget.

Loop until the round ends:

1. **Think one idea through (L1).** Choose an anchor and a lens not yet covered (see below). Work it like a research
   conversation, not a list item: state the problem precisely; derive the key relation or a back-of-envelope estimate
   with this project's numbers; search the 3–5 closest works (`scoop-check`, `paper-search`, `literature-search`,
   `comm-lit-review` or plain web search) and say how each differs; write the three 去壳 sentences; name the cheapest
   check that could kill it; set `value` (3 = would change a design decision across a subfield, 2 = changes one system's
   design or a standard parameter, 1 = incremental) and `next_cost`. Only then create the card (`layer: L1`, `generator:`
   the model that did the thinking). If the idea
   dies during the work (already solved, already being worked per `FUNNEL.md`, on a killed list, or a 去壳 sentence
   cannot be written plainly), do not make a card: add the title and one-line reason to `runs.md` as a dropped draft.
2. **Grow the tree.** When a card passes L2, gets REVISE from the gate, or the derivation suggests a sharper or more
   general version, write the variant as a child card (`funnel.py new --parent <id>`). A child states its one change from
   the parent in its first 筛选记录 line. Kill a parent when a child subsumes it.
3. **Screen together** every `screen_every` new cards (default 5): rank all active cards by pairwise comparison ("which
   of these two is more worth a long simulation, and why"), once by the runner and once in one batched call by a judge
   from a family other than most of the cards' generators; where the two rankings disagree strongly, keep both cards
   (the best LLM judges match expert pairwise preference only about 73% of the time, worst on feasibility: Ideation
   Arena, EMNLP 2026). Kill duplicates and dominated cards; pick at most `l2_per_screen` (default 3) for L2, keeping
   variety.
4. **L2 cheap evidence** within the cap: a readout of existing data, an estimate or bound, a small run of existing code,
   or reading the closest 5–10 papers in full to confirm the gap. At least one check per card faces outside the project
   (literature, standard or real-system evidence): internal simulations alone favour problems we created ourselves.
   Result: kill, park with the heavier check and its cost, or gate candidate.
5. **Cross-model gate**, one batched call per reviewer family for the candidates of this screening: send each card to a
   reviewer of a family different from its `generator` (e.g. `codex exec --sandbox read-only -m <model>` with the prompt on stdin, or
   `devin -p --model <GPT model>`, from a Claude-family generator; Claude from a GPT-family generator), asking per card
   for the strongest objection, whether the anchor and closest-work notes hold, and PASS / KILL / REVISE. Record reviewer,
   model and verdict in the card. PASS → L3; KILL → killed; REVISE → child card or back to L2. With no second family
   available, leave candidates at L2 with `next_cost: cross-model review`.
6. Run `board`; append progress to the round's line in `runs.md`; continue.

External generators (ARIS `idea-creator` Phase 2: generators of different families fail differently, so take the
union). A runner that can call other models — `codex --search exec --sandbox read-only -m gpt-6.2-astra` (prompt on stdin),
`~/.local/bin/agy -p "<prompt>" --model gemini-4-neon-high --mode plan --add-dir <skill dir>` (read-only; slow, minutes per
call), `devin -p --model <id>` — should, each cycle, have one or two of them think an idea
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
