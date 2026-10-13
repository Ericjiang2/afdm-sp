# Oracle Round 1 — Loop 9 plan pick (gpt-5.4-pro / browser manual)

Session slug: `loop9-r1-plan-retry`
Elapsed: 16m41s
Date: 2026-04-22
Files attached: 9

## Verdict at a glance

- **Pick: `C2-rel` (4th option, cleaner than E1/E2/E3)** — candidate-active **relation** head.
- **Fallback pick from original list: E2, stripped down** (candidate↔active relations only, NO candidate-candidate self-attention — "extra variance you do not need").
- **Score: 8/10. GO — hard-gated support-repair round.**
- **Posterior of win**: **0.30 blind, 0.48 if micro-gate clears both relative and absolute thresholds.**

## Q1 — Implementation recipe (C2-rel)

### Interface point
Insert **ONCE at `t==0`**, immediately AFTER `omp_sparse_torch(...)` returns `support_idx` / first LS gains and BEFORE `expand_cluster_support(...)`.

Use **raw OMP support** `S_omp` (not cluster-expanded) for the relation block.

Do **NOT** reuse C1's late `t>=1` post-DA-LS residual input — "that late signal is exactly what Loop 8 showed is near-empty".

### Action
1. Build candidate set = top-`M=48` off-support atoms by **pre-LS pilot MF** `|Φ^H y|`.
2. Score each candidate `j` with relation MLP.
3. Add up to `K_add_max=4` candidates whose logit > 0.
4. Pilot-only LS on the union `S_omp ∪ A`.
5. **Prune back to `P`** atoms (keep top-|gain|).
6. Re-fit LS on pruned support.
7. Continue the existing classical path unchanged (expand_cluster_support, DA-LS, BP).

### Features

**Candidate-local (7-dim)** `u_j`:
```
u_j = [
  log|phi_j^H y|,
  margin_to_Pth_OMP_pick,   # relative margin vs OMP's last pick
  l_j / l_max,
  k_j / k_max,
  d_l_nn / l_max,            # nearest-active delay distance
  d_k_nn / k_max,            # nearest-active Doppler distance
  log sigma2
]
```

**Pair-to-active (6-dim)** `v_{j,s}` for each `s ∈ S_omp`:
```
v_{j,s} = [
  coh_js,
  log(|alpha_s| * coh_js + eps),
  Δl_js / l_max,
  Δk_js / k_max,
  1{|Δl|=0},
  1{|Δk|<=2}
]
```
where `coh_js = |a_j^H a_s| / (||a_j|| ||a_s||)`.

### Architecture

```
pair MLP:    6 -> 16 -> 16, SiLU
pool over s: max-pool(16) + mean-pool(16)          -> 32-dim
concat:      [u_j (7), max_pool (16), mean_pool (16)] = 39-dim
scorer MLP:  39 -> 16 -> 1, SiLU
```

**Identity-at-init:**
- Zero-init final linear weights of scorer
- Final bias = **−8**
- Inference rule: add only candidates with logit > 0, cap at 4

Params: a few thousand. Pair work: `M * |S_omp|` ≈ `48 * 10` per frame.

**No transformer block, no CNN, no dictionary extension.**

### Training

- Cached supervised training.
- Labels: `y_j = 1` iff `j ∈ (S_oracle \ S_omp)`.
- Loss: `L = BCE_miss + 0.5 * rank_loss(pos > hard_neg)`.
- SNR weights: `10/15/20 → 0.2 / 0.4 / 0.4`.
- Frame weight `×2` if classical frame BER > 0.
- Cache size: `60k` frames, mix `1:2:2` over `10/15/20`.
- AdamW, `lr=1e-3`, `wd=1e-4`, batch `512`, `4 epochs`.
- Early-stop after 2 flat val evals.
- Freeze the trained head for BER evaluation; **only if it wins held-out BER at 15+20 with non-regress at 10**, consider optional one-epoch online tune.

## Q2 — Micro-verify gate

Adapt `loop8_diagnose.py`. Cache ~250 paired frames per gate SNR with same seeds.

Build `M=48` candidate set + relation features per frame. Labels as above.

Fit **L2 logistic regression** on a train split of cached candidates; rank candidates on held-out frames.

`recall@K_add` computed exactly the Loop-8 way, but substitute proxy probabilities for residual-MF scores.

### Hard pass thresholds (both SNR=15 AND SNR=20)

- **Relative**: `recall_proxy@K / recall_resMF@K >= 2.0` for `K ∈ {2, 4, 6}`.
- **Absolute**: `recall_proxy@6 >= 0.10` at SNR=15 dB AND `>= 0.12` at SNR=20 dB.
- **Frame-level**: `hit_any@6 >= 0.35` at 15 dB AND `>= 0.45` at 20 dB.

If relative ratio passes but absolute floors fail → **STOP**.

## Q3 — Posterior

- **0.30 blind** (before micro-gate).
- **0.48** if micro-gate clears both the relative AND absolute thresholds.

Reasoning: support is 100% of channel-side gap at 20 dB and 60% at 15 dB, but only 14% at 10 dB. Win at 15+20 is feasible while SNR=10 stays null unless adds are tightly suppressed. **This posterior is inference from Loop 8 diagnostics, not a measured result.**

## Q4 — Sanity / stop rules

1. **No training** if the proxy gate fails any `K` or any absolute floor.
2. **No 500f McNemar** until one frozen checkpoint shows held-out `1000f/gate` BER improvement at both 15 and 20 with `10 dB ≤ +3%` relative regression AND normal BER/MSE waterfalls.
3. Reject any checkpoint with non-monotone waterfall or above-PCSI behavior.
4. Run **exactly one** official paired 500f significance eval after checkpoint lock.
5. If the best cached-trained head only wins on one bad-frame slice and not on a second disjoint `1000f/gate` eval → stop the round.

## Q5 — Score / decision

- **Score: 8/10**
- **GO — hard-gated support-repair round.** C2-rel is structurally aligned with the Loop-8 diagnosis (uses the actually-unused signals: coherence, pre-LS pilot MF, pair geometry) and keeps complexity within budget.
