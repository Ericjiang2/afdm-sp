"""Offline full-raw audit of the four fixed independent frontier blocks."""
from pathlib import Path
import json
import sys
import numpy as np
from scipy.stats import binomtest, beta
from score_development import bound,same,sha,lines,evidence,ROOT,BASE,TASK
from score_new_runs import need
from decoder_equivalence import same_decoder

ARMS=['scalar3','guard_coherent','guard_f1','f1_alone']


def main():
    exp=TASK/'experiments';regpath=exp/'frontier_registration.json';reg=json.loads(regpath.read_text());regsha=sha(regpath)
    pop=exp/'frontier_population_observed';trroot=exp/'frontier_population_truth'
    for folder,kind in [(pop,'observed'),(trroot,'truth')]:
        seal=json.loads((folder/f'{kind}_seal.json').read_text())
        need(seal['status']=='pass' and seal['registration_sha256']==regsha and seal['observations']==2048,'population seal')
        for path,digest in seal['files'].items():need(sha(folder/path)==digest,'population file hash')
    inputs=lines(pop/'ledger.jsonl');truths=lines(trroot/'ledger.jsonl')
    need(len(inputs)==len(truths)==2048,'population size')
    expected=[f'j{s}_f{f:04d}' for s in (600,650) for f in range(1024)]
    need([r['observation_id'] for r in inputs]==[r['observation_id'] for r in truths]==expected,'population order')
    for path,digest in reg['task_sources'].items():need(sha(TASK/path)==digest,'task source')
    for path,digest in reg['f1_hashes'].items():need(sha(ROOT/path)==digest,'F1 source')
    cache=BASE/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    with np.load(cache) as z:H,free=z['H'],z['free_cols']
    syn=lambda d:int(np.count_nonzero((H@d['decoded'])%2))
    frames=[];bindings=[];guard_checks=0;call_total=0
    for block in range(4):
        run=exp/f'frontier_block{block}_v1';result=json.loads((run/'result.json').read_text());manifest=json.loads((run/'manifest.json').read_text())
        need(result['status']=='pass' and result['completed_calls']==2048,'block incomplete')
        need(result['registration_sha256']==manifest['registration_sha256']==regsha,'registration hash')
        need(sha(cache)==manifest['locked_hashes']['ldpc_cache_sha256'],'LDPC hash')
        for name,key in [('manifest.json','manifest_sha256'),('ledger.jsonl','ledger_sha256'),('attempts.jsonl','attempts_sha256')]:need(sha(run/name)==result[key],'block file hash')
        rows=lines(run/'ledger.jsonl');events=lines(run/'attempts.jsonl')
        ids=expected[block*512:(block+1)*512]
        schedule=[(stem,arm) for i,stem in enumerate(ids) for arm in ARMS[i%4:]+ARMS[:i%4]]
        need(len(rows)==2048 and len(events)==4096,'accounting')
        need([(r['observation_id'],r['policy']) for r in rows]==schedule,'registered schedule')
        need(manifest['observation_ids']==ids,'manifest cohort')
        for i,r in enumerate(rows):
            need(r['call_index']==i and r['status']=='ok','index/status')
            a,b=events[2*i:2*i+2];need(a['event']=='started' and b['event']=='finished','event order')
            for key in ('call_index','observation_id','policy','input_sha256'):need(a[key]==b[key]==r[key],'event identity')
            need({k:v for k,v in b.items() if k!='event'}==r,'finished event')
        byid={s:{} for s in ids}
        for r in rows:byid[r['observation_id']][r['policy']]=r
        for offset,stem in enumerate(ids):
            idx=block*512+offset;inp=inputs[idx];tr=truths[idx]
            need(inp['observation_hash']==tr['observation_hash'] and inp['stream_ids']==tr['stream_ids'],'paired truth')
            observation=bound(pop/inp['observation_path'],inp['observation_sha256'])
            need(observation['observation_id']==stem and observation['observation_hash']==inp['observation_hash'],'observation identity')
            truth=bound(trroot/tr['truth_path'],tr['truth_sha256'],dict(observation_id=stem,registration_sha256=regsha,kind='truth'))
            coded=np.asarray(truth['coded']);info=np.asarray(truth['info'])
            need(np.array_equal(coded[free],info) and np.count_nonzero((H@coded)%2)==0,'truth valid codeword')
            payloads={};frame=dict(observation_id=stem,snr=inp['snr_centi_db'],input_sha256=inp['observation_sha256'],truth_sha256=tr['truth_sha256'],arms={})
            for arm in ARMS:
                current=None
                row=byid[stem][arm];need(row['input_sha256']==inp['observation_sha256'],'receiver pairing')
                identity=dict(observation_id=stem,policy=arm,input_sha256=inp['observation_sha256'])
                raw=bound(run/row['raw_path'],row['raw_sha256'],identity);payloads[arm]=raw
                need((raw['coherent'] is not None)==row['coherent_executed'],'coherent record')
                need((raw['restart'] is not None)==row['restart_executed'],'restart record')
                if arm=='f1_alone':need(raw['prefix'] is None and raw['scalar_branch'] is None and raw['coherent'] is None and raw['restart'] is not None,'F1 standalone route')
                else:
                    prefix=raw['prefix']['decoder'];need((raw['scalar_branch'] is not None)==bool(syn(prefix)),'scalar gate')
                    base=raw['scalar_branch']['decoder'] if syn(prefix) else prefix
                    need((raw['coherent'] is not None)==bool(syn(base) and arm in ('guard_coherent','guard_f1')),'coherent gate')
                    current=raw['coherent']['decoder'] if raw['coherent'] is not None else base
                    need((raw['restart'] is not None)==bool(syn(current) and arm=='guard_f1'),'F1 gate')
                    if raw['coherent'] is not None:
                        need(raw['coherent']['geometry_reused'] and np.array_equal(raw['coherent']['check_prior'],raw['scalar_branch']['check_prior']),'same prior reuse')
                if raw['restart'] is not None:
                    restart=raw['restart'];need((restart['branch'] is not None)==bool(syn(restart['decoder'])),'F1 CSTATE gate')
                    current=restart['branch']['decoder'] if syn(restart['decoder']) else restart['decoder']
                    need(same(current,restart['final_decoder']),'F1 selected decoder')
                need(same(current,raw['final_decoder']),'policy selected decoder')
                final=np.asarray(current['decoded']);need(final.shape==(2048,) and np.isin(final,(0,1)).all(),'decoded domain')
                syndrome=syn(current);need(syndrome==row['final_syndrome'],'syndrome recount')
                ready=row['receiver_ready_seconds'];complete=row['complete_seconds'];need(np.isfinite(ready) and 0<ready<=complete,'time boundary')
                frame['arms'][arm]=dict(coded_errors=int(np.count_nonzero(final!=coded)),info_errors=int(np.count_nonzero(final[free]!=info)),syndrome=syndrome,ready_seconds=ready,complete_seconds=complete,raw_sha256=row['raw_sha256'],coherent_executed=row['coherent_executed'],restart_executed=row['restart_executed'])
            for arm in ('guard_coherent','guard_f1'):
                need(same(payloads['scalar3']['prefix']['arrays'],payloads[arm]['prefix']['arrays']),'common prefix')
                need(same_decoder(payloads['scalar3']['prefix']['decoder'],payloads[arm]['prefix']['decoder']),'common prefix decoder')
                b=payloads['scalar3']['scalar_branch'];c=payloads[arm]['scalar_branch']
                if b is not None:
                    need(same_decoder(b['decoder'],c['decoder']),'common scalar decoder')
                    for key in ('paths','gains'):need(same(b['geometry_result'][key],c['geometry_result'][key]),'common geometry')
                if syn(payloads['scalar3']['final_decoder'])==0:need(same_decoder(payloads['scalar3']['final_decoder'],payloads[arm]['final_decoder']),'zero syndrome protection')
                need(not(frame['arms']['scalar3']['coded_errors']==0 and frame['arms'][arm]['coded_errors']>0),'whole codeword harmed')
                guard_checks+=1
            gc=payloads['guard_coherent'];gf=payloads['guard_f1']
            if gc['coherent'] is not None:
                need(gf['coherent'] is not None,'shared coherent gate')
                need(same_decoder(gc['coherent']['decoder'],gf['coherent']['decoder']),'shared coherent decoder')
                need(same(gc['coherent']['detector'],gf['coherent']['detector']),'shared coherent detector')
            if syn(gc['final_decoder'])==0:need(same_decoder(gc['final_decoder'],gf['final_decoder']),'second guard zero-syndrome protection')
            need(not(frame['arms']['guard_coherent']['coded_errors']==0 and frame['arms']['guard_f1']['coded_errors']>0),'second guard harm')
            # Descriptive assembled decoding counterfactual, NOT a timed fifth policy.
            selected='scalar3' if frame['arms']['scalar3']['syndrome']==0 else 'f1_alone'
            frame['direct_f1_assembled_coded_errors']=frame['arms'][selected]['coded_errors']
            if payloads['guard_f1']['restart'] is not None:
                need(same_decoder(payloads['guard_f1']['restart']['final_decoder'],payloads['f1_alone']['final_decoder']),'F1 restart/standalone parity')
            frames.append(frame)
        call_total+=len(rows);bindings.append(dict(block=block,result_sha256=sha(run/'result.json'),manifest_sha256=sha(run/'manifest.json'),ledger_sha256=sha(run/'ledger.jsonl')))
    summaries={}
    for label,subset in [('all',frames)]+[(str(s),[f for f in frames if f['snr']==s]) for s in (600,650)]:
        summaries[label]={}
        for arm in ARMS:
            records=[f['arms'][arm] for f in subset];n=len(records);errors=sum(r['coded_errors']>0 for r in records)
            ci=[float(beta.ppf(.025,errors,n-errors+1)) if errors else 0.,float(beta.ppf(.975,errors+1,n-errors)) if errors<n else 1.]
            summaries[label][arm]=dict(n=n,coded_frame_errors=errors,fer=errors/n,fer_interval95=ci,fer_interval_kind='binomial reference only for fixed-stratum mixture' if label=='all' else 'Clopper-Pearson within stratum',information_frame_errors=sum(r['info_errors']>0 for r in records),undetected_errors=sum(r['coded_errors']>0 and r['syndrome']==0 for r in records),coherent_calls=sum(r['coherent_executed'] for r in records),restart_calls=sum(r['restart_executed'] for r in records),mean_ready_seconds=float(np.mean([r['ready_seconds'] for r in records])),mean_complete_seconds=float(np.mean([r['complete_seconds'] for r in records])),p95_ready_seconds=float(np.quantile([r['ready_seconds'] for r in records],.95)))
    for arm in ARMS:
        bounds=[]
        for snr in ('600','650'):
            cell=summaries[snr][arm];k=cell['coded_frame_errors'];n=cell['n']
            bounds.append([float(beta.ppf(.0125,k,n-k+1)) if k else 0.,float(beta.ppf(.9875,k+1,n-k)) if k<n else 1.])
        summaries['all'][arm]['stratified_conservative95']=[float(np.mean([b[j] for b in bounds])) for j in (0,1)]
    pairs=[]
    for a,b in [('scalar3','guard_coherent'),('scalar3','guard_f1'),('guard_coherent','guard_f1'),('f1_alone','guard_f1')]:
        rescue=[f['observation_id'] for f in frames if f['arms'][a]['coded_errors']>0 and f['arms'][b]['coded_errors']==0]
        harm=[f['observation_id'] for f in frames if f['arms'][a]['coded_errors']==0 and f['arms'][b]['coded_errors']>0]
        n=len(rescue)+len(harm);pairs.append(dict(reference=a,candidate=b,rescue=rescue,harm=harm,primary=len(pairs)<2,paired_exact_p=float(binomtest(len(rescue),n,.5).pvalue) if n else 1.))
    order=sorted(range(2),key=lambda i:pairs[i]['paired_exact_p']);prev=0.
    for rank,i in enumerate(order):prev=max(prev,min(1.,(2-rank)*pairs[i]['paired_exact_p']));pairs[i]['holm_p']=prev
    print(json.dumps(dict(status='pass',scorer_sha256=sha(Path(__file__)),registration_sha256=regsha,scope='2048 independent physical simulations; fixed equal SNR mixture; no real channel measurements',checks=dict(calls=call_total,guard_checks=guard_checks,full_raw_identity=True,truth_valid_codewords=True,schedule=True),summary=summaries,pairs=pairs,direct_f1_assembled=dict(status='posthoc decoding only; no measured latency',errors=sum(f['direct_f1_assembled_coded_errors']>0 for f in frames),rescue_vs_guard=[f['observation_id'] for f in frames if f['arms']['guard_f1']['coded_errors']>0 and f['direct_f1_assembled_coded_errors']==0],harm_vs_guard=[f['observation_id'] for f in frames if f['arms']['guard_f1']['coded_errors']==0 and f['direct_f1_assembled_coded_errors']>0]),bindings=bindings,frames=frames),indent=2,allow_nan=False))

if __name__=='__main__':main()
