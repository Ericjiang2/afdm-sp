# Round 1 Rebuttal

The author requests adjudication on three weaknesses. Verifiable facts only,
each backed by a file path / numerical reconstruction.

## Rebuttal #1 — W1 ("4B headline unreproducible from repo files") — REJECT

The headline -37.7 / -40.2 / -37.6 % at SNR = 20 / 25 / 30 dB pools three independent FYP-era 4B-pooled JSONs that ARE committed:

```
outputs_loop12_r3_official/results.json        : seed_block A (f=200/225/500)
outputs_loop12_seed2_s20_s25_s30/results.json  : seed_block B (f=250/322/500)
outputs_loop12_matched_f2p_s20_30/results.json : seed_block C (f=150/226/300)
```

Pooled re-derivation, computed by `python3 -c "..."` in the repo root:

| SNR | sum_frames | sum_cls_errs | sum_lrn_errs | pooled rel-Δ | paper Table |
|---|---|---|---|---|---|
| 20 | **600**  | 3 686 | 2 295 | **−37.74 %** | −37.7 % ✓ |
| 25 | **773**  | 2 209 | 1 322 | **−40.15 %** | −40.2 % ✓ |
| 30 | **1 300** | 1 160 |   724 | **−37.59 %** | −37.6 % ✓ |

The headline reproduces to displayed precision in all three cells. The reviewer
mistakenly cited the *post-FYP* listwise / threshold-gate JSONs (which use a
different deployment recipe and a single 100-frame eval block) as if they were
the pool source.

**Residual concern accepted**: there is no committed `aggregate_loop12_3seed_pool.py`
that runs the pooling in one command. That is a *reproducibility-script* gap,
not a *data-existence* gap, and the minimum fix is a 30-line aggregator
script + a sentence in §III pointing to it. **Revise W1, do not sustain.**

## Rebuttal #2 — W3 ("≈ 8 % MAC overhead disagrees with wall-clock") — PARTIALLY ACCEPT

The "≈ 8 %" is an *analytical-MAC* count: 1.5 M MAC / 18.6 M MAC = 8.06 %, where
both numerator and denominator are the per-frame complex-MAC totals computed in
`profiling/analytical_macs.py`. The wall-clock numbers in `runtime_table.md`
(learned 402 ms vs classical-torch 416 ms at N = 1024; +3.9 % at N = 2048) are
consistent with the analytical-MAC overhead being *masked* by Python / Torch
launch overhead, FFT-batch fusion, and OMP main-loop residual-update inefficiency
in the classical-torch reference. The two numbers are not *in conflict*; they are
in *different units* and probe different bottlenecks.

**Accepted change**: the abstract should rename the headline from
"≈ 8 % additional per-frame complex-MAC overhead" to "≈ 8 % additional
analytical complex-MAC overhead, with measured wall-clock parity at N=1024 and
+3.9 % at N=2048" so the two regimes are jointly disclosed. **Revise W3, do not
sustain.**

## Rebuttal #3 — W5 ("prior art on learned OMP is thin") — REJECT IN PART

The Section 1.2 literature survey already cites the deep-unfolding line via
Monga et al. (`monga2021unrolling`), the Diagonal Reconstruction CE for AFDM line
via Yin et al. (`yin2024drceafdm`), the SP-AFDM iterative CE+SD line via Zheng
et al. (`qing2024spafdm`), and the GI-free pilot iterative line via Zhou et al.
(`zhao2024gifreeafdm`) — that is four distinct learned-or-iterative receiver
references inside the AFDM family.

**Accepted residual**: the *non-AFDM* learned-OMP / approximate-message-passing
line (LISTA, AMP-net, Borgerding) is missing. Three citations + two prose lines
in §1.2 close it. **Revise W5: agreed but narrow scope.**

## Weaknesses NOT rebutted (accepted in full)

W2, W4, W6, W7, W8 are accepted as written. Particularly:

- W2 (listwise envelope = single eval seed) is a real reporting bug; the "5-seed
  envelope" wording must be replaced with "5 training seeds, single-eval-seed
  deployment band".
- W4 (title still says "low-complexity") is the same hangover from FYP R3.
- W7 (qing baseline not yet threaded into Section 3) is the right Round-2 priority.
