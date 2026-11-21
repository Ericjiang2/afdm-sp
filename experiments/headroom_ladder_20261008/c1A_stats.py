"""Frozen A-prefix7 transfer statistics for the archival, paired-frame screen.

The caller seals :func:`static_predictions` before giving this module labels.
This module never fits predictors or reads receiver rows.  Model axis order is
A-prefix7, G-prefix3, L-nearest, C-cliff; parent-frame axis is IDs 0..199.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from scipy.stats import beta

MODELS = ("A", "G", "L", "C")
BINS = np.array([0.0, .05, .10, .20, .40, .60, .80, 1.0])
FAMILIES = ("H1", "H2", "H3", "H4", "H5")
PRIMARY_DELTA = .10
MARGIN = .02
N_PARENTS = 200


def _field(config: dict, name: str) -> Any:
    if name not in config:
        raise ValueError(f"configuration missing {name}")
    return config[name]


def _tie(config: dict) -> tuple[int, int, int, int]:
    return (int(_field(config, "T")) * int(_field(config, "Rc")),
            int(config["Rc"]), int(config["T"]), int(config["rho_permille"]))


def _primary_indices(configs: list[dict]) -> list[int]:
    return [i for i, c in enumerate(configs) if c.get("cohort") == "primary"]


def _novel_indices(configs: list[dict]) -> list[int]:
    return [i for i in _primary_indices(configs)
            if not (configs[i]["family"] == "H3" and configs[i]["L"] in (28, 32))]


def _validate(configs: list[dict], q: np.ndarray, y: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray | None]:
    q = np.asarray(q, dtype=np.float64)
    if q.shape != (4, len(configs), N_PARENTS) or not np.all(np.isfinite(q)) or np.any((q < 0) | (q > 1)):
        raise ValueError("q must be finite probabilities with shape (4, nconfigs, 200)")
    ids = [_field(c, "id") for c in configs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate configuration id")
    for c in configs:
        for key in ("cohort", "snr_centi_db", "rho_permille", "L", "K", "T", "Rc", "nframes"):
            _field(c, key)
        if int(c["nframes"]) != N_PARENTS:
            raise ValueError(f"configuration {c['id']} has wrong parent-frame count")
        if int(c["K"]) != 8 * int(c["L"]):
            raise ValueError(f"configuration {c['id']} has inconsistent K and L")
        if c["cohort"] == "primary" and c.get("family") not in FAMILIES:
            raise ValueError(f"primary configuration {c['id']} has invalid family")
    if y is None:
        return q, None
    y = np.asarray(y)
    if y.shape != (len(configs), N_PARENTS) or not np.all(np.isfinite(y)) or np.any((y != 0) & (y != 1)):
        raise ValueError("y must contain complete binary fixed-endpoint labels with shape (nconfigs, 200)")
    return q, y.astype(np.float64)


def select_config(pe: np.ndarray, candidates: list[int], delta: float = PRIMARY_DELTA,
                  margin: float = MARGIN) -> int | None:
    """Choose the cheapest frozen candidate, or abstain. Oracle uses margin=0."""
    if not 0 < delta < 1 or margin < 0 or margin >= delta:
        raise ValueError("invalid delta/margin")
    pe = np.asarray(pe, dtype=np.float64)
    if pe.ndim != 1 or not np.all(np.isfinite(pe)) or np.any((pe < 0) | (pe > 1)):
        raise ValueError("pe must be a finite probability vector")
    # Candidates are already in the protocol's cost/Rc/T/rho order.
    for i in candidates:
        if i < 0 or i >= len(pe):
            raise ValueError("candidate index out of bounds")
        if pe[i] <= delta - margin:
            return int(i)
    return None


def design_tasks(configs: list[dict]) -> list[dict]:
    tasks: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i in _primary_indices(configs):
        c = configs[i]
        tasks[(int(c["snr_centi_db"]), int(c["L"]))].append(i)
    return [{"snr_centi_db": snr, "L": load,
             "candidate_indices": sorted(indices, key=lambda i: _tie(configs[i]))}
            for (snr, load), indices in sorted(tasks.items())]


def _novel_cells(configs: list[dict]) -> list[dict]:
    cells: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for i in _novel_indices(configs):
        c = configs[i]
        if int(c["Rc"]) in (2, 3, 4):
            cells[(int(c["snr_centi_db"]), int(c["rho_permille"]), int(c["L"]))].append(i)
    out = []
    for key, indices in sorted(cells.items()):
        out.append({"key": key, "family": configs[indices[0]]["family"],
                    "indices": sorted(indices, key=lambda i: _tie(configs[i]))})
    return out


def boundary_panel(configs: list[dict], qbar: np.ndarray,
                   delta: float = PRIMARY_DELTA) -> list[int]:
    qbar = np.asarray(qbar, dtype=np.float64)
    if qbar.shape != (4, len(configs)) or not np.all(np.isfinite(qbar)):
        raise ValueError("qbar must have shape (4, nconfigs) and be finite")
    panel = set()
    for cell in _novel_cells(configs):
        indices = cell["indices"]
        for m in range(4):
            panel.add(indices[int(np.argmin(np.abs(qbar[m, indices] - delta)))])
    return sorted(panel)


def pava(values: np.ndarray, weights: np.ndarray) -> list[float]:
    """Weighted nondecreasing PAVA, used only for the optional Kc diagnostic."""
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if values.ndim != 1 or weights.shape != values.shape or len(values) == 0:
        raise ValueError("PAVA expects nonempty matching vectors")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("PAVA values and positive weights must be finite")
    blocks: list[list[float | int]] = []
    for value, weight in zip(values, weights):
        blocks.append([float(value), float(weight), 1])
        while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
            right = blocks.pop()
            left = blocks.pop()
            total = left[1] + right[1]
            blocks.append([(left[0] * left[1] + right[0] * right[1]) / total,
                           total, left[2] + right[2]])
    return [float(mean) for mean, _, n in blocks for _ in range(int(n))]


def crossing_05(k: np.ndarray, values: np.ndarray) -> dict:
    """First upward .5 crossing; censor at a grid end, never extrapolate."""
    k = np.asarray(k, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if k.ndim != 1 or values.shape != k.shape or len(k) < 2 or not np.all(np.diff(k) > 0):
        raise ValueError("Kc requires at least two increasing K values")
    if not np.all(np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise ValueError("Kc requires finite probabilities")
    if values[0] >= .5:
        return {"status": "left_censored", "bound_K": float(k[0]), "Kc": None}
    for j in range(1, len(k)):
        if values[j - 1] < .5 <= values[j]:
            x = k[j - 1] + (k[j] - k[j - 1]) * (.5 - values[j - 1]) / (values[j] - values[j - 1])
            return {"status": "uncensored", "bound_K": None, "Kc": float(x)}
    return {"status": "right_censored", "bound_K": float(k[-1]), "Kc": None}


def _kc(configs: list[dict], qbar: np.ndarray, ybar: np.ndarray | None = None) -> dict:
    curves: dict[tuple[str, int, int, int], list[int]] = defaultdict(list)
    for i in _primary_indices(configs):
        c = configs[i]
        curves[(str(c["family"]), int(c["rho_permille"]), int(c["T"]), int(c["Rc"]))].append(i)
    rows = []
    good = 0
    uncensored = 0
    for key, indices in sorted(curves.items()):
        indices.sort(key=lambda i: int(configs[i]["K"]))
        k = np.array([configs[i]["K"] for i in indices], dtype=float)
        if len(np.unique(k)) != len(k):
            raise ValueError("duplicate K in Kc curve")
        weights = np.array([configs[i]["nframes"] for i in indices], dtype=float)
        prediction = crossing_05(k, pava(qbar[0, indices], weights))
        row = {"family": key[0], "rho_permille": key[1], "T": key[2], "Rc": key[3],
               "K": k.astype(int).tolist(), "predicted": prediction}
        if ybar is not None:
            observed = crossing_05(k, pava(ybar[indices], weights))
            error = None
            if prediction["status"] == observed["status"] == "uncensored":
                uncensored += 1
                error = float(abs(np.log(prediction["Kc"] / observed["Kc"])))
                good += error <= .15
            row.update(observed=observed, abs_log_error=error)
        rows.append(row)
    result = {"curves": rows}
    if ybar is not None:
        result["uncensored_pairs"] = uncensored
        result["pairs_abs_log_error_le_015"] = good
        result["pair_fraction_conditional_on_uncensored"] = good / uncensored if uncensored else None
    return result


def static_predictions(configs: list[dict], q: np.ndarray,
                       delta_values: tuple[float, ...] = (.1, .2)) -> dict:
    q, _ = _validate(configs, q)
    qbar = q.mean(axis=2)
    tasks = design_tasks(configs)
    choices = {}
    panels = {}
    for delta in delta_values:
        if not 0 < delta < 1:
            raise ValueError("delta outside (0,1)")
        label = format(delta, ".2f")
        choices[label] = [{"snr_centi_db": task["snr_centi_db"], "L": task["L"],
                           "chosen": {model: (None if (i := select_config(qbar[m], task["candidate_indices"], delta)) is None else configs[i]["id"])
                                      for m, model in enumerate(MODELS)}}
                          for task in tasks]
        panels[label] = [configs[i]["id"] for i in boundary_panel(configs, qbar, delta)]
    return {"schema": "c1A-static-predictions/1", "model_order": list(MODELS),
            "nframes": N_PARENTS, "margin": MARGIN,
            "probabilities": [{"id": c["id"], "mean": {model: float(qbar[m, i])
                                                            for m, model in enumerate(MODELS)}}
                              for i, c in enumerate(configs)],
            "design_choices": choices, "boundary_panels": panels,
            "predicted_Kc": _kc(configs, qbar)}


BOOT_B, BOOT_SEED = 20000, 20261017
GAIN_ALPHA = .04 / 12
KILL_ALPHA = .05 / 7
CP_ALPHA = .01 / (2 * 288)


def interval(values, alpha=.025):
    values = np.asarray(values, float)
    if not np.isfinite(values).all():
        raise ValueError('nonfinite bootstrap statistic')
    return dict(lower=float(np.quantile(values, alpha)), upper=float(np.quantile(values, 1-alpha)), tail_alpha=alpha)


def cp_band(events, n=200, alpha=CP_ALPHA):
    if not 0 <= events <= n or not 0 < alpha < .5:
        raise ValueError('invalid binomial interval')
    return dict(lower=0. if events == 0 else float(beta.ppf(alpha, events, n-events+1)),
                upper=1. if events == n else float(beta.ppf(1-alpha, events+1, n-events)), tail_alpha=alpha)


def frame_weights(B=BOOT_B, seed=BOOT_SEED):
    if B < 1:
        raise ValueError('no bootstrap draws')
    return np.random.default_rng(seed).multinomial(200, np.full(200, 1/200), size=B) / 200.


def _risk_weights(configs):
    weights = np.zeros(len(configs))
    for family in FAMILIES:
        ids = [i for i in _novel_indices(configs) if configs[i]['Rc'] in (2,3,4) and configs[i]['family'] == family]
        if not ids:
            raise ValueError(f'empty primary family {family}')
        weights[ids] = 1/(5*len(ids))
    return weights


def _task_weights(tasks):
    snrs = sorted({t['snr_centi_db'] for t in tasks})
    return np.array([1/(len(snrs)*sum(t['snr_centi_db'] == a['snr_centi_db'] for a in tasks)) for t in tasks])


def _choose_batch(pe, candidates, delta, margin):
    eligible = pe[:, candidates] <= delta-margin
    indices = np.asarray(candidates)[eligible.argmax(axis=1)]
    return np.where(eligible.any(axis=1), indices, -1)


def design_batch(configs, qbar, ybar, delta=.1):
    """Reapply the frozen selector and empirical reference to each draw."""
    tasks = design_tasks(configs)
    B = len(ybar)
    cost = np.array([c['T']*c['Rc'] for c in configs])
    J = np.empty((B,4,len(tasks)))
    picked = np.empty((B,4,len(tasks)),int)
    oracle = np.empty((B,len(tasks)),int)
    ff, fa = np.zeros_like(J,bool), np.zeros_like(J,bool)
    rows = np.arange(B)
    for j, task in enumerate(tasks):
        ids = task['candidate_indices']
        ref = _choose_batch(ybar, ids, delta, 0.)
        oracle[:,j] = ref
        for m in range(4):
            chosen = _choose_batch(qbar[:,m], ids, delta, MARGIN)
            picked[:,m,j] = chosen
            selected_pe = ybar[rows,np.maximum(chosen,0)]
            unsafe = (chosen >= 0) & (selected_pe > delta)
            abstain = (chosen < 0) & (ref >= 0)
            safe = (chosen >= 0) & (ref >= 0) & ~unsafe
            ratio = cost[np.maximum(chosen,0)]/cost[np.maximum(ref,0)]-1
            J[:,m,j] = np.where((ref < 0) & (chosen < 0), 0., np.where(safe,np.minimum(1.,ratio),1.))
            ff[:,m,j],fa[:,m,j] = unsafe,abstain
    return dict(J=J,picked=picked,oracle=oracle,false_feasible=ff,false_abstention=fa)


def _boundary_batch(configs,qbar,ybar,delta=.1):
    B = len(ybar)
    error = np.zeros((B,4))
    good_count,total_count = np.zeros((B,4)),np.zeros(B)
    cells = _novel_cells(configs)
    sizes = {f:sum(c['family']==f for c in cells) for f in FAMILIES}
    for cell in cells:
        ids = cell['indices']
        selected = np.argmin(np.abs(qbar[:,:,ids]-delta),axis=2)
        mask = np.zeros((B,len(ids)),bool)
        for m in range(4):
            mask[np.arange(B),selected[:,m]] = True
        denominator = mask.sum(axis=1)
        residual = np.abs(qbar[:,:,ids]-ybar[:,None,ids])
        error += (residual*mask[:,None,:]).sum(axis=2)/denominator[:,None]/(5*sizes[cell['family']])
        good_count += ((residual <= .05)*mask[:,None,:]).sum(axis=2)
        total_count += denominator
    return error,good_count/total_count[:,None]


def _calibration(configs,q,y,weights,wboot):
    result={}
    for m,name in enumerate(MODELS):
        bins=np.minimum(np.searchsorted(BINS,q[m],side='right')-1,len(BINS)-2)
        contributions=[]
        table=[]
        for b in range(len(BINS)-1):
            mask=(bins==b)&(weights[:,None]>0)
            wm=weights[:,None]*mask
            mass=float(wm.sum()/200)
            residual=(wm*(y-q[m])).sum(axis=0)
            contributions.append(residual)
            meanres=float(residual.mean())
            denominator=wboot@wm.sum(axis=0)
            defined=mass>0 and np.all(denominator>0)
            table.append(dict(bin=[float(BINS[b]),float(BINS[b+1])],weighted_mass=mass,
                              records=int(mask.sum()),unique_parents=int(mask.any(axis=0).sum()),
                              predicted=None if not mass else float((wm*q[m]).sum()/(mass*200)),
                              observed=None if not mass else float((wm*y).sum()/(mass*200)),
                              bias=None if not mass else meanres/mass,
                              bias_CI95=None if not defined else interval((wboot@residual)/denominator),
                              CI_status='DEFINED' if defined else 'EMPTY_OR_UNDEFINED_BOOTSTRAP_BIN'))
        # Empty conditional bootstrap groups cannot be dropped to manufacture a CI.
        for b,row in enumerate(table):
            den=wboot@((weights[:,None]*(bins==b)).sum(axis=0))
            if row['weighted_mass'] and np.any(den==0):
                row['bias_CI95']=None
                row['CI_status']='UNDEFINED_EMPTY_BOOTSTRAP_BIN'
        ece_boot=np.abs(wboot@np.stack(contributions,axis=1)).sum(axis=1)
        result[name]=dict(ECE=float(sum(abs(v.mean()) for v in contributions)),ECE_CI95=interval(ece_boot),
                          reliability=table)
    return result


def population_task(configs,ids,bands,chosen,delta=.1):
    costs={i:configs[i]['T']*configs[i]['Rc'] for i in ids}
    possible=[i for i in ids if bands[i]['lower']<=delta]
    definite=[i for i in ids if bands[i]['upper']<=delta]
    cp=min((costs[i] for i in possible),default=None)
    cd=min((costs[i] for i in definite),default=None)
    out=dict(possible_min_cost=cp,definite_min_cost=cd,certified_nonoperable=not possible,
             chosen=None if chosen<0 else configs[chosen]['id'],certified=False)
    if chosen<0:
        out['status']='CERTIFIED_NONOPERABLE' if not possible else 'UNRESOLVED_REJECTION'
        out['certified']=not possible
    elif bands[chosen]['upper']<=delta:
        if cp is None or cd is None:
            raise ValueError('inconsistent population feasible sets')
        out.update(FER_band=bands[chosen],regret_lower=max(0.,costs[chosen]/cd-1),
                   regret_upper=costs[chosen]/cp-1,status='CERTIFIED_RISK_FEASIBLE')
        out['certified']=out['regret_upper']<=.1
    else:
        out.update(FER_band=bands[chosen],status='RISK_FEASIBILITY_UNRESOLVED',regret_lower=None,regret_upper=None)
    return out


def evaluate(configs,q,y,audit=None,bootstrap_draws=BOOT_B,seed=BOOT_SEED):
    q,y=_validate(configs,q,y)
    primary=_primary_indices(configs)
    novel=[i for i in _novel_indices(configs) if configs[i]['Rc'] in (2,3,4)]
    tasks=design_tasks(configs)
    if len(primary)!=288 or len(novel)!=204 or len(tasks)!=23:
        raise ValueError('frozen primary counts violated')
    weights=_risk_weights(configs)
    qmean,ymean=q.mean(axis=2),y.mean(axis=1)
    wb=frame_weights(bootstrap_draws,seed)
    print(f'bootstrap {bootstrap_draws}, synchronized parent IDs; fixed predictors',flush=True)
    # All arrays share the same multinomial draw stream.
    qb=np.stack([wb@q[m].T for m in range(4)],axis=1)
    yb=wb@y.T
    brier_frames=((q-y[None])**2*weights[None,:,None]).sum(axis=1)
    brier=brier_frames.mean(axis=1)
    briergain={name:dict(point=float(brier[m]-brier[0]),interval=interval(wb@(brier_frames[m]-brier_frames[0]),GAIN_ALPHA))
               for m,name in enumerate(MODELS) if m}
    calibration=_calibration(configs,q,y,weights,wb)
    biases={}
    bias_lower=[]
    for f in FAMILIES:
        ids=[i for i in novel if configs[i]['family']==f]
        vec=(y[ids]-q[0,ids]).mean(axis=0)
        draws=wb@vec
        ci=interval(np.abs(draws),KILL_ALPHA)
        biases[f]=dict(observed_minus_predicted=float(vec.mean()),CI95=interval(draws),
                       abs_bias_kill_interval=ci)
        bias_lower.append(ci['lower'])
    edpoint,goodpoint=_boundary_batch(configs,qmean[None],ymean[None])
    edboot,goodboot=_boundary_batch(configs,qb,yb)
    e_delta={name:dict(point=float(edpoint[0,m]),CI95=interval(edboot[:,m]),
                       kill_interval=interval(edboot[:,m],KILL_ALPHA),fraction_error_le_005=float(goodpoint[0,m]),
                       fraction_CI95=interval(goodboot[:,m])) for m,name in enumerate(MODELS)}
    point=design_batch(configs,qmean[None],ymean[None])
    draws=design_batch(configs,qb,yb)
    tw=_task_weights(tasks)
    Jpoint=(point['J'][0]*tw).sum(axis=1)
    Jboot=(draws['J']*tw).sum(axis=2)
    jgain={name:dict(point=float(Jpoint[m]-Jpoint[0]),interval=interval(Jboot[:,m]-Jboot[:,0],GAIN_ALPHA))
           for m,name in enumerate(MODELS) if m}
    ffboot=draws['false_feasible'][:,0].mean(axis=1)
    ffci=interval(ffboot,KILL_ALPHA)
    bands={i:cp_band(int(y[i].sum())) for i in primary}
    perconfig=[dict(id=c['id'],cohort=c['cohort'],FER_observed=float(ymean[i]),
                    FER_predicted={name:float(qmean[m,i]) for m,name in enumerate(MODELS)},
                    signed_error={name:float(qmean[m,i]-ymean[i]) for m,name in enumerate(MODELS)},
                    abs_error={name:float(abs(qmean[m,i]-ymean[i])) for m,name in enumerate(MODELS)},
                    FER_uniform_band=bands.get(i),nominal_cost=c['T']*c['Rc']) for i,c in enumerate(configs)]
    design_rows=[]
    population=[]
    for j,task in enumerate(tasks):
        oracle=int(point['oracle'][0,j])
        entries={}
        for m,name in enumerate(MODELS):
            chosen=int(point['picked'][0,m,j])
            safe=chosen>=0 and ymean[chosen]<=.1 and oracle>=0
            entries[name]=dict(chosen=None if chosen<0 else configs[chosen]['id'],
                               FER=None if chosen<0 else float(ymean[chosen]),
                               delta_violation=None if chosen<0 else max(0.,float(ymean[chosen]-.1)),
                               cost_regret=None if not safe else float((configs[chosen]['T']*configs[chosen]['Rc'])/(configs[oracle]['T']*configs[oracle]['Rc'])-1),
                               J=float(point['J'][0,m,j]),false_feasible=bool(point['false_feasible'][0,m,j]),
                               false_abstention=bool(point['false_abstention'][0,m,j]),
                               bootstrap_same_choice_fraction=float((draws['picked'][:,m,j]==chosen).mean()))
        design_rows.append(dict(snr_centi_db=task['snr_centi_db'],L=task['L'],
                                observed_best=None if oracle<0 else configs[oracle]['id'],models=entries,
                                bootstrap_same_oracle_fraction=float((draws['oracle'][:,j]==oracle).mean())))
        population.append(dict(snr_centi_db=task['snr_centi_db'],L=task['L'],
                               models={name:population_task(configs,task['candidate_indices'],bands,int(point['picked'][0,m,j]))
                                       for m,name in enumerate(MODELS)}))
    fraction_J=float((point['J'][0,0]<=.1).mean())
    certified=float(np.mean([r['models']['A']['certified'] for r in population]))
    gates={
        'A0':dict(pass_gate=bool(audit and audit.get('integrity_pass')),status='PASS' if audit and audit.get('integrity_pass') else 'INCONCLUSIVE',audit=audit),
        'A1':dict(pass_gate=calibration['A']['ECE']<=.05 and all(abs(z['observed_minus_predicted'])<=.05 for z in biases.values()) and e_delta['A']['point']<=.05 and e_delta['A']['fraction_error_le_005']>=.8),
        'A2':dict(pass_gate=briergain['G']['point']>=.005 and all(z['point']>0 and z['interval']['lower']>0 for z in briergain.values())),
        'A3':dict(pass_gate=Jpoint[0]<=.1 and fraction_J>=.8 and all(z['point']>=.05 and z['interval']['lower']>0 for z in jgain.values())),
        'A4':dict(pass_gate=certified>=.8,certified_task_fraction=certified,status='CERTIFIED_FINITE_GRID' if certified>=.8 else 'POPULATION_DESIGN_INCONCLUSIVE')}
    for key in ('A1','A2','A3'):
        gates[key]['status']='PASS' if gates[key]['pass_gate'] else 'NO_PASS'
    agreement=float((point['picked'][0,0]==point['picked'][0,1]).mean())
    kills={
        'K-A1':dict(triggered=e_delta['A']['kill_interval']['lower']>.05 or sum(x>.05 for x in bias_lower)>=2 or ffci['lower']>.2,
                    E_delta_lower=e_delta['A']['kill_interval']['lower'],families_abs_bias_lower_above_005=sum(x>.05 for x in bias_lower),false_feasible_lower=ffci['lower']),
        'K-A2':dict(triggered=briergain['G']['interval']['upper']<.005 and jgain['G']['interval']['upper']<.05),
        'K-A3':dict(triggered=gates['A2']['pass_gate'] and jgain['G']['interval']['upper']<.05 and agreement>=.9,choice_agreement_with_G=agreement),
        'K-A4':dict(triggered=False,status='NO_OBJECT_CROSSING_USED',reason='No future state/truth/per-cell fit entered predictions; Kc is secondary and cannot rescue A1/A3. Protocol has no separate Kc pass threshold.')}
    verdict='ARCHIVAL_TRANSFER_SCREEN_PASS' if all(gates[k]['pass_gate'] for k in ('A0','A1','A2','A3')) else 'NO_PASS'
    if not gates['A0']['pass_gate']:
        verdict='DATA_IMPLEMENTATION_INCONCLUSIVE'
    elif any(k['triggered'] for k in kills.values()):
        verdict='KILL_A_PREFIX7'
    secondary={}
    for delta in (.2,):
        secondary[str(delta)]={'design_choices':static_predictions(configs,q,(delta,))['design_choices'],
                              'J_macro':{name:float((design_batch(configs,qmean[None],ymean[None],delta)['J'][0,m]*tw).sum()) for m,name in enumerate(MODELS)},
                              'primary_rescue_allowed':False}
    return dict(label='ARCHIVAL_TRANSFER_SCREENING',verdict=verdict,gates=gates,kills=kills,
                bootstrap=dict(B=bootstrap_draws,seed=seed,unit='parent frame ID synced all cells/configs',refit=False,
                               reselect_frozen_rules_each_draw=True,gain_endpoint_alpha=GAIN_ALPHA,negative_endpoint_alpha=KILL_ALPHA),
                Brier={name:float(brier[m]) for m,name in enumerate(MODELS)},Brier_gains=briergain,
                calibration=calibration,family_bias_A=biases,E_delta=e_delta,
                J={name:dict(point=float(Jpoint[m]),CI95=interval(Jboot[:,m])) for m,name in enumerate(MODELS)},J_gains=jgain,
                fraction_tasks_J_A_le_010=fraction_J,false_feasible_A=dict(point=float(point['false_feasible'][0,0].mean()),kill_interval=ffci),
                per_configuration=perconfig,empirical_design=design_rows,population_design=population,
                Kc=_kc(configs,qmean,ymean),secondary=secondary,
                limitations=['Retrospective archival/transductive probe screen; no TCOM claim.',
                             'Bootstrap is approximate near discrete feasibility boundaries; empirical oracle is optimistic.',
                             'Population guarantees use uniform CP bands, not plug-in oracle/bootstrap. Nominal cost excludes CE/LDPC/pilot.',
                             'Conditional on SOURCE calibration, known genie support, one N/code/channel/receiver.'])
