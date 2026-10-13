# Read-only bridge to the six saved observations

This stage reads the six original G1 N1024 observations, preserving the three
shared exogenous channel clusters and their 10/20 dB versions. It calls no
receiver, decoder, channel generator or latent-stream replay. It does not
update a previous result or construct fresh confirmation evidence.

`bridge.py` first computes inverse-DAFT powers and three anchored fourth-order
contrasts using only y, the public chirps, the known pilot and sigma2. These
files are saved **before any truth artifact is opened**. The raw statistic is
observable; it is not automatically an estimate of the blind control model's
q. Pilot cancellation would require an H estimate and is not performed.

A separate applicability pass reads truth geometry and the already completed
`normalization_v1` conditional-PDP audit. PDP and true geometry are explicitly
oracle metadata, never estimator inputs. It checks path count, common delay,
pilot absence, coding independence, gain model, stream sharing and the old
actual internal-state counts. Both original input arrays and imported prior
geometry must match. All input hashes are preserved in the registered result.

The main coefficient requires two paths with common delay, iid equal Gaussian
gains, no pilot and independent uniform QPSK. Eight-path G1 observations with
superimposed pilots and an LDPC code require a different moment model. Six
cross-SNR records cannot serve as six independent repetitions. In particular,
the three earlier positive-definite different-delay Grams cannot refute the
new same-delay rank-one pruning counterexample.

The old state receipt already distinguishes joint1/joint20 from fixed1/fixed20
and records actual gain updates. This bridge reuses that evidence. It preserves
the confounds from changes in internal update budget, gain uncertainty,
point-estimate H, geometry error and outside Gaussianization. Observed
contrasts are not correlated against six FER labels to manufacture causality.
No new performance claim or receiver conclusion follows from this stage.

The registered output supplies the case-by-case matrix, original input hashes,
three-cluster structure and explicit transferable/nontransferable conditions.
`bridge_v1` completed: all six raw observation feature vectors were finite,
zero observations satisfied the blind same-delay two-path control model, and
all three original eight-distinct-delay Grams were positive definite. The
17 explicit input hashes matched before/after; the outer registered source
ledger additionally bound all old population metadata and seals. See
`results/afdm_higher_order_information/PRIOR_BRIDGE_RESULTS.md` for exact
conditions, original schedule confounds, costs and the per-case evidence links.
