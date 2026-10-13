"""Bounded terminal development and separate saved-LLR audits on deinlab.

v4 aligns the campaign scorer with the producer definition (``score_errors``
over ``x_hard`` symbol decisions) for the loader binding and the recorded rows,
as v3 did. The audit replay score keeps ``decoder_scores`` because that replay
returns no ``x_hard``; it is audit-internal and never compared with the
producer score schema. Both definitions agree on FER.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def planned(stage):
    if stage not in ('engineering', 'development'):
        raise ValueError('unknown terminal stage')
    blocks = [0, 20] if stage == 'engineering' else [b for b in range(32) if b not in (0, 20)]
    original = [(b, s, 'ORIGINAL') for b in blocks for s in (7, 8)] if stage == 'engineering' else []
    return original + [(b, s, a) for b in blocks for s in (7, 8) for a in ('TAIL', 'RIDGE_T')]


def validate_contract(c):
    if (c['schema'] != 'tail-terminal-contract-v1' or c['status'] != 'FROZEN_BEFORE_NEW_TERMINAL_RESULTS'
            or c['arms'] != ['ORIGINAL', 'TAIL', 'RIDGE_T']
            or c['data'] != dict(n=1024, blocks=list(range(32)), engineering_blocks=[0, 20],
                snrs=[7, 8], original_support=24, core_doppler_limit=2, tail_doppler_limit=5,
                physical_stride=5, ridge_strength=.1, nominal_q=.01, quadrature=128)
            or c['terminal'] != dict(device='cpu', threads=1, temperature=1., bp_iterations=20,
                threshold=1e-4, clip=20., ldpc_maxiter=50, checkpoints=[1, 4, 7],
                prior='retain_last_check_extrinsic', variance='physical')
            or c['limits'] != dict(wall_seconds=7200, output_bytes=20*2**30,
                reserved_overhead_bytes=64*2**20, max_parallel_jobs=2, T=132, D=132,
                new_receiver_F=0, new_physical_A=0, production_tail_refits=64,
                stage_seconds={'engineering-run': 600, 'engineering-audit': 600,
                               'development-run': 4800, 'development-audit': 1200})
            or c['statistics'] != dict(physical_clusters=32, draws=20000, seed=202609160701,
                comparisons=[['TAIL', 'ORIGINAL'], ['TAIL', 'RIDGE_T']], percentiles=[.0125, .9875],
                go='both_upper_bounds_negative_and_no_per_snr_FER_increase_against_either_reference')):
        raise ValueError('terminal campaign differs from frozen scientific contract')


def channel_scores(H, raw):
    """Truth is used only here, after constructing/decoding the observed arm."""
    truth = np.asarray(raw['H'], dtype=np.complex128)
    H = np.asarray(H, dtype=np.complex128)
    p, d = np.asarray(raw['pilot']), np.asarray(raw['data'])
    error = truth - H
    ep, ed = error @ p, error @ d
    hp = float(np.vdot(ep, ep).real)
    hd = float(np.vdot(ed, ed).real)
    cross = float(2*np.vdot(ep, ed).real)
    response = truth @ (p + d)
    he, re = float(np.vdot(truth, truth).real), float(np.vdot(response, response).real)
    if he <= 0 or re <= 0:
        raise ValueError('nonpositive physical scoring denominator')
    return dict(H_NMSE=float(np.vdot(error, error).real/he),
                response_NMSE=float(np.vdot(ep+ed, ep+ed).real/re),
                pilot_error_squared=hp, data_error_squared=hd, pilot_data_cross=cross)


def old_binding_ok(record, physical_sha256, split_matches, observed_hashes, old, sigma2):
    """Frozen ORIGINAL binding for the saved actual-terminal ridge record.

    v1 additionally required the stop-runner flag ``old['terminal_executed']``.
    The legacy ridge producer never wrote that field, so the clause could only
    raise KeyError on every saved record. Terminal execution and prior
    consumption are already established by the surviving prior/control flags,
    temperature, variance source, control-scale and sigma2 binding below.
    No threshold, endpoint, arm or budget changes.
    """
    return not (record['physical_record_sha256'] != physical_sha256
                or not split_matches
                or record['observed_hashes'] != observed_hashes
                or record['strength'] != .1
                or record['truth_access'] != 'offline scoring only'
                or len(old['dals']) != 9
                or not old['terminal_check_prior_consumed']
                or not old['terminal_controls_consumed']
                or old['terminal_bp_temperature'] != 1.
                or old['terminal_variance_source'] != 'physical'
                or old['terminal_scale_applied']
                or old['sigma2_terminal'] != float(sigma2))


class InputBank:
    def __init__(self, args, c):
        import tail_completion_v2 as tail
        from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
        from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
        from afdm_sp_joint_unrolled.light_gap_replay import verified_record
        from afdm_sp_joint_unrolled.supplement_profile import score_errors
        from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
        self.args, self.c = args, c
        self.hashes, self.read, self.producer_scores, self.reuse = hashes, verified_record, score_errors, reuse_at_snr
        self.array_hash = array_hash
        self.ridge, self.physical = tail.load_index(args)
        self.last_block = self.last_point = self.physical_value = self.point = None
        self.counts = dict(physical_record_reads=0, saved_receiver_record_reads=0)

    def load(self, block, snr):
        if self.last_point == (block, snr):
            return self.point
        pe, fe = self.physical[block], self.ridge[block, snr]
        if self.last_block != block:
            _, self.physical_value = self.read(pe, self.args.old_root)
            self.last_block = block
            self.counts['physical_record_reads'] += 1
        raw, _ = self.reuse(self.physical_value['raw'], self.physical_value['diagnostics'], snr)
        record, old = self.read(fe, self.args.ridge_root)
        self.counts['saved_receiver_record_reads'] += 1
        observed = {k: np.array(raw[k], copy=True) for k in ('y', 'pilot', 'sigma2')}
        observed['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        if not old_binding_ok(record, pe['sha256'], fe['split'] == pe['split'],
                              self.hashes(observed), old, observed['sigma2']):
            raise ValueError('old ridge/physical/actual-terminal binding differs')
        final = old['dals'][-1]
        dl, dk = final['support_delays'], final['support_dopplers']
        if final['outer_iter'] != 9 or len(dl) != 24 or set((5*dl+dk+2).tolist()) != set(old['support']):
            raise ValueError('old terminal S24 identity differs')
        for t, state in enumerate(old['dals'], start=1):
            if state['outer_iter'] != t:
                raise ValueError('CE state schedule differs')
            np.testing.assert_array_equal(state['support_delays'], dl)
            np.testing.assert_array_equal(state['support_dopplers'], dk)
        checkpoints = [v for v in old['code_feedback_records'] if v['stage'] == 'decoder']
        if [v['iteration'] for v in checkpoints] != [1, 4, 7]:
            raise ValueError('terminal check-prior lineage differs')
        prior = checkpoints[-1]['prior_after']
        np.testing.assert_array_equal(prior, np.clip(checkpoints[-1]['raw_check_extrinsic'], -20., 20.))
        params = raw['params']
        if len(observed['y']) != 1024 or params['representation'] != 'physical_cpp_untruncated':
            raise ValueError('physical domain differs')
        legal = dict(H=old['H'], y=observed['y'], pilot=observed['pilot'], x_soft=old['x_soft'],
                     delays=dl, dopplers=dk, c1=params['c1'], c2=params['c2'])
        graphs = [g for g in old['graphs'] if g['stage'] == 'final_bp']
        if (len(graphs) != 1 or graphs[0]['H_hash'] != self.array_hash(np.asarray(old['H'], dtype=np.complex128))
                or graphs[0]['threshold'] != 1e-4 or graphs[0]['operator'] != '>='):
            raise ValueError('saved actual ORIGINAL detector graph differs')
        scores = dict(self.producer_scores(old, raw), **channel_scores(old['H'], raw))
        for key in ('FER', 'coded_bit_errors', 'raw_bit_errors', 'decoded_codeword_bit_errors'):
            if scores[key] != fe['scores'][key]:
                raise ValueError('saved ORIGINAL scores disagree: '+key)
        provenance = dict(reference_record_sha256=fe['sha256'], physical_record_sha256=pe['sha256'],
            observed_hashes=self.hashes(observed), legal_input_hashes=self.hashes(legal),
            prior_hash=self.hashes({'prior': prior})['prior'], truth_access='external scoring only')
        self.point = dict(raw=raw, observed=observed, old=old, legal=legal, prior=prior,
                          provenance=provenance, split=fe['split'], original_scores=scores,
                          original_graph=graphs[0])
        self.last_point = block, snr
        return self.point


def engineering_quote(producer, auditor, already_seconds, existing_bytes):
    """Use complete per-record steps, including I/O, rather than bare BP times."""
    if len(producer['step_times']) != 12 or len(auditor['step_times']) != 12:
        raise ValueError('engineering quote needs all 12 T and 12 D steps')
    longest = {a: max(v['seconds'] for v in producer['step_times'] if v['arm'] == a)
               for a in ('TAIL', 'RIDGE_T')}
    d_seconds = max(v['seconds'] for v in auditor['step_times'])
    t_bytes = max(v['artifact_bytes'] for v in producer['step_times'])
    d_bytes = max(v['artifact_bytes'] for v in auditor['step_times'])
    seconds = already_seconds + 2*(60*sum(longest.values()) + 120*d_seconds) + 180
    output = existing_bytes + 2*(120*t_bytes + 120*d_bytes) + 64*2**20
    return dict(predicted_campaign_seconds=seconds, predicted_output_bytes=output,
                max_T_step_seconds=longest, max_D_step_seconds=d_seconds,
                seconds_go=seconds < 7200, bytes_go=output < 20*2**30,
                GO=bool(seconds < 7200 and output < 20*2**30), factor=2., fixed_seconds=180.)


def completed_wall(root, required=()):
    paths = list((root/'evidence').glob('tail-terminal-*-v1-exit.json'))
    by_name = {p.name: json.loads(p.read_text()) for p in paths}
    for name in required:
        if name not in by_name:
            raise ValueError('required completed stage missing: '+name)
    for name, value in by_name.items():
        if value['exit_code'] != 0 or value['timed_out']:
            raise ValueError('preserved campaign failure must be resolved explicitly: '+name)
    return sum(float(v['wall_seconds']) for v in by_name.values())


def parse():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--old-root', type=Path, required=True)
    parser.add_argument('--ridge-root', type=Path, required=True)
    parser.add_argument('--stage', choices=('engineering', 'development'), required=True)
    parser.add_argument('--mode', choices=('run', 'audit', 'validate'), default='run')
    return parser.parse_args()


def main(args):
    c = json.loads(args.contract.read_text())
    if sha(args.contract) != args.contract_sha256:
        raise ValueError('contract hash differs')
    validate_contract(c)
    here = Path(__file__).resolve().parent
    if sha(here/'tail-terminal-contract-v1.md') != c['method_md_sha256']:
        raise ValueError('method document changed')
    for name, digest in c['implementation_sha256'].items():
        if sha(here/name) != digest:
            raise ValueError('frozen implementation changed: '+name)
    if args.mode == 'validate':
        print(json.dumps(dict(status='PASS_LOCAL_CONTRACT_AND_IMPLEMENTATION_HASHES_ONLY',
                              planned_T=len(planned(args.stage)), new_calls=0)))
        return
    if sys.platform != 'linux' or not args.root.resolve().is_relative_to('/data/guoyikun'):
        raise ValueError('target experiment requires the registered Linux project root')
    sys.path.insert(0, str(args.source_dir))
    import torch
    import tail_completion_v2 as tail
    import tail_terminal_v1 as method
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import (
        CODE_KEYS, LightRun, verified_record, decoder_scores, replay_decode, check_decode_identity)
    from afdm_sp_joint_unrolled.supplement_profile import score_errors
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles

    tail.assert_threads()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    args.source_manifest = args.source_dir/'source-manifest.json'
    tail.source_guard(args, c)
    tail.input_guard(args, c)
    memory = tail.memory_preflight()
    manifest = json.loads(args.source_manifest.read_text())
    files = {args.source_dir/'afdm_sp_joint_unrolled'/name: digest for name, digest in manifest.items()}
    files.update({here/name: digest for name, digest in c['implementation_sha256'].items()})
    files.update({args.contract: args.contract_sha256,
                  here/'tail-terminal-contract-v1.md': c['method_md_sha256'],
                  args.source_manifest: c['source_binding']['analysis_ce_source_v4_manifest_sha256'],
                  args.old_root/c['environment']: c['environment_sha256']})
    required = []
    if args.stage == 'development':
        required += ['tail-terminal-engineering-run-v1-exit.json', 'tail-terminal-engineering-audit-v1-exit.json']
        admission = json.loads((args.root/'runs/engineering/audit/summary.json').read_text())
        original = args.root/'runs/engineering/producer/summary.json'
        if (admission['status'] != 'COMPLETE' or not admission['engineering_quote']['GO']
                or admission['producer_summary_sha256'] != sha(original)
                or admission['contract_sha256'] != args.contract_sha256):
            raise ValueError('engineering audit and budget admission required')
        files[original] = sha(original)
        admission_path = args.root/'runs/engineering/audit/summary.json'
        files[admission_path] = sha(admission_path)
    if args.mode == 'audit':
        required += [f'tail-terminal-{args.stage}-run-v1-exit.json']
    used = completed_wall(args.root, required)
    cap = min(c['limits']['stage_seconds'][args.stage+'-'+args.mode], c['limits']['wall_seconds']-used)
    if cap <= 0:
        raise TimeoutError('campaign wall budget exhausted')
    bank = InputBank(args, c)
    schedule = planned(args.stage)
    producer_path = args.root/'runs'/args.stage/'producer/summary.json'
    producer = None
    if args.mode == 'audit':
        producer = json.loads(producer_path.read_text())
        if (producer['status'] != 'COMPLETE' or producer['calls'] != {'T': len(schedule)}
                or producer['contract_sha256'] != args.contract_sha256):
            raise ValueError('terminal producer incomplete or changed')
        entries = {(v['block'], v['snr'], v['arm']): v for v in producer['records']}
        if set(entries) != set(schedule) or len(entries) != len(producer['records']):
            raise ValueError('duplicate or incomplete producer matrix')
        files[producer_path] = sha(producer_path)
    guard = BoundFiles(files)
    kind, subdir = ('T', 'producer') if args.mode == 'run' else ('D', 'audit')
    run = LightRun(args.root/'runs', args.stage+'/'+subdir, {kind: len(schedule), 'seconds': cap},
        c['limits']['output_bytes']-c['limits']['reserved_overhead_bytes'], guard)
    cache, original_rows, rows, step_times = {}, {}, [], []
    try:
        code_dir = run.out/'code-cache'
        code_dir.mkdir()
        code = build_code(cache_dir=code_dir)
        run.meter.adopt_tree(code_dir)
        env = json.loads((args.old_root/c['environment']).read_text())
        if hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']:
            raise ValueError('LDPC identity differs from old production')
        run.write('environment.json', dict(code_identity=env['code_identity'], numpy=np.__version__,
            torch=torch.__version__, device='cpu', threads=1, memory_preflight=memory))
        for block, snr, arm in schedule:
            begin = time.perf_counter()
            run.check()
            point = bank.load(block, snr)
            before = hashes(point['legal'])
            identity = dict(block=block, snr=snr, arm=arm, split=point['split'])
            original_rows[block, snr] = dict(block=block, snr=snr, arm='ORIGINAL',
                scores=point['original_scores'], actual_edges=point['original_graph']['edges'],
                graph=point['original_graph'], **point['provenance'])
            def score(value):
                return dict(score_errors(value, point['raw']),
                            **channel_scores(value['H'], point['raw']))
            def transform():
                return method.make_candidate(**point['legal'], arm=arm, predictor_cache=cache)
            if args.mode == 'run':
                def terminal_call():
                    candidate = transform()
                    with OperatorProfile(torch.device('cpu')) as profile:
                        value = method.decode_candidate(candidate, float(point['observed']['sigma2']),
                            point['observed']['constellation'], point['prior'], code)
                    method.check_profile(profile.rows)
                    value['operator_profile'] = profile.rows
                    if arm == 'ORIGINAL':
                        for key in method.TERMINAL_FIELDS:
                            np.testing.assert_array_equal(value[key], point['old'][key])
                    return value
                value, record = run.call('T', identity, terminal_call, score, point['provenance'])
            else:
                old_record, value = verified_record(entries[block, snr, arm], args.root/'runs')
                for key, expected in point['provenance'].items():
                    if old_record[key] != expected:
                        raise ValueError('saved terminal provenance differs: '+key)
                candidate = transform()
                for key in ('H', 'z', 'support', 'tail_atoms', 'core_gains', 'tail_before', 'tail_gains', 'centres'):
                    np.testing.assert_array_equal(value[key], candidate[key])
                if value['ridge'] != candidate['ridge'] or value['counts'] != candidate['counts']:
                    raise ValueError('saved method objective or operation counters differ')
                method.check_terminal(value, candidate, float(point['observed']['sigma2']), point['prior'])
                method.check_profile(value['operator_profile'])
                expected_scores = score(value)
                if expected_scores != old_record['scores'] or expected_scores != entries[block, snr, arm]['scores']:
                    raise ValueError('saved external scores differ')
                if arm == 'ORIGINAL':
                    for key in method.TERMINAL_FIELDS:
                        np.testing.assert_array_equal(value[key], point['old'][key])
                reservation = json.loads(Path(entries[block, snr, arm]['record']).with_name(
                    old_record['token']+'-reserve.json').read_text())
                if any(reservation[k] != old_record[k] for k in ('token', 'kind', 'block', 'snr', 'split', 'arm')):
                    raise ValueError('producer reservation identity differs')
                decoded, record = run.call('D', identity, lambda: replay_decode(code, value, 1., 20., 50),
                    # the fresh decode replay returns no x_hard, so this audit-internal
                    # score keeps the LLR-based definition; it is never compared against
                    # the producer score schema (rows/original_rows use producer_scores)
                    lambda v: decoder_scores(v, point['raw']),
                    dict(terminal_record_sha256=entries[block, snr, arm]['sha256']))
                check_decode_identity(decoded, value)
            if hashes(point['legal']) != before:
                raise ValueError('observed input was mutated')
            rows.append(dict(identity, scores=score(value), actual_edges=value['actual_edges'],
                graph=value['graphs'][0], method_counts=value['counts'],
                component_seconds=value['component_seconds'],
                preprocessing_seconds=value['preprocessing_seconds'],
                operator_profile=value['operator_profile'],
                existing_tail_energy=float(len(value['H'])*np.vdot(value['tail_before'], value['tail_before']).real),
                provenance=point['provenance']))
            step_times.append(dict(block=block, snr=snr, arm=arm, seconds=time.perf_counter()-begin,
                                   artifact_bytes=Path(record['state']['file']['path']).stat().st_size))
            print(json.dumps(dict(identity, kind=kind, FER=record['scores']['FER'], calls=run.counts)), flush=True)
        guard.verify()
        tail.input_guard(args, c)
        summary = dict(status='COMPLETE', stage=args.stage, mode=args.mode, calls=run.counts,
            records=run.records, rows=rows, original_rows=list(original_rows.values()),
            step_times=step_times, input_reads=bank.counts, contract_sha256=args.contract_sha256,
            source_sha256=sha(args.source_manifest), script_sha256=sha(__file__),
            scope=method.SCOPE, new_receiver_F=0, new_physical_A=0,
            output_meter_bytes_before_summary=run.meter.used,
            wall_seconds=time.time()-run.started)
        if args.mode == 'audit':
            if rows != producer['rows'] or summary['original_rows'] != producer['original_rows']:
                raise ValueError('producer and audit result rows differ')
            summary['producer_summary_sha256'] = sha(producer_path)
            summary['additional_transform_calls'] = len(schedule)
            summary['additional_method_counts'] = {k: sum(row['method_counts'][k] for row in rows)
                                                   for k in rows[0]['method_counts']}
            if args.stage == 'engineering':
                summary['engineering_quote'] = engineering_quote(producer, summary,
                    used+summary['wall_seconds'], run.meter.used)
        run.write('summary.json', summary)
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    main(parse())
