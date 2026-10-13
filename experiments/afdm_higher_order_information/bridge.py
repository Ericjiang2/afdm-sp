"""Read-only applicability bridge for six old N1024 observations, three clusters."""
import argparse
import json
from pathlib import Path
import numpy as np

from experiments.afdm_higher_order_information.protocol import ROOT,dump,run,hashes
from experiments.afdm_shared_channel_20261004.production_diagnostic import OLD,source_paths,verify_saved_sources
from experiments.afdm_inference_causal_20261002.oracle_comparison import _load

FOLLOW=ROOT/'.mission/20261004_11-00-00-afdm-shared-channel-followup/execution'
NORMAL=FOLLOW/'normalization_v1'
CONFIG=dict(seed=[20261004,213705,38],old_observations=6,independent_clusters=3,
    observed_lags=[256,512,768],new_observations=0,receiver_calls=0,decoder_calls=0,
    new_channel_draws=0,old_latent_replays=0,
    observation_features='raw inverse-DAFT sample powers and three anchored fourth-order contrasts; no pilot cancellation',
    truth_access='after observed feature files are saved; oracle applicability only',
    old_evidence='original saved G1 observations; existing normalization and state receipts',
    no_estimator_claim=True,no_new_fer_inference=True)


def observed_features(observation,c1,c2,physical):
    y=np.asarray(observation['y']); pilot=np.asarray(observation['pilot'])
    if y.shape!=(1024,) or pilot.shape!=y.shape or not np.isfinite(y).all():
        raise ValueError('six-observation bridge requires finite original N1024 payloads')
    t=physical.daft(y,c1,c2,True); power=abs(t)**2
    lags=CONFIG['observed_lags']
    contrasts=np.array([power[0]*(power[a]-power[b]) for a,b in [(lags[0],lags[1]),(lags[0],lags[2]),(lags[1],lags[2])]])
    return dict(time_received=t,power=power,contrasts=contrasts,
                sigma2=float(observation['sigma2']),pilot_energy=float(np.vdot(pilot,pilot).real),
                pilot_nonzero=int(np.count_nonzero(pilot)))


def calculate(output):
    verify_saved_sources()
    evidence=_load('higher_bridge_evidence',ROOT/'experiments/sp_afdm_frozen_20260920/src/evidence.py')
    physical=_load('higher_bridge_physical',ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py')
    registration=json.loads((OLD/'runtime_registration.json').read_text())
    system=registration['runtime_binding']['system']
    inputs=[OLD/'population'/domain/'data'/f'development_f{i:06d}.npz'
            for domain in ['observed','truth'] for i in range(6)]
    inputs += [FOLLOW/'production_v2_state_receipt.json',FOLLOW/'production_v2/results.json',
               *NORMAL.glob('geometry_*.npz')]
    before=hashes(inputs)
    dump(output/'input_sha256_before.json',before)
    observed=[]; features=[]
    for i in range(6):
        stem=f'development_f{i:06d}'; path=OLD/'population/observed/data'/(stem+'.npz')
        payload,_=evidence.load_artifact(path)
        feature=observed_features(payload['observation'],system['c1'],system['c2'],physical)
        # Write observation-only data before reading any truth in this stage.
        np.savez_compressed(output/(stem+'_observed_features.npz'),**feature)
        observed.append(payload); features.append(feature); inputs.append(path)
    states=json.loads((FOLLOW/'production_v2_state_receipt.json').read_text())
    old_results=json.loads((FOLLOW/'production_v2/results.json').read_text())
    inputs.extend([FOLLOW/'production_v2_state_receipt.json',FOLLOW/'production_v2/results.json'])
    rows=[]; cluster_rows=[]
    for cluster in range(3):
        path=NORMAL/f'geometry_{cluster}.npz'; inputs.append(path)
        with np.load(path,allow_pickle=False) as archive:
            saved={k:archive[k] for k in archive.files}
        eigenvalues=np.linalg.eigvalsh(saved['gram'])
        pair=observed[2*cluster:2*cluster+2]
        shared={key:pair[0]['stream_ids'][key]==pair[1]['stream_ids'][key] for key in ['channel','message','noise']}
        if not shared['channel']:
            raise ValueError('old declared exogenous channel cluster mismatch')
        cluster_rows.append(dict(cluster=cluster,observations=[p['observation_id'] for p in pair],
            shared_streams=shared,gram_eigenvalues=eigenvalues.tolist(),pdp=saved['pdp'].tolist(),
            latent_pdp_source='existing normalization_v1; no new replay',
            conditional_gain_all_moments_bounded=bool(eigenvalues.min()>0)))
        for i in range(2*cluster,2*cluster+2):
            stem=f'development_f{i:06d}'; path=OLD/'population/truth/data'/(stem+'.npz'); inputs.append(path)
            truth,_=evidence.load_artifact(path)
            if truth['observation_hash']!=observed[i]['observation_hash']:
                raise ValueError('truth/observed hash differs')
            if not (np.array_equal(truth['l_i'],saved['delays']) and np.array_equal(truth['k_real'],saved['dopplers'])):
                raise ValueError('saved conditional-prior geometry differs from old truth')
            state=next(row for row in states['rows'] if row['observation_id']==stem)
            npaths=len(truth['g_i']); unique_delays=len(np.unique(truth['l_i']))
            has_pilot=features[i]['pilot_energy']>0
            coded=len(truth['coded'])!=len(truth['info'])
            same_delay_two=npaths==2 and unique_delays==1
            assumptions=dict(two_paths=npaths==2,common_delay=unique_delays==1,
                no_pilot=not has_pilot,iid_uncoded_qpsk=not coded,
                iid_equal_gaussian_gains=False,independent_repeated_observation=False)
            rows.append(dict(observation_id=stem,cluster=cluster,
                observation_hash=observed[i]['observation_hash'],physical_paths=npaths,
                unique_delays=unique_delays,delays=truth['l_i'].tolist(),
                dopplers=truth['k_real'].tolist(),gain_rule=truth['diagnostics']['gain_normalization'],
                generator=truth['diagnostics']['generator'],pdp_is_oracle=True,
                pilot_energy=features[i]['pilot_energy'],pilot_nonzero=features[i]['pilot_nonzero'],
                coded_length=len(truth['coded']),information_length=len(truth['info']),
                code_constraint_present=coded,assumptions=assumptions,
                control_model_applicable=bool(all(assumptions.values())),
                same_delay_collision_slice_present=same_delay_two,
                observed_contrasts=features[i]['contrasts'].tolist(),
                native_state_counts=state['actual_state_counts'],
                fixed_gain_unchanged=state['fixed_gain_all_states_equal_front'],
                joint20_gain_change=state['joint20_gain_l2_change'],
                decision='raw contrast computable; control coefficient and moment estimator calibration do not transfer'))
    dump(output/'observed_feature_contract.json',dict(inputs='only y,pilot,sigma2 and public c1/c2',
        no_truth=True,no_pilot_subtraction=True,why='unknown H prevents subtracting the pilot contribution without a new estimator'))
    dump(output/'applicability.json',rows); dump(output/'clusters.json',cluster_rows)
    after=hashes(inputs)
    if after != before:
        raise RuntimeError('saved bridge inputs changed during read-only analysis')
    dump(output/'input_sha256.json',after)
    verify_saved_sources()
    return dict(observations=6,independent_clusters=3,control_applicable=sum(r['control_model_applicable'] for r in rows),
        observed_feature_cases=6,finite_observed_features=all(np.isfinite(f['contrasts']).all() for f in features),
        same_delay_two_path_cases=sum(r['same_delay_collision_slice_present'] for r in rows),
        original_results=old_results['actual'],confounds=old_results['confounds'],
        transferable=['observable powers and contrasts','fixed-base prior accounting','legal extrinsic cavity and normalized integration'],
        not_transferable=['two-path common-delay coefficient','iid-QPSK fourth-moment formula without code/pilot correction',
                          'Gaussian collision effective information','independent-R detection scale from six cross-SNR records'],
        new_observations=0,receiver_calls=0,decoder_calls=0,new_channel_draws=0,old_latent_replays=0,
        conclusion='no saved observation meets the blind Gaussian same-delay two-path model; no FER causal attribution')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);args=parser.parse_args()
    sources=[*source_paths(),__file__,FOLLOW/'production_v2/results.json',FOLLOW/'production_v2_state_receipt.json',
             *NORMAL.glob('geometry_*.npz')]
    run(args.stage,CONFIG,sources,calculate,wall_seconds=600)

if __name__=='__main__':main()
