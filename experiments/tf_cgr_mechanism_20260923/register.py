"""Lock the reviewed observed-only inputs before any production receiver call."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_observed import PROTOCOL_SHA256, WITNESS_MANIFEST_SHA256, sha256


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ('witness-manifest','witness-receipt','source-bindings',
                'qualification','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    if sha256(args.witness_manifest)!=WITNESS_MANIFEST_SHA256:
        raise ValueError('canonical witness manifest differs')
    receipt=json.loads(args.witness_receipt.read_text())
    qualification=json.loads(args.qualification.read_text())
    if receipt.get('status')!='pass' or qualification.get('status')!='synthetic_pass':
        raise ValueError('witness or numerical qualification has not passed')
    registration=dict(schema='tf-cgr-registration/1',status='locked',
        protocol_sha256=PROTOCOL_SHA256,
        witness_manifest_sha256=WITNESS_MANIFEST_SHA256,
        witness_receipt_sha256=sha256(args.witness_receipt),
        source_bindings_sha256=sha256(args.source_bindings),
        qualification_sha256=sha256(args.qualification),
        fixed_observations=25,arms=['BASE','CGR','SHAM','BLOCK'],
        expected_complete_wrappers=100,native_rounds=2,final_tf_iterations=20,
        decoder_maxiter=50,seconds_cap=1800,bytes_cap=2*1024**3,
        truth_online=False)
    args.out.write_text(json.dumps(registration,sort_keys=True,indent=2)+'\n')
    print(args.out)
