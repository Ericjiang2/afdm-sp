"""O3: one t=1 true-data CE in the saved G1 full receiver.

The four default-interface calls are a separate admission stage. Auditing only
reads their saved states; it never starts another receiver or decoder.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


SCHEMA = 'oracle-one-shot-v1'
ENGINEERING = [0, 20]
DEVELOPMENT = [b for b in range(32) if b not in ENGINEERING]
SNRS = [7, 8]
ARM = {'default': 'G1_DEFAULT_INTERFACE', 'oracle': 'O3_TRUE_DATA_CE_T1'}
STAGES = {'default-engineering': ('default', ENGINEERING),
          'oracle-engineering': ('oracle', ENGINEERING),
          'oracle-development': ('oracle', DEVELOPMENT)}


def validate_contract(c):
    stage = c.get('stage')
    if stage not in STAGES:
        raise ValueError('O3 stage differs')
    phase, blocks = STAGES[stage]
    n = len(blocks) * len(SNRS)
    if (c.get('schema') != SCHEMA or c.get('blocks') != blocks or c.get('snrs') != SNRS
            or c.get('arm') != ARM[phase] or c.get('device') != 'cpu'
            or c.get('threads') != 1 or c.get('outer_iterations') != 10
            or c.get('terminal_bp_iterations') != 20
            or c.get('checkpoints') != [1, 4, 7]
            or c.get('terminal_check_prior') != 'retain'
            or c.get('terminal_bp_temperature') != 1.
            or c.get('terminal_variance_source') != 'physical'
            or c.get('initial_lstsq_driver') != 'gels'
            or c.get('receiver_recipe') != 'B0-p2-s0.5'
            or c.get('bounds', {}).get('F') != n
            or not 0 < c.get('bounds', {}).get('seconds', 0) <= 7200
            or set(c['bounds']) != {'F', 'seconds'}
            or not 0 < c.get('output_bytes', 0) <= 20 * 1024**3):
        raise ValueError('O3 frozen full receiver/count contract differs')
    if phase == 'oracle' and not c.get('default_admission'):
        raise ValueError('O3 oracle requires separately audited default 4F')
    if stage == 'oracle-development' and not c.get('engineering_admission'):
        raise ValueError('O3 development requires engineering audit')
    return phase, blocks


def check_admission(c, root, sha, *, phase, source_hash, script_hash):
    """A saved PASS receipt is the gate; a partial/default run is never enough."""
    if phase == 'default':
        return
    receipt_path = root / c['default_admission']
    receipt = json.loads(receipt_path.read_text())
    summary_path = root / receipt['summary_path']
    if (receipt.get('status') != 'PASS' or receipt.get('stage') != 'default-engineering'
            or receipt.get('saved_F') != 4 or receipt.get('default_exact') is not True
            or receipt.get('source_sha256') != source_hash
            or receipt.get('script_sha256') != script_hash
            or receipt.get('summary_sha256') != sha(summary_path)
            or c.get('default_admission_sha256') != sha(receipt_path)):
        raise ValueError('O3 default 4F raw audit gate differs')
    if c['stage'] == 'oracle-development':
        path = root / c['engineering_admission']
        eng = json.loads(path.read_text())
        summary_path = root / eng['summary_path']
        if (eng.get('status') != 'PASS' or eng.get('stage') != 'oracle-engineering'
                or eng.get('saved_F') != 4 or eng.get('one_shot_F') != 4
                or eng.get('source_sha256') != source_hash
                or eng.get('script_sha256') != script_hash
                or eng.get('summary_sha256') != sha(summary_path)
                or c.get('engineering_admission_sha256') != sha(path)):
            raise ValueError('O3 engineering 4F audit gate differs')


def check_default(actual, old, same_receiver_state):
    if 'one_shot_true_data_ce_records' in actual or actual.get('truth_access_level') == 'true_data_ce_only':
        raise ValueError('default interface consumed true data')
    same_receiver_state(actual, old)
    return True


def check_one_shot(actual, old, raw, *, array_hash, check_calls, same_state,
                   build_A_for_DALS_torch):
    import numpy as np
    import torch
    detail = check_calls(actual)
    if (detail['operators']['terminal_BP'] != 1 or detail['resources']['LDPC_calls'] != 4
            or detail['resources']['CE_solves'] != 9
            or detail['operators']['outer_BP'] != 10
            or not actual['terminal_check_prior_consumed'] or not actual['terminal_controls_consumed']
            or actual['terminal_bp_temperature'] != 1.
            or actual['terminal_variance_source'] != 'physical'
            or actual['terminal_scale_applied']
            or actual['sigma2_terminal'] != float(raw['sigma2'])):
        raise ValueError('O3 complete FULL calls or frozen terminal controls differ')
    rec = actual.get('one_shot_true_data_ce_records')
    if (not isinstance(rec, list) or len(rec) != 1 or rec[0]['outer_iter'] != 1
            or rec[0]['location'] != 'after_code_feedback_ce_before_x_total'
            or rec[0]['status'] != 'consumed' or rec[0]['true_variance'] != 0.
            or rec[0]['variance_used_by_CE'] or rec[0]['truth_access'] != 'true_data_ce_only'
            or rec[0]['supplied_sha256'] != array_hash(np.asarray(raw['data'], dtype=np.complex128))):
        raise ValueError('O3 one-shot controller audit differs')
    if len(actual['dals']) != 9 or [d['outer_iter'] for d in actual['dals']] != list(range(1, 10)):
        raise ValueError('O3 full CE trajectory differs')
    injected = actual['dals'][0]
    observer = injected.get('pre_override_moment_audit')
    if (injected['mode'] != 'mean' or injected['moment_source'] != 'true_data_ce'
            or not injected['oracle_mean'] or injected.get('consumed_variance', 0) != 0
            or injected['variance_used_by_CE'] or not isinstance(observer, dict)
            or injected['mu'].shape != raw['data'].shape
            or not np.array_equal(injected['mu'], np.asarray(raw['data'], dtype=injected['mu'].dtype))
            or not np.array_equal(injected['finite_variance'], np.zeros_like(injected['finite_variance']))
            or rec[0]['consumed_mean_sha256'] != array_hash(injected['mu'])
            or rec[0]['A_sha256'] != array_hash(injected['A'])
            or rec[0]['proposal_mean_sha256'] != array_hash(old['dals'][0]['mu'])
            or rec[0]['proposal_variance_sha256'] != array_hash(observer['finite_variance'])):
        raise ValueError('O3 t=1 observer, proposal, or CE design differs')
    same_state(injected['g_previous'], old['dals'][0]['g_previous'])
    params = raw['params']
    total = torch.as_tensor(raw['pilot'], dtype=torch.complex64) + torch.as_tensor(raw['data'], dtype=torch.complex64)
    direct_A = build_A_for_DALS_torch(len(raw['pilot']),
        torch.as_tensor(injected['support_delays']), torch.as_tensor(injected['support_dopplers']),
        total, params['c1'], params['c2'], 2, cdtype=torch.complex64).numpy()
    np.testing.assert_array_equal(injected['A'], direct_A)
    for later in actual['dals'][1:]:
        if later.get('moment_source') != 'code_feedback.ce' or later.get('oracle_mean'):
            raise ValueError('O3 leaked truth into a later CE')
    # t=0 is untouched; the changed t=1 CE can change every later state.
    for key in ('initial_estimator',):
        same_state(actual[key], old[key])
    same_state(actual['graphs'][0], old['graphs'][0])
    same_state(actual['support_trace'][0], old['support_trace'][0])
    if (actual.get('truth_access_level') != 'true_data_ce_only'
            or actual.get('deployment_eligible') is not False):
        raise ValueError('O3 truth scope label differs')
    trajectory = [dict(outer_iter=d['outer_iter'], moment_source=d['moment_source'],
        oracle_mean=d['oracle_mean'], A_sha256=array_hash(d['A']),
        mu_sha256=array_hash(d['mu']), g_solution_sha256=array_hash(d['g_solution']),
        support_delays_sha256=array_hash(d['support_delays']),
        support_dopplers_sha256=array_hash(d['support_dopplers'])) for d in actual['dals']]
    observer_receipt = {k: (dict(shape=list(v.shape), dtype=str(v.dtype), sha256=array_hash(v))
                            if isinstance(v, np.ndarray) else v) for k, v in observer.items()}
    return dict(controller=rec[0], t1_observer=observer_receipt,
                ce_trajectory=trajectory, calls=detail)


def main(args):
    root = args.root.resolve(); source = args.source.resolve()
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import classical_joint_unrolled as joint, supplement_feedback as feedback
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes, offline_scores
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback
    from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
    from afdm_sp_joint_unrolled.one_shot_true_data_ce import OneShotTrueDataCE
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.direction_data import validate_observed
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record
    from afdm_sp_joint_unrolled.light_gap_receiver_run import receiver_resources
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_receiver_state, same_state, check_calls
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles

    contract = root / 'contracts' / (args.tag + '.json')
    c = json.loads(contract.read_text()); manifest = source / 'source-manifest.json'
    if (sha(contract) != args.contract_sha256 or sha(Path(__file__)) != args.script_sha256
            or sha(manifest) != c['source_sha256'] or c.get('tag') != args.tag):
        raise ValueError('O3 contract/script/source identity differs')
    phase, blocks = validate_contract(c)
    if sha(c['checkpoint_path']) != c['checkpoint_sha256']:
        raise ValueError('O3 G1 checkpoint differs')
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard = BoundFiles({**guard.files, Path(__file__): args.script_sha256})
    guard.verify()
    for summary_path, audit_path in c['audited_inputs'].items():
        receipt = json.loads((root / audit_path).read_text())
        if receipt['status'] != 'PASS' or receipt['summary_sha256'] != sha(root / summary_path):
            raise ValueError('O3 upstream raw audit differs')
    check_admission(c, root, sha, phase=phase, source_hash=sha(manifest), script_hash=sha(Path(__file__)))
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    upstream = json.loads((root / c['old_summary']).read_text())
    if upstream['status'] != 'COMPLETE' or len(upstream['records']) != 288:
        raise ValueError('G1 physical/FULL summary incomplete')
    index = {(e['kind'], e['block'], e['snr'], e['arm']): e for e in upstream['records']}
    if len(index) != 288:
        raise ValueError('duplicate G1 input identity')
    env = json.loads((root / c['code_environment']).read_text())
    system = _make_config_a(1024, 2., 8, 10., 4.)
    if (system.N_total, system.l_max_cap, system.k_max_cap, system.rho) != (1024, 102, 2, .5):
        raise ValueError('G1 system geometry differs')

    def inputs(block, snr):
        pe = index['A', block, 7, 'G1_PROPAGATION']
        ref = index['F', block, snr, 'G1_FULL']
        physical_record, physical = verified_record(pe, root)
        old_record, old = verified_record(ref, root)
        raw, _ = reuse_at_snr(physical['raw'], physical['diagnostics'], snr)
        obs = {k: np.array(raw[k], copy=True) for k in ('y', 'pilot', 'sigma2')}
        obs['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        validate_observed(obs, 1024)
        if (old_record['observed_hashes'] != hashes(obs)
                or old_record['physical_record_sha256'] != pe['sha256']
                or pe['split'] != ref['split']
                or len(old['dals']) != 9
                or check_calls(old)['operators']['terminal_BP'] != 1):
            raise ValueError('G1 paired FULL/physical input differs')
        return pe, ref, raw, obs, old

    def audit(summary):
        if (summary.get('status') != 'COMPLETE' or summary.get('calls') != {'F': len(blocks)*2}
                or summary.get('source_sha256') != sha(manifest)
                or summary.get('script_sha256') != args.script_sha256
                or summary.get('contract_sha256') != args.contract_sha256):
            raise ValueError('O3 saved full-call summary differs')
        expected = {(b, s, ARM[phase]) for b in blocks for s in SNRS}
        entries = {(e['block'], e['snr'], e['arm']): e for e in summary['records']}
        if set(entries) != expected or len(entries) != len(summary['records']):
            raise ValueError('O3 saved F identities differ')
        rows, arrays = [], 0
        for b, snr, arm in sorted(expected):
            pe, ref, raw, obs, old = inputs(b, snr)
            entry = entries[b, snr, arm]
            record, value = verified_record(entry, root)
            reservation = json.loads(Path(entry['record']).with_name(record['token']+'-reserve.json').read_text())
            if (entry['split'] != ref['split'] or record['observed_hashes'] != hashes(obs)
                    or record['physical_record_sha256'] != pe['sha256']
                    or record['reference_record_sha256'] != ref['sha256']
                    or any(reservation[k] != record[k] or record[k] != entry[k]
                           for k in ('kind', 'block', 'snr', 'split', 'arm'))):
                raise ValueError('O3 reservation/parent/observed pairing differs')
            detail = (dict(default_exact=check_default(value, old, same_receiver_state))
                      if phase == 'default' else
                      check_one_shot(value, old, raw, array_hash=array_hash, check_calls=check_calls,
                                     same_state=same_state, build_A_for_DALS_torch=joint.build_A_for_DALS_torch))
            scores = offline_scores(value, raw, value['H'])
            if scores != record['scores'] or scores != entry['scores']:
                raise ValueError('O3 saved terminal scores differ')
            if phase == 'default' and scores != index['F', b, snr, 'G1_FULL']['scores']:
                raise ValueError('default interface changed original terminal scores')
            arrays += finite_arrays(value)
            rows.append(dict(block=b, snr=snr, split=ref['split'], arm=arm,
                reference_record_sha256=ref['sha256'], physical_record_sha256=pe['sha256'],
                original_scores=index['F', b, snr, 'G1_FULL']['scores'], scores=scores, **detail))
        return dict(rows=rows, arrays=arrays, saved_F=len(rows),
                    default_exact=(phase == 'default'), one_shot_F=(len(rows) if phase == 'oracle' else 0))

    out = root / 'runs' / args.tag / c['stage']
    if args.mode == 'audit':
        started = time.time()
        exit_state = json.loads((root / 'evidence' / (args.tag + '-exit.json')).read_text())
        if exit_state['exit_code'] != 0 or exit_state['timed_out']:
            raise ValueError('O3 stage did not exit cleanly')
        summary_path = out / 'summary.json'; summary = json.loads(summary_path.read_text())
        details = audit(summary)
        if details != summary['raw_checks']:
            raise ValueError('O3 saved raw checks differ')
        guard.verify()
        receipt = dict(status='PASS', stage=c['stage'], summary_path=str(summary_path.relative_to(root)),
            summary_sha256=sha(summary_path), source_sha256=sha(manifest),
            script_sha256=args.script_sha256, contract_sha256=args.contract_sha256,
            saved_F=details['saved_F'], default_exact=details['default_exact'],
            one_shot_F=details['one_shot_F'], rows=details['rows'], arrays=details['arrays'],
            new_F_calls=0, wall_seconds=time.time()-started,
            independence='main-session self-review; weak')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as handle:
            json.dump(receipt, handle, indent=2)
        print(json.dumps({k:v for k,v in receipt.items() if k != 'rows'}))
        return

    run = LightRun(root/'runs'/args.tag, c['stage'], c['bounds'], c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache); run.meter.adopt_tree(cache)
        if hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
            raise ValueError('G1 code identity differs')
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        run.write('environment.json', dict(code_identity=env['code_identity'], device='cpu', threads=1,
            source_sha256=sha(manifest), numpy=np.__version__, torch=torch.__version__,
            phase=phase, default_admission=c.get('default_admission')))
        for b in blocks:
            for snr in SNRS:
                pe, ref, raw, obs, old = inputs(b, snr); before = hashes(obs)
                controller = OneShotTrueDataCE(raw['data']) if phase == 'oracle' else None
                def full():
                    with OperatorProfile(torch.device('cpu')) as profile:
                        profile.wrap(joint, 'reconstruct_H_torch', 'dense_H_reconstruction')
                        profile.wrap(joint, 'build_A_for_DALS_torch', 'CE_design')
                        profile.wrap(feedback, 'decoder_messages', 'feedback_LDPC')
                        value = receiver.run(obs, audit=True,
                            code_feedback=CodeFeedback(code, checkpoint=1,
                                refresh_checkpoints=[4, 7], retain_messages=True),
                            bp_schedule=UniformBPSchedule(outer_bp_iterations=12),
                            terminal_check_prior='retain', terminal_bp_temperature=1.,
                            terminal_variance_source='physical', one_shot_true_data_ce=controller)
                    value.update(operator_profile=profile.rows, resource_counts=receiver_resources(value))
                    return value
                identity = dict(block=b, snr=snr, split=ref['split'], arm=ARM[phase])
                value, record = run.call('F', identity, full,
                    lambda v: offline_scores(v, raw, v['H']),
                    dict(observed_hashes=before, physical_record_sha256=pe['sha256'],
                         reference_record_sha256=ref['sha256'], truth_access=('none' if phase == 'default' else 'true_data_ce_only')))
                if hashes(obs) != before:
                    raise ValueError('O3 receiver mutated observation')
                if phase == 'default':
                    check_default(value, old, same_receiver_state)
                else:
                    check_one_shot(value, old, raw, array_hash=array_hash, check_calls=check_calls,
                                   same_state=same_state, build_A_for_DALS_torch=joint.build_A_for_DALS_torch)
                print(json.dumps(dict(block=b, snr=snr, arm=ARM[phase], calls=run.counts,
                                      scores=record['scores'])), flush=True)
        summary = dict(status='COMPLETE', calls=run.counts, records=run.records,
            source_sha256=sha(manifest), script_sha256=args.script_sha256,
            contract_sha256=args.contract_sha256, phase=phase)
        summary['raw_checks'] = audit(summary)
        guard.verify(); run.meter.verify(); summary['wall_seconds'] = time.time()-run.started
        run.write('summary.json', summary)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--mode', choices=['run', 'audit'], default='run')
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--script-sha256', required=True)
    main(parser.parse_args())
