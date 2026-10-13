"""Common-state score table; receiver proposal/transaction wiring is separate."""
import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.decision_bound import assemble_lambda_percand
from afdm_sp_joint_unrolled.decision_harvest import whitened_suffstats
from afdm_sp_joint_unrolled.projected_gls import projected_add_statistics


MODES = ('legacy_stats_prior', 'projected_stats_prior', 'ols_no_prior')


def _numpy(tensor):
    return tensor.detach().cpu().numpy()


@torch.no_grad()
def prepare_common_scores(y, phi, covariance, support, candidates, *, pi, sh2,
                          prior_reference, residual_ols=None):
    """Freeze numeric prior once; change only (T,q) in the prior assembly.

    OLS retains incoming dtype/device. Legacy whitening uses CPU complex128;
    GLS retains incoming dtype/device (including its rank threshold). No truth
    lookup or prior fitting occurs here. An optional residual comes from the
    same geometry lookup that supplied pi/sh2, avoiding a second OLS solve.
    """
    if not isinstance(prior_reference, str) or not prior_reference:
        raise ValueError('nonempty prior reference required')
    prior = []
    for name, values in [('pi', pi), ('sh2', sh2)]:
        array = np.array(values, dtype=np.float64, copy=True)
        if array.shape != (len(candidates),) or not np.isfinite(array).all():
            raise ValueError(f'{name} must be a finite per-candidate vector')
        if np.any(array <= 0) or (name == 'pi' and np.any(array >= 1)):
            raise ValueError(f'invalid {name} domain')
        prior.append(array)
    pi, sh2 = prior
    gls = projected_add_statistics(y, phi, covariance, support, candidates)
    table = dict(support=list(support), candidate_ids=list(candidates),
                 prior_reference=prior_reference, candidates=[],
                 prior_hash=array_hash(np.column_stack((candidates, pi, sh2))),
                 hashes={name: array_hash(_numpy(t)) for name, t in
                         [('y', y), ('phi', phi), ('covariance', covariance)]},
                 precision=dict(ols=str(y.dtype), gls=str(y.dtype),
                                gls_device=str(y.device),
                                legacy_whitening='torch.complex128/cpu',
                                assembly='numpy.float64', ranking='numpy.float64'),
                 valid_current=gls['valid_current'], rank=gls['rank'],
                 eligibility='shared projected rank mask; historical A2 unchanged')
    if not gls['valid_current']:
        table['reason'] = 'hold_current_rank'
        return table
    if residual_ols is None:
        active = phi[:, list(support)]
        gains = torch.linalg.lstsq(active, y[:, None]).solution.squeeze(1) if support else y[:0]
        residual_ols = y - active @ gains
    if (residual_ols.shape != y.shape or residual_ols.dtype != y.dtype or
            residual_ols.device != y.device or not bool(torch.isfinite(residual_ols).all())):
        raise ValueError('OLS residual must match finite input vector contract')
    table['residual_ols'] = dict(real=_numpy(residual_ols.real).tolist(),
                                 imag=_numpy(residual_ols.imag).tolist(),
                                 squared_norm=float(torch.vdot(residual_ols, residual_ols).real))
    table['objective_gls'] = float(gls['objective'])
    if not candidates:
        table['reason'] = 'empty_pool'
        return table
    T, q = whitened_suffstats(covariance.to('cpu', torch.complex128),
                             residual_ols.to('cpu', torch.complex128),
                             phi[:, list(candidates)].to('cpu', torch.complex128))
    old = assemble_lambda_percand(_numpy(T), _numpy(q), pi, sh2)
    if not np.isfinite(old).all():
        raise ValueError('nonfinite legacy score assembly')
    for ordinal, entry in enumerate(gls['candidates']):
        row = dict(id=entry['id'], ordinal=ordinal, eligible=entry['accepted'],
                   reason=entry['reason'], pi=float(pi[ordinal]), sh2=float(sh2[ordinal]),
                   T_old=float(T[ordinal]), q_old=float(q[ordinal]),
                   legacy_stats_prior=float(old[ordinal]), D=None, q_perp=None,
                   projected_stats_prior=None, ols_no_prior=None)
        if entry['accepted']:
            D, q_perp = float(entry['D']), float(entry['q_perp'])
            score = float(assemble_lambda_percand(D, q_perp, pi[ordinal], sh2[ordinal]))
            if not np.isfinite([D, q_perp, score]).all():
                raise ValueError('nonfinite projected score assembly')
            row.update(D=D, q_perp=q_perp, projected_stats_prior=score, ols_no_prior=D)
        table['candidates'].append(row)
    table['reason'] = 'ready'
    if not any(r['eligible'] for r in table['candidates']):
        table['reason'] = ('all_active_conflicts' if all(r['reason'] == 'active_conflict'
                           for r in table['candidates']) else 'no_rank_eligible_candidates')
    return table


def gather_scores(table, mode, candidate_ids=None):
    """Gather common eligible candidates in requested order; never add a column."""
    if mode not in MODES:
        raise ValueError('unknown score mode')
    if not table['valid_current']:
        raise ValueError('hold_current_rank')
    ids = table['candidate_ids'] if candidate_ids is None else list(candidate_ids)
    rows = {r['id']: r for r in table['candidates']}
    if len(set(ids)) != len(ids) or any(i not in rows for i in ids):
        raise ValueError('unique frozen candidate IDs required')
    selected = [rows[i] for i in ids if rows[i]['eligible']]
    return [r['id'] for r in selected], [r[mode] for r in selected]


def rank_candidates(table, mode):
    """Float64 descending score; exact ties retain frozen candidate ordinal."""
    ids, scores = gather_scores(table, mode)
    order = np.argsort(-np.asarray(scores, dtype=np.float64), kind='stable')
    return [ids[i] for i in order]


@torch.no_grad()
def prepare_geometry_scores(y, phi, covariance, support, candidates, *, lookup,
                            k_max, K_per_l, prior_reference):
    """Reuse the live scorer's observable OLS geometry lookup exactly once."""
    from afdm_sp_joint_unrolled.decision_gateA import _resid_geom
    if not support:
        raise ValueError('empty_support_no_proposal: geometry prior undefined')
    if not candidates:
        return prepare_common_scores(y, phi, covariance, support, candidates,
                                     pi=[], sh2=[], prior_reference=prior_reference)
    columns = torch.tensor(candidates, device=phi.device, dtype=torch.long)
    residual, dl, dk, gains = _resid_geom(phi, y, support, columns, k_max, K_per_l)
    pi, sh2 = lookup(dl, dk, gains)
    return prepare_common_scores(y, phi, covariance, support, candidates,
                                 pi=pi, sh2=sh2, prior_reference=prior_reference,
                                 residual_ols=residual)
