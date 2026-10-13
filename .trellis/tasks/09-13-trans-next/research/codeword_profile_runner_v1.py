"""Saved ridge failures: fixed terminal H versus fixed-support codeword ridge profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

FAILURES = {7: (2, 4, 9, 11, 14, 15, 17, 18, 22, 25, 26, 27, 31),
            8: (15, 25)}
ENGINEERING = ((2, 7), (15, 8))
K = 24
N = 1024
Q_RTOL = 1e-6  # Frozen complex64 numeric replay tolerance, before outcomes.
SAVED_A_RTOL = 2e-6  # Old complex64 t9 design versus analysis complex128 operator.


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def require_sha(path: Path, expected: str):
    if file_sha(path) != expected:
        raise ValueError('bound input digest differs: ' + str(path))


def saved_operator_parity(saved, rebuilt):
    saved,rebuilt=np.asarray(saved),np.asarray(rebuilt)
    if saved.shape!=(N,K) or rebuilt.shape!=(N,K) or not np.isfinite(saved).all() or not np.isfinite(rebuilt).all():
        raise ValueError('saved/analysis t9 operator invalid')
    relative=float(np.linalg.norm(saved-rebuilt)/max(1.,np.linalg.norm(saved)))
    if relative>SAVED_A_RTOL:
        raise FloatingPointError('analysis source-v4 operator differs from old production t9 A')
    return relative


def score_identity(y, A, lam, g):
    """Direct objective, algebraic profile and saved normal equation agree."""
    y, A, g = np.asarray(y), np.asarray(A), np.asarray(g)
    if (y.shape != (N,) or A.shape != (N, K) or g.shape != (K,)
            or not np.iscomplexobj(A) or not np.isfinite(A).all()
            or not np.isfinite(y).all() or not np.isfinite(g).all()
            or not np.isfinite(lam) or lam <= 0):
        raise ValueError('invalid profile equation shape, finite values or lambda')
    A = np.asarray(A, dtype=np.complex128)
    y = np.asarray(y, dtype=np.complex128)
    g = np.asarray(g, dtype=np.complex128)
    gram = A.conj().T @ A
    eig = np.linalg.eigvalsh(gram)
    if eig[0] <= 1e-10 * eig[-1]:
        raise np.linalg.LinAlgError('candidate sensing matrix is rank deficient')
    rhs = A.conj().T @ y
    lhs = gram + lam * np.eye(K)
    resid = y - A @ g
    residual_square = float(np.vdot(resid, resid).real)
    penalty_square = float(lam * np.vdot(g, g).real)
    direct = residual_square + penalty_square
    closed = float((np.vdot(y, y) - np.vdot(rhs, g)).real)
    normal = float(np.linalg.norm(lhs @ g - rhs) /
                   max(1., np.linalg.norm(lhs) * np.linalg.norm(g) + np.linalg.norm(rhs)))
    if abs(direct - closed) > 2e-8 * max(1., direct) or normal > 2e-8:
        raise FloatingPointError('saved ridge profile objective/normal equation differs')
    return dict(J=direct, residual_square=residual_square, penalty_square=penalty_square,
                closed_profile=closed, rank=K, gram_lambda_min=float(eig[0]),
                gram_lambda_max=float(eig[-1]),
                penalized_condition=float((eig[-1] + lam) / (eig[0] + lam)),
                relative_normal_residual=normal)


def fit_profile(y, A, lam):
    A = np.asarray(A, dtype=np.complex128)
    y = np.asarray(y, dtype=np.complex128)
    if A.shape != (N, K) or y.shape != (N,) or not np.isfinite(A).all() or not np.isfinite(y).all():
        raise ValueError('candidate design or response invalid')
    gram = A.conj().T @ A
    eig = np.linalg.eigvalsh(gram)
    if eig[0] <= 1e-10 * eig[-1] or not np.isfinite(lam) or lam <= 0:
        raise np.linalg.LinAlgError('candidate sensing rank or lambda invalid')
    g = np.linalg.solve(gram + lam * np.eye(K), A.conj().T @ y)
    scores = score_identity(y, A, lam, g)
    return g, scores


def candidate_bits(code, truth, decoded, info_hat):
    from afdm_sp_joint_unrolled.e1_ldpc import encode, extract_info
    truth, decoded, info_hat = (np.asarray(v, dtype=np.uint8) for v in
                                (truth, decoded, info_hat))
    if truth.shape != (2 * N,) or decoded.shape != (2 * N,) or info_hat.shape != (N,):
        raise ValueError('codeword dimensions differ from N1024 code')
    if not all(np.isin(v, (0, 1)).all() for v in (truth, decoded, info_hat)):
        raise ValueError('nonbinary codeword or information output')
    if not np.array_equal(extract_info(code, decoded), info_hat):
        raise ValueError('decoded/info_hat mismatch')
    reencoded = encode(code, info_hat)
    candidates = dict(true_c=truth, decoded_raw=decoded, reencoded_info_hat=reencoded)
    check = np.asarray(code['H'], dtype=np.int64)
    status = {}
    for name, bits in candidates.items():
        syndrome_weight = int(np.count_nonzero((check @ bits.astype(np.int64)) % 2))
        status[name] = dict(valid=syndrome_weight == 0, syndrome_weight=syndrome_weight,
                            information_bit_distance=int(np.count_nonzero(
                                extract_info(code, bits) != extract_info(code, truth))),
                            codeword_bit_distance=int(np.count_nonzero(bits != truth)))
    if not status['true_c']['valid'] or not status['reencoded_info_hat']['valid']:
        raise ValueError('truth or systematic reencoding is not a legal codeword')
    return candidates, status


def margins(fixed, profile):
    result = {}
    for name in ('decoded_raw', 'reencoded_info_hat'):
        h = fixed[name] - fixed['true_c']
        p = profile[name] - profile['true_c']
        result[name] = dict(fixed_H_margin=float(h), profile_margin=float(p),
                            fixed_true_preferred=bool(h > 0),
                            profile_true_preferred=bool(p > 0),
                            ranking_flip=bool((h > 0) != (p > 0)),
                            profile_minus_fixed_margin=float(p - h))
    return result


def parse():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=('run', 'audit'), required=True)
    p.add_argument('--stage', choices=('engineering', 'development'), required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--old-root', type=Path, required=True)
    p.add_argument('--dir-root', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--script-sha256', required=True)
    p.add_argument('--admission', type=Path)
    p.add_argument('--admission-sha256')
    return p.parse_args()


def load_scope(args):
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS
    from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles
    require_sha(Path(__file__), args.script_sha256)
    require_sha(args.contract, args.contract_sha256)
    c = json.loads(args.contract.read_text())
    if (c.get('schema') != 'codeword-profile-v1' or c['source_manifest_sha256'] !=
            file_sha(args.source_root / 'source-manifest.json') or c['code_keys'] != list(CODE_KEYS)
            or c['failures'] != {str(k): list(v) for k, v in FAILURES.items()}
            or c['engineering'] != [list(p) for p in ENGINEERING]
            or c['max_refits'] != 45 or c['lambda_strength'] != .1
            or c['N'] != N or c['K'] != K or c['pilot_W'] != 2 or c['rho'] != .5
            or c['candidate_order'] != ['true_c','decoded_raw','reencoded_info_hat']
            or c['max_refits_engineering'] != 6 or c['max_refits_development'] != 39
            or c['new_receiver_CE'] != 0 or c['new_F'] != 0 or c['new_BP'] != 0
            or c['new_LDPC'] != 0
            or c['q_relative_tolerance'] != Q_RTOL or c['saved_A_relative_tolerance'] != SAVED_A_RTOL
            or c['producer_source_manifest_sha256'] != c['input_sha256']['dir:source-v4/source-manifest.json']
            or c['threads'] != 1):
        raise ValueError('codeword-profile frozen scientific scope differs')
    if not args.root.resolve().is_relative_to(Path('/data/guoyikun/')):
        raise ValueError('new remote output root must be under /data/guoyikun')
    files = {args.contract: args.contract_sha256, Path(__file__): args.script_sha256,
             args.source_root / 'source-manifest.json': c['source_manifest_sha256']}
    for rel, digest in c['input_sha256'].items():
        base = args.old_root if rel.startswith('old:') else args.dir_root
        files[base / rel.split(':', 1)[1]] = digest
    manifest = json.loads((args.source_root / 'source-manifest.json').read_text())
    package = args.source_root / 'afdm_sp_joint_unrolled'
    if set(manifest) != {str(p.relative_to(package)) for p in package.rglob('*.py')}:
        raise ValueError('source-v4 package inventory changed')
    for rel,digest in manifest.items():
        require_sha(package/rel,digest)
    for rel in ('e1_ldpc.py', 'classical_joint_unrolled.py', 'supplement_g1.py',
                'light_gap_replay.py', 'bottleneck_pilot.py', 'loop9_cache_features.py'):
        files[package / rel] = manifest[rel]
    guard = BoundFiles(files)
    guard.check()
    return c, guard


def indexes(args, c):
    from afdm_sp_joint_unrolled.light_gap_replay import sha
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    result = {}
    for label, rel in c['summaries'].items():
        base = args.old_root if label.startswith('g1_') else args.dir_root
        summary = json.loads((base / rel).read_text())
        if summary['status'] != 'COMPLETE':
            raise ValueError('old paired summary is incomplete')
        result[label] = {(r['kind'], r['block'], r['snr'], r['arm']): r
                         for r in summary['records']}
    def ref(b, snr):
        stage = 'engineering' if b in (0, 20) else 'development'
        a = result['g1_' + stage]['A', b, 7, 'G1_PROPAGATION']
        f = result['dir_' + stage]['F', b, snr, 'ridge']
        return a, f
    found = {7: [], 8: []}
    # Validate all 64 saved F/A result and NPZ identities without a new receiver call.
    for b in range(32):
        for snr in (7, 8):
            a, f = ref(b, snr)
            for e, root in ((a, args.old_root), (f, args.dir_root)):
                path = Path(e['record'])
                if not path.resolve().is_relative_to(root.resolve()) or sha(path) != e['sha256']:
                    raise ValueError('saved old result hash/path differs')
                record = json.loads(path.read_text())
                state = record['state']['file']
                raw_path = Path(state['path'])
                if not raw_path.resolve().is_relative_to(root.resolve()) or sha(raw_path) != state['sha256']:
                    raise ValueError('saved old NPZ hash/path differs')
            if json.loads(Path(f['record']).read_text())['physical_record_sha256'] != a['sha256']:
                raise ValueError('ridge F/physical A pairing hash differs')
            if f['scores']['FER'] not in (0, 1):
                raise ValueError('old FER bit invalid')
            if f['scores']['FER']:
                found[snr].append(b)
    if found != {k: list(v) for k, v in FAILURES.items()}:
        raise ValueError('frozen 13/2 ridge failure selection differs')
    return ref


def frame(args, code, system, ref, block, snr):
    import torch
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch,reconstruct_H_torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.e1_ldpc import encode, qpsk_map
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    a, f = ref(block, snr)
    _, physical = verified_record(a, args.old_root)
    fr, old = verified_record(f, args.dir_root)
    raw = physical['raw']
    observed, _ = reuse_at_snr(raw, physical['diagnostics'], snr)
    same = {k: np.array(observed[k]) for k in ('y', 'pilot', 'sigma2')}
    same['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
    if hashes(same) != fr['observed_hashes']:
        raise ValueError('old ridge F observed y/pilot/sigma hashes differ')
    if not np.array_equal(encode(code, raw['info']), raw['coded']):
        raise ValueError('true information bits do not reconstruct saved codeword')
    np.testing.assert_allclose(qpsk_map(raw['coded'], scale=np.sqrt(.5)), raw['data'],
                               rtol=0, atol=1e-12)
    candidates, status = candidate_bits(code, raw['coded'], old['decoded'], old['info_hat'])
    if bool(old['decode_ok']) != status['decoded_raw']['valid']:
        raise ValueError('saved decode_ok disagrees with exact syndrome')
    if int(fr['scores']['FER']) != int(np.count_nonzero(old['info_hat'] != raw['info']) > 0):
        raise ValueError('saved ridge FER differs from information error')
    if np.array_equal(candidates['reencoded_info_hat'], candidates['true_c']):
        raise ValueError('saved ridge failure reencodes to true codeword')
    if len(old['dals']) != 9 or len(old['support']) != K:
        raise ValueError('ridge F missing nine DA-LS states or K24 support')
    t9 = old['dals'][-1]
    delays = np.asarray(t9['support_delays'], dtype=np.int64)
    dopplers = np.asarray(t9['support_dopplers'], dtype=np.int64)
    ids = delays * 5 + dopplers + 2
    if (ids.shape != (K,) or len(set(ids.tolist())) != K or
            set(ids.tolist()) != set(np.asarray(old['support']).tolist())):
        raise ValueError('t9 support differs from actual terminal support')
    for d in old['dals']:
        if not np.array_equal(d['support_delays'], delays) or not np.array_equal(d['support_dopplers'], dopplers):
            raise ValueError('old ridge changed support during nine states')
    A_saved = np.asarray(t9['A'], dtype=np.complex128)
    A_analysis=build_A_for_DALS_torch(N,torch.as_tensor(delays,dtype=torch.long),
        torch.as_tensor(dopplers,dtype=torch.long),
        torch.as_tensor(np.asarray(same['pilot'])+np.asarray(t9['mu']),dtype=torch.complex128),
        system.c1,system.c2,2,cdtype=torch.complex128).numpy()
    A_parity=saved_operator_parity(t9['A'],A_analysis)
    lam = .1 * float(np.vdot(A_saved, A_saved).real) / K
    precision = np.asarray(old['gain_prior']['precision'], dtype=np.complex128)
    Q = np.asarray(t9['Q'], dtype=np.complex128)
    if (np.linalg.norm(precision - np.eye(K)) > Q_RTOL * np.sqrt(K) or
            np.linalg.norm(Q - lam * np.eye(K)) > Q_RTOL * max(1., np.linalg.norm(Q))):
        raise ValueError('saved t9 ridge Q is not same-frame strength .1 identity')
    H = np.asarray(old['H'], dtype=np.complex128)
    y = np.asarray(same['y'], dtype=np.complex128)
    p = np.asarray(same['pilot'], dtype=np.complex128)
    if H.shape != (N, N) or y.shape != (N,) or p.shape != (N,):
        raise ValueError('terminal H or physical y/pilot shape differs')
    if not np.isfinite(H).all() or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise FloatingPointError('nonfinite actual terminal H or observation')
    H_pure=reconstruct_H_torch(N,torch.as_tensor(delays,dtype=torch.long),
        torch.as_tensor(dopplers,dtype=torch.long),
        torch.as_tensor(t9['g_solution'],dtype=torch.complex128),
        system.c1,system.c2,2,cdtype=torch.complex128).numpy()
    return dict(block=block, snr=snr, a=a, f=f, candidates=candidates, status=status,
                H=H, y=y, p=p, lam=lam, delays=delays, dopplers=dopplers,
                terminal_H_vs_t9_H_relative=float(np.linalg.norm(H-np.asarray(t9['H'])) /
                                                max(1., np.linalg.norm(H))),
                terminal_H_vs_t9_pure_support_rebuild_relative=float(np.linalg.norm(H-H_pure) /
                                                max(1., np.linalg.norm(H))),
                saved_t9_A_analysis_relative=A_parity,
                t9_Q_relative=float(np.linalg.norm(Q-lam*np.eye(K))/max(1.,np.linalg.norm(Q))))


def evaluate(args, code, system, ref, run, block, snr):
    import torch
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch
    from afdm_sp_joint_unrolled.e1_ldpc import qpsk_map
    from afdm_sp_joint_unrolled.bottleneck_pilot import array_hash
    fr = frame(args, code, system, ref, block, snr)
    fixed, profiles, entries, cached = {}, {}, {}, {}
    td = torch.as_tensor(fr['delays'], dtype=torch.long)
    tk = torch.as_tensor(fr['dopplers'], dtype=torch.long)
    for name, bits in fr['candidates'].items():
        data = qpsk_map(bits, scale=np.sqrt(.5))
        x = fr['p'] + data
        fixed[name] = float(np.vdot(fr['y']-fr['H']@x, fr['y']-fr['H']@x).real)
        digest = array_hash(bits)
        if digest not in cached:
            A = build_A_for_DALS_torch(N, td, tk, torch.as_tensor(x, dtype=torch.complex128),
                                       system.c1, system.c2, 2, cdtype=torch.complex128).numpy()
            value, _ = run.call('P', dict(block=block, snr=snr, split=fr['f']['split'],
                                         arm=name), lambda A=A: make_value(fr, bits, A),
                                lambda v: v['score'], dict(physical_sha256=fr['a']['sha256'],
                                ridge_F_sha256=fr['f']['sha256'], candidate_bits_sha256=digest))
            cached[digest] = (value['score'], run.records[-1]['sha256'])
        profiles[name], entries[name] = cached[digest]
    return dict(block=block, snr=snr, lambda_fixed=fr['lam'], status=fr['status'],
                candidate_bits_sha256={name:array_hash(bits) for name,bits in fr['candidates'].items()},
                fixed_H_scores=fixed, profile_scores={n:s['J'] for n,s in profiles.items()},
                profile_record_sha256=entries, margins=margins(fixed,{n:s['J'] for n,s in profiles.items()}),
                terminal_H_vs_t9_H_relative=fr['terminal_H_vs_t9_H_relative'],
                terminal_H_vs_t9_pure_support_rebuild_relative=fr['terminal_H_vs_t9_pure_support_rebuild_relative'],
                saved_t9_A_analysis_relative=fr['saved_t9_A_analysis_relative'],
                t9_Q_relative=fr['t9_Q_relative'], physical_record_sha256=fr['a']['sha256'],
                ridge_F_record_sha256=fr['f']['sha256'], actual_refits=len(cached))


def make_value(fr, bits, A):
    from afdm_sp_joint_unrolled.bottleneck_pilot import array_hash
    g, score = fit_profile(fr['y'], A, fr['lam'])
    return dict(A=A, y=fr['y'], g=g, lambda_fixed=fr['lam'], score=score,
                support_delays=fr['delays'], support_dopplers=fr['dopplers'],
                bits_sha256=array_hash(bits))


def execute(args):
    sys.path.insert(0, str(args.source_root))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS, LightRun
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    c, guard = load_scope(args)
    ref = indexes(args, c)
    env = json.loads((args.old_root / c['environment']).read_text())
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    system = _make_config_a(N, 2., 8, 10., 4.)
    if (system.N_total, system.l_max_cap, system.k_max_cap, system.rho) != (N, 102, 2, .5):
        raise ValueError('G1 physical system geometry changed')
    args.root.mkdir(parents=True,exist_ok=True)
    (args.root / 'code-cache').mkdir(exist_ok=True)
    code = build_code(cache_dir=args.root / 'code-cache')
    if hashes({key:code[key] for key in CODE_KEYS}) != env['code_identity']:
        raise ValueError('LDPC source-v4 identity differs from old G1 code')
    pairs = ENGINEERING if args.stage == 'engineering' else tuple((b,s) for s,blocks in FAILURES.items()
                              for b in blocks if (b,s) not in ENGINEERING)
    if args.stage == 'development':
        if args.admission is None or args.admission_sha256 is None or file_sha(args.admission) != args.admission_sha256:
            raise ValueError('development requires hashed engineering audit admission')
        admission = json.loads(args.admission.read_text())
        if (admission['status'] != 'PASS' or admission['contract_sha256'] != args.contract_sha256 or
                admission['script_sha256'] != args.script_sha256):
            raise ValueError('engineering admission not bound to this producer/contract')
    if args.mode == 'audit':
        audit(args, c, guard, code, system, ref, pairs)
        return
    bounds = {'P': 6 if args.stage == 'engineering' else 39,
              'seconds': 900 if args.stage == 'engineering' else 5400}
    run = LightRun(args.root, args.stage, bounds, 20 * 1024**3, guard)
    try:
        rows = [evaluate(args, code, system, ref, run, b, s) for b,s in pairs]
        total = sum(r['actual_refits'] for r in rows)
        if total != run.counts['P'] or total > bounds['P']:
            raise ValueError('actual profile refit count differs from reserved calls')
        run.write('summary.json',dict(status='COMPLETE',schema='codeword-profile-v1',
            stage=args.stage,contract_sha256=args.contract_sha256,script_sha256=args.script_sha256,
            source_manifest_sha256=c['source_manifest_sha256'],rows=rows,
            actual_profile_refits=total, new_receiver_CE=0,new_F=0,new_BP=0,new_LDPC=0,
            recorded_calls=run.counts, records=run.records))
    except Exception as exc:
        run.fail(exc)
        raise


def audit(args,c,guard,code,system,ref,pairs):
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import array_hash
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch
    from afdm_sp_joint_unrolled.e1_ldpc import qpsk_map
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    summary_path=args.root/args.stage/'summary.json'
    summary=json.loads(summary_path.read_text())
    if (summary['status']!='COMPLETE' or summary['contract_sha256']!=args.contract_sha256 or
            summary['script_sha256']!=args.script_sha256 or len(summary['rows'])!=len(pairs)):
        raise ValueError('saved producer summary scope differs')
    indexed={(r['block'],r['snr']):r for r in summary['rows']}
    record_index={r['sha256']:r for r in summary['records']}
    checked=[]
    for b,s in pairs:
        guard.check()
        fr=frame(args,code,system,ref,b,s)
        row=indexed[b,s]
        fixed={}
        prof={}
        for name,bits in fr['candidates'].items():
            x=fr['p']+qpsk_map(bits,scale=np.sqrt(.5))
            z=fr['y']-fr['H']@x
            fixed[name]=float(np.vdot(z,z).real)
            digest=row['profile_record_sha256'][name]
            e=record_index[digest]
            _,saved=verified_record(e,args.root)
            A=build_A_for_DALS_torch(N,torch.as_tensor(fr['delays'],dtype=torch.long),
                 torch.as_tensor(fr['dopplers'],dtype=torch.long),
                 torch.as_tensor(x,dtype=torch.complex128),system.c1,system.c2,2,
                 cdtype=torch.complex128).numpy()
            np.testing.assert_allclose(saved['A'],A,rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(saved['y'],fr['y'],rtol=0,atol=0)
            if saved['bits_sha256']!=array_hash(bits) or saved['lambda_fixed']!=fr['lam']:
                raise ValueError('saved candidate or same-frame lambda differs')
            score=score_identity(saved['y'],saved['A'],saved['lambda_fixed'],saved['g'])
            if abs(score['J']-saved['score']['J'])>2e-8*max(1.,score['J']):
                raise ValueError('saved objective differs on raw audit')
            prof[name]=score['J']
        if (row['candidate_bits_sha256']!={n:array_hash(v) for n,v in fr['candidates'].items()}
                or row['status']!=fr['status'] or row['physical_record_sha256']!=fr['a']['sha256']
                or row['ridge_F_record_sha256']!=fr['f']['sha256']):
            raise ValueError('saved row old-source identity differs')
        bit_to_record={}
        for name,bit_sha in row['candidate_bits_sha256'].items():
            record_sha=row['profile_record_sha256'][name]
            if bit_sha in bit_to_record and bit_to_record[bit_sha]!=record_sha:
                raise ValueError('identical candidate bit vector did not reuse profile record')
            bit_to_record[bit_sha]=record_sha
        if row['actual_refits']!=len(bit_to_record) or len(set(bit_to_record.values()))!=len(bit_to_record):
            raise ValueError('saved unique-bit profile refit count differs')
        for key in ('terminal_H_vs_t9_H_relative','terminal_H_vs_t9_pure_support_rebuild_relative',
                    'saved_t9_A_analysis_relative',
                    't9_Q_relative'):
            if abs(row[key]-fr[key])>2e-8*max(1.,fr[key]):
                raise ValueError('saved terminal-H/rebuild or Q diagnostic differs')
        for name in fixed:
            if (abs(fixed[name]-row['fixed_H_scores'][name])>2e-8*max(1.,fixed[name]) or
                    abs(prof[name]-row['profile_scores'][name])>2e-8*max(1.,prof[name])):
                raise ValueError('saved fixed-H/profile score differs')
        replay_margins=margins(fixed,prof)
        for name in replay_margins:
            for key,value in replay_margins[name].items():
                old_value=row['margins'][name][key]
                if isinstance(value,bool):
                    if value!=old_value:raise ValueError('saved ranking sign differs')
                elif abs(value-old_value)>2e-8*max(1.,abs(value)):
                    raise ValueError('saved paired ranking margin differs')
        checked.append(dict(block=b,snr=s,actual_refits=row['actual_refits']))
    if sum(x['actual_refits'] for x in checked)!=summary['actual_profile_refits']:
        raise ValueError('saved actual refit account differs')
    out=args.root/'evidence'
    out.mkdir(exist_ok=True)
    path=out/f'codeword-profile-{args.stage}-raw-audit-v1.json'
    if path.exists():raise FileExistsError('audit receipt already exists')
    path.write_text(json.dumps(dict(status='PASS',stage=args.stage,schema='codeword-profile-v1',
        contract_sha256=args.contract_sha256,script_sha256=args.script_sha256,
        producer_summary_sha256=file_sha(summary_path),paired_rows=checked,
        saved_profile_refits=summary['actual_profile_refits'],new_profile_refits=0,
        new_receiver_CE=0,new_F=0,new_BP=0,new_LDPC=0),sort_keys=True))
    print(str(path))


if __name__ == '__main__':
    execute(parse())
