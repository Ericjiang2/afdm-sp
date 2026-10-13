"""Explicit fresh inputs for the existing full receiver campaign."""
import json
from pathlib import Path
import time
from .bottleneck_pilot import (NAMESPACE, generate_exogenous, hashes, sha,
                               validate_pilot_namespace)
from .supplement_adjacent_run import save_state

EXOGENOUS_KEYS = ('H', 'info', 'coded', 'data', 'pilot', 'noise')


def fresh_namespace(contract):
    if 'fresh_namespace' not in contract:
        if contract.get('engineering_repeat_mean', False):
            raise ValueError('fresh repeat control requires an explicit namespace')
        return None
    namespace = validate_pilot_namespace(contract['fresh_namespace'])
    if namespace == NAMESPACE or contract.get('engineering_repeat_mean') is not True:
        raise ValueError('fresh namespace must differ from pilot and include engineering repeat')
    return namespace


def stage_arms(contract, stage):
    if stage not in ('engineering', 'development'):
        raise ValueError('only engineering and development are permitted')
    arms = list(contract['arms'])
    if fresh_namespace(contract) is not None and stage == 'engineering':
        mean = [arm for arm in arms if arm['name'] == 'MEAN']
        if len(mean) != 1 or mean[0]['receiver'] or any(a['name'] == 'MEAN_REPEAT' for a in arms):
            raise ValueError('fresh engineering requires one unchanged MEAN control')
        arms.append(dict(mean[0], name='MEAN_REPEAT'))
    return arms


def earlier_exogenous(contract, run_root, stage):
    """Read only bound old summaries and the completed new engineering stage."""
    entries = []
    for previous in ('engineering', 'development'):
        name = f'runs/{previous}/summary.json'
        path = Path(contract['old_root']) / name
        if sha(path) != contract['old_inputs'][name]:
            raise ValueError('old disjointness reference changed')
        summary = json.loads(path.read_text())
        if summary['status'] != 'COMPLETE':
            raise ValueError('old input reference is incomplete')
        entries.extend(summary['exogenous'])
    if stage == 'development':
        summary = json.loads((Path(run_root)/'engineering/summary.json').read_text())
        if summary['status'] != 'COMPLETE' or summary.get('fresh_namespace') != contract['fresh_namespace']:
            raise ValueError('new engineering namespace differs')
        entries.extend(summary['exogenous'])
    return entries


def require_unused_inputs(identity_hashes, previous):
    for key in ('H', 'info', 'noise'):
        if identity_hashes[key] in {entry['hashes'][key] for entry in previous}:
            raise ValueError('fresh input collides with an earlier block: '+key)


def save_fresh_input(run, system, code, block, split, namespace, previous):
    run.check()
    identity = dict(block=block, split=split, namespace=list(namespace))
    run.write(f'exogenous-{block:03d}-reserve.json', dict(identity, reserved_at=time.time()))
    started = time.perf_counter()
    raw = generate_exogenous(system, code, block, split=split, namespace=namespace)
    identity_hashes = hashes({key: raw[key] for key in EXOGENOUS_KEYS})
    require_unused_inputs(identity_hashes, previous)
    run.check()
    state = save_state(run.out/f'exogenous-{block:03d}.npz', raw, run.meter, readback=True)
    entry = dict(identity, state=state, hashes=identity_hashes,
                 generation_seconds=time.perf_counter()-started)
    run.write(f'exogenous-{block:03d}.json', entry)
    return raw, entry
