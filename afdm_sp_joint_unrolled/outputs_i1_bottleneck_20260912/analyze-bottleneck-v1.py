"""Read-only raw audit and paired pilot inference; zero receiver/detector calls."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.stats import beta, binomtest

from afdm_sp_joint_unrolled.bottleneck_pilot import (FULL_ARMS, TERMINAL_ARMS, hashes, load_state,
                                                    observed_at_snr, terminal_inputs)
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash

CONTRASTS = [('I1','I1_DET_ONLY'), ('I1','I1_CE_ONLY'), ('I1','I1_ZERO'),
             ('I1','BP_EST_NOISE'), ('I1','BP_TRUE_BASE'),
             ('BP_EST_NOISE','BP_TRUE_NOISE'), ('BP_EST_NOISE','EP_EST_NOISE'),
             ('BP_TRUE_NOISE','EP_TRUE_NOISE'), ('BP_TRUE_BASE','BP_TRUE_NOISE')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def cp(successes, n, tail):
    if not 0<=successes<=n or n<1 or not 0<tail<.5:
        raise ValueError('invalid binomial interval inputs')
    return [0. if successes==0 else float(beta.ppf(tail, successes, n-successes+1)),
            1. if successes==n else float(beta.ppf(1-tail, successes+1, n-successes))]


def paired(a, b, alpha=.05):
    a, b = np.asarray(a), np.asarray(b)
    if (a.ndim!=1 or a.shape!=b.shape or not a.size
            or not np.isin(a,(0,1)).all() or not np.isin(b,(0,1)).all()):
        raise ValueError('paired binary error vectors with identical nonzero size required')
    n = len(a)
    wins = int(np.count_nonzero((a==1)&(b==0)))
    losses = int(np.count_nonzero((a==0)&(b==1)))
    win_ci, loss_ci = cp(wins, n, alpha/4), cp(losses, n, alpha/4)
    return dict(n=n, baseline_errors=int(a.sum()), candidate_errors=int(b.sum()),
                wins=wins, losses=losses, both_wrong=int(np.count_nonzero((a==1)&(b==1))),
                delta=(wins-losses)/n,
                CI=[win_ci[0]-loss_ci[1], win_ci[1]-loss_ci[0]],
                alpha=alpha, interval='union-bound difference of two Clopper-Pearson intervals',
                mcnemar_p=float(binomtest(wins,wins+losses,.5).pvalue) if wins+losses else 1.)


def holm(values):
    values = np.asarray(values, dtype=float)
    if values.ndim!=1 or not np.isfinite(values).all() or np.any((values<0)|(values>1)):
        raise ValueError('finite p values within [0,1] required')
    result = np.empty(len(values))
    running = 0.
    for rank, index in enumerate(np.argsort(values, kind='stable')):
        running = max(running, min(1., (len(values)-rank)*values[index]))
        result[index] = running
    return result.tolist()


def independently_score(value, raw, H):
    """Do not reuse the collector's score_errors or offline_scores implementation."""
    if (np.asarray(value['info_hat']).shape!=raw['info'].shape
            or np.asarray(value['decoded']).shape!=raw['coded'].shape
            or any(not np.isin(value[key],(0,1)).all() for key in ('info_hat','decoded'))):
        raise ValueError('decoded bit shape or binary convention differs')
    info_errors = int(np.sum(np.asarray(value['info_hat'])!=raw['info']))
    decoded_errors = int(np.sum(np.asarray(value['decoded'])!=raw['coded']))
    hard = np.asarray(value['x_hard'])
    raw_bits = np.r_[hard.real<0, hard.imag<0]
    llr = np.asarray(value['llr'])
    coded = raw['coded'].astype(float)
    if llr.shape!=coded.shape or not np.isfinite(llr).all():
        raise ValueError('raw scoring LLR mismatch')
    margin = llr*(1.-2.*coded)
    high = np.abs(llr)>=5
    return dict(FER=int(info_errors!=0), coded_bit_errors=info_errors,
        raw_bit_errors=int(np.sum(raw_bits!=coded)), decoded_codeword_bit_errors=decoded_errors,
        raw_bits_denominator=len(coded), coded_bits_denominator=len(raw['info']),
        bit_NLL=float(np.logaddexp(0.,-margin).mean()),
        bit_Brier=float(np.mean((1./(1.+np.exp(llr))-coded)**2)),
        high_confidence_bits=int(high.sum()), high_confidence_wrong=int(np.sum(high & (margin<0))),
        channel_NMSE=float(np.vdot(H-raw['H'],H-raw['H']).real /
                           np.vdot(raw['H'],raw['H']).real), decode_ok=bool(value['decode_ok']))


def check_score(recorded, actual):
    for key, value in actual.items():
        if isinstance(value, float):
            if not np.isclose(recorded[key], value, rtol=1e-10, atol=1e-12):
                raise ValueError('independent score differs: '+key)
        elif recorded[key]!=value:
            raise ValueError('independent score differs: '+key)


def verify_source(root, label, summary):
    source = root/('source-'+label)
    manifest = read(source/'source-manifest.json')
    if sha(source/'source-manifest.json')!=summary['source_manifest_sha256']:
        raise ValueError('summary source identity differs')
    package = source/'afdm_sp_joint_unrolled'
    actual = {str(p.relative_to(package)):sha(p) for p in package.rglob('*.py')}
    if actual!=manifest:
        raise ValueError('executed snapshot source changed')


def audit_stage(root, stage):
    directory = root/'runs'/stage
    summary = read(directory/'summary.json')
    contract = read(root/'inputs/contract.json')
    if (summary['status']!='COMPLETE' or summary['stage']!=stage
            or summary['contract_sha256']!=sha(root/'inputs/contract.json')
            or summary['calls']!={key:contract['bounds'][stage][key] for key in ('F','T')}):
        raise ValueError('completed stage contract/count mismatch')
    if (directory/'failure.json').exists():
        raise ValueError('failed stage cannot be promoted as completed evidence')
    verify_source(root, 'golden' if stage=='golden' else 'current', summary)
    reservations = {p.stem.replace('-reserve',''):read(p) for p in directory.glob('*-reserve.json')}
    if len(reservations)!=sum(summary['calls'].values()):
        raise ValueError('reservation ledger count differs')
    expected_blocks = 64 if stage=='development' else 2
    split = 2 if stage=='development' else 1
    if len(summary['exogenous'])!=expected_blocks:
        raise ValueError('missing independent blocks')
    files, arrays_read, rows, identities, inputs_by_block = {}, 0, [], set(), {}
    def checked_load(artifact):
        nonlocal arrays_read
        path = Path(artifact['file']['path'])
        if not path.is_relative_to(directory):
            raise ValueError('raw file outside its stage')
        value = load_state(artifact)
        arrays_read += len(artifact['file']['fields'])
        files[str(path)] = dict(sha256=artifact['file']['sha256'], bytes=path.stat().st_size,
                                arrays=len(artifact['file']['fields']))
        return value
    listed_records = {Path(row['record']):row for row in summary['records']}
    if set(listed_records)!=set(directory.glob('*-result.json')):
        raise ValueError('result inventory differs from summary')
    for block in range(expected_blocks):
        exo = summary['exogenous'][block]
        if exo['block']!=block or exo['split']!=split:
            raise ValueError('exogenous identity mismatch')
        raw = checked_load(exo['state'])
        expected_hashes = hashes({key:raw[key] for key in ('H','info','coded','data','pilot','noise')})
        if exo['hashes']!=expected_hashes:
            raise ValueError('exogenous content hash mismatch')
        inputs_by_block[str(block)] = expected_hashes
        for snr in (7,8):
            obs_manifest = read(directory/f'observed-{block:03d}-{snr}.json')
            observed = checked_load(obs_manifest['state'])
            if obs_manifest['exogenous_hashes']!=expected_hashes:
                raise ValueError('cross-SNR exogenous pairing mismatch')
            # Recompute the deterministic observation algebra, not a receiver call.
            if hashes(observed)!=hashes(observed_at_snr(raw,snr)):
                raise ValueError('SNR observation is not the declared shared exogenous block')
            cohort = [p for p,row in listed_records.items() if row['block']==block and row['snr']==snr]
            expected_arms = ['I1'] if stage=='golden' else list(FULL_ARMS)+list(TERMINAL_ARMS)
            if stage=='engineering':
                expected_arms += ['I1_REPEAT','EP_EST_NOISE_DOUBLE','EP_TRUE_NOISE_DOUBLE']
            if sorted(listed_records[p]['arm'] for p in cohort)!=sorted(expected_arms):
                raise ValueError('missing, duplicate or unknown scheduled arm')
            records = {listed_records[p]['arm']:(p,read(p)) for p in cohort}
            # Load the I1 state once, then all remaining independent raw outputs.
            i1 = checked_load(records['I1'][1]['state'])
            for arm in expected_arms:
                path, record = records[arm]
                listing = listed_records[path]
                if sha(path)!=listing['sha256'] or record['scores']!=listing['scores']:
                    raise ValueError('summary/result content differs')
                if (record['block'],record['snr'],record['split'],record['arm'])!=(block,snr,split,arm):
                    raise ValueError('result identity changed')
                if record['token'] not in reservations:
                    raise ValueError('unreserved scientific call')
                reserved = reservations[record['token']]
                if any(reserved[key]!=record[key] for key in ('kind','block','snr','split','arm')):
                    raise ValueError('reservation and result identity differ')
                if record['token'] in identities:
                    raise ValueError('duplicate scientific call')
                identities.add(record['token'])
                if record['observed_hashes']!=hashes(observed) or not record['input_unchanged'] or not record['rng_unchanged']:
                    raise ValueError('shared observation or RNG neutrality failure')
                value = i1 if arm=='I1' else checked_load(record['state'])
                if record['kind']=='F':
                    H = value['H']
                    if record['truth_access']!='offline scoring only':
                        raise ValueError('full receiver truth boundary changed')
                    decoder = [row for row in value['code_feedback_records'] if row['stage']=='decoder']
                    if len(decoder)!=1 or decoder[0]['iteration']!=1:
                        raise ValueError('full arm decoder schedule mismatch')
                    outer = value['bp_schedule']['calls']
                    if len(outer)!=10 or any(row['requested_iterations']!=12 for row in outer):
                        raise ValueError('full arm outer BP schedule mismatch')
                else:
                    canonical = arm.removesuffix('_DOUBLE')
                    z,H,sigma = terminal_inputs(observed,i1['H'],raw['H'],i1['sigma2_terminal'],canonical)
                    if not arm.endswith('_DOUBLE'):
                        expected = hashes(dict(z=z,H=H,sigma=np.asarray(sigma),constellation=observed['constellation']))
                        if record['terminal_input_hashes']!=expected:
                            raise ValueError('terminal H/cancellation/variance factor mismatch')
                    if arm.startswith('EP'):
                        diag = value['diagnostics']
                        if diag['input_hashes']['H']!=array_hash(H) or diag['sigma_complex']!=sigma:
                            raise ValueError('EP consumed a different channel/variance')
                score = independently_score(value, raw, H)
                check_score(record['scores'],score)
                row = dict(block=block,snr=snr,arm=arm,kind=record['kind'],**score,
                           seconds=record['seconds'],CPU_seconds=record['CPU_seconds'],record=str(path))
                if record['kind']=='F':
                    row['sigma_to_noise'] = value['sigma2_terminal']/float(observed['sigma2'])
                if arm.startswith('EP'):
                    row.update(ep_converged=value['diagnostics']['converged'],
                               ep_fixed_point=value['diagnostics']['fixed_point_residual'])
                rows.append(row)
    if identities!=set(reservations):
        raise ValueError('uncompleted reservations remain')
    code_files = list((directory/'code-cache').glob('*.npz'))
    if len(code_files)!=1:
        raise ValueError('LDPC cache inventory mismatch')
    with np.load(code_files[0],allow_pickle=False) as code:
        for key in code.files:
            value=code[key]
            if value.dtype.hasobject or not np.isfinite(value).all():
                raise ValueError('invalid cached code array')
            arrays_read += 1
        env=read(directory/'environment.json')
        for key in ('G','H','free_cols'):
            if array_hash(code[key])!=env['code_identity'][key]:
                raise ValueError('actual decoder code identity differs')
    files[str(code_files[0])] = dict(sha256=sha(code_files[0]),bytes=code_files[0].stat().st_size,
                                    arrays=len(code.files))
    if set(files)!={str(p) for p in directory.rglob('*.npz')}:
        raise ValueError('unaccounted raw arrays or missing artifacts')
    return dict(stage=stage,status='PASS',calls=summary['calls'],rows=rows,
                independent_blocks=expected_blocks,observations=2*expected_blocks,
                raw_files=files,arrays_read=arrays_read,inputs_by_block=inputs_by_block,
                code_identity=env['code_identity'],wall_seconds=summary['wall_seconds'],
                peak_cuda_allocated_bytes=summary['peak_cuda_allocated_bytes'])


def inference(rows):
    table, contrasts, interactions = [], [], []
    for snr in (7,8):
        vectors = {}
        for arm in (*FULL_ARMS,*TERMINAL_ARMS):
            selected = sorted((row for row in rows if row['snr']==snr and row['arm']==arm),
                              key=lambda row:row['block'])
            if [row['block'] for row in selected]!=list(range(64)):
                raise ValueError('inference lacks the complete predeclared block cohort')
            vector = np.array([row['FER'] for row in selected], dtype=int)
            vectors[arm] = vector
            info_errors = sum(row['coded_bit_errors'] for row in selected)
            info_bits = sum(row['coded_bits_denominator'] for row in selected)
            raw_errors = sum(row['raw_bit_errors'] for row in selected)
            raw_bits = sum(row['raw_bits_denominator'] for row in selected)
            entry = dict(snr=snr,arm=arm,n=64,errors=int(vector.sum()),FER=float(vector.mean()),
                FER_CI95=cp(int(vector.sum()),64,.025),info_bit_errors=info_errors,info_bits=info_bits,
                info_BER=info_errors/info_bits,raw_bit_errors=raw_errors,raw_bits=raw_bits,
                raw_BER=raw_errors/raw_bits,mean_seconds=float(np.mean([r['seconds'] for r in selected])),
                p95_seconds=float(np.quantile([r['seconds'] for r in selected],.95)),
                mean_bit_NLL=float(np.mean([r['bit_NLL'] for r in selected])),
                mean_bit_Brier=float(np.mean([r['bit_Brier'] for r in selected])),
                mean_H_NMSE=float(np.mean([r['channel_NMSE'] for r in selected])),
                high_confidence_bits=sum(r['high_confidence_bits'] for r in selected),
                high_confidence_wrong=sum(r['high_confidence_wrong'] for r in selected))
            if arm in FULL_ARMS:
                entry['mean_sigma_to_noise'] = float(np.mean([r['sigma_to_noise'] for r in selected]))
            if arm.startswith('EP'):
                entry['converged_frames'] = sum(r['ep_converged'] for r in selected)
                entry['fixed_point_residual_median'] = float(np.median([r['ep_fixed_point'] for r in selected]))
            table.append(entry)
        for baseline, candidate in CONTRASTS:
            result = paired(vectors[baseline],vectors[candidate])
            result['family_CI95'] = paired(vectors[baseline],vectors[candidate],.05/18)['CI']
            contrasts.append(dict(snr=snr,baseline=baseline,candidate=candidate,**result))
        # Paired resampling by whole block; SNRs are never pooled as independent channels.
        delta = ((vectors['BP_EST_NOISE']-vectors['EP_EST_NOISE'])-
                 (vectors['BP_TRUE_NOISE']-vectors['EP_TRUE_NOISE']))
        rng = np.random.default_rng(np.random.SeedSequence([20260912,112500,731921,3]))
        boot = delta[rng.integers(0,64,size=(10000,64))].mean(axis=1)
        interactions.append(dict(snr=snr,estimand='(BP_EST-EP_EST)-(BP_TRUE-EP_TRUE)',
            value=float(delta.mean()),bootstrap_CI95=np.quantile(boot,[.025,.975]).tolist(),
            resamples=10000,independent_blocks=64,descriptive_only=True))
    adjusted = holm([row['mcnemar_p'] for row in contrasts])
    for row, p in zip(contrasts,adjusted):
        row['mcnemar_p_Holm18'] = p
    return dict(tables=table,contrasts=contrasts,interactions=interactions,
                independent_blocks=64,observations=128,
                scope='fixed development pilot, per-SNR inference; no confirmation or global ceiling claim')


def execute(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('analysis evidence is immutable: '+str(output))
    started = time.time()
    completion = read(root/'evidence/pipeline-complete-v2.json')
    if completion['status']!='COMPLETE':
        raise ValueError('collection not complete')
    stages = [audit_stage(root,stage) for stage in ('golden','engineering','development')]
    if stages[0]['inputs_by_block']!=stages[1]['inputs_by_block']:
        raise ValueError('old/new engineering blocks differ')
    if not all(stage['code_identity']==stages[0]['code_identity'] for stage in stages):
        raise ValueError('decoder contents changed across stages')
    counts = {kind:sum(stage['calls'][kind] for stage in stages) for kind in ('F','T')}
    if counts!={'F':536,'T':668}:
        raise ValueError('campaign call budget/accounting differs')
    contract = read(root/'inputs/contract.json')
    bytes_used = sum(p.stat().st_size for p in (root/'runs').rglob('*') if p.is_file())
    if bytes_used>contract['total_bounds']['output_bytes'] or completion['execution_wall_seconds']>7200:
        raise ValueError('storage or execution budget exceeded')
    result = inference(stages[-1]['rows'])
    raw_files = {name:info for stage in stages for name,info in stage['raw_files'].items()}
    result.update(schema='i1-bottleneck-analysis-v1',status='PASS',new_receiver_calls=0,
        source_script_sha256=sha(__file__),contract_sha256=sha(root/'inputs/contract.json'),
        audit_seconds=time.time()-started,calls_audited=counts,bytes_used=bytes_used,
        execution_wall_seconds=completion['execution_wall_seconds'],
        raw_files_audited=len(raw_files),arrays_read=sum(stage['arrays_read'] for stage in stages),
        stage_audits=[{key:value for key,value in stage.items() if key not in ('rows','raw_files','inputs_by_block')}
                      for stage in stages],
        engineering_admission=read(root/'evidence/engineering-admission.json'),
        historical_failures_preserved=['pipeline-failure.json','cpu-golden-test-probe.json'],
        limitations=['64 independent development blocks; 8dB may have few errors',
                     'true H replaces terminal H and cancellation, not full-loop state',
                     'fixed EP40 failed engineering stability qualification; no BP optimality inference',
                     'direct feedback masks retain mediated effects through subsequent detection/CE',
                     'runtime diagnostic is not a repeated formal COST02 benchmark'])
    output.mkdir()
    (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
    (output/'raw-manifest.json').write_text(json.dumps(raw_files,indent=2)+'\n')
    rows = stages[-1]['rows']
    columns = sorted({key for row in rows for key in row})
    with (output/'paired-rows.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,columns,lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(dict(status='PASS',raw_files=len(raw_files),arrays=result['arrays_read'],
                          F=counts['F'],T=counts['T'],audit_seconds=result['audit_seconds'])))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    execute(args.root,args.output)


if __name__=='__main__':
    main()
