"""Finite worst-nuisance power design; no receiver calls, no remote dispatch.

Default: compute deterministic sufficient n only. --run-mc explicitly runs
10000+ repetitions at each computed n on the finite registered nuisance grid.
Result is a resource quotation input, never permission to generate confirmation.
Run from project root with PYTHONPATH=. and NumPy/SciPy installed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys
import time

import numpy as np
from afdm_sp_joint_unrolled import supplement_statistics as stats


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def joint_scenario(coefficients, truth, mode):
    c = np.asarray(coefficients, dtype=float)
    states = stats.joint_states(len(c))
    if c.sum() != 0 or not np.all(np.abs(c) == 1):
        raise ValueError('registered joint scenarios require balanced +/-1 contrasts')

    def independent(target, center=.5):
        margins = center + target*c/len(c)
        if np.any(margins < 0) or np.any(margins > 1):
            raise ValueError('incompatible joint scenario truth')
        return np.prod(np.where(states, margins, 1-margins), axis=1)

    if mode == 'independent':
        p = independent(truth)
    elif mode == 'common_difficulty':
        p = .5*independent(truth, .15)+.5*independent(truth, .65)
    elif mode == 'complementary':
        neutral = np.flatnonzero((states @ c == 0) & (states.sum(axis=1) > 0) & (states.sum(axis=1) < len(c)))
        state = int(neutral[0])
        p = .1*independent(truth/.1)
        p[state] += .45
        p[(2**len(c)-1)^state] += .45
    else:
        raise ValueError('unknown nuisance mode')
    if not np.isclose(p @ states @ c, truth, rtol=0, atol=1e-12):
        raise ArithmeticError('joint generator effect differs from design truth')
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run-mc', action='store_true')
    parser.add_argument('--repetitions', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=20260910)
    args = parser.parse_args()
    if args.repetitions < 10000 or args.seed < 0:
        parser.error('repetitions must be >=10000 and seed nonnegative')
    manifest = json.loads(args.manifest.read_text())
    families = manifest['families']
    if set(families) != {'F_H','F_M','F_A','F_I','F_P','F_R','F_C'}:
        raise ValueError('expected exactly seven families')
    if not np.isclose(sum(v['alpha'] for v in families.values()), .05, atol=1e-15, rtol=0):
        raise ValueError('family alpha budget differs from .05')
    args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    designs, mapping = {}, []
    for family, data in families.items():
        contrasts = data['contrasts']
        if data['m_max'] != len(contrasts) or len({c['id'] for c in contrasts}) != len(contrasts):
            raise ValueError(f'invalid multiplicity or duplicate ID in {family}')
        for contrast in contrasts:
            if family == 'F_C':
                mapping.append({'family':family,'contrast':contrast['id'],
                                'status':'OPEN_TIMING_PILOT_AND_TAIL_MODEL','n':None})
                continue
            c = contrast['coefficients']
            for proposition in contrast['propositions']:
                spec = manifest['propositions'][proposition]
                # Paired CP components are W,L. Joint CP uses actual arm margins.
                key = f'{family}-k{len(c)}-{proposition}'
                if key not in designs:
                    bound = stats.sufficient_n(c, spec['gap'], m=data['m_max'],
                                               alpha_family=data['alpha'], beta_error=.1)
                    designs[key] = {'family':family,'method':contrast['method'],
                                    'coefficients':c,'proposition':proposition,
                                    'engine_proposition':spec['engine'],'truth':spec['truth'],
                                    'alpha_family':data['alpha'],'m':data['m_max'],
                                    'bound':bound,'status':'DISTRIBUTION_FREE_SUFFICIENT_N_NOT_RESOURCE_ADMITTED'}
                elif designs[key]['coefficients'] != c:
                    raise ValueError('design key collision: different coefficient pattern')
                mapping.append({'family':family,'contrast':contrast['id'],
                                'proposition':proposition,'design_key':key})
    # Coverage/power simulations are implementation checks at guaranteed n.
    # The theorem, not this finite nuisance grid, provides the worst-case claim.
    mc_index = []
    if args.run_mc:
        for key, design in designs.items():
            n, c, truth = design['bound']['n'], design['coefficients'], design['truth']
            scenarios = [('q'+str(q),q) for q in [.05,.1,.15,.25,.5,1]] if len(c)==2 else [(mode,None) for mode in ['independent','common_difficulty','complementary']]
            for label, q in scenarios:
                common = dict(m=design['m'],alpha_family=design['alpha_family'],repetitions=args.repetitions,seed=args.seed)
                result = stats.paired_power(n,q,truth,**common) if len(c)==2 else stats.joint_power(n,joint_scenario(c,truth,label),c,**common)
                result['nuisance_scenario'] = label
                result['design_key'] = key
                result['required_proposition'] = design['engine_proposition']
                path = args.out/f'{key}-{label}.json'
                with path.open('x') as h:json.dump(result,h,indent=2,allow_nan=False)
                mc_index.append({'file':path.name,'sha256':sha(path)})
                print(path.name,flush=True)
    payload = {'status':'PLANNING_DESIGN_COMPLETE','receiver_confirmation_authorized':False,
               'command':shlex.join([sys.executable,*sys.argv]),'exit_code':0,
               'source_sha256':sha(__file__),'engine_sha256':sha(stats.__file__),
               'manifest_sha256':sha(args.manifest),'seed':args.seed,
               'repetitions':args.repetitions,'mc_executed':args.run_mc,
               'designs':designs,'contrast_design_mapping':mapping,'mc_files':mc_index,
               'wall_seconds':time.monotonic()-start,
               'limitations':['Actual arm identities, hashes, fixed n and measured costs require family admission.',
                             'No timing n claimed: unbounded cost mean/p95 cannot use binary Hoeffding.',
                             'D_mech empirical nuisance unavailable; universal bound substitutes for nuisance restriction, not receiver evidence.',
                             'The finite MC grid is not exhaustive. Proof assumes independent exogenous blocks; cross-SNR observations never increase n.',
                             'No planned sufficient n has been executed on receiver data.']}
    with (args.out/'design.json').open('x') as h:json.dump(payload,h,indent=2,allow_nan=False)
    print(json.dumps({'design_count':len(designs),'mc_count':len(mc_index),
                      'maximum_sufficient_n':max(d['bound']['n'] for d in designs.values())}),flush=True)


if __name__ == '__main__':
    main()
