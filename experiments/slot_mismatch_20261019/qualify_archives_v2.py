"""Phase 1 archival, generator, slot and noise gates on historical keys only."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from qualify_v2 import CODELAY, NOISE_FLOOR, fingerprint, generation, load, observe_only, sm


def verify_archive(root, manifest, files):
    expected = {name: digest for digest, name in
                (line.split() for line in manifest.read_text().splitlines() if line.strip())}
    actual = {p.name: sm.e2_lib.md5_file(p) for p in files}
    if not actual or any(digest != expected[name] for name, digest in actual.items()):
        raise AssertionError(f'Archive files disagree with manifest: {root}')
    return actual


def stage3_cases():
    out = CODELAY.parent / 'out'
    manifest = out / 'MAIN_ROWS_MD5.txt'
    units, computed, seen = [], {}, Counter()
    for path in sorted(out.glob('main-*.jsonl')):
        computed.update(verify_archive(out, manifest, [path]))
        with path.open() as stream:
            for line in stream:
                row = json.loads(line)
                cell = row['scenario'], row['rho_permille']
                if not row['syndrome'] or seen[cell] == 8:
                    continue
                units.append(dict(scenario=cell[0], rho=cell[1]/1000, snr_centi_db=row['snr_centi_db'],
                                  frame=row['frame'], syndrome=row['syndrome'],
                                  saved={a: row['arms'][a]['decoded_sha'] for a in ('F0','CODELAY')}))
                seen[cell] += 1
        if len(units) == 32:
            break
    if seen != {(s,r):8 for s in ('U','G') for r in (300,500)}:
        raise AssertionError(f'Wrong CODELAY archive coverage: {seen}')
    return units, computed


def slots(ctx, variant, obs, arrays, cap):
    record = sm.slot_record(arrays, cap, sm.n_nominated(ctx, variant, obs))
    if not record['ok']:
        raise AssertionError(record)
    return record


def replay(ctx, variant, closed, arm, e2_manifest):
    if arm == 'CODELAY':
        units, md5 = stage3_cases()
    else:
        _, guard = sm.e2d.load_kernels()
        root = sm.E2_ROWS_R
        files = sorted(root.glob('rows_shard*.jsonl.gz'))[:sm.G2_FILES]
        md5 = verify_archive(root, e2_manifest, files)
        units = sm.g2_units(root)[:32]
    if len(units) != 32:
        raise AssertionError(f'Insufficient {arm} archive units')
    records = []
    for u in units:
        obs, truth = sm.make_unit(ctx, u['scenario'], u['rho'], u['snr_centi_db'], u['frame'])
        pack = dec, arrays, syndrome, _ = sm.f0_state(ctx, variant, obs, 8)
        saved = {a:u['saved'][a] for a in ('F0',arm)}
        if not syndrome or ('syndrome' in u and syndrome != u['syndrome']):
            raise AssertionError((arm,u,'F0 syndrome mismatch'))
        if arm == 'CODELAY':
            branch = sm.e1d.run_branch(ctx, closed, obs, arrays, 'A1')
            decoded = sm.gd.bits_sha(branch['decoder']['decoded'])
        else:
            part = sm.e2d.process_key(ctx, guard, obs, truth, {}, pack, arms=('A2',))
            decoded = part['arms']['A2']['decoded_sha256']
        got = dict(F0=sm.gd.bits_sha(dec['decoded']), **{arm:decoded})
        if got != saved:
            raise AssertionError((arm,u,got))
        records.append(dict(scenario=u['scenario'],rho=u['rho'],snr=u['snr_centi_db'],frame=u['frame'],
                            syndrome=syndrome,sha=got,slots=slots(ctx,variant,obs,arrays,8)))
    return dict(archive_md5=md5,units=records)


def generator_gate(ctx):
    specs = {p:generation(ctx,p) for p in (6,8,10)}
    results = {str(p):[] for p in specs}
    cells = [('U',.3),('G',.3),('U',.5),('G',.5)]
    for frame in range(16):
        s,rho = cells[frame%len(cells)]
        raw,diag = reference = sm.p1ctx.base(ctx,s,rho,frame)
        draws = fingerprint(raw)
        for p,generator in specs.items():
            generated = sm.p1ctx.base(generator,s,rho,frame)
            if p == 8:
                mismatch = sm.e2_lib.deep_equal(reference,generated)
                if mismatch:
                    raise AssertionError((s,rho,frame,mismatch))
            new,meta = generated
            details = meta['gen_fixed']
            lmax = int(np.max(new['params']['l_i']))
            count = len(new['params']['l_i'])
            power = details['path_power']
            if count != p or abs(power-1) > 1e-12 or lmax > 102 or fingerprint(new) != draws:
                raise AssertionError((p,frame,count,power,lmax))
            results[str(p)].append(dict(frame=frame,scenario=s,rho=rho,power=power,max_delay=lmax,
                                        count=count,redraws=details['redraws']))
    return results


def g1_slots(ctx, variant):
    records = []
    for u in sm.g1_units():
        obs,_ = sm.make_unit(ctx,u['scenario'],u['rho'],u['snr_centi_db'],u['frame'])
        nominal = sm.n_nominated(ctx,variant,obs)
        for cap in sm.G4_CAPS:
            _,arrays,_,_ = sm.f0_state(ctx,variant,obs,cap)
            record = sm.slot_record(arrays,cap,nominal)
            if not record['ok']:
                raise AssertionError((u,record))
            records.append(dict(**u,**record))
    return records


def noise_gate(ctx):
    results = []
    for frame in range(7800,7832):
        raw,diag = sm.p1ctx.base(ctx,'G',.3,frame)
        for snr in sm.ALL_SNR:
            _,obs,_ = sm.gd.observe(ctx,raw,diag,.3,snr)
            _,row = observe_only(obs,True)
            results.append(dict(row,frame=frame,snr=snr,actual=float(obs['sigma2'])))
    return results


def main(out, initial, commit, e2_manifest):
    start = time.perf_counter()
    initial_gate = json.loads(initial.read_text())['G1']
    if initial_gate['identical'] != initial_gate['checked'] or initial_gate['checked'] < 32:
        raise AssertionError('G1 qualification required before additional gates')
    ctx,variant,_,closed,sources = load()
    config = dict(initial_commit=commit,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  environment=ctx.environment,sources=sources,original_g1=str(initial),e2_manifest=str(e2_manifest),
                  threads={key:os.environ[key] for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','CUDA_VISIBLE_DEVICES')},
                  g3_frames=[0,15],g5_frames=[7800,7831],g5_noise_floor=NOISE_FLOOR,g5_snrs=sm.ALL_SNR)
    with out.open('x') as f:
        print(json.dumps(dict(_argv=sys.argv,_config=config)),file=f,flush=True)
        for name, run in [('G2_CODELAY',lambda:replay(ctx,variant,closed,'CODELAY',e2_manifest)),
                          ('G2_A2',lambda:replay(ctx,variant,closed,'A2',e2_manifest)),
                          ('G3',lambda:generator_gate(ctx)),('G4',lambda:g1_slots(ctx,variant)),
                          ('G5',lambda:noise_gate(ctx))]:
            try:
                result = run()
            except Exception as exc:
                print(json.dumps(dict(gate=name,error=repr(exc))),file=f,flush=True)
                raise
            print(json.dumps(dict(gate=name,records=result),allow_nan=False),file=f,flush=True)
            print(f'{name} complete, {time.perf_counter()-start:.1f} s elapsed',flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]))
