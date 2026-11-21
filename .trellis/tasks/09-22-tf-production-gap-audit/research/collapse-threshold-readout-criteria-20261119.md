# Collapse-threshold readout: criteria written before computing (2026-11-19, Claude)

Context: [miao assessment §3.2](miao-assessment-claude-20261119.md); Eric: "先做这两个零成本检查". Post hoc readout on archived rows only, so
it is exploratory: any law it suggests must still be tested prospectively on a new setting.

**Data.** `experiments/rho_sweep_20261119/out/main_20261119/rows_shard*` on deinlab: 62,400 keys; ρ ∈ {.15, .20, .25, .30, .40, .50};
U/G; 3–12 dB. Triggered frames only (F0 syndrome nonzero). Rescue means CD errors = 0.

**Question.** Is there a per-frame quantity X, known before CD runs, whose rescue curve P(rescue | X) is the same at every ρ once the
data SNR is held fixed? If so, the ρ < .25 collapse is "triggered frames moving past X*", and ρ* could be predicted from where the X
distribution crosses X*.

**Candidates.**
- X1 = F0 info-bit error fraction, errors/1024 (uses truth; a mechanism variable);
- X2 = F0 final syndrome weight (observable online);
- X3 = u/N (observable online).

**Cells.**
- Data SNR is d = SNR + 10·log₁₀(1 − ρ), banded to 1 dB.
- X is split into pooled deciles over all triggered frames.
- A (X decile, d band) cell is **comparable** if at least 3 ρ values each have ≥ 30 frames in it.

**Pass rule for each X** (both must hold):
- (i) **ρ-invariance**: across comparable cells, the median of (max − min rescue rate across ρ) is ≤ 0.10;
- (ii) **threshold shape**: the pooled rescue curve over X deciles, within at least one d band, falls from ≥ .80 to ≤ .20.

**Reported.**
- For a passing X: X*, the pooled 0.5 crossing within each d band.
- Per (ρ, SNR): the fraction of triggered frames beyond X*, next to CD's FER, showing whether the collapse cells are the ones where
  most triggers sit beyond X*.

**Outcomes.**
- **No X passes** → no single bootstrap threshold in these rows. The pilot-law candidate is downgraded and recorded as negative.
- **Only X1 passes** → a mechanism threshold exists but is not observable online. The law can be stated but needs a model for X1(ρ, SNR).
- **X2 or X3 passes** → an online-observable threshold. This is the strongest outcome; a prospective ρ* prediction on a new setting
  becomes the next step (needs Eric's approval).

**Known confound.** Data-limited failures (low d) cannot be rescued at any X. Holding d fixed is meant to remove this; any residual ρ
dependence is reported, not explained away.
