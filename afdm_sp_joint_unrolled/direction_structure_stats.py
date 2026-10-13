"""M02 strict255-block CPU structure replay audit; no final route selection."""
from __future__ import annotations
import argparse
import itertools
from pathlib import Path

import numpy as np

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_logging import validate_record
from afdm_sp_joint_unrolled.direction_select import read,paired_interval

ARMS=('free','group','link','sham')


def comparison(reference,linked):
    result=paired_interval(list(reference),list(linked),comparisons=3)
    return dict(result,definition='FER_reference - FER_link; positive benefits link',
                precision_insufficient=bool(result['interval'][0]<=0<=result['interval'][1]),
                scope='simultaneous conservative95% intervals for three comparisons; exploratory mechanism sample')


def verify_snapshot(entry,*,load=False):
    import hashlib
    path=Path(entry['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise ValueError('snapshot hash mismatch')
    if load:
        with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
    return None


def validate_source_equivalence(manifest):
    allowed={'direction_structure_run.py','direction_structure_replay.py',
             'test_direction_structure_run.py','test_direction_structure_replay.py'}
    maps=manifest['source_maps']
    if manifest['reason']!='device_metadata_fix' or len(maps)!=2 or maps[0]==maps[1]:
        raise ValueError('source equivalence requires two distinct exact source maps')
    if set(maps[0])!=set(maps[1]) or not maps[0]:
        raise ValueError('source equivalence cannot add/remove modules')
    for key in maps[0]:
        if maps[0][key]!=maps[1][key] and Path(key).name not in allowed:
            raise ValueError('numerical source drift is not permitted')
    return maps


def corrected_metadata(record,digest,contract,contract_hash,manifest):
    if manifest['reason']!='device_metadata_fix':raise ValueError('invalid metadata correction reason')
    matches=[e for e in manifest['records'] if e['record_sha256']==digest]
    if len(matches)!=1:raise ValueError('missing/duplicate correction record binding')
    entry=matches[0]
    import hashlib
    import json
    source_digest=entry['source_manifest_sha256']
    source_map=manifest['sources'][source_digest]
    if hashlib.sha256(json.dumps(source_map,sort_keys=True).encode()).hexdigest()!=source_digest:
        raise ValueError('metadata correction source digest mismatch')
    if (entry['contract_sha256']!=contract_hash or source_map!=record['source_sha256']
            or source_map!=contract['source_sha256']
            or entry['original_device']!=record['device'] or entry['original_dtype']!=record['dtype']):
        raise ValueError('metadata correction binding mismatch')
    command=contract['command']
    if (not isinstance(command,list) or command.count('--device')!=1
            or any(str(x).startswith('--device=') for x in command)):
        raise ValueError('correction requires unique --device cpu command')
    index=command.index('--device')
    if index+1>=len(command) or command[index+1]!='cpu':
        raise ValueError('correction requires unique --device cpu command')
    result=dict(record)
    result.update(original_device=record['device'],original_dtype=record['dtype'],
                  device='cpu',dtype={'fit':'complex128','terminal':'complex128'})
    return result


def load_run(root,phash,correction=None):
    import hashlib
    import json
    root=Path(root)
    if (root/'failure.json').exists():raise ValueError('failed structure run cannot be treated as complete')
    complete,chash=read(root/'complete.json');contract,khash=read(root/'contract.json')
    counts=complete['calls_attempted']
    if (complete['status']!='complete' or counts!=complete['calls_completed']
            or set(counts)!={'structure_CE','structure_terminal'} or contract['split']!='mechanism'
            or complete['protocol_sha256']!=phash or contract['protocol_sha256']!=phash):
        raise ValueError('invalid complete structure call accounting or protocol/split')
    for key in ('source_sha256','algorithm_registry_sha256','allocation_registry_sha256'):
        if complete[key]!=contract[key]:raise ValueError('structure registry/source mismatch')
    config=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    files={Path(p).name for p in complete['records']}
    actual={p.name for pattern in ('CE-*.json','terminal-*.json') for p in root.glob(pattern)}
    if files!=actual or len(files)!=sum(counts.values()):raise ValueError('missing/extra structure records')
    hashes={Path(p).name:h for p,h in complete['record_sha256'].items()}
    normal={}
    for entry in complete['normal_provenance']:
        row,digest=read(entry['path'])
        if digest!=entry['sha256'] or not entry['pairing_verified']:raise ValueError('normal provenance mismatch')
        if row['protocol_sha256']!=phash or row['split']!='mechanism':raise ValueError('wrong normal protocol/split')
        validate_record(row,deployable=True)
        verify_snapshot(row['snapshot'])
        geo=verify_snapshot(entry['geometry_snapshot'],load=True)
        if row['block_id'] in normal:raise ValueError('duplicate normal block')
        normal[row['block_id']]=(row,digest,geo,entry['geometry_snapshot']['sha256'])
    if set(normal)!=set(contract['blocks']):raise ValueError('normal block manifest incomplete')
    records=[];seen=set();record_hashes={};corrected=0
    for kind,count in counts.items():
        for prefix in ('started','completed'):
            if len(list(root.glob(f'{prefix}-{kind}-*.json')))!=count:raise ValueError('incomplete call ledger')
        for index in range(1,count+1):
            start,_=read(root/f'started-{kind}-{index:06d}.json');end,_=read(root/f'completed-{kind}-{index:06d}.json')
            if start['ordinal']!=index or start['call_key']!=kind or any(end[k]!=v for k,v in start.items()):
                raise ValueError('structure call start/completion mismatch')
            name=Path(end['record']).name
            if name not in files or name in seen:raise ValueError('duplicate/unknown completed record')
            seen.add(name);r,digest=read(root/name)
            if (digest!=hashes[name] or digest!=end['record_sha256'] or r['protocol_sha256']!=phash
                    or r['source_sha256']!=contract['source_sha256'] or r['config_sha256']!=config
                    or r['split']!='mechanism' or r['SNR']!=contract['SNR'] or r['failure'] is not None
                    or r['block_id']!=start['block'] or r['arm_id']!='M_'+start['arm']):
                raise ValueError('structure record provenance mismatch')
            n,nhash,geometry,geometry_hash=normal[r['block_id']]
            if r['geometry_snapshot']['sha256']!=geometry_hash:raise ValueError('geometry provenance mismatch')
            if r['normal_record_sha256']!=nhash or r['input_hashes']!=n['input_hashes']:
                raise ValueError('normal/structure input pairing failed')
            shot=verify_snapshot(r['snapshot'],load=True)
            verify_snapshot(r['geometry_snapshot'])
            if kind=='structure_terminal':
                validate_record(r,deployable=False)
                if r['device']!='cpu':
                    if correction is None:raise ValueError('registered structure statistics require CPU replay')
                    r=corrected_metadata(r,digest,contract,khash,correction);corrected+=1
                if r['sigma_value']!=n['sigma_value'] or r['truth_access_level']!='geometry_oracle' or r['candidate_eligible'] is not False:
                    raise ValueError('structure noise/oracle contract mismatch')
                hhash=array_hash(shot['Hfit'])
                if (r['H_cancel_source']['sha256']!=hhash or r['H_data_source']['sha256']!=hhash
                        or r['H_cov_source']['H_sha256']!=hhash
                        or r['data_residual']['relative_vector_closure']>1e-10):
                    raise ValueError('Hfit consumption/residual closure mismatch')
                ids=r['S_submitted']
                if array_hash(shot['decoded'])!=r['hard_output_hash']:raise ValueError('terminal decoded hash mismatch')
            else:ids=shot['I'].tolist()
            if ids!=geometry['I'].tolist():raise ValueError('fit added/removed shared I atom')
            r['_coefficients']=shot['coefficients'];r['_geometry']=geometry
            r['_kind']=kind;records.append(r);record_hashes[name]=digest
    return records,{'root':str(root),'complete_sha256':chash,'contract_sha256':khash,
        'source_sha256':contract['source_sha256'],'algorithm_registry_sha256':contract['algorithm_registry_sha256'],
        'allocation_registry_sha256':contract['allocation_registry_sha256'],'record_sha256':record_hashes,
        'normal_provenance':complete['normal_provenance'],'calls':counts,'failures':0,'metadata_corrected_rows':corrected}


def validate_table(rows):
    table={}
    for r in rows:
        key=(r['SNR'],r['block_id'],r['arm_id'],r['_kind'])
        if key in table:raise ValueError('duplicate structure record identity')
        table[key]=r
    expected=set(itertools.product((7,8,9),range(255),('M_'+a for a in ARMS),('structure_CE','structure_terminal')))
    if set(table)!=expected:raise ValueError('requires255x3x4 paired CE and terminal records')
    for snr,block in itertools.product((7,8,9),range(255)):
        base=table[snr,block,'M_free','structure_terminal']
        for arm in ('M_'+a for a in ARMS):
            t=table[snr,block,arm,'structure_terminal'];ce=table[snr,block,arm,'structure_CE']
            if (t['input_hashes']!=base['input_hashes'] or t['S_submitted']!=base['S_submitted']
                    or t['sigma_value']!=base['sigma_value'] or t['device']!=base['device']
                    or t['fit_diagnostics']!=ce['fit_diagnostics']
                    or not np.array_equal(t['_coefficients'],ce['_coefficients'])):
                raise ValueError('four-arm common-state or CE/terminal mismatch')
            if not np.array_equal(t['_geometry']['L_I'],base['_geometry']['L_I']):raise ValueError('geometry differs by arm')
        linked=table[snr,block,'M_link','structure_terminal']['fit_diagnostics']
        sham=table[snr,block,'M_sham','structure_terminal']['fit_diagnostics']
        if not linked['zero_model']:
            info=sham['sham']
            if (linked['basis_rank']!=sham['basis_rank'] or info['rank_link']!=info['rank_sham']
                    or linked['incidence']!=sham['incidence'] or info['incidence_preserved'] is not True
                    or not np.allclose(info['singular_link'],info['singular_sham'],rtol=1e-10,atol=1e-12)):
                raise ValueError('link/sham rank/incidence/spectrum mismatch')
    for block in range(255):
        ref=table[8,block,'M_free','structure_terminal']['input_hashes']
        for snr in (7,9):
            other=table[snr,block,'M_free','structure_terminal']['input_hashes']
            if any(ref[k]!=other[k] for k in ('H','info','coded','noise','pilot','data')):
                raise ValueError('cross-SNR structure exogenous mismatch')
    return table


def describe(table):
    output={}
    for snr in (7,8,9):
        arms={};contrasts={}
        linked=[table[snr,b,'M_link','structure_terminal']['FER'] for b in range(255)]
        for arm in ('M_'+a for a in ARMS):
            rows=[table[snr,b,arm,'structure_terminal'] for b in range(255)]
            costs=[r['elapsed_seconds'] for r in rows];fits=[r['fit_seconds'] for r in rows]
            arms[arm]={'n':255,'frame_errors':sum(r['FER'] for r in rows),'FER':sum(r['FER'] for r in rows)/255,
                'decoded_info_BER':sum(r['coded_bit_errors'] for r in rows)/sum(r['coded_bits_denominator'] for r in rows),
                'raw_coded_BER':sum(r['raw_bit_errors'] for r in rows)/sum(r['raw_bits_denominator'] for r in rows),
                'terminal_mean':float(np.mean(costs)),'terminal_p95':float(np.quantile(costs,.95)),
                'CE_mean':float(np.mean(fits)),'CE_p95':float(np.quantile(fits,.95)),
                'zero_I_frames':sum(r['fit_diagnostics']['zero_model'] for r in rows),
                'fitted_rank_histogram':{str(rank):sum(r['fit_diagnostics'].get('rank',r['fit_diagnostics'].get('observation_rank'))==rank for r in rows)
                    for rank in sorted({r['fit_diagnostics'].get('rank',r['fit_diagnostics'].get('observation_rank')) for r in rows})}}
            if arm!='M_link':contrasts[arm]=comparison([r['FER'] for r in rows],linked)
        sham=[table[snr,b,'M_sham','structure_terminal']['fit_diagnostics'] for b in range(255)]
        output[str(snr)]={'arms':arms,'link_vs_reference':contrasts,
            'sham_degenerate_frames':sum(d['zero_model'] or not d['sham']['sham_nontrivial'] for d in sham),
            'sham_scope':'All degenerate/empty cases retained; no redraw or deletion'}
    gates={}
    for arm in ('M_free','M_group','M_sham'):
        anchor=output['8']['link_vs_reference'][arm]
        neighbor=all(output[str(s)]['link_vs_reference'][arm]['delta']>=0 for s in (7,9))
        gates[arm]={'resource_gate_passed':anchor['delta']>=.05 and neighbor,
            'precision_insufficient':anchor['precision_insufficient'],
            'neighbor_point_directions_nonnegative':neighbor,
            'scope':'resource allocation screen only; not a realizable method or confirmation claim'}
    return output,gates


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--algorithm-registry',type=Path,required=True)
    p.add_argument('--allocation-registry',type=Path,required=True);p.add_argument('--run-dir',type=Path,action='append',required=True)
    p.add_argument('--metadata-correction',type=Path)
    p.add_argument('--source-equivalence',type=Path)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    correction,correction_hash=read(args.metadata_correction) if args.metadata_correction else (None,None)
    equivalence,equivalence_hash=read(args.source_equivalence) if args.source_equivalence else (None,None)
    equivalent_maps=validate_source_equivalence(equivalence) if equivalence else None
    protocol,phash=read(args.protocol);algorithm,ahash=read(args.algorithm_registry);allocation,lhash=read(args.allocation_registry)
    if (protocol['campaign_id']!='afdm-direction-20260908-v1' or allocation['protocol_sha256']!=phash
            or algorithm['status']!='algorithm_preregistered_before_structure_results'
            or allocation['status']!='allocation_frozen_before_structure_results'
            or allocation['arms']!=['M_'+a for a in ARMS]
            or allocation['blocks']!=list(range(255)) or allocation['SNR']!=[7,8,9]):raise ValueError('frozen allocation mismatch')
    rows=[];sources=[]
    for root in args.run_dir:
        r,s=load_run(root,phash,correction)
        if equivalent_maps is not None and s['source_sha256'] not in equivalent_maps:raise ValueError('source not bound by equivalence manifest')
        if s['algorithm_registry_sha256']!=ahash or s['allocation_registry_sha256']!=lhash:
            raise ValueError('mixed algorithm/allocation registry')
        if sources and s['source_sha256']!=sources[0]['source_sha256'] and equivalent_maps is None:raise ValueError('mixed source snapshots')
        rows.extend(r);sources.append(s)
    table=validate_table(rows);descriptions,gates=describe(table)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    publish_json(args.out,{'status':'complete','protocol_sha256':phash,'algorithm_registry_sha256':ahash,
        'allocation_registry_sha256':lhash,'provenance':sources,'by_SNR':descriptions,'resource_screens':gates,
        'counts':{'paired_blocks':255,'SNR_records':765,'CE':3060,'terminal':3060,'failures_in_supplied_runs':0},
        'metadata_correction_sha256':correction_hash,'metadata_corrected_rows':sum(s['metadata_corrected_rows'] for s in sources),
        'source_equivalence_sha256':equivalence_hash,'final_route_selected':False,'scope':'M02 geometry-oracle evidence only; neighbors descriptive; no final M/I/T route or legal-method discovery claim'})


if __name__=='__main__':main()
