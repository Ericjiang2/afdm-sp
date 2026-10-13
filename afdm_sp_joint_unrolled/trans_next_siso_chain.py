"""Bounded exact-SISO full-chain engineering on previously audited inputs."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha, offline_scores
from .budgeted_support_eval import build_receiver
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record
from .light_gap_receiver_run import NUMERIC_FIELDS, run_arm, receiver_resources


def execute(args):
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('SISO source or contract changed')
    c = json.loads(args.contract.read_text())
    stage = c.get('stage', 'engineering')
    if stage not in ('engineering', 'development'):
        raise ValueError('unknown SISO campaign stage')
    engineering = stage == 'engineering'
    names = (['MEAN', 'REFRESH47', 'SISO_MEAN', 'SISO_REF47', 'SISO_REF47_REPEAT']
             if engineering else ['SISO_MEAN', 'SISO_REF47'])
    blocks = [0, 1] if engineering else list(range(32))
    if (c['schema'] != 'trans-siso-chain-v1' or c['device'] != 'cpu' or c['threads'] != 1
            or c['blocks'] != blocks or c['snrs'] != [7, 8] or c['F_limit'] != len(blocks)*2*len(names)
            or args.root.name != c['tag'] or sha(c['input_summary']) != c['input_summary_sha256']
            or sha(c['checkpoint_path']) != c['checkpoint_sha256']
            or [a['name'] for a in c['arms']] != names):
        raise ValueError('unregistered SISO engineering boundary')
    if not engineering:
        if sha(c['engineering_admission']) != c['engineering_admission_sha256']:
            raise ValueError('missing or changed raw engineering admission')
        admission = json.loads(Path(c['engineering_admission']).read_text())
        if (admission['status'] != 'PASS' or admission['records'] != 20 or admission['SISO_states'] != 132
                or admission['source_sha256'] != c['engineering_source_sha256']):
            raise ValueError('engineering raw qualification incomplete')
        producer_manifest = json.loads(Path(c['engineering_source_manifest']).read_text())
        if sha(c['engineering_source_manifest']) != c['engineering_source_sha256']:
            raise ValueError('engineering source identity changed')
        for name, digest in producer_manifest.items():
            if name != 'trans_next_siso_chain.py' and sha(Path(__file__).parent/name) != digest:
                raise ValueError('development changed a qualified algorithm: '+name)
    for arm in c['arms']:
        expected = dict(detector='siso_mmse') if arm['name'].startswith('SISO') else {}
        refresh = [4, 7] if arm['name'] in ('REFRESH47', 'SISO_REF47', 'SISO_REF47_REPEAT') else []
        if arm['receiver'] != expected or arm.get('feedback', {}).get('refresh_checkpoints', []) != refresh:
            raise ValueError('SISO/reference algorithm changed')
    guard = setup_guard(args, c)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(args.root, stage, dict(F=c['F_limit'], seconds=c['seconds']), c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        inputs = json.loads(Path(c['input_summary']).read_text())
        env = json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
        if inputs['status'] != 'COMPLETE' or hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
            raise ValueError('incomplete engineering input or different LDPC')
        exo = {e['block']: e for e in inputs['exogenous']}
        refs = {(r['block'], r['snr'], r['arm']): r for r in inputs['records']}
        system = _make_config_a(1024, 2., 8, 10., 4.)
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        run.write('environment.json', dict(code_identity=env['code_identity'], numpy=np.__version__,
            torch=torch.__version__, device='cpu', threads=1, initial_lstsq_driver='gels',
            input_summary_sha256=c['input_summary_sha256']))
        checks, totals = [], {}
        for block in c['blocks']:
            raw = load_state(exo[block]['state'])
            if hashes({k: raw[k] for k in exo[block]['hashes']}) != exo[block]['hashes']:
                raise ValueError('engineering raw input changed')
            for snr in c['snrs']:
                observed = observed_at_snr(raw, snr)
                before = hashes(observed)
                repeat = {}
                offset = (block+snr) % len(c['arms'])
                for arm in c['arms'][offset:]+c['arms'][:offset]:
                    def full():
                        value = run_arm(receiver, code, observed, arm)
                        value['resource_counts'] = receiver_resources(value)
                        expected_decoders = 2+len(arm.get('feedback', {}).get('refresh_checkpoints', []))
                        resources = value['resource_counts']
                        if not value['baseline_eligible'] or resources['LDPC_calls'] != expected_decoders or resources['CE_solves'] != 9:
                            raise ValueError('incomplete full-chain engineering arm')
                        if arm['name'].startswith('SISO'):
                            if resources['SISO_factorizations'] != 11 or resources['SISO_rhs'] != 11275:
                                raise ValueError('SISO solve accounting differs')
                            if len(value['siso_states']) != 10:
                                raise ValueError('missing actual outer SISO states')
                        return value
                    identity = dict(block=block, snr=snr, split=exo[block]['split'], arm=arm['name'])
                    value, record = run.call('F', identity, full, lambda v: offline_scores(v, raw, v['H']),
                        dict(observed_hashes=before, configuration=arm, exogenous_hashes=exo[block]['hashes'],
                            scope=c['scope'], input_summary_sha256=c['input_summary_sha256']))
                    if hashes(observed) != before:
                        raise ValueError('receiver mutated paired observation')
                    _, saved = verified_record(run.records[-1], args.root)
                    for field in NUMERIC_FIELDS:
                        np.testing.assert_array_equal(saved[field], value[field])
                    if offline_scores(saved, raw, saved['H']) != record['scores']:
                        raise ValueError('saved full-chain score differs')
                    for key, count in saved['resource_counts'].items():
                        totals[key] = totals.get(key, 0)+count
                    if arm['name'] in ('MEAN', 'REFRESH47'):
                        _, reference = verified_record(refs[block, snr, arm['name']], Path(c['reference_root']))
                        for field in NUMERIC_FIELDS:
                            np.testing.assert_array_equal(value[field], reference[field])
                    elif arm['name'] != 'SISO_MEAN':
                        repeat[arm['name']] = {field: saved[field] for field in NUMERIC_FIELDS}
                    checks.append(dict(**identity, resources=saved['resource_counts'], seconds=record['seconds'],
                        old_BP_exact=arm['name'] in ('MEAN', 'REFRESH47'), readback_scores_exact=True,
                        max_solve_residual=max([v['linear_relative_residual'] for v in saved.get('siso_calls', [])]
                            +[saved.get('terminal_siso', {}).get('linear_relative_residual', 0.)])
                            if arm['name'].startswith('SISO') else None))
                    print(json.dumps(dict(**identity, calls=run.counts, scores=record['scores'])), flush=True)
                    del value, saved
                if engineering:
                    for field in NUMERIC_FIELDS:
                        np.testing.assert_array_equal(repeat['SISO_REF47'][field], repeat['SISO_REF47_REPEAT'][field])
        guard.verify()
        if sha(c['input_summary']) != c['input_summary_sha256'] or sha(c['checkpoint_path']) != c['checkpoint_sha256']:
            raise ValueError('engineering input identity changed')
        if not engineering and sha(c['engineering_admission']) != c['engineering_admission_sha256']:
            raise ValueError('engineering admission changed during development')
        run.write('summary.json', dict(status='COMPLETE', stage=stage, records=run.records, checks=checks, calls=run.counts,
            resource_totals=totals, SISO_repeat_exact=True if engineering else None, exogenous=[exo[b] for b in c['blocks']],
            contract_sha256=args.contract_sha256, source_sha256=args.source_sha256,
            input_summary_sha256=c['input_summary_sha256'], wall_seconds=time.time()-run.started, scope=c['scope']))
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):
        parser.add_argument('--'+name, required=True)
    execute(parser.parse_args())
