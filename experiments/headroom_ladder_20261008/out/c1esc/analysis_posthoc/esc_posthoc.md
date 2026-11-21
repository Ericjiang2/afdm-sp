# POST HOC (matched-reliability selection; not a decision input) -- A' escalation test: start T20, escalate to T40 if not decoded by round e (6.5 dB, rho .3, frames 0-599)

Rows 6000 (error rows 0). Dev frames 0-299, test 300-599.

Closure vs stored rows: E10 600 pairs, 0 mismatching; E0 600 pairs, 0 mismatching

## L16 (K 128), delta 0.1 -- PRIMARY

[sec] B* = E0 Rc7

| online policy (selected on dev) | P* | test cost base -> P* | test FER base -> P* | S [95% CI] | d [95% CI] |
|---|---|---|---|---|---|
| all | E3 Rc10 giveup(r2, syn>284) | 0.671 -> 0.496 | 0.073 -> 0.100 | 0.261 [0.215, 0.307] | +0.027 [+0.007, +0.050] |
| escalation_only | E2 Rc8 | 0.671 -> 0.606 | 0.073 -> 0.067 | 0.096 [0.075, 0.119] | -0.007 [-0.017, +0.000] |
| giveup_only | E0 Rc7 giveup(r1, syn>264) | 0.671 -> 0.585 | 0.073 -> 0.100 | 0.128 [0.077, 0.180] | +0.027 [+0.010, +0.047] |

Measured-time saving of P*(all) on test (run t_cum, load-noisy, report-only): 0.301
Oracle headroom vs B* on all 600 frames (matched FER, reference): 0.349

[updates] B* = E0 Rc7

| online policy (selected on dev) | P* | test cost base -> P* | test FER base -> P* | S [95% CI] | d [95% CI] |
|---|---|---|---|---|---|
| all | E3 Rc10 giveup(r2, syn>284) | 101.867 -> 61.200 | 0.073 -> 0.100 | 0.399 [0.348, 0.448] | +0.027 [+0.007, +0.047] |
| escalation_only | E3 Rc9 | 101.867 -> 79.400 | 0.073 -> 0.063 | 0.221 [0.189, 0.255] | -0.010 [-0.023, +0.000] |
| giveup_only | E0 Rc7 giveup(r1, syn>264) | 101.867 -> 86.800 | 0.073 -> 0.100 | 0.148 [0.093, 0.204] | +0.027 [+0.010, +0.047] |

**PRIMARY decision (L16, delta 0.1): A' NOT viable -> demote to remark; direction A only** (S = 0.261 [0.215, 0.307], d = +0.027)

## L20 (K 160), delta 0.2 -- report-only

[sec] B* = E0 Rc6

| online policy (selected on dev) | P* | test cost base -> P* | test FER base -> P* | S [95% CI] | d [95% CI] |
|---|---|---|---|---|---|
| all | E3 Rc9 giveup(r2, syn>306) | 0.993 -> 0.768 | 0.200 -> 0.190 | 0.226 [0.179, 0.276] | -0.010 [-0.030, +0.013] |
| escalation_only | E2 Rc7 | 0.993 -> 0.951 | 0.200 -> 0.170 | 0.042 [0.025, 0.059] | -0.030 [-0.050, -0.013] |
| giveup_only | E0 Rc7 giveup(r1, syn>280) | 0.993 -> 0.902 | 0.200 -> 0.183 | 0.092 [0.048, 0.134] | -0.017 [-0.037, +0.000] |

Measured-time saving of P*(all) on test (run t_cum, load-noisy, report-only): 0.292
Oracle headroom vs B* on all 600 frames (matched FER, reference): 0.413

[updates] B* = E0 Rc6

| online policy (selected on dev) | P* | test cost base -> P* | test FER base -> P* | S [95% CI] | d [95% CI] |
|---|---|---|---|---|---|
| all | E3 Rc9 giveup(r2, syn>306) | 133.067 -> 88.333 | 0.200 -> 0.190 | 0.336 [0.285, 0.386] | -0.010 [-0.033, +0.013] |
| escalation_only | E2 Rc7 | 133.067 -> 117.933 | 0.200 -> 0.170 | 0.114 [0.096, 0.134] | -0.030 [-0.050, -0.013] |
| giveup_only | E0 Rc7 giveup(r1, syn>280) | 133.067 -> 119.600 | 0.200 -> 0.183 | 0.101 [0.055, 0.151] | -0.017 [-0.033, +0.000] |

