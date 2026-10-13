"""Registered FEATURE/EST development study, no production receiver or decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from experiments.sp_afdm_frozen_20260920.src.physical import daft
from experiments.afdm_higher_order_information.features import (
    CandidateBank, collision_jacobian, nuisance_projection, observed_features,
)
from experiments.afdm_higher_order_information.prior import frozen_components, geometry, small_system
from experiments.afdm_higher_order_information.theory_study import independent_transform

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT/'results/afdm_higher_order_information/ESTIMATION_CONFIG.json'


def fingerprint(array):
    array=np.ascontiguousarray(array)
    return hashlib.sha256(str(array.dtype).encode()+str(array.shape).encode()+array.tobytes()).hexdigest()


def draw_observations(config, count, seed, prior, delta, power, noise):
    """Simulator only. Returned truth arrays are not passed to any fit function."""
    if prior not in ('Gaussian', 'sphere2', 'G0_rank1') or min(count, power, noise) <= 0 or delta < 0:
        raise ValueError('declared prior, positive count/power/noise and nonnegative gap required')
    rng=np.random.default_rng(seed); n=config['n']
    bits=rng.integers(2, size=(count, 2, n))
    d=((1-2*bits[:, 0])+1j*(1-2*bits[:, 1]))/np.sqrt(2)
    z=(rng.normal(size=(count, 2))+1j*rng.normal(size=(count, 2)))/np.sqrt(2)
    unit_noise=(rng.normal(size=(count, n))+1j*rng.normal(size=(count, n)))/np.sqrt(2)
    v=daft(d.T, config['c1'], config['c2'], True).T
    if prior=='Gaussian':
        gains=np.sqrt(power/2)*z
        signal=gains @ np.exp(2j*np.pi*np.outer([-delta, delta], np.arange(n))/n)
    elif prior=='sphere2':
        norm=np.linalg.norm(z, axis=1)
        if np.any(norm==0):
            raise FloatingPointError('zero Gaussian sphere direction')
        gains=np.sqrt(power)*z/norm[:, None]
        signal=gains @ np.exp(2j*np.pi*np.outer([-delta, delta], np.arange(n))/n)
    else:
        # Exact G0 plateau pushforward after source-level support verification:
        # one unit integer atom times a uniform global phase. External sqrt(power)
        # is a declared observation scale; it is not latent unnormalized PDP.
        phase=np.exp(1j*np.angle(z[:, 0]))
        signal=np.broadcast_to(np.sqrt(power)*phase[:, None], (count, n))
        gains=np.empty((count, 0), complex)
    r=signal*v+np.sqrt(noise)*unit_noise
    y=daft(r.T, config['c1'], config['c2']).T
    return y, dict(bits=bits, gain_base=z, unit_noise=unit_noise, gain_truth=gains,
                   exogenous_hash=fingerprint(np.column_stack((d, z, unit_noise))))


def group_means(features, groups, repeats):
    if len(features)!=groups*max(repeats):
        raise ValueError('complete preregistered independent groups required')
    cube=features.reshape(groups, max(repeats), -1)
    return {r:cube[:, :r].mean(axis=1) for r in repeats}


def grid(spec):
    return np.linspace(spec['low'], spec['high'], spec['count'])


def external_metrics(fit, q_truth, power_truth, noise_truth):
    """Truth enters only after a completed fit, for external scoring."""
    parameters=fit['parameters']; target=np.array([q_truth, power_truth, noise_truth])
    error=parameters-target
    return dict(q_rmse=float(np.sqrt(np.mean(error[:, 0]**2))),
        half_gap_rmse=float(np.sqrt(np.mean((fit['half_gap']-np.sqrt(q_truth))**2))),
        parameter_bias=error.mean(axis=0).tolist(), parameter_rmse=np.sqrt(np.mean(error**2, axis=0)).tolist(),
        q_zero_rate=float(np.mean(parameters[:, 0]==0)), q_upper_rate=float(np.mean(parameters[:, 0]==.16)),
        boundary_rates=fit['boundary'].mean(axis=0).tolist(), failed_groups=0,
        nuisance_identification='working Gaussian moment fit; misspecified families separately labeled')


def calculate(output):
    from experiments.afdm_higher_order_information.protocol import dump
    config=json.loads(CONFIG_PATH.read_text()); n=config['n']; lags=config['lags']; repeats=config['repeat_counts']
    start=time.perf_counter(); costs=[]; dense_errors=[]; total_observations=0
    # Validate the actual frozen G0 plateau before using its exact phase reduction.
    system=small_system(n); plateau=[]
    for delta in config['evaluation']['G0_rank1_gaps']:
        geo=geometry(system, 0., delta)
        support=np.flatnonzero(np.any(geo['weights']!=0, axis=1))
        if support.tolist()!=[system.k_max_cap]:
            raise AssertionError('declared G0 phase reduction is outside single-atom plateau')
        plateau.append(dict(delta=delta, retained_atoms=[0], gram_eigenvalues=np.linalg.eigvalsh(geo['gram']).tolist(),
            weight_sha256=fingerprint(geo['weights']), model='exact normalized G0 law times declared external sqrt(tau) scale'))
    dump(output/'plateau_source_checks.json', plateau)

    def prepare(label, count, seed, prior, delta, tau, noise):
        nonlocal total_observations
        started=time.perf_counter()
        y, audit=draw_observations(config, count, seed, prior, delta, tau, noise)
        generation=time.perf_counter()-started
        total_observations+=count
        values, feature_cost=observed_features(y, config['c1'], config['c2'], lags)
        direct=y[:64] @ independent_transform(n, config['c1'], config['c2'], 0).T
        p=abs(direct)**2
        direct_features=np.array([[row.mean(), np.mean(row**2), *[row[0]*(row[a]-row[b]) for a,b in lags]] for row in p])
        error=float(np.max(abs(direct_features-values[:64])))
        dense_errors.append(error)
        if error>config['dense_feature_tolerance']:
            raise AssertionError('frozen inverse DAFT feature disagrees with independent dense reference')
        record=dict(label=label, generation_seconds=generation, feature_cost=feature_cost,
            observations=count, prior=prior, external_truth=dict(delta=delta,power=tau,noise=noise),
            seed=seed, exogenous_hash=audit.pop('exogenous_hash'), dense_max_error=error)
        costs.append(record)
        np.savez(output/(label+'.npz'), observed_daft=y, features=values, **audit)
        return values, record

    training=config['training']
    ftrain,_=prepare('training', training['frames'], [*config['seed'], 0], 'Gaussian', 0., training['power'], training['noise'])
    covariance_start=time.perf_counter()
    covariance=np.cov(ftrain, rowvar=False, ddof=1)
    covariance_seconds=time.perf_counter()-covariance_start
    jacobian=collision_jacobian(n, lags, training['power'], training['noise'])
    weights, projected=nuisance_projection(covariance, jacobian, config['covariance_rcond'])
    if not projected['identifiable']:
        raise AssertionError('registered training moment design has no usable q direction')
    # Nuisance derivatives span the first two features at collision; their tiny
    # floating-point residual is reported, never replaced by an oracle direction.
    np.savez(output/'feature_design.npz', covariance=covariance, jacobian=jacobian, weights=weights,
             training_mean=ftrain.mean(axis=0))
    dump(output/'feature_design.json', dict(projection=projected, covariance_seconds=covariance_seconds,
        covariance_multiply_terms=(len(ftrain)-1)*covariance.size, training_observations=len(ftrain),
        weights=weights.tolist(), lag_selection='fixed quarters before data', inference_scope='Gaussian working law'))

    calibration=config['calibration']; thresholds={}; calibration_rows=[]; null_scores={r:[] for r in repeats}
    for j,(tau,noise) in enumerate(calibration['nuisance']):
        values,record=prepare(f'calibration_{j}', calibration['groups']*max(repeats),
            [*config['seed'], 1, j], 'Gaussian', 0., tau, noise)
        for r,means in group_means(values, calibration['groups'], repeats).items():
            score=means @ weights
            cutoff=float(np.quantile(score, calibration['quantile'], method='higher'))
            null_scores[r].append(cutoff)
            calibration_rows.append(dict(nuisance_index=j, repeats=r, groups=len(means), cutoff=cutoff,
                                         exogenous_hash=record['exogenous_hash']))
    for r in repeats:
        thresholds[r]=max(null_scores[r])
    dump(output/'calibration.json', dict(rows=calibration_rows, thresholds=thresholds,
        scope=config['threshold_scope'], covariance_or_threshold_fitted_on_evaluation=False))

    q_grid=grid(config['q_grid']); tau_grid=grid(config['tau_grid']); noise_grid=grid(config['noise_grid'])
    banks={}; bank_records=[]
    for coord in ('q','delta'):
        unknown=CandidateBank(n,lags,q_grid,tau_grid,noise_grid,covariance,coord)
        banks['unknown',coord]=unknown
        bank_records.append(dict(nuisance='unknown',coordinates=coord,**unknown.setup))
        for j,(tau,noise) in enumerate(config['evaluation']['nuisance']):
            bank=CandidateBank(n,lags,q_grid,[tau],[noise],covariance,coord)
            banks[j,coord]=bank
            bank_records.append(dict(nuisance=f'known_statistical_{j}',coordinates=coord,**bank.setup))
    dump(output/'candidate_banks.json', bank_records)

    rows=[]; coordinate_errors=[]; evaluation=config['evaluation']; case=0
    for prior in evaluation['priors']:
        for j,(tau,noise) in enumerate(evaluation['nuisance']):
            for gap_index,delta in enumerate(evaluation[prior+'_gaps']):
                # Same exogenous arrays across priors at matching registered
                # indices; G0's gap grid differs and is explicitly disclosed.
                values,record=prepare(f'evaluation_{case:02d}',evaluation['groups']*max(repeats),
                    [*config['seed'],2,j,gap_index],prior,delta,tau,noise)
                for r,means in group_means(values,evaluation['groups'],repeats).items():
                    detection=means @ weights > thresholds[r]
                    rows.append(dict(case=case,prior=prior,nuisance='second_order',repeats=r,
                        delta_truth=delta,power_truth=tau,noise_truth=noise,groups=len(means),
                        method='matched_second_moment_Gaussian',identifiable=False,q_rmse=None,
                        reason='covariance=(tau+sigma2)I carries zero q information; no arbitrary gap guess',
                        center_identifiable=False,declared_gap_information='zero' if prior=='G0_rank1' else 'not present in matched covariance'))
                    raw={}
                    for nuisance in ('unknown','known'):
                        qfit=banks['unknown' if nuisance=='unknown' else j,'q'].estimate(means)
                        dfit=banks['unknown' if nuisance=='unknown' else j,'delta'].estimate(means)
                        parameter_error=float(np.max(abs(qfit['parameters']-dfit['parameters'])))
                        objective_error=float(np.max(abs(qfit['objectives']-dfit['objectives'])))
                        coordinate_errors.append(dict(case=case,repeats=r,nuisance=nuisance,
                                                      parameter_error=parameter_error,objective_error=objective_error))
                        if parameter_error!=0 or objective_error>config['coordinate_objective_tolerance']:
                            raise AssertionError('same physical candidate grid changed result with coordinates')
                        for coord,fit in [('q',qfit),('delta',dfit)]:
                            metrics=external_metrics(fit,delta**2,tau,noise)
                            rows.append(dict(case=case,prior=prior,nuisance=nuisance,repeats=r,
                                method='higher_order_'+coord,delta_truth=delta,power_truth=tau,noise_truth=noise,
                                groups=len(means),working_model_identifiable=True,center_identifiable=False,
                                physical_gap_identification='zero on G0 plateau' if prior=='G0_rank1' else 'local control evidence; no global uniqueness claim',
                                model_match=prior=='Gaussian',exogenous_hash=record['exogenous_hash'],
                                detection_rate=float(np.mean(detection)),threshold=thresholds[r],
                                statistical_parameters_supplied=nuisance=='known',cost=fit['cost'],**metrics))
                            raw[nuisance+'_'+coord+'_parameters']=fit['parameters']
                            raw[nuisance+'_'+coord+'_objectives']=fit['objectives']
                            raw[nuisance+'_'+coord+'_boundary']=fit['boundary']
                    np.savez(output/f'fit_{case:02d}_R{r}.npz',observed_feature_means=means,
                        calibrated_detection=detection,**raw)
                case+=1
    if total_observations!=config['new_observations']:
        raise AssertionError('actual observation count differs from preregistration')
    dump(output/'costs.json',dict(data=costs,banks=bank_records,covariance_seconds=covariance_seconds,
                                 total_seconds_before_summary=time.perf_counter()-start))
    dump(output/'coordinate_checks.json',coordinate_errors)
    dump(output/'estimation_cases.json',rows)
    return dict(status='all_registered_cases_retained',new_observations=total_observations,
        evaluation_cases=case,rows=len(rows),training_frames=training['frames'],
        calibration_independent_groups=calibration['groups']*len(calibration['nuisance']),
        evaluation_independent_groups=evaluation['groups']*len(evaluation['nuisance'])*len(evaluation['Gaussian_gaps']),
        repeats_share_prefix=True,prior_families_share_exogenous=True,
        max_dense_feature_error=max(dense_errors),max_coordinate_objective_error=max(x['objective_error'] for x in coordinate_errors),
        feature_projection=projected,thresholds=thresholds,
        second_order_unidentifiable_rows=sum(row.get('identifiable') is False for row in rows),
        fit_failures=sum(row.get('failed_groups',0) for row in rows),
        scalar_candidate_objectives=sum(row.get('cost',{}).get('candidate_objectives',0) for row in rows),
        runtime_seconds=time.perf_counter()-start,
        conclusions='raw per-case error, boundary and detection rates retained; no coordinate advantage expected; G0 platform structurally unidentifiable',
        receiver_calls=0,decoder_calls=0)


if __name__=='__main__':
    from experiments.afdm_higher_order_information.protocol import run
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    config=json.loads(CONFIG_PATH.read_text())
    # Load frozen torch/physical dependencies before the recorder freezes BLAS inventory.
    frozen_components()
    from experiments.afdm_shared_channel_20261004.production_diagnostic import source_paths
    sources=[__file__,Path(__file__).with_name('features.py'),Path(__file__).with_name('test_features.py'),
        Path(__file__).with_name('prior.py'),Path(__file__).with_name('theory_study.py'),
        Path(__file__).with_name('moments.py'),CONFIG_PATH,*source_paths(),
        ROOT/'experiments/afdm_shared_channel_20261004/production_prior.py',
        ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py']
    run(args.stage,config,sources,calculate,wall_seconds=config['max_wall_seconds'])
