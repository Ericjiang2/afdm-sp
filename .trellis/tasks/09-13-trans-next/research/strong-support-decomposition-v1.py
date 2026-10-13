"""Truth-only offline projection; no receiver or decoder calls."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main(args):
    root=args.root;source=root/'source-receiver-domain-v2';sys.path.insert(0,str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes,load_state
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
    manifest=source/'source-manifest.json';contract=root/'contracts/strong-support-decomposition-v1.json';c=json.loads(contract.read_text())
    assert sha(manifest)=='2fd0beb6efd405e7c7921a79c8e209f87203322bed67bc41c7f6cde4a6bb9dd9'
    assert sha(contract)==args.contract_sha256 and sha(Path(__file__))==args.script_sha256
    assert c['bounds']==dict(A=32,seconds=300) and c['blocks']==list(range(32)) and c['snrs']==[7]
    guard=setup_guard(SimpleNamespace(contract=contract,contract_sha256=args.contract_sha256,source_manifest=manifest,source_sha256=sha(manifest)),c);guard.verify()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(root/'runs'/c['tag'],'analysis',c['bounds'],c['output_bytes'],guard)
    try:
        inputs=json.loads((root/'runs/refs-v1/development/summary.json').read_text())
        references=json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
        assert inputs['status']==references['status']=='COMPLETE'
        refs={r['block']:r for r in references['records'] if r['snr']==7 and r['arm']=='BP_RETAIN'}
        assert set(refs)==set(range(32))
        domain=c['cells'][1];assert (domain['N'],domain['k_max'],domain['K'])==(1024,2,5)
        rows=[]
        for block in range(32):
            entry=refs[block];record,actual=verified_record(entry,root)
            exo=next(e for e in inputs['exogenous'] if e['block']==block);truth=load_state(exo['state'])
            assert hashes({k:truth[k] for k in exo['hashes']})==exo['hashes']
            ids=np.asarray(actual['support'],dtype=np.int64);delays=torch.from_numpy(ids//5);dopplers=torch.from_numpy(ids%5-2)
            state=actual['dals'][-1]
            np.testing.assert_array_equal(ids,state['support_delays']*5+state['support_dopplers']+2)
            true=torch.as_tensor(np.asarray(truth['H'],dtype=np.complex128));estimated=torch.as_tensor(np.asarray(actual['H'],dtype=np.complex128))
            def project(H):return project_channel_on_support(H,delays,dopplers,domain['c1'],domain['c2'],2)
            def decompose():
                projected,gains=project(true);estimated_projected,estimated_gains=project(estimated)
                residual=true-projected;orthogonality=project(residual)[0]
                energy=lambda value:float(torch.sum(torch.abs(value)**2))
                denominator=energy(true);total=energy(estimated-true)
                if denominator<=0 or total<=0:raise ValueError('nonpositive error denominator; ratio undefined')
                representation=energy(residual);distance=energy(estimated-projected)
                metrics=dict(truth_energy=denominator,total_error=total,representation_error=representation,
                    distance_to_support_oracle=distance,within_span_gain_error=energy(estimated_projected-projected),
                    actual_outside_span_error=energy(estimated-estimated_projected),
                    decomposition_cross_term=total-representation-distance,
                    projection_residual_in_span=energy(orthogonality),
                    representation_fraction=representation/total,channel_NMSE=total/denominator,
                    oracle_support_NMSE=representation/denominator)
                assert metrics['projection_residual_in_span']<=1e-20*max(1.,denominator)
                return dict(projected_H=projected.numpy(),oracle_gains=gains.numpy(),projected_estimated_gains=estimated_gains.numpy(),support_ids=ids,metrics=metrics)
            identity=dict(block=block,snr=7,split=2,arm='SUPPORT_ORACLE_ANALYSIS')
            value,out=run.call('A',identity,decompose,lambda v:v['metrics'],dict(reference_record_sha256=entry['sha256'],exogenous_hashes=exo['hashes'],reference_scores=record['scores'],offline_truth_access='Frobenius diagnostic only'))
            rows.append(dict(block=block,reference_FER=record['scores']['FER'],metrics=value['metrics']))
        # Re-read all saved projections and verify scalar errors directly from old raw H.
        for entry in run.records:
            record,value=verified_record(entry,root);block=entry['block']
            exo=next(e for e in inputs['exogenous'] if e['block']==block);truth=load_state(exo['state'])
            _,actual=verified_record(refs[block],root);metrics=value['metrics']
            for name,error in [('representation_error',truth['H']-value['projected_H']),('distance_to_support_oracle',actual['H']-value['projected_H'])]:
                np.testing.assert_allclose(float(np.sum(np.abs(error)**2)),metrics[name],rtol=1e-12,atol=1e-12)
        guard.verify();assert sha(Path(__file__))==args.script_sha256 and run.counts==dict(A=32)
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,raw_readback_records=32,rows=rows,records=run.records,
            source_sha256=sha(manifest),contract_sha256=args.contract_sha256,script_sha256=args.script_sha256,scope=c['scope']))
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,rows=rows)))
    except BaseException as exc:run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
