# Where the lattice barrier does and does not apply

Status: model audit, not a validated deployment scenario. Response to VALUE_CHALLENGE.md.

## Explicit physically realizable acquisition model
Consider scheduled isolated or guard-separated QPSK blocks with a known transmit block clock and coarse receiver sampling alignment, a single unknown propagation path, and a cyclic prefix of at least N/4 samples for N divisible by four. The receiver retains a fixed N-sample window following the prefix. An unknown path delay l∈{0,...,N/4-1} remains inside the prefix allowance, so every such hypothesis has an uncontaminated circular useful-block model. Known window boundaries do not imply known propagation delay: the prefix supplies timing slack. An integer row-chirp s with even sN makes the chirp prefix coincide with the cyclic extension assumed in the derivation.

The residual *integer* carrier-frequency hypothesis set in the theorem is all N Nyquist-equivalent bins, with fractional offset assumed zero or already corrected. This is a worst-case blind acquisition benchmark, motivated by full-band acquisition studied in classical OFDM synchronization. It is not asserted to be the usual oscillator error after practical coarse synchronization. The prefix is transmitted but excluded from the chosen observation interface; any guard-aware estimator has more information and is outside the lower bound.

This configuration is physically constructible, with 20% prefix overhead for CP=N/4, but its combination of a broad frequency search, broad delay allowance, single path and useful-window-only processing is restrictive. No claim is made that it matches the project's production prior or that a receiver should discard available prefix information to obtain the theorem's assumptions.

## Parameter membership, not merely small effective k
For the arbitrary quadratic c2 bound, Dirichlet produces k∈{1,...,K}, an integer d and residual ε=2Nc2 k-d. Choose d'=d mod (N/4), l0=0,l1=d', ν0=0 and ν1=k-sd' modulo N. Then both delays are inside the stated prior and both CFOs inside the N-bin search set. The coefficient change from d to d' is coordinatewise C4 and thus leaves the unknown-QPSK law unchanged. This explicitly establishes membership in the broad benchmark. Small k alone does not establish small physical CFO difference.

For a narrower prior D×V, this construction is valid only if there exist l0,l1∈D and ν0,ν1∈V with l1-l0 congruent to d modulo N/g and ν1-ν0+s(l1-l0)=k modulo N. The current proof offers no such guarantee for every c2. Therefore the entire-quadratic-class barrier is not promoted to a narrow-prior result.

## More practical, but weaker retained claim
For the actual c2=1/(10N²) baseline, the explicit hard pair is d=0,k=1, with identical delay and physical CFOs differing by one subcarrier. This requires neither a broad delay prior nor a long prefix. It applies whenever the allowed carrier-acquisition set contains two adjacent integer CFO bins. It still does not apply to a fully corrected CFO prior narrower than one bin. It proves an asymptotic information limitation of this fixed design, not superiority over all optimized quadratic designs in that short-prior setting.

## Research decision
Retain both results with different scopes: the all-quadratic theorem as a broad blind-acquisition structural result; the small-c2 hard pair as the closer-to-practice design warning. A phase-code adaptation may be worth developing, but actual benefit requires prior-aware design, finite-SNR evidence, and an efficient estimator. The present theoretical grid establishes existence only. User's acceptance of modest adaptations permits retaining this work; it does not justify hiding these limitations or declaring production success.
