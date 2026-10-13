"""Fixed public-grid objectives, independent calibration and finite-grid sets."""
import time

import numpy as np

from experiments.afdm_efficient_information.score import matrix_pinv


def load_score_model(path):
    from experiments.afdm_efficient_information.score import ScoreRegressor
    with np.load(path) as saved:
        model=ScoreRegressor(float(saved['ridge']))
        for name in ['mean','scale','active','score_mean','score_scale','coefficients','singular_values']:
            setattr(model,name,saved[name].copy())
        model.rank=int(saved['rank'])
    return model


class MomentBank:
    """Frozen common within-training covariance; candidate means built once."""
    def __init__(self,training,training_means,candidate_means,rcond=1e-10):
        started=time.perf_counter()
        training=np.asarray(training,float); training_means=np.asarray(training_means,float)
        candidate_means=np.asarray(candidate_means,float)
        if training.ndim!=2 or len(training)<2 or not training.shape[1] or training_means.shape!=training.shape or candidate_means.ndim!=2 or not len(candidate_means) or candidate_means.shape[1]!=training.shape[1] or not all(np.isfinite(x).all() for x in [training,training_means,candidate_means]):
            raise ValueError('finite matching training residuals and public candidate means required')
        residual=training-training_means
        self.scale=np.sqrt(np.mean(residual**2,axis=0))
        self.active=self.scale>1e-14*max(float(self.scale.max()),1.)
        z=residual[:,self.active]/self.scale[self.active]
        covariance=z.T @ z/len(z)
        self.inverse,self.rank=matrix_pinv(covariance,rcond) if len(covariance) else (np.empty((0,0)),dict(rank=0))
        self.means=candidate_means[:,self.active]/self.scale[self.active]
        self.weighted=self.means @ self.inverse
        self.constant=np.sum(self.means*self.weighted,axis=1)
        self.cost=dict(setup_seconds=time.perf_counter()-started,candidates=len(candidate_means),
            candidate_response_values=int(candidate_means.size),training_rows=len(training),
            covariance_factorizations=1,active_features=int(self.active.sum()))

    def objective(self,group_means,repeats):
        start=time.perf_counter(); f=np.asarray(group_means,float)
        if f.ndim!=2 or f.shape[1]!=len(self.scale) or not np.isfinite(f).all() or repeats<1:
            raise ValueError('finite observed group feature means and positive R required')
        z=f[:,self.active]/self.scale[self.active]
        objective=repeats*(np.sum((z @ self.inverse)*z,axis=1)[:,None]+self.constant[None,:]-2*z @ self.weighted.T)
        return objective,dict(seconds=time.perf_counter()-start,groups=len(f),candidate_objectives=int(objective.size),
            new_candidate_response_values=0,cached_candidate_response_values=int(self.means.size))

    def state(self):
        return dict(scale=self.scale,active=self.active,inverse=self.inverse,means=self.means,
                    rank=np.array(self.rank['rank']))


def aggregate_rows(values,groups,max_repeats,repeats,mean=True):
    values=np.asarray(values)
    if len(values)!=groups*max_repeats or not 1<=repeats<=max_repeats:
        raise ValueError('complete registered groups and legal prefix R required')
    cube=values.reshape(groups,max_repeats,*values.shape[1:])[:, :repeats]
    return cube.mean(axis=1) if mean else cube.sum(axis=1)


def upper_order_statistic(values,alpha):
    """Conservative split-calibration cutoff; no Wilks or continuity assumption."""
    values=np.asarray(values,float)
    if values.ndim!=1 or not len(values) or not np.isfinite(values).all() or not 0<alpha<1:
        raise ValueError('finite calibration scores and alpha in (0,1) required')
    rank=int(np.ceil((len(values)+1)*(1-alpha)))
    if rank>len(values):
        raise ValueError('calibration group count cannot resolve requested alpha')
    return float(np.partition(values,rank-1)[rank-1]),rank


def grid_statistics(objective,candidates,null_value):
    objective=np.asarray(objective,float); candidates=np.asarray(candidates,float)
    if objective.ndim!=2 or candidates.ndim!=2 or objective.shape[1]!=len(candidates) or not np.isfinite(objective).all() or not np.isfinite(candidates).all():
        raise ValueError('finite common-grid candidate objectives required')
    null=candidates[:,0]==null_value
    if not np.any(null): raise ValueError('public null must occur on the grid')
    index=np.argmin(objective,axis=1); best=objective[np.arange(len(index)),index]
    statistic=np.min(objective[:,null],axis=1)-best
    return dict(index=index,estimate=candidates[index],detection=statistic,
                candidate_gap=objective-best[:,None])


def calibrate(objectives_by_condition,candidates,null_value,alpha):
    """Each input condition is a separately generated known public calibration law."""
    if len(objectives_by_condition)!=len(candidates):
        raise ValueError('all public candidate conditions require calibration')
    rows=[]; detection=[]; confidence=[]
    for truth_index,objective in enumerate(objectives_by_condition):
        statistics=grid_statistics(objective,candidates,null_value)
        coverage,rank=upper_order_statistic(statistics['candidate_gap'][:,truth_index],alpha)
        confidence.append(coverage)
        null_cutoff=None
        if candidates[truth_index,0]==null_value:
            null_cutoff,_=upper_order_statistic(statistics['detection'],alpha)
            detection.append(null_cutoff)
        rows.append(dict(condition=truth_index,groups=len(objective),rank=rank,
                         confidence_cutoff=coverage,null_cutoff=null_cutoff))
    return dict(detection_cutoff=max(detection),confidence_cutoff=max(confidence),conditions=rows,
        guarantee='marginal over independent calibration and future group, at each registered finite-grid law; no conditional-on-realized-calibration or continuous-domain guarantee')


def wilson(successes,total,z=1.959963984540054):
    if not 0<=successes<=total or total<=0: raise ValueError('valid independent Bernoulli counts required')
    p=successes/total; denominator=1+z*z/total
    center=(p+z*z/(2*total))/denominator
    half=z*np.sqrt(p*(1-p)/total+z*z/(4*total*total))/denominator
    return [float(center-half),float(center+half)]


def evaluate_grid(objective,candidates,truth_index,null_value,calibration,*,interest='q',unidentifiable=(),randomized_null=None):
    """Truth index is confined to this external scorer, never objective construction."""
    if interest not in ('q','delta') or len(objective)<2 or calibration['confidence_cutoff']<0:
        raise ValueError('q/delta target, at least two groups and nonnegative grid cutoff required')
    statistics=grid_statistics(objective,candidates,null_value); truth=candidates[truth_index]
    inclusion=statistics['candidate_gap']<=calibration['confidence_cutoff']
    rejected=statistics['detection']>calibration['detection_cutoff'] if randomized_null is None else np.asarray(randomized_null,bool)
    selected=statistics['estimate']; errors=selected-truth
    half_gap=np.sqrt(selected[:,0]) if interest=='q' else selected[:,0]
    true_half=np.sqrt(truth[0]) if interest=='q' else truth[0]
    axes=[np.unique(candidates[:,j]) for j in range(candidates.shape[1])]
    boundary=np.column_stack([(selected[:,j]==axis[0])|(selected[:,j]==axis[-1]) for j,axis in enumerate(axes)])
    q_covered=np.array([np.any(candidates[inside,0]==truth[0]) for inside in inclusion])
    widths=np.array([np.ptp(np.sqrt(candidates[inside,0]) if interest=='q' else candidates[inside,0]) for inside in inclusion])
    n=len(objective); target_unidentified=0 in unidentifiable
    mse=(half_gap-true_half)**2
    result=dict(groups=n,rejections=int(rejected.sum()),rejection_rate=float(rejected.mean()),
        rejection_wilson95=wilson(int(rejected.sum()),n),null_condition=bool(truth[0]==null_value),
        parameter_rmse=np.sqrt(np.mean(errors**2,axis=0)).tolist(),parameter_bias=errors.mean(axis=0).tolist(),
        half_gap_rmse=None if target_unidentified else float(np.sqrt(mse.mean())),
        half_gap_mse_standard_error=None if target_unidentified else float(mse.std(ddof=1)/np.sqrt(n)),
        boundary_rates=boundary.mean(axis=0).tolist(),unidentifiable_coordinates=list(unidentifiable),
        target_identifiable=not target_unidentified,
        joint_grid_coverage=float(inclusion[:,truth_index].mean()),
        joint_grid_coverage_wilson95=wilson(int(inclusion[:,truth_index].sum()),n),
        interest_grid_coverage=float(q_covered.mean()),mean_grid_set_size=float(inclusion.sum(axis=1).mean()),
        mean_half_gap_grid_hull_width=float(widths.mean()),empty_grid_sets=int((inclusion.sum(axis=1)==0).sum()),
        fit_failures=0,coverage_scope='finite public candidate grid; projected hull is not a calibrated continuous-parameter interval',
        randomized_information_free_baseline=randomized_null is not None)
    for coordinate in unidentifiable:
        result['parameter_rmse'][coordinate]=None; result['parameter_bias'][coordinate]=None
    return result,dict(indices=statistics['index'],estimates=selected,detection_statistic=statistics['detection'],
                       rejected=rejected,grid_confidence_set=inclusion,boundary=boundary)
