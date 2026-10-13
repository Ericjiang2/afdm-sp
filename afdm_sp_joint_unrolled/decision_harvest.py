#!/usr/bin/env python
"""Decision-experiment harvester (t=0 "why learn" 2x2 ablation, Phase 1-2).

For each frame (deterministic seed) at a fixed SNR/config, harvest the candidate
pool (pilot-MF top-M off-support atoms), the head input features (u, v), the
genie missed-atom labels y, and the per-candidate SUFFICIENT STATISTICS of the
in-class optimal detector Lambda for three covariance variants:

  - genie   C = (1-rho) sigma_x^2  H_true H_true^H + sigma_w^2 I      (E1, achievable bound)
  - realiz. C = (1-rho) sigma_x^2  Hhat0 Hhat0^H + sigma_w^2 I        (E1', sec.5 gate) [TODO]
  - white   C = sigma_w^2 I                                            (E0, OMP/white-MF floor)

The Lambda factorisation is
    logLambda(phi_i) = log(pi_i/(1-pi_i)) + (b_i/(1+b_i)) T_i - log(1+b_i),
    b_i = sigma_h,i^2 q_i,   q_i = phi_i^H C^-1 phi_i,
    T_i = |phi_i^H C^-1 r|^2 / q_i.
Only (T_i, q_i) are frame-local and computed here; the calibration-dependent
pi_bin and sigma_h,bin^2 are plugged in by a separate post-processing pass
(Phase 3) so they can be estimated held-out (red line: no per-frame |h_i|^2,
no eval-set pi). We also dump bin_id (geometry bin) and genie_gain_sq (true
|gain|^2 of genie-active candidates, for the held-out sigma_h,bin^2 estimate only).

Red lines honoured:
  - C uses Cholesky solves, never an explicit inverse (H H^H is ill-conditioned).
  - sigma_h^2 / pi are NOT consumed here; only the calibration ingredients are dumped.

Run `--self-test` first: a synthetic Proposition-1 check (C -> sigma^2 I makes the
general whitened-MF statistic collapse to the white matched filter |phi^H r|^2),
which validates the Cholesky path with no env dependency.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, tempfile, fcntl, functools, inspect
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Reuse the faithful Config-A harvest helpers (these imports also install the
# mp_detect_bp shim path; the decisive cut never runs MP-BP).
from afdm_sp_joint_unrolled.loop9_cache_features import (
    _make_config_a, _oracle_dictionary_support, _merged_dictionary_coefficients,
    _build_features_np, _pad_v_to,
)
from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix, omp_sparse,
)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import QPSK
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash, dev_rng
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_job_queue import write_status


def validate_prior_manifest(manifest, n_frames):
    """Validate the frozen stream9 prior identities, including actual seed values."""
    if (not isinstance(manifest, dict) or type(n_frames) is not int or n_frames < 1
            or manifest.get('schema') != 'afdm-prior-frames-v1' or manifest.get('root_seed') != 20260905):
        raise ValueError('invalid prior manifest schema or root seed')
    frames = manifest.get('frames')
    if not isinstance(frames, list) or len(frames) != n_frames:
        raise ValueError('prior manifest frame count mismatch')
    seeds = set()
    for i, frame in enumerate(frames):
        if not isinstance(frame, dict) or any(type(frame.get(k)) is not int for k in
                                              ('split', 'replicate', 'frame_index', 'stream', 'seed')):
            raise ValueError('prior manifest needs integer identity fields')
        expected = int(dev_rng(40, i, 9, split=2).integers(0, 2**31))
        if (frame['split'], frame['replicate'], frame['frame_index'], frame['stream'], frame['seed']) != (2, 40, i, 9, expected):
            raise ValueError('prior manifest identity or seed mismatch')
        if expected in seeds:
            raise ValueError('duplicate prior manifest seed')
        seeds.add(expected)
    return frames


def prior_metadata_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def validate_complete_prior(cache, n_frames):
    """Reject incomplete or internally inconsistent fixed-domain prior evidence."""
    if cache.get('schema') != 'afdm-direct-prior-v1':
        raise ValueError('direct40 requires a full-label fixed-frame prior')
    config = cache.get('config', {})
    if (config.get('receiver_shell') != 'direct40' or config.get('nomination_cap') != 40
            or config.get('truth_zero_threshold') != 0.
            or cache.get('configuration_sha256') != prior_metadata_hash(config)):
        raise ValueError('direct prior configuration hash or domain mismatch')
    manifest = cache.get('frame_manifest')
    identities = validate_prior_manifest(manifest, n_frames)
    if cache.get('manifest_sha256') != prior_metadata_hash(manifest):
        raise ValueError('direct prior manifest hash mismatch')
    records = cache.get('frame_records')
    if not isinstance(records, list) or len(records) != n_frames:
        raise ValueError('direct prior full frame records missing')
    Q = (config['l_max'] + 1) * (2 * config['k_max'] + 1)
    for i, (identity, record) in enumerate(zip(identities, records)):
        if (record.get('identity') != identity or record.get('receiver_nomination') != 40
                or int(cache['seed'][i]) != identity['seed']):
            raise ValueError('direct prior frame identity/domain mismatch')
        hashes = record.get('input_hashes', {})
        if set(hashes) != {'y', 'H', 'pilot', 'data', 'noise'} or any(
                not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
                for v in hashes.values()):
            raise ValueError('direct prior input hashes missing or malformed')
        truth = record.get('truth', {})
        params = record.get('channel_parameters', {})
        required = {'l_i','k_real','g_i','l_exp','k_exp','chan_coef_exp','fro_scale','k_leak','P_actual','taps'}
        if (not required <= set(params) or int(params['taps']) != config['p_paths']
                or int(params['k_leak']) != 2
                or any(np.asarray(params[k]).ndim != 1 or len(params[k]) != config['p_paths']
                       for k in ('l_i','k_real','g_i'))
                or any(len(params[k]) != int(params['P_actual']) for k in ('l_exp','k_exp','chan_coef_exp'))):
            raise ValueError('full physical channel parameters missing or inconsistent')
        if truth.get('zero_threshold') != 0.:
            raise ValueError('direct prior truth threshold mismatch')
        columns = np.asarray(truth.get('columns'))
        coefficients = np.asarray(truth.get('coefficients'))
        if (columns.ndim != 1 or columns.dtype.kind not in 'iu'
                or coefficients.shape != columns.shape or not np.iscomplexobj(coefficients)
                or not np.isfinite(coefficients).all() or len(set(columns.tolist())) != len(columns)
                or (columns < 0).any() or (columns >= Q).any()):
            raise ValueError('invalid complete prior truth coefficients')
        merged_cols, merged_gains = _merged_dictionary_coefficients(
            params, config['k_max'], 2*config['k_max']+1)
        active = columns[np.abs(coefficients) > 0.]
        if (not np.array_equal(columns, merged_cols) or not np.array_equal(coefficients, merged_gains)
                or not np.array_equal(active, truth.get('active_columns'))):
            raise ValueError('full truth does not match complex coefficient merge')
        support = np.asarray(record.get('omp_support'))
        if (support.ndim != 1 or support.dtype.kind not in 'iu' or len(support) > 40
                or len(set(support.tolist())) != len(support) or (support < 0).any() or (support >= Q).any()):
            raise ValueError('invalid prior OMP support')
        missed = set(active.tolist()) - set(support.tolist())
        candidates = cache['cand_cols'][i].tolist()
        if (len(candidates) != cache['M'] or len(set(candidates)) != len(candidates)
                or any(c < 0 or c >= Q or c in support for c in candidates)):
            raise ValueError('invalid prior candidate pool')
        labels = np.asarray([int(c in missed) for c in candidates])
        if not np.array_equal(labels, np.asarray(cache['y'][i])):
            raise ValueError('candidate labels disagree with complete frame truth')
        gains_by_column = dict(zip(columns.tolist(), coefficients.tolist()))
        gain_sq = np.asarray([abs(gains_by_column.get(c, 0.))**2 for c in candidates])
        if not np.allclose(gain_sq, np.asarray(cache['genie_gain_sq'][i]), rtol=1e-6, atol=0.):
            raise ValueError('candidate gains disagree with complete frame truth')


# --------------------------------------------------------------------------- #
# Core: whitened-MF sufficient statistics via Cholesky (no explicit inverse).
# --------------------------------------------------------------------------- #
def whitened_suffstats(C: torch.Tensor, r: torch.Tensor,
                       Phi_cand: torch.Tensor):
    """Return (T, q) for each candidate column of Phi_cand under covariance C.

    C        : (N, N) Hermitian positive-definite (complex)
    r        : (N,)   residual (complex)
    Phi_cand : (N, M) candidate atoms (complex)

    q_i = phi_i^H C^-1 phi_i           (real, > 0)
    T_i = |phi_i^H C^-1 r|^2 / q_i     (real, >= 0)   [whitened matched filter / GLRT]

    Uses one Cholesky factor of C and triangular solves for C^-1 r and C^-1 Phi.
    """
    L = torch.linalg.cholesky(C)                       # C = L L^H
    # Solve C x = b  for b = r and b = Phi_cand via cholesky_solve.
    Cinv_r = torch.cholesky_solve(r.unsqueeze(1), L).squeeze(1)     # (N,)
    Cinv_Phi = torch.cholesky_solve(Phi_cand, L)                    # (N, M)
    # q_i = phi_i^H (C^-1 phi_i)  -> column-wise inner product, real part.
    q = torch.einsum('ni,ni->i', Phi_cand.conj(), Cinv_Phi).real    # (M,)
    q = q.clamp_min(1e-30)
    # numerator |phi_i^H C^-1 r|^2 = |(Phi^H Cinv_r)_i|^2
    proj = Phi_cand.conj().T @ Cinv_r                               # (M,)
    T = (proj.abs() ** 2) / q                                       # (M,)
    return T, q


def _self_test():
    """Proposition 1 numerical confirmation + Cholesky-path correctness.

    With C = sigma^2 I, the general whitened statistic must collapse to
        q_i  -> ||phi_i||^2 / sigma^2,
        T_i  -> |phi_i^H r|^2 / (sigma^2 ||phi_i||^2),
    and rank(T_i) must equal rank(|phi_i^H r|^2 / ||phi_i||^2) (the OMP/white-MF
    selection statistic). We also cross-check the general genie path against a
    brute-force explicit-inverse reference on a small system.
    """
    torch.manual_seed(0)
    N, M = 64, 12
    sigma2 = 0.37
    Phi = torch.randn(N, M, dtype=torch.cdouble)
    r = torch.randn(N, dtype=torch.cdouble)

    # (a) white C = sigma^2 I via the GENERAL Cholesky path.
    C_white = sigma2 * torch.eye(N, dtype=torch.cdouble)
    T_g, q_g = whitened_suffstats(C_white, r, Phi)
    col_sq = (Phi.abs() ** 2).sum(0)                    # ||phi_i||^2
    q_ref = col_sq / sigma2
    T_ref = (Phi.conj().T @ r).abs() ** 2 / (sigma2 * col_sq)
    assert torch.allclose(q_g, q_ref, rtol=1e-8, atol=1e-10), "q white mismatch"
    assert torch.allclose(T_g, T_ref, rtol=1e-8, atol=1e-10), "T white mismatch"
    # Prop.1: ranking equals white matched-filter |phi^H r|^2 / ||phi||^2.
    white_mf = (Phi.conj().T @ r).abs() ** 2 / col_sq
    assert torch.equal(torch.argsort(T_g), torch.argsort(white_mf)), \
        "Prop.1 ranking mismatch"

    # (b) general genie C (colored) vs explicit-inverse reference (small N).
    A = torch.randn(N, N, dtype=torch.cdouble)
    C = A @ A.conj().T + sigma2 * torch.eye(N, dtype=torch.cdouble)   # HPD
    T_chol, q_chol = whitened_suffstats(C, r, Phi)
    Cinv = torch.linalg.inv(C)
    q_inv = torch.einsum('ni,nm,mi->i', Phi.conj(), Cinv, Phi).real
    proj = torch.einsum('ni,nm,m->i', Phi.conj(), Cinv, r)
    T_inv = (proj.abs() ** 2) / q_inv
    assert torch.allclose(q_chol, q_inv, rtol=1e-6, atol=1e-8), "q genie mismatch"
    assert torch.allclose(T_chol, T_inv, rtol=1e-6, atol=1e-8), "T genie mismatch"

    print("[self-test] PASS")
    print("  (a) Prop.1: C=sigma^2 I  =>  whitened-MF stat == white MF |phi^H r|^2,"
          " ranking identical.")
    print("  (b) Cholesky genie path matches explicit-inverse reference"
          f" (max |dT|={float((T_chol-T_inv).abs().max()):.2e}).")


# --------------------------------------------------------------------------- #
# Per-frame harvest of features + Lambda sufficient statistics.
# --------------------------------------------------------------------------- #
def _bin_id(dl_nn: np.ndarray, dk_nn_signed: np.ndarray) -> np.ndarray:
    """Geometry bin per candidate: Dirichlet leakage lives at same delay (dl=0),
    Doppler offset dk in {0,+-1,+-2}; everything else is 'far'.
    bins: 0 = dl0&|dk|0, 1 = dl0&|dk|1, 2 = dl0&|dk|2, 3 = far. (red-line: this is
    pure geometry, no genie identity.)"""
    adk = np.abs(dk_nn_signed)
    out = np.full(dl_nn.shape, 3, dtype=np.int8)        # far
    on_delay = (dl_nn == 0)
    out[on_delay & (adk <= 2)] = adk[on_delay & (adk <= 2)].astype(np.int8)
    return out


def harvest_frame(sys_obj, n_total, sigma2, Phi_np, col_norms, K_per_l, M,
                  seed, rho, device='cpu', return_raw=False, nomination_cap=None,
                  complete_truth=False):
    """Return per-frame dict with features, genie label, and Lambda suff. stats.

    None if insufficient off-support candidates. If return_raw, also include the
    raw frame data needed to run the downstream receiver for Phase-6 BER.
    """
    rng = np.random.default_rng(seed)
    np.random.seed(seed)
    H_true, _, channel_params = sys_obj.generate_channel_matrix()
    sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
    P_d = 1.0 - rho
    data_idx = rng.integers(0, 4, size=n_total)
    data_qam = QPSK[data_idx]
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    y_clean = H_true @ x_sp
    noise = (rng.standard_normal(n_total)
             + 1j * rng.standard_normal(n_total)) / np.sqrt(2.0)
    y_daft = y_clean + np.sqrt(sigma2) * noise

    # Classical OMP + LS -> support, gains, residual r^0.
    if nomination_cap is not None and (not isinstance(nomination_cap,int) or not 1<=nomination_cap<=Phi_np.shape[1]):
        raise ValueError('invalid receiver nomination cap')
    _, support = omp_sparse(y_daft, Phi_np, sparsity if nomination_cap is None else nomination_cap)
    s_omp = np.array(support, dtype=int)
    Phi_S = Phi_np[:, s_omp]
    g_ls, *_ = np.linalg.lstsq(Phi_S, y_daft, rcond=None)
    r0 = y_daft - Phi_S @ g_ls                          # (N,) residual

    # Genie support (Dirichlet-weighted) + per-atom |gain|.
    s_oracle, g_oracle = _oracle_dictionary_support(
        channel_params, sys_obj.k_max_cap, K_per_l, sparsity, return_gains=True)
    frame_record = None
    if complete_truth:
        columns, coefficients = _merged_dictionary_coefficients(channel_params, sys_obj.k_max_cap, K_per_l)
        if (not np.isfinite(coefficients).all() or (columns < 0).any()
                or (columns >= Phi_np.shape[1]).any()):
            raise ValueError('invalid full dictionary truth')
        active = np.abs(coefficients) > 0.
        s_oracle, g_oracle = columns[active], np.abs(coefficients[active])
        frame_record = dict(
            channel_parameters={k:np.asarray(v).copy() for k,v in channel_params.items()},
            truth=dict(columns=columns, coefficients=coefficients,
                       active_columns=columns[active], zero_threshold=0.,
                       merge_rule='complex_sum_by_dictionary_column_before_exact_nonzero_test'),
            receiver_nomination=nomination_cap, omp_support=s_omp.copy(),
            input_hashes={k:array_hash(v) for k,v in dict(
                y=y_daft, H=H_true, pilot=pilot_scaled,
                data=np.sqrt(P_d)*data_qam, noise=noise).items()})
    missed = set(int(x) for x in s_oracle) - set(int(x) for x in s_omp)
    gain_per_col = {int(s_oracle[i]): float(g_oracle[i])
                    for i in range(len(s_oracle))}

    # Head features (u, v) + candidate columns (pilot-MF top-M off-support).
    u, v, cand_cols = _build_features_np(Phi_np, col_norms, y_daft, s_omp, g_ls,
                                         sigma2, sys_obj.l_max_cap,
                                         sys_obj.k_max_cap, K_per_l, M)
    if u is None:
        return None
    Mc = len(cand_cols)
    y_lbl = np.array([1 if int(c) in missed else 0 for c in cand_cols],
                     dtype=np.int8)

    # ---- Lambda sufficient statistics on the candidate pool --------------- #
    dev = torch.device(device)
    H = torch.as_tensor(H_true, dtype=torch.cdouble, device=dev)
    r = torch.as_tensor(r0, dtype=torch.cdouble, device=dev)
    Phi_cand = torch.as_tensor(Phi_np[:, cand_cols], dtype=torch.cdouble, device=dev)
    sigma_x2 = 1.0                                       # QPSK unit data power
    eye = torch.eye(n_total, dtype=torch.cdouble, device=dev)
    # genie C (E1)
    C_genie = (1.0 - rho) * sigma_x2 * (H @ H.conj().T) + sigma2 * eye
    T_gen, q_gen = whitened_suffstats(C_genie, r, Phi_cand)
    # white C (E0) -- closed form (and also the white-MF score).
    col_sq = torch.as_tensor(col_norms[cand_cols] ** 2, dtype=torch.double, device=dev)
    proj_white = (Phi_cand.conj().T @ r)
    white_mf = (proj_white.abs() ** 2).cpu().numpy()            # |phi^H r|^2 (E0,P0 score)
    T_white = (proj_white.abs() ** 2 / (sigma2 * col_sq)).cpu().numpy()
    q_white = (col_sq / sigma2).cpu().numpy()
    # realiz. C (E1') -- Ĥ⁰ covariance from OMP-once support+gains, NO genie
    # identity (Sec.5 realisable gate). Ĥ⁰ = gen_h_daft(g_ls, l_omp, k_omp).
    l_omp = (s_omp // K_per_l)
    k_omp = (s_omp % K_per_l) - sys_obj.k_max_cap
    Hhat0 = sys_obj.gen_h_daft(g_ls, l_omp, k_omp)
    Hh = torch.as_tensor(Hhat0, dtype=torch.cdouble, device=dev)
    C_realiz = (1.0 - rho) * sigma_x2 * (Hh @ Hh.conj().T) + sigma2 * eye
    T_re, q_re = whitened_suffstats(C_realiz, r, Phi_cand)

    # ---- geometry bin + calibration ingredients --------------------------- #
    l_c = cand_cols // K_per_l
    k_c = (cand_cols % K_per_l) - sys_obj.k_max_cap
    l_s = s_omp // K_per_l
    k_s = (s_omp % K_per_l) - sys_obj.k_max_cap
    dl_mat = np.abs(l_c[:, None] - l_s[None, :])
    dk_mat = (k_c[:, None] - k_s[None, :])
    d_sum = dl_mat + np.abs(dk_mat)
    j_nn = d_sum.argmin(axis=1)
    dl_nn = dl_mat[np.arange(Mc), j_nn]          # delay offset to nearest atom
    dk_nn = dk_mat[np.arange(Mc), j_nn]          # signed Doppler offset
    g_nn = np.abs(g_ls)[j_nn]                     # OBSERVABLE OMP-LS gain of nearest atom
    bin_id = _bin_id(dl_nn, dk_nn)               # coarse 4-bin (kept for back-compat)
    # genie |gain|^2 for active candidates (held-out sigma_h,bin^2 use ONLY).
    genie_gain_sq = np.array([gain_per_col.get(int(c), 0.0) ** 2
                              for c in cand_cols], dtype=np.float32)

    raw = None
    if return_raw:
        raw = dict(y_daft=y_daft, data_idx=data_idx, H_true=H_true,
                   pilot_scaled=pilot_scaled, s_omp=s_omp, g_ls=g_ls,
                   missed_cols=np.array(sorted(int(c) for c in missed), dtype=int),
                   sparsity=int(sparsity))

    return dict(
        u=u, v=v, cand_cols=cand_cols.astype(np.int32), y=y_lbl, raw=raw,
        T_genie=T_gen.cpu().numpy().astype(np.float32),
        q_genie=q_gen.cpu().numpy().astype(np.float32),
        T_white=T_white.astype(np.float32), q_white=q_white.astype(np.float32),
        T_realiz=T_re.cpu().numpy().astype(np.float32),
        q_realiz=q_re.cpu().numpy().astype(np.float32),
        white_mf=white_mf.astype(np.float32),
        bin_id=bin_id, genie_gain_sq=genie_gain_sq,
        dl_nn=dl_nn.astype(np.int16), dk_nn=dk_nn.astype(np.int16),
        g_nn=g_nn.astype(np.float32),
        p_real=int(v.shape[1]),
        n_missed=int(len(missed)), frame_record=frame_record,
    )


def _record_prior_failure(out_dir, record):
    publish_json(Path(out_dir)/f'failure-{time.time_ns()}.json', record)
    write_status(Path(out_dir)/'failure.json', record)


def _publish_torch(value, path):
    """Publish a complete immutable file; never overwrite an existing artifact."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.harvest-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            torch.save(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def _exclusive_fixed_prior(function):
    @functools.wraps(function)
    def locked(*args, **kwargs):
        bound = inspect.signature(function).bind(*args, **kwargs)
        if bound.arguments.get('frame_manifest') is None:
            return function(*args, **kwargs)
        output = Path(bound.arguments['out_dir'])
        output.mkdir(parents=True, exist_ok=True)
        with (output/'.harvest.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError('fixed prior already running') from error
            return function(*args, **kwargs)
    return locked


@_exclusive_fixed_prior
def run_harvest(out_dir, snr, n_frames, n_total, v_mean, p_paths, tau_ms,
                fs_factor, M, p_pad, seed_base, print_every=50, device='cpu',
                rho_override=None, nomination_cap=None, frame_manifest=None, resume=False):
    manifest, identities = None, None
    if resume and frame_manifest is None:
        raise ValueError("resume requires a fixed frame manifest")
    if frame_manifest is not None:
        manifest = json.loads(Path(frame_manifest).read_text())
        identities = validate_prior_manifest(manifest, n_frames)
        if nomination_cap != 40 or p_pad < 40:
            raise ValueError('fixed prior requires nomination40 and padding at least40')
        if (Path(out_dir)/f'cache_snr{snr}.pt').exists():
            raise FileExistsError('fixed prior cache already exists')
    os.makedirs(out_dir, exist_ok=True)
    sys_obj = _make_config_a(n_total, v_mean, p_paths, tau_ms, fs_factor=fs_factor)
    if rho_override is not None:
        sys_obj.rho = float(rho_override)          # SP pilot/data power split sweep
    rho = float(sys_obj.rho)
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    K_per_l = 2 * sys_obj.k_max_cap + 1
    Phi = construct_sensing_matrix(n_total, pilot_scaled, sys_obj.c1, sys_obj.c2,
                                   sys_obj.l_max_cap, sys_obj.k_max_cap)
    col_norms = np.linalg.norm(Phi, axis=0)
    print(f"[harvest] N={n_total} v={sys_obj.v_mean} P={sys_obj.P_paths} "
          f"rho={rho} l_max={sys_obj.l_max_cap} k_max={sys_obj.k_max_cap} "
          f"fs={sys_obj.fs/1e3:.1f}kHz(x{fs_factor}) SNR={snr} M={M} "
          f"n_frames={n_frames}", flush=True)

    provenance = None
    if manifest is not None:
        provenance = dict(manifest=manifest, snr=snr, n_total=n_total, v_mean=v_mean,
                          p_paths=p_paths, tau_ms=tau_ms, fs_factor=fs_factor, M=M,
                          p_pad=p_pad, seed_base=seed_base, rho=rho,
                          nomination_cap=nomination_cap, device=device,
                          source_hashes={str(p.relative_to(Path(__file__).parent)):hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in sorted(Path(__file__).parent.rglob('*.py'))})
        provenance_path = Path(out_dir)/'provenance.json'
        if provenance_path.exists():
            if not resume:
                raise FileExistsError('fixed prior output exists; use explicit resume')
            if json.loads(provenance_path.read_text()) != provenance:
                raise ValueError('fixed prior resume provenance mismatch')
        else:
            if resume:
                raise ValueError('resume provenance missing')
            publish_json(provenance_path, provenance)
    sigma2 = 10 ** (-snr / 10.0)
    rng_master = np.random.default_rng(seed_base + int(snr))
    P_pad = int(p_pad)
    buf = {k: [] for k in ('u', 'v', 'mask', 'cand_cols', 'y', 'T_genie',
                           'q_genie', 'T_white', 'q_white', 'white_mf',
                           'bin_id', 'genie_gain_sq', 'dl_nn', 'dk_nn', 'g_nn',
                           'p_real', 'seed')}
    frame_records = []
    kept = 0; tries = 0; t0 = time.time()
    while kept < n_frames and tries < n_frames * 3:
        identity = None if identities is None else identities[tries]
        seed_fi = int(rng_master.integers(0, 2**31)) if identity is None else identity['seed']
        tries += 1
        frame_path = None if identity is None else Path(out_dir)/f'frame-{identity["frame_index"]:04d}.pt'
        restored = bool(resume and frame_path is not None and frame_path.exists())
        try:
            if restored:
                saved = torch.load(frame_path, map_location='cpu', weights_only=False)
                if saved['provenance_sha256'] != prior_metadata_hash(provenance):
                    raise ValueError('fixed prior frame provenance mismatch')
                r = saved['result']
                if r['frame_record']['identity'] != identity:
                    raise ValueError('fixed prior restored frame identity mismatch')
            else:
                r = harvest_frame(sys_obj, n_total, sigma2, Phi, col_norms, K_per_l, M,
                                  seed_fi, rho, device=device,nomination_cap=nomination_cap,
                                  complete_truth=identities is not None)
        except Exception as error:
            if identity is not None:
                _record_prior_failure(out_dir, dict(frame=identity, completed_frames=kept, error=repr(error)))
            raise
        if r is None or r['p_real'] > P_pad:
            if identity is not None:
                _record_prior_failure(out_dir, dict(frame=identity, completed_frames=kept,
                    error='insufficient candidates or support exceeds padding'))
                raise ValueError('fixed prior frame failed; replacement sampling is forbidden')
            continue
        if identity is not None:
            r['frame_record']['identity'] = identity
            frame_records.append(r['frame_record'])
            # Keep completed fixed-frame evidence even if a later frame fails.
            if not restored:
                _publish_torch(dict(provenance_sha256=prior_metadata_hash(provenance), result=r), frame_path)
        v_pad, mask = _pad_v_to(r['v'], P_pad)
        buf['u'].append(r['u']); buf['v'].append(v_pad); buf['mask'].append(mask)
        buf['cand_cols'].append(r['cand_cols']); buf['y'].append(r['y'])
        buf['T_genie'].append(r['T_genie']); buf['q_genie'].append(r['q_genie'])
        buf['T_white'].append(r['T_white']); buf['q_white'].append(r['q_white'])
        buf['white_mf'].append(r['white_mf']); buf['bin_id'].append(r['bin_id'])
        buf['genie_gain_sq'].append(r['genie_gain_sq'])
        buf['dl_nn'].append(r['dl_nn']); buf['dk_nn'].append(r['dk_nn'])
        buf['g_nn'].append(r['g_nn'])
        buf['p_real'].append(r['p_real']); buf['seed'].append(seed_fi)
        kept += 1
        if kept % print_every == 0:
            dt = time.time() - t0
            print(f"  [snr={snr}] kept={kept}/{n_frames} tries={tries} "
                  f"{dt:.1f}s ({dt/kept*1e3:.0f}ms/frame)", flush=True)

    def _stack(key, dtype):
        return torch.as_tensor(np.stack(buf[key]), dtype=dtype)
    out = dict(
        u=_stack('u', torch.float32), v=_stack('v', torch.float32),
        mask=torch.as_tensor(np.stack(buf['mask'])),
        cand_cols=_stack('cand_cols', torch.int32),
        y=_stack('y', torch.int8),
        T_genie=_stack('T_genie', torch.float32),
        q_genie=_stack('q_genie', torch.float32),
        T_white=_stack('T_white', torch.float32),
        q_white=_stack('q_white', torch.float32),
        white_mf=_stack('white_mf', torch.float32),
        bin_id=torch.as_tensor(np.stack(buf['bin_id'])),
        genie_gain_sq=_stack('genie_gain_sq', torch.float32),
        dl_nn=_stack('dl_nn', torch.int16), dk_nn=_stack('dk_nn', torch.int16),
        g_nn=_stack('g_nn', torch.float32),
        p_real=torch.as_tensor(np.array(buf['p_real']), dtype=torch.int32),
        seed=torch.as_tensor(np.array(buf['seed']), dtype=torch.int64),
        snr=int(snr), n=int(kept), M=int(M), P_pad=int(P_pad),
        config=dict(N=n_total, v_mean=v_mean, p_paths=p_paths, tau_ms=tau_ms,
                    fs_factor=fs_factor, rho=rho, l_max=sys_obj.l_max_cap,
                    k_max=sys_obj.k_max_cap, sigma2=sigma2, seed_base=seed_base,
                    nomination_cap=nomination_cap),
        _argv=sys.argv,
    )
    if manifest is not None:
        out.update(schema='afdm-direct-prior-v1', frame_manifest=manifest,
                   manifest_sha256=prior_metadata_hash(manifest),
                   manifest_file_sha256=hashlib.sha256(Path(frame_manifest).read_bytes()).hexdigest(),
                   frame_records=frame_records)
        out['config'].update(receiver_shell='direct40', truth_zero_threshold=0.)
        out['configuration_sha256'] = prior_metadata_hash(out['config'])
        validate_complete_prior(out, n_frames)
    out_file = Path(out_dir) / f"cache_snr{snr}.pt"
    if manifest is not None:
        _publish_torch(out, out_file)
    else:
        torch.save(out, out_file)
    total_missed = int(out['y'].sum())
    print(f"[harvest] saved {out_file}  kept={kept}  "
          f"total_missed_atoms={total_missed}  "
          f"frac_frames_with_missed={float((out['y'].sum(1) > 0).float().mean()):.3f}",
          flush=True)
    return out_file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true',
                    help='Run Prop.1 + Cholesky correctness check and exit.')
    ap.add_argument('--out', type=str, default=None)
    ap.add_argument('--snr', type=int, default=20)
    ap.add_argument('--n-frames', type=int, default=150)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=10)
    ap.add_argument('--tau-ms', type=float, default=10.0)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--M', type=int, default=48)
    ap.add_argument('--p-pad', type=int, default=64)
    ap.add_argument('--seed-base', type=int, default=20260606)
    ap.add_argument('--print-every', type=int, default=50)
    ap.add_argument('--rho', type=float, default=None,
                    help='override SP pilot/data power split (default config 0.5)')
    ap.add_argument('--nomination-cap',type=int,default=None)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--frame-manifest',type=Path,default=None,
                    help='fixed stream9 identities; failed frames are never replaced')
    args = ap.parse_args()

    if args.self_test:
        _self_test(); return
    if args.out is None:
        ap.error('--out required unless --self-test')
    run_harvest(args.out, args.snr, args.n_frames, args.n_total, args.v_mean,
                args.p_paths, args.tau_ms, args.fs_factor, args.M, args.p_pad,
                args.seed_base, print_every=args.print_every, rho_override=args.rho,
                nomination_cap=args.nomination_cap,frame_manifest=args.frame_manifest,resume=args.resume)


if __name__ == '__main__':
    main()
