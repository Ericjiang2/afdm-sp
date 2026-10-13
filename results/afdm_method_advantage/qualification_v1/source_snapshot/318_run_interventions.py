"""Bounded B campaign on frozen observations; never generate a new frame."""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
import traceback
from pathlib import Path

import numpy as np

from audit_io import attach, load_bound, sha256, unpack, verify_sources, write_csv, write_json


ARMS = ['J40R2', 'J20R3', 'true_geometry', 'true_H_TF20R2', 'true_H_EP8R2',
        'true_data_original_TF20R2', 'true_data_expanded_TF20R2']


def compare_replay(result, record, run, evidence):
    largest = 0.
    for cp in record['checkpoints']:
        saved = load_bound(evidence, run / cp['path'], cp['artifact_sha256'])
        r = cp['round']
        if not np.array_equal(result.arrays[f'r{r}_decoded'], unpack(saved['decoded'])):
            raise ValueError('baseline replay hard decision differs')
        for key in ['input_llr', 'app', 'check', 'delays', 'dopplers', 'gains', 'mu', 'variance']:
            a, b = np.asarray(result.arrays[f'r{r}_{key}']), np.asarray(saved['snapshot'][key])
            if a.shape != b.shape or not np.allclose(a, b, rtol=1e-12, atol=1e-12):
                raise ValueError(f'baseline replay differs: round{r}/{key}')
            largest = max(largest, float(np.max(abs(a-b))))
    return largest


def run_campaign(args):
    import interventions as wrappers
    import metrics
    run, out = args.run.resolve(), args.out.resolve()
    if out.exists():
        raise FileExistsError('B already attempted; no automatic retry')
    evidence = attach(args.source, args.baseline)
    manifest = json.loads((run/'manifest.json').read_text())
    verify_sources(manifest, args.source, args.baseline, evidence)
    chosen = json.loads(args.selection.read_text())['observations']
    if len(chosen) != 64 or sum(bool(x['baseline_error']) for x in chosen) != 32:
        raise ValueError('fixed32/32 selection differs')
    a_receipt = json.loads((args.selection.parent/'receipt.json').read_text())
    if (a_receipt['files']['selection.json'] != sha256(args.selection)
            or a_receipt['manifest_sha256'] != sha256(run/'manifest.json')
            or a_receipt['ledger_sha256'] != sha256(run/'ledger.jsonl')):
        raise ValueError('A selection/Part-B identity differs')
    cache = args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if sha256(cache) != a_receipt['ldpc_cache_sha256']:
        raise ValueError('frozen code cache differs before context construction')
    import native_twofft as native
    from receiver import context
    from physical import Channel, daft
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info, qpsk_map
    out.mkdir(parents=True)
    for folder in ['baseline_replay', 'arms', 'checkpoints', 'fits']:
        (out/folder).mkdir()
    environment = evidence.bind_runtime_environment()
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    if header['code_g_sha256'] != json.loads((run/'context_header.json').read_text())['code_g_sha256']:
        raise ValueError('code context differs')
    code_moments = metrics.exact_code_moments(code['G'], pd=1-system.rho)
    write_json(out/'manifest.json', dict(scope='A+B+C selected reused development frames only',
        arms=ARMS, maximum_receiver_calls=512, deadline_seconds=args.seconds,
        selection_sha256=sha256(args.selection), original_manifest_sha256=sha256(run/'manifest.json'),
        environment=environment, pid=os.getpid(), start_epoch=time.time(),
        audit_source_hashes={p.name:sha256(p) for p in Path(__file__).parent.glob('*.py')},
        original_baseline_outputs_immutable=True, no_new_observations=True))
    started = time.perf_counter()
    attempts, stages, fits, baseline_hashes = [], [], [], {}
    ledger = out/'ledger.jsonl'

    def save_attempt(row):
        attempts.append(row)
        with ledger.open('a') as stream:
            stream.write(json.dumps(row, allow_nan=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())

    for index, selected in enumerate(chosen):
        record = selected['baseline_record']
        stem = selected['observation_id']
        obs = load_bound(evidence, run/'frames'/f'{stem}_input.npz', selected['input_sha256'])
        truth = load_bound(evidence, run/'frames'/f'{stem}_truth.npz', selected['truth_sha256'])
        coded, info = unpack(truth['coded']), unpack(truth['info'])
        true_symbols = np.sqrt(1-system.rho)*qpsk_map(coded)
        true_channel = Channel(len(obs['y']), system.c1, system.c2,
                               truth['l_i'], truth['k_real'], truth['g_i'])
        order = ['baseline_replay'] + ARMS[index % len(ARMS):] + ARMS[:index % len(ARMS)]
        final_saved = load_bound(evidence, run/record['checkpoints'][-1]['path'],
                                 record['checkpoints'][-1]['artifact_sha256'])['snapshot']
        earlier = load_bound(evidence, run/record['checkpoints'][0]['path'],
                             record['checkpoints'][0]['artifact_sha256'])['snapshot']
        delays = np.asarray(final_saved['delays'], int)
        centers = np.array([earlier['dopplers'][np.flatnonzero(earlier['delays']==d)[0]] for d in delays])
        for arm in order:
            if len(attempts) >= 512 or time.perf_counter()-started >= args.seconds:
                raise TimeoutError('bounded B allocation/deadline reached')
            if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) >= 2*1024**3:
                raise RuntimeError('2GiB evidence cap reached')
            trace, checkpoints = {}, []
            identity = dict(schema='tf-production-gap-audit/1', observation_id=stem, arm=arm,
                            input_sha256=selected['input_sha256'])
            write_json(out/'inflight.json', dict(identity,start_epoch=time.time(), completed_calls=len(attempts)))
            begin = time.perf_counter()
            fitting_seconds = 0.
            fit_record = None
            receiver_started = False

            def sink(event, decoded):
                path = out/'checkpoints'/f"{stem}_{arm}_r{event['round']}.npz"
                digest = evidence.save_artifact(path, dict(event=event, decoded=decoded),
                                               dict(identity, round=event['round']))
                checkpoints.append(dict(round=event['round'], path=str(path.relative_to(out)),
                    artifact_sha256=digest, receiver_ready_seconds=event['ready'],
                    complete_intervention_ready_seconds=fitting_seconds+event['ready'],
                    _decoded=decoded.copy(),
                    event={k:v for k,v in event.items() if k!='snapshot'}))

            def score_checkpoints():
                for checkpoint in checkpoints:
                    decoded = checkpoint.pop('_decoded')
                    checkpoint.update(info_errors=int(np.count_nonzero(extract_info(code,decoded)!=info)),
                        coded_errors=int(np.count_nonzero(decoded!=coded)),
                        syndrome_weight=int(np.count_nonzero((code['H']@decoded)%2)))
            try:
                kwargs = dict(checkpoint_sink=sink, trace=trace)
                if arm == 'baseline_replay':
                    receiver_started = True
                    result = wrappers.run_instrumented_baseline(obs, system, code, native, **kwargs)
                    max_difference = compare_replay(result, record, run, evidence)
                elif arm in ['J40R2','J20R3']:
                    receiver_started = True
                    result = wrappers.run_more_work(obs, system, code, native, arm=arm, **kwargs)
                elif arm == 'true_geometry':
                    receiver_started = True
                    result = wrappers.run_true_geometry(obs, system, code, native,
                        delays=truth['l_i'], dopplers=truth['k_real'], **kwargs)
                elif arm.startswith('true_H_'):
                    receiver_started = True
                    result = wrappers.run_fixed_channel(obs, system, code, native, channel=true_channel,
                        detector='ep' if 'EP8' in arm else 'tf', **kwargs)
                else:
                    fit_start = time.perf_counter()
                    bounds = metrics.final_refit_bounds(centers, expanded='expanded' in arm)
                    starts = np.array([np.asarray(final_saved['dopplers']), bounds[:,0],
                                       bounds.mean(axis=1), bounds[:,1]])
                    fit = metrics.search_geometry(daft(obs['y'],system.c1,system.c2,True),
                        obs['pilot']+true_symbols, delays, starts, bounds, system.c1, system.c2,
                        obs['sigma2'], objective='profile', passes=2, maxiter=16)
                    channel = Channel(len(obs['y']),system.c1,system.c2,delays,fit['dopplers'],fit['gains'])
                    fitting_seconds = time.perf_counter()-fit_start
                    # Offline truth evaluation is outside receiver/fit latency.
                    mismatch = metrics.operator_mismatch(channel, true_channel, obs['pilot'],
                                                         data_covariance=code_moments['covariance'],
                                                         data_mean=code_moments['mean'])
                    fit_record = dict(observation_id=stem,arm=arm,fit_seconds=fitting_seconds,
                        evaluations=fit['evaluations'],profile_score=fit['score'],
                        operator_frobenius_squared=mismatch['operator_frobenius_squared'],
                        sp_weighted_mismatch=mismatch['sp_weighted_mismatch'])
                    fits.append(fit_record)
                    evidence.save_artifact(out/'fits'/f'{stem}_{arm}.npz',
                        dict(fit=fit, mismatch=mismatch, info_access='true symbols only in this offline fit'),identity)
                    receiver_started = True
                    result = wrappers.run_fixed_channel(obs, system, code, native,
                                                        channel=channel, detector='tf', **kwargs)
                complete = fitting_seconds + float(result.timing['seconds'])
                score_checkpoints()
                row = dict(observation_id=stem, frame=selected['frame'], arm=arm, status='ok',
                    baseline_error=selected['baseline_error'], original_baseline_complete_seconds=record['seconds'],
                    original_baseline_first_ready=record['checkpoints'][0]['ready'],
                    info_errors=checkpoints[-1]['info_errors'], coded_errors=checkpoints[-1]['coded_errors'],
                    syndrome_weight=checkpoints[-1]['syndrome_weight'],
                    complete_seconds=complete, fitting_seconds=fitting_seconds,
                    receiver_started=True,
                    wrapper_wall_seconds=time.perf_counter()-begin, checkpoints=checkpoints,
                    rescue=bool(selected['baseline_error'] and checkpoints[-1]['info_errors']==0),
                    harm=bool(not selected['baseline_error'] and checkpoints[-1]['info_errors']>0))
                payload = dict(decoder=result.decoder,arrays=result.arrays,timing=result.timing,trace=result.trace)
                path = out/('baseline_replay' if arm=='baseline_replay' else 'arms')/(
                    f'{stem}.npz' if arm=='baseline_replay' else f'{stem}_{arm}.npz')
                row['artifact_sha256']=evidence.save_artifact(path,payload,identity)
                row['path']=str(path.relative_to(out))
                if arm=='baseline_replay':
                    baseline_hashes[stem]=row['artifact_sha256']
                    row['max_continuous_replay_difference']=max_difference
                save_attempt(row)
                for event in result.timing['events']:
                    stages.append(dict(observation_id=stem,arm=arm,**event,
                        acquisition_seconds=result.trace.get('acquisition_seconds',result.timing['pilot_seconds']),
                        initial_override_seconds=(result.trace.get('initial_override') or {}).get('seconds'),
                        complete_seconds=complete, fitting_seconds=fitting_seconds))
            except BaseException as error:
                elapsed=time.perf_counter()-begin
                for checkpoint in checkpoints:
                    checkpoint.pop('_decoded', None)
                evidence.save_artifact(out/'failure_trace.npz',dict(trace=trace,checkpoints=checkpoints,
                    exception=traceback.format_exc()),identity)
                save_attempt(dict(observation_id=stem,arm=arm,status='failed',
                    complete_seconds=elapsed, checkpoints=checkpoints, exception=repr(error),
                    receiver_started=receiver_started))
                write_json(out/'blocked.json',dict(reason=repr(error),calls_attempted=len(attempts),
                    elapsed_seconds=time.perf_counter()-started))
                raise
            print(stem,arm,'info_errors',row['info_errors'],'seconds',round(complete,3),flush=True)
    write_csv(out/'intervention_pairs.csv',[{k:v for k,v in row.items() if k!='checkpoints'} for row in attempts])
    write_csv(out/'stage_costs.csv',stages)
    write_csv(out/'true_data_fits.csv',fits)
    summary = {arm:dict(calls=sum(r['arm']==arm for r in attempts),
        rescues=sum(r.get('rescue',False) for r in attempts if r['arm']==arm),
        harms=sum(r.get('harm',False) for r in attempts if r['arm']==arm),
        remaining_selected_failures=sum(r['info_errors']>0 and r['baseline_error'] for r in attempts if r['arm']==arm),
        complete_seconds_total=sum(r['complete_seconds'] for r in attempts if r['arm']==arm))
        for arm in ['baseline_replay']+ARMS}
    write_json(out/'summary.json',summary)
    write_json(out/'receipt.json',dict(status='pass',receiver_calls=512,observations=64,
        newly_generated_observations=0, baseline_replay_hashes=baseline_hashes,
        total_elapsed_seconds=time.perf_counter()-started,ledger_sha256=sha256(ledger),
        audit_source_hashes={p.name:sha256(p) for p in Path(__file__).parent.glob('*.py')},
        files={p.name:sha256(p) for p in out.iterdir() if p.is_file()}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    for name in ['run','source','baseline','selection','out']:
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--seconds',type=float,default=3600)
    run_campaign(parser.parse_args())
