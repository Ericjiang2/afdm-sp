#!/usr/bin/env python
"""Engineering gates only; prints no scientific performance readout."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
START=time.perf_counter()
HERE=Path(__file__).resolve().parent
from e3c_budget import BudgetLease,LIMIT_SECONDS


def charged(budget):
    data=json.loads((Path(budget)/'budget.json').read_text())
    if data['limit_seconds']!=LIMIT_SECONDS:
        raise RuntimeError('budget limit changed')
    return sum(x.get('actual_seconds',x['reserved_seconds']) for x in data['leases'].values())


def unit(args):
    args.root.mkdir(parents=True,exist_ok=True)
    receipt=args.root/'unit.json'
    if receipt.exists():
        raise FileExistsError(receipt)
    with BudgetLease(args.budget_dir,args.lease_seconds,sys.argv,started=START):
        for name in ('test_e3c.py','test_e3c_agg.py','test_e3c_provenance.py'):
            subprocess.run([sys.executable,str(HERE/name)],check=True)
        from e3c_driver import source_identity
        receipt.write_text(json.dumps(dict(passed=True,sources_sha256=source_identity()),indent=1)+'\n')


def merge(args):
    from e3c_agg import read_rows
    import e3c_lib as lib
    unit=json.loads((args.root/'unit.json').read_text())
    gate,sources=read_rows(args.root/'gate',lib.gate_keys(),gate=True)
    smoke,smoke_sources=read_rows(args.root/'smoke',lib.smoke_keys(),smoke=True)
    if not unit['passed'] or sources!=unit['sources_sha256'] or sources!=smoke_sources:
        raise RuntimeError('unit/gate/smoke source mismatch')
    from e3c_driver import source_identity
    if source_identity()!=sources:
        raise RuntimeError('current source differs from engineering evidence')
    per_key=sum(r['elapsed_seconds'] for r in smoke)/len(smoke)
    spent=charged(args.budget_dir)
    projection=per_key*lib.N_KEYS*1.3
    receipt=dict(G1=dict(pass_=True,keys=len(gate)),G2=dict(pass_=True),G3=dict(pass_=True,keys=len(gate)),
                 G4=dict(pass_=spent+projection<=LIMIT_SECONDS,smoke_keys=len(smoke),seconds_per_key=per_key,
                         spent_core_hours=spent/3600,projected_main_core_hours=projection/3600,contention_factor=1.3,limit_core_hours=15),
                 sources_sha256=sources,budget_dir=str(args.budget_dir.resolve()),all_pass=bool(spent+projection<=LIMIT_SECONDS))
    target=args.root/'gates.json'
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(receipt,indent=1)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='sources_sha256'},indent=1))
    if not receipt['all_pass']:
        raise SystemExit(3)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('unit','merge','remaining','freeze-check'))
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--budget-dir',type=Path,required=True)
    p.add_argument('--lease-seconds',type=float,default=300)
    a=p.parse_args()
    if a.mode=='unit':
        unit(a)
    elif a.mode=='merge':
        merge(a)
    elif a.mode=='remaining':
        print(max(0.,LIMIT_SECONDS-charged(a.budget_dir)))
    else:
        from e3c_driver import source_identity
        g=json.loads((a.root/'gates.json').read_text())
        if not g['all_pass'] or source_identity()!=g['sources_sha256'] or str(a.budget_dir.resolve())!=g['budget_dir']:
            raise RuntimeError('engineering gates/source/budget identity failed')
        freeze=a.root/'FREEZE.json'
        f=json.loads(freeze.read_text())
        if not f.get('git_commit') or f.get('sources_sha256')!=g['sources_sha256']:
            raise RuntimeError('main-owned source-freeze receipt missing or mismatched')
        required={p.name for p in HERE.glob('*.py')}|{p.name for p in HERE.glob('*.sh')}|{'PROTOCOL.md','SOURCE_MD5.txt'}
        checked=set()
        for line in (HERE/'CODE_MD5.txt').read_text().splitlines():
            digest,name=line.split()
            name=name.removeprefix('*')
            if name not in required or hashlib.md5((HERE/name).read_bytes()).hexdigest()!=digest or name in checked:
                raise RuntimeError(f'CODE_MD5 mismatch/unexpected/duplicate {name}')
            checked.add(name)
        if checked!=required:
            raise RuntimeError('CODE_MD5 incomplete')
        if charged(a.budget_dir)/3600+g['G4']['projected_main_core_hours']>15:
            raise RuntimeError('remaining budget no longer covers projected main')
        print('freeze and gates verified')


if __name__=='__main__':
    main()
