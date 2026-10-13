"""Saved-data known-nuisance oracle and candidate ambiguity, no new observations."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_efficient_information.inference import upper_order_statistic, wilson
from experiments.afdm_efficient_information.protocol import ROOT, ARTIFACT, dump, run

CONFIG_PATH=ARTIFACT/'ORACLE_IDENTIFIABILITY_CONFIG.json'


def read_json(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def resolve(path):
    path=Path(path)
    return path if path.is_absolute() else ROOT/path


class SavedStage:
    """Verify each consumed artifact against a pre-bound completed attempt."""
    def __init__(self,stage,expected):
        self.folder=ARTIFACT/stage; self.stage=stage; self.checked={}
        for name in ('registration.json','attempt.json'):
            path=self.folder/name
            if sha(path)!=expected[name]: raise ValueError(f'bound input record changed: {path}')
        self.registration=read_json(self.folder/'registration.json')
        self.attempt=read_json(self.folder/'attempt.json')
        if self.attempt['status']!='complete': raise ValueError('only complete source stages are admissible')
        if self.registration['git_head']!=expected['git_head']: raise ValueError('source commit differs from bound input')
        self.config=self.registration['config']; self.check(self.folder/'registration.json')
        for key in ('score_model','actual_score_model','control_score_model'):
            if key not in self.config: continue
            path=resolve(self.config[key]); relative=str(path.relative_to(ROOT))
            digest=self.registration['source_sha256'][relative]
            if sha(path)!=digest: raise ValueError(f'original source model changed: {path}')
            self.checked[relative]=digest

    def check(self,path):
        path=Path(path); relative=str(path.relative_to(ROOT))
        expected=self.attempt['artifact_sha256'][relative]
        if sha(path)!=expected: raise ValueError(f'original artifact changed: {path}')
        self.checked[relative]=expected
        return path

    def json(self,name):
        return read_json(self.check(self.folder/name))

    def npz(self,name):
        path=self.check(self.folder/name)
        with np.load(path,allow_pickle=False) as saved:
            return {key:saved[key].copy() for key in saved.files}

    def observation_index(self,name):
        # Read only metadata arrays, not another copy of the original observations.
        path=self.check(self.folder/name)
        with np.load(path,allow_pickle=False) as saved:
            return {key:saved[key].copy() for key in ('candidates','calibration_slices','evaluation_slices')}


def validate_candidates(candidates):
    candidates=np.asarray(candidates,float)
    if candidates.ndim!=2 or len(candidates)<2 or candidates.shape[1]<2 or not np.isfinite(candidates).all():
        raise ValueError('finite target-first public candidate grid required')
    if len(np.unique(candidates,axis=0))!=len(candidates): raise ValueError('candidate IDs must be unique physical grid points')
    return candidates


def oracle_pairs(candidates,null_value):
    """Public simple-vs-simple alternatives; nuisance is explicitly oracle-known."""
    candidates=validate_candidates(candidates); pairs=[]
    for alt in np.flatnonzero(candidates[:,0]>null_value):
        matching=np.flatnonzero((candidates[:,0]==null_value)&np.all(candidates[:,1:]==candidates[alt,1:],axis=1))
        if len(matching)!=1: raise ValueError('each alternative needs exactly one same-nuisance null')
        pairs.append([int(matching[0]),int(alt)])
    if not pairs: raise ValueError('nonempty public alternative set required')
    return np.array(pairs,int)


def grouped_logpdf(logpdf,slices,groups,max_repeats,repeats,offset):
    logpdf=np.asarray(logpdf,float); slices=np.asarray(slices,int)
    if logpdf.ndim!=2 or not np.isfinite(logpdf).all() or not 1<=repeats<=max_repeats:
        raise ValueError('finite saved densities and legal registered R prefix required')
    rows=[]
    for begin,end in slices:
        begin-=offset; end-=offset
        if begin<0 or end>len(logpdf) or end-begin!=groups*max_repeats:
            raise ValueError('saved observation partition does not match likelihood rows')
        rows.append(logpdf[begin:end].reshape(groups,max_repeats,-1)[:,:repeats].sum(axis=1))
    return np.array(rows)


def bernoulli(values):
    values=np.asarray(values,bool)
    if values.ndim!=1 or not len(values): raise ValueError('nonempty independent-group flags required')
    count=int(values.sum())
    return dict(count=count,groups=len(values),rate=float(values.mean()),wilson95=wilson(count,len(values)))


def mean_se(values):
    values=np.asarray(values,float)
    if values.ndim!=1 or len(values)<2 or not np.isfinite(values).all():
        raise ValueError('at least two finite independent-group values required')
    return dict(mean=float(values.mean()),standard_error=float(values.std(ddof=1)/np.sqrt(len(values))))


def np_oracle(calibration,null_evaluation,alt_evaluation,null_id,alt_id,alpha):
    """Inputs are grouped full-likelihood rows, with no fitted original receiver."""
    cal=calibration[:,alt_id]-calibration[:,null_id]
    null=null_evaluation[:,alt_id]-null_evaluation[:,null_id]
    alt=alt_evaluation[:,alt_id]-alt_evaluation[:,null_id]
    cutoff,rank=upper_order_statistic(cal,alpha)
    raw=dict(calibration_llr=cal,evaluation_null_llr=null,evaluation_alt_llr=alt,
             null_rejected=null>cutoff,alt_rejected=alt>cutoff)
    result=dict(cutoff=cutoff,rank=rank,alpha=alpha,calibration_groups=len(cal),
        calibration_marginal_error_bound=(len(cal)+1-rank)/(len(cal)+1),
        false_alarm=bernoulli(raw['null_rejected']),power=bernoulli(raw['alt_rejected']),
        null_llr=mean_se(null),alt_llr=mean_se(alt),
        scope='finite independently calibrated known-nuisance/known-alternative reference, not an empirical upper bound',
        kl_scope='LLR means are Monte Carlo diagnostics only; no certified KL or information bound')
    return result,raw


def paired_decisions(oracle,original):
    oracle=np.asarray(oracle,bool); original=np.asarray(original,bool)
    if oracle.shape!=original.shape or oracle.ndim!=1: raise ValueError('same-group paired decisions required')
    difference=oracle.astype(float)-original.astype(float)
    return dict(groups=len(oracle),both_reject=int((oracle&original).sum()),oracle_only=int((oracle&~original).sum()),
        original_only=int((~oracle&original).sum()),neither=int((~oracle&~original).sum()),
        oracle=bernoulli(oracle),original=bernoulli(original),oracle_minus_original=mean_se(difference))


def check_calibration(objectives,candidates,null_value,alpha,record,tolerance):
    """Recompute all saved method calibration rows without changing any cutoff."""
    null=candidates[:,0]==null_value; detection=[]; confidence=[]; errors=[]
    conditions={row['condition']:row for row in record['conditions']}
    if set(conditions)!=set(range(len(candidates))): raise ValueError('incomplete conditional calibration IDs')
    for condition,objective in enumerate(objectives):
        best=objective.min(axis=1); original=conditions[condition]
        cutoff,rank=upper_order_statistic(objective[:,condition]-best,alpha)
        confidence.append(cutoff); errors.append(abs(cutoff-original['confidence_cutoff']))
        if original['groups']!=len(objective) or original['rank']!=rank:
            raise ValueError('saved calibration sample count or rank changed')
        if null[condition]:
            cutoff,_=upper_order_statistic(objective[:,null].min(axis=1)-best,alpha)
            detection.append(cutoff); errors.append(abs(cutoff-original['null_cutoff']))
        elif original['null_cutoff'] is not None:
            raise ValueError('alternative unexpectedly has a null calibration cutoff')
    errors.extend([abs(max(detection)-record['detection_cutoff']),abs(max(confidence)-record['confidence_cutoff'])])
    maximum=float(max(errors))
    if maximum>tolerance: raise ValueError('saved method calibration differs from complete matrix reconstruction')
    return maximum


def known_eta_mle(grouped,candidates,condition,interest):
    candidates=validate_candidates(candidates); grouped=np.asarray(grouped,float)
    allowed=np.flatnonzero(np.all(candidates[:,1:]==candidates[condition,1:],axis=1))
    if grouped.ndim!=2 or grouped.shape[1]!=len(candidates) or not np.isfinite(grouped).all() or interest not in ('q','delta'):
        raise ValueError('full saved likelihood and legal target coordinate required')
    selected=allowed[np.argmax(grouped[:,allowed],axis=1)]
    coordinate=candidates[selected,0]; truth=candidates[condition,0]
    delta=np.sqrt(coordinate) if interest=='q' else coordinate
    true_delta=np.sqrt(truth) if interest=='q' else truth
    squared=(delta-true_delta)**2
    result=dict(groups=len(selected),allowed_candidate_ids=allowed.tolist(),
        target_coordinate_rmse=float(np.sqrt(np.mean((coordinate-truth)**2))),
        target_coordinate_bias=float(np.mean(coordinate-truth)),delta_rmse=float(np.sqrt(squared.mean())),
        delta_bias=float(np.mean(delta-true_delta)),delta_mse=mean_se(squared),
        interest_boundary=bernoulli((coordinate==candidates[allowed,0].min())|(coordinate==candidates[allowed,0].max())),
        tie_break='first original candidate ID attaining the maximum; same physical target grid',
        scope='truth nuisance supplied only to this labelled oracle; no deployable known-nuisance claim')
    return result,selected,squared,allowed


def count_distribution(values):
    unique,counts=np.unique(values,return_counts=True)
    return [dict(candidates=int(value),groups=int(count)) for value,count in zip(unique,counts)]


def ambiguity(objective,candidates,selected_indices,multiplier):
    """Exact floating ties and a frozen machine-resolution near-minimum set."""
    candidates=validate_candidates(candidates); objective=np.asarray(objective,float)
    selected=np.asarray(selected_indices,int)
    if objective.ndim!=2 or objective.shape[1]!=len(candidates) or not np.isfinite(objective).all() or selected.shape!=(len(objective),):
        raise ValueError('complete finite objective and original chosen IDs required')
    if not np.array_equal(selected,np.argmin(objective,axis=1)):
        raise ValueError('original first-argmin ID must remain unchanged')
    eps=float(multiplier)*np.finfo(float).eps
    if not np.isfinite(eps) or eps<=0: raise ValueError('positive preregistered epsilon multiplier required')
    minimum=objective.min(axis=1); gaps=objective-minimum[:,None]
    tolerance=eps*np.maximum(1.,np.max(abs(objective),axis=1))
    sets={'exact':gaps==0,'tolerance':gaps<=tolerance[:,None]}
    raw=dict(selected_indices=selected,row_tolerance=tolerance)
    result={}
    for name,inside in sets.items():
        joint=inside.sum(axis=1)
        interest=np.array([len(np.unique(candidates[row,0])) for row in inside])
        nuisance=np.array([len(np.unique(candidates[row,1:],axis=0)) for row in inside])
        coordinate=np.array([[len(np.unique(candidates[row,j])) for j in range(candidates.shape[1])] for row in inside])
        raw.update({name+'_set':inside,name+'_joint_counts':joint,name+'_interest_counts':interest,
                    name+'_nuisance_counts':nuisance,name+'_coordinate_counts':coordinate})
        result[name]=dict(joint_multiple=bernoulli(joint>1),interest_multiple=bernoulli(interest>1),
            nuisance_multiple=bernoulli(nuisance>1),coordinate_multiple=[bernoulli(coordinate[:,j]>1) for j in range(coordinate.shape[1])],
            joint_count_distribution=count_distribution(joint),interest_count_distribution=count_distribution(interest),
            nuisance_count_distribution=count_distribution(nuisance))
    result.update(groups=len(objective),selected_indices_unchanged=True,maximum_row_tolerance=float(tolerance.max()),
        interpretation='finite saved objective ties or near-ties, not a proof of full-distribution physical nonidentifiability')
    return result,raw


def moment_equivalence(means,inverse,multiplier):
    """Equality of frozen quadratic criterion coefficients; near is NOT transitive."""
    means=np.asarray(means,float); inverse=np.asarray(inverse,float)
    if means.ndim!=2 or inverse.shape!=(means.shape[1],means.shape[1]) or not np.isfinite(means).all() or not np.isfinite(inverse).all():
        raise ValueError('matching finite normalized candidate means and frozen precision required')
    weighted=means@inverse
    coefficients=np.column_stack([weighted,np.sum(means*weighted,axis=1)])
    exact=np.all(coefficients[:,None,:]==coefficients[None,:,:],axis=2)
    pair_scale=np.maximum(1.,np.maximum(abs(coefficients[:,None,:]),abs(coefficients[None,:,:])))
    nearby=np.all(abs(coefficients[:,None,:]-coefficients[None,:,:])<=float(multiplier)*np.finfo(float).eps*pair_scale,axis=2)
    classes=[]; class_ids=np.full(len(means),-1,int)
    for candidate in range(len(means)):
        if class_ids[candidate]>=0: continue
        ids=np.flatnonzero(exact[candidate]); class_ids[ids]=len(classes); classes.append(ids.tolist())
    return dict(exact_classes=classes,nearby_candidate_sets=[np.flatnonzero(row).tolist() for row in nearby],
        exact_class_count=len(classes),criterion='Q/R=z^T P z+c_i-2 z^T w_i; coefficients (w_i,c_i) from saved arrays',
        scope='exact equality of stored-coefficient polynomials; floating objective evaluation may introduce roundoff',
        nearby_scope='coordinatewise machine-tolerance neighbors, NOT a partition or transitive equivalence'),dict(
        coefficient_rows=coefficients,exact_class_ids=class_ids,exact_equal_matrix=exact,nearby_matrix=nearby)


def structural_status(family,method):
    if family=='control' and method=='second_gaussian':
        return dict(coordinates=[0,1],status='inherited_analytic',scope='working Gaussian covariance (tau+noise)I is independent of q and mu; not the full physical mixture')
    if family=='control' and method in ('old_T','powers'):
        return dict(coordinates=[1],status='inherited_analytic',scope='control power-feature distribution is independent of center mu by deterministic phase rotation')
    return dict(coordinates=[],status='not_established',scope='no new proof of complete physical-distribution identifiability or nonidentifiability inferred from finite objective ties')


def calculate(output):
    config=read_json(CONFIG_PATH); started=time.perf_counter()
    oracle_rows=[]; paired_rows=[]; mle_rows=[]; mle_paired_rows=[]; ambiguity_rows=[]; equivalences=[]; input_audit=[]
    comparison_max_error=0.; calibration_max_error=0.
    for family,spec in config['inputs'].items():
        stage=SavedStage(spec['stage'],spec['records']); result=stage.json('results.json'); source_rows=stage.json('cases.json')
        source_lookup={(row['method'],row['repeats'],row['condition']):row for row in source_rows}
        if len(source_lookup)!=len(source_rows): raise ValueError('duplicate original evaluation keys')
        index=stage.observation_index(spec['observations']); candidates=validate_candidates(index['candidates'])
        likelihood=stage.npz('likelihoods.npz')[spec['likelihood_key']]
        offset=int(index['calibration_slices'][0,0]); max_r=max(result['repeats']); null_value=float(candidates[:,0].min())
        pairs=oracle_pairs(candidates,null_value); grouped={}
        for r in result['repeats']:
            for split,key in [('calibration','calibration_groups'),('evaluation','evaluation_groups')]:
                grouped[split,r]=grouped_logpdf(likelihood,index[split+'_slices'],stage.config[key],max_r,r,offset)
        # Check the exact/reference raw's registered calibration and evaluation
        # against the saved complete likelihood before building new contrasts.
        calibration_record=stage.json('calibration.json')
        for r in result['repeats']:
            for method in result['methods']:
                saved_cal=stage.npz(f'calibration_{method}_R{r}.npz')['objectives']
                if saved_cal.shape!=(len(candidates),stage.config['calibration_groups'],len(candidates)) or not np.isfinite(saved_cal).all():
                    raise ValueError('incomplete original method calibration matrix')
                if len(calibration_record[f'{method}_R{r}']['conditions'])!=len(candidates):
                    raise ValueError('original conditional calibration record is incomplete')
                calibration_max_error=max(calibration_max_error,check_calibration(saved_cal,candidates,null_value,
                    stage.config['alpha'],calibration_record[f'{method}_R{r}'],config['saved_objective_absolute_tolerance']))
                if method==spec['reference_method']:
                    error=float(np.max(abs(saved_cal+2*grouped['calibration',r])))
                    comparison_max_error=max(comparison_max_error,error)
                    if error>config['saved_objective_absolute_tolerance']: raise ValueError('saved likelihood/calibration objective mismatch')
        source_raw={}
        for r in result['repeats']:
            for method in result['methods']:
                for condition in range(len(candidates)):
                    filename=f'evaluation_{method}_R{r}_c{condition:02d}.npz'
                    original=stage.npz(filename)
                    if len(original['objective'])!=stage.config['evaluation_groups']: raise ValueError('original evaluation group count changed')
                    if method==spec['reference_method']:
                        error=float(np.max(abs(original['objective']+2*grouped['evaluation',r][condition])))
                        comparison_max_error=max(comparison_max_error,error)
                        if error>config['saved_objective_absolute_tolerance']: raise ValueError('saved likelihood/evaluation objective mismatch')
                    row,raw=ambiguity(original['objective'],candidates,original['indices'],config['machine_epsilon_multiplier'])
                    source_raw[method,r,condition]=dict(indices=original['indices'],rejected=original['rejected'])
                    if int(original['rejected'].sum())!=source_lookup[method,r,condition]['rejections']:
                        raise ValueError('original decision/summary mismatch')
                    if not source_lookup[method,r,condition]['randomized_information_free_baseline']:
                        best=original['objective'].min(axis=1)
                        detection=original['objective'][:,candidates[:,0]==null_value].min(axis=1)-best
                        if not np.array_equal(original['rejected'],detection>calibration_record[f'{method}_R{r}']['detection_cutoff']):
                            raise ValueError('original deployed decision differs from its frozen objective and calibration')
                    ambiguity_rows.append(dict(family=family,source_stage=spec['stage'],method=method,repeats=r,condition=condition,
                        source_file=filename,public_truth=candidates[condition].tolist(),structural_status=structural_status(family,method),
                        original_unidentifiable_coordinates=source_lookup[method,r,condition]['unidentifiable_coordinates'],**row))
                    np.savez_compressed(output/f'ambiguity_{family}_{method}_R{r}_c{condition:02d}.npz',**raw)
        for method in spec['moment_methods']:
            bank_path=stage.folder/f'bank_{method}.npz'
            bank=stage.npz(bank_path.name); row,raw=moment_equivalence(bank['means'],bank['inverse'],config['machine_epsilon_multiplier'])
            equivalences.append(dict(family=family,method=method,source_file=str(bank_path.relative_to(ROOT)),
                structural_status=structural_status(family,method),**row))
            np.savez_compressed(output/f'moment_equivalence_{family}_{method}.npz',**raw)
        oracle_arrays={key:[] for key in ['calibration_llr','evaluation_null_llr','evaluation_alt_llr','null_rejected','alt_rejected','cutoffs','ranks']}
        mle_selected=[]; allowed_masks=[]
        for r in result['repeats']:
            current={key:[] for key in oracle_arrays}
            for pair_id,(null_id,alt_id) in enumerate(pairs):
                row,raw=np_oracle(grouped['calibration',r][null_id],grouped['evaluation',r][null_id],
                    grouped['evaluation',r][alt_id],int(null_id),int(alt_id),stage.config['alpha'])
                oracle_rows.append(dict(family=family,source_stage=spec['stage'],pair_id=pair_id,null_condition=int(null_id),
                    alt_condition=int(alt_id),null_theta=candidates[null_id].tolist(),alt_theta=candidates[alt_id].tolist(),
                    repeats=r,reference_method=spec['reference_method'],**row))
                for key in raw: current[key].append(raw[key])
                current['cutoffs'].append(row['cutoff']); current['ranks'].append(row['rank'])
                for role,condition in [('null',int(null_id)),('alt',int(alt_id))]:
                    for method in result['methods']:
                        paired_rows.append(dict(family=family,pair_id=pair_id,repeats=r,role=role,condition=condition,
                            null_condition=int(null_id),alt_condition=int(alt_id),method=method,
                            **paired_decisions(raw[role+'_rejected'],source_raw[method,r,condition]['rejected'])))
            for key in current: oracle_arrays[key].append(current[key])
            selected_by_condition=[]
            for condition in range(len(candidates)):
                row,selected,squared,allowed=known_eta_mle(grouped['evaluation',r][condition],candidates,condition,spec['interest'])
                selected_by_condition.append(selected)
                if r==result['repeats'][0]: allowed_masks.append(np.isin(np.arange(len(candidates)),allowed))
                mle_rows.append(dict(family=family,source_stage=spec['stage'],condition=condition,repeats=r,
                    public_truth=candidates[condition].tolist(),**row))
                for method in result['methods']:
                    original=source_lookup[method,r,condition]
                    error=None
                    if original['target_identifiable']:
                        values=candidates[source_raw[method,r,condition]['indices'],0]
                        truth=candidates[condition,0]
                        if spec['interest']=='q': values=np.sqrt(values); truth=np.sqrt(truth)
                        error=mean_se(squared-(values-truth)**2)
                    mle_paired_rows.append(dict(family=family,condition=condition,repeats=r,method=method,
                        oracle_delta_rmse=row['delta_rmse'],original_delta_rmse=original['half_gap_rmse'],
                        original_target_identifiable=original['target_identifiable'],oracle_minus_original_squared_error=error,
                        scope='same observed groups; unidentified original target has no meaningful paired target-error claim'))
            mle_selected.append(selected_by_condition)
        np.savez_compressed(output/f'oracle_{family}.npz',candidates=candidates,pair_indices=pairs,repeats=result['repeats'],
                            **{key:np.asarray(value) for key,value in oracle_arrays.items()})
        np.savez_compressed(output/f'known_eta_mle_{family}.npz',candidates=candidates,repeats=result['repeats'],
            selected_indices=np.array(mle_selected),allowed_candidate_mask=np.array(allowed_masks))
        inherited=(result['reference_qualification'] if family=='actual' else
                   dict(independent_reference_max_error=result['independent_reference_max_error']))
        for name,expected_hash in stage.checked.items():
            if sha(resolve(name))!=expected_hash: raise ValueError(f'input changed during saved-data reader: {name}')
        for name in ('registration.json','attempt.json'):
            if sha(stage.folder/name)!=spec['records'][name]: raise ValueError('bound source record changed during reader')
        input_audit.append(dict(family=family,stage=spec['stage'],bound_records=spec['records'],checked_artifacts=stage.checked,
            reference_qualification=inherited,complete_original_rows=len(source_rows),pairs=len(pairs)))
    expected=config['expected_rows']
    actual=dict(oracle_pairs=len(oracle_rows),paired_decisions=len(paired_rows),known_eta_mle=len(mle_rows),
                paired_estimation=len(mle_paired_rows),ambiguity=len(ambiguity_rows),moment_equivalence=len(equivalences))
    if actual!=expected: raise AssertionError(f'complete registered row coverage mismatch: {actual} != {expected}')
    for filename,rows in [('oracle_pairs.json',oracle_rows),('paired_cases.json',paired_rows),('known_eta_mle_cases.json',mle_rows),
        ('mle_paired_cases.json',mle_paired_rows),('ambiguity_cases.json',ambiguity_rows),('moment_equivalence.json',equivalences),('input_audit.json',input_audit)]:
        dump(output/filename,rows)
    return dict(schema='oracle-identifiability/1',new_observations=0,new_scientific_nodes=0,new_scientific_rules=0,
        rows=actual,complete_original_evaluation_rows=len(ambiguity_rows),saved_objective_maximum_error=comparison_max_error,
        original_calibration_maximum_error=calibration_max_error,
        machine_epsilon_multiplier=config['machine_epsilon_multiplier'],failures=0,receiver_calls=0,decoder_calls=0,
        seconds_before_summary=time.perf_counter()-started,
        scope='saved-data finite-calibration oracle and criterion/sample ambiguity; ideal NP theorem is separate from empirical estimates')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--stage',required=True); args=parser.parse_args()
    config=read_json(CONFIG_PATH); base=Path(__file__).parent
    sources=[Path(__file__),base/'test_oracle_identifiability.py',base/'ORACLE_IDENTIFIABILITY.md',CONFIG_PATH]
    for spec in config['inputs'].values():
        folder=ARTIFACT/spec['stage']
        sources.extend([folder/'registration.json',folder/'attempt.json'])
    # Attempts bind the large original NPZs; validate in place, never duplicate them.
    run(args.stage,config,sources,calculate,wall_seconds=config['wall_seconds'])


if __name__=='__main__':
    main()
