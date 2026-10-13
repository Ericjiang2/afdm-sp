"""Independent offline scoring for fresh reaction and archived repair campaigns."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from scipy.stats import binomtest
sys.path.insert(0,'/data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/analysis')
from score_development import bound,same,sha,lines,evidence,ROOT,BASE,TASK


def need(test,message):
    if not test:raise ValueError(message)


def main():
    kind=sys.argv[1]
    need(kind in ('confirmation','repairs'),'unknown run kind')
    fresh=kind=='confirmation'
    run=TASK/'experiments'/('confirmation_v1' if fresh else 'repairs_dev_v2')
    population=(TASK/'experiments/confirmation_population_observed' if fresh else
                ROOT/'results/tf_cstate_prospective_20260923/population_observed')
    truthroot=(TASK/'experiments/confirmation_population_truth' if fresh else
               ROOT/'results/tf_cstate_prospective_20260923/population_truth')
    arms=['scalar','coherent','full'] if fresh else ['coherent3','local4','pair4','f1_restart']
    armkey='arm' if fresh else 'policy';inputkey='observation_sha256' if fresh else 'input_sha256'
    count=1536 if fresh else 512
    result=json.loads((run/'result.json').read_text());manifest=json.loads((run/'manifest.json').read_text())
    need(result['status']=='pass' and result['completed_calls']==count,'incomplete result')
    need(sha(run/'manifest.json')==result['manifest_sha256'],'manifest hash')
    need(sha(run/'ledger.jsonl')==result['ledger_sha256'],'ledger hash')
    afile='allcalls.jsonl' if fresh else 'attempts.jsonl'
    akey='allcalls_sha256' if fresh else 'attempts_sha256'
    need(sha(run/afile)==result[akey],'attempt log hash')
    rows=lines(run/'ledger.jsonl');attempts=lines(run/afile)
    need(len(rows)==count and len(attempts)==2*count,'attempt counts')
    need([r['call_index'] for r in rows]==list(range(count)),'call index allocation')
    regpath=TASK/'experiments'/('confirmation_registration.json' if fresh else 'repairs_registration.json')
    need(sha(regpath)==manifest['registration_sha256'],'registration binding')
    reg=json.loads(regpath.read_text())
    expected_ids=([f'i{s}_f{f:04d}' for s in (600,650) for f in range(256)] if fresh else reg['observation_ids'])
    expected=[(stem,a) for i,stem in enumerate(expected_ids) for a in arms[i%len(arms):]+arms[:i%len(arms)]]
    need([(r['observation_id'],r[armkey]) for r in rows]==expected,'registered ordered cohort')
    need(len({(r['observation_id'],r[armkey]) for r in rows})==count,'duplicate rows')
    for i,row in enumerate(rows):
        a,b=attempts[2*i:2*i+2]
        need(a['event']==('attempt_started' if fresh else 'started') and
             b['event']==('attempt_finished' if fresh else 'finished'),'event sequence')
        for key in ('call_index','observation_id',armkey,inputkey):need(a[key]==b[key]==row[key],'event identity')
        need({k:v for k,v in b.items() if k!='event'}==row,'event/ledger payload')
    popseal=json.loads((population/'observed_seal.json').read_text())
    tseal=json.loads((truthroot/'truth_seal.json').read_text())
    need(popseal['status']==tseal['status']=='pass','unsealed input')
    need(sha(population/'ledger.jsonl')==popseal['files']['ledger.jsonl'],'observed ledger hash')
    need(sha(truthroot/'ledger.jsonl')==tseal['files']['ledger.jsonl'],'truth ledger hash')
    inputs={r['observation_id']:r for r in lines(population/'ledger.jsonl')}
    truths={r['observation_id']:r for r in lines(truthroot/'ledger.jsonl')}
    cache=BASE/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    need(sha(cache)==manifest['locked_hashes']['ldpc_cache_sha256'],'code identity')
    with np.load(cache) as z:H,free=z['H'],z['free_cols']
    grouped={};checked_inputs=set()
    for row in rows:
        need(row['status']=='ok','failed row in complete result')
        stem,arm=row['observation_id'],row[armkey];inp=inputs[stem];tr=truths[stem]
        need(row[inputkey]==inp['observation_sha256'],'input pairing')
        if stem not in checked_inputs:
            need(popseal['files'][inp['observation_path']]==inp['observation_sha256'],'observed seal raw')
            observed=bound(population/inp['observation_path'],inp['observation_sha256'])
            need(observed['observation_id']==stem and observed['stream_ids']==inp['stream_ids'],'observed payload identity')
            checked_inputs.add(stem)
        need(tr['stream_ids']==inp['stream_ids'] and tr['observation_hash']==inp['observation_hash'],'truth pairing')
        need(tseal['files'][tr['truth_path']]==tr['truth_sha256'],'truth seal raw')
        truth=bound(truthroot/tr['truth_path'],tr['truth_sha256'])
        _,truth_identity=evidence.load_artifact(truthroot/tr['truth_path'])
        need(truth_identity['kind']=='truth' and truth_identity['observation_id']==stem,'truth envelope identity')
        identity=(dict(schema=row['schema'],observation_id=stem,arm=arm,observation_sha256=row[inputkey]) if fresh
                  else dict(observation_id=stem,policy=arm,input_sha256=row[inputkey]))
        raw=bound(run/row['raw_path'],row['raw_sha256'],identity)
        frame=grouped.setdefault(stem,dict(observation_id=stem,snr=inp['snr_centi_db'],
                          input_sha256=inp['observation_sha256'],truth_sha256=tr['truth_sha256'],arms={}))
        if '_prefix' in frame:need(same(frame['_prefix'],raw['prefix_arrays']),'full prefix differs')
        else:frame['_prefix']=raw['prefix_arrays']
        coded,info=np.asarray(truth['coded']),np.asarray(truth['info'])
        final=np.asarray(raw['final_decoder']['decoded'])
        need(coded.shape==final.shape==(2048,) and np.isin(final,(0,1)).all(),'invalid codeword')
        need(np.array_equal(coded[free],info),'truth information mapping')
        syndrome=int(np.count_nonzero((H@final)%2))
        need(syndrome==row['final_syndrome_weight' if fresh else 'final_syndrome'],'syndrome recount')
        if fresh:
            for cp in row['checkpoints']:need(sha(run/cp['path'])==cp['artifact_sha256'],'checkpoint hash')
        record=dict(info_errors=int(np.count_nonzero(final[free]!=info)),coded_errors=int(np.count_nonzero(final!=coded)),
            syndrome=syndrome,raw_sha256=row['raw_sha256'],
            complete_seconds=row['complete_artifact_seconds' if fresh else 'complete_seconds'],
            ready_seconds=row['receiver_seconds' if fresh else 'receiver_ready_seconds'])
        if not fresh:
            syn=lambda d:int(np.count_nonzero((H@d['decoded'])%2))
            before=syn(raw['prefix_decoder']);need(before==row['native_syndrome'],'prefix syndrome')
            need(len(raw['branches'])==row['branch_count'],'raw branch count')
            trigger=bool(before and syn(raw['branches'][0]['decoder']))
            need(trigger==row['repair_trigger'],'repair gate recount')
            need((raw['restart'] is not None)==row['restart_executed']==(trigger and arm=='f1_restart'),'restart gate')
            expected_final=raw['prefix_decoder']
            if before:
                expected_final=raw['branches'][0]['decoder']
                if trigger and arm in ('local4','pair4'):expected_final=raw['branches'][1]['decoder']
                if trigger and arm=='f1_restart':
                    expected_final=raw['restart']['decoder']
                    if syn(expected_final):expected_final=raw['branches'][-1]['decoder']
            need(same(raw['final_decoder'],expected_final),'final selected output')
            record.update(repair_trigger=row['repair_trigger'],branch_count=row['branch_count'],restart_executed=row['restart_executed'])
            if arm=='pair4' and len(raw['branches'])>1:
                record['pair_bank']=raw['branches'][1]['geometry_result']['diagnostics']['near_cluster_bank']
        frame['arms'][arm]=record
    frames=[grouped[s] for s in sorted(grouped)]
    for f in frames:del f['_prefix'];need(set(f['arms'])==set(arms),'incomplete pairing')
    need(len(frames)==(512 if fresh else 128),'observation count')
    summaries={}
    for label,subset in [('all',frames)]+[(str(s),[f for f in frames if f['snr']==s]) for s in sorted({f['snr'] for f in frames})]:
        summaries[label]={a:dict(n=len(subset),errors=sum(f['arms'][a]['info_errors']>0 for f in subset),
            coded_frame_errors=sum(f['arms'][a]['coded_errors']>0 for f in subset),
            undetected_errors=sum(f['arms'][a]['coded_errors']>0 and f['arms'][a]['syndrome']==0 for f in subset),
            mean_ready_seconds=float(np.mean([f['arms'][a]['ready_seconds'] for f in subset])),
            mean_complete_seconds=float(np.mean([f['arms'][a]['complete_seconds'] for f in subset]))) for a in arms}
    pairs=[]
    for arm in arms[1:]:
        rescue=[f['observation_id'] for f in frames if f['arms'][arms[0]]['coded_errors']>0 and f['arms'][arm]['coded_errors']==0]
        harm=[f['observation_id'] for f in frames if f['arms'][arms[0]]['coded_errors']==0 and f['arms'][arm]['coded_errors']>0]
        n=len(rescue)+len(harm)
        pairs.append(dict(reference=arms[0],candidate=arm,rescue=rescue,harm=harm,
                          paired_exact_p=float(binomtest(len(rescue),n,.5).pvalue) if n else 1.))
    order=sorted(range(len(pairs)),key=lambda i:pairs[i]['paired_exact_p']);previous=0.
    for rank,i in enumerate(order):
        previous=max(previous,min(1.,(len(order)-rank)*pairs[i]['paired_exact_p']))
        pairs[i]['holm_p']=previous
    direct=[]
    if not fresh:
        for a,b in [('local4','pair4'),('local4','f1_restart')]:
            direct.append(dict(reference=a,candidate=b,rescue=[f['observation_id'] for f in frames if f['arms'][a]['coded_errors']>0 and f['arms'][b]['coded_errors']==0],harm=[f['observation_id'] for f in frames if f['arms'][a]['coded_errors']==0 and f['arms'][b]['coded_errors']>0]))
    print(json.dumps(dict(status='pass',direct_descriptive_pairs=direct,scorer_sha256=sha(Path(__file__)),primary_endpoint='coded frame error',kind=kind,scope='fresh registered confirmation' if fresh else 'exposed enriched development',
        checks=dict(calls=count,identity_and_events=True,prefix_arrays_equal=True),summary=summaries,pairs=pairs,frames=frames,
        manifest_sha256=result['manifest_sha256'],ledger_sha256=result['ledger_sha256'],receiver_calls_added=0),indent=2,allow_nan=False))


if __name__=='__main__':main()
