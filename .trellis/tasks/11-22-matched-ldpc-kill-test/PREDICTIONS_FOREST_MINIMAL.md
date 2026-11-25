# Frozen two-point forest-code test

Run only the forest code in the original C1 L28 `FULL_R10` receiver at 7.50
and 7.75 dB on frame IDs 12000–12199. Keep the 0.30 pilot fraction, true
delays, ten outer rounds, 20 detector updates, and up to 50 decoder updates.
Reuse the original regular and matched rows from `main_49470497`. Verify
shared information bits, pilot, unit noise, channel seed and gains on all
400 new rows. This is a replay on the original cohort. The choice of frame
IDs and SNRs was informed by its prior results.

Use the exact length-2048, rate-1/2 matrix from the forest screen, with
degree counts 2:1023, 3:974, 30:51. Bind H, G and the systematic columns to
their hashes in the runner. The original regular L28 reference curve is the
saved 5.25–10.50 dB grid and its 10% FER crossing is 8.4375 dB. Bind the
reference rows to the aggregate digest of the published raw-file manifest.

## Readouts and decision

- Frame error means any wrong information bit after round ten. At each SNR,
  report the three FER counts. A recovered four-bit error means that the old
  matched word failed, differed by four coded bits, and had zero syndrome,
  and the forest code decodes that frame correctly. The fixed denominators
  are 13 at 7.50 dB and 12 at 7.75 dB. Also report all rescued frames and
  newly failed frames relative to the old matched code and the regular code.
  The paired net reduction is rescues minus new failures.
- Use the original regular crossing with the original isotonic fit and linear
  FER interpolation. For the new code use the two registered points with
  the same interpolation when they bracket 10%. If both points are below or
  above target, retain the one-sided grid bound. A reversed crossing (at or
  below target at 7.50 dB, above target at 7.75 dB) is unresolved. At an
  exact equality in non-reversed data use the first measured equality.
- Gain is regular crossing minus new-code crossing. **PASS** requires a point
  gain or lower bound of at least 0.8 dB. **BELOW** requires a point gain or
  upper bound below 0.8 dB. Otherwise report **UNRESOLVED**. Against the
  original point crossing the forest code needs to reach 10% by 7.6375 dB.
  Keep grid censoring rather than extrapolating either crossing. The
  decision is a two-point screen on the reused cohort.
- Report descriptive paired 95% bootstrap bounds using 4,000 draws, seed
  20261126. Each draw uses the same resampled frame IDs across both new
  points and the saved regular grid. For each gain draw retain both bounds,
  including open ends. Use the 2.5% quantile of lower bounds and the 97.5%
  quantile of upper bounds. The point or its grid bounds determine the gate.
- Forecast: PASS 0.30, BELOW 0.60, UNRESOLVED 0.10. A plausible outcome is a
  sizable rescue on the old four-bit frames and some new failures, leaving
  a smaller net gain. Arithmetic removal of those old errors is a motivation
  for the two points. It is not a prediction that each affected frame is rescued.

## Cost and stop

At most 400 receiver calls, all on the forest code. Cap the added controller
and worker CPU allocation at 1.9 core-hours. This keeps total allocation below
the original 20-core-hour ceiling given the prior 17.90 core-hours. Stop on
an incomplete or mismatched paired cell and retain its attempted rows.
Never add a receiver setting or an SNR point in response to the results.
