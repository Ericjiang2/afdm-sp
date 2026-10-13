"""Small deterministic mathematical diagnostics, not receiver FER experiments."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import sys
from unittest.mock import patch

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'experiments/sp_afdm_native_joint_20260921/src'
FROZEN = ROOT / 'experiments/sp_afdm_frozen_20260920/src'
sys.path[:0] = [str(NATIVE), str(FROZEN)]
import twofft
from physical import Channel, daft


def posterior(B, noise, tau):
    """Proper Gaussian covariance; positive prior prevents singular inversion."""
    return np.linalg.solve(np.eye(B.shape[1]) / tau + B.conj().T @ B / noise,
                           np.eye(B.shape[1]))


def dense_response(c, x):
    """Independent dense DFT/CPP construction used only as a verifier."""
    n = c.n
    k = np.arange(n)
    F = np.exp(-2j*np.pi*np.outer(k, k)/n)/np.sqrt(n)
    A = np.diag(np.exp(2j*np.pi*c.c2*k*k)) @ F @ np.diag(np.exp(2j*np.pi*c.c1*k*k))
    columns = []
    for delay, nu in zip(c.delays, c.dopplers):
        T = np.zeros((n, n), complex)
        for row in range(n):
            wrap = row-int(delay)
            cpp = np.exp(2j*np.pi*c.c1*(n*n+2*n*wrap)) if wrap < 0 else 1.
            T[row, wrap % n] = cpp*np.exp(2j*np.pi*row*nu/n)
        columns.append(A @ T @ A.conj().T @ x)
    return np.column_stack(columns)


def known_data_run(c, x, y, noise, damping=.3, iterations=1600):
    """Execute actual scalar_joint; replace only data factors by a delta law.

    Pilot=x and known d=0 is a diagnostic conditioning interface, not legal
    transmitted QPSK. It fixes the total input exactly and bypasses decoding.
    """
    z = np.zeros(c.n)
    def fixed_moments(prior, pd):
        return z.astype(complex), z.copy(), z.astype(complex)
    def fixed_marginal(likelihood, prior, pd):
        return np.zeros(2*c.n), np.zeros(2*c.n), z.astype(complex), z.copy()
    with patch.object(twofft, 'moments', fixed_moments), patch.object(twofft, 'marginal', fixed_marginal):
        return twofft.scalar_joint(y, x, c, noise, iterations=iterations,
                                   damping=damping, record_states=True)


def run_all():
    rng = np.random.default_rng(20261002)
    records = []
    for p in [1, 2]:
        for noise in [.05, .5, 5.]:
            for scale in [.1, 1., 10.]:
                n = 16
                c = Channel(n, .137, .019, np.arange(p)+1,
                            np.arange(p)*.71+.13, np.full(p, .1+.03j))
                x = scale*(rng.normal(size=n)+1j*rng.normal(size=n))/np.sqrt(2)
                B = c.regressors(x)
                y = B @ np.full(p, .7+.1j) + .03*(rng.normal(size=n)+1j*rng.normal(size=n))
                G = B.conj().T @ B
                rhs = B.conj().T @ y
                ce, info = twofft.time_refine(y, x, np.zeros(n), np.zeros(n), c.delays,
                    c.dopplers, c.gains, c.c1, c.c2, noise, rounds=0)
                # time_refine sorts by equal energy; compare its own output order.
                Bce = ce.regressors(x)
                ce_expected = np.linalg.solve(Bce.conj().T@Bce+noise*np.eye(p), Bce.conj().T@y)
                expected = np.linalg.solve(G+noise*p*np.eye(p), rhs)
                out = known_data_run(c, x, y, noise)
                h = out['gains']
                st = out['states'][-1]
                Y = daft(y, c.c1, c.c2, True)
                Bt = twofft.TimePathOps(c).responses_time(daft(x, c.c1,c.c2,True))
                records.append(dict(p=p, noise=noise, scale=scale,
                    ce_actual_error=float(np.linalg.norm(ce.gains-ce_expected)),
                    joint_actual_error=float(np.linalg.norm(h-expected)),
                    joint_stationarity=float(np.linalg.norm((G+noise*p*np.eye(p))@h-rhs)),
                    onsager_residual=float(np.linalg.norm(noise*st['s']-(Y-Bt@h))),
                    ce_joint_gap=float(np.linalg.norm(np.linalg.solve(G+noise*np.eye(p),rhs)-expected)),
                    variance=float(st['vh']), precision_floor=any(t['gain_precision_floor'] for t in out['trace'])))
    n=16
    geometry = []
    for label, delays, nus, xt in [
        ('physical_duplicate', [1,1], [.23,.23], np.ones(n,complex)),
        ('physical_near_duplicate', [1,1], [.23,.23001], np.ones(n,complex)),
        ('physical_orthogonal', [1,1], [.23,1.23], np.ones(n,complex)),
        ('physical_distinct_delay_near_response', [1,2], [.23,.23001], np.ones(n,complex)),
    ]:
        # c1 satisfies 2*N*c1 integer: CPP is legal and nontrivial in other cases.
        c=Channel(n, 3/(2*n), .017, delays, nus, [.1,.2])
        x=daft(xt,c.c1,c.c2)
        B=c.regressors(x)
        C=posterior(B,.5,.5)
        eig,Q=np.linalg.eigh(B.conj().T@B)
        null=Q[:,0]
        perm=np.array([1,0])
        Cp=posterior(B[:,perm],.5,.5)
        Qr,_=np.linalg.qr(rng.normal(size=(2,2))+1j*rng.normal(size=(2,2)))
        Cr=posterior(B@Qr,.5,.5)
        actual=known_data_run(c,x,B@np.array([.7,.4]),.5)
        geometry.append(dict(label=label, gram_eigenvalues=eig.tolist(),
            covariance_eigenvalues=np.linalg.eigvalsh(C).tolist(),
            weakest_direction_variance=float(np.vdot(null,C@null).real),
            scalar_variance_actual=float(actual['gain_variance'][0]),
            best_scalar_fro_error=float(np.linalg.norm(C-np.trace(C)/2*np.eye(2))),
            dense_error=float(np.max(abs(B-dense_response(c,x)))),
            time_error=float(np.max(abs(B-daft(twofft.TimePathOps(c).responses_time(daft(x,c.c1,c.c2,True)),c.c1,c.c2)))),
            permutation_error=float(np.max(abs(Cp-C[np.ix_(perm,perm)]))),
            coordinate_error=float(np.max(abs(Cr-Qr.conj().T@C@Qr)))))
    # Genuinely nontrivial CPP, including fractional Doppler.
    c=Channel(15,.137,.019,[2,4],[.23,-.71],[.2,.3])
    x=rng.normal(size=15)+1j*rng.normal(size=15)
    cpp_error=float(np.max(abs(c.regressors(x)-dense_response(c,x))))
    B=np.ones((8,2),complex)
    y=np.full(8,2.)
    ce=np.linalg.solve(B.conj().T@B+.5*np.eye(2),B.conj().T@y)
    joint=np.linalg.solve(B.conj().T@B+np.eye(2),B.conj().T@y)
    damping=[]
    c=Channel(16,.137,.019,[1,2],[.23,-.71],[.1,.2])
    x=rng.normal(size=16)+1j*rng.normal(size=16)
    Bp=c.regressors(x); yp=Bp@np.array([.7,.4]); target=np.linalg.solve(Bp.conj().T@Bp+np.eye(2),Bp.conj().T@yp)
    for d in [.1,.3,.7]:
        out=known_data_run(c,x,yp,.5,damping=d)
        damping.append(dict(damping=d,error=float(np.linalg.norm(out['gains']-target))))
    return dict(scope='small CPU conditional mathematical diagnostics; no FER/no decoder',
        config=dict(seed=20261002,iterations=1600,default_damping=.3),
        actual_known_data=records,geometry=geometry,cpp_dense_error=cpp_error,damping=damping,
        artificial=dict(ce=ce.real.tolist(),joint=joint.real.tolist(),
            covariance_eigenvalues=np.linalg.eigvalsh(posterior(B,.5,.5)).tolist()))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=run_all()
    paths=[Path(__file__),NATIVE/'twofft.py',FROZEN/'physical.py',FROZEN/'messages.py']
    result['provenance']=dict(argv=sys.argv,python=sys.version,executable=sys.executable,
        platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,
        sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(output=str(args.out),cases=len(result['actual_known_data']),
        max_joint_error=max(x['joint_actual_error'] for x in result['actual_known_data']))))

if __name__=='__main__':main()
