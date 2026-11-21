# Idea-generation methods（出题方法索引）

A toolbox, not a checklist: use whatever helps, including methods not listed here. It is self-contained (cloud runners
only have this file); fuller versions live in the local files named under each section. Each deep idea notes the method
it leaned on, or `自己的`, in its first 筛选记录 line (`方法：<id>`), so later rounds can see which approaches produce
survivors. Varying methods helps avoid circling; it is a habit, not a rule.

## M. How people with a steady stream of good ideas work (habits)

| id | Method | How to apply here | Source |
|---|---|---|---|
| M1 | Keep a list of 10–20 important open problems; when a new tool or result appears, ask "which problem does this bear on?" | Keep your own list (start from your decomposition; `ABSTRACTION.md` §4 is one author's list built from the project's current cards, so it leans toward the current pit); match every inspiration-read paper against it | Hamming, *You and Your Research* (1986 talk) |
| M2 | Important = you have a reasonable attack, not just big consequences | Every card names the attack (sentence 3 of 去壳) | Hamming (1986) |
| M3 | Spend fixed time on "what is and is not important in the field" | The per-screening reflection and the inspiration read are this time | Hamming: "Friday afternoons … great thoughts only", ~10% of his time |
| M4 | Keep a dozen favourite problems; test every new trick against them | Same list as M1; when a method below works once, try it on the other open problems | Rota, *Ten Lessons I Wish I Had Been Taught* (1996), on Feynman |
| M5 | Choose by feasibility × interest; the stuck point is where new things are found | Value and next_cost on every card; a stall is a signal to look sideways, not to stop | Alon, "How to choose a good scientific problem", *Mol. Cell* 2009 |
| M6 | Follow anomalies: results that do not fit the model | Anchor B; anything our genie ladder or readouts could not explain | Kuhn (1962); in this project: A3 anchor mismatch → card c01 |
| M7 | A long-held concrete problem plus an old idea from elsewhere | Arıkan: boosting the cutoff rate of sequential decoding + Pinsker/Massey channel splitting → polar codes | Arıkan, "On the origin of polar coding", JSAC 2016 |
| M8 | Engineering questions can open theory | Berrou: "can repeated decoding improve SNR?" while building a decoder → turbo codes | Berrou et al., turbo-code history |

## G. Generative operators (to produce or reshape an idea)

| id | Operator | How | Source |
|---|---|---|---|
| G1 | Restate the problem in as many forms as possible | Write the problem in 3 framings (estimation, detection, information budget) before choosing one | Shannon, "Creative Thinking" (Bell Labs, 1952) |
| G2 | Generalise / specialise | Drop a condition (any waveform, any pilot) or add one (one path, noiseless) | Pólya, *How to Solve It*; Shannon (1952) |
| G3 | Two small jumps instead of one big one | Find an intermediate problem that is solvable and connects to the target | Shannon (1952) |
| G4 | Toy setting → the one ingredient that makes it easy → a native substitute in the real setting | Where is our problem easy (genie channel, high ρ, integer Doppler, known data)? What exactly makes it easy? What real quantity can play that role? | Alpöge's account of the 2026 RH claim (function fields → integers) |
| G5 | Combine two different ideas that each work in a toy setting | Name the interaction between them, not just the sum | Alpöge (2026); ccf-idea-optimizer "combine" |
| G6 | Inversion | Ask what would guarantee failure; or swap cause and effect, input and output, transmitter and receiver | Jacobi; methods handbook A7 |
| G7 | Extremes and scale shifts | ρ → 0 or 1, N → ∞, SNR → ∞, one path, a continuum of paths; what breaks first? | scientific-brainstorming "scale shifting"; Pólya |
| G8 | Constraint removal | "If we knew X, how much would we gain?" (our genie ladder A/A2/A3 is this); then ask how to get X | — |
| G9 | Contradiction (TRIZ) | Improving A worsens B (pilot power vs data power; resolution vs noise): look for separation in time, frequency, condition or scale rather than a trade-off | Altshuller, TRIZ |
| G10 | Morphological analysis | List the design axes (pilot type, waveform, receiver stage, metric, channel model) and their options; look for empty combinations | Zwicky |
| G11 | Assumption reversal | List what nearly every paper assumes (integer delays, known σ², narrowband Doppler, NMSE as target) and flip one | scientific-brainstorming; ARIS lens "untested assumption" |
| G12 | Method transfer and literature-based discovery | Find a field with the same abstract structure (see the project's `ABSTRACTION.md` §analogues), read how it solved it; or two literatures A–C linked only through B | Swanson's ABC model (1986); ARIS lens "method transfer" |
| G13 | Contradiction between published findings | Two papers that disagree are a problem waiting for a unifying condition | ARIS lens "contradiction" |
| G14 | Instrument instead of improve | Turn the idea into a diagnostic, a benchmark, a bound or a measurement when a better algorithm is crowded | ccf-idea-optimizer "instrument" and rescue patterns |
| G15 | Rescue before rejecting | Before dropping an idea, name its smallest plausible repair and why that fails | ccf-idea-optimizer coherence audit |

Fuller local libraries: `~/.skills-manager/skills/scientific-brainstorming/references/brainstorming_methods.md` (SCAMPER,
TRIZ, morphological analysis, biomimicry, provocation, future backwards); `~/.agents/skills/ccf-idea-optimizer/references/frontier-ideation.md`;
`~/.claude/skills/idea-spark/references/ideation-patterns/` (15 patterns from 1,947 ML papers); methods handbook
`~/projects/personal-ai-workflow/docs/methods-handbook.md` (A1–A13, judgement-oriented).

## F. First principles: get below the code names

Before generating, and whenever a round stalls, rebuild the problem from the bottom yourself. Do this before reading the
project's `ABSTRACTION.md`: that file is one earlier author's map, useful to compare against afterwards, and it can be
wrong; record where you disagree.
1. Strip names. "AFDM", "SP", "CODELAY" are particular technical choices; say what each one does physically and
   mathematically.
2. Layers: physics (what creates delay and Doppler) → signal model (what operator acts on what) → inference structure
   (what is unknown, what is known, what couples them) → algorithm (stages, what each stage needs to start) → system
   objective (what the user pays and receives) → evaluation (what metric stands for the objective).
3. Ask what is fundamentally scarce, unknown or limiting at each layer, and which layer the idea attacks.
4. Name the abstract problem class and list other fields with the same class; read how they handle it (G12).
5. Ask whether the project's own premises hold (see track `pit` in the protocol).

## W. Workflows of people who recently did strong work with AI (what we copy)

| Who | What they did | What we copy |
|---|---|---|
| Anthropic (Aug 2026): Claude raised the known fraction of zeta zeros on the critical line from 41.6% to 67.2% | ~650 failed ideas first; then ~60 subagents for a day and a half, thousands of numerical checks against known zeros, subagents reviewing each other, a novelty check against 54 arXiv papers, an independent re-proof, Lean formalisation, expert review | Breadth with many expected failures; a cheap numerical check on every claim (L2); cross-review (gate); independent re-derivation of the key number for L3 candidates; novelty search before promotion |
| Alpöge with Claude (Nov 2026 claim, unverified at the time of writing) | Decades of preparing every tool he might recognise; a toy setting; combining two ideas; recognising structure in others' results; Claude supplying depth in fields he had not mastered; formal verification | G4, G5, M1/M4; let an external model supply depth in an adjacent field (Neon, Astra) |
| Tao, Georgiev, Gómez-Serrano, Wagner with AlphaEvolve (Nov 2025) | Evolutionary search on 67 problems where a construction can be scored | When an idea reduces to a scoreable quantity, let search optimise it (OpenEvolve/ShinkaEvolve) and extract the principle afterwards |
| Google AI co-scientist (2025) | Generate → reflect → pairwise tournament → evolve → meta-review | Pairwise ranking at screening; children (evolve); per-screening reflection (meta-review) |
| ARIS `idea-creator` (2026) | Lens fan-out, two external generators, cross-model jury, small pilots | Lenses, family-diverse generators, the gate |
| IDEAgent (2026) | Quality-diversity search with lineages; compares new ideas with completed, ancestor and rejected ones; Yield metric | The tree; the diverse-yield stop rule |

## X. Failure patterns to recognise in the reflection

- Crowded neighbourhood: half or more of the deaths are "already done" → move up an abstraction level or to another
  field, do not try a tenth variant.
- Self-made problems: issues that exist only in our code or our simulator (Neon, 2026-11-20 retrospective) → require an
  outside-facing check.
- Circling in the pit: three ideas in a row on the same mechanism → ban that mechanism for the rest of the round. A
  variant: one experiment re-run at another parameter value and filed as a new child (cloud round 5, 2026-11-21: 45 deep
  ideas around c48/c77, none gated as its own problem) → a parameter-only child must say why that parameter is decisive,
  and at most two in a row per branch (SKILL step 4).
- Judging by looks: LLM-generated ideas look more novel than they turn out after execution (Si et al., 2024; 2025) →
  promotion depends on checks, not on wording.
