#!/usr/bin/env python3
"""Frozen two-stage SBL on fresh shared P1 frames, with exactly three final arms."""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
from pathlib import Path
import sys
import time
import traceback
from unittest import mock
import numpy as np

HERE = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE/filename)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


gamma = module('__fresh_gamma_reference', 'gamma_ablation.py')
cohort = gamma.cohort
ROOT, V = cohort.ROOT, cohort.VARIANTS
FRAMES = range(2000000, 2000050)
EXPECTED = {(sc,300,snr,f) for sc in ('U','G') for snr in (700,800) for f in FRAMES}
ARMS = ('L-diag/full', 'L-cov/full', 'L-cov/joint')
CONTROL = 'L-cov/joint'
SCHEMA = 'fresh-three-arm-sbl-v1'
OUT = gamma.FULL.parent/'fresh_cohort1'
OWN = ('fresh_cohort.py', 'aggregate_fresh_cohort.py', 'launch_fresh_cohort.sh',
       'test_fresh_cohort.py', 'test_aggregate_fresh_cohort.py', 'gamma_ablation.py')


def cov_order(meta):
    index = meta['frame']-FRAMES.start+('U','G').index(meta['scenario'])+(700,800).index(meta['snr_centi_db'])
    return ('full','joint') if index%2 == 0 else ('joint','full')


def terminal_score(ctx, e3d, oldd, det, dec, channel, truth, data_af, coded, elapsed, decoded_seconds):
    """Score the already returned decoder output; never call a decoder here."""
    error = int(e3d.gd.score(ctx, dec['decoded'], truth))
    path = dict(delays=channel.delays, dopplers=channel.dopplers, gains=det['gains'])
    score = dict(info_errors=error, fer=int(error>0), decoded_sha256=e3d.gd.bits_sha(dec['decoded']),
        ldpc_iters=int(dec['iterations']), extrinsic_bit_logloss=oldd.bit_loss(det['extrinsic'],coded),
        nmse_final=float(e3d.crb.channel_nmse(path,e3d.truth_paths(truth),channel.n)),
        data_mse_final=float(np.mean(np.abs(det['mu']-data_af)**2)), symbol_variance_final=float(np.mean(det['variance'])),
        detect_seconds=elapsed, decode_seconds=decoded_seconds, final_gains=oldd.pairs(det['gains']), trace=det['trace'],
        fft_count=det['fft_count'], recorded_states=len(det['states']), native_symbol_fft_count=41,
        gain_solve_calls=det.get('gain_solve_calls',0), covariance_solve_calls=det.get('covariance_solve_calls',0),
        gamma_fft_count=det.get('gamma_fft_count',0), gain_variance=det['gain_variance'].tolist(),
        block_diagnostics=[{k:v for k,v in d.items() if k!='covariance'} for d in det.get('gain_blocks',[])])
    cohort.validate_score(score)
    return score


def process_key(ctx, helper, block, native, physical, cache, grid, meta, obs, data_af, truth, generation):
    e3d, oldd = helper.e3d, helper.replay.oldd
    row = dict(meta, schema=SCHEMA, status='running', n_symbols=len(obs['y']), arms={}, upstream={}, attempts=[], sbl_fits=[],
        sbl_calls=0, receiver_calls=0, decoder_calls=0, generation=generation)
    try:
        coded = ctx.encode(ctx.code, truth['info'])
        if not np.array_equal(coded,truth['coded']) or coded.shape != (2*len(obs['y']),):
            raise ValueError('re-encoded physical codeword mismatch')
        row['input_sha256'] = {k:oldd.sha(obs[k]) for k in ('y','pilot')}
        row['input_sha256']['coded'] = e3d.gd.bits_sha(coded)
        row['shared_frame_fingerprint'] = list(e3d.p1ctx.p1_driver.pair_fingerprint(truth))
        original_detect, original_sbl = e3d.detect_decode, e3d.sbl.sbl_em
        original_native, original_decoder = ctx.native.scalar_joint, ctx.native.decoder_messages
        captured = []

        def native_counted(*args, **kwargs):
            row['receiver_calls'] += 1
            return original_native(*args, **kwargs)

        def decoder_counted(*args, **kwargs):
            row['decoder_calls'] += 1
            return original_decoder(*args, **kwargs)

        def fit_counted(B,Y,*args,**kwargs):
            index = len(row['sbl_fits'])
            record = dict(stage=('stage1','L-diag','L-cov')[index] if index<3 else 'unexpected',status='running',
                B_shape=list(B.shape),B_sha256=oldd.sha(B),Y_sha256=oldd.sha(Y),
                max_iter=int(kwargs.get('max_iter',e3d.sbl.MAX_ITER)),beta0=float(kwargs['beta0']),
                Gamma_kind='none' if kwargs.get('Gamma') is None else ('scalar' if np.isscalar(kwargs['Gamma']) else 'full'),
                Gamma_sha256=None if kwargs.get('Gamma') is None else oldd.sha(np.asarray(kwargs['Gamma'])))
            row['sbl_fits'].append(record); row['sbl_calls'] += 1
            start = time.perf_counter()
            try:
                if index>=3 or record['max_iter']!=100: raise ValueError('unexpected SBL count/iteration budget')
                result = original_sbl(B,Y,*args,**kwargs)
                record.update({k:result[k] for k in ('iterations','converged','n_start','n_final','beta','jitter_events')})
                if (not np.isfinite(result['mu']).all() or not np.isfinite(result['gamma']).all()
                        or not np.isfinite(result['beta']) or result['beta']<=0 or not 1<=result['iterations']<=100):
                    raise ValueError('invalid SBL fit result')
                record['status']='ok'
                return result
            except Exception:
                record['status']='error'; raise
            finally:
                record['seconds']=time.perf_counter()-start

        def wrapped(c, observation, channel, prior):
            if prior is None:
                attempt = dict(stage='round1',status='running');row['attempts'].append(attempt)
                try:
                    result = original_detect(c,observation,channel,None)
                    det,dec,td,tc = result
                    row['round1_receipt'] = dict(decoded_sha256=e3d.gd.bits_sha(dec['decoded']),
                        check_prior=np.clip(dec['raw_check_extrinsic'],-20,20).tolist(),
                        check_prior_sha256=oldd.sha(np.clip(dec['raw_check_extrinsic'],-20,20)),
                        detect_seconds=td,decode_seconds=tc,fft_count=det['fft_count'])
                    attempt['status']='ok'
                    return result
                except Exception:
                    attempt['status']='error';raise
            if len(captured)>=2: raise ValueError('extra stage2 detector invocation')
            variant = V[len(captured)]; captured.append(variant)
            prior = np.asarray(prior,float)
            original_prior = np.asarray(row['round1_receipt']['check_prior'],float)
            if not np.array_equal(prior,original_prior) or oldd.sha(prior)!=row['round1_receipt']['check_prior_sha256']:
                raise ValueError('stage2 prior changed or final-decoder feedback entered pipeline')
            row['upstream'][variant] = dict(support=dict(delays=channel.delays.tolist(),dopplers=channel.dopplers.tolist()),
                h0=oldd.pairs(channel.gains),prior_sha256=oldd.sha(prior))
            order = ('full',) if variant=='L-diag' else cov_order(meta)
            selected = None
            for mode in order:
                attempt = dict(stage=variant,mode=mode,status='detecting',detect_seconds=None,decode_seconds=None)
                row['attempts'].append(attempt)
                start = time.perf_counter()
                try:
                    common = dict(pd=1-c.system.rho,prior=prior,iterations=20,damping=.3,record_states=True)
                    if mode=='full':
                        row['receiver_calls'] += 1
                        det=block.scalar_point(observation['y'],observation['pilot'],channel,observation['sigma2'],
                            native=native,physical=physical,gain_block='full',**common)
                    else:
                        det=c.native.scalar_joint(observation['y'],observation['pilot'],channel,observation['sigma2'],gain_mode='joint',**common)
                finally:
                    attempt['detect_seconds']=time.perf_counter()-start
                cohort.validate_detection(det,mode,channel,observation['sigma2'])
                attempt['status']='decoding'; start=time.perf_counter()
                try:
                    dec=c.native.decoder_messages(c.code,np.clip(det['extrinsic'],-20,20),maxiter=50)
                finally:
                    attempt['decode_seconds']=time.perf_counter()-start
                score=terminal_score(c,e3d,oldd,det,dec,channel,truth,data_af,coded,attempt['detect_seconds'],attempt['decode_seconds'])
                row['arms'][variant+'/'+mode]=score;attempt['status']='ok'
                if mode==('full' if variant=='L-diag' else 'joint'):
                    selected=(det,dec,attempt['detect_seconds'],attempt['decode_seconds'])
            return selected

        with mock.patch.object(e3d,'detect_decode',wrapped), mock.patch.object(e3d.sbl,'sbl_em',fit_counted), \
                mock.patch.object(ctx.native,'scalar_joint',native_counted), mock.patch.object(ctx.native,'decoder_messages',decoder_counted):
            pipeline=e3d.process_key(ctx,cache,grid,obs,data_af,truth,meta,V,max_iter=100)
        if captured!=list(V) or (row['sbl_calls'],row['receiver_calls'],row['decoder_calls'])!=(3,4,4):
            raise ValueError('two-stage SBL/receiver/decoder coverage')
        for variant in V:
            pipeline['variants'][variant]['pipeline_return_mode']='full' if variant=='L-diag' else 'joint'
        row.update(status='ok',pipeline=pipeline)
    except Exception as exc:
        for attempt in row['attempts']:
            if attempt['status']!='ok': attempt['status']='error'
        row.update(status='error',error=repr(exc),error_trace=traceback.format_exc()[-4000:])
    return row


def validate_gate(row, three, old, full):
    if row['status']!='ok' or gamma.oldagg.key(row)!=cohort.KEY: raise ValueError('failed/wrong gate key')
    r1=row['pipeline']['round1']; saved=three['round1']
    for field in ('decoded_sha256','info_errors','ldpc_iters','syndrome'):
        if r1[field]!=saved[field]: raise AssertionError(f'round1 replay {field}')
    if row['input_sha256']['y']!=full['observation_sha256']['y'] or row['input_sha256']['pilot']!=full['observation_sha256']['pilot']:
        raise AssertionError('gate observation drift')
    _,prior=gamma.oldagg.reference.restore_inputs(old)
    if not np.array_equal(prior,np.asarray(row['round1_receipt']['check_prior'])): raise AssertionError('gate original prior drift')
    for variant in V:
        expected={k:three['three_mode'][variant][k] for k in ('support','h0','prior_sha256')}
        if row['upstream'][variant]!=expected: raise AssertionError('gate SBL support/h0/prior drift')
        gamma.validate_full(row['arms'][variant+'/full'],full['arms'][variant]['full'])
    cohort.validate_baseline(row['arms'][CONTROL],three['three_mode']['L-cov']['modes']['joint'])
    return True


def run(args):
    if not re.fullmatch(r'[0-9a-f]{40}',args.producing_commit): raise ValueError('full producing commit required')
    if not 0<=args.shard<12 or not 0<args.deadline_seconds<=690 or (args.gate_only and args.shard!=0):
        raise ValueError('registered12 shards, <=690s deadline; gate shard0')
    out=args.out.resolve()
    if out!=OUT: raise ValueError('registered fresh /data output only')
    helper=module('__fresh_helper','restart_point.py');trajectory=module('__fresh_trajectory','trajectory_analysis.py')
    block=module('__fresh_block','gram_block.py')
    if helper.e3d.e3_lib.md5_file(Path(block.__file__))!=cohort.BLOCK_MD5: raise ValueError('immutable block changed')
    if Path(gamma.__file__).resolve()!=(HERE/'gamma_ablation.py').resolve():
        raise ValueError('actual Gamma reference helper path changed')
    ctx=helper.e3d.p1ctx.load()
    three,old,receipt=cohort.load_references(args,ctx,helper,trajectory)
    full,full_receipt=gamma.load_full(args.full_rows,three,old,receipt)
    for name,digest in full_receipt['identity']['own_md5'].items():
        if helper.e3d.e3_lib.md5_file(ROOT/name)!=digest: raise ValueError(f'old producing helper changed: {name}')
    e3d=helper.e3d;native=sys.modules[ctx.native.scalar_joint.__module__];physical=sys.modules['physical']
    config=dict(schema=SCHEMA,producing_commit=args.producing_commit,shard=args.shard,frames=[FRAMES.start,FRAMES.stop],arms=ARMS,reference=receipt,full_reference=full_receipt,
        source_md5=ctx.source_md5,frozen_actual_paths=receipt['run2']['identity']['frozen_actual_paths'],
        own_md5={name:e3d.e3_lib.md5_file(HERE/name) for name in OWN},
        gamma_helper_path=str(Path(gamma.__file__).resolve()),hyper=e3d.sbl.HYPER,environment=ctx.environment,
        family_P1=dict(entropy=e3d.p1ctx.p1_driver.ENTROPY_HEX,domain=e3d.p1ctx.p1_driver.DOMAIN),
        deadline_seconds=args.deadline_seconds,timing_scope='shared SBL pipeline plus diagnostic multipath receivers; not optimized deployment latency')
    config=json.loads(json.dumps(config,allow_nan=False))  # Compare serialized tuples/lists consistently.
    if not args.gate_only:
        gate=json.loads((out/'gate.json').read_text())
        if gate.get('passed') is not True or any(gate['_config'][k]!=config[k] for k in config if k!='shard'):
            raise ValueError('successful identical-source gate required before fresh frames')
    out.mkdir(parents=True,exist_ok=True)
    stem='gate' if args.gate_only else f'shard{args.shard:03d}'
    row_path=out/('gate_attempt.jsonl' if args.gate_only else f'rows_{stem}.jsonl')
    cfg_path=out/f'config_{stem}.json'
    if row_path.exists() or cfg_path.exists(): raise FileExistsError('fresh output required')
    with cfg_path.open('x') as handle: handle.write(json.dumps(dict(_argv=sys.argv[1:],_config=config),allow_nan=False,indent=1)+'\n')
    cache=e3d.PilotCache();grid=e3d.sbl.full_grid(int(ctx.system.l_max_cap));base_original=e3d.p1ctx.base;generations={}
    def base_counted(c,scenario,rho,frame):
        if (scenario,frame) in generations: raise ValueError('duplicate physical base generation')
        start=time.perf_counter();raw,diag=base_original(c,scenario,rho,frame)
        generations[(scenario,frame)]=dict(scenario=scenario,frame=frame,seconds=time.perf_counter()-start,
            info_sha256=e3d.gd.bits_sha(raw['info']),coded_sha256=e3d.gd.bits_sha(raw['coded']),
            noise_sha256=helper.replay.oldd.sha(raw['noise']),channel_seed=int(raw['channel_seed']))
        return raw,diag
    start=time.monotonic()
    with row_path.open('x') as handle, mock.patch.object(e3d.p1ctx,'base',base_counted):
        if args.gate_only:
            raw,diag=e3d.p1ctx.base(ctx,'U',.3,9100)
            cells=[e3d.observe_key(ctx,raw,diag,'U',300,700,9100)]
        else:
            cells=(cell for f in list(FRAMES)[args.shard::12] for cell in e3d.cells_of_frame(ctx,f,helper.replay.GRID,None))
        for meta,obs,data_af,truth in cells:
            if time.monotonic()-start>args.deadline_seconds:
                row=dict(meta,status='error',error='fresh shard deadline',sbl_calls=0,receiver_calls=0,decoder_calls=0)
            else:
                row=process_key(ctx,helper,block,native,physical,cache,grid,meta,obs,data_af,truth,generations[(meta['scenario'],meta['frame'])])
            e3d.write_row(handle,row)
            if row['status']!='ok': raise RuntimeError(f'failed {e3d.key_of(meta)}: {row["error"]}')
            if args.gate_only:
                try:
                    validator=module('__fresh_gate_validator','aggregate_fresh_cohort.py')
                    validator.validate([row],expected={cohort.KEY})
                    validate_gate(row,three[cohort.KEY],old[cohort.KEY],full[cohort.KEY])
                except Exception as exc:
                    with (out/'gate_failure.json').open('x') as failure: failure.write(json.dumps(dict(passed=False,error=repr(exc)))+'\n')
                    raise
                with (out/'gate.json').open('x') as gatefile:
                    gatefile.write(json.dumps(dict(passed=True,row_sha256=gamma.oldagg.row_sha(row),_config=config,_argv=sys.argv[1:]),indent=1,allow_nan=False)+'\n')
            print(f'{e3d.key_of(meta)} ok',flush=True)
    expected_bases=1 if args.gate_only else 2*len(list(FRAMES)[args.shard::12])
    if len(generations)!=expected_bases: raise ValueError('physical generation coverage')
    with (out/f'generations_{stem}.json').open('x') as handle: handle.write(json.dumps(list(generations.values()),allow_nan=False,indent=1)+'\n')


def main():
    parser=argparse.ArgumentParser()
    for name,default in (('old-rows',cohort.OLD),('three-rows',cohort.THREE),('full-rows',gamma.FULL),('out',OUT)):
        parser.add_argument('--'+name,type=Path,default=default)
    parser.add_argument('--shard',type=int,required=True);parser.add_argument('--deadline-seconds',type=float,default=690)
    parser.add_argument('--producing-commit',required=True)
    parser.add_argument('--gate-only',action='store_true');run(parser.parse_args())


if __name__=='__main__': main()
