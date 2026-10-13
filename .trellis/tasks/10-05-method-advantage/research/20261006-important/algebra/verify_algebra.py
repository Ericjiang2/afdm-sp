"""Tiny deterministic identities only; no production imports, RNG, or fitting."""
import cmath
from fractions import Fraction
import json
import math


def alpha(n, m, nu):
    x = m + nu
    return cmath.exp(1j * math.pi * (n - 1) * x / n) * math.sin(math.pi * x) / (n * math.sin(math.pi * x / n))


def alpha_sum(n, m, nu):
    return sum(cmath.exp(2j * math.pi * (m + nu) * j / n) for j in range(n)) / n


def weights(n, nu, cap):
    window = {m: alpha(n, m, nu) for m in range(-2, 3)}
    norm = math.sqrt(sum(abs(v) ** 2 for v in window.values()) + 1e-300)
    peak = max(abs(v) ** 2 for v in window.values())
    return {m: v / norm for m, v in window.items() if abs(m) <= cap and abs(v) ** 2 >= .01 * peak}


def coordinate(n, nu):
    return math.tan(math.pi / n) / math.tan(math.pi * nu / n)


def inverse_coordinate(n, y):
    return n / math.pi * math.atan(math.tan(math.pi / n) / y)


def scalar(n, nu):
    y = coordinate(n, nu)
    return weights(n, nu, 1)[0] / (1 - y * y)


def normalized_coefficients(n, nus, raw, cap=1):
    ws = [weights(n, nu, cap) for nu in nus]
    active = sorted(set().union(*ws))
    q = {m: sum(g * w.get(m, 0j) for g, w in zip(raw, ws)) for m in active}
    norm = math.sqrt(sum(abs(v) ** 2 for v in q.values()))
    return {m: v / norm for m, v in q.items()}


def moments(n, q):
    beta = {m: cmath.exp(1j * math.pi * m / n) * q[m] for m in (-1, 0, 1)}
    m0 = math.cos(math.pi / n) * (beta[-1] + beta[1]) / 2
    return [m0, math.cos(math.pi / n) * (beta[-1] - beta[1]) / 2, m0 - beta[0]]


def recover(n, mm):
    m0, m1, m2 = mm
    determinant = (m1 * m0.conjugate()).imag
    s = (m2 * m0.conjugate()).imag / determinant
    p = (m2 * m1.conjugate()).imag / determinant
    disc = math.sqrt(s * s - 4 * p)
    return sorted(inverse_coordinate(n, y) for y in ((s - disc) / 2, (s + disc) / 2)), determinant


def matrix(n, q):
    out = [[0j for _ in range(n)] for _ in range(n)]
    c2 = .1 / n ** 2
    for k, v in q.items():
        for column in range(n):
            row = (column + k) % n
            out[row][column] += v * cmath.exp(2j * math.pi * c2 * (row * row - column * column))
    return out


def det(a):
    a = [row[:] for row in a]
    value = 1 + 0j
    for j in range(len(a)):
        pivot = max(range(j, len(a)), key=lambda i: abs(a[i][j]))
        if pivot != j:
            a[j], a[pivot] = a[pivot], a[j]
            value = -value
        value *= a[j][j]
        for i in range(j + 1, len(a)):
            scale = a[i][j] / a[j][j]
            for k in range(j + 1, len(a)):
                a[i][k] -= scale * a[j][k]
    return value


result = dict(scope="unregistered lightweight deterministic algebra exploration; not formal scientific acceptance", production_imports=0,
              rng_calls=0, generator_calls=0, receiver_calls=0, decoder_calls=0, fitting_calls=0)
result["trig_vs_finite_geometric_sum_max_error"] = max(abs(alpha(n, m, nu) - alpha_sum(n, m, nu))
    for n in (4, 5, 6) for m in range(-2, 3) for nu in (.22, .29, .33, .42))
generic = []
for n in (4, 5):
    nus = [.29, .33]
    q = normalized_coefficients(n, nus, [1 + .2j, -.4 + .7j])
    recovered, determinant = recover(n, moments(n, q))
    generic.append(dict(N=n, dopplers=nus, active=sorted(q), recovered=recovered,
                        max_doppler_error=max(abs(a - b) for a, b in zip(nus, recovered)),
                        real_prony_determinant=determinant))
result["generic_recovery"] = generic

ys_a, ls_a = [Fraction(4), Fraction(9, 2)], [Fraction(1), Fraction(1)]
ys_b, ls_b = [Fraction(39, 10), Fraction(31, 7)], [Fraction(25, 37), Fraction(49, 37)]
exact_a = [sum(lam * y ** j for lam, y in zip(ls_a, ys_a)) for j in range(3)]
exact_b = [sum(lam * y ** j for lam, y in zip(ls_b, ys_b)) for j in range(3)]
assert exact_a == exact_b
case = []
qs = []
for ys, lambdas in ((ys_a, ls_a), (ys_b, ls_b)):
    nus = [inverse_coordinate(4, float(y)) for y in ys]
    raw = [float(lam) / scalar(4, nu) for lam, nu in zip(lambdas, nus)]
    q = normalized_coefficients(4, nus, raw)
    qs.append(q)
    case.append(dict(dopplers=sorted(nus), coordinate_order_dopplers=nus,
                     coordinate_order_raw_gains=[[v.real, v.imag] for v in raw],
                     coordinate_order_y=[str(v) for v in ys], coordinate_order_lambda=[str(v) for v in lambdas],
                     mu=sum(nus) / 2, delta=abs(nus[1] - nus[0]) / 2,
                     pdp_limits=[math.floor(67 * (1 + nu / 6)) for nu in nus],
                     normalized_atom_energy=sum(abs(v) ** 2 for v in q.values()),
                     transformed_prony_determinant=(moments(4, q)[1] * moments(4, q)[0].conjugate()).imag))
h_a, h_b = matrix(4, qs[0]), matrix(4, qs[1])
result["continuous_ambiguity_witness"] = dict(exact_moments=[str(x) for x in exact_a], cases=case,
    normalized_coefficient_max_difference=max(abs(qs[0][m] - qs[1][m]) for m in qs[0]),
    normalized_dense_H_max_difference=max(abs(h_a[i][j] - h_b[i][j]) for i in range(4) for j in range(4)),
    H_frobenius_norm=math.sqrt(sum(abs(v) ** 2 for row in h_a for v in row)))

n, nodes, atoms = 6, [.22, .28, .35, .42], [-2, -1, 0, 1]
w = [weights(n, nu, 2) for nu in nodes]
four = [[wj[m] for wj in w] for m in atoms]
four_sum = []
for m in atoms:
    row = []
    for nu in nodes:
        norm = math.sqrt(sum(abs(alpha_sum(n, k, nu)) ** 2 for k in range(-2, 3)))
        row.append(alpha_sum(n, m, nu) / norm)
    four_sum.append(row)
dt, ds = det(four), det(four_sum)
result["four_atom_full_spark_check"] = dict(N=n, dopplers=nodes, selected_atoms=atoms,
    actual_active=[sorted(v) for v in w], determinant_modulus=abs(dt),
    independent_geometric_sum_determinant_modulus=abs(ds), determinant_absolute_difference=abs(dt - ds))
assert result["trig_vs_finite_geometric_sum_max_error"] < 2e-14
assert max(x["max_doppler_error"] for x in generic) < 1e-10
assert result["continuous_ambiguity_witness"]["normalized_dense_H_max_difference"] < 2e-14
assert abs(dt) > 1e-10
print(json.dumps(result, indent=2, allow_nan=False))
