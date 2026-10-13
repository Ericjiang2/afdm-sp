"""Deterministic algebra checks only; no project receiver or communication simulation."""
import cmath
import json
import math
from pathlib import Path


def coefficient(n, nu, q):
    return sum(cmath.exp(2j * math.pi * (nu-q) * t / n) for t in range(n)) / n


def integer_operator(n, delay, q, c1, c2):
    step = round(2*n*c1)
    out = [[0j]*n for _ in range(n)]
    for col in range(n):
        row = (col + delay*step + q) % n
        phase = -c1*delay**2 + c2*(row**2-col**2)-delay*col/n
        out[row][col] = cmath.exp(2j*math.pi*phase)
    return out


def full_operator(n, delay, nu, c1, c2):
    out = [[0j]*n for _ in range(n)]
    for row in range(n):
        for col in range(n):
            kernel = coefficient(n, nu+2*n*c1*delay, (row-col) % n)
            phase = -c1*delay**2+c2*(row**2-col**2)-delay*col/n
            out[row][col] = kernel*cmath.exp(2j*math.pi*phase)
    return out


def run():
    n = 16
    c1, c2 = 5/(2*n), (math.sqrt(2)-1)/(2*n*n)
    cases = []
    for delay in (0, 2):
        for nu in (-2.5, -0.1, 0., 1.37, 2.5):
            exact = full_operator(n, delay, nu, c1, c2)
            approx = [[0j]*n for _ in range(n)]
            for q in range(n):
                atom = integer_operator(n, delay, q, c1, c2)
                cq = coefficient(n, nu, q)
                for row in range(n):
                    for col in range(n):
                        approx[row][col] += cq*atom[row][col]
            relative = math.sqrt(sum(abs(exact[r][c]-approx[r][c])**2
                                     for r in range(n) for c in range(n))/n)
            assert relative < 1e-12, (delay, nu, relative)
            cases.append(dict(n=n, delay=delay, nu=nu, relative_frobenius_error=relative))
    table = []
    for eps in (0., .1, .25, .5):
        row = dict(epsilon=eps)
        for width in (1, 2, 4, 8):
            row[str(width)] = max(0., 1-sum(abs(coefficient(1024, eps, q))**2
                                           for q in range(-width, width+1)))
        table.append(row)
    # Nested orthogonal Fourier-coordinate subspaces. No channel-estimation claim.
    truth = [complex((j+1)/10, (-1)**j/20) for j in range(8)]
    domain, support = range(6), range(3)
    estimate = [truth[j]+(.03-.02j) if j in support else 0j for j in range(8)]
    e_domain = sum(abs(truth[j])**2 for j in range(8) if j not in domain)
    e_support = sum(abs(truth[j])**2 for j in domain if j not in support)
    e_gain = sum(abs(truth[j]-estimate[j])**2 for j in support)
    e_total = sum(abs(truth[j]-estimate[j])**2 for j in range(8))
    split_error = abs(e_total-e_domain-e_support-e_gain)
    assert split_error < 1e-12
    # Unit-Frobenius rank-one errors; p is one right singular vector or orthogonal.
    # Both have tr(E V E^H)=0.5 for V=0.5 I, yet ||E p||^2 is 1 versus 0.
    risk_example = dict(frobenius_squared=[1., 1.], pilot_response_error=[1., 0.],
                        data_error_for_V_half_I=[.5, .5], total=[1.5, .5])
    return dict(scope='deterministic finite-block algebra, not project simulation',
                python_standard_library_only=True, cases=cases,
                tail_energy_table_N1024=table,
                three_level_projection_identity_absolute_error=split_error,
                equal_frobenius_different_SP_risk_example=risk_example)


if __name__ == '__main__':
    result = run()
    target = Path(__file__).with_name('finite_fourier_results.json')
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(dict(status='PASS', output=str(target),
                         max_relative_operator_error=max(x['relative_frobenius_error']
                                                         for x in result['cases'])),
                     ensure_ascii=False))
