# Claude main code review (2026-10-13) — scope split with Codex KR (codex-kernel-review-20261013.md)

Split (no duplication): Claude = Sonnet's driver --shuffle-arms change + c1e_predict.k_cross (Kc estimator). Codex KR = core
receiver kernel (dpss_rx.scalar_joint_cols / vector_prior / Design / refit, tapchannel, GenieRefine, IntervenedRefine).

## driver_c1esc.py --shuffle-arms (Sonnet, uncommitted diff, 27+/4-)
- Default off: order = arms as given, no extra row fields -> rows unchanged. results_shard JSON gains loadavg_start/end
  (not part of _config; merge unaffected). OK.
- Order stream: SeedSequence(entropy_words + [0x41505242 'APRB', frame, L]) — separate domain from channel/message/noise
  streams (C1_DOMAIN components). OK.
- arm_rank: `extra` dict mutated per arm but unpacked into a new row dict at append time -> each row gets its own rank. OK.
- Resume (c1i.load_done by arm set) unaffected. Numeric order-independence: per-arm refiner and monkeypatch restored per arm;
  caches (_BASIS, frozen modules) deterministic -> expected bit-identical; Sonnet's smoke closure (E10/E0 vs stored rows) confirms.
Verdict: correct; no change requested.

## c1e_predict.k_cross (Kc = first FER = .5 crossing, linear in K)
- Interpolation algebra correct for both directions; ties at exactly .5 handled consistently with kc_cens censoring.
- Latent issue (minor): returns the FIRST crossing in EITHER direction. A non-monotone curve that starts >= .5 and dips below
  (e.g. .55, .45, .80) yields a downward "cliff" and underestimates Kc. Check on stored X1/IB2 curves (rt.json): 72 curves,
  33 non-monotone, 0 point estimates change under an upward-only rule -> reported Kc values unaffected. Bootstrap CIs at
  lower-edge cells (e.g. 6.5 dB rho .5) could be affected; not used by run (b).
- Recommendation for future A gates: upward-only crossing on an isotonic (monotone) fit of FER(K), stated in the protocol.

## Codex KR outcome (codex-kernel-review-20261013.md) and Claude spot-check
- 0 critical; flat arm (SPg_flat, all C1 flat results incl. IB/IB2/X1/X2/T1-T3/A') = algebraically the frozen update (P = K);
  bit-exactness not proven. No result invalidated.
- Major M1 (scoped): the scalar contraction sum(vh)*||x||^2/N and shared gain precision assume unit-modulus path columns;
  DPSS columns have energy beta_d = sum_k N v_d[k]^2 |x_t[k-l]|^2 != ||x||^2 per realisation. This approximation is inherited
  by the frozen kernel when run on DPSS columns, so all DPSS arms (flat included) are measurements of this specific
  scalar-approximate receiver; do not call it exact (vector) AMP. Idea noted: a column-energy-aware precision is a small,
  principled receiver fix (candidate method item; not tested).
- Major M2 (latent): TapChannel.apply/adjoint/tap_matrix ignore ch.gains. Claude spot-check: only non-test callers driver_m1
  (explicit_misfit_taps) and driver_c1r2 (r_mis) build channels via make_tap_channel (full tap sequences, gains = 1) -> correct;
  the detector uses TimePathOps with gains. No existing result affected.
- Minor m1 (trace gain_variance semantics), m2 (record_states dropped by the vector router -> KeyError if requested).
- Fixes deferred until after run (b): changing tapchannel.py / dpss_rx.py now would change code md5s during the campaign.
  Follow-up list: (1) TapChannel coef *= gains (+ conj in adjoint) with the Codex unit test; (2) router rejects record_states=True
  explicitly; (3) document the scalar-approximate kernel in methods text; (4) optional column-energy-aware variant as a
  separate, pre-registered receiver arm.
