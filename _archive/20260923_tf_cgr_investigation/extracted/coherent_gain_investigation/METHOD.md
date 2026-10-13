# Coherence-complete gain reaction (CGR): a specific candidate, not a new AMP family

## Status

There is no evidence proving that TF+CSTATE is a natural performance stopping point.
The complete PRO pack and source inspection identify an untested compatibility issue:
CSTATE can create same-delay physical slots; TF's gain reaction continues to use an
identity operator Gram. This is a mean-feedback hypothesis, not a claim that propagated
scalar gain variance is important. Causality in the fresh saved failures is untested.

The primary proposal is the minimal R-corrected gain reaction. More elaborate delay-
block/full-block covariances were implemented and challenged; they did not earn a
consistent additional reliability benefit over the minimal operation in our reference
fixtures. They remain controls, not extra proposed contributions.

## Signal convention

Use the supplied positive chirp/Doppler CPP convention, integer delays, sufficient CPP,
fixed blockwise parameters, proper thermal variance sigma2, QPSK +/-0.5 +/-0.5j,
and all-I-then-all-Q bit order. Nothing is renormalized per observation.

Let U_i=A M_i A^H, with M_i a CPP-weighted shift/modulation. Define

R_ij = tr(U_i^H U_j)/N = 1_(l_i=l_j) D_N(nu_j-nu_i),
D_N(t)=N^-1 sum_n exp(2j*pi*n*t/N).

R is Hermitian PSD and has unit diagonal. It is an operator Gram, NOT B(x)^H B(x)
and NOT a posterior covariance. Individual paths are unitary; their sum is not.

## Exact moment and reaction identities

For a diagonal AF-domain working covariance V=diag(v), set
Gamma_ij=tr(U_i^H U_j V). The exact Fourier identity in the Master gives

Gamma_ij = exp(2j*pi*c1*(l_i^2-l_j^2))
           D_N(nu_j-nu_i+2*N*c1*(l_j-l_i)) FFT(v)[l_j-l_i].

For equal delays this is exactly

Gamma_ij = sum(v) R_ij = N vx R_ij,

without requiring v to be uniform. For V=vx I, Gamma=N vx R on the entire path set.
Cross-delay entries of Gamma for nonuniform v are not restored by CGR.

The full quadratic data-uncertainty feedback has component
sum_j Gamma_ij hbar_j. This follows either by expanding the second moment of
H(h)(d-mu), or as the Wirtinger derivative of h^H Gamma h. The original P-BiG-AMP
pre-large-system cross reaction supplies the same algebraic ancestry. Restoring this
term does not make the complete damped approximate receiver exact EM or exact BP.

## Core update

Keep TF's current state, output step, data denoiser and data reaction unchanged:

rh_TF = h + vq [B(xbar)^H s - alpha N vx hbar].

Use instead

rh_CGR = h + vq [B(xbar)^H s - alpha N vx R hbar].

Apply the original Gaussian gain denoiser hplus=tau*rh/(tau+vq), tau=1/P,
and the original propagated scalar variance tau*vq/(tau+vq).
Keep the original reciprocal floor and every other numerical contract.

At the SAME entering state, the mean change relative to TF is exactly

delta_hplus = -alpha N vx/(P+vq^-1) (R-I) hbar.

With the reciprocal floor inactive, vq^-1=alpha||xbar||^2. If ||xbar||^2=N a
and alpha*a stays nonzero as N increases, the coefficient approaches vx/a.
It is therefore not an O(P/N) effect. It contains no propagated vh.

For a same-delay pair separated by delta Doppler bins,
|R12|=|sin(pi delta)/(N sin(pi delta/N))|. At N1024 and delta=.05 this is
.9958927391492818. The eigenvalues of R-I are +/-|R12|. Thus an order-one omitted
mean direction is possible even though the scalar gain variance is order 1/N.

## Algorithm

1. Run the two frozen TF rounds and frozen CSTATE exactly as before.
2. At its final geometry, use the already constructed physical R.
3. Run its existing final TF20/LDPC50 continuation, changing only the gain reaction.
4. Preserve APP/check-extrinsic interfaces and original fallback/deadline handling.
5. Use no new structural candidates, decoder rounds, model order, learned parameters,
   truth, current residual covariance estimate, or clipping schedule.

No inverse of R is used. The new work is a block matrix-vector multiplication
with cost sum_l m_l^2 <= P^2 per iteration, no extra transforms, and no new required
belief state. R is already present in the frozen operator object.
Distinct-delay geometry has R=I, so the declared maps agree (floating-point qualification
is still required). Fixed gains or vx=0 remove this proposed mechanism.

## Important negative cases

A large ||R-I|| alone is not a recoverability certificate. For duplicate operators and
hbar=(1,-1), (R-I)hbar is nonzero but its physical channel is zero. Record the change
in operator energy, delta_h^H R delta_h, not Euclidean gain motion alone.

Restoring the reaction does not correct all scalar pseudo-precisions, residual dependence,
wrong geometry, incorrect APPs, code loops or finite-iteration failures. It is not fully
invariant to merging duplicate parameter slots. The optional Gaussian block control has
a stronger merge-invariance property only when the aggregate channel prior is preserved.
That property must not be attributed to the minimal CGR arm.

## Scientific and novelty boundary

This investigation identifies a concrete approximation regime exposed by the existing
structural extension, not a previously unknown cross-term identity. Parker/Schniter's
pre-simplification equations, the archived coherent variant, and the archived full block
already contain the relevant ancestry. A claim to a new general bilinear AMP or to the
invention of full gain covariance would be false.

A possible paper-level delta is the deterministic coherence/mean-feedback failure law,
its end-to-end manifestation after observed model-space inference, and an inexpensive
minimal scalar closure avoiding full cavity/covariance state. The production effect and
whether this delta is sufficiently methodological for a Transactions paper remain OPEN.
A one-line beneficial patch alone is not automatically a publishable new core method.

## Numerical evidence

See README and the JSON rows. These are independent reference experiments, not a replay
of the cold production population. The LDPC2048 experiments use the supplied code/cache,
but synthetic fixed geometry, true geometry supplied to every arm, and a common scalar
first round. Only the second detector batch changes. No true bits or gains enter the
estimator. Complete production acquisition/CSTATE/latency are not simulated.
