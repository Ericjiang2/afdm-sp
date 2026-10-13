"""Frozen paired development pilot. Run only after admission on SSH."""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
from statistics import NormalDist
import time

import numpy as np
import scipy

from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol, thread_binding
from .config import CONFIG_PATH, load_config
from .core import estimate, waveform


def array_hash(value):
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode())
    digest.update(json.dumps(list(array.shape)).encode())
    digest.update(array.tobytes())
    return digest.hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def paired_interval(differences, probability=.95):
    values = np.asarray(differences, float)
    if values.ndim != 2 or values.shape[1] < 2 or not np.isfinite(values).all() or not 0 < probability < 1:
        raise ValueError('finite equally sized paired cells with at least two groups required')
    cells, groups = values.shape
    mean = float(np.mean(values.mean(axis=1)))
    variance = float(np.sum(np.var(values, axis=1, ddof=1))/(cells*cells*groups))
    standard_error = float(np.sqrt(variance))
    quantile = NormalDist().inv_cdf((1+probability)/2)
    return dict(mean=mean, standard_error=standard_error,
                interval=[mean-quantile*standard_error, mean+quantile*standard_error],
                probability=probability, method='exploratory paired normal approximation across fixed equal-weight cells')


def wrapped_error(estimate_value, truth, period):
    return float((estimate_value-truth+period/2) % period-period/2)


def summarize(records, config):
    methods = ['current_analytic', 'current_grid', 'zero_analytic', 'designed_analytic']
    cells, differences = [], []
    for n, t, snr in product(config['Ns'], config['Ts'], config['snr_db']):
        selected = [row for row in records if (row['N'], row['T'], row['snr_db']) == (n, t, snr)]
        if len(selected) != config['groups_per_cell']:
            raise ValueError('incomplete pilot cell; do not summarize survivors')
        reports = {}
        for method in methods:
            values = [row['estimates'][method] for row in selected]
            full = np.array([value['full_error'] for value in values])
            fractional = np.array([value['fractional_error'] for value in values])
            reports[method] = dict(count=len(values), full_rmse=float(np.sqrt(np.mean(full*full))),
                fractional_rmse=float(np.sqrt(np.mean(fractional*fractional))),
                catastrophic_count=sum(value['catastrophic'] for value in values),
                catastrophic_fraction=float(np.mean([value['catastrophic'] for value in values])),
                flat_count=sum(value['flat'] for value in values),
                near_tie_count=sum(value['near_tie'] for value in values),
                total_elapsed_seconds=sum(value['elapsed_seconds'] for value in values),
                total_fft_vectors=sum(value['counts']['fft_vectors'] for value in values),
                total_search_objectives=sum(value['counts']['search_objective_evaluations'] for value in values),
                total_objectives_including_final=sum(value['counts']['total_objective_evaluations'] for value in values))
        differences.append([int(row['estimates']['current_analytic']['catastrophic'])
                            -int(row['estimates']['designed_analytic']['catastrophic']) for row in selected])
        elapsed_ratio = (reports['current_grid']['total_elapsed_seconds']
                         /reports['current_analytic']['total_elapsed_seconds'])
        cells.append(dict(N=n, T=t, snr_db=snr, methods=reports,
                          grid_over_analytic_elapsed_ratio=elapsed_ratio,
                          paired_catastrophe_reduction=float(np.mean(differences[-1]))))
    interval = paired_interval(differences, config['normal_interval_probability'])
    search_ratio = config['grid_size']/len(config['fractional_evaluations'])
    numerical_pass = all(row['objective_dominance'] for row in records)
    total_grid = sum(cell['methods']['current_grid']['total_elapsed_seconds'] for cell in cells)
    total_analytic = sum(cell['methods']['current_analytic']['total_elapsed_seconds'] for cell in cells)
    return dict(cells=cells, design=interval,
                useful_design_pilot_signal=(interval['mean'] >= config['minimum_mean_catastrophe_reduction']
                                           and interval['interval'][0] > 0),
                computation=dict(objective_dominance_every_group=numerical_pass,
                    search_objective_ratio=search_ratio,
                    including_final_objective_ratio=(config['grid_size']+1)/4,
                    grid_over_analytic_complete_elapsed_ratio=total_grid/total_analytic,
                    useful_bounded_computation=(numerical_pass
                        and search_ratio >= config['minimum_objective_evaluation_ratio']),
                    baseline_limit='64-point grid for the same estimator, not the established classical three-point CFO method'),
                all_groups_retained=len(records), confirmatory=False,
                model=config['model'], evidence=config['evidence'])


def calculate(output, config):
    generator = np.random.default_rng(config['seed'])
    records = []
    counts = dict(paired_groups=0, waveform_datasets=0, new_observations=0,
                  complex_scalars=0, geometry_probes=0, receiver_calls=0, decoder_calls=0,
                  generation_ifft_vectors=0, cfo_estimator_calls=0,
                  estimator_fft_vectors=0, estimator_search_objectives=0,
                  estimator_total_objectives=0)
    raw_directory = output/'groups'
    raw_directory.mkdir(exist_ok=False)
    try:
        for n, t, snr in product(config['Ns'], config['Ts'], config['snr_db']):
            noise_variance = 10.**(-snr/10)
            index = np.arange(n)
            chirps = dict(zero=waveform(n, 0.), current=waveform(n, 1/(10*n*n)),
                          designed=waveform(n, 1/(8*n)))
            for within_cell in range(config['groups_per_cell']):
                group = counts['paired_groups']
                integer = int(generator.integers(-n//2, n//2))
                fractional = float(generator.uniform(-.5, .5))
                phase = float(generator.uniform(0., 2*np.pi))
                states = generator.integers(0, 4, size=(t, n))
                symbols = np.exp(1j*(np.pi/4+np.pi/2*states))
                standard_noise = (generator.standard_normal((t, n))
                                  +1j*generator.standard_normal((t, n)))/np.sqrt(2)
                frequency, gain = integer+fractional, np.exp(1j*phase)
                observations = {}
                for label in config['waveforms']:
                    if counts['new_observations']+t > config['new_observations']:
                        raise RuntimeError('observation budget exceeded before construction')
                    row, column = chirps[label]
                    counts['generation_ifft_vectors'] += t
                    signal = gain*np.exp(2j*np.pi*frequency*index/n)*row*np.fft.ifft(
                        symbols*column, axis=1, norm='ortho')
                    observations[label] = signal+np.sqrt(noise_variance)*standard_noise
                    counts['waveform_datasets'] += 1
                    counts['new_observations'] += t
                    counts['complex_scalars'] += t*n
                folder = raw_directory/f'group_{group:04d}'
                folder.mkdir(exist_ok=False)
                raw_path = folder/'raw.npz'
                with raw_path.open('xb') as handle:
                    np.savez_compressed(handle, states=states, symbols=symbols, standard_noise=standard_noise,
                        integer=integer, fractional=fractional, phase=phase, frequency=frequency,
                        gain=gain, noise_variance=noise_variance,
                        **{f'Y_{label}': value for label, value in observations.items()},
                        **{f'{label}_{name}': chirps[label][position] for label in config['waveforms']
                           for position, name in enumerate(['R', 'C'])})
                order = ['current_analytic', 'current_grid']
                if group % 2:
                    order.reverse()
                order += ['zero_analytic', 'designed_analytic']
                estimates, arrays = {}, {}
                for method_label in order:
                    label, method = method_label.split('_')
                    counts['cfo_estimator_calls'] += 1
                    started = time.perf_counter()
                    result = estimate(observations[label], *chirps[label], method=method,
                        grid_size=config['grid_size'], flat_relative=config['flat_relative'],
                        tie_relative=config['tie_relative'])
                    elapsed = time.perf_counter()-started
                    if elapsed <= 0 or not np.isfinite(elapsed):
                        raise RuntimeError('invalid complete estimator timing')
                    counts['estimator_fft_vectors'] += result['counts']['fft_vectors']
                    counts['estimator_search_objectives'] += result['counts']['search_objective_evaluations']
                    counts['estimator_total_objectives'] += result['counts']['total_objective_evaluations']
                    array_keys = ['search_frequencies', 'search_objectives', 'fourth_power_mean', 'integer_scores']
                    arrays.update({f'{method_label}_{key}': result[key] for key in array_keys})
                    scalar = {key: value for key, value in result.items() if key not in array_keys}
                    full_error = wrapped_error(result['frequency'], frequency, n)
                    scalar.update(full_error=full_error,
                                  fractional_error=wrapped_error(result['fractional'], frequency, 1.),
                                  catastrophic=abs(full_error) > config['catastrophic_error_threshold'],
                                  elapsed_seconds=float(elapsed), Y_sha256=array_hash(observations[label]))
                    estimates[method_label] = scalar
                estimate_path = folder/'estimates.npz'
                with estimate_path.open('xb') as handle:
                    np.savez_compressed(handle, **arrays)
                analytic_value = estimates['current_analytic']['objective']
                grid_value = estimates['current_grid']['objective']
                dominance = analytic_value <= grid_value+config['objective_relative_tolerance']*abs(grid_value)
                record = dict(group=group, within_cell=within_cell, N=n, T=t, snr_db=snr,
                    integer=integer, fractional=fractional, frequency=frequency, phase=phase,
                    estimator_order=order, estimates=estimates, objective_dominance=bool(dominance),
                    analytic_minus_grid_objective=analytic_value-grid_value,
                    raw_path=str(raw_path.relative_to(output)), raw_sha256=file_hash(raw_path),
                    estimates_path=str(estimate_path.relative_to(output)), estimates_sha256=file_hash(estimate_path),
                    scope=config['model'], random_observation_vectors=3*t)
                dump(folder/'record.json', record)
                records.append(record)
                counts['paired_groups'] += 1
        expected = dict(paired_groups=config['paired_groups'], waveform_datasets=config['waveform_datasets'],
                        new_observations=config['new_observations'], complex_scalars=config['new_complex_scalars'],
                        cfo_estimator_calls=4*config['paired_groups'],
                        generation_ifft_vectors=config['new_observations'])
        if any(counts[key] != value for key, value in expected.items()):
            raise RuntimeError(f'incomplete generation accounting: {counts}')
        result = summarize(records, config)
        dump(output/'records.json', records)
        dump(output/'summary.json', result)
        dump(output/'work_counts.json', counts)
        if not result['computation']['objective_dominance_every_group']:
            raise AssertionError('analytic objective mismatch; all paired groups retained')
        return dict(**result, **counts, accounting='new_observations counts waveform-specific N-vectors; source S/noise paired across three waveforms')
    except BaseException:
        dump(output/'partial_work_counts.json', counts)
        raise


def preload():
    # Trigger lazy random-module import without creating a stream or drawing.
    return scipy.__version__, np.random.Generator, thread_binding.blas_binding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage')
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--config', type=Path, default=CONFIG_PATH)
    parser.add_argument('--wall-seconds', type=int, default=300)
    parser.add_argument('--print-config', action='store_true')
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    config = load_config(args.config)
    if args.print_config:
        print(json.dumps(config, indent=2))
        return
    preload()
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if not args.stage or args.artifact_root is None:
        parser.error('--stage and --artifact-root are required')
    registered = dict(study=config, phase='pilot', seed=config['seed'], new_observations=config['new_observations'],
                      new_geometry_probes=0, receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)

    def callback(output):
        return calculate(output, config)

    protocol.run(args.stage, registered, [args.config.resolve()], callback,
                 artifact_root=args.artifact_root, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
