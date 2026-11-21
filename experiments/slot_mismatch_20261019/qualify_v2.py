"""Stage 1 qualification and timing only, with no main-run mode."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

import numpy as np

import sm_driver as sm

HERE = Path(__file__).resolve().parent
CODELAY = HERE.parent/'cstate_codelay_sbl_stage3_20261118'/'codelay.py'
CODELAY_SHA = 'a5af12d5f0131f70793904b255d83d9db1edc8c7e9443158f150d61335b4f929'
FAMILIES = {'M': (8,(6,8,10,12)), 'T6': (6,(8,)), 'T10': (10,(8,)), 'N': (8,(8,12))}
FRAMES = (7800,7801)
NOISE_FLOOR = 1e-3


def estimate_noise(y,pilot):
    """Calibrated unit-channel-power moment in the internal observation units."""
    raw = float((np.vdot(y,y).real-np.vdot(pilot,pilot).real)/len(y)-.5)
    return max(NOISE_FLOOR,raw),raw


def observe_only(obs,unknown):
    if not unknown:
        return obs,None
    estimate,raw = estimate_noise(obs['y'],obs['pilot'])
    receipt = dict(estimate=estimate,raw=raw,clipped=raw<NOISE_FLOOR)
    return dict(y=obs['y'],pilot=obs['pilot'],sigma2=estimate),receipt


def load():
    ctx,_,variant = sm.load_all()
    sources = sm.e2d.check_frozen_md5(ctx)
    if any(s['status'] != 'ok' for s in sources.values()):
        raise AssertionError('Frozen sources did not pass the inventory gate')
    if hashlib.sha256(CODELAY.read_bytes()).hexdigest() != CODELAY_SHA:
        raise AssertionError('Stage 3 CODELAY differs from its qualified source')
    sys.path.insert(0,str(CODELAY.parent))
    import codelay
    full = sm.e1d.load_variant()
    return ctx,variant,full,codelay.load(full),sources


def g1(ctx,variant):
    results = []
    for u in sm.g1_units():
        obs,_ = sm.make_unit(ctx,u['scenario'],u['rho'],u['snr_centi_db'],u['frame'])
        opts = dict(rounds=2,iterations=20,ce_mode='soft',gain_mode='joint')
        ref,ra,_ = ctx.native.receive(obs,ctx.system,ctx.code,**opts)
        got,ga,_ = variant.receive(obs,ctx.system,ctx.code,max_paths=8,**opts)
        mismatch = sm.e2_lib.deep_equal(dict(decoded=ref['decoded'],arrays=ra),
                                        dict(decoded=got['decoded'],arrays=ga))
        if mismatch:
            raise AssertionError((u,mismatch))
        results.append(dict(**u,arrays=len(ra),decoded_sha256=sm.gd.bits_sha(ref['decoded']),
                            triggered=bool(ctx.hd.syndrome_weight(ctx,ref['decoded']))))
    if len(results) != 40:
        raise AssertionError('Incomplete G1 population')
    return results


def fingerprint(raw):
    return {field:hashlib.sha256(np.ascontiguousarray(raw[field]).tobytes()).hexdigest()
            for field in ('pilot','info','coded','data','noise')}


def generation(ctx, p):
    model = copy.copy(ctx)
    model.system = copy.copy(ctx.system)
    model.system.P_paths = p
    return model


def timed_branches(ctx,variant,full,closed,uniform,obs,truth,cap,bridged,nom):
    start = time.process_time()
    _,arrays,syndrome,_ = sm.f0_state(ctx,variant,obs,cap)
    seconds = dict(f0=time.process_time()-start,codelay=0.,diag=0.)
    slots = sm.slot_record(arrays,cap,nom)
    if not slots['ok']:
        raise AssertionError(slots)
    bridge = None
    if syndrome:
        start = time.process_time()
        a1 = sm.e1d.run_branch(ctx,closed,obs,arrays,'A1')
        seconds['codelay'] = time.process_time()-start
        start = time.process_time()
        sm.e1d.run_branch(ctx,full,obs,arrays,'A2')
        seconds['diag'] = time.process_time()-start
        if cap not in bridged:
            check = sm.e1d.run_branch(ctx,uniform,obs,arrays,'A1')
            np.testing.assert_array_equal(a1['decoder']['decoded'],check['decoder']['decoded'])
            bridge = sm.gd.bits_sha(check['decoder']['decoded'])
            bridged.add(cap)
    return dict(slot_count=slots['slot_count'],triggered=bool(syndrome),cpu_seconds=seconds,
                bridge_sha256=bridge)


def smoke(family):
    ctx,variant,full,closed,_ = load()
    p,caps = FAMILIES[family]
    generator = ctx if p==8 else generation(ctx,p)
    cells = [('G',.3)] if family=='N' else [(s,r) for s in ('U','G') for r in (.3,.5)]
    bridged = set()
    rows = []

    def reopen(y,x,v,paths,**opts):
        return full.reopen_geometry(y,x,np.full_like(v,v.mean()),paths,**opts)
    uniform = SimpleNamespace(Path=full.Path,reopen_geometry=reopen)

    for frame in FRAMES:
        for scenario,rho in cells:
            start = time.process_time()
            raw_base, diag = sm.p1ctx.base(generator,scenario,rho,frame)
            generated = time.process_time()-start
            shared = fingerprint(raw_base)
            physical_power = float(diag['channel_energy_per_dimension'])
            if abs(physical_power-1) > 1e-9:
                raise AssertionError((family,scenario,frame,physical_power))
            for i,snr in enumerate(sm.ALL_SNR):
                start = time.process_time()
                _,actual,truth = sm.gd.observe(ctx,raw_base,diag,rho,snr)
                obs,noise = observe_only(actual,family=='N')
                input_cpu = time.process_time()-start
                if len(truth['l_i']) != p or max(truth['l_i']) > ctx.system.l_max_cap:
                    raise AssertionError(f'Unexpected true support in {family} at {frame}')
                if noise is not None:
                    noise['true']=float(actual['sigma2'])
                    noise['ratio']=noise['estimate']/noise['true']
                nom = sm.n_nominated(ctx,variant,obs)
                by_cap = {str(s):timed_branches(ctx,variant,full,closed,uniform,obs,truth,s,bridged,nom)
                          for s in caps}
                start = time.process_time()
                a3 = sm.p1ctx.p1_driver.compute_arms(ctx,obs,truth,['A3'])['A3']
                genie_cpu = time.process_time()-start
                if a3['status'] != 'ok':
                    raise AssertionError(f'Failed true-H branch at {family}/{frame}/{snr}')
                rows.append(dict(family=family,frame=frame,scenario=scenario,rho=rho,snr=snr,
                                 p_true=p,physical_power=physical_power,draws=shared,noise=noise,
                                 observation_sha256=hashlib.sha256(np.ascontiguousarray(obs['y']).tobytes()).hexdigest(),
                                 redraws=diag['gen_fixed']['redraws'],nominated=nom,
                                 generation_cpu=generated if i==0 else 0.,
                                 inputs_cpu=input_cpu,genie_cpu=genie_cpu,caps=by_cap))
    print(f'{family}: {len(rows)} old-key timings, CODELAY bridge caps {sorted(bridged)}',flush=True)
    return rows


def projection(rows, scope):
    families = ('M','N') if scope=='minimal' else tuple(FAMILIES)
    max_snr = 700 if scope=='minimal' else 800
    result={}
    per_frame = {f:0. for f in FRAMES}
    scale = 1000 / len(FRAMES)
    for family in families:
        chosen = [r for r in rows if r['family']==family and r['snr']<=max_snr]
        caps = (8,12) if scope=='minimal' else FAMILIES[family][1]
        subtotal = 0.
        for r in chosen:
            seconds = r['generation_cpu']+r['inputs_cpu']+r['genie_cpu']
            seconds += sum(sum(r['caps'][str(s)]['cpu_seconds'].values()) for s in caps)
            subtotal += seconds
            per_frame[r['frame']] += seconds
        result[family]=dict(main_keys=int(len(chosen)*scale),caps=list(caps),
                            projected_core_hours=subtotal*scale/3600)
    total=sum(r['projected_core_hours'] for r in result.values())
    return dict(families=result,main_keys=sum(r['main_keys'] for r in result.values()),
                core_hours=total,per_smoke_frame_core_hours=[v/3.6 for v in per_frame.values()],
                core_hours_plus30pct=1.3*total,wall_hours_at_24_single_thread_workers=1.3*total/24)


def check_rows(rows):
    signatures = {(r['frame'],r['scenario'],r['rho'],r['snr']):r
                  for r in rows if r['family']=='M'}
    for r in rows:
        if r['family']!='M':
            k=(r['frame'],r['scenario'],r['rho'],r['snr'])
            if r['draws']!=signatures[k]['draws']:
                raise AssertionError(f'Paired exogenous streams changed at {k}')
            if r['family']=='N' and r['observation_sha256']!=signatures[k]['observation_sha256']:
                raise AssertionError(f'Unknown-noise input waveform changed at {k}')
    observed=Counter(r['family'] for r in rows)
    assert observed == {'M':64,'T6':64,'T10':64,'N':16}
    noise=[r['noise'] for r in rows if r['noise'] is not None]
    bridge={f:Counter(s for r in rows if r['family']==f for s,c in r['caps'].items()
                     if c['bridge_sha256'] is not None) for f in FAMILIES}
    for f,caps in bridge.items():
        required={s for r in rows if r['family']==f for s,c in r['caps'].items() if c['triggered']}
        assert set(caps)==required and all(n==1 for n in caps.values())
    return dict(rows=dict(observed),known_noise_blind_ratio_min=float(min(r['ratio'] for r in noise)),
                known_noise_blind_ratio_median=float(np.median([r['ratio'] for r in noise])),
                known_noise_blind_ratio_max=float(max(r['ratio'] for r in noise)),
                noise_floor_hits=sum(r['clipped'] for r in noise),bridge=bridge)


def main(out,commit):
    # Hard-coded historical G1/smoke cohorts only.
    start=time.perf_counter()
    ctx,variant,_,_,sources=load()
    gate=g1(ctx,variant)
    if len(os.sched_getaffinity(0))-math.ceil(os.getloadavg()[0])<20:
        raise RuntimeError('Insufficient CPU headroom for four smoke workers')
    out.mkdir(parents=True,exist_ok=False)
    with (out/'g1.json').open('x') as f:
        json.dump(gate,f,indent=2,allow_nan=False)
    print(f'G1 passed {len(gate)}/{len(gate)}',flush=True)
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        rows=[r for batch in pool.map(smoke,FAMILIES) for r in batch]
    checks=check_rows(rows)
    receipt=dict(commit=commit,wall_seconds=time.perf_counter()-start,environment=ctx.environment,
                 source_parity=sources,codelay_source_sha256=CODELAY_SHA,
                 G1=dict(checked=len(gate),identical=len(gate),triggered=sum(r['triggered'] for r in gate),
                         array_count=sorted({r['arrays'] for r in gate})),
                 smoke=checks,minimal=projection(rows,'minimal'),complete=projection(rows,'complete'))
    with (out/'smoke.jsonl').open('x') as f:
        for r in rows:
            print(json.dumps(r,allow_nan=False),file=f)
    with (out/'receipt.json').open('x') as f:
        json.dump(receipt,f,indent=2,allow_nan=False)
    print(json.dumps({k:receipt[k] for k in ('G1','smoke','minimal','complete','wall_seconds')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path)
    parser.add_argument('--commit',required=True)
    args=parser.parse_args()
    if re.fullmatch(r'[0-9a-f]{40}',args.commit) is None:
        parser.error('Expected producing Git commit')
    main(args.out,args.commit)
