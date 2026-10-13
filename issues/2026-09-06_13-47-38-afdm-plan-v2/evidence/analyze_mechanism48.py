"""Analyze the complete 48-frame controlled matrix, preserving paired failures."""
import hashlib
import json
from pathlib import Path
import tarfile
import numpy as np

ROOT = Path(__file__).resolve().parent
ARMS = ['a0', 'baseline', 'r00', 'r01', 'r10', 'r11', 'r11_protect0', 'ols_no_prior', 'mechanism_keep']


def load(path):
    with tarfile.open(path) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}


def main():
    raw = load(ROOT/'mechanism48-runtime.tar.gz')
    smoke = load(ROOT/'commonkeep-smoke-runtime.tar.gz')
    queues = [json.loads(r['queue-status.json']) for r in (raw, smoke)]
    assert all(q['complete'] and all(r['exit_code'] == 0 for r in q['runs']) for q in queues)
    rows = [json.loads(smoke['dev0-first/frames.jsonl'])]
    statuses = [json.loads(smoke['dev0-first/status.json'])]
    for rep in range(3):
        rows.extend(json.loads(line) for line in raw[f'dev{rep}/frames.jsonl'].splitlines())
        statuses.append(json.loads(raw[f'dev{rep}/status.json']))
    for s in statuses:
        assert s['complete'] and not s.get('failure')
        for k in ('source_sha256', 'checkpoint_sha256', 'calibration_sha256', 'ldpc_sha256', 'device'):
            assert s[k] == statuses[0][k]
    rows.sort(key=lambda r: (r['replicate'], r['frame_index']))
    assert [(r['replicate'],r['frame_index']) for r in rows] == [(rep,i) for rep in range(3) for i in range(16)]
    matrix, frame_records, behavior, costs = [], [], {a: [] for a in ARMS[2:8]}, []
    gate_pairs = []
    for frame in rows:
        assert frame['split'] == 'D_dev' and frame['snr'] == 8 and frame['receiver_shell'] == 'direct40'
        assert set(frame['arms']) == set(ARMS)
        keep = frame['arms']['mechanism_keep']; kt = keep['support_transaction']
        assert kt['reason'] == 'diagnostic_forced_keep' and kt['complete_proposals_used'] == 0
        assert kt['baseline'] == kt['committed'] and kt['score_tables'] == []
        matrix.append([int(frame['arms'][a]['info_errors'] > 0) for a in ARMS])
        labels = {}
        for name, a in frame['arms'].items():
            assert a['finite']
            caps = a['capacity_trace']
            assert [c['outer_iter'] for c in caps if c['stage']=='outer'] == list(range(10))
            assert all(c['unique_count'] == len(set(c['atom_ids'])) <= (48 if c['stage']=='temporary' else 40) for c in caps)
            if name in ARMS[:2]: continue
            tx = a['support_transaction']
            assert tx['baseline'] == kt['baseline']
            assert tx['reference_hashes'] == kt['reference_hashes']
            consumers = {e['stage']:e for e in a['transaction_consumer']}
            for stage in ('committed','t0_reconstruction'):
                assert consumers[stage]['gains'] == tx['committed']['gains']
                assert consumers[stage]['active_ids'] == tx['committed']['active_ids']
            assert a['final_bp_input_h_sha256'] == a['output_h_sha256']
            if name == 'mechanism_keep': continue
            assert tx['complete_proposals_used'] <= 1 and len(tx['score_tables']) <= 2
            if not tx['accepted']:
                assert tx['committed'] == tx['baseline']
                for key in ('output_h_sha256','output_x_sha256','sigma2_final','info_errors','raw_errors'):
                    assert a[key] == keep[key], (frame['replicate'],frame['frame_index'],name,key)
            for rr, table in enumerate(tx['score_tables']):
                ref = frame['mechanism_reference']['rounds'][rr]
                assert table['candidate_ids'] == [i for i in ref['candidate_ids'] if i not in table['support']]
                for candidate in table['candidates']:
                    i = ref['candidate_ids'].index(candidate['id'])
                    assert (candidate['pi'],candidate['sh2']) == (ref['pi'][i],ref['sh2'][i])
            delta = a['info_errors']-keep['info_errors']
            label = 'harmful' if delta>0 else 'beneficial' if delta<0 else 'tie'
            entry = dict(info_bit_label=label, info_bit_delta=delta,
                raw_bit_delta=a['raw_errors']-keep['raw_errors'],
                fer_harm=bool(a['info_errors']>0 and keep['info_errors']==0),
                fer_benefit=bool(a['info_errors']==0 and keep['info_errors']>0),
                proposed_action_kind=tx['action_kind'],
                committed_action_kind=tx['action_kind'] if tx['accepted'] else 'keep',
                accepted=tx['accepted'], reason=tx['reason'], objective_delta=tx['delta'])
            labels[name]=entry;behavior[name].append(entry)
        for no_gate, gate in [('r00','r01'),('r10','r11')]:
            left,right = [frame['arms'][name]['support_transaction'] for name in (no_gate,gate)]
            assert left['proposal'] == right['proposal']
            assert left['reference_hashes'] == right['reference_hashes']
            gate_pairs.append(dict(replicate=frame['replicate'],frame_index=frame['frame_index'],
                pair=[no_gate,gate], same_complete_proposal=True, rejected=not right['accepted'],
                executed_no_gate_info_bit_delta=labels[no_gate]['info_bit_delta'],
                executed_no_gate_fer_harm=labels[no_gate]['fer_harm']))
        costs.append(dict(receiver_seconds=sum(a['receiver_seconds'] for a in frame['arms'].values()),
            per_arm={name: {key:a[key] for key in ('receiver_seconds', 'standalone_seconds_estimate')}
                     for name,a in frame['arms'].items()},
            shared_mechanism_preparation_seconds=keep['shared_mechanism_preparation_seconds'],
            shared_scorer_preparation_seconds=keep['shared_scorer_preparation_seconds'],
            keep_seconds=keep['receiver_seconds']))
        frame_records.append(dict(replicate=frame['replicate'],frame_index=frame['frame_index'],
            input_hashes=frame['input_hashes'],info_errors={a:frame['arms'][a]['info_errors'] for a in ARMS},labels=labels))
    m = np.array(matrix,dtype=float); parts = m.reshape(3,16,9)
    rng=np.random.default_rng(2026090609)
    indices=[rng.integers(0,16,(20000,16)) for _ in range(3)]
    boot=sum(part[idx].mean(axis=1) for part,idx in zip(parts,indices))/3
    bits=np.array([[r['info_errors'][a] for a in ARMS] for r in frame_records],dtype=float)
    bit_parts=bits.reshape(3,16,9)
    bit_boot=sum(part[idx].mean(axis=1) for part,idx in zip(bit_parts,indices))/3
    weights={'statistics_no_F': {'r10':1,'r00':-1}, 'statistics_with_F':{'r11':1,'r01':-1},
        'gate_old_stats':{'r01':1,'r00':-1}, 'gate_projected_stats':{'r11':1,'r10':-1},
        'interaction':{'r11':1,'r10':-1,'r01':-1,'r00':1}, 'remove_protection':{'r11_protect0':1,'r11':-1}}
    weights.update({a+'_vs_keep':{a:1,'mechanism_keep':-1} for a in ARMS[2:8]})
    weights.update({a+'_vs_'+base:{a:1,base:-1} for a in ARMS[2:8] for base in ARMS[:2]})
    weights.update({'keep_vs_'+base:{'mechanism_keep':1,base:-1} for base in ARMS[:2]})
    contrasts={}
    for name,terms in weights.items():
        w=np.array([terms.get(a,0) for a in ARMS]);contrasts[name]=dict(delta_FER=float(m.mean(0)@w),
            bootstrap95=np.quantile(boot@w,[.025,.975]).tolist(),per_stream=[float(x.mean(0)@w) for x in parts],
            net_info_bit_delta=int(bits.sum(0)@w), mean_info_bit_delta=float(bits.mean(0)@w),
            mean_info_bit_delta_bootstrap95=np.quantile(bit_boot@w,[.025,.975]).tolist())
    result=dict(scope='48 paired development frames; descriptive mechanism evidence, not confirmatory safety/benefit',
        n=48,receiver_evaluations=432,smoke_reused_receivers=9,new_receivers=423,
        pooled_errors=dict(zip(ARMS,m.sum(0).astype(int).tolist())),
        per_stream_errors=[dict(zip(ARMS,x.sum(0).astype(int).tolist())) for x in parts],
        actions={a:{'beneficial':sum(x['info_bit_label']=='beneficial' for x in xs),
            'harmful':sum(x['info_bit_label']=='harmful' for x in xs),'tie':sum(x['info_bit_label']=='tie' for x in xs),
            'accepted':sum(x['accepted'] for x in xs),'FER_benefit':sum(x['fer_benefit'] for x in xs),
            'FER_harm':sum(x['fer_harm'] for x in xs)} for a,xs in behavior.items()},
        contrasts=contrasts,bootstrap=dict(seed=2026090609,draws=20000,unit='paired frame within stream',
            limitation='descriptive percentile, no multiplicity or coverage guarantee'),frame_records=frame_records,
        costs=costs,gate_pairs=gate_pairs,queues=queues,subprocess_seconds=sum(r['ended_at']-r['started_at'] for q in queues for r in q['runs']),
        artifact_sha256={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()},
        reused_smoke_sha256={k:hashlib.sha256(v).hexdigest() for k,v in smoke.items()})
    (ROOT/'mechanism48-runtime-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('pooled_errors','per_stream_errors','actions')},indent=2))


if __name__=='__main__':
    main()
