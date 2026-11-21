"""Frozen-model GLS addition statistics, with explicit rank rejection."""
import torch


def _rank_contract(matrix):
    n, k = matrix.shape
    threshold = 10 * max(n, k) * torch.finfo(matrix.real.dtype).eps
    if not k:
        return True, dict(ratio=1., threshold=threshold)
    norms = torch.linalg.vector_norm(matrix, dim=0)
    if k > n or not bool(torch.isfinite(norms).all()) or bool((norms == 0).any()):
        return False, dict(ratio=0., threshold=threshold)
    singular = torch.linalg.svdvals(matrix/norms)
    ratio = float((singular[-1]/singular[0]).item())
    return ratio > threshold, dict(ratio=ratio, threshold=threshold)


def projected_add_statistics(y, phi, covariance, support, candidates):
    """Return D and q_perp on one frozen state; no prior or prune guarantee."""
    if y.dtype not in (torch.complex64, torch.complex128):
        raise ValueError('complex64 or complex128 inputs required')
    if any(t.dtype != y.dtype or t.device != y.device for t in (phi,covariance)):
        raise ValueError('dtype and device must agree')
    if y.ndim != 1 or not y.numel() or phi.ndim != 2 or phi.shape[0] != y.numel() or covariance.shape != (y.numel(),y.numel()):
        raise ValueError('invalid GLS dimensions')
    if any(not bool(torch.isfinite(t).all()) for t in (y,phi,covariance)):
        raise ValueError('nonfinite GLS inputs')
    for ids in (support,candidates):
        if len(set(ids)) != len(ids) or any(type(i) is not int or i < 0 or i >= phi.shape[1] for i in ids):
            raise ValueError('unique in-range integer columns required')
    support, candidates = list(support), list(candidates)
    tolerance = 10 * y.numel() * torch.finfo(y.real.dtype).eps
    scale = max(1.,float(covariance.abs().max().item()))
    if not torch.allclose(covariance,covariance.mH,rtol=0.,atol=tolerance*scale):
        raise ValueError('covariance is not Hermitian')
    L, info = torch.linalg.cholesky_ex(covariance)
    if int(info.item()) != 0:
        raise ValueError('covariance is not positive definite; no jitter applied')
    z = torch.linalg.solve_triangular(L,y[:,None],upper=False).squeeze(1)
    A = torch.linalg.solve_triangular(L,phi,upper=False)
    if not bool(torch.isfinite(z).all() and torch.isfinite(A).all()):
        raise ValueError('nonfinite whitened system')
    active = A[:,support]
    valid, rank = _rank_contract(active)
    result = dict(valid_current=valid, rank=rank, candidates=[],
                  energy=max(1.,float(torch.vdot(z,z).real.item())))
    if not valid:
        result['reason'] = 'hold_current_rank'
        return result
    if support:
        basis, R = torch.linalg.qr(active,mode='reduced')
        gains = torch.linalg.solve_triangular(R,(basis.mH@z)[:,None],upper=True).squeeze(1)
        residual = z-basis@(basis.mH@z)
    else:
        basis = A[:,:0]
        gains = y[:0]
        residual = z
    result.update(gains=gains, objective=torch.vdot(residual,residual).real, residual_w=residual)
    for candidate in candidates:
        entry = dict(id=candidate, accepted=False, D=None, q_perp=None)
        result['candidates'].append(entry)
        if candidate in support:
            entry['reason'] = 'active_conflict'
            continue
        valid, rank = _rank_contract(A[:,support+[candidate]])
        entry['rank'] = rank
        if not valid:
            entry['reason'] = 'candidate_rank'
            continue
        atom = A[:,candidate]
        projected = atom-basis@(basis.mH@atom)
        q = torch.vdot(projected,projected).real
        if not bool(q > 0):
            entry['reason'] = 'zero_projected_norm'
            continue
        D = torch.vdot(projected,residual).abs().square()/q
        if not bool(torch.isfinite(D)):
            raise ValueError('nonfinite GLS statistic')
        entry.update(accepted=True,reason='accepted',D=D,q_perp=q)
    return result
