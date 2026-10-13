"""One frozen BP update with explicit weak-edge summaries, never a receiver."""
from __future__ import annotations

import time

import numpy as np
import torch
import torch.nn.functional as functional

from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


def reference_update(state):
    """Use the existing production operator for the one-update reference."""
    events = []
    started = time.perf_counter()
    hard, mean, variance = mp_detect_bp_torch(state['y'], state['H'], float(state['sigma2']),
        state['constellation'], n_iter=1, threshold=float(state['threshold']), damp=.5,
        device=torch.device('cpu'), return_numpy=True, return_soft=True,
        code_prior=state['code_prior'], message_observer=events.append)
    seconds = time.perf_counter() - started
    if len(events) != 1:
        raise ValueError('expected one explicit-prior BP output')
    return dict(llr=events[0]['channel_llr'].numpy(), mean=mean, variance=variance,
        retained=np.ones(int(np.count_nonzero(np.abs(state['H'].astype(complex)) >= state['threshold'])), dtype=bool),
        certificate=np.zeros(len(mean)), seconds=seconds, recovery=False,
        timings={'complete_local_update': seconds}, hard=hard)


def bounded_update(state, rule, parameter):
    """Update retained edge messages; weak initial means/variances remain in rows.

    Every invocation builds fresh summaries, so no H/prior/noise-dependent cache
    survives into a different outer state. Metrics and file IO are outside the
    operator timer, and are reported separately by the caller.
    """
    if rule not in ('amplitude', 'reliability', 'budget') or not np.isfinite(parameter) or parameter < 0:
        raise ValueError('unknown local rule or threshold')
    started = time.perf_counter()
    H = torch.as_tensor(state['H'], dtype=torch.complex128)
    y = torch.as_tensor(state['y'], dtype=torch.complex128)
    const = torch.as_tensor(state['constellation'], dtype=torch.complex128)
    prior = torch.as_tensor(state['code_prior'], dtype=torch.float64)
    sigma = float(state['sigma2'])
    n = len(y)
    if (H.shape != (n, n) or prior.shape != (2*n,) or const.shape != (4,)
            or not sigma > 0 or not np.isfinite(sigma)
            or any(not torch.isfinite(value).all() for value in (H, y, const, prior))
            or not torch.allclose(const, torch.tensor([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j], dtype=torch.complex128))):
        raise ValueError('invalid frozen local BP input or QPSK power')
    rows, cols = torch.nonzero(H.abs() >= float(state['threshold']), as_tuple=True)
    h = H[rows, cols]
    mag2 = h.abs().square()
    bits = (const.real < 0, const.imag < 0)
    prior_log = sum(torch.where(bit[None, :], -functional.softplus(part[:, None]),
                               -functional.softplus(-part[:, None]))
                    for bit, part in zip(bits, (prior[:n], prior[n:])))
    probability = torch.softmax(prior_log, dim=-1)
    initial_mean = (probability * const[None, :]).sum(-1)
    initial_var = torch.clamp(.5 - initial_mean.abs().square(), min=1e-10)
    graph_done = time.perf_counter()

    # All original graph edges contribute, including those subsequently omitted.
    hm = h * initial_mean[cols]
    hv = mag2 * initial_var[cols]
    row_residual = y.clone().scatter_add(0, rows, -hm)
    row_variance = torch.full((n,), sigma, dtype=torch.float64).scatter_add(0, rows, hv)
    excluded_residual = row_residual[rows] + hm
    excluded_variance = torch.clamp(row_variance[rows] - hv, min=.1*sigma)
    safe_h = torch.where(h.abs() > 1e-10, h, torch.full_like(h, 1e-10))
    mu = excluded_residual / safe_h
    variance = torch.clamp(excluded_variance / torch.clamp(mag2, min=1e-10), min=1e-10)
    summary_done = time.perf_counter()

    bounds = None
    if rule == 'amplitude':
        row_max = torch.zeros(n, dtype=torch.float64)
        row_max.scatter_reduce_(0, rows, h.abs(), reduce='amax', include_self=True)
        keep = h.abs() >= float(parameter)*row_max[rows]
    elif rule == 'reliability':
        keep = hv / sigma >= float(parameter)
    else:
        bounds = (2*const.abs().max()*(mu/variance).abs()).numpy()
        columns = cols.numpy()
        order = np.lexsort((rows.numpy(), bounds, columns))
        sorted_cols = columns[order]
        beginning = np.r_[0, np.flatnonzero(np.diff(sorted_cols)) + 1]
        if len(order):
            counts = np.diff(np.r_[beginning, len(order)])
            cumulative = np.cumsum(bounds[order])
            offsets = np.repeat(np.r_[0., cumulative[beginning[1:] - 1]], counts)
            omit_sorted = cumulative - offsets <= float(parameter)
            keep_np = np.ones(len(order), dtype=bool)
            keep_np[order[omit_sorted]] = False
            # Enforce the actual per-column budget after cumulative subtraction.
            used = np.bincount(columns[~keep_np], weights=bounds[~keep_np], minlength=n)
            keep_np |= used[columns] > float(parameter)
            keep = torch.as_tensor(keep_np)
        else:
            keep = torch.zeros(0, dtype=torch.bool)
    residual_ratio = float((row_residual.abs().square()/row_variance).max())
    recovery = residual_ratio > 100.
    if recovery:
        keep = torch.ones_like(keep)
    selector_done = time.perf_counter()

    selected_cols = cols[keep]
    inv_var = 1. / variance[keep]
    natural_edge = mu[keep] / variance[keep]
    precision = torch.zeros(n, dtype=torch.float64).scatter_add(0, selected_cols, inv_var)
    natural = torch.zeros(n, dtype=torch.complex128).scatter_add(0, selected_cols, natural_edge)
    prec_ext = torch.clamp(precision[selected_cols] - inv_var, min=1e-10)
    mean_ext = natural[selected_cols] - natural_edge
    var_ext = 1. / prec_ext
    mu_ext = mean_ext / prec_ext
    log_probability = -(mu_ext[:, None] - const[None, :]).abs().square()/var_ext[:, None] + prior_log[selected_cols]
    projected = torch.softmax(log_probability, dim=-1)
    mu_new = (projected * const[None, :]).sum(-1)
    var_new = torch.clamp((projected*const.abs().square()[None, :]).sum(-1) - mu_new.abs().square(), min=1e-10)
    outgoing_mean = initial_mean[cols].clone()
    outgoing_var = initial_var[cols].clone()
    outgoing_mean[keep] = .5*initial_mean[selected_cols] + .5*mu_new
    outgoing_var[keep] = var_new

    likelihood = 2*(natural.conj()[:, None]*const[None, :]).real - precision[:, None]*const.abs().square()[None, :]
    posterior = torch.softmax(likelihood + prior_log, dim=-1)
    mean = (posterior*const[None, :]).sum(-1)
    post_var = torch.clamp(.5 - mean.abs().square(), min=0)
    llr = torch.cat([torch.logsumexp(likelihood[:, ~bit], -1) - torch.logsumexp(likelihood[:, bit], -1) for bit in bits])
    ended = time.perf_counter()

    if bounds is None:
        bounds = (2*const.abs().max()*(mu/variance).abs()).numpy()
    kept = keep.numpy()
    certificate = np.bincount(cols.numpy()[~kept], weights=bounds[~kept], minlength=n)
    if any(not np.isfinite(value).all() for value in (llr.numpy(), mean.numpy(), post_var.numpy(), certificate)):
        raise FloatingPointError('nonfinite local approximation')
    return dict(llr=llr.numpy(), mean=mean.numpy(), variance=post_var.numpy(),
        retained=kept, certificate=certificate, seconds=ended - started,
        recovery=recovery, residual_ratio=residual_ratio,
        outgoing_mean=outgoing_mean.numpy(), outgoing_variance=outgoing_var.numpy(),
        timings={'graph_and_prior': graph_done - started,
            'all_edge_row_summary': summary_done - graph_done,
            'selector_and_recovery_check': selector_done - summary_done,
            'retained_message_update': ended - selector_done,
            'offline_certificate': time.perf_counter() - ended})
