# Native tensor-free joint SP-AFDM: direction validation

**Verdict: supported.** This is fresh direction-validation evidence, not statistical equivalence or publication-level confirmation. Numerical source remained frozen at `2d130b4d`, baseline `31d5ec0d`, runner `beb5ab73`. No receiver redesign, damping/iteration change, SNR search or additional sample allocation.

## Paired results by SNR

Each cell contains32 fresh independent observations, paired across TF_J20_R2 and EP2_MEAN_R2. Seed namespace940318; previous development frames were not reused. FE and information errors below are unrestricted final decisions. A rescue is EP wrong/TF correct; a harm is TF wrong/EP correct. Latency includes all online receiver work, including initialization, refits, decoding and saved-checkpoint hooks.

| SNR dB | FE TF / EP2 (n=32) | Info errors TF / EP2 (32768 bits each) | Rescues / harms | Median TF / EP2 s | p90 TF / EP2 s | Median / p90 ratio |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 6 / 9 | 481 / 889 | 3 / 0 | 0.2955 / 0.5013 | 0.3128 / 0.7081 | 0.590 / 0.442 |
| 6.5 | 1 / 6 | 97 / 396 | 5 / 0 | 0.2969 / 0.5018 | 0.3176 / 0.6711 | 0.592 / 0.473 |
| 7 | 1 / 1 | 148 / 175 | 0 / 0 | 0.2946 / 0.5031 | 0.3068 / 0.6869 | 0.586 / 0.447 |

All three cells remain in the decision; no favorable cell was selected afterward. Prospective support required median ratio≤0.75 and p90≤1 in every cell, at least2 error-informative cells, no numerical failures, and no predefined material reliability penalty. These are engineering criteria, not equivalence margins.

Observed: 3 informative cells; 0 numerical failures across all arms; net harms per cell {'600': -3, '650': -5, '700': 0}; material information-bit penalty cells [].

| SNR dB | Conservative ≥95% interval for FER_EP2−FER_TF | Mean channel NMSE TF / EP2 |
|---:|---:|---:|
| 6 | [-0.1128, 0.2738] | 0.010994 / 0.018830 |
| 6.5 | [-0.0838, 0.3526] | 0.011131 / 0.015241 |
| 7 | [-0.1280, 0.1280] | 0.009715 / 0.011379 |

Intervals use paired frame outcomes and the prospectively retained conservative exact-binomial construction. NMSE is diagnostic. Full BER, latency CDF, auxiliary old-D results and raw counts are retained in the summary/ledger. The oldD=0.678048s does not drive this verdict.

## Predefined controls

EP4 and POINT use first8 frames per cell; PBi uses first4. Every row below compares exactly the same observations. Rescues/harms favor TF relative to the named control.

| SNR dB | Control | n | FE TF / control | Rescues / harms | Median TF / control s |
|---:|---|---:|---:|---:|---:|
| 6 | EP4_MEAN_R2 | 8 | 2 / 2 | 0 / 0 | 0.2995 / 0.7895 |
| 6 | PBI8_SOFT_R2 | 4 | 0 / 2 | 2 / 0 | 0.2972 / 14.5769 |
| 6 | TF_POINT20_R2 | 8 | 2 / 2 | 0 / 0 | 0.2995 / 0.3037 |
| 6.5 | EP4_MEAN_R2 | 8 | 1 / 1 | 0 / 0 | 0.3045 / 0.9952 |
| 6.5 | PBI8_SOFT_R2 | 4 | 1 / 3 | 2 / 0 | 0.3118 / 14.5519 |
| 6.5 | TF_POINT20_R2 | 8 | 1 / 1 | 0 / 0 | 0.3045 / 0.3068 |
| 7 | EP4_MEAN_R2 | 8 | 0 / 0 | 0 / 0 | 0.3017 / 0.7271 |
| 7 | PBI8_SOFT_R2 | 4 | 0 / 0 | 0 / 0 | 0.3082 / 14.4496 |
| 7 | TF_POINT20_R2 | 8 | 0 / 0 | 0 / 0 | 0.3017 / 0.2985 |

EP4 matches TF frame-error outcomes on all three eight-frame subsets, while costing roughly2.4–3.3× their matched-subset median latency; at6.5dB it improves on EP2 (1/8 versus4/8). It remains a meaningful stronger-accuracy control, but does not remove the observed TF speed advantage. POINT also matches TF frame-error outcomes on all24 paired control frames, with similar runtime: POINT information errors are178/122/0 versus matched TF155/97/0 at6/6.5/7dB. Gain-variance propagation still has no demonstrated independent benefit on frame reliability; this does not prove message/BER equivalence or justify relabeling the primary. PBi is slower by roughly47–49× median on matched four-frame subsets, with FE2/4,3/4,0/4 versus TF0/4,1/4,0/4. It did not explain the apparent gain in this small predefined subset.

## Decision and minimum next step

**Supported as a research direction.** Median latency is consistently about59% of practical EP2 across all3 prospectively fixed cells, p90 about44–47%; information errors are lower in each cell, with8 paired rescues and0 harms overall. This is repeatable engineering evidence for a latency–reliability tradeoff worth studying. The conservative cellwise uncertainty intervals still include zero; no statistical equivalence or general accuracy superiority is established.

**Minimum next step:** use the saved traces and POINT comparison to sharpen the mechanism/contribution: joint gain-mean adaptation and efficient inference versus the unproven benefit of propagated gain variance. No additional grid is needed for this direction decision. Keep EP2 and EP4 as practical and stronger-accuracy controls; do not launch confirmation or change the frozen primary without a separately defined next task.

## Evidence and cost

252 measured calls on96 independent observations. Numerical failures and missing decisions are retained, not silently replaced. Per-frame inputs/truth, seed descriptors, configs, source hashes, decoded bits/LLRs, compact physical paths, timings and diagnostics remain available for recount. Heavy arrays are limited to frame0 of each SNR and exceptional failures.

One changed-orchestration check preceded launch; old numerical qualification was reused. Final recount and transfer receipts are recorded alongside this report. Remote evidence root: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_native_direction_20260921/`. The single-process CPU run started2026-09-21 11:59:08UTC. No confirmation job was launched.

Actual cost: measured receiver calls283.601s; numerical process wall356.20s (5.94min); warmup16.195s; frame generation34.911s; scoring/storage5.476s. Categories are not an exhaustive wall-time identity. Peak RSS1,135,104KiB (~1.08GiB) is the shared sequential process, not an isolated per-arm peak. Remote989-artifact inventory totals53,847,372bytes (51.35MiB). All504 checkpoints passed independent information/coded-error and syndrome recount. Local summary/recount/manifest/ledger/completion/inventory hashes match remote copies; final process check found no related Python or tmux job. Raw data remain remote, indexed by `stage_D_artifact_inventory.sha256`.
