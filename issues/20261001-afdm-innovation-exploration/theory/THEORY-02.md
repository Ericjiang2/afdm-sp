# Near-collision cluster coordinates and prior invariance

Status: **COHERENT AFTER REFRAMING**. The object is the response of a same-delay path cluster, not necessarily its individually identifiable physical parameters. All Dopplers use the project's dimensionless bin units.

## 1. Centered expansion

Absorb the deterministic phase caused by time centering into each gain. Let tₙ=(n−(N−1)/2)/N and b(ν) be the physical same-delay response to a fixed vector z, with b(ν)=Q diag(exp(2πiνtₙ))Wz. Here Q and W are the fixed physical unitary output/input transforms (including the common delay and CPP phase), independent of ν. Then

\[
h_1b(\bar\nu-\delta/2)+h_2b(\bar\nu+\delta/2)
=a_0b(\bar\nu)+a_1b'(\bar\nu)+r,
\quad a_0=h_1+h_2,\quad a_1=\tfrac\delta2(h_2-h_1).
\]

For real u, |exp(iu)−1−iu|≤u²/2. Apply this separately with u=±πδtₙ; use ‖T²Wz‖≤((N−1)/(2N))²‖z‖, where T=diag(t) and the triangle inequality:

\[
\|r\|_2\le
\frac{\pi^2\delta^2(N-1)^2}{8N^2}
(|h_1|+|h_2|)\|z\|_2.
\]

This is an absolute upper bound. It provides no relative response guarantee near cancellation. For exactly opposite gains the even Taylor terms cancel and the leading remainder is cubic; that structure should not be replaced by a blanket claim that cancellation always worsens relative accuracy.

## 2. Keep the prior and dimension

For δ≠0, the transform is invertible: h₁=a₀/2−a₁/δ and h₂=a₀/2+a₁/δ. Thus an original isotropic ridge becomes exactly

\[
\lambda(|h_1|^2+|h_2|^2)
=\lambda\left(\frac{|a_0|^2}{2}+\frac{2|a_1|^2}{\delta^2}\right).
\]

Using equal ridge on a₀ and a₁ changes the prior. Keeping two complex coefficients does not compress two complex degrees of freedom. An exact invertible basis change with the transformed prior preserves the physical regularized optimum; any apparent exact-inference gain must come from changed numerics, a changed prior, truncation or an incomplete optimizer.

For exact optimum equivalence, the actual transformed columns are c₀=(b(ν̄−δ/2)+b(ν̄+δ/2))/2 and c₁=(b(ν̄+δ/2)−b(ν̄−δ/2))/δ. Replacing these by b(ν̄), b′(ν̄) is Taylor truncation, even when the prior is transformed correctly. The induced covariance is diag(2τ,τδ²/2).

The equivalence is for fixed δ or direct substitution in the original penalized objective. If δ is also optimized, MAP density is not coordinate invariant: the real Jacobian is |δ|², and a normalized density in the new coordinates introduces 2log|δ| into its negative log density. Do not silently change to that different coordinate-dependent MAP objective.

At δ=0 the transform is singular. The two identical operators combine into one sum gain; independent CN(0,τ) gains give a₀∼CN(0,2τ), hence penalty |a₀|²/(2τ). The minimum-norm split is h₁=h₂=a₀/2. A separately free derivative coefficient is not the δ=0 limit under the original prior.

## 3. Working uncertainty versus actual response conditioning

Let U₀ be the centered physical operator and U₁=∂U/∂ν at a fixed center and delay. For AF-coordinate diagonal V≽0 and s=tr(V), DAFT equal-modulus elements imply that the time-domain diagonal of the transformed V is s/N. Since ∑tₙ=0 and N⁻¹∑tₙ²=(N²−1)/(12N²), direct traces give

\[
\Gamma_{ij}=\operatorname{tr}(U_i^HU_jV),\qquad
\Gamma=s\begin{pmatrix}1&0\\0&\pi^2(1-N^{-2})/3\end{pmatrix}.
\]

For N>1, normalizing the derivative operator by sqrt(π²(1−N⁻²)/3) gives sI **within this fixed cluster**. The corresponding coefficient and prior must also be rescaled. Cross-cluster terms remain. The result assumes centered operators with the corresponding rephased gains; an uncentered derivative has a different cross term.

For the actual observed-response columns B=[U₀z,U₁z], let wₙ be the shifted time-input energy and S=∑wₙ. Then BᴴB has off-diagonal 2πi∑wₙtₙ and determinant

\[
\det(B^HB)=4\pi^2S^2\operatorname{Var}_{w/S}(t).
\]

The weighted-variance expression assumes S>0; S=0 gives B=0 directly. Consequently, centered time alone does not make the response columns orthogonal. An input concentrated at one time index has zero weighted variance and singular B, despite the clean working Γ formula. Positive weighted variance gives full rank; good conditioning needs a quantitative variance bound. Scaling S improves absolute information/SNR but does not improve the condition number. Recovering h₁−h₂ still magnifies error by 1/δ.

## 4. Legal receiver interface and scientific value

U₁ is nonunitary. Frozen TF assumes physical unitary path operators and a specific gain prior; directly inserting derivative atoms violates those assumptions. A legal low-risk implementation can use exact sum/difference coordinates internally, transform the prior, then restore the same physical paths before TF. A genuinely different candidate needs an explicit finite-budget pair update, truncation rule, or rederived nonunitary inference with consistent variance and power terms.

The numerical checker verifies Taylor behavior including δ=0/opposite gains, transformed ridge and exact-fit equivalence, direct dense Γ traces, and the concentrated-input counterexample. See `verification_clean_env.json`; no cluster full-receiver advantage is implied by these synthetic checks.

Classical nearest neighbors include confluent/derivative bases, variable projection, NOMP, and near-colliding-source resolution theory (arXiv:1904.09186). This derivation does not claim novelty for Taylor expansion or reparameterization. The current data show a real collision association, but stronger F1+CSTATE already corrects all six archived F0+CSTATE failures. New contribution requires an observable, cheaper or more reliable mechanism beyond that strong reference, followed by independent samples.
