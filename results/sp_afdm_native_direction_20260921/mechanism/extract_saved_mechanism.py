"""Reconstruct frozen TF/POINT mechanism metrics from saved D252 checkpoints only.

No receiver, scalar_joint, decoder, or Monte Carlo generator is invoked.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
a = parser.parse_args()
if a.out.exists() and any(a.out.iterdir()):
    raise ValueError('mechanism output must be a new empty directory')
a.out.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(a.source / 'src'), str(a.baseline / 'src')]
import evidence
from physical import Channel
from twofft import TimePathOps, daft
from messages import moments


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_ratio(numerator, denominator, name):
    if not np.isfinite([numerator, denominator]).all() or denominator <= 0:
        raise ValueError(f'undefined {name} ratio')
    return float(numerator / denominator)


def load_checkpoint(run_hash, snr, frame, arm, row, cp):
    path = a.run / cp['path']
    if sha(path) != cp['artifact_sha256']:
        raise ValueError('saved checkpoint hash differs')
    ident = {'schema':'spafdm-native-direction-compact/1','run_identity_sha256':run_hash,
             'kind':'checkpoint','snr_centi_db':snr,'frame':frame,'arm':arm,'round':cp['round']}
    payload, _ = evidence.load_artifact(path, ident)
    return payload, path


manifest = json.loads((a.run / 'manifest.json').read_text())
run_hash = evidence.canonical_hash(manifest)
if manifest['stage'] != 'D' or manifest['source_commit'] != '2d130b4d':
    raise ValueError('frozen D252 run identity differs')
if manifest['source_hashes'] != evidence.source_hashes(a.source):
    raise ValueError('frozen numerical source changed')
if manifest['baseline_source_hashes'] != evidence.source_hashes(a.baseline):
    raise ValueError('frozen baseline changed')
header = json.loads((a.run / 'context_header.json').read_text())
if int(header['system']['n_total']) != 1024:
    raise ValueError('unexpected N')
c1, c2 = float(header['system']['c1']), float(header['system']['c2'])
rows = [json.loads(line) for line in (a.run / 'ledger.jsonl').read_text().splitlines()]
index = {(r['snr_centi_db'],r['frame'],r['arm']):r for r in rows}
if len(index) != 252:
    raise ValueError('D252 ledger incomplete or duplicated')

full_rows = []
scalar_rows = []
audited_sources = []
scalar_sources = []
parity = defaultdict(float)
for snr in (600,650,700):
    input_path = a.run / 'frames' / f's{snr}_f000_input.npz'
    input_id = {'schema':'spafdm-native-direction-compact/1','run_identity_sha256':run_hash,
                'kind':'frame_input','snr_centi_db':snr,'frame':0}
    observed,_ = evidence.load_artifact(input_path,input_id)
    pilot = np.asarray(observed['pilot'],complex)
    noise = float(observed['sigma2'])
    n = len(pilot)
    if n != 1024 or noise <= 0:
        raise ValueError('saved input dimensions/noise differ')
    for arm in ('TF_J20_R2','TF_POINT20_R2'):
        gain_mode = 'joint' if arm == 'TF_J20_R2' else 'point'
        for frame in range(8):
            row = index[(snr,frame,arm)]
            if row['status'] != 'ok' or len(row['checkpoints']) != 2:
                raise ValueError('selected scalar-trace batch lacks both decisions')
            previous_check = None
            for cp in row['checkpoints']:
                payload,path = load_checkpoint(run_hash,snr,frame,arm,row,cp)
                snapshot = payload['snapshot']
                trace = snapshot['inference_trace']
                if len(trace) != 20:
                    raise ValueError('missing scalar trace')
                p_count = len(snapshot['ce_gains'])
                if p_count <= 0 or p_count != len(snapshot['delays']):
                    raise ValueError('invalid inferred path count')
                scalar_sources.append({'snr_centi_db':snr,'frame':frame,'arm':arm,
                    'round':cp['round'],'path':str(path),'sha256':cp['artifact_sha256']})
                for it, t in enumerate(trace):
                    if t['iteration'] != it:
                        raise ValueError('scalar trace order differs')
                    scalar_rows.append({
                        'snr_centi_db':snr,'frame':frame,'arm':arm,'round':cp['round'],
                        'iteration':it,'n':n,'p_count':p_count,
                        'trace_post_vx':float(t['data_variance']),
                        'trace_post_vh':float(t['gain_variance']),
                        'trace_channelpower_pre':float(t['channel_norm_factor']),
                        'trace_bar':float(t['pseudo_variance_bar']),
                        'trace_vp':float(t['pseudo_variance_total']),
                        'trace_vr':float(t['data_pseudo_variance']),
                        'trace_vq':float(t['gain_pseudo_variance']),
                        'trace_sv':float(t['output_precision']),
                        'trace_data_precision_floor':int(t['data_precision_floor']),
                        'trace_gain_precision_floor':int(t['gain_precision_floor']),
                        'trace_fft_count':int(t['fft_count']),
                        'n_trace_post_vh':n*float(t['gain_variance']),
                        'n_trace_vq':n*float(t['gain_pseudo_variance'])})
                if frame != 0:
                    continue
                states = payload.get('inference_states')
                if len(states or []) != 20:
                    raise ValueError('audited frame lacks full iteration states')
                if cp['round'] == 0:
                    prior = np.zeros(2*n)
                else:
                    if previous_check is None:
                        raise ValueError('round-one prior lacks previous saved check message')
                    prior = np.clip(previous_check,-20,20)
                mu_pre,v_pre,_ = moments(prior,.5)
                h_pre = np.asarray(snapshot['ce_gains'],complex).copy()
                vh_pre = 1/p_count if gain_mode == 'joint' else 0.
                x_initial = pilot + mu_pre
                xb_prev = x_initial.copy()
                hb_prev = h_pre.copy()
                sv_prev = 0.
                operator = TimePathOps(Channel(n,c1,c2,snapshot['delays'],snapshot['dopplers'],snapshot['ce_gains']))
                for it,(state,t) in enumerate(zip(states,trace)):
                    if t['iteration'] != it:
                        raise ValueError('audited trace/state iteration differs')
                    x_pre = pilot + mu_pre
                    vx_pre = float(np.mean(v_pre))
                    xpower = float(np.vdot(x_pre,x_pre).real/n)
                    channelpower = operator.power(h_pre)
                    xb = .3*x_pre+.7*xb_prev
                    hb = .3*h_pre+.7*hb_prev
                    xb_power = float(np.vdot(xb,xb).real/n)
                    s = np.asarray(state['s'],complex)
                    sv = float(state['sv'])
                    vq = float(state['vq'])
                    adj = daft(operator.adjoint_time(hb,s),c1,c2)
                    adj_norm = float(np.linalg.norm(adj))
                    if sv <= 0:
                        raise ValueError('nonpositive saved output precision')
                    reaction = checked_ratio(float(np.linalg.norm(xb*(sv*p_count*vh_pre))),adj_norm,'actual reaction')
                    user_literal = checked_ratio(float(np.linalg.norm((p_count*vh_pre)*x_pre))*sv,
                                                 adj_norm,'user literal reaction')
                    movement = checked_ratio(float(np.linalg.norm(np.asarray(state['h'])-h_pre)),
                                             float(np.linalg.norm(h_pre)),'gain movement')
                    correction = float(p_count*vh_pre*(xpower+vx_pre)/(noise+vx_pre*channelpower))
                    tau = 1/p_count
                    latent_vh = float(tau*vq/(tau+vq))
                    predicted_nvh = float(1/(sv*xb_power+p_count/n))
                    post_vh = float(state['vh'])
                    post_vx = float(np.mean(state['v']))
                    sv_pred = float(.3/(noise+float(state['vp']))+.7*sv_prev)
                    vq_pred = float(1/max(sv*np.vdot(xb,xb).real,1e-12))
                    errors = {
                        'post_vh':abs(post_vh-(latent_vh if gain_mode=='joint' else 0.)),
                        'n_vh_prediction':abs(n*latent_vh-predicted_nvh),
                        'sv':abs(sv-sv_pred),
                        'vq':abs(vq-vq_pred),
                        'trace_channelpower':abs(channelpower-float(t['channel_norm_factor'])),
                        'trace_post_vx':abs(post_vx-float(t['data_variance'])),
                        'trace_post_vh':abs(post_vh-float(t['gain_variance'])),
                        'trace_vq':abs(vq-float(t['gain_pseudo_variance'])),
                        'trace_sv':abs(sv-float(t['output_precision'])),
                        'trace_bar':abs(float(state['bar'])-float(t['pseudo_variance_bar'])),
                        'trace_vp':abs(float(state['vp'])-float(t['pseudo_variance_total']))}
                    if t['gain_precision_floor']:
                        # The algebraic N-scaled identity omits the documented 1e-12 floor.
                        errors['n_vh_prediction'] = None
                    for key,value in errors.items():
                        if value is not None:
                            parity[key] = max(parity[key],value)
                    scale = p_count/n
                    full_rows.append({
                        'snr_centi_db':snr,'frame':frame,'arm':arm,'gain_mode':gain_mode,
                        'round':cp['round'],'iteration':it,'n':n,'p_count':p_count,
                        'sigma2':noise,'pre_vh':float(vh_pre),'post_vh':post_vh,
                        'latent_posterior_vh':latent_vh,'pre_vx':vx_pre,'post_vx':post_vx,
                        'xpower':xpower,'xb_power':xb_power,'channelpower':channelpower,
                        'vq':vq,'sv':sv,'correction':correction,
                        'actual_reaction_ratio':reaction,
                        'user_literal_reaction_ratio':user_literal,
                        'gain_movement_ratio':movement,
                        'n_pre_vh':n*vh_pre,'n_post_vh':n*post_vh,
                        'n_latent_posterior_vh':n*latent_vh,'n_vq':n*vq,
                        'n_vh_prediction':predicted_nvh,
                        'correction_over_p_over_n':correction/scale,
                        'reaction_over_p_over_n':reaction/scale,
                        'gain_movement_over_p_over_n':movement/scale,
                        'trace_gain_precision_floor':int(t['gain_precision_floor']),
                        'trace_data_precision_floor':int(t['data_precision_floor']),
                        **{'parity_abs_'+key:value for key,value in errors.items()}})
                    xb_prev,hb_prev = xb,hb
                    mu_pre = np.asarray(state['mu'])
                    v_pre = np.asarray(state['v'])
                    h_pre = np.asarray(state['h'])
                    vh_pre = post_vh
                    sv_prev = sv
                audited_sources.append({'snr_centi_db':snr,'arm':arm,'round':cp['round'],
                    'path':str(path),'sha256':cp['artifact_sha256'],'input_path':str(input_path),
                    'input_sha256':row['input_sha256'],'p_count':p_count})
                previous_check = np.asarray(snapshot['check'])

if len(full_rows)!=240 or len(scalar_rows)!=1920:
    raise ValueError(f'row count differs full={len(full_rows)} scalar={len(scalar_rows)}')
for name,value in parity.items():
    if value > 1e-8:
        raise ValueError(f'saved-state parity failed: {name}={value}')


def write_csv(path, items):
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows(items)


full_path = a.out/'audit_iteration_metrics.csv'
scalar_path = a.out/'paired_saved_scalar_traces.csv'
write_csv(full_path,full_rows)
write_csv(scalar_path,scalar_rows)
grouped = []
periods = (('init_it0',lambda i:i==0),('it1_4',lambda i:1<=i<=4),
           ('it5_19',lambda i:5<=i<=19))
for snr in (600,650,700):
    for arm in ('TF_J20_R2','TF_POINT20_R2'):
        for round_index in (0,1):
            for period,predicate in periods:
                selection=[r for r in full_rows if r['snr_centi_db']==snr and r['arm']==arm
                           and r['round']==round_index and predicate(r['iteration'])]
                aggregates={}
                for key in ('n_post_vh','n_latent_posterior_vh','n_vq','n_vh_prediction',
                            'correction_over_p_over_n','actual_reaction_ratio',
                            'gain_movement_ratio','reaction_over_p_over_n',
                            'gain_movement_over_p_over_n'):
                    values=np.asarray([r[key] for r in selection],float)
                    aggregates[key]={'median':float(np.median(values)),
                                     'min':float(values.min()),'max':float(values.max())}
                grouped.append({'snr_centi_db':snr,'arm':arm,'round':round_index,
                                'period':period,'iterations':len(selection),'metrics':aggregates})
summary = {
    'schema':'spafdm-native-direction-saved-mechanism/1',
    'scope':'offline saved-state mechanism analysis; no receiver, scalar_joint, decoder or radio regeneration',
    'source_commit':'2d130b4d','run_identity_sha256':run_hash,
    'n':1024,'audit_frame':0,'audited_batches':12,'audited_iteration_rows':len(full_rows),
    'paired_first8_scalar_rows':len(scalar_rows),'group_summaries':grouped,
    'parity_max_abs':dict(parity),
    'definitions':{
       'pre_post':'trace data_variance/gain_variance are POST update; pre values reconstructed from prior checkpoint/previous saved state',
       'round_prior':'r0 zero; r1 clip(previous round saved raw_check_extrinsic,-20,20)',
       'actual_reaction_ratio':'norm(xb_damped*(sv_current*P*vh_pre))/norm(adj), where adj=daft(adjoint_time(hb_damped,s_saved))',
       'user_literal_reaction_ratio':'norm(P*vh_pre*x_pre)/norm(adj/sv_current); uses x_pre, not xb_damped',
       'n_vh_prediction':'1/(sv_current*xb_power+P/N) with gain-precision floor omitted; POINT reports latent posterior while propagated vh=0',
       'scaling_limit':'Only N=1024 observed; N-asymptotic scaling is not identifiable. Initial joint vh=1/P is a transient and not O(1/N) evidence.',
       'scalar_subset':'first eight frames per SNR for both arms and rounds, raw saved scalars only; vector-derived fields exist only for audit frame0'},
    'source_paths':{'run_manifest':str(a.run/'manifest.json'),
                    'run_ledger':str(a.run/'ledger.jsonl'),
                    'audited_checkpoints':audited_sources,
                    'paired_scalar_checkpoints':scalar_sources},
    'sha256':{'manifest':sha(a.run/'manifest.json'),'ledger':sha(a.run/'ledger.jsonl'),
              'extractor':sha(__file__),'audit_csv':sha(full_path),'scalar_csv':sha(scalar_path)}}
summary_path=a.out/'summary.json'
summary_path.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
receipt={'status':'pass','run_identity_sha256':run_hash,'audited_rows':len(full_rows),
         'paired_scalar_rows':len(scalar_rows),'parity_max_abs':dict(parity),
         'audit_csv_sha256':sha(full_path),'scalar_csv_sha256':sha(scalar_path),
         'summary_sha256':sha(summary_path),'source_manifest_sha256':sha(a.run/'manifest.json'),
         'source_ledger_sha256':sha(a.run/'ledger.jsonl'),'extractor_sha256':sha(__file__)}
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
print(json.dumps({'status':'pass','audited_rows':len(full_rows),
                  'paired_scalar_rows':len(scalar_rows),'parity_max_abs':dict(parity)}))
