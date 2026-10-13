"""Frozen-terminal support/gain diagnostics, explicitly run on CPU.

Truth interventions are not deployment methods or FER upper bounds. Integer
dictionary algebra and complete cancellation/detection inputs are retained.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch

from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha
from .budgeted_support_diagnostics import project_channel_on_support
from .classical_joint_unrolled import build_A_for_DALS_torch, reconstruct_H_torch
from .direction_receiver import terminal_decode
from .e1_ldpc import build_code
from .light_gap_replay import (CODE_KEYS, LightRun, check_decode_identity, decoder_scores,
                               setup_guard, verified_record)
from .supplement_adjacent_run import save_state

ARMS = ('I1_CPU', 'TRUE_CPU', 'PROJ_CURRENT', 'TOPK_TRUTH', 'DOMAIN_TRUTH',
        'TRUE_DATA_LS_CURRENT', 'OBS_LS_CURRENT', 'OBS_LS_TOPK')


def relative_error(actual, reference):
    return float(np.linalg.norm(actual-reference) / max(1., np.linalg.norm(reference)))


def terminal_equivalence(actual, expected):
    check_decode_identity(actual, expected)
    if not np.array_equal(actual['x_hard'], expected['x_hard']):
        raise ValueError('CPU terminal replay changed hard symbols')
    errors = {key: relative_error(actual[key], expected[key]) for key in ('mu', 'var', 'llr')}
    if max(errors.values()) > 1e-6:
        raise ValueError('CPU terminal replay exceeds1e-6: '+str(errors))
    return dict(soft_relative_l2=errors, decisions_exact=True)


def make_cases(raw, i1, observed, *, lmax=102, kmax=2):
    """Use only actual normalized generator coefficients; never renormalize again."""
    H = np.asarray(raw['H'], dtype=np.complex128)
    params, N = raw['params'], len(H)
    c1, c2 = float(params['c1']), float(params['c2'])
    width = 2*kmax+1
    ids = np.asarray(i1['support'], dtype=np.int64)
    if (ids.ndim != 1 or not len(ids) or len(np.unique(ids)) != len(ids)
            or np.any(ids < 0) or np.any(ids >= (lmax+1)*width)):
        raise ValueError('invalid frozen I1 support')
    pairs = {}
    lengths = [len(params[key]) for key in ('l_exp', 'k_exp', 'chan_coef_exp')]
    emitted = list(zip(params['l_exp'], params['k_exp'], params['chan_coef_exp']))
    if len(set(lengths)) != 1 or not emitted:
        raise ValueError('invalid generator atom inventory')
    for delay, doppler, gain in emitted:
        key = int(delay), int(doppler)
        if (key[0] != delay or key[1] != doppler or not 0 <= key[0] < N
                or abs(key[1]) > kmax or not np.isfinite(gain)):
            raise ValueError('generator atom outside declared integer model')
        pairs[key] = pairs.get(key, 0j)+complex(gain)

    def reconstruct(pair_list, gains):
        return reconstruct_H_torch(N, torch.tensor([p[0] for p in pair_list], dtype=torch.long),
            torch.tensor([p[1] for p in pair_list], dtype=torch.long),
            torch.tensor(gains, dtype=torch.complex128), c1, c2, kmax).numpy()

    def from_ids(chosen, gains):
        return reconstruct([(int(p)//width, int(p)%width-kmax) for p in chosen], gains)

    all_pairs = sorted(pairs)
    rebuilt = reconstruct(all_pairs, [pairs[p] for p in all_pairs])
    rebuilt_error = relative_error(rebuilt, H)
    if rebuilt_error > 1e-9:
        raise ValueError('normalized generator coefficients do not reconstruct trueH')
    truth_coefficients = np.zeros((lmax+1)*width, dtype=np.complex128)
    for (delay, doppler), gain in pairs.items():
        if delay <= lmax:
            truth_coefficients[delay*width+doppler+kmax] = gain
    top = np.argsort(-np.abs(truth_coefficients)**2, kind='stable')[:len(ids)]
    in_domain = np.flatnonzero(truth_coefficients != 0)
    delays, dopplers = torch.tensor(ids//width), torch.tensor(ids%width-kmax)
    projection, gains = project_channel_on_support(torch.from_numpy(H), delays, dopplers, c1, c2, kmax)
    projected_hat, _ = project_channel_on_support(
        torch.tensor(i1['H'], dtype=torch.complex128), delays, dopplers, c1, c2, kmax)

    def fit(chosen, data):
        A = build_A_for_DALS_torch(N, torch.tensor(chosen//width), torch.tensor(chosen%width-kmax),
            torch.tensor(observed['pilot']+data, dtype=torch.complex128), c1, c2, kmax).numpy()
        rcond = np.finfo(np.float64).eps*max(A.shape)
        coefficients, _, rank, singular = np.linalg.lstsq(A, observed['y'], rcond=rcond)
        normal = np.linalg.norm(A.conj().T@(A@coefficients-observed['y']))
        normal /= max(1., np.linalg.norm(A.conj().T@observed['y']))
        if not np.isfinite(coefficients).all() or normal > 1e-8:
            raise ValueError('gain fit failed finite/normal-equation check')
        return from_ids(chosen, coefficients), dict(gains=coefficients, rank=int(rank),
            singular_values=singular, rcond=rcond, normal_equation_relative_residual=float(normal))

    true_data, true_fit = fit(ids, raw['data'])
    obs_data, obs_fit = fit(ids, i1['x_soft'])
    obs_top, top_fit = fit(top, i1['x_soft'])
    cases = dict(I1_CPU=np.array(i1['H'], copy=True), TRUE_CPU=H.copy(),
        PROJ_CURRENT=projection.numpy(), TOPK_TRUTH=from_ids(top, truth_coefficients[top]),
        DOMAIN_TRUTH=from_ids(in_domain, truth_coefficients[in_domain]),
        TRUE_DATA_LS_CURRENT=true_data, OBS_LS_CURRENT=obs_data, OBS_LS_TOPK=obs_top)
    norm2 = float(np.linalg.norm(H)**2)
    representation = H-cases['PROJ_CURRENT']
    coefficients = cases['PROJ_CURRENT']-i1['H']
    metrics = dict(P_physical=int(params['taps']), K_emitted=len(emitted), K_unique=len(all_pairs),
        K_current=len(ids), K_truth_in_domain=len(in_domain), K_top=len(top),
        K_top_nonzero=int(np.count_nonzero(truth_coefficients[top])),
        K_outside_domain=sum(delay>lmax for delay,k in all_pairs),
        generator_reconstruction_relative_l2=rebuilt_error,
        NMSE={arm:float(np.linalg.norm(value-H)**2/norm2) for arm,value in cases.items()},
        current_representation_error=float(np.linalg.norm(representation)**2/norm2),
        current_coefficient_error=float(np.linalg.norm(coefficients)**2/norm2),
        decomposition_cross_term=float(2*np.vdot(representation, coefficients).real/norm2),
        estimated_H_outside_own_span=float(np.linalg.norm(i1['H']-projected_hat.numpy())**2/norm2),
        truth_scope='explicit trueH/true data/topK diagnostics; observed LS uses cached scaled x_soft',
        projection_scope='Frobenius/NMSE optimum only, never a FER upper bound')
    state = dict(channels=cases, current_support=ids, top_support=top, domain_support=in_domain,
                 truth_coefficients=truth_coefficients, current_projected_gains=gains.numpy(),
                 fits=dict(TRUE_DATA_LS_CURRENT=true_fit, OBS_LS_CURRENT=obs_fit, OBS_LS_TOPK=top_fit))
    return cases, metrics, state


def execute(args):
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('contract or source manifest changed')
    contract = json.loads(args.contract.read_text())
    if (contract['schema'] != 'i1-light-support-v1' or contract['device'] != 'cpu'
            or tuple(contract['arms']) != ARMS or contract['N'] != 1024 or contract['rho'] != .5
            or contract['snrs'] != [7,8] or contract['engineering_blocks'] != 2
            or contract['development_blocks'] != 64
            or contract['bounds'] != {'engineering': {'T':36,'seconds':180},
                                      'development': {'T':1024,'seconds':1800}}):
        raise ValueError('support probe differs from frozen contract')
    root = args.root.resolve()
    if not root.is_relative_to(Path('/data/guoyikun/')):
        raise ValueError('real outputs must be under authorized data root')
    guard = setup_guard(args, contract)
    if args.stage == 'development':
        if args.admission is None or sha(args.admission) != args.admission_sha256:
            raise ValueError('development needs hashed support admission')
        admission = json.loads(args.admission.read_text())
        if (admission['status'] != 'PASS' or admission['contract_sha256'] != args.contract_sha256
                or admission['source_sha256'] != args.source_sha256
                or admission['engineering_summary_sha256'] != sha(root/'engineering/summary.json')):
            raise ValueError('support admission does not match this run')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(root, args.stage, contract['bounds'][args.stage], contract['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        old_root = Path(contract['old_root'])
        old_stage = old_root/'runs'/args.stage
        summary = json.loads((old_stage/'summary.json').read_text())
        environment = json.loads((old_stage/'environment.json').read_text())
        code_hashes = hashes({key:code[key] for key in CODE_KEYS})
        if code_hashes != environment['code_identity']:
            raise ValueError('support experiment code identity differs')
        run.write('environment.json', dict(device='cpu',threads=1,numpy=np.__version__,torch=torch.__version__,
            contract_sha256=args.contract_sha256,source_manifest_sha256=args.source_sha256,code_identity=code_hashes))
        index = {(r['block'],r['snr'],r['arm']):r for r in summary['records']}
        exogenous = {r['block']:r for r in summary['exogenous']}
        if len(index) != len(summary['records']) or len(exogenous) != contract[args.stage+'_blocks']:
            raise ValueError('old source observation inventory differs')
        contexts, comparisons, used_inputs = [], [], []
        for block in range(contract[args.stage+'_blocks']):
            exo = exogenous[block]
            raw = load_state(exo['state'])
            if hashes({key:raw[key] for key in exo['hashes']}) != exo['hashes']:
                raise ValueError('exogenous hashes differ')
            for snr in contract['snrs']:
                run.check()
                observed = observed_at_snr(raw,snr)
                item = index[block,snr,'I1']
                old_record, i1 = verified_record(item,old_root)
                used_inputs.append(dict(record=item['record'],sha256=item['sha256'],state=old_record['state']['file']))
                start = time.perf_counter()
                cases, metrics, state = make_cases(raw,i1,observed,lmax=contract['l_max'],kmax=contract['k_max'])
                algebra_seconds = time.perf_counter()-start
                artifact = save_state(run.out/f'cases-{block:03d}-{snr}.npz',state,run.meter,readback=True)
                context = dict(block=block,snr=snr,split=exo['split'],state=artifact,metrics=metrics,
                    algebra_seconds=algebra_seconds,exogenous_hashes=exo['hashes'],
                    observed_hashes=hashes(observed),sigma=float(i1['sigma2_terminal']),source_record=item)
                run.write(f'cases-{block:03d}-{snr}.json',context)
                contexts.append(context)
                outputs={}
                for arm in ARMS + (('I1_REPEAT',) if args.stage=='engineering' else ()):
                    H = cases['I1_CPU' if arm=='I1_REPEAT' else arm]
                    z = observed['y']-H@observed['pilot']
                    sigma = float(i1['sigma2_terminal'])
                    value, _ = run.call('T',dict(block=block,snr=snr,split=exo['split'],arm=arm),
                        lambda:terminal_decode(z,H,sigma,observed['constellation'],code,device='cpu',audit=True),
                        lambda value:dict(decoder_scores(value,raw),channel_NMSE=float(np.linalg.norm(H-raw['H'])**2/np.linalg.norm(raw['H'])**2)),
                        dict(terminal_input_hashes=hashes(dict(y=z,H=H,sigma=np.asarray(sigma),constellation=observed['constellation'])),
                             exogenous_hashes=exo['hashes'],case_file=artifact['file'],
                             truth_access=metrics['truth_scope'] if arm not in ('I1_CPU','I1_REPEAT','OBS_LS_CURRENT') else 'offline scoring only'))
                    outputs[arm]=value
                if args.stage=='engineering':
                    _, old_true = verified_record(index[block,snr,'BP_TRUE_BASE'],old_root)
                    comparisons.append(dict(block=block,snr=snr,
                        I1_CPU_vs_old=terminal_equivalence(outputs['I1_CPU'],i1),
                        TRUE_CPU_vs_old=terminal_equivalence(outputs['TRUE_CPU'],old_true),
                        I1_repeat=terminal_equivalence(outputs['I1_REPEAT'],outputs['I1_CPU'])))
                print(json.dumps(dict(stage=args.stage,block=block,snr=snr,calls=run.counts)),flush=True)
        if run.counts != {k:v for k,v in run.bounds.items() if k!='seconds'}:
            raise ValueError('support call inventory incomplete')
        if hashes({key:code[key] for key in CODE_KEYS}) != code_hashes:
            raise ValueError('code changed during terminal probe')
        for item in used_inputs:
            if sha(item['record'])!=item['sha256'] or sha(item['state']['path'])!=item['state']['sha256']:
                raise ValueError('old source changed during support run')
        guard.verify()
        run.meter.verify()
        report=dict(schema='i1-light-support-stage-v1',status='COMPLETE',stage=args.stage,
            calls=dict(run.counts,F=0,D=0),bounds=run.bounds,records=run.records,contexts=contexts,
            engineering_comparisons=comparisons,input_inventory=used_inputs,
            independent_blocks=contract[args.stage+'_blocks'],exogenous=list(exogenous.values()),
            wall_seconds=time.time()-run.started,contract_sha256=args.contract_sha256,
            source_manifest_sha256=args.source_sha256,code_identity=code_hashes,
            scope='fixed terminal diagnostics on old development blocks; not deployable oracle performance')
        run.write('summary.json',report)
        run.meter.verify()
        print(json.dumps({k:report[k] for k in ('status','calls','wall_seconds')}),flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',required=True,choices=('engineering','development'))
    for name in ('root','contract','source-manifest'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('contract-sha256','source-sha256'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--admission',type=Path)
    parser.add_argument('--admission-sha256')
    execute(parser.parse_args())


if __name__=='__main__':
    main()
