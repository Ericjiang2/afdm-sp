# Closure defect and actual decisions

Status: **COHERENT AFTER REFRAMING**. Target: exact fixed-state identities, sufficient finite-bank decision conditions, and a controlled intervention in the actual TF recurrence. This is not a FER certificate or a newly derived full-covariance AMP algorithm.

## 1. Fixed regularized problem

Let B be a fixed complex response matrix, b=Bᴴy, Γ≽0 the fixed working uncertainty Gram, s≥0, and λ>0. Set A₀=BᴴB+(s+λ)I, E=Γ−sI, A=A₀+E. Both A₀ and A are positive definite. The minimizers are h₀=A₀⁻¹b and h=A⁻¹b. Subtraction gives exactly

\[
h-h_0=-A^{-1}Eh_0.
\]

This is standard normal-equation sensitivity. A large matrix defect is insufficient: choose nonzero E with h₀ in its nullspace, then h=h₀. The numerical checker supplies this and a non-null direction for the same E.

Let F=A₀⁻¹ᐟ²EA₀⁻¹ᐟ² and η=‖F‖₂<1. Multiplying the difference equation by A₀¹ᐟ² yields

\[
\|h-h_0\|_{A_0}
\le\frac{\|F A_0^{1/2}h_0\|_2}{1-\eta}
\le\frac{\eta}{1-\eta}\|h_0\|_{A_0}.
\]

The first inequality retains direction, unlike a pure Frobenius defect. It requires the same B, b, Γ, prior and objective. It does not compare diverging receiver trajectories.

## 2. A finite candidate certificate

For a fixed candidate a, let Qₐ(h)=c−2Re(hᴴbₐ)+hᴴAₐh, with c independent of the candidate. Its minimized value, up to this common constant, is Jₐ=−bₐᴴAₐ⁻¹bₐ. Its scalar approximation is J₀ₐ=−bₐᴴA₀ₐ⁻¹bₐ. If ηₐ=‖A₀ₐ⁻¹ᐟ²EₐA₀ₐ⁻¹ᐟ²‖₂<1, then

\[
|J_a-J_{0a}|\le\epsilon_a
=\frac{\eta_a}{1-\eta_a}b_a^H A_{0a}^{-1}b_a.
\]

Proof: use Aₐ⁻¹=A₀ₐ⁻¹ᐟ²(I+Fₐ)⁻¹A₀ₐ⁻¹ᐟ² and ‖(I+Fₐ)⁻¹−I‖₂≤ηₐ/(1−ηₐ). If the approximate winner a* satisfies J₀b−J₀a*>εb+εa* for every b≠a*, the exact winner is unchanged. This is sufficient, not necessary; it applies only to that frozen bank. An arbitrarily small perturbation can switch a near tie. Candidate generation, later refits, hard decoding and FER are outside the certificate. Candidate-dependent constants, prior normalization or marginal-likelihood log-determinants must be included explicitly; the displayed certificate does not cover their omission.

## 3. The actual TF consumer

Assume P>0. Bars denote damped estimates, not complex conjugation. Define Rᵢⱼ=tr(UᵢᴴUⱼ)/N, the operator Gram rather than an observed-response Gram. The frozen `twofft.scalar_joint` computes, at one entering state,

\[
v_q^{-1}=\max\{\alpha\|\bar x\|^2,10^{-12}\},\quad
r_h=h+v_q(\bar B^Hs-\alpha Nv_x\bar h),\quad
h^+=\frac{\tau}{\tau+v_q}r_h,\qquad\tau=1/P.
\]

Here α is the output precision `sv`; the residual vector s is a different object from the scalar uncertainty sum sᵥ=∑v=Nvₓ. Holding **all entering variables** fixed, replacing sᵥI by Γ(v) changes the next gain by

\[
\Delta h^+=-\frac{\alpha}{P+v_q^{-1}}
[\Gamma(v)-s_vI]\bar h.
\]

The denominator includes the actual precision floor. The coherent control replaces Γ by sᵥR. Uniform AF variance gives Γ=sᵥR; arbitrary AF variance need not. The new adapter checks the entire source SHA and uniquely replaces the `rh` assignment; it does not modify the old source or CSTATE geometry.

There is a real timing constraint: within an iteration, the data pseudo-observation and LLR are computed before the newly updated h can affect them. A one-step gain change can leave that step's LLR exactly unchanged; after the next iteration the LLR can change. The checker exercises both cases on the actual frozen module. A 20-step gain comparison alone is therefore not a 20-step LLR sensitivity certificate.

No global Lipschitz bound for the full finite-alphabet/LDPC loop is established. Clipping, codeword boundaries, support changes, damping and future states matter. The intervention retains scalar variance and other approximate reactions; it is **one-term consistency testing**, not exact Bayes or a consistent matrix-AMP derivation. Scalar/coherent/full complete receiver runs provide the empirical bridge.

## 4. Verification and paper scope

`verify_theory.py` checks fixed-state identity/bound, finite-bank margin and near-tie counterexamples, actual TF common-state gain changes, identity replay, observer parity, coordinate rotation and one-step delay. `verification_clean_env.json` reports eight passing groups and 13 small TF calls, using Python3.12.14/NumPy2.3.5/SciPy1.16.3 with warnings promoted to errors. These are synthetic checks, zero complete receivers and zero decoders.

The earlier Mac CE environment produced RuntimeWarnings despite finite passing outputs. Its `verification.json` and stricter failed evidence are retained. The isolated clean environment passed without suppressing warnings or changing the adapter. This does not diagnose the BLAS library root cause or make the earlier warning disappear.

Sensitivity and margin arguments are classical and overlap previous project JVP/margin work. The paper may use them to delimit claims and explain a measured interface effect. They cannot independently justify a new algorithmic contribution or guarantee improved FER.
