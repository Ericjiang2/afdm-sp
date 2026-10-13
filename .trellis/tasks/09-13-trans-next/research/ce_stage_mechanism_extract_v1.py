"""SYN-02 read-only O2 accounting and old FULL error-index description.

Reads frozen saved records only. No receiver, CE, BP, LDPC, interleaver, or new F.
Adjacent lag-1 and cross-SNR overlap are post-hoc descriptions, not PRED endpoints.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

MAP=('map','tail','noise')
OLD_TERMS=MAP+('feedback',)
LAG=1
MAX_BYTES=20*1024**3
MAX_SECONDS=7200


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):return np.isfinite(np.asarray(value)).all()


def proc_kib(name,path):
    for line in Path(path).read_text().splitlines():
        if line.startswith(name+':'):return int(line.split()[1])*1024
    raise ValueError('Linux resource field missing: '+name)


def resources(contract):
    available=proc_kib('MemAvailable','/proc/meminfo')
    peak=contract['conservative_peak_bytes']
    require(available>=2*peak and peak<=MAX_BYTES,
            'offline 4GiB conservative peak requires at least 8GiB available')
    return dict(MemAvailable_bytes=available,conservative_peak_bytes=peak)


def budget(started,out):
    require(time.monotonic()-started<MAX_SECONDS,'offline analysis exceeds 2h wall cap')
    require(proc_kib('VmHWM','/proc/self/status')<=MAX_BYTES,
            'offline analysis exceeds 20GiB peak RSS')
    cache=Path(os.environ.get('TMPDIR',out))
    new_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if cache.exists() and not cache.is_relative_to(out):
        new_bytes+=sum(p.stat().st_size for p in cache.rglob('*') if p.is_file())
    require(new_bytes<=MAX_BYTES,
            'offline analysis exceeds 20GiB new disk')


def guard(contract,args):
    require(sha(args.contract)==args.contract_sha256
        and sha(Path(__file__))==args.script_sha256,
        'frozen script/config SHA differs')
    require(contract.get('schema')=='ce-stage-mechanism-contract-v1'
        and contract.get('status')=='frozen_after_local_tests'
        and contract.get('blocks')==32 and contract.get('snrs')==[7,8]
        and contract.get('O2_analysis_states')==contract.get('O2_CE_states')==64
        and contract.get('old_FULL_states')==64
        and contract.get('error_index_lags')==[LAG]
        and contract.get('error_domains')==['info','coded']
        and contract.get('index_boundary')=='linear_no_wrap'
        and contract.get('threads')==1
        and contract.get('wall_seconds_cap')==MAX_SECONDS
        and contract.get('new_disk_bytes_cap')==MAX_BYTES
        and (contract.get('new_F'),contract.get('new_CE'),contract.get('new_BP'),
             contract.get('new_LDPC'))==(0,0,0,0),
        'frozen offline field/budget scope differs')
    old=Path(contract['old_root']).resolve();ce=Path(contract['ce_root']).resolve()
    require(old==Path(args.old_root).resolve() and ce==Path(args.ce_root).resolve(),
            'analysis data roots differ from frozen config')
    manifest=ce/contract['analysis_source']/'source-manifest.json'
    require(sha(manifest)==contract['analysis_source_manifest_sha256'],
            'analysis source-v4 manifest SHA differs')
    package=manifest.parent/'afdm_sp_joint_unrolled'
    inventory=json.loads(manifest.read_text())
    require(set(inventory)=={str(p.relative_to(package)) for p in package.rglob('*.py')},
            'analysis source-v4 Python inventory differs')
    for name,digest in inventory.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and sha(package/name)==digest,'analysis source file differs: '+name)
    for name,digest in contract['old_inputs'].items():
        path=old/name
        require(path.is_relative_to(old) and sha(path)==digest,
                'original saved summary/audit SHA differs: '+name)
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS'):
        require(os.environ.get(name)=='1','single-thread environment required: '+name)
    sys.path.insert(0,str(manifest.parent))
    import afdm_sp_joint_unrolled as loaded
    require(Path(loaded.__file__).resolve().parent==package.resolve(),
            'imported package not bound source-v4')
    return old,ce,dict(contract_sha256=args.contract_sha256,
        script_sha256=args.script_sha256,manifest_sha256=sha(manifest),
        original_input_sha256=contract['old_inputs'])


def source_index(old,contract):
    gname='runs/g1-strong-development-recovery-v1/development/summary.json'
    oname='runs/ce-oracle-fixed-ce-v1/analysis/summary.json'
    g=json.loads((old/gname).read_text());o=json.loads((old/oname).read_text())
    ga=json.loads((old/'evidence/g1-strong-development-recovery-v1-raw-audit.json').read_text())
    oa=json.loads((old/'evidence/ce-oracle-fixed-ce-v1-raw-audit.json').read_text())
    require(g['status']==o['status']=='COMPLETE' and ga['status']==oa['status']=='PASS'
        and ga['summary_sha256']==sha(old/gname) and oa['summary_sha256']==sha(old/oname)
        and len(g['records'])==288 and len(o['records'])==128
        and o['calls']=={'A':64,'E':64}
        and oa['saved_records']==128 and oa['new_CE']==64,
        'old G1/O2 run or original raw audit incomplete')
    gi={(e['kind'],e['block'],e['snr'],e['arm']):e for e in g['records']}
    oi={(e['kind'],e['block'],e['snr'],e['arm']):e for e in o['records']}
    require(len(gi)==288 and len(oi)==128
        and {(e['block'],e['snr']) for e in o['records'] if e['kind']=='E'}
             =={(b,s) for b in range(32) for s in (7,8)}
        and {(e['block'],e['snr']) for e in g['records'] if e['kind']=='F'
             and e['arm']=='G1_FULL'}=={(b,s) for b in range(32) for s in (7,8)},
        'original G1/O2 paired work-point inventory differs')
    return gi,oi,g,o


def accounting(value,terms):
    required={f'{a}:{b}' for i,a in enumerate(terms) for b in terms[i+1:]}
    require(set(value['terms'])==set(terms) and set(value['squared'])==set(terms)
        and set(value['cross'])==required and all(finite(value['terms'][k])
            for k in terms),'O2 actual-S saved term inventory differs')
    squared={k:float(value['squared'][k]) for k in terms}
    cross={k:float(v) for k,v in value['cross'].items()}
    for k in terms:
        vector=np.asarray(value['terms'][k]);direct=float(np.vdot(vector,vector).real)
        require(abs(direct-squared[k])<=1e-8*max(1.,direct),
                'O2 saved squared vector differs: '+k)
    for k in required:
        a,b=k.split(':');direct=2*float(np.vdot(value['terms'][a],value['terms'][b]).real)
        require(abs(direct-cross[k])<=1e-8*max(1.,abs(direct)),
                'O2 saved real cross differs: '+k)
    affine=float(value['affine_error'])
    require(abs(sum(squared.values())+sum(cross.values())-affine)
            <=2e-9*max(1.,affine) and value['closure_relative']<=2e-5
            and value['dtype_rounding_relative']<=2e-5,
            'O2 saved affine equation or dtype closure differs')
    return dict(squared=squared,cross=cross,affine_error=affine,
        actual_error=float(value['actual_error']),
        closure_relative=float(value['closure_relative']),
        dtype_rounding_relative=float(value['dtype_rounding_relative']))


def schur_record(value):
    s=np.asarray(value['schur'],dtype=np.float64)
    require(s.ndim==1 and len(s)>0 and finite(s) and np.min(s)>=-1e-8,
            'O2 saved Schur candidate array differs')
    return dict(candidate_count=len(s),minimum=float(np.min(s)),
                mean=float(np.mean(s)),maximum=float(np.max(s)))


def o2_rows(old,gi,oi,started,out):
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    rows=[]
    for b in range(32):
        for snr in (7,8):
            budget(started,out)
            ae=oi['A',b,snr,'TRUE_DATA_FIXED_S_CE']
            ee=oi['E',b,snr,'TRUE_DATA_FIXED_S_CE']
            ar,av=verified_record(ae,old);er,ev=verified_record(ee,old)
            require(er['analysis_record_sha256']==ar['state']['file']['sha256']
                and ev['reference_record_sha256']==gi['F',b,snr,'G1_FULL']['sha256']
                and ev['physical_record_sha256']==gi['A',b,7,'G1_PROPAGATION']['sha256']
                and av['resource_counts']['new_CE']==0 and ev['resource_counts']['new_CE']==1,
                'O2 A/E and original FULL/A parent linkage differs')
            before=accounting(ev['ordinary'],OLD_TERMS)
            after=accounting(ev['oracle'],MAP)
            require(abs(before['actual_error']-av['ordinary']['actual_error'])<=1e-12
                and before['actual_error']>=0 and after['actual_error']>=0,
                'O2 saved pre/post actual coefficient risk differs')
            Q=np.asarray(ev['Q_plugin_mean_unused'])
            consumed=np.asarray(ev['Q_true_data_consumed'])
            require(Q.shape==(24,24) and consumed.shape==Q.shape and finite(Q)
                and np.array_equal(consumed,np.zeros_like(consumed)),
                'O2 diagnostic Q or mean-mode consumed variance differs')
            hist=ev['coefficient_histogram'];support=len(ev['support_ids'])
            require(support==24 and all(int(np.asarray(hist[k]).sum())==support
                for k in ('true','old_error','oracle_error')),
                'O2 saved coefficient histogram misses actual-S atoms')
            rows.append(dict(block=b,snr=snr,ordinary=before,oracle=after,
                actual_after_minus_before=after['actual_error']-before['actual_error'],
                Q_plugin_trace=float(np.trace(Q).real),Q_consumed_frobenius=0.,
                schur_old=schur_record(ev['schur_old']),
                schur_new=schur_record(ev['schur_new']),
                histogram_bin_edges=np.asarray(hist['bin_edges']).tolist(),
                histogram_true=np.asarray(hist['true']).tolist(),
                histogram_old_error=np.asarray(hist['old_error']).tolist(),
                histogram_oracle_error=np.asarray(hist['oracle_error']).tolist(),
                support_size=support,
                analysis_record_sha256=ae['sha256'],
                analysis_state_npz_sha256=ar['state']['file']['sha256'],
                CE_record_sha256=ee['sha256'],
                reference_FULL_record_sha256=ev['reference_record_sha256'],
                physical_A_record_sha256=ev['physical_record_sha256']))
    require(len(rows)==64,'O2 64 actual-S analysis rows required')
    return rows


def adjacent(error):
    e=np.asarray(error,dtype=bool)
    require(e.ndim==1 and len(e)>LAG and finite(e),
            'finite saved terminal bit-error vector required')
    left=e[:-LAG].astype(float);right=e[LAG:].astype(float)
    both=float(np.mean(left*right));p_left=float(left.mean());p_right=float(right.mean())
    covariance=both-p_left*p_right
    scale=np.sqrt(p_left*(1-p_left)*p_right*(1-p_right))
    return dict(bits=len(e),errors=int(e.sum()),adjacent_pairs=len(left),
        adjacent_joint_error_fraction=both,adjacent_error_covariance=covariance,
        adjacent_phi_correlation=None if scale==0 else float(covariance/scale))


def overlap(a,b):
    a=np.asarray(a,dtype=bool);b=np.asarray(b,dtype=bool)
    require(a.shape==b.shape,'paired 7/8dB terminal bit order differs')
    both=int(np.count_nonzero(a&b));either=int(np.count_nonzero(a|b))
    return dict(both_error_positions=both,either_error_positions=either,
        jaccard=None if either==0 else both/either)


def legacy_rows(old,gi,started,out):
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    rows=[];paired=[]
    for b in range(32):
        budget(started,out)
        pe=gi['A',b,7,'G1_PROPAGATION']
        pr,physical=verified_record(pe,old)
        raw=physical['raw']
        truth={k:np.asarray(raw[k]) for k in ('info','coded')}
        require(truth['info'].shape==(1024,) and truth['coded'].shape==(2048,)
            and all(np.isin(v,(0,1)).all() for v in truth.values()),
            'original coded/info truth or code size differs')
        by_snr={}
        for snr in (7,8):
            fe=gi['F',b,snr,'G1_FULL']
            fr,full=verified_record(fe,old)
            require(full['info_hat'].shape==truth['info'].shape
                and full['decoded'].shape==truth['coded'].shape
                and np.isin(full['info_hat'],(0,1)).all()
                and np.isin(full['decoded'],(0,1)).all(),
                'old FULL decoded/info arrays differ from original code truth')
            err={k:np.asarray(full['info_hat' if k=='info' else 'decoded'])!=truth[k]
                 for k in truth}
            require(int(err['info'].sum())==fe['scores']['coded_bit_errors']
                and int(err['coded'].sum())==fe['scores']['decoded_codeword_bit_errors']
                and int(err['info'].any())==fe['scores']['FER'],
                'old FULL saved bit positions differ from original FER counts')
            by_snr[snr]=err
            rows.append(dict(block=b,snr=snr,
                info=adjacent(err['info']),coded=adjacent(err['coded']),
                FULL_record_sha256=fe['sha256'],FULL_state_npz_sha256=fr['state']['file']['sha256'],
                physical_A_record_sha256=pe['sha256'],
                physical_A_state_npz_sha256=pr['state']['file']['sha256']))
        paired.append(dict(block=b,info=overlap(by_snr[7]['info'],by_snr[8]['info']),
            coded=overlap(by_snr[7]['coded'],by_snr[8]['coded'])))
    require(len(rows)==64 and len(paired)==32,
            'old FULL paired bit-error position inventory differs')
    return rows,paired


def mean(values):
    arr=np.asarray(values,dtype=float)
    require(len(arr)>0 and np.isfinite(arr).all(),'finite offline aggregate required')
    return float(arr.mean())


def aggregate_o2(rows):
    groups=[]
    for snr in (7,8):
        subset=[r for r in rows if r['snr']==snr]
        require(len(subset)==32,'32 physical O2 work points per SNR required')
        terms={}
        for phase in ('ordinary','oracle'):
            names=OLD_TERMS if phase=='ordinary' else MAP
            terms[phase]=dict(squared_mean={k:mean([r[phase]['squared'][k]
                for r in subset]) for k in names},cross_mean={k:mean([r[phase]['cross'][k]
                for r in subset]) for k in subset[0][phase]['cross']},
                affine_error_mean=mean([r[phase]['affine_error'] for r in subset]),
                actual_error_mean=mean([r[phase]['actual_error'] for r in subset]))
        require(all(r['histogram_bin_edges']==subset[0]['histogram_bin_edges']
            for r in subset),'O2 coefficient histogram bin identity differs')
        groups.append(dict(snr=snr,channels=32,terms=terms,
            actual_error_after_minus_before_mean=mean([r['actual_after_minus_before']
                for r in subset]),
            Q_plugin_trace_mean_unused=mean([r['Q_plugin_trace'] for r in subset]),
            Q_consumed_frobenius_max=0.,
            schur_old_min=min(r['schur_old']['minimum'] for r in subset),
            schur_new_min=min(r['schur_new']['minimum'] for r in subset),
            schur_old_candidate_mean=mean([r['schur_old']['mean'] for r in subset]),
            schur_new_candidate_mean=mean([r['schur_new']['mean'] for r in subset]),
            histogram_bin_edges=subset[0]['histogram_bin_edges'],
            histogram_counts={k:[sum(r['histogram_'+k][i] for r in subset)
                for i in range(len(subset[0]['histogram_'+k]))]
                for k in ('true','old_error','oracle_error')}))
    return groups


def aggregate_legacy(rows,paired):
    groups=[]
    for snr in (7,8):
        subset=[r for r in rows if r['snr']==snr]
        require(len(subset)==32,'32 old FULL terminal states per SNR required')
        domains={}
        for domain in ('info','coded'):
            profiles=[r[domain] for r in subset]
            defined=[p['adjacent_phi_correlation'] for p in profiles
                     if p['adjacent_phi_correlation'] is not None]
            domains[domain]=dict(total_errors=sum(p['errors'] for p in profiles),
                mean_adjacent_joint_error_fraction=mean([p['adjacent_joint_error_fraction']
                    for p in profiles]),
                mean_adjacent_error_covariance=mean([p['adjacent_error_covariance']
                    for p in profiles]),phi_defined_channels=len(defined),
                mean_phi_when_defined=None if not defined else mean(defined))
        groups.append(dict(snr=snr,channels=32,domains=domains))
    overlaps={}
    for domain in ('info','coded'):
        values=[r[domain] for r in paired]
        defined=[v['jaccard'] for v in values if v['jaccard'] is not None]
        overlaps[domain]=dict(total_both_error_positions=sum(v['both_error_positions']
            for v in values),total_either_error_positions=sum(v['either_error_positions']
            for v in values),jaccard_defined_channels=len(defined),
            mean_jaccard_when_defined=None if not defined else mean(defined))
    return dict(by_snr=groups,cross_snr_same_physical_channel=overlaps)


def extract(old,gi,oi,started,out):
    o2=o2_rows(old,gi,oi,started,out)
    legacy,paired=legacy_rows(old,gi,started,out)
    return dict(O2_rows=o2,legacy_FULL_rows=legacy,
                legacy_7_8_overlap_rows=paired)


def verify_end(contract,args,binding):
    old,ce,now=guard(contract,args)
    require(now==binding,'script/config/source/original summaries changed during analysis')


def run(args):
    started=time.monotonic();CPU_started=time.process_time()
    contract=json.loads(args.contract.read_text())
    old,ce,binding=guard(contract,args)
    out=Path(args.output_dir).resolve()
    require(out.is_relative_to(ce) and out!=ce,
            'new offline output outside frozen CE data root')
    memory=resources(contract)
    gi,oi,g,o=source_index(old,contract)
    out.mkdir(parents=True,exist_ok=False)
    try:
        rows=extract(old,gi,oi,started,out)
        (out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
        summary=dict(schema='ce-stage-mechanism-extract-v1',status='COMPLETE',
            source_binding=binding,O2_analysis_states=64,O2_CE_states_read=64,
            original_physical_A_states_read=32,original_FULL_states_read=64,
            O2_saved_squared_vector_checks=64*7,O2_saved_real_cross_checks=64*9,
            old_FULL_adjacent_profiles=64*2,same_channel_cross_snr_overlaps=32*2,
            O2_by_snr=aggregate_o2(rows['O2_rows']),
            legacy_error_positions=aggregate_legacy(rows['legacy_FULL_rows'],
                rows['legacy_7_8_overlap_rows']),
            candidate_status='post-hoc lag1 and same-channel 7/8 overlap description; not PRED registration',
            code_interleaver_mapping='not saved in the used terminal/truth arrays; no randomized/JSG comparator',
            Q_consumed_by_original_mean_CE=False,
            no_new_receiver_CE_BP_LDPC=(0,0,0,0),
            rows_sha256=sha(out/'rows.json'),memory_preflight=memory,
            peak_resident_bytes=proc_kib('VmHWM','/proc/self/status'),
            wall_seconds=time.monotonic()-started,
            CPU_seconds=time.process_time()-CPU_started)
        budget(started,out);verify_end(contract,args,binding)
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        # Same saved-source self-audit; a second pass is costed separately.
        audited=extract(old,gi,oi,started,out)
        require(audited==rows and aggregate_o2(audited['O2_rows'])==summary['O2_by_snr']
            and aggregate_legacy(audited['legacy_FULL_rows'],
                audited['legacy_7_8_overlap_rows'])==summary['legacy_error_positions'],
            're-read saved O2/FULL arrays disagree with recorded offline summary')
        budget(started,out);verify_end(contract,args,binding)
        audit=dict(schema='ce-stage-mechanism-raw-audit-v1',status='PASS',
            summary_sha256=sha(out/'summary.json'),rows_sha256=sha(out/'rows.json'),
            source_binding=binding,
            O2_A_state_reads_run=64,O2_E_state_reads_run=64,
            original_A_state_reads_run=32,original_FULL_state_reads_run=64,
            O2_A_state_rereads_audit=64,O2_E_state_rereads_audit=64,
            original_A_state_rereads_audit=32,original_FULL_state_rereads_audit=64,
            O2_saved_squared_vector_rechecks=64*7,O2_saved_real_cross_rechecks=64*9,
            old_FULL_adjacent_profile_rechecks=64*2,
            same_channel_cross_snr_overlap_rechecks=32*2,
            new_F=0,new_CE=0,new_BP=0,new_LDPC=0,
            independence='same-process source re-read/self-audit; scientific review weak',
            audit_wall_seconds=time.monotonic()-started-summary['wall_seconds'],
            total_wall_seconds=time.monotonic()-started,
            peak_resident_bytes=proc_kib('VmHWM','/proc/self/status'))
        (out/'raw-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
        print(json.dumps(dict(status='PASS',O2_rows=64,legacy_rows=64,
            wall_seconds=audit['total_wall_seconds'],output=str(out))),flush=True)
    except BaseException as error:
        (out/'failure.json').write_text(json.dumps(dict(status='FAILED',error=repr(error),
            wall_seconds=time.monotonic()-started),indent=2)+'\n')
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--old-root',type=Path,required=True)
    p.add_argument('--ce-root',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--contract-sha256',required=True)
    p.add_argument('--script-sha256',required=True)
    run(p.parse_args())
