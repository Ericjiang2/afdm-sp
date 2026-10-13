"""Offline actual-normalization prior audit on three saved physical geometries.

No receiver, decoder, make_frame, channel-matrix generator or observation draw.
The only legacy RNG replay recovers omitted latent PDP from original seeds.
"""
import argparse
import importlib
import json
from pathlib import Path
import sys

import numpy as np

from experiments.afdm_shared_channel_20261004.common import ROOT, dump, run
from experiments.afdm_shared_channel_20261004.production_diagnostic import OLD, sha, source_paths, verify_saved_sources
from experiments.afdm_shared_channel_20261004.quadrature import independent_nodes, validate_nodes

UP = ROOT/'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff'
CONFIG = dict(seed=[20261004, 110000, 11], exponents=[12, 15, 18], scrambles=[2301, 2302],
              laplace_orders=[64, 128, 256],
              saved_clusters=3, receiver_calls=0, decoder_calls=0, new_observations=0,
              old_channel_latent_replays=3, scope='offline oracle geometry and latent-PDP prior audit',
              models=['iid_gaussian', 'unit_sphere', 'pdp_sphere', 'actual_g0_normalized'],
              relative_refinement_tolerance=.01, identity_tolerance=1e-11,
              normalization='h=D^1/2*s/sqrt(s^H*D^1/2*R_G0*D^1/2*s)')


def frozen_components():
    """Import the existing physical/config helpers exclusively from frozen UP."""
    for name, module in tuple(sys.modules.items()):
        if name == 'afdm_sp_joint_unrolled' or name.startswith('afdm_sp_joint_unrolled.'):
            locations = [getattr(module, '__file__', None), *getattr(module, '__path__', [])]
            if any(p and not Path(p).resolve().is_relative_to(UP) for p in locations):
                raise RuntimeError('non-frozen AFDM module already loaded')
    saved_path = sys.path.copy()
    try:
        sys.path[:] = [str(UP)] + [p for p in sys.path if p and not (Path(p)/'afdm_sp_joint_unrolled').is_dir()]
        env = importlib.import_module('afdm_sp_joint_unrolled.afdm_env')
        diagnostics = importlib.import_module('afdm_sp_joint_unrolled.budgeted_support_diagnostics')
        factory = importlib.import_module('afdm_sp_joint_unrolled.loop9_cache_features')
        return env.AFDMEnvMixin, diagnostics.physical_cluster_weights, factory._make_config_a
    finally:
        sys.path[:] = saved_path


def normalization_gram(system, delays, dopplers):
    """R_ij=<A_i,A_j>_F/N = W^H W in the legal orthogonal integer basis.

    Reuses the exact original Dirichlet normalization, clipping and pruning.
    Distinct integer delays must lie in [0,N); virtual k have no modulo-N alias.
    Physical paths themselves may repeat, retaining off-diagonal cross terms.
    """
    delays, dopplers = np.asarray(delays), np.asarray(dopplers, float)
    if (delays.ndim != 1 or delays.shape != dopplers.shape or not len(delays)
            or not np.issubdtype(delays.dtype, np.integer) or np.any(delays < 0)
            or np.any(delays > system.l_max_cap) or system.l_max_cap >= system.N_total
            or not np.isfinite(dopplers).all() or system.gen_h_daft_convention != 'python'
            or not system.use_frac_doppler or 2*system.k_max_cap >= system.N_total):
        raise ValueError('G0 Gram requires legal frozen fractional Python geometry')
    _, weights, _ = frozen_components()
    w = weights(system, dict(taps=len(delays), l_i=delays, k_real=dopplers))
    return w.conj().T@w, w


def dense_gram(system, weights):
    """Independent actual gen_h_daft basis contractions; small matrices in tests."""
    width = 2*system.k_max_cap+1
    ids = np.flatnonzero(np.any(weights != 0, axis=1))
    matrices = [system.gen_h_daft(weights[ids, p], ids//width, ids % width-system.k_max_cap)
                for p in range(weights.shape[1])]
    return np.array([[np.vdot(a, b)/system.N_total for b in matrices] for a in matrices])


def normalize_gain(nodes, gram):
    nodes, gram = np.asarray(nodes, complex), np.asarray(gram, complex)
    if nodes.ndim != 2 or gram.shape != (nodes.shape[1], nodes.shape[1]):
        raise ValueError('gain/Gram dimensions disagree')
    if not np.isfinite(nodes).all() or not np.isfinite(gram).all():
        raise ValueError('nonfinite gain/Gram')
    if not np.allclose(gram, gram.conj().T, atol=1e-13, rtol=1e-13):
        raise ValueError('normalization Gram must be Hermitian')
    if np.linalg.eigvalsh(gram).min() < -1e-12:
        raise ValueError('normalization Gram must be PSD')
    power = np.einsum('bi,ij,bj->b', nodes.conj(), gram, nodes).real
    if np.any(power <= 0):
        raise ValueError('normalization undefined on zero Gram power')
    return nodes/np.sqrt(power)[:, None]


def pushforward_nodes(sphere, weights, pdp, gram):
    sphere, weights = validate_nodes(sphere, weights)
    pdp = np.asarray(pdp, float)
    if pdp.shape != (sphere.shape[1],) or not np.isfinite(pdp).all() or np.any(pdp <= 0):
        raise ValueError('positive finite conditional PDP required')
    return validate_nodes(normalize_gain(sphere*np.sqrt(pdp), gram), weights)


def recover_latent(system, truth):
    """Replay just the original saved channel stream, then demand archive parity.

    This does not call generate_channel_matrix or make_frame. Only latent PDP,
    delay/gain/velocity arrays of the already saved observation are recovered.
    """
    words = np.frombuffer(bytes.fromhex(truth['stream_ids']['channel']), dtype='<u4').astype(np.uint32).tolist()
    stream = np.random.default_rng(np.random.SeedSequence(words))
    channel_seed = int(stream.integers(0, 2**31))
    before = np.random.get_state()
    try:
        np.random.seed(channel_seed)
        delays, raw, index, pdp, doppler_a, velocities, attempts = system.generate_uwa_channel()
    finally:
        np.random.set_state(before)
    physical_delays = np.clip(np.round(delays/system.delay_resolution).astype(int), 0, system.l_max_cap)
    clip = min(system.k_max_cap, int(np.floor(system.N_total/2)-system.k_guard-1))
    physical_nu = np.clip(doppler_a*system.fc/system.fs*system.N_total, -clip, clip)
    saved_raw = truth['g_i']/truth['diagnostics']['g0_fro_scale']
    errors = dict(raw_gain=float(np.max(abs(raw-saved_raw))),
                  doppler=float(np.max(abs(physical_nu-truth['k_real']))),
                  raw_energy=abs(float(np.vdot(raw, raw).real)-1))
    if not np.array_equal(physical_delays, truth['l_i']) or max(errors.values()) > CONFIG['identity_tolerance']:
        raise AssertionError('saved latent replay does not match original physical arrays')
    return dict(pdp=pdp, raw_gain=raw, saved_raw_gain=saved_raw, channel_seed=channel_seed,
                delay_index=index, velocity=velocities, replay_attempts=attempts, errors=errors)


def projection_directions(system, delays, dopplers, pilot):
    from experiments.afdm_structured_inference_20261003.collapsed import PHYSICAL
    p = len(delays)
    channel = PHYSICAL.Channel(system.N_total, system.c1, system.c2, delays, dopplers, np.ones(p))
    response = channel.regressors(pilot)
    directions = np.column_stack((np.eye(p)[:, 0], np.eye(p)[:, -1],
                                  response[0].conj(), response[system.N_total//3].conj()))
    directions /= np.linalg.norm(directions, axis=0)
    return directions


def gain_moments(nodes, weights, directions):
    projections = nodes@directions.conj()
    energy = np.sum(abs(nodes)**2, axis=1)
    covariance = np.einsum('b,bi,bj->ij', weights, nodes, nodes.conj(), optimize=True)
    second = weights@(abs(projections)**2)
    fourth = weights@(abs(projections)**4)
    return dict(mean=weights@nodes, covariance=covariance, second=second, fourth=fourth,
                energy_mean=float(weights@energy), energy_second=float(weights@(energy**2)))


def relative_moment_error(first, second):
    return max(float(np.max(abs(first[k]-second[k])/np.maximum(abs(second[k]), 1e-12)))
               for k in ('second', 'fourth'))


def diagonal_laplace_moments(pdp, gram, directions, order):
    """Independent positive 1-D quadrature of analytic exponential integrals.

    Available only for diagonal R and independent phases. If X_i~Exp(1),
    denominator=sum_i R_ii D_i X_i; use 1/z=int exp(-tz)dt and
    1/z^2=int t exp(-tz)dt. These integrals are not called numerically exact.
    """
    pdp, gram = np.asarray(pdp, float), np.asarray(gram, complex)
    if not np.allclose(gram, np.diag(np.diag(gram)), rtol=0, atol=1e-13):
        raise ValueError('Laplace phase integration requires a diagonal normalization Gram')
    a = pdp*np.diag(gram).real
    if np.any(a <= 0) or order < 2:
        raise ValueError('positive diagonal rates and quadrature order required')
    axis, weights = np.polynomial.legendre.leggauss(order)
    u, weights = (axis+1)/2, weights/2
    scale = np.exp(np.mean(np.log(a)))
    t = u/((1-u)*scale)
    weights = weights/(scale*(1-u)**2)
    q = 1/(1+t[:, None]*a)
    product = np.prod(q, axis=1)
    second_gain = pdp*((weights*product)@q)
    fourth_gain = np.outer(pdp, pdp)*np.einsum('b,bi,bj->ij', weights*t*product, q, q)
    fourth_gain[np.diag_indices_from(fourth_gain)] *= 2
    power = abs(directions)**2
    second = second_gain@power
    fourth = 2*np.einsum('ir,ij,jr->r', power, fourth_gain, power)-np.diag(fourth_gain)@(power**2)
    return dict(second=second, fourth=fourth, energy_mean=float(np.sum(second_gain)),
                energy_second=float(np.sum(fourth_gain)), covariance=np.diag(second_gain))


def calculate(output):
    verify_saved_sources()
    _, _, factory = frozen_components()
    from experiments.afdm_inference_causal_20261002.oracle_comparison import _load
    threads = _load('normalization_thread_binding', ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py')
    binding = threads.blas_binding()
    dump(output/'threads.json', binding)
    # Physical configuration only: this constructor does not build a receiver.
    system = factory(1024, 2., 8, 10., 4.)
    evidence = _load('production_prior_evidence', ROOT/'experiments/sp_afdm_frozen_20260920/src/evidence.py')
    dump(output/'system.json', {k:getattr(system, k) for k in ('N_total', 'c1', 'c2', 'l_max_cap', 'k_max_cap',
        'k_guard', 'k_leak', 'frac_prune_rel_thres', 'P_paths', 'tau_mean', 'tau_spread', 'att_dB', 'fs', 'Ts',
        'delay_resolution', 'max_delay_idx_bar_supported', 'uwa_resample_max_tries')})
    records, identities = [], []
    for cluster in range(3):
        stem = f'development_f{2*cluster:06d}'
        tp = OLD/'population/truth/data'/(stem+'.npz')
        op = OLD/'population/observed/data'/(stem+'.npz')
        truth, _ = evidence.load_artifact(tp)
        observed, _ = evidence.load_artifact(op)
        if truth['observation_hash'] != observed['observation_hash']:
            raise ValueError('saved truth/observation identity differs')
        latent = recover_latent(system, truth)
        gram, w = normalization_gram(system, truth['l_i'], truth['k_real'])
        raw, saved_gain = latent['raw_gain'], truth['g_i']
        denominator = float(np.vdot(raw, gram@raw).real)
        predicted_scale = 1/np.sqrt(denominator)
        predicted_gain = raw*predicted_scale
        normalized_power = float(np.vdot(saved_gain, gram@saved_gain).real)
        # Independent actual G0 matrix construction only, not a channel draw.
        width = 2*system.k_max_cap+1
        ids = np.flatnonzero(np.any(w != 0, axis=1))
        h0 = system.gen_h_daft((w@raw)[ids], ids//width, ids % width-system.k_max_cap)
        matrix_power = float(np.vdot(h0, h0).real/system.N_total)
        identity = dict(cluster=cluster, observation_id=stem, observation_hash=truth['observation_hash'],
            truth_sha256=sha(tp), observed_sha256=sha(op), raw_replay_errors=latent['errors'],
            replay_attempts=latent['replay_attempts'], channel_seed=latent['channel_seed'],
            gram_eigenvalues=np.linalg.eigvalsh(gram).tolist(), pdp=latent['pdp'].tolist(),
            saved_scale=float(truth['diagnostics']['g0_fro_scale']), predicted_scale=predicted_scale,
            scale_error=abs(predicted_scale-truth['diagnostics']['g0_fro_scale']),
            gain_error=float(np.max(abs(predicted_gain-saved_gain))),
            matrix_power_error=abs(matrix_power-denominator), normalized_gram_power=normalized_power,
            physical_gain_energy=float(np.vdot(saved_gain, saved_gain).real))
        if max(identity['scale_error'], identity['gain_error'], identity['matrix_power_error'], abs(normalized_power-1)) > CONFIG['identity_tolerance']:
            raise AssertionError('actual normalization identity failed')
        if np.linalg.eigvalsh(gram).min() <= 0:
            raise ValueError('saved-geometry bounded moment study requires positive normalization Gram')
        identities.append(identity)
        directions = projection_directions(system, truth['l_i'], truth['k_real'], observed['observation']['pilot'])
        np.savez_compressed(output/f'geometry_{cluster}.npz', gram=gram, weights=w, pdp=latent['pdp'],
            raw_gain=raw, saved_raw_gain=latent['saved_raw_gain'], saved_gain=saved_gain, predicted_gain=predicted_gain,
            delays=truth['l_i'], dopplers=truth['k_real'], directions=directions, delay_index=latent['delay_index'])
        by_key = {}
        for exponent in CONFIG['exponents']:
            for scramble in CONFIG['scrambles']:
                gaussian, weights = independent_nodes(len(raw), 1., exponent, scramble, normalized=False)
                sphere = normalize_gain(gaussian, np.eye(len(raw)))
                models = dict(iid_gaussian=gaussian, unit_sphere=sphere,
                    pdp_sphere=normalize_gain(sphere*np.sqrt(latent['pdp']), np.eye(len(raw))),
                    actual_g0_normalized=pushforward_nodes(sphere, weights, latent['pdp'], gram)[0])
                if cluster == 0:
                    np.savez_compressed(output/f'base_{exponent}_{scramble}.npz', gaussian_nodes=gaussian, weights=weights)
                raw_output = {}
                for name, nodes in models.items():
                    moments = gain_moments(nodes, weights, directions)
                    by_key[(exponent, scramble, name)] = moments
                    raw_output.update({name+'_'+k:v for k, v in moments.items()})
                    records.append(dict(cluster=cluster, exponent=exponent, scramble=scramble, model=name,
                        second=moments['second'].tolist(), fourth=moments['fourth'].tolist(),
                        energy_mean=moments['energy_mean'], energy_variance=moments['energy_second']-moments['energy_mean']**2,
                        covariance_trace=float(np.trace(moments['covariance']).real)))
                np.savez_compressed(output/f'moments_{cluster}_{exponent}_{scramble}.npz', **raw_output)
        refinements = []
        fine, coarse = CONFIG['exponents'][-1], CONFIG['exponents'][-2]
        for name in CONFIG['models']:
            for scramble in CONFIG['scrambles']:
                refinements.append(dict(model=name, comparison='nested refinement', scramble=scramble,
                    relative_error=relative_moment_error(by_key[(coarse, scramble, name)], by_key[(fine, scramble, name)])))
            refinements.append(dict(model=name, comparison='independent fine scramble',
                relative_error=relative_moment_error(by_key[(fine, CONFIG['scrambles'][0], name)], by_key[(fine, CONFIG['scrambles'][1], name)])))
        identities[-1]['refinements'] = refinements
        identities[-1]['numerically_refined'] = max(r['relative_error'] for r in refinements) <= CONFIG['relative_refinement_tolerance']
        p = len(raw)
        identities[-1]['analytic_control_errors'] = {}
        for name, fourth in (('iid_gaussian', 2/p**2), ('unit_sphere', 2/(p*(p+1)))):
            exact = dict(second=np.full(directions.shape[1], 1/p), fourth=np.full(directions.shape[1], fourth))
            identities[-1]['analytic_control_errors'][name] = max(relative_moment_error(by_key[(fine, s, name)], exact)
                                                                  for s in CONFIG['scrambles'])
        laplace_rows = []
        for model, matrix in (('actual_g0_normalized', gram), ('pdp_sphere', np.eye(p))):
            laplace = {order:diagonal_laplace_moments(latent['pdp'], matrix, directions, order)
                       for order in CONFIG['laplace_orders']}
            reference = laplace[CONFIG['laplace_orders'][-1]]
            laplace_rows.append(dict(model=model, second=reference['second'].tolist(), fourth=reference['fourth'].tolist(),
                energy_mean=reference['energy_mean'], energy_variance=reference['energy_second']-reference['energy_mean']**2,
                refinement_error=relative_moment_error(laplace[CONFIG['laplace_orders'][-2]], reference),
                sobol_reference_errors={str(s):relative_moment_error(by_key[(fine, s, model)], reference) for s in CONFIG['scrambles']}))
        identities[-1]['independent_laplace_reference'] = laplace_rows
        identities[-1]['numerically_refined'] = bool(identities[-1]['numerically_refined']
            and max(identities[-1]['analytic_control_errors'].values()) <= CONFIG['relative_refinement_tolerance']
            and max(max(r['refinement_error'], *r['sobol_reference_errors'].values()) for r in laplace_rows)
                <= CONFIG['relative_refinement_tolerance'])
    dump(output/'identities.json', identities)
    dump(output/'moments.json', records)
    verify_saved_sources()
    if threads.blas_binding() != binding:
        raise RuntimeError('effective BLAS binding changed during prior audit')
    return dict(identities=identities, cases=records, receiver_calls=0, decoder_calls=0, new_observations=0,
        old_channel_latent_replays=3, all_refined=all(r['numerically_refined'] for r in identities),
        prior='conditional on each recovered original latent PDP and saved geometry; not the unconditional production prior',
        scope='offline oracle prior moments; not deployable geometry/PDP or posterior/FER evidence',
        quadrature='positive equal-weight scrambled Sobol pushforward; analytic transformation, numerical moment reference',
        convergence='all cases retained including unresolved refinement; no successful-subset selection')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    sources = [*source_paths(), __file__, Path(__file__).with_name('test_production_prior.py'),
               Path(__file__).with_name('quadrature.py')]
    run(args.stage, CONFIG, sources, calculate, wall_seconds=600)


if __name__ == '__main__':
    main()
