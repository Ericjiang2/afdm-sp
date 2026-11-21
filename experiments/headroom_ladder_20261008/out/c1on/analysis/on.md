# T1-T3: online-scheduling headroom and scalar-state sufficiency (6.5 dB, rho .3, frames 0-299)

Frames 300; cost = quiet timing reference t_cum by (T, L, round); secondary unit = inner updates r*T.

## T1 oracle headroom (matched-FER oracle vs best fixed schedule with syndrome early stop)

| L | K | best fixed (T, Rc) | FER | cost s | oracle cost s | S1 [95% CI] | S1 (own FER) | S1 (unit r*T) |
|---|---|---|---|---|---|---|---|---|
| 16 | 128 | T40, R7 | 0.097 | 0.698 | 0.463 | 0.337 [0.282, 0.377] | 0.310 | 0.460 |
| 20 | 160 | not operable (no member with FER <= 0.1) | | | | | | |
| 24 | 192 | not operable (no member with FER <= 0.1) | | | | | | |
| 28 | 224 | not operable (no member with FER <= 0.1) | | | | | | |
| 32 | 256 | not operable (no member with FER <= 0.1) | | | | | | |

**T1 decision: go to T2 (headroom >= .15 at L [16])**

## T2 deployable give-up rule (select on frames 0-149, evaluate on 150-299)

| L | base | rule (r_g, theta) | dev saving / dFER | test saving / dFER | AUC syn_r (r=1..4) |
|---|---|---|---|---|---|
| 16 | T40, R7 | (1, 264) | 0.158 / +0.007 | 0.111 / +0.000 | 0.96 0.96 0.96 0.98 |

**T2 decision: A-first**

## T3 scalar-state sufficiency (held-out log-loss, nats; Delta = LL(M0) - LL(M1))

| T | fold (train -> test) | n test | LL M0 | LL M1 | Delta | drop-one increase (dI / round / syn) |
|---|---|---|---|---|---|---|
| 20 | A | 4603 | 0.0706 | 0.0365 | +0.0341 | +0.0021 / +0.0207 / +0.0038 |
| 20 | B | 4701 | 0.0842 | 0.0380 | +0.0462 | +0.0030 / +0.0337 / +0.0038 |
| 40 | A | 3678 | 0.1135 | 0.0766 | +0.0368 | +0.0039 / +0.0361 / +0.0013 |
| 40 | B | 3851 | 0.1158 | 0.0892 | +0.0266 | -0.0003 / +0.0266 / +0.0061 |

**T3 decision: scalar state insufficient (A needs >= 2 states)**

