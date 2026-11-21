# Native F0 outer-round budget screen

Producing revision `4432c0a0`. Evaluated 2,240 paired U/G keys at physical rho .3, with 160 physical frames per scenario and SNR. Measured latency on a separate 48-key single-core panel at 6.5 and 7 dB. Native/experimental prefix and early-stop outputs passed the four-key parity gate. All remote data checksums and the local summary recomputation passed.

## Actual native two-round F0 profile

| Stage | Mean (ms) | Share |
| --- | ---: | ---: |
| Pilot acquisition | 77.68 | 31.6% |
| Channel refinement | 95.36 | 38.7% |
| Scalar-joint detector | 38.69 | 15.7% |
| LDPC and decoder messages | 33.91 | 13.8% |
| Remaining | 0.46 | 0.2% |
| Total | 246.10 | 100% |

The LDPC core already stops its own iterations on zero syndrome. Native F0 still completes both outer rounds. Mean LDPC iterations were 17.23 and 3.52 in those rounds.

## FER crossing and early termination

| Outer budget K | U SNR at 1% FER (dB) | G SNR at 1% FER (dB) | Fixed mean latency U / G (ms) | Early mean latency U / G (ms) |
| --- | ---: | ---: | ---: | ---: |
| 1 | 8.441 | >9.0 | 161.98 / 162.87 | 162.55 / 163.30 |
| 2 | 6.175 | 6.354 | 244.11 / 247.58 | 169.42 / 177.76 |
| 3 | ≤5.5 | 6.080 | 319.18 / 323.67 | 169.42 / 177.76 |
| 5 | ≤5.5 | 5.854 | 463.59 / 471.79 | 169.42 / 177.76 |
| 10 | ≤5.5 | 5.786 | 821.69 / 837.50 | 169.42 / 177.76 |

Early stopping retained the same frame error outcome as fixed K at every evaluated key and budget. The 48 timing keys included 42 first-round stops and six second-round stops. With a cap of two, mean latency against the separately executed native F0 comparison was 173.59 versus 246.10 ms (29.5% lower). All caps at or above two share the measured latency on this timing panel. In the broader FER population at 5.5 dB, the actual mean number of rounds under the early cap of 10 was 1.43 in U and 1.81 in G. The timing panel's latency applies to 6.5/7 dB.

## Frozen criterion and interpretation

Both scenarios are inconclusive under the 0.2 dB paired criterion. U reaches the grid floor at K=3, and all bootstrap replicates of the U K=10 crossing are left-censored. In G, the K=2 point estimate is 0.568 dB away from K=10 and K=5 is 0.068 dB away, but the K=2 paired 95% interval is [0.095, +infinity) dB. The point estimates therefore suggest some value from extra rounds, with limited precision about the depth needed for a 0.2 dB comparison. The reference is fixed K=10, a finite computational budget.

Pilot and refinement take 70.3% of the native F0 timing. Under fixed round counts and other component costs, removing all scalar-joint detection cost would save 38.69 ms per frame on this panel. Whether a learned schedule can accelerate the complete acquisition/refinement/decoding trajectory beyond classical early stopping remains untested. The screen uses the default constant damping .3.

See [the budget plot](frontier.png), [full per-budget metrics](summary.json), [timing rows](timing.jsonl), [run binding](provenance.json) and [checksums](SHA256SUMS). The original remote output is `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/f0_round_budget_20261118/out`.
