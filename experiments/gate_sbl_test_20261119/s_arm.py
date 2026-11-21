"""Phase 1 SBL arms on the frozen E-3c receiver and initial candidate grid."""

from functools import lru_cache
from hashlib import sha256
from importlib import import_module
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import numpy as np

EXPERIMENTS = Path(__file__).resolve().parents[1]
UNIFIED = 'unified_cov_prospective_20261119'
SCREEN = 'gate_screen_20261119'
ARM_NAMES = ('R0', 'S-lo', 'G')
PROJECTOR_ATOL = 1e-12
S_PROJECTOR_EQUAL_ATOL = 1e-8


def frozen_module(directory, name, digest):
    path = EXPERIMENTS / directory / f'{name}.py'
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'Frozen source SHA-256 mismatch: {path}')
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    module = import_module(name)
    if Path(module.__file__).resolve() != path:
        raise RuntimeError(f'Unexpected frozen import for {name}: {module.__file__}')
    return module


@lru_cache(maxsize=1)
def gate_source():
    return frozen_module(SCREEN, 'gate', 'e7b6052af8158d35b8978fe862d19df1eaf0cadddfa78dbddbce9be0c8a19a73')


@lru_cache(maxsize=1)
def receiver():
    frozen_module(UNIFIED, 'projector', '600da7cdd837452c8df049fd19745f9fce441b5b30a234a7364d4c908ac4b4e8')
    return frozen_module(UNIFIED, 'sbl', 'be8afdbb11c278b182185d21ca3e7e7e92d23adf405bd97b2beb52c8b8658b80')


def gate_projector(gram, dirichlet, u, ridge):
    # Source: gate.py::compare_block at bb5ad661; expose its selected subspace because the frozen function returns only census scalars.
    gate = gate_source()
    size = len(dirichlet)
    if size == 1:
        return np.zeros_like(dirichlet), 0
    if size == 2:
        contrast = gate.pair_contrast(dirichlet)
        if not gate.floor_pair(gram, u * dirichlet, ridge, contrast):
            return np.zeros_like(dirichlet), 0
        return np.outer(contrast, contrast.conj()), 1
    values, modes = np.linalg.eigh(dirichlet)
    protected = modes[:, values < 1.]
    q0 = u * dirichlet + ridge * np.eye(size)
    q1 = q0 + gate.hermitian(gram)
    difference = protected.conj().T @ (2 * np.linalg.solve(q1, protected)
                                       - np.linalg.solve(q0, protected))
    eig, vectors = np.linalg.eigh(gate.hermitian(difference))
    selected = protected @ vectors[:, eig > 0.]
    return selected @ selected.conj().T, selected.shape[1]


def block_census(projector, gate_rank, low_projector, low_rank, *, equality_atol=PROJECTOR_ATOL):
    overlap = float(np.trace(projector @ low_projector).real)
    distance = float(np.linalg.norm(projector - low_projector, ord='fro'))
    return dict(size=len(projector), gate_rank=gate_rank, s_lo_rank=low_rank,
                overlap_trace=overlap,
                gate_in_s_lo=abs(overlap - gate_rank) <= PROJECTOR_ATOL,
                projectors_equal=gate_rank == low_rank and distance <= equality_atol)


def initial_gate(B, delays, dopplers, blocks, u, sigma2):
    from physical import dkernel

    n = B.shape[0]
    ridge = sigma2 + u / n
    penalty = np.zeros((B.shape[1], B.shape[1]), dtype=complex)
    census = []
    for ix, _, low, _ in blocks:
        indices = ix[0][:, 0]
        nu = dopplers[indices]
        columns = B[:, indices]
        dirichlet = gate_source().hermitian(dkernel(nu[None, :] - nu[:, None], n))
        projector, rank = gate_projector(columns.conj().T @ columns, dirichlet, u, ridge)
        penalty[ix] = u * projector
        census.append(dict(delay=int(delays[indices[0]]), **block_census(
            projector, rank, low, int(np.rint(np.trace(low).real)),
            equality_atol=S_PROJECTOR_EQUAL_ATOL)))
    return penalty, census


def retained_penalty_fro(gate_penalty, low_penalty, retained):
    """Measure the difference of the applied initial ridges on S-lo's active grid."""
    ix = np.ix_(retained, retained)
    return float(np.linalg.norm(gate_penalty[ix] - low_penalty[ix], ord='fro'))


def run_key(ctx, grid, key, *, replace_with_low=False):
    """Score the three Phase 1 arms, allowing archived keys only for G2 reduction."""
    sbl = receiver()
    if replace_with_low:
        allowed = (key[0] in ('G', 'U') and key[1] == 300
                   and key[2] in sbl.e3c.lib.SNRS and key[3] in range(4400, 4600))
    else:
        allowed = key in sbl.e3c.lib.smoke_keys()
    if not allowed:
        raise ValueError(f'Phase 1 SBL key disallowed: {key}, replace_with_low={replace_with_low}')
    started = time.process_time()
    spectral = sbl.spectral
    gate_census = None
    gate_seconds = 0.0
    slo_retained = None

    def settings(v, sigma2, delays, dopplers, c1, smoke):
        nonlocal arm_inputs
        specs, matrices, ridges, blocks, census = spectral.arm_settings(v, sigma2, delays, dopplers, c1, smoke)
        ranks = [int(np.rint(np.trace(block[2]).real)) for block in blocks]
        census = dict(census, projector_rank=sum(ranks), projector_nonempty_blocks=sum(rank > 0 for rank in ranks))
        arm_inputs = matrices, ridges, delays, dopplers, blocks, specs['R1']['sum_vec'], sigma2
        return specs, matrices, ridges, blocks, census

    def fit(results, name, B, Y, beta0, gamma, max_iter):
        nonlocal gate_census, gate_seconds, slo_retained
        if name != 'R1':
            result = spectral.fit_sbl(results, name, B, Y, beta0, gamma, max_iter)
            if name == 'S-lo':
                slo_retained = result['idx']
            return result
        # The frozen schedule pre-fits R1 for T0. These arms do not use R1's
        # fit. The hook gets the exact initial dictionary before any arm fit.
        begin = time.process_time()
        matrices, ridges, delays, dopplers, blocks, u, sigma2 = arm_inputs
        if replace_with_low:
            ridges['G'] = ridges['S-lo']
            matrices['G'] = matrices['S-lo']
        else:
            ridges['G'], gate_census = initial_gate(B, delays, dopplers, blocks, u, sigma2)
            matrices['G'] = matrices['R1'] + ridges['G']
        gate_seconds = time.process_time() - begin

    arm_inputs = None
    run = sbl.frozen_main.process_main_key
    namespace = dict(run.__globals__, main_budgets=lambda _: (100,), MAIN_ARMS={100: ARM_NAMES},
                     arm_settings=settings, fit_sbl=fit, REFINEMENT=dict(spectral.REFINEMENT, G='R1'),
                     time=SimpleNamespace(perf_counter=time.process_time))
    row = FunctionType(run.__code__, namespace)(ctx, sbl.e3c.e3d.PilotCache(), grid, key)
    row['variants'] = row.pop('budgets')['100']['variants']
    for score in row['variants'].values():
        score['decoded'] = score['fer'] == 0
    if gate_census is not None:
        row['gate_census'] = gate_census
        row['projectors_equal'] = all(block['projectors_equal'] for block in gate_census)
        ridges = arm_inputs[1]
        row['slo_retained_penalty_fro'] = retained_penalty_fro(ridges['G'], ridges['S-lo'], slo_retained)
    row['seconds']['gate_construction'] = gate_seconds
    row['seconds']['cpu_total'] = time.process_time() - started
    return row
