"""Shared fixed-support CPU fits and external operator error accounting."""
import numpy as np
import torch

from .bandlimited_basis import normalized_geometry


def fit_coefficients(design, observation, ridge_strength=0.):
    """One complex64 gels fit, with an optional normalized zero-center penalty."""
    design, observation = np.asarray(design), np.asarray(observation)
    if (observation.shape != (design.shape[0],)
            or not np.isfinite(observation).all()
            or type(ridge_strength) not in (float, int) or not np.isfinite(ridge_strength)
            or ridge_strength < 0 or not normalized_geometry(design)["qualified"]):
        raise ValueError("finite observation, qualified design and nonnegative ridge required")
    penalty = float(ridge_strength*np.vdot(design, design).real/design.shape[1])
    a = torch.tensor(np.ascontiguousarray(design), dtype=torch.complex64)
    y = torch.tensor(np.ascontiguousarray(observation), dtype=torch.complex64)
    if penalty:
        a = torch.cat((a, np.sqrt(penalty)*torch.eye(a.shape[1], dtype=a.dtype)))
        y = torch.cat((y, torch.zeros(a.shape[1], dtype=y.dtype)))
    coefficients = torch.linalg.lstsq(a, y[:, None], driver="gels").solution[:, 0]
    if not torch.isfinite(coefficients).all():
        raise ValueError("nonfinite CPU coefficient solve")
    residual = a@coefficients-y
    normal_residual = torch.linalg.vector_norm(a.conj().T@residual)
    normal_scale = torch.linalg.matrix_norm(a)*torch.linalg.vector_norm(y)
    return dict(coefficients=coefficients.detach().numpy().copy(),penalty=penalty,
        ridge_strength=float(ridge_strength),driver="gels",dtype="complex64",
        completed_solves=1,
        normal_residual=float(normal_residual/torch.clamp(normal_scale,min=1e-20)))


def operator_coordinates(geometry, channel):
    """External truth projection; never call this from a receiver/selector."""
    channel = np.asarray(channel)
    if channel.shape != (geometry.n,geometry.n) or not np.isfinite(channel).all():
        raise ValueError("finite external channel matched to basis required")
    unchirped = geometry.l2.conj()[:,None]*channel*geometry.l2[None,:]
    time_channel = np.fft.fft(np.fft.ifft(unchirped,axis=0,norm="ortho"),axis=1,norm="ortho")
    time_channel *= geometry.l1.conj()[:,None]*geometry.l1[None,:]
    delays = np.arange(geometry.delay_cap+1)
    indices, phase = geometry._indices_phase(delays)
    envelopes = time_channel[np.arange(geometry.n)[:,None],indices]/phase
    return ((geometry.basis.conj().T@envelopes)/np.sqrt(geometry.n)).T.reshape(-1)


def external_error_accounting(geometry, columns, fit, observation, truth):
    """Decompose error AFTER freezing an observed-selected support and fit.

    Representation and omitted-support errors are Frobenius-orthogonal to the
    selected operator span. Shrinkage, pilot alias, data and noise need not be
    orthogonal; their cross terms are retained, together with numeric remainder.
    """
    columns = np.asarray(columns,dtype=int)
    h = truth["H"]
    design = geometry.sensing(observation["pilot"])[:,columns]
    all_coefficients = operator_coordinates(geometry,h)
    selected = all_coefficients[columns]
    omitted = all_coefficients.copy(); omitted[columns]=0
    all_delays = np.arange(geometry.delay_cap+1)
    projected = geometry.channel(all_delays,all_coefficients)
    energy = float(np.vdot(h,h).real)
    if energy <= 0:
        raise ValueError("external relative errors require nonzero channel")
    signal_parts = np.column_stack((design@selected,
        h@observation["pilot"]-design@selected,
        h@truth["data"], np.sqrt(float(observation["sigma2"]))*truth["noise"]))
    augmented = design
    rhs = signal_parts
    if fit["penalty"]:
        augmented = np.vstack((design,np.sqrt(fit["penalty"])*np.eye(len(columns))))
        rhs = np.vstack((rhs,np.zeros((len(columns),4),complex)))
    parts,_,rank,_ = np.linalg.lstsq(augmented,rhs,rcond=None)
    if rank != len(columns):
        raise ValueError("external decomposition lost the qualified support rank")
    pieces = dict(shrink=parts[:,0]-selected,pilot_alias=parts[:,1],
        data_interference=parts[:,2],noise=parts[:,3],
        numerical=fit["coefficients"].astype(complex)-parts.sum(axis=1))
    matrix = np.stack(list(pieces.values()))
    gram = geometry.n*(matrix.conj()@matrix.T).real/energy
    rep = h-projected
    rep_error = float(np.vdot(rep,rep).real/energy)
    selection_error = float(geometry.n*np.vdot(omitted,omitted).real/energy)
    full = np.zeros_like(all_coefficients); full[columns]=fit["coefficients"]
    estimated = geometry.channel(all_delays,full)
    error = estimated-h
    nmse = float(np.vdot(error,error).real/energy)
    closure = float(abs(nmse-(rep_error+selection_error+gram.sum())))
    if closure > 1e-9*max(1.,nmse):
        raise ValueError("external operator error accounting does not close")
    hp = h@observation["pilot"]
    hp_error = error@observation["pilot"]
    residual = observation["y"]-design@fit["coefficients"]
    return dict(channel_nmse=nmse,pilot_nmse=float(np.vdot(hp_error,hp_error).real/np.vdot(hp,hp).real),
        observed_residual=float(np.vdot(residual,residual).real/np.vdot(observation["y"],observation["y"]).real),
        representation=rep_error,selection=selection_error,
        component_names=list(pieces),component_gram=gram,
        component_coefficients=matrix,projected_coefficients=all_coefficients,
        cross_terms=float(gram.sum()-np.trace(gram)),closure_error=closure,
        scope="external truth score on fixed noisy-selected support; no receiver decision")
