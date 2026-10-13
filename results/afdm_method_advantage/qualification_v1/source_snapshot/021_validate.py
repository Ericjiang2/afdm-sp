"""Deterministic tiny synthetic algebra check; no receiver/FER evidence."""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from profile_geometry import ProfileGeometry, channel_jacobian, realify
from test_profile_geometry import make_channel, moved

OUT = Path(__file__).resolve().parent
ch = make_channel(4)
pilot = np.array([.3+.1j, -.1+.2j, .2-.2j, .1+.3j])
# Toy even-parity (8,7) code, exhaustive 128 legal QPSK words, all I then all Q.
words = np.asarray([b for b in itertools.product((0, 1), repeat=8) if sum(b)%2 == 0])
data = ((1-2*words[:, :4])+1j*(1-2*words[:, 4:])) / np.sqrt(2)
x0 = pilot + data[0]
y = ch.apply(x0)
variance = .2
penalty = .1*np.eye(6)
fixed = ProfileGeometry(channel_jacobian(ch, x0), variance, penalty)
rows = []
for bits, d in zip(words, data):
    x = pilot+d
    r = realify(ch.apply(x)-y)
    geom = ProfileGeometry(channel_jacobian(ch, x), variance, penalty)
    aug = np.vstack((geom.a, geom.root))
    rhs = np.r_[-r/np.sqrt(variance), np.zeros(6)]
    direct = np.linalg.lstsq(aug, rhs, rcond=geom.rtol)[0]
    linear = float(geom.value(r))
    # Local nonlinear solve, NOT a globally minimized likelihood/correctness oracle.
    def nonlinear(step):
        return np.r_[realify(moved(ch, step).apply(x)-y)/np.sqrt(variance), geom.root@step]
    solved = least_squares(nonlinear, np.zeros(6), max_nfev=150, ftol=1e-10, xtol=1e-10, gtol=1e-10)
    rows.append(dict(bits=''.join(map(str,bits)), linear=linear, direct_linear=float(np.linalg.norm(aug@direct-rhs)**2), fixed_j=float(fixed.value(r)), nonlinear_local=float(np.sum(solved.fun**2)), nonlinear_success=bool(solved.success), nuisance_norm=float(np.linalg.norm(geom.nuisance_step(r)))))
err = max(abs(r['linear']-r['direct_linear']) for r in rows)
assert err < 1e-10
assert all(r['linear'] >= 0 for r in rows)
assert max(abs(r['fixed_j']-r['linear']) for r in rows) > .01
assert max(abs(r['nonlinear_local']-r['linear']) for r in rows) > .01
result = dict(scope='exhaustive synthetic 4-symbol even-parity code; no formal receiver frames, no FER or novelty claim', codewords=len(rows), real_observation_dimension=8, nuisance_dimension=6, max_linear_direct_error=err, max_candidate_j_vs_fixed_j_difference=max(abs(r['fixed_j']-r['linear']) for r in rows), max_local_nonlinear_vs_linear_difference=max(abs(r['nonlinear_local']-r['linear']) for r in rows), nonlinear_converged=sum(r['nonlinear_success'] for r in rows), rows=rows, source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'profile_geometry.py', OUT/'test_profile_geometry.py', OUT/'validate.py']})
(OUT/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('rows','source_sha256')}, indent=2))
