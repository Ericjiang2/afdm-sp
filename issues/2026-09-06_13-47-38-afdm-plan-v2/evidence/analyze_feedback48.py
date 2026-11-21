"""Paired full-loop feedback and frozen-state diagnostics; no retuning."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import tarfile
import numpy as np

ROOT=Path(__file__).resolve().parent
ARMS=['f_mean','f_uniform','f_dynamic','o_data']


def main():
    with tarfile.open(ROOT/'feedback48-runtime.tar.gz') as archive:
        raw={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    queue=json.loads(raw['queue-status.json'])
    assert queue['complete'] and len(queue['runs'])==3 and all(x['exit_code']==0 for x in queue['runs'])
    rows=[]; statuses=[]
    for rep in range(3):
        statuses.append(json.loads(raw[f'dev{rep}/status.json']))
        rows.extend(json.loads(line) for line in raw[f'dev{rep}/frames.jsonl'].splitlines())
    for status in statuses:
        assert status['complete'] and status['completed_frames']==16 and not status.get('failure')
        for key in ('source_sha256','checkpoint_sha256','calibration_sha256','ldpc_sha256','device'):
            assert status[key]==statuses[0][key]
    rows.sort(key=lambda r:(r['replicate'],r['frame_index']))
    assert [(r['replicate'],r['frame_index']) for r in rows]==[(rep,i) for rep in range(3) for i in range(16)]
    mechanism=json.loads((ROOT/'mechanism48-runtime-validation.json').read_text())['frame_records']
    bins=defaultdict(lambda:dict(count=0,sum_variance=0.,sum_actual_squared_error=0.,wrong=0))
    reliability=defaultdict(lambda:dict(count=0,nll_sum=0.,brier_sum=0.,high_confidence_count=0,high_confidence_errors=0,out_of_range_count=0,cases=[]))
    records=[];nmse_comparisons=[];costs=[];snapshots=[]
    for frame,old in zip(rows,mechanism):
        assert frame['input_hashes']==old['input_hashes'] and frame['split']=='D_dev' and frame['snr']==8
        assert set(frame['arms'])==set(ARMS)
        assert frame['arms']['f_mean']['info_errors']==old['info_errors']['baseline']
        for name,a in frame['arms'].items():
            assert a['finite'] and a['dals_temperature']==1 and a['oracle']==(name=='o_data')
            assert [s['outer_iter'] for s in a['dals_consumers']]==list(range(1,10))
            assert all(c['unique_count']<=(48 if c['stage']=='temporary' else 40) for c in a['capacity_trace'])
            assert len(a['reliability'])==18
            for observation in a['reliability']:
                assert observation['count']==1024 and observation['nll_status']=='finite'
                key=(name,observation['stage'],observation['outer_iter']); r=reliability[key]
                for field in ('count','high_confidence_count','high_confidence_errors','out_of_range_count'):
                    r[field]+=observation[field]
                r['nll_sum']+=observation['nll']*observation['count'];r['brier_sum']+=observation['brier']*observation['count']
                for symbol in observation['first_high_confidence_error_symbols']:
                    if len(r['cases'])<3:r['cases'].append(dict(replicate=frame['replicate'],frame_index=frame['frame_index'],symbol=symbol,frame_error=a['info_errors']>0))
                for i,b in enumerate(observation['bins']):
                    target=bins[(*key,i)]
                    for field in target:target[field]+=b[field]
            costs.append(dict(replicate=frame['replicate'],frame_index=frame['frame_index'],arm=name,
                receiver_seconds=a['receiver_seconds'],standalone_seconds=a['standalone_seconds_estimate'],
                observer_transfer_seconds=a['dals_observer_transfer_seconds'],
                snapshot_io_seconds=a.get('dals_snapshot_io_seconds',0),offline_matrix_seconds=a.get('offline_matrix_seconds',0)))
        mean=frame['arms']['f_mean']; assert len(mean['frozen_state_comparisons'])==9
        snapshots.append(mean['dals_snapshot'])
        for i,c in enumerate(mean['frozen_state_comparisons']):
            assert all(c[m]['own_objective_after']<=c[m]['own_objective_before'] for m in ('unweighted','uniform','dynamic'))
            nmse_comparisons.append(dict(replicate=frame['replicate'],frame_index=frame['frame_index'],outer_iter=i+1,**c['same_support_channel_nmse']))
        records.append(dict(replicate=frame['replicate'],frame_index=frame['frame_index'],input_hashes=frame['input_hashes'],
            info_errors={a:frame['arms'][a]['info_errors'] for a in ARMS},
            frame_errors={a:int(frame['arms'][a]['info_errors']>0) for a in ARMS}))
    m=np.array([[r['frame_errors'][a] for a in ARMS] for r in records],dtype=float)
    bits=np.array([[r['info_errors'][a] for a in ARMS] for r in records],dtype=float)
    rng=np.random.default_rng(2026090611);indices=[rng.integers(0,16,(20000,16)) for _ in range(3)]
    boot=sum(part[idx].mean(1) for part,idx in zip(m.reshape(3,16,4),indices))/3
    bitboot=sum(part[idx].mean(1) for part,idx in zip(bits.reshape(3,16,4),indices))/3
    contrasts={}
    for left,right in [('f_dynamic','f_uniform'),('f_dynamic','f_mean'),('f_uniform','f_mean'),('o_data','f_mean')]:
        i,j=ARMS.index(left),ARMS.index(right);w=np.eye(4)[i]-np.eye(4)[j]
        contrasts[left+'_vs_'+right]=dict(delta_FER=float(m.mean(0)@w),bootstrap95=np.quantile(boot@w,[.025,.975]).tolist(),
            per_stream=[float(x.mean(0)@w) for x in m.reshape(3,16,4)],net_info_bit_delta=int(bits.sum(0)@w),
            mean_info_bit_delta_bootstrap95=np.quantile(bitboot@w,[.025,.975]).tolist(),
            paired_FER_benefit=int(((m[:,i]==0)&(m[:,j]==1)).sum()),paired_FER_harm=int(((m[:,i]==1)&(m[:,j]==0)).sum()))
    rel=[]
    for key,r in sorted(reliability.items()):
        r.update(nll=r.pop('nll_sum')/r['count'],brier=r.pop('brier_sum')/r['count'],
            high_confidence_error_rate=r['high_confidence_errors']/r['high_confidence_count'] if r['high_confidence_count'] else None,
            high_confidence_error_frequency=r['high_confidence_errors']/r['count'])
        rel.append(dict(arm=key[0],stage=key[1],outer_iter=key[2],**r))
    result=dict(scope='48 paired development frames; descriptive feedback attribution only',n=48,receiver_evaluations=192,
        pooled_errors=dict(zip(ARMS,m.sum(0).astype(int).tolist())),
        per_stream_errors=[dict(zip(ARMS,x.sum(0).astype(int).tolist())) for x in m.reshape(3,16,4)],
        contrasts=contrasts,frame_records=records,reliability=rel,
        bins=[dict(arm=k[0],stage=k[1],outer_iter=k[2],bin=k[3],**v) for k,v in sorted(bins.items())],
        common_state_nmse=nmse_comparisons,costs=costs,snapshots=snapshots,queue=queue,
        bootstrap=dict(seed=2026090611,draws=20000,unit='paired frame within fixed stream',limitation='descriptive percentile only; no multiplicity or formal coverage'),
        artifact_sha256={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()})
    (ROOT/'feedback48-runtime-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('pooled_errors','per_stream_errors','contrasts')},indent=2))


if __name__=='__main__':main()
