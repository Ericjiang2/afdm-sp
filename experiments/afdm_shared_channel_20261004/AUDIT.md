# Gaussian-pair arithmetic and interface audit

Scope: AUDIT-01, shared-channel follow-up. The old source and all old raw
results remain immutable. This audit tests the declared approximation; it does
not certify its equality to a QPSK/shared-channel marginal.

`production_diagnostic.arithmetic_case` independently builds a finite DFT and
CPP matrix for each path. At N=2/4, noise=.02/2 and singleton/pair blocks it
compares the old low-rank `GaussianPairLikelihood` with a direct full
covariance solve. A separate complete outside-QPSK enumeration computes
E[yy^H|d_B] using analytic Gaussian-gain second moments. The audit keeps the
normalization -N log(pi), log determinant and quadratic form. Tests require
likelihood error <1e-9 and covariance entry error <1e-10; raw matrices and
likelihoods are saved in the registered audit run.

The interface contract is all I bits followed by all Q bits, bit 0 maps to
positive real/imaginary amplitude .5, total QPSK symbol power .5, and
LLR=log P(0)-log P(1). A deliberately different I/Q sign pattern verifies
the old enumeration, native alphabet/marginal and local `bit_extrinsic`
against an independent enumeration. No sign/order discrepancy was found.
The frontend receives DAFT y/pilot and physical complex-noise variance. The
old generation wrapper scales all three consistently by
sqrt(2(1-rho)); at the frozen rho=.5 the scale is 1.

The actual path is:

1. `receiver.pilot_front` constructs the observed-pilot 515-column dictionary,
   selects 40 atoms, and initializes uniform data moments/prior.
2. `native_twofft.time_refine` performs two observation-only geometry passes,
   returning at most 8 paths and observed fitted gains.
3. `native_twofft.receive(rounds=1, iterations=20)` passes those gains into
   `twofft.scalar_joint`. That single outer round has 20 internal data/gain
   updates with damping .3; gain prior variance is 1/P. Its decoder is the
   actual frozen LDPC decoder, maxiter=50, receiving detector extrinsic
   LLRs clipped to [-20,20].
4. With two outer rounds, decoder check extrinsic is the replacement detector
   prior, decoder APP supplies next CE moments, and gains persist. A one-round
   success therefore does not establish that internal iteration is dispensable.
5. `local_receiver.receive(enabled=True)` executes the same frontend/refine,
   retains its geometry, then constructs `CollapsedModel(0,I/P)` and one
   uniform-incoming `gaussian_pair_pass`. It deliberately does not carry the
   fitted gain estimate or native AMP state into that approximation, and it
   has no feedback. Nonuniform input is explicitly rejected.

For iid zero-mean Gaussian gains and uniform outside QPSK, the old covariance
is the correct conditional second moment. Replacing the remaining mixture by
CN(0,S) is a separate approximation. The production generator first normalizes
the truncated G0 channel matrix in Frobenius norm (`afdm_env.py:630-641`), then
`supplement_g1.py` reuses those physical gains in the untruncated CPP operator
without rescaling. Its gain prior is neither iid Gaussian nor exactly uniform
fixed-total-energy. Saved physical gain energies for the three clusters are
1.0160185417, 1.0098600449 and 1.0089457377. A unit-sphere gain experiment is a
controlled mathematical model, not an exact reproduction of this production
prior. These distinctions are necessary before attributing the six failures.

Validation command (single-thread environment required):

```sh
/tmp/afdm-shared-channel-env/bin/python -m pytest -q experiments/afdm_shared_channel_20261004/test_production_diagnostic.py
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.production_diagnostic audit --stage audit_v1
```

Registered `execution/audit_v1` completed: maximum likelihood error
1.4210854715202004e-13; maximum conditional-moment entry error
2.220446049250313e-15, across all 8 cases. Its source snapshot preserves the
original audit implementation and raw matrices. Current contracts: 15 tests
passed, including an actual frozen-context bootstrap regression.

One initial test used bit-exact equality
after complex abs/square and observed 1.11e-16 floating-point roundoff. It now
checks the defining real-square plus imaginary-square power directly. This
was a test assertion issue; no old receiver code changed.
