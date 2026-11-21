"""Run E-3c on a nominal first-stage bank and an eta-specific EM bank."""

from types import FunctionType, SimpleNamespace
import time

import numpy as np

ETAS = (2, 4, 8)
ARMS = ("R0", "R1", "S-lo")


def grid(sbl, cap, eta):
    source = sbl.e3c.sbl.full_grid
    build = FunctionType(source.__code__, dict(source.__globals__, GRID_STEP=1 / eta))
    return build(cap)


def second_stage_receiver(main, nominal_grid):
    # Source: spectral_receiver.process_key via main_receiver._build_main_receiver.
    # Bind two banks and hash the first-round state because the frozen entry accepts one bank.
    source = main._receiver_bytes.decode("utf-8")
    replacements = (
        ("    delays_g, nus_g = grid", "    delays_g, nus_g = nominal_grid"),
        ("    Bs = sbl.columns(xt, delays_g, nus_g, c1, c2)",
         "    delays_em, nus_em = grid\n    Bs = sbl.columns(xt, delays_em, nus_em, c1, c2)"),
        ("sbl.candidate_union(top2, kept_delays, delays_g)",
         "sbl.candidate_union(top2, kept_delays, delays_em)"),
        ("    delays, dopplers = delays_g[cand2], nus_g[cand2]",
         "    delays, dopplers = delays_em[cand2], nus_em[cand2]"),
        ("        mean_v=float(np.mean(v)), n_candidates_stage2=int(len(cand2)),",
         """        first_round_sha256={name: e3c.array_sha(array) for name, array in dict(
            pilot_screen=cand1, support=g1_idx, gains=g1_mu, raw_app=dec1['raw_app'],
            raw_check_extrinsic=dec1['raw_check_extrinsic']).items()},
        mean_v=float(np.mean(v)), n_candidates_stage2=int(len(cand2)),"""),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError(f"Frozen SBL grid hook changed: {old}")
        source = source.replace(old, new)
    build = main._build_main_receiver
    bind = FunctionType(build.__code__, dict(build.__globals__, _receiver_bytes=source.encode("utf-8")))
    receiver = bind()
    receiver.__globals__["nominal_grid"] = nominal_grid
    return receiver


def process(sbl, projector, ctx, key, eta, *, arms=ARMS, iterations=100):
    started = time.process_time()
    cap = int(ctx.system.l_max_cap)
    nominal = grid(sbl, cap, 4)
    bank = nominal if eta == 4 else grid(sbl, cap, eta)
    receiver = second_stage_receiver(sbl.frozen_main, nominal)
    spectral = sbl.spectral
    geometry = {}

    def settings(v, sigma2, delays, dopplers, c1, smoke):
        result = spectral.arm_settings(v, sigma2, delays, dopplers, c1, smoke)
        blocks = result[3]
        geometry.update(
            screened_block_sizes=[len(block[0][0]) for block in blocks],
            screened_block_ranks=[int(np.linalg.matrix_rank(block[1], hermitian=True)) for block in blocks],
            screened_geometry_sha256=dict(delays=sbl.e3c.array_sha(delays),
                                          dopplers=sbl.e3c.array_sha(dopplers)))
        return result

    def fit(results, name, B, Y, beta0, gamma, _):
        return spectral.fit_sbl(results, name, B, Y, beta0, gamma, iterations)

    source = sbl.process_key
    namespace = dict(source.__globals__, GATE_ARMS=arms,
                     frozen_main=SimpleNamespace(process_main_key=receiver),
                     spectral=SimpleNamespace(REFINEMENT=spectral.REFINEMENT, arm_settings=settings, fit_sbl=fit))
    run = FunctionType(source.__code__, namespace, source.__name__, source.__defaults__)
    run.__kwdefaults__ = source.__kwdefaults__
    row = run(ctx, sbl.e3c.e3d.PilotCache(), bank, key, include_u2=False)
    delays, dopplers = bank
    block = dopplers[delays == 0]
    _, rank = projector.block_projector(block, ctx.system.N_total, .5)
    for arm in row["variants"].values():
        arm["frame_error"] = arm["info_errors"] > 0
        arm["sbl"]["max_iter"] = iterations
    return dict(row, eta=eta, dopplers_per_delay=len(block), grid_low_modes_per_delay=int(rank),
                grid_low_modes=int(rank) * (int(delays[-1]) + 1), **geometry,
                cpu_seconds=time.process_time() - started)
