"""Registered observed-only uncoded G1 development; no production edits."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import torch

ARMS = ('OMP40', 'OMP40_HARD', 'OMP44', 'F2P_HEAD', 'F2P_RESID')
SNRS = (10, 15, 20)


def bits_of(x):
    return np.concatenate((x.real < 0, x.imag < 0)).astype(np.uint8)


def uncoded_symbols(block, n):
    bits = np.random.default_rng([20260914, 730031, block, 1]).integers(
        0, 2, 2*n, dtype=np.uint8)
    signs = 1. - 2.*bits.astype(float)
    data = .5*(signs[:n] + 1j*signs[n:])
    np.testing.assert_array_equal(bits_of(data), bits)
    return bits, data


def validate_observed(obs, n):
    if set(obs) != {'y', 'pilot', 'sigma2', 'constellation'}:
        raise ValueError('receiver accepts only four public observation fields')
    if any(np.asarray(obs[k]).shape != (n,) for k in ('y', 'pilot')):
        raise ValueError('invalid observed vector dimensions')
    sigma = np.asarray(obs['sigma2'])
    if sigma.shape != () or np.iscomplexobj(sigma) or not np.isfinite(sigma) or sigma <= 0:
        raise ValueError('positive finite scalar observation variance required')
    if any(not np.isfinite(v).all() for v in obs.values()):
        raise ValueError('nonfinite observation')
    if not np.array_equal(obs['constellation'], np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])):
        raise ValueError('registered QPSK order and power required')


def residual_score(Phi, y, support, candidates, sigma2):
    del sigma2
    a = Phi[:, support]
    gains = torch.linalg.lstsq(a, y[:, None]).solution[:, 0]
    residual = y-a@gains
    candidates_a = Phi[:, candidates]
    norm = candidates_a.abs().square().sum(0)
    if bool((norm <= 0).any()):
        raise ValueError('zero candidate atom')
    return (candidates_a.conj().T@residual).abs().square()/norm


@contextmanager
def cpu_lstsq(counts):
    """Explicit process-local numerical policy, shared by every arm."""
    original = torch.linalg.lstsq
    def solve(a, b, *args, **kwargs):
        if a.device.type != 'cpu' or kwargs.get('driver') not in (None, 'gels'):
            raise ValueError('uncoded experiment requires CPU gels')
        kwargs['driver'] = 'gels'
        result = original(a, b, *args, **kwargs)
        counts['lstsq'] += 1
        return result
    torch.linalg.lstsq = solve
    try:
        yield
    finally:
        torch.linalg.lstsq = original


@contextmanager
def forbid_coding(counts):
    """Catch loaded decoder/encoder aliases, including hidden wrapper consumers."""
    replacements = []
    def forbidden(*args, **kwargs):
        counts['coding_calls'] += 1
        raise AssertionError('coding function crossed uncoded boundary')
    names = ('build_code', 'encode', 'decode_llr', 'decoder_messages', 'CodeFeedback')
    for name, module in list(sys.modules.items()):
        if module is None or not name.startswith('afdm_sp_joint_unrolled'):
            continue
        for attr in names:
            if hasattr(module, attr):
                replacements.append((module, attr, getattr(module, attr)))
                setattr(module, attr, forbidden)
    try:
        yield
    finally:
        for module, attr, value in reversed(replacements):
            setattr(module, attr, value)


def receive(model, obs, arm):
    from afdm_sp_joint_unrolled import classical_joint_unrolled as joint
    from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
    if arm not in ARMS:
        raise ValueError('unregistered uncoded arm')
    validate_observed(obs, model.cfg.N)
    repair = arm.startswith('F2P_')
    nomination = 44 if arm == 'OMP44' else 40
    model.cfg.n_paths = nomination
    model.use_soft_decisions = arm != 'OMP40_HARD'
    head = model.cand_active_rel
    head.set_refine_config(2, 96, True, 2)
    head._gateA_scorer = residual_score if arm == 'F2P_RESID' else None
    head._gateA_tau = -1e9
    counts = dict(lstsq=0, coding_calls=0, repair_calls=0, learned_score_calls=0,
                  initial_omp_calls=0)
    old_refine, old_score, old_omp = head.apply_f2p_refinement, head.score, joint.omp_sparse_torch
    def refine(*args, **kwargs):
        counts['repair_calls'] += 1
        return old_refine(*args, **kwargs)
    def score(*args, **kwargs):
        counts['learned_score_calls'] += 1
        return old_score(*args, **kwargs)
    def omp(*args, **kwargs):
        counts['initial_omp_calls'] += 1
        return old_omp(*args, **kwargs)
    head.apply_f2p_refinement, head.score, joint.omp_sparse_torch = refine, score, omp
    support = {}
    def observe_support(raw, final, delays, dopplers):
        support.update(initial=list(raw), final_nomination=list(final),
                       expanded_delays=delays.detach().cpu().numpy().copy(),
                       expanded_dopplers=dopplers.detach().cpu().numpy().copy())
    cfg = model.cfg
    try:
        with torch.no_grad(), cpu_lstsq(counts), forbid_coding(counts):
            result = model(torch.tensor(obs['y'], dtype=cfg.dtype),
                torch.tensor(obs['pilot'], dtype=cfg.dtype),
                torch.tensor(obs['sigma2'], dtype=cfg.rdtype),
                torch.tensor(obs['constellation'], dtype=cfg.dtype),
                enable_support_repair=repair, code_feedback=None,
                diagnostic_support_observer=observe_support,
                bp_schedule=UniformBPSchedule(outer_bp_iterations=20))
    finally:
        head.apply_f2p_refinement, head.score, joint.omp_sparse_torch = old_refine, old_score, old_omp
        head._gateA_scorer = None
    array = lambda key: result[key].detach().cpu().numpy().copy()
    value = dict(x_soft=array('x_soft'), H=array('H_est'), sigma2_final=array('sigma2_final'),
        gains=array('gains'), delays=array('support_delays'), dopplers=array('support_dopplers'),
        support_trace=support, counts=counts, bp_schedule=result['bp_schedule'],
        nomination=nomination, cluster_extension=2, soft_decisions=model.use_soft_decisions)
    value['bits'] = bits_of(value['x_soft'])
    check_receiver(value, arm, cfg.N)
    return value


def check_receiver(value, arm, n):
    counts, schedule = value['counts'], value['bp_schedule']
    repair = arm.startswith('F2P_')
    assert counts['coding_calls'] == 0 and counts['initial_omp_calls'] == 1
    assert counts['repair_calls'] == int(repair)
    assert counts['learned_score_calls'] == (2 if arm == 'F2P_HEAD' else 0)
    assert schedule['outer_iterations'] == 10 and len(schedule['calls']) == 10
    assert schedule['completed_ce_solves'] == 9
    assert all(row['requested_iterations'] == 20 for row in schedule['calls'])
    assert value['H'].shape == (n, n) and value['x_soft'].shape == (n,)
    assert value['bits'].shape == (2*n,) and counts['lstsq'] > 0
    np.testing.assert_array_equal(value['bits'], bits_of(value['x_soft']))
    ids = value['delays']*5+value['dopplers']+2
    assert len(set(ids.tolist())) == len(ids) <= 5*value['nomination']
    assert len(value['support_trace']['initial']) <= value['nomination']
    assert len(value['support_trace']['final_nomination']) <= value['nomination']


def offline_score(value, raw):
    delta = value['bits'] != raw['bits']
    error = value['H'].astype(complex)-raw['H']
    norm = lambda x: float(np.vdot(x, x).real)
    return dict(bit_errors=int(delta.sum()), bit_count=len(delta), block_error=bool(delta.any()),
        channel_nmse=norm(error)/norm(raw['H']),
        pilot_nmse=norm(error@raw['pilot'])/norm(raw['H']@raw['pilot']),
        active_atoms=len(value['delays']))


def main(args):
    root = args.root
    source = root/'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun, setup_guard, verified_record
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.supplement_pilots import transform, propagate_cpp
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    contract = root/'contracts'/(args.tag+'.json')
    c = json.loads(contract.read_text())
    manifest = source/'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert c['schema'] == 'uncoded-g1-v1' and c['arms'] == list(ARMS) and c['snrs'] == list(SNRS)
    assert sha(manifest) == c['source_sha256'] and sha(c['checkpoint_path']) == c['checkpoint_sha256']
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else [b for b in range(32) if b not in (0, 20)])
    nblocks = len(c['blocks'])
    assert c['bounds']['A'] == nblocks and c['bounds']['F'] == nblocks*15+(5 if engineering else 0)
    assert c['device'] == 'cpu' and c['threads'] == 1
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=sha(contract),
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for sp, ap in c['audited_inputs'].items():
        a = json.loads((root/ap).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root/sp)
    if not engineering:
        a = json.loads((root/c['engineering_audit']).read_text())
        assert a['status'] == 'PASS' and a['script_sha256'] == sha(Path(__file__))
    parent = json.loads((root/c['physical_summary']).read_text())
    parents = {e['block']: e for e in parent['records'] if e['kind'] == 'A' and e['arm'] == 'G1_PROPAGATION'}
    assert set(parents) == set(range(32))
    system = _make_config_a(1024, 2., 8, 10., 4.)
    def load_parent(block):
        _, value = verified_record(parents[block], root)
        return value['raw']
    def generate(block):
        raw = load_parent(block)
        bits, data = uncoded_symbols(block, 1024)
        p = raw['params']
        signal = transform(propagate_cpp(transform(raw['pilot']+data, system.c1, system.c2,
            inverse=True), system.c1, p['l_i'], p['k_real'], p['g_i'], prefix_length=102),
            system.c1, system.c2)
        return dict(bits=bits, data=data, pilot=raw['pilot'], noise=raw['noise'],
                    H=raw['H'], noiseless=signal, block=block, uncoded=True)
    def check_input(raw, block):
        parent_raw = load_parent(block)
        bits, data = uncoded_symbols(block, 1024)
        for key, expected in [('bits', bits), ('data', data)]:
            np.testing.assert_array_equal(raw[key], expected)
        for key in ('H', 'pilot', 'noise'):
            np.testing.assert_array_equal(raw[key], parent_raw[key])
        matrix_y = raw['H']@(raw['pilot']+raw['data'])
        error = float(np.linalg.norm(raw['noiseless']-matrix_y)/max(1., np.linalg.norm(matrix_y)))
        assert error <= 1e-10 and raw['uncoded'] is True
        assert float(np.vdot(raw['data'],raw['data']).real/len(raw['data'])) == .5
        return error
    def observed(raw, snr):
        sigma2 = 10.**(-snr/10.)
        return dict(y=raw['noiseless']+np.sqrt(sigma2)*raw['noise'], pilot=raw['pilot'].copy(),
            sigma2=np.array(sigma2), constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]))
    def equal(a, b):
        return flatten(a, {}) == flatten(b, {})
    def audit(summary):
        assert summary['calls'] == {k:v for k,v in c['bounds'].items() if k != 'seconds'}
        assert summary['script_sha256'] == sha(Path(__file__)) and summary['source_sha256'] == sha(manifest)
        entries = {(e['kind'],e['block'],e['snr'],e['arm']):e for e in summary['records']}
        assert len(entries) == len(summary['records']) == nblocks+c['bounds']['F']
        rows, arrays, errors = [], 0, []
        for block in c['blocks']:
            ae = entries['A',block,10,'UNCODED_INPUT']
            ar, raw = verified_record(ae, root)
            assert ar['physical_record_sha256'] == parents[block]['sha256']
            errors.append(check_input(raw, block))
            arrays += finite_arrays(raw)
            for snr in SNRS:
                obs = observed(raw, snr)
                for arm in ARMS:
                    e = entries['F',block,snr,arm]
                    record, value = verified_record(e, root)
                    assert record['input_record_sha256'] == ae['sha256'] and record['observed_hashes'] == hashes(obs)
                    check_receiver(value, arm, 1024)
                    scores = offline_score(value, raw)
                    assert scores == e['scores'] == record['scores']
                    rows.append(dict(block=block,snr=snr,arm=arm,seconds=e['seconds'],
                        CPU_seconds=e['CPU_seconds'], scores=scores, counts=value['counts'],
                        total_bp_iterations=sum(x['executed_iterations'] for x in value['bp_schedule']['calls']),
                        mean_bp_edges=float(np.mean([x['edges'] for x in value['bp_schedule']['calls']]))))
                    arrays += finite_arrays(value)
                    if engineering and block == 0 and snr == 15:
                        re = entries['F',block,snr,arm+'_REPEAT']
                        rr, rv = verified_record(re, root)
                        assert rr['observed_hashes'] == hashes(obs) and equal(rv, value)
                        assert rr['scores'] == re['scores'] == scores
                        arrays += finite_arrays(rv)
        return dict(rows=rows, arrays=arrays, saved_records=len(entries),
            max_cpp_relative_error=max(errors), coding_calls=0,
            exact_repeat_receivers=5 if engineering else 0)
    out = root/'runs'/args.tag/c['stage']
    if args.mode == 'audit':
        started = time.time()
        end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads((out/'summary.json').read_text())
        assert summary['status'] == 'COMPLETE'
        details = audit(summary)
        assert details == summary['raw_checks']
        guard.verify()
        report = dict(status='PASS', **details, source_sha256=sha(manifest),
            script_sha256=sha(Path(__file__)), contract_sha256=sha(contract),
            summary_sha256=sha(out/'summary.json'), wall_seconds=time.time()-started,
            scope=c['scope'], independence='main-session self-review; weak')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps({k:v for k,v in report.items() if k != 'rows'}))
        return
    run = LightRun(root/'runs'/args.tag,c['stage'],c['bounds'],c['output_bytes'],guard)
    try:
        setup_start = time.perf_counter()
        model = build_receiver(c['checkpoint_path'],system,1024,'cpu')
        assert model.learnable_heads == {'cand_active_rel'}
        assert model.cfg.k_leak == 2 and model.cfg.n_outer_iter == 10 and model.cfg.pic_iter == 20
        run.write('environment.json',dict(numpy=np.__version__,torch=torch.__version__,
            device='cpu',threads=1,lstsq_driver='gels',LDPC_constructed=False,
            model_setup_seconds=time.perf_counter()-setup_start,source_sha256=sha(manifest),
            checkpoint_sha256=c['checkpoint_sha256']))
        for block in c['blocks']:
            raw, record = run.call('A',dict(block=block,snr=10,arm='UNCODED_INPUT',split=1),
                lambda:generate(block),lambda v:{},dict(physical_record_sha256=parents[block]['sha256']))
            ae = run.records[-1]
            check_input(raw, block)
            for snr in SNRS:
                obs = observed(raw,snr)
                before = hashes(obs)
                order = list(ARMS)
                np.random.default_rng([20260914,730031,block,snr,2]).shuffle(order)
                for arm in order:
                    value, rec = run.call('F',dict(block=block,snr=snr,arm=arm,split=1),
                        lambda:receive(model,obs,arm),lambda v:offline_score(v,raw),
                        dict(observed_hashes=before,input_record_sha256=ae['sha256'],order=order))
                    assert hashes(obs) == before
                    print(json.dumps(dict(block=block,snr=snr,arm=arm,calls=run.counts,
                        scores=rec['scores'],seconds=rec['seconds'])),flush=True)
                    if engineering and block == 0 and snr == 15:
                        repeated, _ = run.call('F',dict(block=block,snr=snr,arm=arm+'_REPEAT',split=1),
                            lambda:receive(model,obs,arm),lambda v:offline_score(v,raw),
                            dict(observed_hashes=before,input_record_sha256=ae['sha256']))
                        assert hashes(obs) == before and equal(value,repeated)
        summary = dict(status='COMPLETE',calls=run.counts,records=run.records,
            source_sha256=sha(manifest),script_sha256=sha(Path(__file__)),
            contract_sha256=sha(contract),scope=c['scope'])
        summary['raw_checks'] = audit(summary)
        guard.verify()
        summary['wall_seconds'] = time.time()-run.started
        run.write('summary.json',summary)
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,wall_seconds=summary['wall_seconds'])),flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--script-sha256',required=True)
    parser.add_argument('--mode',choices=['run','audit'],default='run')
    main(parser.parse_args())
