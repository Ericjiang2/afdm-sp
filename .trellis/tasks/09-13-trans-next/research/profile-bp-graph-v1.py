"""Three graph-construction microprofiles; never a detector/receiver benchmark."""
import argparse
import json
from pathlib import Path
import resource
import time
import numpy as np
import torch
from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
from afdm_sp_joint_unrolled.light_gap_replay import verified_record


def layout(n, support):
    ids = np.asarray(support, dtype=np.int64)
    delta = (ids//5*5+(ids%5-2)) % n
    if len(set(ids)) != len(ids) or len(set(delta)) != len(delta):
        raise ValueError('profile requires unique observed integer displacements')
    col = np.broadcast_to(np.arange(n)[:, None], (n, len(ids)))
    row = (col+delta[None, :]) % n
    flat = np.sort((row*n+col).ravel())
    return torch.from_numpy(flat//n), torch.from_numpy(flat%n)


def graph(H, row, col, mode):
    if mode == 'DENSE':
        h = torch.as_tensor(H, dtype=torch.complex128)
        r, c = torch.nonzero(h.abs() >= 1e-4, as_tuple=True)
        return r, c, h[r, c]
    if mode == 'INDEXED_DENSE_CAST':
        values = torch.as_tensor(H, dtype=torch.complex128)[row, col]
    elif mode == 'INDEXED_EDGE_CAST':
        values = torch.as_tensor(H)[row, col].to(torch.complex128)
    else:
        raise ValueError('unregistered graph profile mode')
    active = values.abs() >= 1e-4
    return row[active], col[active], values[active]


def main(args):
    root = args.root
    path = root/'runs/refs-v1/engineering/summary.json'
    expected_sha = 'ef13fc55728fc821fcffed8f05944fc7f47400763b26468f7fbc7406e0a4972b'
    assert sha(path) == expected_sha
    source = json.loads(path.read_text());assert source['status'] == 'COMPLETE'
    references = [r for r in source['records'] if r['arm'] == 'REFRESH47']
    assert {(r['block'], r['snr']) for r in references} == {(b,s) for b in (0,1) for s in (7,8)}
    assert len(references) == 4
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    rows=[];calls=0;start=time.monotonic()
    modes=['DENSE','INDEXED_DENSE_CAST','INDEXED_EDGE_CAST']
    for entry in references:
        record, state = verified_record(entry, root)
        H=state['H'];before=hashes(dict(H=H))
        t=time.perf_counter();r,c=layout(len(H),state['support']);layout_seconds=time.perf_counter()-t
        original=graph(H,r,c,'DENSE');calls+=1
        for mode in modes[1:]:
            actual=graph(H,r,c,mode);calls+=1
            for a,b in zip(actual,original):assert torch.equal(a,b)
        for _ in range(2):
            for mode in modes:graph(H,r,c,mode);calls+=1
        measured={m:[] for m in modes}
        for repeat in range(20):
            for mode in (modes if repeat%2==0 else modes[::-1]):
                t=time.perf_counter();cpu=time.process_time();value=graph(H,r,c,mode)
                elapsed=time.perf_counter()-t;cpu_elapsed=time.process_time()-cpu;calls+=1
                measured[mode].append(dict(seconds=elapsed,CPU_seconds=cpu_elapsed))
            if time.monotonic()-start>300:raise TimeoutError('graph quote budget exceeded')
        assert hashes(dict(H=H))==before
        rows.append(dict(block=entry['block'],snr=entry['snr'],reference_sha256=entry['sha256'],
            N=len(H),atoms=len(state['support']),candidate_edges=len(r),active_edges=len(original[0]),
            input_dtype=str(H.dtype),H_hash=before['H'],layout_build_seconds=layout_seconds,
            ordered_edges_and_values_exact=True,timings=measured,
            means={m:dict(seconds=float(np.mean([x['seconds'] for x in v])),
                          CPU_seconds=float(np.mean([x['CPU_seconds'] for x in v]))) for m,v in measured.items()}))
    assert calls==276 and sha(path)==expected_sha
    result=dict(status='PASS',A_calls=calls,F_calls=0,T_calls=0,LDPC_calls=0,rows=rows,
        summary_sha256=expected_sha,script_sha256=sha(Path(__file__)),wall_seconds=time.monotonic()-start,
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope='4 saved N1024 H; 20 repeated microtimings are not independent channels or complete COST; concurrent diagnostic only',
        instrumentation_files=[str(Path(__file__))],receiver_sources_modified=False)
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
    for row in rows:print(json.dumps({k:v for k,v in row.items() if k!='timings'}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
