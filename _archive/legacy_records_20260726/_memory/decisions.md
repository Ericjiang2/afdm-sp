# Decisions

## 2026-05-17

### Decision 11

- Treat `paper-tmlcn/main_round2_ieeetrans_20260517.pdf` as the current
  IEEE-Transactions-style cleaned paper snapshot.
- Reason:
  - it compiles successfully as a 14-page letter PDF
  - the hard LaTeX checks are clean: no undefined references, undefined
    citations, missing BibTeX entries, or overfull boxes
  - the bibliography is fully used: 46 cited, 0 unused, 0 missing
  - the paper-facing text no longer exposes targeted code/file/path/QA/internal
    provenance terms

### Decision 12

- Use Codex subagent review as the accepted fallback when Claude MCP
  `opus 4.7 high` is unavailable/no-access.
- Reason:
  - the user explicitly requested Claude MCP first and automatic Codex fallback
  - Claude MCP failed at model selection rather than manuscript content review
  - the fallback review found concrete IEEE-style issues, which were fixed and
    verified

## 2026-03-30

### Decision 1

- Stop pursuing detector-side mean-residual distillation as the main paper claim.
- Reason:
  - corrected BER results falsified the original positive claim
  - the method was not decision-effective

### Decision 2

- Pivot the project framing from pure positive-method to diagnostic-plus-method.
- Reason:
  - the strongest supported story combines a sharp failure diagnosis with a small but real decision-level fix

### Decision 3

- Use the frozen direct-bit corrector as the new method anchor.
- Reason:
  - it is the first method that generalizes across untouched independent caches
  - it reaches the requested external score target of `6/10`

### Decision 4

- Treat regime-shift robustness as the next upgrade path instead of more in-distribution tuning.
- Reason:
  - external reviewer says the remaining blocker is breadth, not existence
  - another tiny same-pipeline gain is unlikely to move the score much further

### Decision 5

- Keep the `P_paths=15` negative result instead of hiding it.
- Reason:
  - it defines an honest failure boundary
  - it strengthens the paper's scope discipline

### Decision 6

- Use the lower-pilot-power (`rho=0.4`) shift as the strongest current robustness package.
- Reason:
  - it provides the largest positive shifted gain so far (`1.6699e-03`)
  - it materially helps with the “practical significance” criticism

### Decision 7

- Do not replace the current frozen corrector with a confidence-gated or simple `5` dB fallback variant.
- Reason:
  - the train-selected confidence threshold is `0.5`, i.e. no useful gate
  - disabling correction at `5` dB changes aggregate gain only marginally
  - these patches would complicate the story without materially improving the score

### Decision 8

- Use statistical packaging plus feature-group ablation as the next safety-first upgrade path.
- Reason:
  - it does not change the main method
  - it materially strengthens significance and mechanism evidence
  - external reviewer raised the score from `7.0` to `7.2` after seeing this package

### Decision 9

- Use the integer-Doppler structural shift as the main new robustness upgrade path and stop weaker exploratory shift lines once it proved clearly positive.
- Reason:
  - integer-Doppler scout was positive on `2/2` caches with mean gain `1.3538e-03`
  - clean `3`-seed confirmation stayed positive on `3/3` caches with mean gain `1.3249e-03`
  - external reviewer raised the score from `7.2` to `7.4` after seeing this new axis
  - the remaining gap is now importance beyond the AFDM simulator family, not lack of AFDM-local robustness

### Decision 10

- Use `64`-bit and `256`-bit contiguous packet endpoints plus expected transmissions under a simple ARQ proxy as the main system-level significance package.
- Reason:
  - reviewer explicitly said this was the shortest honest path from `7.4` to `7.5`
  - the positive regimes show clean packet/goodput gains with paired-bootstrap CIs
  - the harsh `P_paths=15` regime keeps the BER failure boundary explicit and loses reliable packet-level benefit at the chosen endpoints
  - external reviewer raised the score from `7.4` to `7.5` after seeing this package
