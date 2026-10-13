"""Read-only O1_S/O1_F final-terminal analysis on audited 32 G1 blocks.

The old FULL prefix and terminal controls are frozen. These are exposed
development channels and exploratory descriptive intervals, not confirmation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
PRED=HERE/'ce-state-predictions-v1.json'
DEFAULT_OLD=PROJECT/'afdm_sp_joint_unrolled/outputs_trans_next_20260913'
DEFAULT_CONTRACTS=PROJECT/'afdm_sp_joint_unrolled/outputs_ce_state_20260915/contracts'
ARMS=('O1_S','O1_F')
SNRS=(7,8)
BLOCKS=tuple(range(32))
BOOTSTRAP_SEED=202609150601  # analysis-time descriptive choice; not frozen P2/CONF
BOOTSTRAP_DRAWS=20000


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(ok,message):
    if not ok:
        raise ValueError(message)


def audited_oracle_rows(old_root,contract_root):
    """Verify all four immutable stage admissions before collecting any endpoint."""
    prediction_sha=digest(PRED)
    expected_blocks={'engineering':{0,20},'development':set(BLOCKS)-{0,20}}
    rows={};bindings={};source=None;script=None;reference_sha=None
    for arm in ARMS:
        letter=arm[-1].lower()
        for stage in ('engineering','development'):
            tag=f'ce-o1-{letter}-{stage}-v2'
            contract_path=Path(contract_root)/(tag+'.json')
            audit_path=Path(old_root)/'evidence'/(tag+'-raw-audit.json')
            contract=read(contract_path);audit=read(audit_path)
            require(contract.get('schema')=='oracle-terminal-v1' and
                contract.get('tag')==tag and contract.get('stage')==stage and
                contract.get('arms')==[arm] and contract.get('snrs')==list(SNRS) and
                set(contract.get('blocks',[]))==expected_blocks[stage] and
                contract.get('predictions_sha256')==prediction_sha,
                'O1 frozen contract identity/prediction differs: '+tag)
            require((contract.get('temperature'),contract.get('bp_iterations'),
                     contract.get('ldpc_maxiter'),contract.get('clip'))==(1.,20,50,20.)
                    and contract.get('device')=='cpu' and contract.get('threads')==1,
                'O1 terminal numerical/control recipe differs: '+tag)
            expected_points=2*len(expected_blocks[stage])
            require(audit.get('status')=='PASS' and
                audit.get('contract_sha256')==digest(contract_path) and
                audit.get('source_sha256')==contract['source_sha256'] and
                audit.get('complete_matrix_mode')==(arm=='O1_F') and
                audit.get('saved_records')==2*expected_points and
                audit.get('new_F_T_D_A_calls')==0 and
                len(audit.get('rows',[]))==expected_points,
                'O1 stage audit failed or T/D record scope differs: '+tag)
            if source is None:source=contract['source_sha256'];script=audit['script_sha256']
            require(contract['source_sha256']==source and audit['script_sha256']==script,
                'O1 stages use different production snapshot or runner: '+tag)
            current_reference=contract['old_inputs'].get('runs/g1-strong-development-recovery-v1/development/summary.json')
            if reference_sha is None:reference_sha=current_reference
            require(current_reference==reference_sha and current_reference is not None,
                'old FULL source binding differs across O1 stages')
            for row in audit['rows']:
                key=(row['block'],row['snr'],arm)
                scores=row['scores']
                require(row['block'] in expected_blocks[stage] and row['snr'] in SNRS and
                    row['arm']==arm and key not in rows and
                    scores['info_bits']==1024 and scores['coded_bits']==2048 and
                    scores['FER'] in (0,1) and
                    scores['FER']==int(scores['info_bit_errors']>0) and
                    0<=scores['info_bit_errors']<=1024 and
                    np.isfinite(scores['bit_NLL']) and scores['bit_NLL']>=0 and
                    type(row['actual_edges']) is int and row['actual_edges']>=0 and
                    np.isfinite(row['operator_action']['operator_relative_squared']) and
                    row['operator_action']['operator_relative_squared']>=0,
                    'O1 saved endpoint invalid or duplicate: '+str(key))
                rows[key]=row
            bindings[tag]=dict(contract_sha256=digest(contract_path),
                audit_sha256=digest(audit_path),remote_summary_sha256=audit['summary_sha256'],
                source_sha256=source,script_sha256=script,points=expected_points)
    wanted={(b,s,a) for b in BLOCKS for s in SNRS for a in ARMS}
    require(set(rows)==wanted,'O1_S/O1_F 32-block x 2-SNR endpoint inventory incomplete')
    return rows,bindings


def full_reference(old_root,contract_root,oracle_rows):
    contract=read(Path(contract_root)/'ce-o1-s-development-v2.json')
    expected_hash=contract['old_inputs']['runs/g1-strong-development-recovery-v1/development/summary.json']
    path=Path(old_root)/'runs/g1-strong-development-recovery-v1/development/summary.json'
    require(digest(path)==expected_hash,'old G1 FULL summary differs from O1 frozen binding')
    summary=read(path)
    require(summary.get('status')=='COMPLETE' and len(summary.get('records',[]))==288,
        'old G1 FULL summary incomplete')
    old_audit_path=Path(old_root)/'evidence/g1-strong-development-recovery-v1-raw-audit.json'
    expected_audit_hash=contract['old_inputs']['evidence/g1-strong-development-recovery-v1-raw-audit.json']
    require(digest(old_audit_path)==expected_audit_hash,
        'old G1 independent raw audit differs from frozen O1 binding')
    old_audit=read(old_audit_path)
    require(old_audit.get('status')=='PASS' and old_audit.get('summary_sha256')==expected_hash,
        'old G1 FULL raw audit failed or summary binding differs')
    old={}
    for entry in summary['records']:
        if entry.get('kind')!='F' or entry.get('arm')!='G1_FULL':continue
        key=(entry['block'],entry['snr'])
        score=entry['scores']
        require(key not in old and key[0] in BLOCKS and key[1] in SNRS and
            score['FER'] in (0,1) and
            score['coded_bits_denominator']==1024 and
            0<=score['coded_bit_errors']<=1024 and
            score['FER']==int(score['coded_bit_errors']>0) and
            np.isfinite(score['bit_NLL']) and score['bit_NLL']>=0,
            'old FULL information BER/FER endpoint invalid')
        old[key]=entry
    require(set(old)=={(b,s) for b in BLOCKS for s in SNRS},
        'old FULL 64 endpoints incomplete')
    for (block,snr),entry in old.items():
        for arm in ARMS:
            require(oracle_rows[block,snr,arm]['reference_record_sha256']==entry['sha256'],
                'O1 oracle was not paired to its frozen old FULL endpoint')
    audited={(r['block'],r['snr']):r['scores'] for r in old_audit['rows'] if r['arm']=='G1_FULL'}
    require(set(audited)==set(old) and all(audited[key]==entry['scores'] for key,entry in old.items()),
        'old FULL per-channel scores differ from independent raw audit')
    return old,dict(path=str(path),summary_sha256=expected_hash,
        raw_audit_sha256=expected_audit_hash,
        source_sha256=summary.get('source_sha256'),
        score_scope='FER/information-bit BER and coded-bit LLR NLL from original FULL; NLL uses the same bit-margin formula as oracle decoder_scores. Old terminal graph edges are not supplied.')


def values(old,oracle,metric,snr,arm):
    if arm=='FULL':
        if metric=='FER':return np.array([old[b,snr]['scores']['FER'] for b in BLOCKS],float)
        if metric=='info_BER':return np.array([old[b,snr]['scores']['coded_bit_errors']/1024 for b in BLOCKS],float)
        if metric=='bit_NLL':return np.array([old[b,snr]['scores']['bit_NLL'] for b in BLOCKS],float)
        raise ValueError('old FULL bound score cannot supply terminal graph edges')
    if metric=='FER':return np.array([oracle[b,snr,arm]['scores']['FER'] for b in BLOCKS],float)
    if metric=='info_BER':return np.array([oracle[b,snr,arm]['scores']['info_bit_errors']/1024 for b in BLOCKS],float)
    if metric=='bit_NLL':return np.array([oracle[b,snr,arm]['scores']['bit_NLL'] for b in BLOCKS],float)
    if metric=='edges':return np.array([oracle[b,snr,arm]['actual_edges'] for b in BLOCKS],float)
    raise ValueError('unknown O1 descriptive metric')


def descriptive_pair(a,b,draws):
    require(a.shape==b.shape==(32,) and np.isfinite(a).all() and np.isfinite(b).all(),
        'paired descriptive vectors must contain 32 finite channel outcomes')
    differences=b-a
    sampled=differences[draws].mean(axis=1)
    return dict(mean_after_minus_before=float(differences.mean()),
        percentile_95_CI=np.quantile(sampled,[.025,.975],method='linear').tolist(),
        channel_differences=differences.tolist())


def analyze(old_root,contract_root):
    oracle,stage_bindings=audited_oracle_rows(old_root,contract_root)
    old,reference_binding=full_reference(old_root,contract_root,oracle)
    draws=np.random.default_rng(BOOTSTRAP_SEED).integers(0,32,(BOOTSTRAP_DRAWS,32))
    aggregate={};paired={}
    for snr in SNRS:
        label=str(snr)
        aggregate[label]={};paired[label]={}
        for arm in ('FULL',*ARMS):
            metrics=('FER','info_BER','bit_NLL') if arm=='FULL' else ('FER','info_BER','bit_NLL','edges')
            aggregate[label][arm]={metric:dict(mean=float(values(old,oracle,metric,snr,arm).mean()),
                total=float(values(old,oracle,metric,snr,arm).sum()),channels=32)
                for metric in metrics}
            if arm!='FULL':
                action=np.array([oracle[b,snr,arm]['operator_action']['operator_relative_squared'] for b in BLOCKS])
                aggregate[label][arm]['operator_relative_squared_mean']=float(action.mean())
        for arm in ARMS:
            paired[label][arm+'-FULL']={metric:descriptive_pair(
                values(old,oracle,metric,snr,'FULL'),values(old,oracle,metric,snr,arm),draws)
                for metric in ('FER','info_BER','bit_NLL')}
        paired[label]['O1_F-O1_S']={metric:descriptive_pair(
            values(old,oracle,metric,snr,'O1_S'),values(old,oracle,metric,snr,'O1_F'),draws)
            for metric in ('FER','info_BER','bit_NLL','edges')}
    return dict(schema='oracle-terminal-O1-analysis-v1',status='AUDITED_EXPLORATORY_DEVELOPMENT',
        scope='fixed old G1 FULL prefix/check prior/physical variance, complete true pilot cancellation; O1_S final observed-support projection, O1_F complete physical H and dense BP graph',
        interpretation='O1_S is not FER-optimal and O1_F is not a global achievable upper bound; CSI and graph density change jointly',
        independence='32 exposed development channel clusters; self-review weak; no independent CONF',
        no_registered_confirmation_test=True,no_new_full_receiver_calls=True,
        descriptive_interval=dict(unit='32 physical channel clusters retaining 7/8dB observations together',
            draws=BOOTSTRAP_DRAWS,seed=BOOTSTRAP_SEED,method='paired percentile 95%; exploratory analysis-time seed, no multiplicity/promotion gate'),
        reference=reference_binding,stage_bindings=stage_bindings,
        aggregate=aggregate,paired=paired,
        NLL_scope='old FULL offline_scores and O1 decoder_scores use the same coded-bit LLR margin formula, permitting paired NLL; all are retrospective',
        edge_scope='actual terminal BP graph edges for O1_S/O1_F; old FULL edges unavailable in bound summary, and dense O1_F graph/workload differs')


def markdown(result):
    lines=['# O1 固定终端信道干预：开发集描述性结果','',
        '32个已暴露 G1 物理信道、7/8 dB；原 FULL 外层前缀、最后check先验、BP温度和物理噪声固定。O1_S 用原终端支持的真值Frobenius投影，O1_F 用完整真值 H 与密集图；两臂均用真值 H 抵消导频。终端 BP/LDPC 回放各64点，0新增完整接收机。','',
        'O1 两臂工程和开发的四份独立 raw 审计均 PASS，原 FULL 64点和每个oracle的 reference_record_sha256 逐点绑定。','',
        '| SNR | 臂 | FER/32 | 信息BER | bit NLL | 终端边数均值 |','|---|---|---:|---:|---:|---:|']
    for snr,arms in result['aggregate'].items():
        for arm,metric in arms.items():
            nll=f'{metric["bit_NLL"]["mean"]:.6f}'
            edges=f'{metric["edges"]["mean"]:.1f}' if 'edges' in metric else '未由绑定摘要提供'
            lines.append(f'| {snr} dB | {arm} | {metric["FER"]["total"]:.0f}/32 | {metric["info_BER"]["mean"]:.6f} | {nll} | {edges} |')
    lines+=['','| SNR | 配对对比（后−前） | ΔFER及描述性95%区间 | Δ信息BER及描述性95%区间 |','|---|---|---:|---:|']
    for snr,pairs in result['paired'].items():
        for name,metric in pairs.items():
            fer=metric['FER'];ber=metric['info_BER']
            lines.append(f'| {snr} dB | {name} | {fer["mean_after_minus_before"]:+.6f} [{fer["percentile_95_CI"][0]:+.6f}, {fer["percentile_95_CI"][1]:+.6f}] | {ber["mean_after_minus_before"]:+.6f} [{ber["percentile_95_CI"][0]:+.6f}, {ber["percentile_95_CI"][1]:+.6f}] |')
    lines+=['','| SNR | 配对对比（后−前） | Δbit NLL及描述性95%区间 | Δ终端边数及描述性95%区间 |','|---|---|---:|---:|']
    for snr,pairs in result['paired'].items():
        for name,metric in pairs.items():
            nll=metric['bit_NLL'];edges=metric.get('edges')
            edge_text=(f'{edges["mean_after_minus_before"]:+.1f} [{edges["percentile_95_CI"][0]:+.1f}, {edges["percentile_95_CI"][1]:+.1f}]'
                       if edges else '旧FULL边数未提供')
            lines.append(f'| {snr} dB | {name} | {nll["mean_after_minus_before"]:+.6f} [{nll["percentile_95_CI"][0]:+.6f}, {nll["percentile_95_CI"][1]:+.6f}] | {edge_text} |')
    lines+=['','NLL使用同一coded-bit LLR margin公式。原FULL绑定摘要缺少终端图边数，不补造同口径边数基线。','',
        '95%区间按32物理信道成簇重抽样，7/8 dB 同步保留；20,000次、分析时固定seed 202609150601。当前冻结合同没有O1确认主检验或晋级门，区间仅为探索性描述，不作方法门槛或独立确认。','',
        'O1_S并非FER最优增益；O1_F仍面对旧先验/方差且图密度改变，不是全局可达性能上界。oracle改善或失败都不能单独归因于CE或否定其他全链方法。','']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--old-root',type=Path,default=DEFAULT_OLD)
    p.add_argument('--contract-root',type=Path,default=DEFAULT_CONTRACTS)
    p.add_argument('--result-json',type=Path,required=True)
    p.add_argument('--result-md',type=Path,required=True)
    args=p.parse_args()
    result=analyze(args.old_root,args.contract_root)
    for path,content in ((args.result_json,json.dumps(result,indent=2,ensure_ascii=False)+'\n'),
                         (args.result_md,markdown(result))):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as stream:stream.write(content)
    print(json.dumps(dict(status=result['status'],aggregate=result['aggregate'],
                          reference=result['reference']),ensure_ascii=False))


if __name__=='__main__':main()
