"""Quiet CPU timings on frozen keys, with archived response parity."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from time import perf_counter, sleep
from types import FunctionType, SimpleNamespace

import numpy as np

from run import ARMS, EXP, arm, context, decoded, dump, e1, input_record, inputs, observed, write_json

JOINT_ARMS = (*ARMS,'L-hard','diag-off')


class MeasuredDiagnostics:
    def __init__(self):
        self.seconds = 0.

    def exclude(self, operation):
        def wrapper(*args, **kwargs):
            start = perf_counter()
            result = operation(*args, **kwargs)
            self.seconds += perf_counter() - start
            return result

        return wrapper


def timing_variants():
    sys.path.insert(0, str(EXP/'tf_e3b_offgrid_20261017'))
    import e3b_driver as off
    on = off.e3d
    specs = [(on, 'tf_e3_sbl_20261017', ('e3_driver.py','sbl_rx.py')),
             (off,'tf_e3b_offgrid_20261017',('e3b_driver.py','offgrid_refine.py','e3b_lib.py'))]
    for module, exp, files in specs:
        cfg = json.loads((EXP/exp/'out/main/config_shard000.json').read_text())['_config']
        actual = module.own_md5()
        if any(actual[name] != cfg['own_md5'][name] for name in files):
            raise AssertionError(f'SBL timing pipeline source differs from {exp}')
    diagnostics = MeasuredDiagnostics()
    funcs = {}
    for module, label in ((on,'L-hard'),(off,'diag-off')):
        fn = module.process_key
        ns = fn.__globals__.copy()
        for mod, names in [('gd',('score','bits_sha')),
                           ('sbl',('codelay_pairs',)),('crb',('channel_nmse',))]:
            original = ns[mod]
            ns[mod] = SimpleNamespace(**dict(vars(original), **{
                name:diagnostics.exclude(getattr(original,name)) for name in names}))
        if label == 'diag-off':
            ns['OFF'] = ('diag-off',)
            ns['e3d'] = SimpleNamespace(**dict(vars(on), atoms_record=diagnostics.exclude(on.atoms_record),
                                               truth_paths=diagnostics.exclude(on.truth_paths)))
        else:
            for name in ('atoms_record','truth_paths'):
                ns[name] = diagnostics.exclude(ns[name])
        funcs[label] = FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__)
    return on, funcs, diagnostics


def timed_reopen(kernel, receipt):
    def reopen(*args,**kwargs):
        start = perf_counter()
        result = kernel.reopen_geometry(*args,**kwargs)
        receipt.append(perf_counter() - start)
        return result
    return SimpleNamespace(Path=kernel.Path,reopen_geometry=reopen)


def own_timing(ctx,kernels,obs,truth,label):
    receipt = []
    route = timed_reopen(kernels[label],receipt) if label != 'F0' else None
    stamp = perf_counter()
    dec, arrays, syndrome, _ = e1.f0_state(ctx,obs)
    if route is None or not syndrome:
        seconds = perf_counter()-stamp
        result = decoded(ctx,dec,truth)
    else:
        branch = e1.run_branch(ctx,route,obs,arrays,'A1')
        seconds = perf_counter()-stamp
        result = decoded(ctx,branch['decoder'],truth)
    assert len(receipt) == int(route is not None and syndrome != 0)
    return result, seconds, receipt[0] if receipt else None, syndrome


def sb_timing(ctx,routes,diagnostics,cache,grid,obs,truth,data,meta,label):
    diagnostics.seconds = 0.
    start = perf_counter()
    extra = dict(variants=('L-hard',)) if label == 'L-hard' else {}
    value = routes[label](ctx,cache,grid,obs,data,truth,meta,**extra)
    elapsed = perf_counter()-start
    actual = elapsed-diagnostics.seconds
    record = value['variants'][label]
    return dict(errors=record['info_errors'],decoded_sha=record['decoded_sha256']), actual


def latency(values):
    return dict(n=len(values),mean=float(np.mean(values)),median=float(np.median(values)),
                p95=float(np.quantile(values,.95)))


def summarize(rows):
    panels = {}
    for name in ('common','trigger_panel'):
        subset = [r for r in rows if r['panel']==name]
        labels = JOINT_ARMS if name=='common' else ARMS
        strata = {'all':subset}
        strata.update({str(g):[r for r in subset if r['key'][2]==g]
                       for g in sorted({r['key'][2] for r in subset})})
        strata['triggered'] = [r for r in subset if r['syndrome']]
        strata['untriggered'] = [r for r in subset if not r['syndrome']]
        result = {}
        for stratum, values in strata.items():
            if not values:
                continue
            seconds = {a:np.array([r['latency'][a] for r in values]) for a in labels}
            result[stratum] = dict(keys=len(values), triggers=sum(r['syndrome'] != 0 for r in values),
                                   latency={a:latency(x) for a,x in seconds.items()},
                                   relative_to_codelay={
                                       a:dict(ratio_of_means=float(x.mean()/seconds['CODELAY'].mean()),
                                              median_paired_ratio=float(np.median(x/seconds['CODELAY'])))
                                       for a,x in seconds.items() if a!='CODELAY'})
            if stratum=='triggered':
                full, closed = (np.array([r['geometry'][a] for r in values]) for a in ('FULL','CODELAY'))
                result[stratum]['reopen'] = dict(FULL=latency(full),CODELAY=latency(closed),
                                                  full_over_codelay=dict(ratio_of_means=float(full.mean()/closed.mean()),
                                                                         median_paired_ratio=float(np.median(full/closed))))
        panels[name] = result
    return panels


def proc_cpu_times():
    cpus = {}
    for line in Path('/proc/stat').read_text().splitlines():
        name, *values = line.split()
        if name.startswith('cpu') and name[3:].isdigit():
            fields = [int(x) for x in values[:8]]
            cpus[int(name[3:])] = (sum(fields), fields[3] + fields[4])
    return cpus


def pin_quiet_cpu():
    before = proc_cpu_times()
    sleep(1.)
    after = proc_cpu_times()
    utilization = {}
    for cpu in os.sched_getaffinity(0):
        total = after[cpu][0] - before[cpu][0]
        idle = after[cpu][1] - before[cpu][1]
        if total > 0:
            utilization[cpu] = 100 * (total-idle)/total
    chosen = min(utilization, key=lambda cpu:(utilization[cpu], cpu))
    os.sched_setaffinity(0, {chosen})
    return dict(load=list(os.getloadavg()), idle_cpu=chosen,
                measured_utilization_pct=utilization[chosen], host_cpus=len(after))


def run(out, commit):
    pre = pin_quiet_cpu()
    print(f'Quiet timing CPU {pre}',flush=True)
    ctx, full, closed, _ = context()
    kernels = {'FULL':full,'CODELAY':closed}
    on, routes, diagnostic = timing_variants()
    s = ctx.system
    cache, grid = on.PilotCache(), on.sbl.full_grid(s.l_max_cap)
    refs = sorted(json.loads((out/'timing_reference.json').read_text()),
                  key=lambda x:(x['key'][2] == 500,x['key'][3],x['key'][0],x['key'][2]))
    assert len(refs)==200
    prewarm_key = refs[0]['key']
    site,rho,snr,frame = prewarm_key
    _, obs, truth = observed(ctx,inputs(ctx,frame,site,rho),rho,snr)
    cache.columns(obs['pilot'],s.c1,s.c2,*grid)
    # Warm native tensor and solver paths using a paid panel input, without measuring it.
    e1.f0_state(ctx,obs)
    rows=[]
    started=perf_counter()
    with (out/'timing.jsonl').open('x') as handle:
        for index, ref in enumerate(refs):
            site,rho,snr,frame=ref['key']
            raw, obs, truth=observed(ctx,inputs(ctx,frame,site,rho),rho,snr)
            assert input_record(raw,obs)==ref['inputs']
            labels=ARMS if snr==500 else JOINT_ARMS
            cache.columns(obs['pilot'],s.c1,s.c2,*grid)
            offset=index%len(labels)
            order=labels[offset:]+labels[:offset]
            times,geometry = {},{}
            for a in order:
                if a in ARMS:
                    got, times[a], geom, syndrome = own_timing(ctx,kernels,obs,truth,a)
                    assert syndrome==ref['syndrome']
                    if geom is not None:
                        geometry[a]=geom
                else:
                    meta=dict(scenario=site,rho_permille=rho,snr_centi_db=snr,frame=frame)
                    got,times[a]=sb_timing(ctx,routes,diagnostic,cache,grid,obs,truth,
                                          raw['data']/np.sqrt(2*(1-rho/1000)),meta,a)
                if got!=ref['arms'][a]:
                    raise AssertionError(f'Timing output drift in {ref["key"]} / {a}: {got}')
            row=dict(panel='trigger_panel' if snr==500 else 'common',key=ref['key'],
                     syndrome=ref['syndrome'],order=order,latency=times,geometry=geometry)
            dump(row,handle)
            rows.append(row)
            if index==9:
                common=(perf_counter()-started)*10
                if common>1320:
                    raise TimeoutError(f'Timing kickoff projects {common:.1f}s before the 5 dB panel')
            if (index+1)%25==0:
                print(f'Quiet timing {index+1}/200 after {perf_counter()-started:.1f}s',flush=True)
    write_json(out/'timing_summary.json',dict(cpu=pre,end_load=list(os.getloadavg()),
               wall_seconds=perf_counter()-started,panels=summarize(rows),timing_commit=commit,
               accuracy_commit=json.loads((out/'gate.json').read_text())['commit']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path)
    parser.add_argument('--commit',required=True)
    args=parser.parse_args()
    if re.fullmatch(r'[0-9a-f]{40}', args.commit) is None:
        parser.error('Expected audited timing commit')
    run(args.out,args.commit)
