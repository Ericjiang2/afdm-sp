"""Create a reviewable exact file-hash binding before any receiver call."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_observed import _source_files, sha256


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ('source','baseline','geometry','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    hashes={name:sha256(path) for name,path in _source_files(args).items()}
    args.out.write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
    print(args.out)
