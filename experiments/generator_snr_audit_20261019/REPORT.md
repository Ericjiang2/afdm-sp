# Generator and SNR audit

**No scientific BLOCKER or MAJOR.** The frozen run completed normally; independent physical propagation matched all 450 checked frames.

| Severity | Finding |
|---|---|
| BLOCKER | 0 |
| MAJOR | 0 |
| MINOR | The brief’s “Jakes-4 rays per tap” means `1+Poisson(3)`, mean four. Observed mean 4.0045, maximum 12 rays/tap; the frozen E2 protocol and accepted card already state the law correctly. |
| OK | A numerical and B1–B4 completed; no wrong operator, power split, systematic SNR offset or claimed-frame-sharing failure was detected. |

Finding sources: `e2_channels.py:84` under `experiments/tf_cstate_e2_20261017/`; its `PROTOCOL.md:50`; `research-assets/res-20261017-02.md:37`; task `codex-brief.md:39`.

Freeze: `b1fc64d0`. Status: `DONE exit=0`. CPU: 206.19 seconds (0.0573 core-hours; cap 6). One run; no execution fixes. Report commit is handled by the orchestrator.

## Frozen numerical verdicts

| Check | Sample / result | Frozen verdict |
|---|---|---|
| B1 P1/U | 200 frames; maximum relative error 8.711e-13; operator-power error 4.441e-16 | OK (limits 1e-10 / 1e-9) |
| B1 P1/G | 200 frames; maximum relative error 8.892e-13; operator-power error 4.441e-16 | OK (limits 1e-10 / 1e-9) |
| B1 C/J4 | 50 frames; maximum relative error 8.922e-13; operator-power error 6.661e-16 | OK (limits 1e-10 / 1e-9) |
| B2 U/G/S | 2000 draws each; 20000 independent reference draws per law | OK |
| B2 C | 2000 geometries; mean 4.0045 rays/tap | OK |
| B2 multiplicity | 140 tests; 0 Holm rejections at alpha=.01; minimum raw p=.009190, minimum adjusted p=1 | OK |
| B3 D1/D2/A1 | Maximum delay 102 (U/G), 25 (S); delta_f=15.625 Hz; maximum path-power error 6.66e-16 | OK |
| B3 sharing/determinism | P1: 100 U/G cases, 50 cross-scenario pairs; C: 50 frames; S: 100 rho-cases; EP/SP: 50 shared channel/noise frames; archived/current P1 default path identical | OK |
| A noise coordinates | Maximum physical/internal SNR difference 1.93e-15 dB | OK |

Operator and invariant evidence: `audit.py:221`, `audit.py:296`; independent implementation: `independent.py:29`. The documented positive Doppler sign matched; no alternate sign was needed.

| Scenario | Draws | First-draw rejection | 99% binomial interval | Independent reference | Historical estimate |
|---|---:|---:|---:|---:|---:|
| U | 2000 | 49.70% | 46.80–52.60% | 48.50% | 48.6% |
| G | 2000 | 49.70% | 46.80–52.60% | 48.58% | 48.6% |
| S | 2000 | 59.50% | 56.63–62.33% | 58.04% | 58.2% |

All historical-rate comparisons met the frozen three-standard-error diagnostic. S used the registered exponential mean `0.0008*(25/102)` seconds and truncation at 25. Distribution-test evidence: `audit.py:123`.

## SNR and energy

The common axis is `sigma2=10^(-SNR/10)` relative to unit nominal total pilot-plus-data energy before the channel. The 15-row [definition table](definitions.md) covers every requested receiver/comparison; full configuration, individual tests and numerical summaries are in [report.json](report.json).

At physical rho=.3, division by `sqrt(1.4)=1.1832159566` gives internal data power .5, pilot power .2142857143 and noise variance `sigma2/1.4`; the SNR offset is zero. P2b uses LDPC n=1530, k=767 versus SP n=2048, k=1024, on the same nominal total-energy SNR axis. These definitions match the checked generator and receiver inputs (`headroom_ladder_20261008/driver.py:227`, `tcom_reference_frame_20261015/ep_rx.py:74`).

Each entry below pools the measured per-frame energies; powers are per useful complex sample. E1 uses actual triggered keys at 4.5 dB; the other samples use their registered frame ranges and grid points. All groups have at least 50 distinct frames (`audit.py:279`, `audit.py:296`).

| Family / scenario / rho | n | Pilot / data TX | Combined TX | Noiseless RX | Noise | Nominal dB | Empirical dB | Data-only dB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E1 / G / 0.3 | 100 | 0.3 / 0.7 | 0.99926 | 0.99447 | 0.35690 | 4.5 | 4.451 | 2.910 |
| E1 / G / 0.5 | 100 | 0.5 / 0.5 | 0.99679 | 0.99243 | 0.35573 | 4.5 | 4.456 | 1.454 |
| E1 / U / 0.3 | 100 | 0.3 / 0.7 | 1.00046 | 0.99737 | 0.35624 | 4.5 | 4.471 | 2.924 |
| E1 / U / 0.5 | 100 | 0.5 / 0.5 | 1.00166 | 0.99516 | 0.35593 | 4.5 | 4.465 | 1.478 |
| E2-C / J4 / 0.3 | 50 | 0.3 / 0.7 | 1.00144 | 1.00357 | 0.25102 | 6.0 | 6.018 | 4.470 |
| E2-C / J4 / 0.5 | 50 | 0.5 / 0.5 | 1.00158 | 1.00295 | 0.15838 | 8.0 | 8.016 | 5.009 |
| E2-R / G / 0.3 | 50 | 0.3 / 0.7 | 0.99941 | 0.99324 | 0.25250 | 6.0 | 5.948 | 4.395 |
| E2-R / G / 0.5 | 50 | 0.5 / 0.5 | 0.99936 | 0.99453 | 0.25250 | 6.0 | 5.954 | 2.934 |
| E2-R / U / 0.3 | 50 | 0.3 / 0.7 | 0.99941 | 0.99610 | 0.25250 | 6.0 | 5.960 | 4.408 |
| E2-R / U / 0.5 | 50 | 0.5 / 0.5 | 0.99936 | 0.99747 | 0.25250 | 6.0 | 5.966 | 2.947 |
| E3 / G / 0.5 | 50 | 0.5 / 0.5 | 1.00179 | 1.00074 | 0.24942 | 6.0 | 6.034 | 3.018 |
| E3 / U / 0.5 | 50 | 0.5 / 0.5 | 1.00179 | 1.00570 | 0.24942 | 6.0 | 6.055 | 3.030 |
| E3/E3b/E3c/GSO / G / 0.3 | 50 | 0.3 / 0.7 | 1.00164 | 1.00067 | 0.24942 | 6.0 | 6.034 | 4.479 |
| E3/E3b/E3c/GSO / U / 0.3 | 50 | 0.3 / 0.7 | 1.00164 | 1.00511 | 0.24942 | 6.0 | 6.053 | 4.491 |
| P1+CRB+genie / G / 0.3 | 50 | 0.3 / 0.7 | 0.99894 | 0.99698 | 0.25117 | 6.0 | 5.987 | 4.446 |
| P1+CRB+genie / G / 0.5 | 50 | 0.5 / 0.5 | 0.99884 | 0.99663 | 0.25117 | 6.0 | 5.986 | 2.985 |
| P1+CRB+genie / U / 0.3 | 50 | 0.3 / 0.7 | 0.99894 | 0.98990 | 0.25117 | 6.0 | 5.956 | 4.425 |
| P1+CRB+genie / U / 0.5 | 50 | 0.5 / 0.5 | 0.99884 | 0.98996 | 0.25117 | 6.0 | 5.957 | 2.963 |
| P2a / G / 0.3 | 50 | 0.3 / 0.7 | 1.00081 | 0.99808 | 0.25117 | 6.0 | 5.992 | 4.446 |
| P2a / G / 0.5 | 50 | 0.5 / 0.5 | 1.00088 | 0.99839 | 0.25117 | 6.0 | 5.993 | 2.985 |
| P2a / U / 0.3 | 50 | 0.3 / 0.7 | 1.00081 | 0.99443 | 0.25117 | 6.0 | 5.976 | 4.425 |
| P2a / U / 0.5 | 50 | 0.5 / 0.5 | 1.00088 | 0.99559 | 0.25117 | 6.0 | 5.981 | 2.963 |
| P2b-EP/EPG / S / 0.2 | 50 | 0.2 / 0.8 | 1.00000 | 1.00422 | 0.24977 | 6.0 | 6.043 | 5.080 |
| P2b-SP / S / 0.3 | 50 | 0.3 / 0.7 | 1.00341 | 0.99477 | 0.24977 | 6.0 | 6.002 | 4.430 |
| P2b-SP / S / 0.5 | 50 | 0.5 / 0.5 | 1.00372 | 0.99711 | 0.24977 | 6.0 | 6.012 | 2.968 |
| prospective-K / G / 0.5 | 50 | 0.5 / 0.5 | 0.99801 | 0.99815 | 0.25088 | 6.0 | 5.997 | 3.001 |
| prospective-K / U / 0.5 | 50 | 0.5 / 0.5 | 0.99801 | 1.00353 | 0.25088 | 6.0 | 6.021 | 3.004 |
| prospective-S/K / G / 0.3 | 50 | 0.3 / 0.7 | 0.99818 | 0.99867 | 0.25088 | 6.0 | 5.999 | 4.463 |
| prospective-S/K / U / 0.3 | 50 | 0.3 / 0.7 | 0.99818 | 1.00400 | 0.25088 | 6.0 | 6.023 | 4.466 |

The largest group empirical-minus-nominal magnitude was 0.0554 dB. P1/E3 physical and internal coordinate ratios agreed within 1.93e-15 dB. No systematic inter-arm offset reached the frozen 0.1 dB BLOCKER threshold.

## Limitations

- Finite sampled generator/definition audit; no receiver/decoder, FER, MCRB or genie-result recomputation was performed.
- P1 complex gains were regenerated and authenticated against saved gain-array SHA256; stored E1 delays/Dopplers and C complex gains were used. The preserved P1 source snapshot and current default-path equivalence distinguish the later scenario-S extension.
- Distributional non-rejection is not proof of equality. Discrete KS tests are conservative; the 140 tests use the frozen Holm family at alpha=.01, preserving the shared-frame sampling design.
- Nominal SNR uses unit nominal pilot-plus-data energy per useful symbol, excluding CPP energy. Realized pilot/data cross terms and noise energy vary; P2b compares equal nominal total energy, with its disclosed +1.255 dB EP energy per information bit.

## Evidence and checkpoint

Small runtime results and log: `out/main/runtime.json`, `out/main/run.log`, `out/main/STATUS.txt`. Remote parameter arrays remain at:

`/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/generator_snr_audit_20261019/out/main/parameter_draws.npz`

MD5: `853ecae4820a74221faca002619c2055` (1208482 bytes).

**Observation:** 450 operator comparisons, 1650 energy measurements across 29 groups and 140 law tests completed. **Frozen verdict:** OK within the audited scope. **Untested explanation:** none. The registered H0 prediction (.80) matched this outcome; multiclass Brier score=.065. No result card or STATE change was made.
