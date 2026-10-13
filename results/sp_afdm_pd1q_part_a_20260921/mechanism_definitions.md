| Quantity | Iteration convention / definition |
|---|---|
| `vq` | Current gain pseudo-variance, after the output update and before the gain posterior update. |
| `vh_pre`, `vx_pre`, `xpower_pre`, `hRh_pre` | Values entering iteration t; x=pilot+mu. Used in the requested raw, undamped variance-correction expression. |
| `vh_post`, `vx_post` | Values after the current posterior/marginal update; these correspond to the saved scalar trace. |
| Output-variance correction | P vh_pre (xpower_pre+vx_pre)/(sigma²+vx_pre hRh_pre). Raw term ratio; output damping/history are not folded into this diagnostic. |
| Actual reaction/backprojection ratio | ||sv P vh_pre xb|| / ||adj||; xb is the damped data mean and adj=DAFT(A(hb)ᴴ s) uses the damped gain mean. The common data-step scale vr cancels. Equivalently ||P vh_pre xb||/||adj/sv||. |
| Literal x reaction ratio | ||P vh_pre x_pre||/||adj/sv||. Separately reported because the implemented reaction uses xb, not undamped x. |
| Gain-mean movement | ||h_post−h_pre||/||h_pre||. Each coded round restarts its inner iteration history and variance initialization. |
| Scaling coefficient | With precision floor inactive, joint N vh_post=1/(sv ||xb||²/N+P/N). POINT has the same gain-mean posterior shrinkage but propagates vh=0; a hypothetical posterior variance is not propagated. |
| Initial transient | Joint vh_pre=1/P at the first iteration of each coded round. It is not an O(1/N) posterior variance and must be separated from later iterations. |
| Sampling scope | Full requested vector-derived diagnostics: pre-existing frame0 at each of6.0,6.5,7.0dB, TF and POINT,2 coded rounds×20 iterations. Broader paired scalar-only traces remain separate; missing vector diagnostics are not imputed. |
| Scaling identifiability | Only one N and nominal P are observed. N vh and correction/(P/N) test consistency of coefficients at this operating point, not an empirical large-N/P order or first-order limit. |
| Attribution limit | TF and POINT have their own evolving means and decoder/refit feedback. Ratios measure explicit terms along each saved trajectory; trajectory differences are not a controlled same-state causal performance effect. |

| Part-A evidence extension | Required convention |
|---|---|
| Pre-state vectors | Save reconstructed x_pre/h_pre and barred xb/hb for declared audit frames, with original checkpoint identity/hash. Derived from saved states, not new observations. |
| Precision alpha | Report alpha_x=sv hbᴴRhb and alpha_h=sv ||xb||² separately; vr/vq use max(alpha,1e−12). |
| Raw output variance | bar_raw=vx_pre hRh_pre+P vh_pre xpower_pre; vp_raw=bar_raw+P vh_pre vx_pre. |
| Damped output variance | First inner iteration uses raw values; later beta×raw+(1−beta)×previous damped value, beta=.3. Both histories reset each coded round. |
| Direct-term norm | Report ||adj||, ||sv P vh_pre xb|| and gain-step numerator/denominator separately, alongside their ratios. Zero denominators must be flagged, not silently regularized. |
| Validation location | Recount occurs on saved arrays on deinlab, not locally unless explicitly recorded. Returned small files/hashes are transfer-checked locally. |
| Independence | Reused E1 inputs and controls are marked reused; new control/replay/memory calls reuse those same radio observations. None are fresh independent observations. |

Part-A artifacts: `mechanism_extension/extended_audit_metrics.csv` contains240 per-iteration scalar/norm rows, linked by vector_index to remote `audit_vectors.npz`; `mechanism_extension/receipt.json` records12 batch resets, source/checkpoint hashes and zero checked-state mismatch. All1920 older scalar rows are recounted without imputing absent vector fields. `analysis/mechanism_summary.csv` pools the two coded rounds at each SNR/arm, taking per-iteration medians for t5–19 and min/max for t0, not ratios of pooled medians. Its late diagnostic subset does not discard either initialization reset from the full data.
