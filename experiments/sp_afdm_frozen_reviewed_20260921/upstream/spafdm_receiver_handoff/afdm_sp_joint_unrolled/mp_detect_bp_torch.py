"""Torch-vectorized Gaussian BP detector for AFDM — functionally equivalent to
afdm_sp_joint_unrolled.afdm_baselines.mp_detect_bp but using scatter_add_ instead
of Python for-loops.

Speedup on CPU: ~30-50× at N=1024 with ~45 edges/row;
speedup on GPU: 100-500×.

Interface matches mp_detect_bp(y, H, sigma2, constellation, n_iter, threshold, damp).
"""
from __future__ import annotations
import numpy as np
import torch


def _qpsk_edge_moments(natural, temperature, prior_i=None, prior_q=None):
    """Circular likelihood factorization for ordered amplitude-.5 QPSK.

    Constant symbol energy cancels. The two bit log odds are twice the
    respective natural component / temperature, plus the delivered prior.
    Keep the historical edge variance floor and mean-only damping outside.
    """
    real = natural.real/temperature
    imag = natural.imag/temperature
    if prior_i is not None:
        real = real+prior_i/2
        imag = imag+prior_q/2
    mean = torch.complex(.5*torch.tanh(real), .5*torch.tanh(imag))
    return mean, torch.clamp(.5-mean.abs().square(), min=1e-10)


def _improper_natural(mean, variance, pseudovariance):
    """Information form of a nonsingular two-real-dimensional Gaussian."""
    if (torch.is_complex(variance) or not torch.isfinite(mean).all()
            or not torch.isfinite(variance).all() or not torch.isfinite(pseudovariance).all()
            or (variance <= pseudovariance.abs()).any()):
        raise ValueError('positive-definite finite complex Gaussian moments required')
    determinant = variance.square()-pseudovariance.abs().square()
    zero = pseudovariance == 0
    precision = torch.where(zero,1./variance,variance/determinant)
    pseudo_precision = pseudovariance/determinant
    natural = torch.where(zero,mean/variance,
                          precision*mean-pseudo_precision*mean.conj())
    return precision,pseudo_precision,natural


def mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
                      damp=0.5, device=None, return_numpy=None, return_soft=False, graph_observer=None,
                      code_prior=None, message_observer=None, convergence_observer=None,
                      message_temperature=None, noncircular=False,
                      pseudovariance_scale=1., cavity_observer=None, edge_projection=None,
                      edge_count_observer=None, complete_nonzero=False):
    """Vectorized BP detector.

    Inputs may be numpy or torch (complex64/complex128). Returns same dtype as input.

    ``message_temperature`` controls only the finite-alphabet edge projection.
    None preserves the historical factors: 2 without a code prior, 1 with one.
    It is separate from physical noise variance and final LLR calibration.
    The optional noncircular path keeps the original mean-only damping rule.
    It requires an explicit code prior (zeros for a terminal observation).
    ``edge_projection='qpsk_tanh'`` uses the algebraic circular QPSK edge
    moments; None keeps the original enumerated arithmetic. Full noncircular
    or probability-level cavity diagnostics require that original path.
    H may also be a finite square, canonical torch sparse COO matrix. Its
    implicit entries are zero, so sparse input requires a positive threshold.
    Sparse and dense inputs share the same ordered-edge message kernel. Only
    the optional graph observer materializes sparse H for its dense ledger.
    ``complete_nonzero=True`` consumes every nonzero entry, including entries
    below the usual threshold, while still excluding exact zeros. This is an
    explicit full-matrix graph mode; the message kernel is unchanged.
    ``edge_count_observer`` receives the active edge count once, without
    enabling the graph ledger or changing any message iteration.
    """
    if type(complete_nonzero) is not bool:
        raise ValueError('complete_nonzero must be boolean')
    def edge_mask(matrix):
        return matrix.abs() > 0 if complete_nonzero else matrix.abs() >= threshold

    graph_threshold = 0. if complete_nonzero else threshold
    graph_operator = '>' if complete_nonzero else '>='
    if (type(noncircular) is not bool or isinstance(pseudovariance_scale,(bool,np.bool_))
            or pseudovariance_scale not in (0.,1.) or
            (cavity_observer is not None and not callable(cavity_observer))):
        raise ValueError('explicit noncircular boolean, zero/one pseudo control and callable observer required')
    if noncircular and code_prior is None:
        raise ValueError('noncircular BP requires explicit discrete prior, including zeros')
    if edge_count_observer is not None and not callable(edge_count_observer):
        raise ValueError('edge count observer must be callable')
    track_pseudo = noncircular or cavity_observer is not None
    use_pseudo = noncircular and pseudovariance_scale == 1.
    if edge_projection not in (None, 'qpsk_tanh') or (edge_projection is not None and track_pseudo):
        raise ValueError('qpsk_tanh requires circular BP without a cavity observer')
    if message_temperature is not None and (
            isinstance(message_temperature,(bool,np.bool_)) or not np.isscalar(message_temperature)
            or np.iscomplexobj(message_temperature) or not np.isfinite(message_temperature)
            or message_temperature <= 0):
        raise ValueError('message temperature must be a positive finite real scalar')
    temperature = (1. if code_prior is not None else 2.) if message_temperature is None else float(message_temperature)
    # Detect input type
    was_numpy = isinstance(y, np.ndarray)
    if return_numpy is None:
        return_numpy = was_numpy
    dev = device if device is not None else (
        y.device if isinstance(y, torch.Tensor) else torch.device('cpu'))

    def _t(x, ctype=torch.complex128, rtype=torch.float64):
        if isinstance(x, torch.Tensor):
            return x.to(device=dev, dtype=ctype) if torch.is_complex(x) else x.to(device=dev, dtype=rtype)
        x = np.asarray(x)
        if np.iscomplexobj(x):
            return torch.as_tensor(x, device=dev, dtype=ctype)
        return torch.as_tensor(x, device=dev, dtype=rtype)

    sparse_H = isinstance(H, torch.Tensor) and H.layout != torch.strided
    if sparse_H:
        if (H.layout != torch.sparse_coo or H.ndim != 2 or H.shape[0] != H.shape[1]
                or H.sparse_dim() != 2 or H.dense_dim() != 0 or not H.is_coalesced()):
            raise ValueError('sparse BP requires a square canonical COO matrix')
        if (isinstance(threshold, (bool, np.bool_)) or not np.isscalar(threshold)
                or np.iscomplexobj(threshold) or not np.isfinite(threshold) or threshold <= 0):
            raise ValueError('sparse BP threshold must be a positive finite real scalar')
        indices = H.indices()
        flat = indices[0]*H.shape[0]+indices[1]
        if (not bool(torch.isfinite(H.values()).all()) or bool((indices < 0).any())
                or bool((indices >= H.shape[0]).any()) or bool((flat[1:] <= flat[:-1]).any())):
            raise ValueError('sparse BP requires finite values and unique row-major in-range indices')
    H = _t(H)
    y = _t(y)
    const = _t(constellation)
    if edge_projection is not None:
        expected = torch.tensor([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j], dtype=const.dtype, device=dev)
        if const.shape != (4,) or not torch.equal(const, expected):
            raise ValueError('qpsk_tanh requires exact amplitude-.5 ordered QPSK')
    sigma2_t = torch.as_tensor(float(sigma2), device=dev, dtype=torch.float64)
    N = H.shape[0]
    prior_log=None
    if convergence_observer is not None:
        if code_prior is not None:
            raise ValueError('convergence observer is only defined for the Gaussian BP branch')
        if isinstance(n_iter, (bool, np.bool_)) or not isinstance(n_iter, (int, np.integer)) or n_iter < 1:
            raise ValueError('convergence observer requires a positive integer iteration count')
    if code_prior is not None:
        prior=torch.as_tensor(code_prior,device=dev)
        if (prior.shape!=(2*N,) or torch.is_complex(prior) or not bool(torch.isfinite(prior).all()) or
                n_iter<1 or float(sigma2)<=0 or not bool(torch.isfinite(sigma2_t))):
            raise ValueError('finite I-then-Q code prior and positive noise/iterations required')
        expected=torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j],device=dev)
        if const.shape!=(4,) or not torch.allclose(const,expected.to(const.dtype)):
            raise ValueError('feedback requires frozen QPSK amplitude/order')
        prior=prior.to(torch.float64)
        bits_i=(const.real<0);bits_q=(const.imag<0)
        prior_log=torch.where(bits_i[None,:],-torch.nn.functional.softplus(prior[:N,None]),-torch.nn.functional.softplus(-prior[:N,None]))
        prior_log=prior_log+torch.where(bits_q[None,:],-torch.nn.functional.softplus(prior[N:,None]),-torch.nn.functional.softplus(-prior[N:,None]))
    elif message_observer is not None:
        raise ValueError('message observer requires explicit prior branch, including zero prior')
    def discrete_message(likelihood):
        app=likelihood+prior_log
        probability=torch.softmax(app,dim=-1)
        mean=(probability*const[None,:]).sum(-1)
        variance=torch.clamp(.5-mean.abs().square(),min=0)
        channel=torch.cat([torch.logsumexp(likelihood[:,~b],-1)-torch.logsumexp(likelihood[:,b],-1) for b in (bits_i,bits_q)])
        if use_pseudo:
            # A noncircular likelihood can couple I and Q. Marginalize with
            # the other bit's prior, then exclude this bit's own prior.
            channel=torch.cat([torch.logsumexp(app[:,~b],-1)-torch.logsumexp(app[:,b],-1) for b in (bits_i,bits_q)])-prior
        if message_observer is not None:
            payload=dict(channel_llr=channel.detach().clone(),prior_llr=prior.detach().clone(),
                posterior_mean=mean.detach().clone(),posterior_variance=variance.detach().clone(),
                convention=('positive logP0/P1; complex variance; own prior excluded' if use_pseudo else
                            'positive logP0/P1; complex variance; prior excluded before bit marginalization'))
            if track_pseudo:
                payload.update(probabilities=probability.detach().clone(),log_likelihood=likelihood.detach().clone(),
                    posterior_pseudovariance=((probability*const[None,:].square()).sum(-1)-mean.square()).detach().clone())
            message_observer(payload)
        return const[probability.argmax(-1)],mean,variance
    def no_observation_result():
        # With no graph edges the posterior is the constellation prior.
        # Preserve the historical hard-only zero output, but honor the soft
        # return contract used by the joint receiver and terminal decoder.
        if prior_log is not None:
            values=discrete_message(torch.zeros_like(prior_log))
            if not return_soft:values=values[0]
            if return_numpy:
                return tuple(v.detach().cpu().numpy() for v in values) if return_soft else values.detach().cpu().numpy()
            return values
        out = torch.zeros(N, dtype=H.dtype, device=dev)
        if not return_soft:
            return out.cpu().numpy() if return_numpy else out
        mean = const.mean().expand(N).clone()
        variance = const.var(unbiased=False).real.expand(N).clone()
        hard = const[(mean[:, None]-const[None, :]).abs().argmin(dim=1)]
        values = (hard, mean, variance)
        return tuple(v.detach().cpu().numpy() for v in values) if return_numpy else values
    def observe_empty_convergence():
        if convergence_observer is None:
            return
        convergence_observer(dict(
            mu_previous=torch.empty(0,dtype=H.dtype,device=dev),
            mu_current=torch.empty(0,dtype=H.dtype,device=dev),
            var_previous=torch.empty(0,dtype=torch.float64,device=dev),
            var_current=torch.empty(0,dtype=torch.float64,device=dev),
            executed_iterations=0))
    if N == 0:
        if edge_count_observer is not None:
            edge_count_observer(0)
        if graph_observer is not None:
            from afdm_sp_joint_unrolled.representation_ledger import actual_bp_graph
            empty = torch.empty(0, dtype=torch.long, device=dev)
            observed_H = H.to_dense() if sparse_H else H
            graph_observer(actual_bp_graph(observed_H, edge_mask(observed_H), empty, empty, graph_threshold, operator=graph_operator))
        observe_empty_convergence()
        return no_observation_result()

    # Build edge list (row, col, h) where |h| >= threshold
    if sparse_H:
        active = edge_mask(H.values())
        row_idx, col_idx = H.indices()[:, active]
        h_vals = H.values()[active]
    else:
        mask = edge_mask(H)
        row_idx, col_idx = torch.nonzero(mask, as_tuple=True)
        h_vals = H[row_idx, col_idx]
    E = h_vals.shape[0]
    if edge_count_observer is not None:
        edge_count_observer(E)
    if graph_observer is not None:
        from afdm_sp_joint_unrolled.representation_ledger import actual_bp_graph
        observed_H = H.to_dense() if sparse_H else H
        observed_mask = edge_mask(observed_H) if sparse_H else mask
        graph_observer(actual_bp_graph(observed_H, observed_mask, row_idx, col_idx, graph_threshold, operator=graph_operator))
    if E == 0:
        observe_empty_convergence()
        return no_observation_result()

    h_mag2 = (h_vals.abs() ** 2).to(torch.float64)

    # Messages: one per edge
    prior_mean = const.mean()
    prior_var = torch.var(const, unbiased=False).real.to(torch.float64)  # QPSK variance (real scalar)
    mu_v2o = torch.full((E,), fill_value=0.0, dtype=H.dtype, device=dev) + prior_mean
    var_v2o = torch.full((E,), fill_value=float(prior_var), dtype=torch.float64, device=dev)
    if prior_log is not None:
        initial=torch.softmax(prior_log,-1)
        initial_mean=(initial*const[None,:]).sum(-1)
        mu_v2o=initial_mean[col_idx]
        var_v2o=torch.clamp(.5-initial_mean.abs().square(),min=1e-10)[col_idx]
    if track_pseudo:
        c_v2o=torch.full_like(mu_v2o,((const-prior_mean).square()).mean())
        if prior_log is not None:
            c_v2o=((initial*const[None,:].square()).sum(-1)-initial_mean.square())[col_idx]
    mu_o2v = torch.zeros(E, dtype=H.dtype, device=dev)
    var_o2v = torch.ones(E, dtype=torch.float64, device=dev)

    for _ in range(n_iter):
        mu_v2o_old = mu_v2o.clone()
        var_v2o_old = var_v2o.clone()
        if track_pseudo:
            c_v2o_old = c_v2o.clone()

        # ---- Phase 1: observation -> variable ----
        # Row aggregates (excluded): for each row d, compute z_total, V_total
        edge_hmu = h_vals * mu_v2o                           # (E,) complex
        edge_hmag2_var = h_mag2 * var_v2o                    # (E,) real

        z_total_row = y.clone()
        z_total_row = z_total_row.scatter_add(0, row_idx, -edge_hmu)

        V_total_row = torch.full((N,), float(sigma2_t), dtype=torch.float64, device=dev)
        V_total_row = V_total_row.scatter_add(0, row_idx, edge_hmag2_var)

        # Per-edge excluded (gather back per edge):
        z_ext = z_total_row[row_idx] + edge_hmu              # remove self's negative contribution
        V_ext = V_total_row[row_idx] - edge_hmag2_var
        V_ext = torch.clamp(V_ext, min=float(sigma2_t) * 0.1)
        if track_pseudo:
            hc = h_vals.square()*c_v2o
            C_total = torch.zeros(N,dtype=H.dtype,device=dev).scatter_add(0,row_idx,hc)
            C_ext = C_total[row_idx]-hc
            if not torch.isfinite(C_ext).all() or (C_ext.abs()>=V_ext).any():
                raise FloatingPointError('BP observation cavity is not positive definite')

        # Message o2v = (z_ext / h_e, V_ext / |h_e|²)
        eps = 1e-10
        safe_h = torch.where(h_vals.abs() > eps, h_vals,
                             torch.full_like(h_vals, eps))
        mu_o2v = z_ext / safe_h
        var_o2v = torch.clamp(V_ext / torch.clamp(h_mag2, min=eps), min=eps)

        # ---- Phase 2: variable -> observation ----
        inv_var = 1.0 / var_o2v
        mu_over_var = (mu_o2v / var_o2v).to(H.dtype)

        prec_total_col = torch.full((N,), 1.0 / float(prior_var), dtype=torch.float64, device=dev)
        prec_total_col = prec_total_col.scatter_add(0, col_idx, inv_var)

        mean_total_col = torch.full((N,), 0.0, dtype=H.dtype, device=dev)
        mean_total_col = mean_total_col + prior_mean / prior_var
        mean_total_col = mean_total_col.scatter_add(0, col_idx, mu_over_var)

        if prior_log is not None:
            prec_total_col=torch.zeros(N,dtype=torch.float64,device=dev).scatter_add(0,col_idx,inv_var)
            mean_total_col=torch.zeros(N,dtype=H.dtype,device=dev).scatter_add(0,col_idx,mu_over_var)
        # Per-edge excluded
        prec_ext = prec_total_col[col_idx] - inv_var
        prec_ext = torch.clamp(prec_ext, min=eps)
        mean_ext = mean_total_col[col_idx] - mu_over_var
        var_ext = 1.0 / prec_ext
        mu_ext = mean_ext / prec_ext

        if edge_projection == 'qpsk_tanh':
            prior_i = prior[col_idx] if prior_log is not None else None
            prior_q = prior[N+col_idx] if prior_log is not None else None
            mu_new, var_new = _qpsk_edge_moments(mean_ext, temperature, prior_i, prior_q)
        else:
            # Enumerated reference retained for other alphabets and diagnostics.
            dist_sq = (mu_ext.unsqueeze(-1) - const.unsqueeze(0)).abs() ** 2
            log_prob = -dist_sq / (temperature * var_ext.unsqueeze(-1))
            if use_pseudo:
                a_o,b_o,t_o = _improper_natural(mu_o2v,var_o2v,C_ext/safe_h.square())
                a_col=torch.zeros(N,dtype=torch.float64,device=dev).scatter_add(0,col_idx,a_o)
                b_col=torch.zeros(N,dtype=H.dtype,device=dev).scatter_add(0,col_idx,b_o)
                t_col=torch.zeros(N,dtype=H.dtype,device=dev).scatter_add(0,col_idx,t_o)
                a_ext=a_col[col_idx]-a_o;b_ext=b_col[col_idx]-b_o;t_ext=t_col[col_idx]-t_o
                log_prob=(-a_ext[:,None]*const.abs().square()[None,:]
                          +(b_ext.conj()[:,None]*const[None,:].square()).real
                          +2*(t_ext.conj()[:,None]*const[None,:]).real)/temperature
            if prior_log is not None:
                log_prob=log_prob+prior_log[col_idx]
            log_prob = log_prob - log_prob.max(dim=-1, keepdim=True).values
            prob = torch.exp(log_prob)
            prob = prob / prob.sum(dim=-1, keepdim=True)
            mu_new = (prob.to(const.dtype) * const.unsqueeze(0)).sum(dim=-1)
            const_mag2 = (const.abs() ** 2).to(torch.float64).unsqueeze(0)
            var_new = (prob * const_mag2).sum(dim=-1) - mu_new.abs().to(torch.float64) ** 2
            var_new = torch.clamp(var_new, min=eps)
        if track_pseudo:
            c_v2o=(prob.to(const.dtype)*const[None,:].square()).sum(-1)-mu_new.square()

        # Damping (numpy only damps mu, not var)
        mu_v2o = (1.0 - damp) * mu_v2o_old + damp * mu_new
        var_v2o = var_new
        if cavity_observer is not None:
            cavity_observer(dict(iteration=int(_)+1,row=row_idx.detach().clone(),col=col_idx.detach().clone(),
                h=h_vals.detach().clone(),incoming_mean=mu_v2o_old.detach().clone(),
                incoming_variance=var_v2o_old.detach().clone(),incoming_pseudovariance=c_v2o_old.detach().clone(),
                cavity_mean=z_ext.detach().clone(),cavity_variance=V_ext.detach().clone(),
                cavity_pseudovariance=C_ext.detach().clone(),projection_probabilities=prob.detach().clone(),
                projection_mean=mu_new.detach().clone(),projection_pseudovariance=c_v2o.detach().clone(),
                delivered_mean=mu_v2o.detach().clone(),delivered_variance=var_v2o.detach().clone(),
                noncircular=noncircular,pseudovariance_scale=pseudovariance_scale,
                covariance_semantics='undamped finite projection covariance; only means are damped, as in legacy BP'))

    if convergence_observer is not None:
        convergence_observer(dict(
            mu_previous=mu_v2o_old.detach().clone(),
            mu_current=mu_v2o.detach().clone(),
            var_previous=var_v2o_old.detach().clone(),
            var_current=var_v2o.detach().clone(),
            executed_iterations=int(n_iter)))

    # ---- Final posterior ----
    inv_var = 1.0 / var_o2v
    mu_over_var = (mu_o2v / var_o2v).to(H.dtype)
    prec_post = torch.full((N,), 1.0 / float(prior_var), dtype=torch.float64, device=dev)
    prec_post = prec_post.scatter_add(0, col_idx, inv_var)
    mean_post = torch.full((N,), 0.0, dtype=H.dtype, device=dev) + prior_mean / prior_var
    mean_post = mean_post.scatter_add(0, col_idx, mu_over_var)
    var_post = 1.0 / torch.clamp(prec_post, min=eps)
    mu_post = mean_post * var_post.to(mean_post.dtype)  # (N,) complex

    if prior_log is not None:
        precision=torch.zeros(N,dtype=torch.float64,device=dev).scatter_add(0,col_idx,inv_var)
        natural=torch.zeros(N,dtype=H.dtype,device=dev).scatter_add(0,col_idx,mu_over_var)
        likelihood=2*(natural.conj()[:,None]*const[None,:]).real-precision[:,None]*const.abs().square()[None,:]
        if use_pseudo:
            # The last observation messages determine the terminal finite
            # constellation weights. A circular mu/variance demapper is invalid.
            likelihood=(-a_col[:,None]*const.abs().square()[None,:]
                        +(b_col.conj()[:,None]*const[None,:].square()).real
                        +2*(t_col.conj()[:,None]*const[None,:]).real)
        values=discrete_message(likelihood)
        if return_numpy:return tuple(v.detach().cpu().numpy() for v in values) if return_soft else values[0].detach().cpu().numpy()
        return values if return_soft else values[0]

    # Hard-decision to nearest constellation point
    d = (mu_post.unsqueeze(-1) - const.unsqueeze(0)).abs()
    idx = d.argmin(dim=-1)
    x_hat = const[idx]

    if return_numpy:
        if return_soft:
            return (x_hat.detach().cpu().numpy(),
                    mu_post.detach().cpu().numpy(),
                    var_post.detach().cpu().numpy())
        return x_hat.detach().cpu().numpy()
    if return_soft:
        return x_hat, mu_post, var_post
    return x_hat
