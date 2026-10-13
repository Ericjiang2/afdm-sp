"""Offline truth-assisted diagnosis of saved A256 failures; never runs receiver."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from candidates import reliable_basis, symbols, PhysicalScore, ROOT
sys.path.insert(0,str(ROOT/'experiments/sp_afdm_frozen_20260920/src'))
import evidence
from physical import Channel
from profile_geometry import channel_jacobian, ProfileGeometry, realify

HERE=Path(__file__).resolve().parent
EXP=HERE.parent/'experiments'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,digest):
    if sha(p)!=digest:raise ValueError('artifact binding mismatch')
    return evidence.load_artifact(p)[0]

def stats(llr,coded):
    l=np.asarray(llr)
    return dict(zero_llr=int(np.count_nonzero(l==0)),nonfinite=int(np.count_nonzero(~np.isfinite(l))),hard_bit_errors=int(np.count_nonzero((l<0)!=coded)),median_abs=float(np.median(abs(l))),max_abs=float(np.max(abs(l))),saturated_abs20=int(np.count_nonzero(abs(l)>=20)))

def main():
    scored=EXP/'development-scored.json';report=json.loads(scored.read_text())
    run=EXP/'development-run';pop=EXP/'development-population'
    manifest=json.loads((run/'manifest.json').read_text())
    ledger={(r['observation_id'],r['policy']):r for r in map(json.loads,(run/'ledger.jsonl').read_text().splitlines())}
    truthrows={r['observation_id']:r for r in map(json.loads,(pop/'truth/ledger.jsonl').read_text().splitlines())}
    observed={r['observation_id']:r for r in map(json.loads,(pop/'observed/ledger.jsonl').read_text().splitlines())}
    cache=ROOT/'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    h=np.load(cache)['H'];records=[]
    failures=[r['observation_id'] for r in report['records'] if r['policy']=='cascade' and r['error']]
    for stem in failures:
        row=ledger[(stem,'cascade_geometry')];r=load(run/row['raw_path'],row['raw_sha256'])
        tr=truthrows[stem];t=load(pop/'truth'/tr['truth_path'],tr['truth_sha256']);coded=np.asarray(t['coded'],np.uint8)
        ob=observed[stem];obs=load(pop/'observed'/ob['observation_path'],ob['observation_sha256'])['observation']
        app=r['pre_acquisition_decoder']['raw_app'];a=r['acquisition'];basis=reliable_basis(h,app)
        for k in ('anchor','free'):np.testing.assert_array_equal(basis[k],a[k])
        free=a['free'];wrong=np.flatnonzero(a['anchor'][free]!=coded[free]);moves=set(map(int,a['moves']))
        order=np.lexsort((free,abs(app[free])));rank=np.empty(len(free),int);rank[order]=np.arange(1,len(free)+1)
        delta=np.zeros(len(free),np.uint8);delta[wrong]=1
        np.testing.assert_array_equal(a['anchor']^(basis['generator']@delta%2),coded)
        stage_llr={'prefix':r['prefix']['decoder']['raw_app'],'scalar_cstate':r['scalar_branch']['decoder']['raw_app'],'coherent':r['coherent']['decoder']['raw_app'],'f1_round1':r['restart']['arrays']['r1_app'],'final_f1_cstate':app}
        geom=r['acquisition_geometry'];n=len(obs['y']);system=manifest['registration']['runtime_binding']['system']
        channel=Channel(n,system['c1'],system['c2'],geom['delays'],geom['dopplers'],geom['gains'])
        x=obs['pilot']+symbols(a['anchor'],np.sqrt(1-system['rho']))
        gain_s=np.linalg.svd(channel.regressors(x),compute_uv=False);jac=channel_jacobian(channel,x);j_s=np.linalg.svd(jac,compute_uv=False)
        working=ProfileGeometry(jac,float(obs['sigma2'])/2,.1*np.eye(jac.shape[1]))
        weighted=working.apply(realify(channel.apply(x)-obs['y']))
        adjoint=channel.adjoint(weighted[:n]+1j*weighted[n:])
        signs=1-2*a['anchor'].astype(float);scale=np.sqrt(1-system['rho'])
        bit_linear=-np.sqrt(2)*scale*np.r_[signs[:n]*adjoint.real,signs[n:]*adjoint.imag]
        free_linear=basis['generator'].T@bit_linear
        raw_adjoint=channel.adjoint(2*(channel.apply(x)-obs['y'])/float(obs['sigma2']))
        raw_bit=-np.sqrt(2)*scale*np.r_[signs[:n]*raw_adjoint.real,signs[n:]*raw_adjoint.imag]
        raw_order=np.lexsort((free,basis['generator'].T@raw_bit));raw_rank=np.empty(len(free),int);raw_rank[raw_order]=np.arange(1,len(free)+1)
        geo_order=np.lexsort((free,free_linear));geo_rank=np.empty(len(free),int);geo_rank[geo_order]=np.arange(1,len(free)+1)
        top_direction=int(geo_order[0]);proposed=a['anchor']^basis['generator'][:,top_direction]
        scorer=PhysicalScore(channel,obs['y'],obs['pilot'],float(obs['sigma2']),scale,gain_precision=0.)
        proposed_score,_=scorer(proposed);truth_score,_=scorer(coded)
        candidates=np.asarray(a['candidates']);distinct=[int(np.count_nonzero(w!=coded)) for w in candidates]
        support=[dict(free_basis_index=int(i),code_bit_index=int(free[i]),absolute_llr=float(abs(app[free[i]])),reliability_rank_ascending=int(rank[i]),in_branch12=int(i) in moves) for i in wrong]
        rec=dict(observation_id=stem,snr_centi_db=tr['snr_centi_db'],free_errors=len(wrong),free_error_ranks=[int(rank[i]) for i in wrong],free_error_support=support,diagnostic_top1_global_move=dict(free_basis_index=top_direction,equals_truth=bool(np.array_equal(proposed,coded)),bit_errors=int(np.count_nonzero(proposed!=coded)),physical_gain_profile_score=proposed_score,better_than_all_saved_candidates=bool(proposed_score<float(np.min(a['scores'])))),diagnostic_truth_profile_score=truth_score,diagnostic_saved_best_profile_score=float(np.min(a['scores'])),diagnostic_unprojected_linear_ranks=[int(raw_rank[i]) for i in wrong],diagnostic_global_linear_geometry_ranks=[int(geo_rank[i]) for i in wrong],diagnostic_global_linear_geometry_top12_true_free_errors=sum(int(geo_rank[i])<=12 for i in wrong),outside_branch12=sum(int(i) not in moves for i in wrong),inside_branch12=sum(int(i) in moves for i in wrong),oracle_reachable_entire_12dim_subspace=all(int(i) in moves for i in wrong),oracle_reachable_depth3=all(int(i) in moves for i in wrong) and len(wrong)<=3,anchor_bit_errors=int(np.count_nonzero(a['anchor']!=coded)),best_saved_candidate_bit_errors=min(distinct),selected_candidate_bit_errors=distinct[a['selected']],stage_llr={k:stats(v,coded) for k,v in stage_llr.items()},geometry=dict(delays=np.asarray(geom['delays']).tolist(),dopplers=np.asarray(geom['dopplers']).tolist(),gain_magnitudes=abs(geom['gains']).tolist(),unique_delays=len(set(geom['delays'])),gain_design_singular_values=gain_s.tolist(),jacobian_singular_values=j_s.tolist(),gain_design_condition=float(gain_s[0]/gain_s[-1]),jacobian_condition=float(j_s[0]/j_s[-1])),raw_sha256=row['raw_sha256'])
        records.append(rec)
    out=dict(scope='post-outcome truth-assisted offline diagnosis on six development failures; no receiver reruns, no deployable oracle',source_scored_sha256=sha(scored),parity_sha256=sha(cache),failures=len(records),reachable_full12=sum(r['oracle_reachable_entire_12dim_subspace'] for r in records),reachable_depth3=sum(r['oracle_reachable_depth3'] for r in records),records=records,script_sha256=sha(Path(__file__)))
    (HERE/'diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='records'},indent=2))
    for r in records:print(r['observation_id'],r['free_errors'],r['outside_branch12'],r['free_error_ranks'],r['stage_llr']['final_f1_cstate'],r['geometry']['gain_design_condition'],r['geometry']['jacobian_condition'])

if __name__=='__main__':main()
