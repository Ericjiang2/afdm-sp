# Stage10 Uncertainty-Aware SIC Summary

- fixed_best final_mean_ber=`1.2891e-03`
- fixed_best+vx_recalibration_v1 final_mean_ber=`1.3184e-03`
- best_global `(sic_kappa)=(0.0000)`, final_mean_ber=`1.3184e-03`
- rel_gain_vs_fixed_best=`-2.273%`
- rel_gain_vs_vx_recal_v1=`0.000%`

## Best By Seed / SNR

### seed=42

- `15 dB`: kappa=`0.0000`, rel_gain_vs_fixed_best=`-2.290%`, rel_gain_vs_vx_recal_v1=`0.000%`
- `25 dB`: kappa=`0.0000`, rel_gain_vs_fixed_best=`0.000%`, rel_gain_vs_vx_recal_v1=`0.000%`

## Aggregate Calibration

- fixed_best: mean_rho=`1.865`, mean_eta=`0.369`
- fixed_best+vx_recalibration_v1: mean_rho=`0.758`, mean_eta=`0.369`
- fixed_best+vx_recalibration_v1+uncertainty_aware_sic: mean_rho=`0.758`, mean_eta=`0.369`
- best_kappa mean_sic_weight=`1.000` (range=`1.000` to `1.000`)

## Trace Comparison

- early_iters_gain_vs_v1=`0.000%`
- late_iters_gain_vs_v1=`0.000%`

## Verdict

- Verdict: uncertainty-aware SIC does not yet deliver a stable enough BER gain; keep this as the first outer-loop use probe and decide next whether to try refit weighting.
