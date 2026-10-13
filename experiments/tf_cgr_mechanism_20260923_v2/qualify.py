"""Synthetic algebra and frozen-map qualification; no production observation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PARSER = argparse.ArgumentParser()
PARSER.add_argument('--out',type=Path,required=True)
PARSER.add_argument('--source',type=Path,default=None)
PARSER.add_argument('--baseline',type=Path,default=None)
PARSER.add_argument('--archive',type=Path,default=None)
ARGS = PARSER.parse_args()

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ARCHIVE = EXP.parent / '_archive/20260923_tf_cgr_investigation/extracted/coherent_gain_investigation'
SOURCE = ARGS.source or EXP/'sp_afdm_native_joint_20260921'
BASELINE = ARGS.baseline or EXP/'sp_afdm_frozen_20260920'
ARCHIVE = ARGS.archive or ARCHIVE
sys.path[:0] = [str(HERE), str(SOURCE/'src'),
                str(BASELINE/'src'), str(ARCHIVE)]

import generate_variants
import tf_base
import tf_cgr
import tf_sham
import tf_block
from block_bilinear import block_amp
from coherence_reference import Physics, receive
from physical import Channel, daft, projected_variance
from twofft import scalar_joint as frozen_scalar


def delta(a, b, keys=('extrinsic', 'app', 'mu', 'variance', 'gains')):
    return max(float(np.max(np.abs(np.asarray(a[k])-np.asarray(b[k])))) for k in keys)


def check(condition, name, value=None):
    if not condition:
        raise AssertionError(f'{name}: {value}')
    return dict(check=name, value=value)


def run(out: Path):
    out = out.resolve()
    if out.exists():
        raise FileExistsError(out)
    variants = generate_variants.verify(SOURCE/'src/twofft.py')
    tf_block.bind_source(SOURCE/'src/block_bilinear.py')
    out.mkdir(parents=True)
    copied = out/'archived_reference_copy'
    copied.mkdir()
    for name in ('coherence_reference.py', 'verify_reference.py', 'verify_reaction.py'):
        shutil.copy2(ARCHIVE/name, copied/name)
    shutil.copytree(ARCHIVE/'frozen_reference', copied/'frozen_reference')
    reference_runs = []
    for name in ('verify_reference.py', 'verify_reaction.py'):
        result = subprocess.run([sys.executable, str(copied/name)], cwd=copied,
            env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        reference_runs.append(dict(script=name, stdout=result.stdout,
            output_sha256=hashlib.sha256((copied/('qualification.json' if name=='verify_reference.py'
                else 'reaction_qualification.json')).read_bytes()).hexdigest()))

    rng = np.random.default_rng(233023)
    checks = []
    for n, delays, nus in ((17,[1,3,7],[.1,.23,-.7]),
                            (32,[3,3,3],[.2,.27,1.1]),
                            (64,[1,3,3],[.2,.21,.26])):
        phys = Physics(n,delays,nus,3.7/(2*n),.017)
        h = (rng.normal(size=3)+1j*rng.normal(size=3))/3
        c = Channel(n,phys.c1,phys.c2,delays,nus,h)
        y = rng.normal(size=n)+1j*rng.normal(size=n)
        pilot = .5*(rng.normal(size=n)+1j*rng.normal(size=n))
        for prior in (rng.normal(size=2*n),np.full(2*n,30.),np.full(2*n,-30.)):
            kw = dict(prior=prior,iterations=3,record_states=True)
            base = tf_base.scalar_joint(y,pilot,c,.25,**kw)
            frozen = frozen_scalar(y,pilot,c,.25,**kw)
            err = delta(base,frozen)
            checks.append(check(err < 1e-12,'instrumented_base_matches_frozen',err))
            cgr = tf_cgr.scalar_joint(y,pilot,c,.25,**kw)
            sham = tf_sham.scalar_joint(y,pilot,c,.25,**kw)
            if len(set(delays)) == 3:
                for mode, obj in [('cgr',cgr),('sham',sham)]:
                    err = delta(base,obj)
                    checks.append(check(err < 1e-12,f'distinct_delay_{mode}_identity',err))
            for mode, obj in [('base',base),('cgr',cgr),('sham',sham)]:
                checks.append(check(len(obj['states'])==3 and
                    all(set(('h_pre','hbar','x','xbar','mu','v','s','alpha','vq','physical_R','gain_R','app'))
                    <= set(state) for state in obj['states']),f'{mode}_trace_complete'))
            # One-step common-state formula uses the actual reciprocal floor through vq.
            a = tf_base.scalar_joint(y,pilot,c,.25,prior=prior,iterations=1,record_states=True)
            b = tf_cgr.scalar_joint(y,pilot,c,.25,prior=prior,iterations=1,record_states=True)
            t = a['states'][0]
            R = t['physical_R']
            dh = -t['alpha']*n*t['vx']/(c.p+1/t['vq'])*(R-np.eye(c.p))@t['hbar']
            err = float(np.max(np.abs(b['gains']-a['gains']-dh)))
            checks.append(check(err < 1e-10,'actual_vq_common_state_delta',err))
            physical = float(np.vdot(dh,R@dh).real)
            checks.append(check(physical >= -1e-12,'physical_delta_nonnegative',physical))
            block = tf_block.scalar_joint(y,pilot,c,.25,**kw)
            ref_block = block_amp(daft(y,c.c1,c.c2,True),pilot,c,.25,
                                  prior=prior,iterations=3)
            err = delta(block,ref_block,keys=('extrinsic','app','mu','variance',
                                             'gains','gain_covariance'))
            checks.append(check(err < 1e-9,'production_block_map',err))
            checks.append(check(len(block['states'])==3 and
                all(np.isfinite(state['S']).all() for state in block['states']),
                'block_snapshots_complete'))

        U = phys.dense()
        R_dense = np.einsum('imk,jmk->ij',U.conj(),U)/n
        err = float(np.max(abs(R_dense-phys.R)))
        checks.append(check(err < 1e-10,'dense_physical_R',err))
        v = rng.uniform(.01,.5,n)
        gamma = projected_variance(v,delays,nus,phys.c1)
        gamma_dense = np.einsum('imk,jmk,k->ij',U.conj(),U,v)
        err = float(np.max(abs(gamma-gamma_dense)))
        checks.append(check(err < 1e-10,'dense_nonuniform_Gamma',err))
        for group_delay in set(delays):
            ids = np.flatnonzero(np.asarray(delays)==group_delay)
            err = float(np.max(abs(gamma[np.ix_(ids,ids)]-
                                   v.sum()*phys.R[np.ix_(ids,ids)])))
            checks.append(check(err < 1e-10,'same_delay_nonuniform_moment',err))
        eig = np.linalg.eigvalsh(phys.R)
        checks.append(check(np.max(abs(phys.R-phys.R.conj().T))<1e-12 and
            np.max(abs(np.diag(phys.R)-1))<1e-12 and eig.min()>-1e-10,
            'physical_R_Hermitian_PSD',float(eig.min())))

    # Exactly exercise the reciprocal floor: first xbar is zero, so 1/vq=1e-12.
    n=32
    phys=Physics(n,[3,3],[.2,.27],3.7/(2*n),.017)
    c=Channel(n,phys.c1,phys.c2,phys.delays,phys.dopplers,
              np.array([.4+.2j,-.3+.1j]))
    y=rng.normal(size=n)+1j*rng.normal(size=n)
    pilot=np.zeros(n,complex)
    a=tf_base.scalar_joint(y,pilot,c,.25,iterations=1,record_states=True)
    b=tf_cgr.scalar_joint(y,pilot,c,.25,iterations=1,record_states=True)
    t=a['states'][0]
    checks.append(check(a['trace'][0]['gain_precision_floor'] and
        t['vq']==1e12,'actual_reciprocal_floor_active',float(t['vq'])))
    dh=(-t['alpha']*n*t['vx']/(c.p+1/t['vq'])*
        (t['physical_R']-np.eye(c.p))@t['hbar'])
    err=float(np.max(abs(b['gains']-a['gains']-dh)))
    checks.append(check(err<1e-10,'floored_common_state_delta',err))

    receipt = dict(status='synthetic_pass',source_sha256=generate_variants.EXPECTED,
        qualifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        detector_sha256=variants,block_source_sha256=tf_block.EXPECTED_BLOCK,
        checks=checks,archived_reference_runs=reference_runs,
        max_error=max(x['value'] for x in checks if x['check'] not in
            ('physical_delta_nonnegative','physical_R_Hermitian_PSD',
             'actual_reciprocal_floor_active') and
            isinstance(x['value'],float)))
    (out/'qualification.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(f"{len(checks)} synthetic checks passed")


if __name__ == '__main__':
    run(ARGS.out)
