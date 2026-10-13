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
