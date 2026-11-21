#!/usr/bin/env python
"""E3c controls. Run only after source freeze; gate/smoke are engineering checks."""
from __future__ import annotations
import time
IMPORT_START = time.perf_counter()
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3c_lib as lib
import e3c_arms as arms
import e3_driver as e3d
import offgrid_refine as ref
import sbl_rx as sbl
gd, crb, p1ctx = e3d.gd, e3d.crb, e3d.p1ctx


def array_sha(a):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def geometry_diagnostics(B, Q, gamma, gains, delays, dopplers):
    gram = B.conj().T @ B
    singular = np.linalg.svd(B, compute_uv=False)
    eig = np.linalg.eigvalsh(Q)
    norms = np.sqrt(np.diag(gram).real)
    coherence = np.abs(gram) / np.maximum(norms[:, None] * norms[None, :], np.finfo(float).tiny)
    np.fill_diagonal(coherence, 0.)
    # Eigenvalues can be zero for a rank deficient data operator; avoid nonfinite JSON.
    pairs = []
    for j in range(len(delays)):
        for k in range(j+1, len(delays)):
            if delays[j] != delays[k]:
                continue
            cross = gamma[j, k]
            phase = cross / abs(cross) if abs(cross) else 1.+0j
            u = np.array([phase, 1.]) / np.sqrt(2.)
            z = np.array([-phase, 1.]) / np.sqrt(2.)
            sub = gamma[np.ix_([j,k],[j,k])]
            pairs.append(dict(indices=[j,k], dnu=float(abs(dopplers[j]-dopplers[k])), coherence=float(coherence[j,k]),
                              sum_penalty=float(np.vdot(u, sub @ u).real), contrast_penalty=float(np.vdot(z, sub @ z).real)))
    return dict(operator_rank=int(np.linalg.matrix_rank(B)), operator_singular_values=singular.tolist(),
                operator_cond=(float(singular[0]/singular[-1]) if singular[-1] > 0 else None),
                gain_Q_eigenvalues=eig.tolist(), gain_Q_cond=float(np.linalg.cond(Q)),
                max_coherence=float(coherence.max()), uncertainty_gain_penalty=float(np.vdot(gains, gamma @ gains).real),
                same_delay_pairs=pairs)


def score_stage(ctx, obs, check, tp, truth, dl, dn, gains, n):
    _, dec, td, tc = e3d.detect_decode(ctx, obs, e3d.make_channel(ctx, n, dl, dn, gains), check)
    error = int(gd.score(ctx, dec['decoded'], truth))
    return dict(info_errors=error, fer=int(error > 0), decoded_sha256=gd.bits_sha(dec['decoded']),
                nmse=float(crb.channel_nmse(dict(delays=dl, dopplers=dn, gains=gains), tp, n)),
                n_atoms=int(len(dl)), detect_seconds=td, decode_seconds=tc, gain_sha256=array_sha(gains))


def process_key(ctx, cache, grid, obs, data_true_af, truth, meta, phase_clock=None, ongrid_reuse=None):
    """One row.  Stage 1, round 1, the shared candidate set and the four stage-2 SBL runs are the E-3 process_key lines; the refinement is new.
    ``ongrid_check`` (gate / smoke only) additionally runs round 2 on the unrefined SBL atoms (E-3's on-grid result) and records it; its time is
    excluded from every ``total``."""
    from messages import moments
    from physical import daft
    t_all = time.perf_counter()
    phase_clock = phase_clock if phase_clock is not None else {}
    phase_clock["phase"] = "shared stage1/round1"
    s = ctx.system
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    pd = 1 - s.rho
    sigma2 = float(obs['sigma2'])
    delays_g, nus_g = grid
    tp = e3d.truth_paths(truth)
    true_delays = set(tp['delays'])
    sec = {}
    Y = daft(obs['y'], c1, c2, True)
    # ---- stage 1: pilot-only SBL (as E-3)
    t = time.perf_counter()
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    sec['stage1_screen'] = time.perf_counter() - t
    t = time.perf_counter()
    r1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (sigma2 + pd), Gamma=None)
    g1_idx, g1_mu, g1_e = sbl.select_output(cand1[r1['idx']], r1['mu'])
    sec['stage1_sbl'] = time.perf_counter() - t
    ch1 = e3d.make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    # ---- round 1 (as E-3)
    det1, dec1, t_det, t_dec = e3d.detect_decode(ctx, obs, ch1, None)
    sec['round1_detect'], sec['round1_decode'] = t_det, t_dec
    mu_d, v, _ = moments(np.clip(dec1['raw_app'], -20, 20), pd)
    check = np.clip(dec1['raw_check_extrinsic'], -20, 20)
    err1 = gd.score(ctx, dec1['decoded'], truth)
    # ---- stage 2 shared candidate set (as E-3)
    t = time.perf_counter()
    xt_soft = e3d.self_xt(obs['pilot'] + mu_d, c1, c2)
    Bs = sbl.columns(xt_soft, delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(x) for x in delays_g[g1_idx]), delays_g)
    cd, cn = delays_g[cand2], nus_g[cand2]
    sec['stage2_screen'] = time.perf_counter() - t
    mean_v = float(np.mean(v))
    beta0_soft = 1.0 / (sigma2 + mean_v)
    row = dict(meta, sigma2=sigma2,
               truth=dict(delays=tp['delays'], dopplers=tp['dopplers'], gains=[[float(g.real), float(g.imag)] for g in tp['gains']]),
               stage1=dict(n_candidates=int(len(cand1)), iterations=r1['iterations'], converged=r1['converged'], n_final=r1['n_final'], beta=r1['beta'],
                           jitter_events=r1['jitter_events'], atoms=e3d.atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                           nmse=float(crb.channel_nmse(dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu), tp, n))),
               round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])), decoded_sha256=gd.bits_sha(dec1['decoded']),
                           ldpc_iters=int(dec1['iterations'])),
               mean_v=mean_v, n_candidates_stage2=int(len(cand2)), kept_delays_stage1=int(len(set(int(x) for x in delays_g[g1_idx]))), variants={})
    vo = arms.oracle_variance(data_true_af, mu_d, pd)
    row['calibration'] = arms.calibration(mu_d, v, data_true_af, pd)
    row['power'] = dict(label_rho=meta['rho'], e_rho=meta['rho'], system_rho=float(s.rho), p_d=float(pd),
                        physical_to_internal_scale=float(np.sqrt(2 * (1-meta['rho']))),
                        pilot_power=float(np.mean(np.abs(obs['pilot'])**2)), true_data_power=float(np.mean(np.abs(data_true_af)**2)))
    row['input_sha256'] = {k: array_sha(a) for k, a in dict(y=obs['y'], pilot=obs['pilot'], data_true=data_true_af, soft_mean=mu_d, app_v=v).items()}
    row['rng_domain'] = str(p1ctx.p1_driver.DOMAIN)
    row['rng_entropy'] = p1ctx.p1_driver.ENTROPY_HEX
    row['pairing'] = dict(noise_sha256=truth['noise_sha256'], physical_gains_sha256=truth['physical_gains_sha256'],
                          coded_sha256=array_sha(truth['coded']), info_sha256=array_sha(truth['info']))
    gamma_cache = {}
    for name in arms.ARMS:
        phase_clock['phase'] = name + ': columns'
        t_v = time.perf_counter()
        vsec = {}
        t = time.perf_counter()
        spec = arms.arm_spec(name, v, vo, sigma2)
        xt, B, beta0, v_m, g_m = xt_soft, Bs[:, cand2], beta0_soft, spec['v_m'], spec['mode']
        G = arms.sbl_gamma(spec, cd, cn, c1, gamma_cache)
        vsec['columns'] = time.perf_counter() - t
        t = time.perf_counter()
        phase_clock['phase'] = name + ': SBL'
        res = sbl.sbl_em(B, Y, beta0=beta0, Gamma=G)
        idx, mu, e = sbl.select_output(cand2[res['idx']], res['mu'])
        vsec['sbl'] = time.perf_counter() - t
        dl, dn0 = delays_g[idx], nus_g[idx]
        t = time.perf_counter()
        phase_clock['phase'] = name + ': refinement'
        rf = ref.refine(Y, xt, v_m, dl, dn0, c1, c2, spec['ridge'], g_m)
        vsec['refine'] = time.perf_counter() - t
        phase_clock['phase'] = name + ': continuous decode'
        ch2 = e3d.make_channel(ctx, n, dl, rf['dopplers'], rf['gains'])
        det2, dec2, t_det, t_dec = e3d.detect_decode(ctx, obs, ch2, check)
        vsec['detect'], vsec['decode'] = t_det, t_dec
        err2 = gd.score(ctx, dec2['decoded'], truth)
        pairs = sbl.codelay_pairs(dl, rf['dopplers'], n, true_delays)
        out = dict(info_errors=int(err2), fer=int(err2 > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, dec2['decoded'])), decoded_sha256=gd.bits_sha(dec2['decoded']),
                   ldpc_iters=int(dec2['iterations']), n_atoms=int(len(idx)), gamma_mode=g_m, atoms_ongrid=e3d.atoms_record(dl, dn0, e),
                   atoms=e3d.atoms_record(dl, rf['dopplers'], np.abs(rf['gains']) ** 2), n_pair=len(pairs), pairs=pairs,
                   nmse=float(crb.channel_nmse(dict(delays=dl, dopplers=rf['dopplers'], gains=rf['gains']), tp, n)),
                   sbl=dict(max_iter=sbl.MAX_ITER, iterations=res['iterations'], converged=res['converged'], n_start=res['n_start'], n_final=res['n_final'],
                            beta=res['beta'], jitter_events=res['jitter_events']),
                   refine={k: val for k, val in rf.items() if k not in ('dopplers', 'gains')})
        phase_clock['phase'] = name + ': diagnostics'
        pos = np.array([int(np.flatnonzero(cand2 == j)[0]) for j in idx])
        ge, de = arms.gamma_consistency(Y, xt, spec, G, pos, dl, dn0, c1, c2, sigma2)
        if ge > arms.GAMMA_TOL or (de is not None and de > arms.GAMMA_TOL):
            raise AssertionError(f'Gamma mismatch {name}: {ge}, {de}')
        out['gamma_check'] = dict(relative_error=ge, diagonal_error=de)
        paths = [arms.GPath(int(l), float(nu)) for l, nu in zip(dl, dn0)]
        t = time.perf_counter()
        Bf, Qf, _, hf, vf, gf = arms._system(Y, xt, v_m, paths, c1, c2, spec['ridge'], g_m)
        effective_gf = gf + spec['extra_ridge'] * np.eye(len(dl))
        out['geometry_diagnostics'] = geometry_diagnostics(Bf, Qf, effective_gf, mu, dl, dn0)
        out['regularization'] = dict(sum_profile=spec['sum_vec'], extra_ridge=spec['extra_ridge'], ridge=spec['ridge'], profile=spec['vec'])
        out['fixed_gain_sha256'] = array_sha(hf)
        out['sbl_gain_sha256'] = array_sha(mu)
        out['continuous_gain_sha256'] = array_sha(rf['gains'])
        vsec['diagnostics'] = time.perf_counter() - t
        if name in arms.CHECK_ARMS:
            out['stages'] = {}
            for stage, gains in (('sbl', mu), ('fixed_refit', hf)):
                phase_clock['phase'] = name + ': ' + stage + ' decode'
                t = time.perf_counter()
                if stage == 'sbl' and ongrid_reuse is not None:
                    old = ongrid_reuse['variants'][{'diag-off':'L-diag','cov-off':'L-cov'}[name]]
                    if old['atoms'] != out['atoms_ongrid']:
                        raise AssertionError('on-grid atoms differ from E3')
                    out['stages'][stage] = dict(old, provenance='frozen E3 saved row', recomputed=False)
                    continue
                out['stages'][stage] = score_stage(ctx, obs, check, tp, truth, dl, dn0, gains, n)
                out['stages'][stage]['recomputed'] = True
                out['stages'][stage]['provenance'] = 'recomputed same key'
                vsec[stage + '_detect_decode'] = time.perf_counter() - t
            out['stages']['fixed_refit']['objective'] = float(vf)
        vsec['total'] = time.perf_counter() - t_v
        out['seconds'] = vsec
        row['variants'][name] = out
        phase_clock.setdefault('completed_arms', {})[name] = vsec
    sec['total'] = time.perf_counter() - t_all
    row['seconds'] = sec
    return row


def strip_timing(value):
    if isinstance(value, dict):
        return {k: strip_timing(v) for k,v in value.items() if k not in ('seconds', 'gen_seconds', 'detect_seconds', 'decode_seconds')}
    if isinstance(value, list):
        return [strip_timing(x) for x in value]
    return value


def compare_baseline(row, old):
    checks = dict(stage1=row['stage1']['atoms'] == old['stage1_atoms'],
                  round1=row['round1']['decoded_sha256'] == old['round1_sha'], candidates=row['n_candidates_stage2'] == old['n_cand2'])
    checks['variants'] = {a: dict(sha=row['variants'][a]['decoded_sha256'] == old['variants'][a]['decoded_sha256'],
                                      atoms=row['variants'][a]['atoms'] == old['variants'][a]['atoms'],
                                      atoms_ongrid=row['variants'][a]['atoms_ongrid'] == old['variants'][a]['atoms_ongrid'],
                                      errors=row['variants'][a]['info_errors'] == old['variants'][a]['info_errors'],
                                      nmse=row['variants'][a]['nmse'] == old['variants'][a]['nmse']) for a in arms.CHECK_ARMS}
    checks['all'] = all(checks[k] for k in ('stage1','round1','candidates')) and all(all(x.values()) for x in checks['variants'].values())
    return checks


def source_identity(ctx=None):
    from e3c_provenance import resolve_frozen
    if ctx is None:
        ctx = p1ctx.load()
    if not getattr(ctx, 'source_paths', None):
        raise RuntimeError('loaded context must expose actual source_paths')
    paths = set(HERE.glob('*.py')) | set(HERE.glob('*.sh'))
    paths.add(HERE / 'PROTOCOL.md')
    paths.add(HERE / 'SOURCE_MD5.txt')
    paths.add(HERE.parent / 'tf_covariance_audit_20261018' / 'sampling.py')
    frozen = HERE / 'SOURCE_MD5.txt'
    resolutions = resolve_frozen(HERE.parent, frozen,
                                 getattr(ctx, 'source_md5', None), getattr(ctx, 'source_paths', None))
    paths.update((lib.E3B_DIR/'offgrid_refine.py', lib.E3B_DIR/'e3b_lib.py'))
    result = {str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    result.update({rel: val['sha256'] for rel, val in resolutions.items()})
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=1, allow_nan=False, default=str)+'\n')


def run(args, argv):
    import scipy
    for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        if os.environ.get(name) != '1':
            raise RuntimeError(f'{name}=1 required before Python starts')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    rows_path = out / f'rows_shard{args.shard:03d}.jsonl'
    if cfg_path.exists() or rows_path.exists():
        raise FileExistsError('refuse overwrite/resume: use a new output directory')
    keys = lib.gate_keys() if args.mode == 'gate' else (lib.smoke_keys() if args.smoke else lib.main_keys())
    mine = lib.shard_block(keys, args.shard, args.nshard)
    old = {}
    manifest = None
    if not args.smoke:
        old, manifest = lib.load_e3b_rows(args.e3b_rows, mine)
    old_grid = {}
    grid_manifest = None
    if args.mode == 'run' and not args.smoke:
        old_grid, grid_manifest = lib.load_e3_grid_rows(args.e3_rows, mine)
        if set(old_grid) != set(mine):
            raise RuntimeError('missing on-grid E3 rows')
    ctx = p1ctx.load()
    identity = source_identity(ctx)
    if args.mode == 'run' and not args.smoke:
        if args.freeze_root is None:
            raise RuntimeError('production requires --freeze-root from the main-owned launcher')
        frozen=json.loads((args.freeze_root/'FREEZE.json').read_text())
        gates=json.loads((args.freeze_root/'gates.json').read_text())
        if not frozen.get('git_commit') or not gates['all_pass'] or frozen['sources_sha256']!=identity or gates['sources_sha256']!=identity:
            raise RuntimeError('production source freeze/gates mismatch')
    from e3c_provenance import resolve_frozen
    config = dict(argv=list(argv), args=vars(args), arms=arms.ARMS, sources_sha256=identity, source_md5=ctx.source_md5,
                  runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, host=platform.node(),
                               env={k: os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','CUDA_VISIBLE_DEVICES')}),
                  hyper_sbl=sbl.HYPER, hyper_refine=ref.HYPER, rng=dict(domain=p1ctx.p1_driver.DOMAIN, entropy=p1ctx.p1_driver.ENTROPY_HEX),
                  system=dict(rho=float(ctx.system.rho), p_d=float(1-ctx.system.rho), N=int(ctx.system.N_total),
                              c1=float(ctx.system.c1), c2=float(ctx.system.c2), l_max_cap=int(ctx.system.l_max_cap)),
                  baseline_manifest=manifest, ongrid_manifest=grid_manifest, keys=mine, smoke=bool(args.smoke),
                  frozen_source_resolution=resolve_frozen(HERE.parent,HERE/'SOURCE_MD5.txt',ctx.source_md5,ctx.source_paths))
    write_json(cfg_path, dict(_argv=list(sys.argv),_config=config))
    config_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    records=[]
    with rows_path.open('x') as handle:
        for key in mine:
            clock = dict(phase='generation')
            t0 = time.perf_counter()
            meta = dict(zip(('scenario','rho_permille','snr_centi_db','frame'),key))
            try:
                sc, rho, snr, frame = key
                base = p1ctx.base(ctx, sc, rho / 1000, frame)
                gen_s = time.perf_counter()-t0
                meta, obs, data, truth = e3d.observe_key(ctx, base[0], base[1], sc, rho, snr, frame, gen_s)
                row = process_key(ctx, cache, grid, obs, data, truth, meta, phase_clock=clock,
                                  ongrid_reuse=old_grid.get(key))
                if args.smoke:
                    row['smoke'] = True
                else:
                    row['baseline_check'] = compare_baseline(row, old[key])
                    if not row['baseline_check']['all']:
                        raise AssertionError(f'E3b replay mismatch: {row["baseline_check"]}')
                if args.mode == 'gate':
                    clock['phase']='G3 repeat'
                    repeat=process_key(ctx, cache, grid, obs, data, truth, meta, phase_clock=clock)
                    diff = lib.deep_equal(strip_timing(row), strip_timing(dict(repeat, baseline_check=row['baseline_check'])))
                    row['g3'] = dict(pass_=not diff, mismatch=diff[:5])
                    if diff:
                        raise AssertionError(f'G3 repeat mismatch: {diff[:5]}')
            except BaseException as exc:
                failed = dict(meta, status='error', error=repr(exc), trace=traceback.format_exc()[-4000:], phase=clock,
                              elapsed_seconds=time.perf_counter()-t0, config_sha256=config_sha,_argv=list(sys.argv),_config=dict(config_file=cfg_path.name,config_sha256=config_sha))
                e3d.write_row(handle, failed)
                raise
            row.update(status='ok', config_sha256=config_sha, _argv=list(sys.argv), _config=dict(config_file=cfg_path.name,config_sha256=config_sha), elapsed_seconds=time.perf_counter()-t0)
            e3d.write_row(handle,row)
            records.append(dict(key=key, elapsed_seconds=row['elapsed_seconds']))
            print(json.dumps(dict(key=key,status='ok',seconds=row['elapsed_seconds'])),flush=True)
    write_json(out / f'completed_shard{args.shard:03d}.json', dict(keys=records, config_sha256=config_sha))


def parse_args():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('gate','run'),required=True)
    p.add_argument('--smoke',action='store_true')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--e3b-rows',type=Path,default=lib.E3B_ROWS)
    p.add_argument('--e3-rows',type=Path,default=lib.b3lib.E3_ROWS)
    p.add_argument('--shard',type=int,default=0)
    p.add_argument('--nshard',type=int,default=1)
    p.add_argument('--lease-seconds',type=float,default=1800.)
    p.add_argument('--budget-dir',type=Path,required=True)
    p.add_argument('--freeze-root',type=Path)
    a=p.parse_args()
    if not 1 <= a.nshard <= 24 or not 0 <= a.shard < a.nshard or a.lease_seconds <= 0:
        p.error('invalid shard / concurrency / lease')
    if a.smoke and a.mode != 'run':
        p.error('--smoke requires --mode run')
    return a


if __name__=='__main__':
    args=parse_args()
    from e3c_budget import BudgetLease
    with BudgetLease(args.budget_dir, args.lease_seconds, list(sys.argv), started=IMPORT_START):
        run(args, sys.argv[1:])
