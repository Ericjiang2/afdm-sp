"""Finalize a protected/pruned nomination on the actual expanded GLS support."""
import copy
import math
import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import expand_cluster_support
from afdm_sp_joint_unrolled.projected_gls import projected_add_statistics


def _fit_state(y, phi, covariance, nomination, k_max, extension, active_cap):
    if (len(set(nomination)) != len(nomination) or
            any(type(i) is not int or i < 0 or i >= phi.shape[1] for i in nomination)):
        return None, 'columns'
    zeros = phi.new_zeros(phi.shape[1])
    delays, dopplers, _ = expand_cluster_support(nomination, k_max, extension, zeros, phi.shape[1])
    active = (delays*(2*k_max+1)+dopplers+k_max).tolist()
    before_merge = sum(min(k_max, i % (2*k_max+1)-k_max+extension)
                       - max(-k_max, i % (2*k_max+1)-k_max-extension)+1 for i in nomination)
    if len(active) > active_cap:
        return None, 'capacity'
    fit = projected_add_statistics(y, phi, covariance, active, [])
    if not fit['valid_current']:
        return None, 'rank'
    gains = fit['gains'].clone()
    # Evaluate the residual of the exact gain tensor to be committed, not a
    # separate projection that could conceal rounding or zero-filled neighbors.
    L = torch.linalg.cholesky(covariance)
    residual = torch.linalg.solve_triangular(
        L, (y-phi[:, active]@gains)[:, None], upper=False).squeeze(1)
    objective = float(torch.vdot(residual, residual).real)
    if not math.isfinite(objective) or not math.isfinite(fit['energy']):
        raise ValueError('nonfinite committed GLS objective')
    eta = 1e-10 if y.dtype == torch.complex128 else 1e-5
    if abs(objective-float(fit['objective'])) > eta*max(1., fit['energy'], objective):
        return None, 'gain_objective_mismatch'
    return dict(nomination_ids=list(nomination), active_ids=active,
                support_delays=delays.clone(), support_dopplers=dopplers.clone(),
                gains=gains, objective=objective, F=objective, rank=fit['rank'],
                energy=fit['energy'], dtype=str(y.dtype), device=str(y.device),
                expansion_policy='existing boundary clipping and unique sorted columns',
                raw_neighbor_count=len(nomination)*(2*extension+1),
                boundary_clipped_count=len(nomination)*(2*extension+1)-before_merge,
                duplicate_neighbors_merged=before_merge-len(active),
                unique_active_count=len(active)), None


@torch.no_grad()
def finalize_support_transaction(y, phi, covariance, baseline_nomination,
                                 proposal_nomination, *, k_max, extension,
                                 active_cap, gate_enabled=True, lambda_size=0.,
                                 tau=0., proposal_budget=1):
    """Fit baseline/proposal by one policy; select once without shared mutation.

    The caller supplies the output of the common protection/pruning pipeline.
    This finalizer owns expansion, uniqueness/capacity, final GLS and commit.
    None denotes an empty proposal pool; [] denotes an explicit drop-all action.
    One proposal may contain up to two F2P rounds; this is one F comparison.
    """
    for name, value, lower in [('k_max', k_max, 0), ('extension', extension, 0),
                               ('active_cap', active_cap, 1), ('proposal_budget', proposal_budget, 0)]:
        if type(value) is not int or value < lower:
            raise ValueError(f'invalid {name}')
    if type(gate_enabled) is not bool or lambda_size != 0 or tau != 0 or proposal_budget > 1:
        raise ValueError('registered first version requires boolean gate, lambda=tau=0, budget<=1')
    if phi.ndim != 2 or phi.shape[1] % (2*k_max+1):
        raise ValueError('dictionary must contain complete Doppler blocks')
    baseline, error = _fit_state(y, phi, covariance, list(baseline_nomination),
                                k_max, extension, active_cap)
    result = dict(accepted=False, valid_current=error is None, baseline=baseline,
                  proposal=None, committed=copy.deepcopy(baseline),
                  action_kind='keep', delta=None, margin=None,
                  complete_proposals_used=0, stop_reason=None,
                  lambda_size=0., tau=0., gate_enabled=gate_enabled)
    if error:
        result['reason'] = 'hold_current_'+error
        return result
    if proposal_budget == 0:
        result.update(reason='proposal_budget_exhausted', stop_reason='proposal_budget_exhausted')
        return result
    if proposal_nomination is None:
        result['reason'] = 'empty_pool'
        return result
    result.update(complete_proposals_used=1, stop_reason='proposal_budget_exhausted')
    proposal, error = _fit_state(y, phi, covariance, list(proposal_nomination),
                                k_max, extension, active_cap)
    result['proposal'] = proposal
    if error:
        result['reason'] = 'reject_final_'+error
        return result
    before, after = set(baseline['active_ids']), set(proposal['active_ids'])
    added, dropped = after-before, before-after
    result['added_ids'], result['dropped_ids'] = sorted(added), sorted(dropped)
    result['action_kind'] = 'replace' if added and dropped else 'add' if added else 'drop' if dropped else 'keep'
    delta = baseline['F']-proposal['F']
    eta = 1e-10 if y.dtype == torch.complex128 else 1e-5
    margin = eta*max(1., abs(baseline['F']), abs(proposal['F']), baseline['energy'])
    result.update(delta=delta, margin=margin)
    if before == after:
        result['reason'] = 'no_effective_support_change'
        return result
    if not gate_enabled:
        result.update(accepted=True, reason='topk_no_F_gate')
    elif delta > margin:
        result.update(accepted=True, reason='objective_improvement')
    else:
        result['reason'] = 'reject_worse' if delta < -margin else 'reject_critical'
    if result['accepted']:
        result['committed'] = copy.deepcopy(proposal)
    return result
