"""Post hoc decomposition of the weak projection on the same 2,016 main-v2 units."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import importlib.util
import json
import multiprocessing
from pathlib import Path
import resource
import struct
import sys

import numpy as np
from scipy.linalg import cho_factor, cho_solve


HERE = Path(__file__).resolve().parent
AUDIT_SHA = "985a414d6fd091c788cea80f4869eeef9d72cd43f69932a7c31e6fa0c4584f48"
RECEIPT_SHA = "4ecd41d91581cdcb816a72caac8fca5f3837d78228c2980ec3e7ae3381d1ff1f"
WORKERS = 14
CPU_LIMIT = 110
TERMS = ("a","b1","b2","c","d","geometry")
TOL = 1e-10
THRESHOLD = .60

# Keep the existing audit helper out of the frozen receiver's import inventory.
spec = importlib.util.spec_from_file_location("__first_audit", HERE/"audit.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def initialize():
    assert prior.digest(HERE/"audit.py") == AUDIT_SHA
    prior.initialize()


def split_terms(k, system, Y, B, Q, b, paths, slot, xt_mean, xt_true, xt_diff, noise,
                truth_paths, truth_gains, weak):
    """Return literal terms and the omitted true-versus-fitted Doppler term."""
    c1, c2 = system.c1, system.c2
    keep = np.arange(len(paths)) != slot
    kept = [p for p, retained in zip(paths,keep,strict=True) if retained]
    index = {p.delay:i for i,p in enumerate(truth_paths)}
    fitted_delays = {p.delay for p in kept}
    assert len(fitted_delays) == len(kept) and truth_paths[weak].delay not in fitted_delays

    # An unmatched fitted delay has zero true gain at its fitted geometry.
    matched = [index.get(p.delay) for p in kept]
    true_geometry = [truth_paths[i] if i is not None else p for p,i in zip(kept,matched,strict=True)]
    true_gain = np.array([truth_gains[i] if i is not None else 0j for i in matched])
    missing = [i for i,p in enumerate(truth_paths) if i != weak and p.delay not in fitted_delays]
    h = cho_solve(cho_factor(Q[np.ix_(keep,keep)],lower=True,check_finite=True),b[keep],check_finite=True)
    full_truth = k._responses(xt_true,truth_paths,c1,c2)
    true_support_data = k._responses(xt_true,true_geometry,c1,c2)
    true_support_diff = k._responses(xt_diff,true_geometry,c1,c2)
    true_support_mean = k._responses(xt_mean,true_geometry,c1,c2)
    B_kept = B[:,keep]
    a = full_truth[:,weak] * truth_gains[weak]
    b1 = true_support_data @ (true_gain - h)
    b2 = true_support_diff @ h
    c = full_truth[:,missing] @ truth_gains[missing]
    geometry = (true_support_mean - B_kept) @ h
    return (a,b1,b2,c,noise,geometry), Y - B_kept @ h


def replay(item):
    frame, rows = item
    _, ctx, _, full, *_ = prior.study
    s = ctx.system
    draw = prior.sw.draw_frame(prior.study,frame)
    weak = draw["weak"]
    weak_delay = int(draw["l_i"][weak])
    transform = lambda x: prior.daft(x,s.c1,s.c2,True)
    records = []
    for rho, ratio in prior.CELLS:
        saved = rows[rho,ratio]
        assert saved["defined"]
        base, truth = prior.sw.controlled_base(ctx,draw,rho,ratio,background_clip=prior.v2.BACKGROUND_CLIP)
        obs = prior.sw.observation(ctx,base,rho,4.5)
        _, r1, syndrome = prior.v2.f0_state(prior.study,obs,weak_delay)
        assert bool(syndrome) == saved["triggered"]
        window = prior.v2.window(full,s,obs,r1,ratio)
        assert window == {key:float(value) for key,value in saved["window"].items()}
        mu, _, _ = prior.moments(np.clip(r1["r1_app"],-20,20),1-s.rho)
        true_data = base["data"]/np.sqrt(2*(1-rho))
        xt_true = transform(obs["pilot"] + true_data)
        xt_diff = transform(true_data - mu)
        noise = transform(np.sqrt(obs["sigma2"])*base["noise"])
        out = dict(frame=frame,rho=rho,R=ratio,arms={})

        def capture(arm, kernel, args, opts, result, matrix, pair, anchor):
            logged = saved["arms"][arm]["pair"]
            for key in ("slot","weak_doppler","weak_index","Q"):
                assert pair[key] == logged[key], (frame,rho,ratio,arm,key)
            for key in ("weak_gain","phantom_gain"):
                assert struct.pack("d",pair[key]) == struct.pack("d",logged[key]), (frame,rho,ratio,arm,key)
            Y, x, v, paths = args
            np.testing.assert_array_equal(x,obs["pilot"]+mu)
            E = float(np.vdot(x,x).real)
            assert E == window["E"]
            xt = transform(x)
            B,Q,b,_,_,_ = kernel._system(Y,xt,v,paths,s.c1,s.c2,opts["ridge"],opts["gamma_mode"])
            true_paths = [kernel.Path(int(delay),float(nu))
                          for delay,nu in zip(truth["l_i"],truth["k_real"],strict=True)]
            terms,residual = split_terms(kernel,s,Y,B,Q,b,paths,pair["slot"],xt,xt_true,xt_diff,noise,
                                         true_paths,truth["g_i"],weak)
            wk = kernel.Path(weak_delay,pair["weak_doppler"])
            Bw = kernel._responses(xt,[wk],s.c1,s.c2)[:,0]
            denom = E*truth["g_i"][weak]
            reference = np.vdot(Bw,residual)/denom
            projection = [np.vdot(Bw,t)/denom for t in terms]
            err5 = abs(sum(projection[:5])-reference)/abs(reference)
            err6 = abs(sum(projection)-reference)/abs(reference)
            out["arms"][arm] = dict(reference=[reference.real,reference.imag],
                                    terms={name:[z.real,z.imag] for name,z in zip(TERMS,projection,strict=True)},
                                    five_error=float(err5),six_error=float(err6))

        prior.paired.run_from_r1(prior.study,prior.observers,obs,r1,truth,weak,False,window,audit=capture)
        records.append(out)
    return records


def result_group(rows, arm):
    data = [r["arms"][arm] for r in rows]
    return dict(n=len(rows), projections={term:np.percentile([r["terms"][term][0] for r in data],[25,50,75]).tolist()
                                          for term in TERMS})


def reading_group(rows, arm):
    data = [r["arms"][arm] for r in rows]
    shortfall = sum(1-abs(complex(*r["reference"])) for r in data)
    assert shortfall > 0
    shares = {term:-sum(r["terms"][term][0] for r in data)/shortfall for term in ("b1","b2","c","d","geometry")}
    support = shares["b1"]+shares["b2"]
    outside = shares["c"]+shares["d"]
    return dict(n=len(rows),average_amplitude_shortfall=shortfall/len(rows),shares=shares,
                support_share=support,outside_and_noise_share=outside,
                support_plus_geometry_share=support+shares["geometry"],
                dominant_support_term=max(("b1","b2"),key=lambda key:shares[key]))


def verdict(groups):
    supports = all(g["support_share"] >= THRESHOLD for g in groups)
    falsifies = all(g["outside_and_noise_share"] >= THRESHOLD for g in groups)
    return "SUPPORTED" if supports and not falsifies else "FALSIFIED" if falsifies and not supports else "MIXED"


def seconds():
    usage = [resource.getrusage(t) for t in (resource.RUSAGE_SELF,resource.RUSAGE_CHILDREN)]
    return sum(r.ru_utime+r.ru_stime for r in usage)


def main(out):
    # At most 16 Python processes, each bounded at 110 CPU seconds.
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_LIMIT,CPU_LIMIT))
    first = HERE/"out/audit.json"
    assert prior.digest(first) == RECEIPT_SHA and prior.digest(HERE/"audit.py") == AUDIT_SHA
    frozen = json.loads(first.read_text())["_config"]
    frames = frozen["frames"]
    assert len(frames)*len(prior.CELLS) == frozen["units"] == 2016
    units = prior.saved_rows(frames)
    with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context("spawn"),
                             initializer=initialize) as pool:
        rows = []
        for i, frame_rows in enumerate(pool.map(replay,units),1):
            rows.extend(frame_rows)
            if i % 12 == 0:
                print(f"Replayed {i}/{len(frames)} frames",flush=True)
    assert len(rows) == 2016
    with (out/"projections.jsonl.gz").open("xb") as raw, gzip.GzipFile(filename="",fileobj=raw,mode="wb",mtime=0) as f:
        for row in rows:
            f.write((json.dumps(row,allow_nan=False,separators=(",",":"))+"\n").encode())
    closure = {}
    for arm in prior.ARMS:
        closure[arm] = {}
        for label,key in (("five_terms","five_error"),("including_geometry","six_error")):
            errors = [r["arms"][arm][key] for r in rows]
            nfail = sum(x > TOL for x in errors)
            closure[arm][label] = dict(status="FAIL" if nfail else "PASS",failed=nfail,
                                       max_relative_error=max(errors),n=len(errors))
    reading = {}
    for arm in prior.ARMS:
        groups = {str(rho):reading_group([r for r in rows if r["rho"]==rho and r["R"]<=4],arm)
                  for rho in (.3,.5)}
        reading[arm] = dict(by_rho=groups,verdict=verdict(list(groups.values())))
    cells = [dict(rho=rho,R=ratio,arms={arm:result_group([r for r in rows if (r["rho"],r["R"])==(rho,ratio)],arm)
                                       for arm in prior.ARMS}) for rho,ratio in prior.CELLS]
    cfg = dict(analysis="post hoc",model="gpt-6.2-sol",workers=WORKERS,threads=1,core_hour_cap=.5,
               per_python_cpu_limit_seconds=CPU_LIMIT,source_commit="b4e294cf53cc999448b8fb64e5f38c0a7abce543",
               audit1_sha256=RECEIPT_SHA,source_sha256=prior.digest(Path(__file__)),frames=frames,
               parent_main_manifest_sha256=prior.MANIFEST_SHA,parent_main_freeze_sha256=prior.FREEZE_SHA,
               reference="complex projection reconstructed at the deletion-slot support; prior b_w was not saved per unit",
               support_matching="true path matched by delay; unmatched fitted path has zero true gain at fitted geometry",
               reading="negative sum of signed real terms divided by sum of realized amplitude shortfalls; R<=4 pooled within rho",
               reading_threshold=THRESHOLD,relative_closure_tolerance=TOL,quantiles=[25,50,75])
    doc = dict(_argv=sys.argv,_config=cfg,status="DONE",core_hours=seconds()/3600,units=len(rows),
               cells=cells,closure=closure,reading=reading,projections_sha256=prior.digest(out/"projections.jsonl.gz"))
    assert 0 < doc["core_hours"] <= cfg["core_hour_cap"]
    with (out/"audit2.json").open("x") as f:
        json.dump(doc,f,indent=2,allow_nan=False)
        f.write("\n")
    print("Audit 2 complete",flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True,type=Path)
    main(p.parse_args().out)
