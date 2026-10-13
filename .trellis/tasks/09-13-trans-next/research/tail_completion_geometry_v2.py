"""Read-only operator-graph geometry for frozen TAIL v2 output.

Counts distinct physical row shifts. It does not evaluate another candidate,
channel, receiver, CE, BP, LDPC or FER. A row shift is a possible sparse H
edge family, not a measured BP graph after coefficient cancellation.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

import tail_completion_v2 as tail


def graph_geometry(S,T,n=tail.N):
    core={((tail.STRIDE*l+k)%n) for l,k in S}
    full={((tail.STRIDE*l+k)%n) for l,k in S+T}
    tail.require(core<=full,'graph shifts changed original core')
    return dict(core_unique_row_shifts=len(core),completed_unique_row_shifts=len(full),
        additional_unique_row_shifts=len(full-core),
        core_possible_matrix_edges=n*len(core),completed_possible_matrix_edges=n*len(full),
        additional_possible_matrix_edges=n*len(full-core),
        extra_atom_contributions=n*len(T))


def main():
    p=argparse.ArgumentParser()
    for name in ('contract','source_dir','source_manifest','old_root','ridge_root','tail_rows','output_dir'):
        p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--contract-sha256',required=True)
    p.add_argument('--tail-script-sha256',required=True)
    p.add_argument('--geometry-script-sha256',required=True)
    a=p.parse_args();started=time.monotonic()
    tail.assert_threads()
    tail.require(tail.sha(__file__)==a.geometry_script_sha256
        and tail.sha(a.contract)==a.contract_sha256
        and tail.sha(tail.__file__)==a.tail_script_sha256,
        'geometry/source script hash differs')
    contract=json.loads(a.contract.read_text())
    tail.require(contract['status']=='FROZEN_AFTER_INDEPENDENT_REVIEW'
        and not a.output_dir.exists(),'unfrozen contract or occupied geometry output')
    tail.source_guard(a,contract);tail.input_guard(a,contract)
    preflight=tail.memory_preflight()
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    ri,_=tail.load_index(a)
    original=json.loads(a.tail_rows.read_text())
    index={(r['block'],r['snr']):r for r in original
           if r['arm']==tail.ARMS[2] and r['t']==1}
    tail.require(len(index)==64 and len(original)==384,
        'frozen TAIL rows work-point inventory differs')
    rows=[]
    for b in range(32):
        tail.require(time.monotonic()-started<7200,'geometry wall cap reached')
        for snr in tail.SNRS:
            _,state=verified_record(ri[b,snr],a.ridge_root)
            S,T=tail.support_and_tail(state['dals'][0]['support_delays'],
                                      state['dals'][0]['support_dopplers'])
            S9,T9=tail.support_and_tail(state['dals'][8]['support_delays'],
                                       state['dals'][8]['support_dopplers'])
            tail.require(S==S9 and T==T9,'t1/t9 source geometry differs')
            source=index[b,snr]
            tail.require(source['ridge_F_record_sha256']==ri[b,snr]['sha256']
                and source['original_S_sha256']==tail.array_sha(np.array(S,dtype=np.int64))
                and source['T_atoms']==len(T),
                'geometry re-read differs from frozen scored support')
            rows.append(dict(block=b,snr=snr,physical_support_record_sha256=ri[b,snr]['sha256'],
                             original_S_sha256=source['original_S_sha256'],
                             S_atoms=len(S),T_atoms=len(T),**graph_geometry(S,T)))
    tail.require(len(rows)==64,'geometry work-point count differs')
    a.output_dir.mkdir(parents=True)
    rp=a.output_dir/'rows.json';rp.write_text(json.dumps(rows,indent=2)+'\n')
    fields=('S_atoms','T_atoms','core_unique_row_shifts','completed_unique_row_shifts',
            'additional_unique_row_shifts','core_possible_matrix_edges',
            'completed_possible_matrix_edges','additional_possible_matrix_edges',
            'extra_atom_contributions')
    aggregate={field:dict(mean=float(np.mean([r[field] for r in rows])),
                           minimum=int(min(r[field] for r in rows)),
                           maximum=int(max(r[field] for r in rows))) for field in fields}
    summary=dict(schema='tail-completion-geometry-v2',status='COMPLETE',
        tail_rows_sha256=tail.sha(a.tail_rows),rows_sha256=tail.sha(rp),
        contract_sha256=a.contract_sha256,tail_script_sha256=a.tail_script_sha256,
        geometry_script_sha256=a.geometry_script_sha256,
        original_ridge_F_record_reads=64,new_F=0,new_CE=0,new_BP=0,new_LDPC=0,
        graph_scope='distinct physical row shifts give possible sparse H edges; actual BP graph/cancellation not measured',
        by_work_point=aggregate,memory_preflight=preflight,
        peak_resident_bytes=__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss*1024,
        wall_seconds=time.monotonic()-started)
    (a.output_dir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    tail.source_guard(a,contract);tail.input_guard(a,contract)
    tail.require(tail.sha(__file__)==a.geometry_script_sha256
        and tail.sha(tail.__file__)==a.tail_script_sha256,'geometry source changed')
    print(json.dumps({'status':'COMPLETE','work_points':64,'wall_seconds':summary['wall_seconds']}))


if __name__=='__main__':main()
