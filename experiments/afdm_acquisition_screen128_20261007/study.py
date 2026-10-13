"""P/A immutable stages, with unchanged prior design references. Scientific runs require admitted SSH snapshots."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import scipy.special
from scipy.stats import beta

from experiments.afdm_phase_information_20261006.study import array_hash, file_hash, paired_interval
from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol, thread_binding
from .core import ARMS, METHODS, estimate, simulate

CONFIG_PATH = Path(__file__).with_name('STUDY_CONFIG.json')
CONFIG_SHA256 = '1a556ab95e91706858c96c057557cb88c3629d3ce03076a79d6cc8a7c64b581b'
ARRAY_KEYS = ('hypotheses', 'profile_scores', 'best_gain_indices', 'fourth_scores')


def save_npz(path, values):
    with path.open('xb') as handle:
        np.savez_compressed(handle, **values)


def summarize(records, config):
    cells, differences = [], []
    bad = reverse = 0
    totals = {f'{arm}_{method}': 0. for arm in ARMS for method in METHODS}
    for n in config['Ns']:
        for snr in config['snr_db']:
            selected = [r for r in records if r['N'] == n and r['snr_db'] == snr]
            if len(selected) != config['groups_per_cell']:
                raise ValueError('incomplete cell; never summarize successful survivors')
            errors, elapsed = {}, {}
            for key in totals:
                errors[key] = sum(r['estimates'][key]['error'] for r in selected)
                elapsed[key] = sum(r['estimates'][key]['elapsed_seconds'] for r in selected)
                totals[key] += elapsed[key]
            differences.append([int(r['estimates']['quadratic_SCREEN128']['error'])-
                                int(r['estimates']['random_SCREEN128']['error']) for r in selected])
            bad += sum(r['estimates']['random_SCREEN128']['error'] and
                       not r['estimates']['random_FULL']['error'] for r in selected)
            reverse += sum(r['estimates']['random_FULL']['error'] and
                           not r['estimates']['random_SCREEN128']['error'] for r in selected)
            cells.append(dict(N=n, snr_db=snr, groups=len(selected), error_counts=errors,
                              elapsed_seconds=elapsed,
                              random_speed_ratio=elapsed['random_FULL']/elapsed['random_SCREEN128']))
    interval = paired_interval(differences)
    ratio = totals['random_FULL']/totals['random_SCREEN128']
    gates = dict(dominance=all(all(r['dominance'].values()) for r in records),
                 complete_time_ratio=ratio >= 3., noninferiority=bad <= 12,
                 code_improvement=interval['mean'] >= .10 and interval['interval'][0] > 0,
                 each_cell_usable=all(c['error_counts']['random_SCREEN128']/c['groups'] <= .25 for c in cells))
    return dict(cells=cells, paired_improvement=interval, total_elapsed_seconds=totals,
                random_speed_ratio=ratio, mean_cell_speed_ratio=float(np.mean([c['random_speed_ratio'] for c in cells])),
                bad_discordance=bad, reverse_discordance=reverse,
                binomial_reference_cp_upper=float(beta.ppf(.95, bad+1, len(records)-bad)) if bad < len(records) else 1.,
                noninferiority_interpretation='single iid cell: x<=12 and one-sided95% Clopper-Pearson upper<=.02',
                gates=gates, positive_pilot_signal=all(gates.values()))


def pilot(output, config, design_root):
    if json.loads((design_root/'attempt.json').read_text())['status'] != 'complete':
        raise ValueError('design did not complete')
    receipt = json.loads((design_root/'results.json').read_text())
    if file_hash(design_root/'codes.npz') != receipt['code_file_sha256'] or receipt['code_file_sha256'] != config['reference_code_sha256']:
        raise ValueError('design code hash mismatch')
    with np.load(design_root/'codes.npz', allow_pickle=False) as source:
        codes = {key: source[key] for key in source.files}
    rng = np.random.default_rng(config['pilot_seed'])
    records = []
    counts = dict(paired_groups=0, waveform_datasets=0, new_observations=0,
                  complex_scalars=0, acquisition_calls=0, geometry_probes=0,
                  receiver_calls=0, decoder_calls=0, generation_ifft_vectors=0,
                  attempted_observation_vectors=0, completed_acquisition_calls=0)
    generation_seconds = io_seconds = 0.
    folder, raw, estimates, arrays = None, {}, {}, {}
    operation = 'initialize'
    try:
        for n in config['Ns']:
            for snr in config['snr_db']:
                for within in range(config['groups_per_cell']):
                    group = len(records)
                    folder = output/'groups'/f'{group:04d}'
                    raw, estimates, arrays = {}, {}, {}
                    operation = 'initialize_group'
                    folder.mkdir(parents=True, exist_ok=False)
                    start = time.perf_counter()
                    delay, cfo = int(rng.integers(n//4)), int(rng.integers(n))
                    rho, phase = float(rng.uniform(.75, 1.25)), float(rng.uniform(0, 2*np.pi))
                    gain, sigma2 = rho*np.exp(1j*phase), 10**(-snr/10)
                    shape = (config['T'], n)
                    states = rng.integers(0, 4, size=shape)
                    noise = rng.standard_normal(shape)+1j*rng.standard_normal(shape)
                    raw = dict(states=states, standard_noise=noise, gain=np.array(gain),
                               delay=np.array(delay), cfo=np.array(cfo), sigma2=np.array(sigma2))
                    ys = {}
                    for arm in ARMS:
                        operation = f'generate:{arm}'
                        counts['attempted_observation_vectors'] += config['T']
                        ys[arm] = simulate(states, noise, codes[f'n{n}_{arm}'], delay, cfo, gain, sigma2)
                        raw[f'Y_{arm}'] = ys[arm]
                        counts['waveform_datasets'] += 1
                        counts['new_observations'] += config['T']
                        counts['generation_ifft_vectors'] += config['T']
                        counts['complex_scalars'] += config['T']*n
                    generation_seconds += time.perf_counter()-start
                    start = time.perf_counter()
                    operation = 'save_raw'
                    save_npz(folder/'raw.npz', raw)
                    io_seconds += time.perf_counter()-start
                    order = [f'{arm}_{method}' for arm in ARMS for method in METHODS]
                    offset = group % len(order)
                    order = order[offset:]+order[:offset]
                    for key in order:
                        arm, method = key.split('_')
                        operation = f'estimate:{key}'
                        counts['acquisition_calls'] += 1
                        start = time.perf_counter()
                        answer = estimate(ys[arm], codes[f'n{n}_{arm}'], sigma2, method)
                        elapsed = time.perf_counter()-start
                        if not np.isfinite(elapsed) or elapsed <= 0:
                            raise ValueError('invalid complete-call elapsed time')
                        arrays.update({f'{key}_{name}': answer.pop(name) for name in ARRAY_KEYS})
                        answer.update(elapsed_seconds=elapsed, Y_sha256=array_hash(ys[arm]),
                                      error=bool(answer['delay'] != delay or answer['cfo'] != cfo))
                        estimates[key] = answer
                        counts['completed_acquisition_calls'] += 1
                    start = time.perf_counter()
                    operation = 'save_complete_group'
                    save_npz(folder/'estimates.npz', arrays)
                    dominance = {}
                    for arm in ARMS:
                        full, screen = [estimates[f'{arm}_{method}']['objective'] for method in ('FULL', 'SCREEN128')]
                        dominance[arm] = bool(full >= screen-1e-8-1e-10*abs(screen))
                    row = dict(group=group, within_cell=within, N=n, T=config['T'], snr_db=snr,
                               delay=delay, cfo=cfo, gain=[float(gain.real), float(gain.imag)], sigma2=sigma2,
                               estimator_order=order, estimates=estimates, dominance=dominance,
                               raw_path=str((folder/'raw.npz').relative_to(output)),
                               raw_sha256=file_hash(folder/'raw.npz'),
                               estimates_path=str((folder/'estimates.npz').relative_to(output)),
                               estimates_sha256=file_hash(folder/'estimates.npz'),
                               array_sha256={key: array_hash(value) for key, value in raw.items()})
                    dump(folder/'record.json', row)
                    io_seconds += time.perf_counter()-start
                    records.append(row)
                    counts['paired_groups'] += 1
                    if group % 16 == 15:
                        print(json.dumps(dict(completed_groups=len(records), acquisition_calls=counts['acquisition_calls'])), flush=True)
        expected = dict(paired_groups=1024, waveform_datasets=2048, new_observations=4096,
                        complex_scalars=262144, acquisition_calls=4096, generation_ifft_vectors=4096,
                        attempted_observation_vectors=4096, completed_acquisition_calls=4096)
        if any(counts[k] != v for k, v in expected.items()):
            raise RuntimeError(f'incomplete count contract: {counts}')
        summary = summarize(records, config)
        dump(output/'records.json', records)
        return dict(**counts, **summary, generation_seconds=generation_seconds,
                    raw_io_seconds=io_seconds, waveform_design_sha256=receipt['code_file_sha256'])
    except BaseException as error:
        # Preserve the completed prefix of the active group; never count it as a
        # complete group or overwrite complete raw/record files.
        if folder is not None and folder.is_dir():
            if raw and not (folder/'raw.npz').exists():
                save_npz(folder/'partial_raw.npz', raw)
            if arrays and not (folder/'estimates.npz').exists():
                save_npz(folder/'partial_estimates.npz', arrays)
            dump(folder/'partial_record.json', dict(failed_operation=operation, error=repr(error),
                                                   estimates=estimates, counts=dict(counts)))
        dump(output/'partial_work_counts.json', counts)
        raise


def main():
    process_start = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['P', 'A'])
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    payload = CONFIG_PATH.read_bytes()
    if hashlib.sha256(payload).hexdigest() != CONFIG_SHA256:
        raise ValueError('study config differs from frozen hash')
    config = json.loads(payload)
    # Resolve lazy numerical imports before freezing the thread/source inventory.
    from . import audit
    _ = np.random.Generator, scipy.special.logsumexp, beta.ppf, thread_binding.blas_binding
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.phase is None or args.artifact_root is None:
        parser.error('--phase and --artifact-root required')
    phase = config['phases'][args.phase]
    registered = dict(study=config, phase=args.phase, seed=config['pilot_seed'],
                      new_observations=phase['new_observations'], new_geometry_probes=phase['new_geometry_probes'],
                      receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)
    sources = [CONFIG_PATH]
    sources += sorted((args.artifact_root/'design_reference').glob('*.json'))
    sources += [args.artifact_root/'design_reference'/'codes.npz']
    if args.phase == 'A':
        sources += sorted(p for p in (args.artifact_root/'execution'/'P').rglob('*') if p.is_file())

    def callback(output):
        if args.phase == 'P':
            result = pilot(output, config, args.artifact_root/'design_reference')
        else:
            result = audit.calculate_audit(output, args.artifact_root)
        result['entry_to_callback_end_seconds'] = time.perf_counter()-process_start
        return result

    protocol.run(args.phase, registered, sources, callback, artifact_root=args.artifact_root.resolve(),
                 wall_seconds=phase['wall_seconds'])


if __name__ == '__main__':
    main()
