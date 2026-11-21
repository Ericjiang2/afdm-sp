# AFDM Claim Reconstruction Bundle

**Created:** 2026-07-26  
**Purpose:** Give an external AI (or human referee) a self-contained evidence pack to rebuild paper claims from **primary data + math**, without trusting existing HTML verdicts.

## How to use

1. Upload this whole unzipped folder (or the zip) to a strong model with file access + web retrieval.
2. Open and follow:
   - `00_prompt/PROMPT_claim_reconstruction.md`  ← **main instruction**
3. Ask the model to output **one complete HTML report**.
4. Optional short starter message (prefer `00_prompt/STARTER_MESSAGE.txt`):

```text
严格按照 00_prompt/PROMPT_claim_reconstruction.md 执行。
不要轻信 01_adjudication_html 里的结论；先从 03_raw_results 和 04_analysis_scripts 重算与重导。
先指出作者没问但更关键的问题；拆解以讲清因果机制为准，禁止堆砌空洞抽象层级。
数学推理要硬。最终只输出一份完整 HTML 报告。
```

## Directory contract

| Dir | Trust level | Role |
|-----|-------------|------|
| `00_prompt/` | instruction | What the AI must do |
| `01_adjudication_html/` | **LOW** (secondary) | Prior human/AI writeups; audit target, not proof |
| `02_theory_architecture_html/` | hypothesis | Intended theory/architecture notes |
| `03_raw_results/` | **HIGH** (primary) | JSON/NPZ/logs from GateA/B, mech, self-supp, F2-P firm, complexity |
| `04_analysis_scripts/` | **HIGH** (definitional) | Scorer definitions, bootstrap, eval entrypoints |
| `05_old_narrative_for_contrast/` | LOW stale | Old claims to attack/rewrite |
| `06_qa_and_logs/` | process | QA index / reproduction notes |
| `07_direction_context_optional/` | optional | PhD/direction context; not required for this paper’s claims |

## What was intentionally excluded

- Large training caches / checkpoints (`*.pt`, feature caches)
- Full git history
- Unrelated loop outputs and bulky auto-review dumps
- Remote-only artifacts not present locally

This keeps the pack small (~few MB) while preserving the numbers needed to re-adjudicate claims.

## Suggested human QA after the AI returns HTML

Check that the report:
1. Names an **unasked but decisive** question before listing contributions
2. Recomputes at least one Gate table from JSON rather than copying HTML prose
3. Defines achievable/genie/geom/white from code
4. Separates F2-P deployment gain from scorer gain with a mechanism chain
5. Contains a kill-list against `NARRATIVE_REPORT.md`
6. Gives a venue-matched MVP contribution list with evidence paths
7. Does **not** replace missing mechanisms with multi-layer abstract frameworks
