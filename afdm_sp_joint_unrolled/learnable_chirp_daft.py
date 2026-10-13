"""learnable_chirp_daft.py — W8 Direction-D Round-0 (Option A).

Trainable scalar c1, c2 wrapped around ``ClassicalJointUnrolled``. AFDM identity
is preserved (still A_n = Λ_c2·F·Λ_c1 with c_i ∈ ℝ); only Bemani's analytic
c1* = (2k_max+1)/(2N) is replaced by an end-to-end-learned scalar.

Design rationale — see tcom_plan/W8D_learnable_daft_design.md.

Quick usage
-----------
>>> base = build_classical_joint_unrolled(N, l_max, k_max, c1_init, c2_init,
...                                       learnable_heads=('cand_active_rel',))
>>> recv = LearnableChirpDAFTReceiver(base, c1_init=c1_init, c2_init=c2_init)
>>> out = recv(y_daft, x_pilot, sigma2, constellation)  # base.cfg.c1/c2 are
...                                                     # transparently swapped
"""
from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn

from .classical_joint_unrolled import ClassicalJointUnrolled


class LearnableChirpDAFTReceiver(nn.Module):
    """Wraps a ClassicalJointUnrolled with two learnable AFDM chirp scalars.

    At forward time, the underlying receiver's ``cfg.c1`` and ``cfg.c2`` are
    transiently overridden with our Parameters; gradients flow back through the
    chirp-phase computations inside ``construct_sensing_matrix_torch``,
    ``reconstruct_H_torch``, and ``build_A_for_DALS_torch``.

    Bit-exact parity at init: when c1_init/c2_init match the base cfg values,
    the wrapper produces identical outputs to the base receiver (verified by
    ``verify_learnable_chirp_init_parity.py``).

    Parameters
    ----------
    base : ClassicalJointUnrolled
        Existing receiver. Its cfg.c1/c2 are the analytic Bemani values; they
        are used as initialization for the trainable scalars.
    c1_init, c2_init : float
        Initialization values. If None, taken from ``base.cfg.c1``/``c2``.
    constrain : str | None
        Constraint mode on the learned params:
        - None: unconstrained (raw nn.Parameter, can drift arbitrarily far).
        - 'relative_tanh': c1 = c1_init * (1 + 0.005 * tanh(c1_raw)) so the
          learned value stays within ±0.5% of Bemani's value. Same for c2.
          Use this for the conservative Round-0 sanity smoke; remove for the
          full Round-0 if smoke shows the unconstrained scalar wants to drift.
    """

    def __init__(self,
                 base: ClassicalJointUnrolled,
                 c1_init: Optional[float] = None,
                 c2_init: Optional[float] = None,
                 constrain: Optional[str] = None):
        super().__init__()
        self.base = base
        rdtype = base.cfg.rdtype

        c1_init = float(base.cfg.c1) if c1_init is None else float(c1_init)
        c2_init = float(base.cfg.c2) if c2_init is None else float(c2_init)
        self._c1_init = c1_init
        self._c2_init = c2_init
        self.constrain = constrain

        if constrain is None:
            self.c1_raw = nn.Parameter(torch.tensor(c1_init, dtype=rdtype))
            self.c2_raw = nn.Parameter(torch.tensor(c2_init, dtype=rdtype))
        elif constrain == 'relative_tanh':
            # tanh(0) = 0 → c_i = c_init * (1 + 0) = c_init at init
            self.c1_raw = nn.Parameter(torch.tensor(0.0, dtype=rdtype))
            self.c2_raw = nn.Parameter(torch.tensor(0.0, dtype=rdtype))
        else:
            raise ValueError(f"unknown constrain mode: {constrain!r}")

    # ------------------------------------------------------------------
    # Pass-through accessor: callers (e.g. _one_forward in train_*) that
    # poke module.cfg.n_paths need the base cfg here.
    # ------------------------------------------------------------------
    @property
    def cfg(self):
        return self.base.cfg

    # ------------------------------------------------------------------
    # Effective chirp scalars (the values actually fed into the receiver)
    # ------------------------------------------------------------------
    @property
    def c1_eff(self) -> torch.Tensor:
        if self.constrain is None:
            return self.c1_raw
        # relative_tanh: keep within ±0.5% of init
        return self._c1_init * (1.0 + 0.005 * torch.tanh(self.c1_raw))

    @property
    def c2_eff(self) -> torch.Tensor:
        if self.constrain is None:
            return self.c2_raw
        return self._c2_init * (1.0 + 0.005 * torch.tanh(self.c2_raw))

    # ------------------------------------------------------------------
    # Forward — swap cfg.c1/c2 with our Parameters, then defer to base
    # ------------------------------------------------------------------
    def forward(self, *args, **kwargs):
        cfg = self.base.cfg
        orig_c1, orig_c2 = cfg.c1, cfg.c2
        cfg.c1 = self.c1_eff
        cfg.c2 = self.c2_eff
        try:
            return self.base(*args, **kwargs)
        finally:
            cfg.c1 = orig_c1
            cfg.c2 = orig_c2

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def current_chirp(self) -> dict:
        """Snapshot the current learned (c1, c2) and their relative deviation."""
        c1 = float(self.c1_eff.detach())
        c2 = float(self.c2_eff.detach())
        return dict(
            c1=c1,
            c2=c2,
            c1_init=self._c1_init,
            c2_init=self._c2_init,
            c1_rel_dev=(c1 - self._c1_init) / self._c1_init if self._c1_init != 0 else float('nan'),
            c2_rel_dev=(c2 - self._c2_init) / self._c2_init if self._c2_init != 0 else float('nan'),
        )


__all__ = ['LearnableChirpDAFTReceiver']
