"""Registered deterministic checks against the actual frozen physical columns."""
from fractions import Fraction

import numpy as np

from experiments.afdm_efficient_information.prior_likelihood import pdp_distribution, system_for
from experiments.afdm_higher_order_information.prior import geometry
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain
from experiments.afdm_shared_channel_20261004.common import dump
from .core import conditional_contrast


def coordinate(n, nu):
    return np.tan(np.pi/n)/np.tan(np.pi*nu/n)


def inverse_coordinate(n, y):
    return n/np.pi*np.arctan(np.tan(np.pi/n)/np.asarray(y))


def moments(n, q):
    beta = np.exp(1j*np.pi*np.array([-1, 0, 1])/n)*q
    m0 = np.cos(np.pi/n)*(beta[0]+beta[2])/2
    return np.array([m0, np.cos(np.pi/n)*(beta[0]-beta[2])/2, m0-beta[1]])


def recover(n, values, rtol=1e-12):
    """Qualify the real Prony system before division; never regularize it.

    The fixed relative cutoff is a numerical admission rule, not an alternative
    identifiability theorem. Rejected near-phase cases remain unresolved.
    """
    values = np.asarray(values, complex)
    if (values.shape != (3,) or not np.isfinite(values).all()
            or not isinstance(n, int) or n < 3 or not np.isfinite(rtol) or not 0 < rtol < 1):
        raise ValueError('three finite moments, N>=3 and a relative tolerance required')
    m0, m1, m2 = values
    determinant = float((m1*m0.conjugate()).imag)
    scale = float(abs(m0)*abs(m1))
    matrix = np.array([[m1.real, -m0.real], [m1.imag, -m0.imag]])
    singular = np.linalg.svd(matrix, compute_uv=False)
    if (not np.isfinite(determinant) or not np.isfinite(scale) or scale == 0
            or abs(determinant) <= rtol*scale or singular[-1] <= rtol*singular[0]):
        raise ValueError('exceptional or numerically near-singular real-phase Prony system')
    s = (m2*m0.conjugate()).imag/determinant
    p = (m2*m1.conjugate()).imag/determinant
    discriminant = s*s-4*p
    if not np.isfinite([s, p, discriminant]).all() or discriminant <= 0:
        raise ValueError('Prony roots are not distinct and real')
    nodes = np.array([(s-np.sqrt(discriminant))/2, (s+np.sqrt(discriminant))/2])
    if not np.isfinite(nodes).all() or np.any(nodes <= 0):
        raise ValueError('Prony roots must be finite positive branch coordinates')
    recovered = np.sort(inverse_coordinate(n, nodes))
    if not np.isfinite(recovered).all() or np.any(recovered <= .22) or np.any(recovered >= .42):
        raise ValueError('Prony Dopplers leave the declared open common-atom branch (.22,.42)')
    lambda0 = (m1-nodes[1]*m0)/(nodes[0]-nodes[1])
    coefficients = np.array([lambda0, m0-lambda0])
    reconstructed = np.array([sum(coefficients*nodes**j) for j in range(3)])
    residual = float(np.max(abs(reconstructed-values)))
    relative_residual = residual/float(np.max(abs(values)))
    if not np.isfinite(relative_residual) or relative_residual > 10*rtol:
        raise ValueError('Prony moment reconstruction exceeds the fixed numerical tolerance')
    return recovered, dict(determinant=determinant, determinant_scale=scale,
                           relative_determinant=abs(determinant)/scale, rtol=rtol,
                           K=matrix.tolist(), K_condition=float(singular[0]/singular[-1]),
                           nodes=nodes.tolist(), reconstruction_residual=residual,
                           relative_reconstruction_residual=relative_residual,
                           branch=[.22, .42], branch_endpoints='open')


def c2_derivative(mu, tau, raw):
    raw = np.asarray(raw, complex)
    if raw.shape != (2,) or raw.sum() == 0:
        raise ValueError('fixed gains require a nonzero leading mode')
    xi = np.tan(np.pi*mu/4)
    k = 2*np.pi*tau*(1+xi*xi)/(1+2*xi*xi+5*xi**4)*np.array([1+3*xi*xi, -(1-xi*xi)])
    return ((raw[1]-raw[0])/raw.sum()).imag*k


def calculate(output):
    probes = 0
    rows = []

    def actual(n, mu, delta):
        nonlocal probes
        probes += 1
        return geometry(system_for(n), mu, delta)

    def save(name, arrays, evidence, passed):
        with (output/(name+'.npz')).open('xb') as handle:
            np.savez_compressed(handle, **arrays)
        row = dict(check=name, passed=bool(passed), **evidence)
        dump(output/(name+'.json'), row)
        rows.append(row)

    for mu in (.27, .31, .35):
        for label, raw in [('generic', np.array([1+.2j, -.4+.7j])),
                           ('real_ratio', np.array([1., .7]))]:
            analytic = c2_derivative(mu, 1., raw)
            derivatives = []
            for step in (1e-5, 5e-6):
                geo = actual(4, mu, step)
                gp = normalize_gain(raw[None, :], geo['gram'])
                gm = normalize_gain(raw[::-1][None, :], geo['gram'])
                hp, hm = gp@geo['g0'].T, gm@geo['g0'].T
                derivatives.append((conditional_contrast(hp)-conditional_contrast(hm))[0]/(2*step))
            error = float(np.max(abs(np.asarray(derivatives)-analytic)))
            save(f'derivative_{mu}_{label}', dict(raw=raw, analytic=analytic, finite_difference=derivatives),
                 dict(mu=mu, gain_case=label, max_absolute_error=error,
                      tolerance=2e-7, steps=[1e-5, 5e-6]), error < 2e-7)

    for n in (4, 5):
        geo = actual(n, .31, .02)
        raw = np.array([1+.2j, -.4+.7j])
        gain = normalize_gain(raw[None, :], geo['gram'])[0]
        active = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
        q = geo['weights'][active]@gain
        recovered, qualification = recover(n, moments(n, q))
        error = float(np.max(abs(recovered-[.29, .33])))
        save(f'prony_N{n}', dict(q=q, moments=moments(n, q), recovered=recovered),
             dict(N=n, atom_ids=active.tolist(), doppler_error=error,
                  prony_qualification=qualification, tolerance=1e-10), error < 1e-10 and len(active) == 3)

    ys = [[Fraction(4), Fraction(9, 2)], [Fraction(39, 10), Fraction(31, 7)]]
    ls = [[Fraction(1), Fraction(1)], [Fraction(25, 37), Fraction(49, 37)]]
    exact = [[sum(coefficient*y**j for coefficient, y in zip(lam, nodes)) for j in range(3)]
             for nodes, lam in zip(ys, ls)]
    h_all, q_all, case_rows, case_arrays = [], [], [], {}
    for index, (nodes, lam) in enumerate(zip(ys, ls)):
        nu = inverse_coordinate(4, np.asarray(nodes, float))
        order = np.argsort(nu)
        nu, lam = nu[order], np.asarray(lam, float)[order]
        geo = actual(4, float(nu.mean()), float(np.diff(nu)[0]/2))
        active = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
        w = geo['weights'][active]
        scalar = w[1]/(1-coordinate(4, nu)**2)
        raw = lam/scalar
        pdp_law = pdp_distribution(4, float(nu.mean()), float(np.diff(nu)[0]/2))
        pdp = np.array([1., 10**(-1/40)])
        support = np.flatnonzero(np.all(np.isclose(pdp_law['pdp'], pdp, atol=1e-14, rtol=0), axis=1))
        z = raw/np.sqrt(pdp)
        gains = normalize_gain((z*np.sqrt(pdp))[None, :], geo['gram'])[0]
        q = w@gains
        system = system_for(4)
        h = system.gen_h_daft(q, np.zeros(3, int), np.array([-1, 0, 1]))
        h_all.append(h)
        q_all.append(q)
        case_arrays.update({f'case{index}_'+key: value for key, value in
                           dict(dopplers=nu, raw=raw, pdp=pdp, gaussian_direction=z,
                                gains=gains, gram=geo['gram'], q=q, H=h).items()})
        case_rows.append(dict(dopplers=nu.tolist(), mu=float(nu.mean()),
                              delta=float(np.diff(nu)[0]/2), pdp_limits=pdp_law['limits'].tolist(),
                              pdp_support_mass=float(pdp_law['weights'][support].sum())))
    error = float(np.max(abs(h_all[0]-h_all[1])))
    save('actual_same_H_counterexample', case_arrays,
         dict(exact_moments=[str(x) for x in exact[0]], exact_equal=exact[0] == exact[1],
              cases=case_rows, max_H_difference=error, tolerance=3e-13,
              H_norms=[float(np.linalg.norm(h)) for h in h_all]),
         exact[0] == exact[1] and error < 3e-13 and all(r['pdp_support_mass'] > 0 for r in case_rows))

    for n in (16, 64, 1024):
        nodes = np.array([.27, .31, .35, .39])
        system = system_for(n)
        columns = []
        for nu in nodes:
            geo = actual(n, float(nu), 0.)
            columns.append(geo['weights'][:5, 0])
        w = np.column_stack(columns)
        atoms = np.array([-2, -1, 0, 1])
        alpha = np.array([[system.dirichlet_alpha(int(m), float(nu), n) for nu in nodes]
                          for m in range(-2, 3)])
        norm = np.sqrt(np.sum(abs(alpha)**2, axis=0)+1e-300)
        a = np.exp(2j*np.pi*atoms/n)
        z = np.exp(2j*np.pi*nodes/n)
        predicted = (1-np.exp(2j*np.pi*nodes))[None, :]/(n*norm[None, :]*(1-a[:, None]*z[None, :]))
        selected = w[:4]
        identity_error = float(np.max(abs(selected-predicted)))
        singular = np.linalg.svd(selected, compute_uv=False)
        # Direct finite Fourier sum is an independent Dirichlet identity check.
        direct = np.array([[np.mean(np.exp(2j*np.pi*(m+nu)*np.arange(n)/n)) for nu in nodes]
                           for m in range(-2, 3)])
        sum_error = float(np.max(abs(alpha-direct)))
        save(f'four_atom_N{n}', dict(actual=selected, predicted=predicted, singular=singular,
                                    direct_alpha=direct, alpha=alpha),
             dict(N=n, nodes=nodes.tolist(), atoms=atoms.tolist(), identity_error=identity_error,
                  finite_sum_error=sum_error, rank=int(np.linalg.matrix_rank(selected)),
                  determinant_modulus=float(abs(np.linalg.det(selected))), tolerance=2e-12),
             np.all(selected != 0) and np.linalg.matrix_rank(selected) == 4
             and identity_error < 2e-12 and sum_error < 2e-12)
    result = dict(checks=rows, all_passed=all(r['passed'] for r in rows), geometry_probes=probes,
                  new_observations=0, receiver_calls=0, decoder_calls=0,
                  scope='deterministic actual-physical identities; no power or receiver claim')
    dump(output/'geometry_checks.json', result)
    if not result['all_passed']:
        raise AssertionError('deterministic checks failed; every check retained in geometry_checks.json')
    return result
