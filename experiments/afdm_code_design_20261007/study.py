"""Immutable D/A design stages; no channel/noise draws or receiver calls."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from . import core, protocol, thread_binding

CONFIG_PATH = Path(__file__).with_name('STUDY_CONFIG.json')
CONFIG_SHA256 = '65eec42c367a0de17a17377dec04cb6f65c17cc5a4329735571796492b8728e0'


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_npz(path, values):
    with path.open('xb') as handle:
        np.savez_compressed(handle, **values)


def design(output, config, reference):
    if json.loads((reference/'attempt.json').read_text())['status'] != 'complete':
        raise ValueError('historical reference incomplete')
    if file_hash(reference/'codes.npz') != config['reference_code_sha256']:
        raise ValueError('historical reference hash mismatch')
    with np.load(reference/'codes.npz', allow_pickle=False) as code:
        initial = np.angle(code['n64_random']**4)
    if config['N'] != 64 or config['steps'] != 200:
        raise ValueError('foreign design registration')
    phase, first, second = initial.copy(), np.zeros(64), np.zeros(64)
    trace = dict(phases=[], gradients=[], losses=[], mus=[], Qs=[])
    entered = 0
    try:
        for index in range(201):
            entered += 1
            answer = core.evaluate(phase)
            trace['phases'].append(phase.copy())
            trace['gradients'].append(answer['gradient'].copy())
            for key, field in (('losses', 'loss'), ('mus', 'mu'), ('Qs', 'Q')):
                trace[key].append(answer[field])
            if index == 200:
                break
            step = index+1
            gradient = answer['gradient'].copy()
            gradient[0] = 0.
            first = .9*first+.1*gradient
            second = .999*second+.001*gradient**2
            rate = .001+.049*(1+np.cos(np.pi*(step-1)/199))/2
            phase -= rate*(first/(1-.9**step))/(np.sqrt(second/(1-.999**step))+1e-8)
            if not np.isfinite(phase).all() or phase[0] != initial[0]:
                raise FloatingPointError('invalid phase update or changed gauge')
        selected = int(np.argmin(trace['mus']))
        v = np.exp(.25j*np.angle(np.exp(1j*trace['phases'][selected])))
        unit_error = float(np.max(abs(abs(v)-1)))
        arrays = {k: np.asarray(value) for k, value in trace.items()}
        save_npz(output/'design_trace.npz', arrays)
        save_npz(output/'code.npz', dict(v=v))
        qualified = trace['mus'][selected] <= .9*trace['mus'][0] and unit_error <= 1e-12
        return dict(new_observations=0, geometry_probes=entered*1008,
                    objective_evaluations=entered, completed_objective_evaluations=len(trace['mus']),
                    acquisition_calls=0, receiver_calls=0, decoder_calls=0, design_random_draws=0,
                    selected_index=selected, initial_mu=trace['mus'][0], selected_mu=trace['mus'][selected],
                    selected_loss=trace['losses'][selected], selected_Q=trace['Qs'][selected],
                    max_unit_modulus_error=unit_error, design_qualified=bool(qualified),
                    code_sha256=file_hash(output/'code.npz'), trace_sha256=file_hash(output/'design_trace.npz'),
                    reference_code_sha256=config['reference_code_sha256'],
                    scope='Observation-free deterministic200-step code design; no global optimum or acquisition accuracy claim')
    except BaseException as error:
        if not (output/'design_trace.npz').exists():
            save_npz(output/'partial_trace.npz', {k: np.asarray(v) for k, v in trace.items()})
        dump(output/'partial_work_counts.json', dict(entered_objective_evaluations=entered,
              completed_objective_evaluations=len(trace['mus']), error=repr(error),
              geometry_probes=entered*1008, new_observations=0))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['D', 'A'])
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    payload = CONFIG_PATH.read_bytes()
    if hashlib.sha256(payload).hexdigest() != CONFIG_SHA256:
        raise ValueError('design config differs from frozen hash')
    config = json.loads(payload)
    from . import audit
    _ = thread_binding.blas_binding
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.phase is None or args.artifact_root is None:
        parser.error('--phase and --artifact-root required')
    phase = config['phases'][args.phase]
    registered = dict(study=config, phase=args.phase, seed=0, new_observations=0,
                      new_geometry_probes=phase['new_geometry_probes'], receiver_calls=0,
                      decoder_calls=0, acquisition_calls=0, new_confirmation_stream=False)
    sources = [CONFIG_PATH, *sorted((args.artifact_root/'design_reference').glob('*.json')),
               args.artifact_root/'design_reference'/'codes.npz']
    if args.phase == 'A':
        sources += sorted(p for p in (args.artifact_root/'execution'/'D').rglob('*') if p.is_file())

    def callback(output):
        start = time.perf_counter()
        if args.phase == 'D':
            result = design(output, config, args.artifact_root/'design_reference')
        else:
            result = audit.calculate_audit(output, args.artifact_root)
        result['callback_wall_seconds'] = time.perf_counter()-start
        return result

    protocol.run(args.phase, registered, sources, callback, artifact_root=args.artifact_root.resolve(),
                 wall_seconds=phase['wall_seconds'])


if __name__ == '__main__':
    main()
