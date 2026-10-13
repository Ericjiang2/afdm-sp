# Stage9 VX Recalibration Coefficients

## Per-Iteration Scale

- iter `0`: c_t=`8.3019`
- iter `1`: c_t=`0.2500`
- iter `2`: c_t=`0.2500`
- iter `3`: c_t=`0.2500`
- iter `4`: c_t=`0.5851`

## Interpretation

- Coefficients are fitted from `fixed_best` calibration data using the median `sym_err_mean / vx_mean` per iteration.
- Values are clipped into `[0.25, 64]` and then applied as `v_x_cal = clip(c_t * v_x, 1e-4, 2.0)`.
