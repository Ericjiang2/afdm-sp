"""Bounded offline D_design audit. No receiver calls, confirmation, or freeze mutation."""
import hashlib
import json
import signal
import sys
import time
from pathlib import Path

ROOT=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908')
sys.path.insert(0,str(ROOT/'source-runtime-v8'))
import numpy as np
from afdm_sp_joint_unrolled.direction_budget import locked,settle_many
from afdm_sp_joint_unrolled.direction_select import read,load_run,indexed,paired_interval
from afdm_sp_joint_unrolled.direction_logging import validate_pair
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def source_map(version):
    folder=ROOT/f'source-runtime-{version}'/'afdm_sp_joint_unrolled'
    return {str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*.py'))}


def audit_snapshot(row):
    entry=row['snapshot'];require(sha(entry['path'])==entry['sha256'],'snapshot digest mismatch')
    with np.load(entry['path'],allow_pickle=False) as data:
        for field,key in [('y','y'),('pilot','pilot'),('Htrue','H'),('info','info'),
                          ('coded','coded'),('noise','noise'),('data','data')]:
            require(array_hash(data[field])==row['input_hashes'][key],'snapshot input mismatch '+field)
        require(array_hash(data['decoded'])==row['hard_output_hash'],'decoded hash mismatch')
        require(float(data['sigma2_terminal'])==row['sigma_value'],'terminal sigma mismatch')
        require(int(np.count_nonzero(data['info_hat']!=data['info']))==row['coded_bit_errors'],'info errors mismatch')
        raw=np.concatenate((data['x_hard'].real<0,data['x_hard'].imag<0))
        require(int(np.count_nonzero(raw!=data['coded']))==row['raw_bit_errors'],'raw errors mismatch')
        for field in ('mu','var','llr'):
            require(array_hash(data[field])==row['posterior_audit'][field]['sha256'],'posterior hash mismatch')
        cancel=row['arm_id'].startswith('cancel-')
        if cancel:
            for field,key in [('detector_H','detector_H_sha256'),('detector_z','detector_z_sha256'),('cancellation_B','cancellation_B_sha256')]:
                require(array_hash(data[field])==row[key],'transform hash mismatch '+field)
            require(float(data['sigma2_terminal_base'])==row['sigma2_terminal_base'],'base sigma mismatch')
        H=np.asarray(data['detector_H' if cancel else 'Hhat'],dtype=np.complex128)
        graphs=[g for g in row['graph_edges_each_stage'] if g['stage']=='final_bp']
        require(len(graphs)==1,'requires one recorded terminal BP graph')
        graph=graphs[0];mask=np.abs(H)>=1e-4
        require(graph['H_hash']==array_hash(H) and graph['threshold']==1e-4 and graph['operator']=='>=','terminal graph source mismatch')
        require(graph['edges']==int(mask.sum()) and graph['row_degrees']==mask.sum(axis=1).tolist()
                and graph['column_degrees']==mask.sum(axis=0).tolist(),'terminal graph edge mismatch')
        return {'snapshot':entry,'graph_H_sha256':graph['H_hash'],'edges':graph['edges'],
                'recorded_terminal_graphs':1,'transform_bindings':{k:row[k] for k in
                    ('detector_H_sha256','detector_z_sha256','cancellation_B_sha256')} if cancel else None}


def analyze():
    protocol,phash=read(ROOT/'source-runtime-v8/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/campaign-protocol.json')
    old={r['id']:r for r in protocol['design']['recipes']}
    new={f'cancel-{m}':dict(id=f'cancel-{m}',family='sbl',parameter=.001,terminal_scale=.5,cancellation_mode=m)
         for m in ('scalar','diagonal','lowrank')}
    require(len(old)==8,'requires eight frozen baselines')
    baseline=[];provenance=[];snapshot_bindings=[]
    v4=source_map('v4');v8=source_map('v8')
    for name,recipes,expected_source in [('design-000-096-v4',old,v4),('design-096-192-v4',old,v4),('cancel-design-v8',new,v8)]:
        rows,binding=load_run(ROOT/name,phash,recipes,'design')
        require(binding['source_sha256']==expected_source,'unexpected source version '+name)
        provenance.append(binding)
        for row in rows:
            snapshot_bindings.append(dict(block=row['block_id'],arm=row['arm_id'],**audit_snapshot(row)))
        if name=='cancel-design-v8':cancel=rows
        else:baseline.extend(rows)
    require(len(baseline)==1536 and len(cancel)==576,'incorrect full-call totals')
    table=indexed(baseline+cancel,{**old,**new},range(192),'design')
    ref=[table[b,'sbl-s0.5']['FER'] for b in range(192)]
    require(sum(ref)==31,'frozen B_star does not match31/192')
    metrics={}
    for arm in (*old,*new):
        rows=[table[b,arm] for b in range(192)]
        times=[r['elapsed_seconds'] for r in rows]
        metrics[arm]={'n':192,'frame_errors':sum(r['FER'] for r in rows),'FER':float(np.mean([r['FER'] for r in rows])),
            'decoded_info_BER':sum(r['coded_bit_errors'] for r in rows)/sum(r['coded_bits_denominator'] for r in rows),
            'raw_coded_BER':sum(r['raw_bit_errors'] for r in rows)/sum(r['raw_bits_denominator'] for r in rows),
            'elapsed_seconds_raw':times,'mean':float(np.mean(times)),'p95':float(np.quantile(times,.95)),
            'process_cpu_seconds_total':sum(r['process_cpu_seconds'] for r in rows),
            'transfer_seconds_total':sum(r['transfer_seconds'] for r in rows),
            'inclusive_seconds_total':sum(r['inclusive_seconds'] for r in rows),
            'peak_gpu_bytes':max(r['peak_gpu_bytes'] for r in rows)}
    comparisons={arm:paired_interval(ref,[table[b,arm]['FER'] for b in range(192)],comparisons=3) for arm in new}
    pareto=[a for a in metrics if not any(metrics[b]['FER']<=metrics[a]['FER'] and metrics[b]['mean']<=metrics[a]['mean']
              and (metrics[b]['FER']<metrics[a]['FER'] or metrics[b]['mean']<metrics[a]['mean']) for b in metrics if a!=b)]
    strict=[a for a in new if metrics[a]['frame_errors']<31]
    strong=min(strict,key=lambda a:(metrics[a]['FER'],metrics[a]['mean'],a)) if strict else 'sbl-s0.5'
    engineering,ehash=read(ROOT/'evidence/cancellation-engineering-audit-v8.json')
    require(engineering['status']=='passed' and engineering['source_sha256']==v8,'engineering evidence mismatch')
    require(all(c['n']==4 for c in engineering['cost'].values()),'unexpected engineering timing sample')
    return {'status':'complete','protocol_sha256':phash,'provenance':provenance,'snapshot_bindings':snapshot_bindings,
        'metrics':metrics,'paired_exploratory_CIs':comparisons,'contrast_definition':'FER_sbl-s0.5 minus FER_candidate; positive benefits candidate',
        'all_eleven_arms_retained':list(metrics),'point_estimate_FER_cost_Pareto':pareto,
        'suggested_strong_reference':strong,'reference_rule':'strictly lower design FER; tie by diagnostic mean then ID; otherwise retain sbl-s0.5',
        'engineering_audit_sha256':ehash,'engineering_cost':engineering['cost'],
        'source_version_differences':[k for k in sorted(set(v4)|set(v8)) if v4.get(k)!=v8.get(k)],
        'scope':'Exploratory design selection only. Costs are instrumented across source versions; engineering n4 is not a formal cost gate. No formal significance, new-algorithm, or confirmation claim.',
        'truth_boundary':'Only static receiver-interface review supports observed-only routing; this analysis does not prove all dependencies leak-free.',
        'terminal_count_scope':'One final_bp graph per logged full call; static code review additionally required to certify unlogged calls.',
        'freeze_modified':False,'analysis_source_sha256':sha(__file__)}


def main():
    out=ROOT/'evidence/cancellation-design-results-v8.json';failure=out.with_name('cancellation-design-analysis-failure-v8.json')
    require(not out.exists() and not failure.exists(),'immutable analysis already exists')
    ledger_path=ROOT/'resource-ledger.json';rid='cancellation-design-analysis-v8'
    started=time.perf_counter();cpu=time.process_time();status='failed'
    with locked(ledger_path) as ledger:
        rows=ledger['completed']+ledger['reservations']
        require(not any(r['id']==rid for r in rows),'analysis already reserved/attempted')
        reservation=dict(host_seconds=300,gpu_seconds=0,cpu_core_seconds=300)
        for key,value in reservation.items():
            require(value+sum(r[key] for r in rows)<=ledger['limits'][key],'analysis resource budget exhausted')
        ledger['reservations'].append(dict(id=rid,calls={},**reservation))
    def timeout(*_):raise TimeoutError('300-second offline analysis limit')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGPROF,timeout)
    signal.setitimer(signal.ITIMER_REAL,300);signal.setitimer(signal.ITIMER_PROF,300)
    try:
        result=analyze();result['analysis_resources']={'host_seconds':time.perf_counter()-started,'cpu_core_seconds':time.process_time()-cpu,'gpu_seconds':0}
        publish_json(out,result);status='complete'
    except BaseException as error:
        publish_json(failure,{'status':'failed','error':repr(error),'calls':{},'analysis_source_sha256':sha(__file__),
            'host_seconds':time.perf_counter()-started,'cpu_core_seconds':time.process_time()-cpu})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.setitimer(signal.ITIMER_PROF,0)
        settle_many(ledger_path,rid,calls={},resources=dict(host_seconds=time.perf_counter()-started,
            cpu_core_seconds=time.process_time()-cpu,gpu_seconds=0),evidence=str(out if status=='complete' else failure),status=status)


if __name__=='__main__':main()
