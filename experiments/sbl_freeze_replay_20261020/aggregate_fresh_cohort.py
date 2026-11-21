#!/usr/bin/env python3
"""Prospective three-arm paired readout; no generator, SBL or receiver calls."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('__fresh_producer',HERE/'fresh_cohort.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
a=f.gamma.oldagg
SEED,N_BOOT=20261028,10000
METRICS=('extrinsic_bit_logloss','fer','info_errors','nmse_final','data_mse_final','symbol_variance_final')
IDENTITY=('producing_commit','schema','frames','arms','reference','full_reference','source_md5','frozen_actual_paths','own_md5','gamma_helper_path','hyper','family_P1','timing_scope')


def validate_score(score,mode,p,noise):
    f.cohort.validate_score(score)
    full=mode=='full';gains=np.asarray(score['final_gains']);variance=np.asarray(score['gain_variance'])
    if (gains.shape!=(p,2) or not np.isfinite(gains).all() or variance.shape!=(p,) or not np.isfinite(variance).all()
            or np.any(variance<0) or (full and np.any(variance!=0)) or score['recorded_states']!=20
            or score['fft_count']!=(61 if full else 41) or score['native_symbol_fft_count']!=41
            or any(score[name]!=(20 if full else 0) for name in ('gain_solve_calls','covariance_solve_calls','gamma_fft_count'))):
        raise ValueError('terminal shape/variance/primitive count')
    trace=score['trace'];diagnostics=score['block_diagnostics']
    if (len(trace)!=20 or [t['iteration'] for t in trace]!=list(range(20))
            or any(not all(np.isfinite(v) for v in t.values()) or t['fft_count']!=(3 if full else 2)
                   or t['gain_variance']<0 or (full and t['gain_variance']!=0) for t in trace)
            or len(diagnostics)!=(20 if full else 0)):
        raise ValueError('terminal finite trace/diagnostics coverage')
    for i,d in enumerate(diagnostics):
        if (d['iteration']!=i or d['gamma_fft_count']!=1 or not all(np.isfinite(v) for v in d.values())
                or d['normal_relative_residual']>1e-10 or d['covariance_relative_residual']>1e-10
                or not np.isclose(d['alpha'],noise*p,rtol=1e-10,atol=1e-12) or d['seconds']<0 or d['solve_seconds']<0):
            raise ValueError('terminal invalid solve diagnostics')


def validate(rows,expected=f.EXPECTED):
    keys=[a.key(r) for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=expected: raise ValueError('missing/duplicate/extra fresh keys')
    for r in rows:
        if (r.get('schema')!=f.SCHEMA or r.get('status')!='ok' or set(r['arms'])!=set(f.ARMS)
                or (r['sbl_calls'],r['receiver_calls'],r['decoder_calls'])!=(3,4,4)
                or set(r['upstream'])!=set(f.V) or set(r['input_sha256'])!={'y','pilot','coded'}):
            raise ValueError('failed row/arm/count/input coverage')
        prior=np.asarray(r['round1_receipt']['check_prior'],float)
        if prior.shape!=(2*r['n_symbols'],) or not np.isfinite(prior).all() or a.reference.array_sha(prior)!=r['round1_receipt']['check_prior_sha256']:
            raise ValueError('saved original check-prior binding')
        p=r['pipeline'];noise=p['sigma2']
        if not np.isfinite(noise) or noise<=0 or set(p['variants'])!=set(f.V): raise ValueError('pipeline noise/variants')
        if (r['round1_receipt']['decoded_sha256']!=p['round1']['decoded_sha256'] or r['round1_receipt']['fft_count']!=41
                or p['round1']['info_errors']<0 or not 1<=p['round1']['ldpc_iters']<=50):
            raise ValueError('round1 pipeline/receipt mismatch')
        for v in f.V:
            upstream=r['upstream'][v];h=np.asarray(upstream['h0']);support=upstream['support'];n=len(h)
            if (not 1<=n<=24 or h.shape!=(n,2) or not np.isfinite(h).all()
                    or len(support['delays'])!=n or len(support['dopplers'])!=n
                    or not np.isfinite(support['dopplers']).all() or not np.isfinite(support['delays']).all()
                    or upstream['prior_sha256']!=r['round1_receipt']['check_prior_sha256']
                    or p['variants'][v]['n_atoms']!=n or p['variants'][v]['sbl']['max_iter']!=100
                    or p['variants'][v]['pipeline_return_mode']!=('full' if v=='L-diag' else 'joint')):
                raise ValueError('upstream support/prior/budget/return-mode drift')
            atoms=np.asarray(p['variants'][v]['atoms'])
            if (atoms.shape!=(n,3) or not np.isfinite(atoms).all() or not np.array_equal(atoms[:,0],support['delays'])
                    or not np.array_equal(atoms[:,1],support['dopplers'])
                    or not np.allclose(atoms[:,2],np.sum(h*h,axis=1),rtol=1e-10,atol=1e-12)):
                raise ValueError('SBL selected output/support/h0 binding')
            for label in (v+'/full',)+(('L-cov/joint',) if v=='L-cov' else ()):
                validate_score(r['arms'][label],label.split('/')[1],n,noise)
            returned=r['arms'][v+'/'+p['variants'][v]['pipeline_return_mode']]
            for field in ('decoded_sha256','info_errors','fer','ldpc_iters'):
                if returned[field]!=p['variants'][v][field]: raise ValueError('pipeline returned final-arm mismatch')
        fits=r['sbl_fits']
        if len(fits)!=3 or [d['stage'] for d in fits]!=['stage1','L-diag','L-cov']:
            raise ValueError('SBL fit stage coverage')
        for d,kind in zip(fits,('none','scalar','full')):
            if (d['status']!='ok' or d['Gamma_kind']!=kind or d['max_iter']!=100 or not 1<=d['iterations']<=100
                    or not 1<=d['n_final']<=d['n_start'] or d['jitter_events']<0
                    or not np.isfinite(d['beta']) or d['beta']<=0 or not np.isfinite(d['seconds']) or d['seconds']<0):
                raise ValueError('invalid SBL fit/attempt')
        attempts=r['attempts'];terminal=[x for x in attempts if x['stage']!='round1']
        expected_order=['L-diag/full']+['L-cov/'+m for m in f.cov_order(r)]
        if (len(attempts)!=4 or attempts[0]['stage']!='round1' or any(x['status']!='ok' for x in attempts)
                or [x['stage']+'/'+x['mode'] for x in terminal]!=expected_order
                or any(not np.isfinite(x[k]) or x[k]<0 for x in terminal for k in ('detect_seconds','decode_seconds'))):
            raise ValueError('attempt/arm order/failure retention')
        fp=r['shared_frame_fingerprint'];gen=r['generation']
        if (len(fp)!=4 or fp[0]!=gen['channel_seed'] or gen['scenario']!=r['scenario'] or gen['frame']!=r['frame']
                or gen['coded_sha256']!=r['input_sha256']['coded'] or not np.isfinite(gen['seconds']) or gen['seconds']<0):
            raise ValueError('physical generation/input fingerprint')
    # The frozen P1 stream shares channel seed/gains/message/noise across U/G/SNR.
    for frame in {r['frame'] for r in rows}:
        selected=[r for r in rows if r['frame']==frame]
        if any(r['shared_frame_fingerprint']!=selected[0]['shared_frame_fingerprint'] for r in selected):
            raise ValueError('changed within-frame exogenous randomness')
    return rows


def load(directory):
    paths=[directory/f'rows_shard{i:03d}.jsonl' for i in range(12)]
    configs=[directory/f'config_shard{i:03d}.json' for i in range(12)]
    if set(directory.glob('rows_shard*.jsonl'))!=set(paths) or set(directory.glob('config_shard*.json'))!=set(configs):
        raise ValueError('exact12 raw/config shards required')
    values=[json.loads(p.read_text()) for p in configs]
    identities=[{k:c['_config'][k] for k in IDENTITY} for c in values];identity=identities[0]
    if any(x!=identity for x in identities) or identity['schema']!=f.SCHEMA or identity['frames']!=[f.FRAMES.start,f.FRAMES.stop] or identity['arms']!=list(f.ARMS):
        raise ValueError('mixed source/reference/config identity')
    if (identity['own_md5'].get('gamma_ablation.py')!=hashlib.md5(Path(f.gamma.__file__).read_bytes()).hexdigest()
            or identity['gamma_helper_path']!=str(f.ROOT/'experiments/sbl_freeze_replay_20261020/gamma_ablation.py')):
        raise ValueError('actual Gamma reference helper missing/changed')
    prior_identity=identity['full_reference']['identity']
    if (not re.fullmatch(r'[0-9a-f]{40}',identity['producing_commit'])
            or identity['full_reference']['summary_sha256']!=f.gamma.FULL_SUMMARY_SHA
            or identity['full_reference']['verification_sha256']!=f.gamma.FULL_VERIFICATION_SHA
            or identity['reference']!=prior_identity['reference']
            or identity['source_md5']!=prior_identity['source_md5']
            or identity['frozen_actual_paths']!=prior_identity['frozen_actual_paths']
            or identity['family_P1']!=identity['reference']['three']['source_identity']['family_P1']):
        raise ValueError('frozen reference/source/family/commit drift')
    gate=json.loads((directory/'gate.json').read_text());gate_rows=[json.loads(x) for x in (directory/'gate_attempt.jsonl').read_text().splitlines() if x.strip()]
    if (gate.get('passed') is not True or len(gate_rows)!=1 or a.row_sha(gate_rows[0])!=gate['row_sha256']
            or {k:gate['_config'][k] for k in IDENTITY}!=identity): raise ValueError('successful identical-source gate absent')
    gate_config=json.loads((directory/'config_gate.json').read_text())
    if gate_config!=dict(_argv=gate['_argv'],_config=gate['_config']):
        raise ValueError('gate receipt/config mismatch')
    validate(gate_rows,expected={f.cohort.KEY})
    rows=[];generations=[]
    for shard,(path,cfg) in enumerate(zip(paths,values)):
        if cfg['_config']['shard']!=shard or not 0<cfg['_config']['deadline_seconds']<=690 or not isinstance(cfg['_argv'],list):
            raise ValueError('shard config ownership/deadline/argv')
        selected=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        if any((r['frame']-f.FRAMES.start)%12!=shard for r in selected): raise ValueError('shard key ownership')
        rows.extend(selected);generations.extend(json.loads((directory/f'generations_shard{shard:03d}.json').read_text()))
    validate(rows)
    if len(generations)!=100 or {(g['scenario'],g['frame']) for g in generations}!={(sc,frame) for sc in ('U','G') for frame in f.FRAMES}:
        raise ValueError('100 physical-base generation coverage')
    gm={(g['scenario'],g['frame']):g for g in generations}
    if any(r['generation']!=gm[(r['scenario'],r['frame'])] for r in rows): raise ValueError('generation receipts/rows mismatch')
    gate_generations=json.loads((directory/'generations_gate.json').read_text())
    if gate_generations!=[gate_rows[0]['generation']]: raise ValueError('gate base generation mismatch')
    evidence=paths+configs+[directory/f'generations_shard{i:03d}.json' for i in range(12)]+[directory/name for name in ('gate.json','gate_attempt.jsonl','config_gate.json','generations_gate.json')]
    return rows,{p.name:a.reference.file_sha(p) for p in evidence},identity,gate_rows[0]


def summarize(rows,n_boot=N_BOOT):
    groups={'pooled':rows}|{f'{sc}_{snr}':[r for r in rows if r['scenario']==sc and r['snr_centi_db']==snr] for sc in ('U','G') for snr in (700,800)}
    output={}
    for name,selected in groups.items():
        arms={}
        for label in f.ARMS:
            records=[r['arms'][label] for r in selected]
            elapsed={k:np.array([d[k] for d in records]) for k in ('detect_seconds','decode_seconds')}
            elapsed['combined_seconds']=elapsed['detect_seconds']+elapsed['decode_seconds']
            arms[label]=dict(failures=sum(d['fer'] for d in records),**{f'mean_{k}':float(np.mean([d[k] for d in records])) for k in METRICS},
                timing={k:a.timing(v) for k,v in elapsed.items()})
        columns=[[r['arms'][label][metric]-r['arms'][f.CONTROL][metric] for r in selected] for label in f.ARMS[:2] for metric in METRICS]
        effects=a.trajectory.paired(np.column_stack(columns),[r['frame'] for r in selected],frames=list(f.FRAMES),n_boot=n_boot,seed=SEED)
        contrasts={}
        for i,label in enumerate(f.ARMS[:2]):
            effect={k:effects[i*len(METRICS)+j] for j,k in enumerate(METRICS)}
            lo,hi=effect['extrinsic_bit_logloss']['ci95'];harm=effect['fer']['ci95'][0]>0
            verdict='favorable' if hi<0 else ('reversal' if lo>0 else 'inconclusive')
            ref=arms[f.CONTROL]['mean_extrinsic_bit_logloss']
            contrasts[label]=dict(delta=label+' minus '+f.CONTROL,effects=effect,primary_logloss_verdict=verdict,
                detected_FER_harm=harm,interpretation='detected FER harm; blocks practical pass' if harm else 'FER remains unresolved; no equivalence/noninferiority',
                relative_logloss_change=effect['extrinsic_bit_logloss']['point']/ref if ref>0 else None,
                transitions={f'{x}->{y}':sum(r['arms'][f.CONTROL]['fer']==x and r['arms'][label]['fer']==y for r in selected) for x in (0,1) for y in (0,1)})
        upstream={v:dict(mean_atoms=float(np.mean([len(r['upstream'][v]['h0']) for r in selected])),
            converged=sum(r['pipeline']['variants'][v]['sbl']['converged'] for r in selected),
            jitter_events=sum(r['pipeline']['variants'][v]['sbl']['jitter_events'] for r in selected),
            mean_sbl_seconds=float(np.mean([r['pipeline']['variants'][v]['seconds']['sbl'] for r in selected]))) for v in f.V}
        output[name]=dict(n=len(selected),arms=arms,contrasts=contrasts,upstream=upstream,
            pipeline_seconds={k:a.timing([r['pipeline']['seconds'][k] for r in selected]) for k in selected[0]['pipeline']['seconds']})
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    rows,hashes,identity,gate=load(args.out)
    report=dict(label='Prospective fresh P1 frames; pointwise score validation, no unique mechanism or deployment acceptance',_argv=sys.argv[1:],
        bootstrap=dict(seed=SEED,resamples=N_BOOT,cluster='50 shared P1 frames, all4cells/all3arms jointly'),n_keys=len(rows),source_identity=identity,
        raw_sha256=hashes,groups=summarize(rows),main_calls={k:sum(r[k+'_calls'] for r in rows) for k in ('sbl','receiver','decoder')},
        gate_calls={k:gate[k+'_calls'] for k in ('sbl','receiver','decoder')},base_generations=dict(main=100,gate=1),timing_scope=identity['timing_scope'])
    with (args.out/'summary.json').open('x') as handle: handle.write(json.dumps(report,allow_nan=False,indent=1)+'\n')
    print('validated200 fresh keys:600 SBL,800/800 receiver/decoder; old gate3 SBL,4/4')


if __name__=='__main__':main()
