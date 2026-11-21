# Per-frame logloss versus the C1 MI threshold (post hoc)

Date: 2026-10-21. **Exploratory, post hoc, no pre-registered prediction or verdict.** Read-only on saved
rows; zero generator/SBL/receiver/decoder calls; nothing written on the server. Question raised by a
Gemini brainstorm: can the C1 code threshold `I* = .577` turn per-frame extrinsic logloss into a FER proxy?

## Coordinate and code check

| Item | C1 `I*` ([res-20261009-01](../../research-assets/res-20261009-01.md), `headroom_ladder_20261008/c1_t1_transfer.py`) | This pipeline (`fresh_cohort.py`, `gram_cohort.py`) | Same? |
|---|---|---|---|
| LDPC code | P1 context, `code_g_sha256 bfd42472…` (asserted in `headroom_ladder_20261008/driver.py`) | Same P1 loader (`p1ctx.load` → `p1_driver.load_context`; P1 configs record `bfd42472…`); not re-recorded in these outputs | Yes, by loader |
| Decoder | `decoder_messages(code, clip(LLR, ±20), maxiter=50)` | `decoder_messages(code, clip(extrinsic, ±20), maxiter=50)` | Yes |
| Quantity | `1 − logloss_bits(clip(LLR, ±20))`, bits | `bit_loss(extrinsic)` = mean `ln(1+e^{−sL})`, nats, **unclipped** | Units convert exactly, `I = 1 − L/ln 2`; clipping differs |
| Role / regime | Round-1 decoder input, ρ .5 | Stage-2 terminal detector extrinsic (decoder input), ρ .3 | Same role, different stage/regime |

`L_th = (1 − .577) ln 2 = .2932` nats. Rows store only the scalar logloss, so the clipped variant cannot be
recomputed; unclipped loss is ≥ clipped loss.

## Observation

All non-diagonal arms (the whole-Gram diagonal arms fail almost always and are excluded). AUC by
Mann–Whitney; 95% CI from 2000 frame-cluster bootstrap draws, seed 20261021.

| Cohort | Frame-arms | Fails | Frames | AUC [95% CI] | Fail, L ≤ L_th | Fail, L > L_th | Min failing L | Logistic L50 (I50) |
|---|---:|---:|---:|---|---:|---:|---:|---|
| `gram_cohort1` (old 200 keys; fixed/point/joint/full × 2 upstreams) | 1600 | 95 | 50 | .985 [.978, .991] | 2/1370 | 93/230 | .279 | .3333 nats (.519 bit) |
| `fresh_cohort1` (reserved 200 keys; 3 arms) | 600 | 6 | 50 | .996 [.989, 1.000] | 0/584 | 6/16 | .305 | .3205 nats (.538 bit), 6 events only |

Old-cohort failure rate by L bin: [0, .27) 0/1184; [.27, .29) 2/166; [.29, .31) 7/96; [.31, .33) 22/70;
[.33, .36) 34/50; [.36, .40) 19/23; ≥ .40 11/11.

## Reading (three layers)

1. Observation: per-frame logloss nearly separates decode failure (AUC ≈ .99 in both cohorts). Below
   `L_th` only 2/1954 frame-arms fail; above it about 40% fail.
2. Verdict: none. No prediction was registered; this cannot be cited as validating threshold universality
   for the stage-2 detector.
3. Untested explanations for the 50% point lying below `I*` (I50 ≈ .52 vs .577): unclipped LLRs inflate the
   loss of confident wrong bits (direction consistent; M); the stage-2 extrinsic distribution differs in shape
   from C1 round-1 inputs (M); ρ/stage difference (L).

Use: `L_th` behaves as a near-safe boundary, not as the 50% point. A tail-mass endpoint such as
"fraction of frames with L > L_th" has about 2.5× more events than FER here (230 vs 95; 16 vs 6), so it
could serve as a **pre-registered secondary** endpoint in a future FER confirmation. FER stays primary.
The quantity needs the true bits, so it is an evaluation metric, not a deployable statistic. The old
cohort is development data and may be used to fix the endpoint threshold before any prospective test.

## Limits

- Post hoc on cohorts already used repeatedly; arms share keys and frames (clustered by frame only).
- Clipping mismatch not resolvable from saved rows.
- One scenario family (U/G, ρ .3, 7/8 dB); fresh cohort has 6 failures, so its L50 is unstable.
- No claim about mainline F0+CSTATE frames, other SNR/ρ, or decoder iterations.

## Provenance

Script: [posthoc_logloss_mi.py](posthoc_logloss_mi.py), run as
`python -I - <root>` from stdin in the server AFDM env; output reproduced exactly on rerun.
Remote rows (not copied locally), root
`/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/`:

- `gram_cohort1/rows_shard000..011.jsonl`, 27,034,607 bytes, md5 cf9093a40873f498238d472e97c7aa99,
  6a3599987d0046a009fb6dc894fd6a31, 46e4c05f3c57132a690ca5b285d68e58, eb6dc9ba7dc715f807e737a32aca38ba,
  9b9d12a6bc1a363931bf08d7fff42d3e, dcf85e99dc989b690cf844c69a03ade9, 215b288c4a51cdbba994fd74529148f4,
  e4b3e2cc6630fe62c3f9be0c504bb736, 70cfb9a5985f14f2a4ca46db43ecc7d4, 0f8bdd0be7fcf320f0eef9ffda5738c2,
  7600bf685708342255389f8c2c8e5049, 0bd718a3345a1bc7b30688e57c157f9b.
- `fresh_cohort1/rows_shard000..011.jsonl`, 20,276,050 bytes, md5 f958550fa60a1e03f8c7c1a2586e5637,
  9aef84c60a8af1be079880c2c2eb8522, 984ab530c33c7caf31564c5668e4fe42, ee527130ffd6a51235250cf73142af58,
  dd5b755aa368acd33c4d47572f729d6c, 9075475062efb4ef80ca9e7919e88e56, 373399aa96f4fafdc5eb51c90dd18307,
  97ae951058e05d29f2f5022408167e61, 0a45fbd794703e44d72bef1688ce3576, 8b990fc74f3e8634c06a20564ad4fd60,
  3191d74f3e1160a983ee9454d22d613e, f2169537ae8006f0156641288a865d16.
