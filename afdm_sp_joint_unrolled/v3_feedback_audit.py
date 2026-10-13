"""Read existing f_mean states; regenerate exogenous frames, never rerun BP."""
import argparse
import contextlib
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.feedback_diagnostics import reliability_statistics
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.v3_statistics import residual_decomposition


def audit(manifest):
    started=time.time()
    with contextlib.redirect_stdout(sys.stderr):system=_make_config_a(1024,2,8,10,4)
    code=build_code(2048,d_v=3,d_c=6,seed=20260726)
    results=[]
    for item in manifest:
        path=Path(item['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('old state snapshot changed')
        saved=torch.load(path,map_location='cpu',weights_only=False)
        rep,index=item['identity'];frame=make_frame(system,code,rep,index,8.,split=1)
        for key,digest in saved['frame_input_hashes'].items():
            if array_hash(frame[key])!=digest:raise ValueError('regenerated exogenous frame differs: '+key)
        if [s['outer_iter'] for s in saved['states']]!=list(range(1,10)):raise ValueError('missing old feedback stages')
        for s in saved['states']:
            array=lambda key:s[key].numpy()
            probabilities=array('probabilities');constellation=array('constellation')
            reliable=reliability_statistics(probabilities,constellation,frame['data'],.5)
            decomposition=residual_decomposition(frame['y'],frame['H'],array('H'),frame['pilot'],frame['data'],array('mu'))
            if decomposition['relative_vector_closure']>1e-10:raise ValueError('residual identity failed')
            results.append(dict(replicate=rep,frame=index,outer_iter=s['outer_iter'],
                sigma2=float(s['sigma2']),reliability=reliable,residual=decomposition))
        print(json.dumps(dict(audited_frames=len(results)//9,total_frames=len(manifest))),file=sys.stderr,flush=True)
    return dict(frames=len(manifest),states=len(results),full_receiver_calls=0,
        wall_seconds=time.time()-started,trajectory='historical f_mean; not B0',records=results,
        scope='offline same-state reliability and exact residual audit; existing solutions not rerun')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    result=audit(json.loads(a.manifest.read_text()))
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(frames=result['frames'],states=result['states'],wall_seconds=result['wall_seconds'])))
