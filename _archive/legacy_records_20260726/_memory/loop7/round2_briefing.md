# Loop 7 — Round 2 briefing for Oracle GPT-5.4-pro (browser)

[Continuation of `loop7-phaseA-plan-review` — new session]

## Where we are

In Round 1 you scored the plan **5/10** with verdict "skip-to-writeup" (posterior 20-25% < my 30% no-go threshold). You approved a **cheap headroom probe** on Config A (N=1024 v=2 P=10 tau=10ms) as the only justified GPU spend, and gave fallback picks if I still proceeded: **Method 1 (C1+B1)**, 1000 paired frames at gate SNRs.

I ran the cheap probe, saw real headroom, and proceeded to train. I also did a complementary C1-alone retrain because your Round 1 ranking was C1B1 > C1 (I wanted both on the table). Results below. **I did not hit 1000-frame gate eval** — user mandated `--target-errors 150` adaptive stop, so I ran **200 frames at gate SNRs** instead of 1000. That compromise is on me; I accept it may cost McNemar power.

## Round-1 recommended probe — **confirmed large headroom** ✅

Config A classical BP-torch joint @ 100 frames, Perfect-CSI BP @ up to 1500 frames.

| SNR | classical BP-joint (P=10) | PCSI BP (P=10) | headroom ratio | P=8 fallback (paired 500f) |
|---|---|---|---|---|
| 5 | 1.948e-01 | 1.618e-01 | 1.20× | 1.901e-01 |
| 10 | 1.114e-01 | 6.45e-02 | 1.73× | 1.035e-01 |
| 15 | **4.70e-02** | 5.08e-03 | **9.25×** | 2.848e-02 |
| 20 | **9.43e-03** | **0** (0/3.072M bits) | ∞ | 3.255e-03 |
| 25 | **4.66e-03** | **0** (0/3.072M bits) | ∞ | 2.672e-03 |

So P=10 gave the exact headroom you predicted. Classical BP-joint is 9-10× above PCSI-BP at SNR=15 and essentially at a ~5e-3 estimation floor at SNR=20/25 while PCSI is at ~0. Waterfall monotone non-increasing, no cliffs, passes sanity rule #2.

## Training (short, user killed at iter~120 after seeing patience-wait pattern)

Both variants configured identically: `train_classical_joint_unrolled.py`, variant ∈ {C1, C1B1}, N=1024, v=2, P=10, tau=0.010, mp=bp, batch=4, phase0=5, phase1=100 (no scalars), phase2=200-300, eval-hard, checkpoint-score gate, cdtype=complex64. Best-ckpt at iter=49 for both variants; subsequent evals (iter=99, 149, ...) never improved — very noisy 20-frame in-training eval.

## Round-2 results — 200-frame paired McNemar at gate SNRs

### Variant C1B1 (your Round-1 top pick)

| SNR | classical | learned | Δ vs cls | McNemar n10/n01 | p (learned better) | verdict |
|---|---|---|---|---|---|---|
| 10 | 1.121e-01 | 1.125e-01 | **+0.38%** | 1344/1520 | 0.9995 | **stat-sig learned WORSE** |
| 15 | 4.609e-02 | 4.600e-02 | −0.20% | 683/646 | 0.155 | null |
| 20 | 8.799e-03 | 8.989e-03 | **+2.16%** | 408/486 | 0.996 | **stat-sig learned WORSE** |

### Variant C1 alone (Loop-6 architecture on new Config A)

| SNR | classical | learned | Δ vs cls | McNemar n10/n01 | p (learned better) | verdict |
|---|---|---|---|---|---|---|
| 10 | 1.121e-01 | 1.128e-01 | **+0.70%** | 1807/2127 | 1.000 | **stat-sig learned WORSE** |
| 15 | 4.609e-02 | 4.614e-02 | +0.10% | 970/988 | 0.658 | null |
| 20 | 8.799e-03 | 8.962e-03 | **+1.86%** | 527/594 | 0.977 | **stat-sig learned WORSE** |

### Full-SNR 30-frame paired (for waterfall only, low power at gates)

C1B1 non-gate:
- SNR=5:  +0.09% null
- SNR=25: −20.22% (p=4.5e-6) learned stat-sig better — *but* torch-ref drifts 13% below classical at SNR=25 at only 30 frames, so this is partly a drift artefact not a real gain.

## Loop-6 fallback (P=8, C1 alone, 500-frame adaptive) — unchanged

| SNR | classical | learned | Δ | McNemar p | verdict |
|---|---|---|---|---|---|
| 5 | 1.901e-01 | 1.903e-01 | +0.07% | 0.721 | null |
| 10 | 1.035e-01 | 1.033e-01 | −0.17% | 0.265 | null |
| 15 | 2.848e-02 | 2.824e-02 | **−0.86%** | **0.0013** | **stat-sig learned better** |
| 20 | 3.255e-03 | 3.353e-03 | +3.00% | 0.834 | null |
| 25 | 2.672e-03 | 2.903e-03 | +8.63% | 0.983 | null |

## Key observation — the head adds **noise**, not correction

At Config A:
- Classical H-est NMSE at SNR=20 = **−18.73 dB** (P=10, paired 200f)
- Learned H-est NMSE at SNR=20 = **−18.69 dB** (learned is 0.04 dB worse)
- i.e. the C1 off-support correction head **degrades** channel estimate on average at high SNR.

This contradicts my prior belief that C1 was architecturally sound. At P=8 the head was bit-exact-at-init and couldn't regress — at P=10 the head has more off-support atoms to choose from, and it's picking slightly wrong ones.

## Side-by-side: Loop-7 vs Loop-6 fallback at gates

| gate | Loop-6 fallback verdict | Loop-7 C1B1 verdict | Loop-7 C1 verdict |
|---|---|---|---|
| SNR=10 | null (−0.17%) | **stat-sig worse (+0.38%)** | **stat-sig worse (+0.70%)** |
| SNR=15 | **stat-sig better (−0.86%)** | null (−0.20%) | null (+0.10%) |
| SNR=20 | null (+3.00%) | **stat-sig worse (+2.16%)** | **stat-sig worse (+1.86%)** |

**Loop-6 fallback is strictly better than Loop-7** at every gate: where fallback wins (15), Loop-7 is null; where fallback is null (10, 20), Loop-7 is stat-sig worse.

## Waterfall sanity (rules #2, #4)

- Config A classical waterfall: monotone (1.95e-1 → 1.11e-1 → 4.70e-2 → 9.43e-3 → 4.66e-3). ✅
- No cliff > 10× between adjacent points (5→10: 1.75×, 10→15: 2.37×, 15→20: 4.98×, 20→25: 2.02×). ✅
- Learned below PCSI-BP upper bound at every SNR (learned 9e-3 > PCSI 0 at SNR=20). ✅
- Classical ≡ torch-ref bit-exact at SNR=5/10/15; ≤ 1% drift at SNR=20; ≤ 13% drift at SNR=25 (30-frame only, vanishes at 200 frames).

Fig: `figures/loop7/loop7_ber_mse.png` (2-panel BER + NMSE for C1B1 paired eval).

## Questions for Round 2

1. **Final verdict**: given that Loop-6 fallback strictly beats Loop-7 C1 and C1B1 at every gate, do I:
   - (a) ship Loop-6 fallback as the headline result and write Loop-7 as "P=10 headroom exists but C1-family heads cannot capture it" (negative result section), or
   - (b) try one more variant (B2 detector-side selector / B3 channel-tap corrector / scalar S-lam lamba_ls only) before closing?

2. **Structural diagnosis**: the fact that both C1 and C1B1 REGRESS at SNR=10/20 despite 9-∞× headroom tells me something specific. Is the remaining error at classical P=10 primarily:
   - (A) support selection error (OMP picks wrong atoms) — C1 off-support can't help because wrong support ≠ off-support,
   - (B) amplitude/phase error on the *correct* support — B3-style corrector might help, or
   - (C) noise-limited detector error that no channel-side head can fix?

3. **Score this Round 2**: 1-10, with "1 = abandon project" and "10 = submit as-is".

4. **If (b)**: pick ONE variant (S-lam, B2, B3, B1B3) and a specific training recipe. Expected time budget: 1 GPU-hour + 30 min eval.

5. **Logging**: I did print config at top of every stdout (`[LOOP5_CONFIG] variant=... N=1024 v=2.0 P=10 tau=10.00ms ...`). Sidecar JSON is in each `outputs_loop7_*/results.json`. Did I miss anything from your Round-1 logging checklist?

6. **McNemar power**: at 200 frames I had n10+n01 ≈ 900-4000 discordants at gates. Was that sufficient, or am I seeing a shadow of low-power false-null at SNR=15?

Please be honest. If the answer is "ship fallback", say so — I would rather write a short honest paper than keep grinding a dead architecture.
