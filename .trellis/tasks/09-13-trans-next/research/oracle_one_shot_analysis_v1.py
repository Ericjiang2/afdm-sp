"""Read-only O3 t1 true-data CE analysis from both audited saved stages.

All points are the 32 exposed G1 physical blocks; intervals are exploratory.
No receiver, BP, LDPC, or new CE solve is invoked here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
OLD=PROJECT/'afdm_sp_joint_unrolled/outputs_trans_next_20260913'
CONTRACTS=PROJECT/'afdm_sp_joint_unrolled/outputs_ce_state_20260915/contracts'
PRED=HERE/'ce-state-predictions-v1.json'
SNRS=(7,8);BLOCKS=tuple(range(32));ENGINEERING=(0,20)
ARM='O3_TRUE_DATA_CE_T1'
BOOTSTRAP_DRAWS=20000
BOOTSTRAP_SEED=202609150601  # reuse O1 descriptive convention; no frozen O3 test


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def require(ok,message):
    if not ok:raise ValueError(message)


def stages(old_root,contract_root):
    """Admit immutable engineering/development results before scoring."""
    pred=read(PRED)
    require(pred['oracle_stage']['O3'].startswith('preserve t0; only replace CE-local mu'),
            'frozen O3 oracle stage differs')
    pred_sha=sha(PRED)
    rows={};bindings={};source=None;runner=None;old_binding=None
    for label,tag,phase,blocks in (
        ('engineering','ce-o3-engineering-v1','oracle-engineering',set(ENGINEERING)),
        ('development','ce-o3-development-v1','oracle-development',set(BLOCKS)-set(ENGINEERING))):
        contract_path=Path(contract_root)/(tag+'.json')
        contract=read(contract_path)
        audit_path=Path(old_root)/'evidence'/(tag+'-raw-audit.json')
        audit=read(audit_path)
        summary_path=Path(old_root)/audit['summary_path']
        summary=read(summary_path)
        require(contract.get('schema')=='oracle-one-shot-v1' and
            contract.get('tag')==tag and contract.get('stage')==phase and
            contract.get('arm')==ARM and contract.get('predictions_sha256')==pred_sha and
            contract.get('snrs')==list(SNRS) and set(contract.get('blocks',[]))==blocks and
            contract.get('engineering_included_in_64') is True and
            (contract.get('device'),contract.get('threads'))==('cpu',1) and
            (contract.get('outer_iterations'),contract.get('terminal_bp_iterations'))==(10,20) and
            contract.get('checkpoints')==[1,4,7] and
            contract.get('terminal_check_prior')=='retain' and
            contract.get('terminal_variance_source')=='physical',
            'O3 frozen stage geometry/recipe differs: '+tag)
        expected=2*len(blocks)
        require(audit.get('status')=='PASS' and audit.get('stage')==phase and
            audit.get('summary_sha256')==sha(summary_path) and
            audit.get('contract_sha256')==sha(contract_path) and
            audit.get('source_sha256')==contract['source_sha256'] and
            audit.get('saved_F')==expected and audit.get('one_shot_F')==expected and
            audit.get('default_exact') is False and audit.get('new_F_calls')==0 and
            len(audit.get('rows',[]))==expected,
            'O3 independent raw stage audit missing/different: '+tag)
        require(summary.get('status')=='COMPLETE' and
            summary.get('calls')=={'F':expected} and
            summary.get('source_sha256')==contract['source_sha256'] and
            summary.get('script_sha256')==audit['script_sha256'] and
            summary.get('contract_sha256')==sha(contract_path) and
            len(summary.get('records',[]))==expected and
            summary.get('raw_checks',{}).get('rows')==audit['rows'],
            'O3 producer summary and separate audit disagree: '+tag)
        if source is None:source=contract['source_sha256'];runner=audit['script_sha256']
        require(source==contract['source_sha256'] and runner==audit['script_sha256'],
            'O3 stages use different source/runner')
        binding=(contract['old_inputs']['runs/g1-strong-development-recovery-v1/development/summary.json'],
                 contract['old_inputs']['evidence/g1-strong-development-recovery-v1-raw-audit.json'])
        if old_binding is None:old_binding=binding
        require(old_binding==binding,'O3 old FULL endpoint binding differs by stage')
        if label=='development':
            engineering_audit=Path(old_root)/'evidence/ce-o3-engineering-v1-raw-audit.json'
            require(contract['engineering_admission_sha256']==sha(engineering_audit),
                    'O3 development not admitted by audited engineering')
        require(contract['default_admission_sha256']==sha(
            Path(old_root)/contract['default_admission']),
            'O3 default on/off admission differs')
        entries={(e['block'],e['snr']):e for e in summary['records']}
        require(len(entries)==expected,'O3 producer entry identity duplicated')
        for row in audit['rows']:
            key=(row['block'],row['snr'])
            require(row['block'] in blocks and row['snr'] in SNRS and key not in rows and
                row['arm']==ARM and entries[key]['scores']==row['scores'] and
                entries[key]['arm']==ARM and entries[key]['split']==row['split'],
                'O3 saved block/SNR/score identity differs: '+str(key))
            verify_release(row)
            rows[key]=row
        bindings[label]=dict(contract_sha256=sha(contract_path),
            summary_sha256=sha(summary_path),audit_sha256=sha(audit_path),
            source_sha256=source,runner_sha256=runner,points=expected,
            blocks=sorted(blocks))
    require(set(rows)=={(b,s) for b in BLOCKS for s in SNRS},
            'O3 full 32-block x 2-SNR audited endpoint inventory incomplete')
    return rows,bindings,old_binding


def verify_release(row):
    c=row['controller'];tr=row['ce_trajectory'];obs=row['t1_observer'];score=row['scores']
    require(c['status']=='consumed' and c['outer_iter']==1 and
        c['location']=='after_code_feedback_ce_before_x_total' and
        c['truth_access']=='true_data_ce_only' and c['legal_receiver_input'] is False and
        c['true_variance']==0. and c['variance_used_by_CE'] is False and
        c['consumed_mean_sha256']==tr[0]['mu_sha256'] and
        c['A_sha256']==tr[0]['A_sha256'] and
        c['proposal_variance_sha256']==obs['finite_variance']['sha256'] and
        tr[0]['outer_iter']==1 and tr[0]['moment_source']=='true_data_ce' and
        tr[0]['oracle_mean'] is True and
        len(tr)==9 and [x['outer_iter'] for x in tr]==list(range(1,10)) and
        all(x['moment_source']=='code_feedback.ce' and x['oracle_mean'] is False
            for x in tr[1:]),
        'O3 truth release location/CE trajectory differs')
    calls=row['calls']['resources']
    require((calls['CE_solves'],calls['outer_BP_calls'],calls['terminal_BP_calls'],
             calls['LDPC_calls'])==(9,10,1,4) and
        score['coded_bits_denominator']==1024 and score['FER'] in (0,1) and
        score['FER']==int(score['coded_bit_errors']>0) and
        0<=score['coded_bit_errors']<=1024 and
        np.isfinite(score['bit_NLL']) and score['bit_NLL']>=0,
        'O3 terminal call/score scope differs')


def old_full(old_root,binding,o3):
    summary_path=Path(old_root)/'runs/g1-strong-development-recovery-v1/development/summary.json'
    audit_path=Path(old_root)/'evidence/g1-strong-development-recovery-v1-raw-audit.json'
    require((sha(summary_path),sha(audit_path))==binding,
            'O3 old G1 FULL source differs from frozen contract')
    summary,audit=read(summary_path),read(audit_path)
    require(summary.get('status')=='COMPLETE' and len(summary.get('records',[]))==288 and
            audit.get('status')=='PASS' and audit.get('summary_sha256')==sha(summary_path),
            'old G1 FULL summary/independent raw audit incomplete')
    full={}
    for e in summary['records']:
        if e.get('kind')!='F' or e.get('arm')!='G1_FULL':continue
        key=(e['block'],e['snr']);score=e['scores']
        require(key not in full and key[0] in BLOCKS and key[1] in SNRS and
            score['coded_bits_denominator']==1024 and score['FER'] in (0,1) and
            score['FER']==int(score['coded_bit_errors']>0) and
            np.isfinite(score['bit_NLL']) and score['bit_NLL']>=0,
            'old G1 FULL endpoint invalid/duplicate')
        full[key]=e
    require(set(full)==set(o3),'old G1 FULL 64 endpoint inventory differs')
    audited={(r['block'],r['snr']):r['scores'] for r in audit['rows'] if r['arm']=='G1_FULL'}
    require(set(audited)==set(full) and all(audited[k]==full[k]['scores'] for k in full),
            'old FULL scores differ from independent raw audit')
    for key,e in full.items():
        require(o3[key]['reference_record_sha256']==e['sha256'] and
                o3[key]['original_scores']==e['scores'],
                'O3 point not paired to its frozen old FULL score/source')
    return full,dict(summary_sha256=binding[0],raw_audit_sha256=binding[1],
        score_scope='FER, information-bit BER and coded-bit LLR NLL from original FULL')


def vector(index,metric,snr,blocks):
    out=[]
    for b in blocks:
        score=index[b,snr]['scores']
        out.append(score['FER'] if metric=='FER' else
                   score['coded_bit_errors']/1024 if metric=='info_BER' else
                   score['bit_NLL'])
    return np.asarray(out,float)


def pair(a,b,draws):
    difference=b-a
    sampled=difference[draws].mean(axis=1)
    return dict(mean_after_minus_before=float(difference.mean()),
        percentile_95_CI=np.quantile(sampled,[.025,.975],method='linear').tolist(),
        channel_differences=difference.tolist())


def analyze(old_root,contract_root):
    oracle,bindings,old_binding=stages(old_root,contract_root)
    original,reference=old_full(old_root,old_binding,oracle)
    draws=np.random.default_rng(BOOTSTRAP_SEED).integers(
        0,len(BLOCKS),(BOOTSTRAP_DRAWS,len(BLOCKS)))
    aggregate={};paired={};engineering={}
    for snr in SNRS:
        label=str(snr);aggregate[label]={};paired[label]={};engineering[label]={}
        for arm,index in (('FULL',original),('O3',oracle)):
            aggregate[label][arm]={metric:dict(mean=float(vector(index,metric,snr,BLOCKS).mean()),
                total=float(vector(index,metric,snr,BLOCKS).sum()),channels=32)
                for metric in ('FER','info_BER','bit_NLL')}
            engineering[label][arm]={metric:dict(mean=float(vector(index,metric,snr,ENGINEERING).mean()),
                total=float(vector(index,metric,snr,ENGINEERING).sum()),channels=2)
                for metric in ('FER','info_BER','bit_NLL')}
        paired[label]={metric:pair(vector(original,metric,snr,BLOCKS),
            vector(oracle,metric,snr,BLOCKS),draws)
            for metric in ('FER','info_BER','bit_NLL')}
        engineering[label]['paired']={metric:dict(mean_after_minus_before=float(
            (vector(oracle,metric,snr,ENGINEERING)-vector(original,metric,snr,ENGINEERING)).mean()),
            channel_differences=(vector(oracle,metric,snr,ENGINEERING)-
                vector(original,metric,snr,ENGINEERING)).tolist())
            for metric in ('FER','info_BER','bit_NLL')}
    release=dict(points=64,t1_true_data_CE=64,normal_feedback_t2_through_t9=64*8,
        t0_preservation='runner raw audit compares original initial estimator, first graph and support trace',
        true_variance_used_by_CE=False,legal_receiver_input=False,
        CE_solves=sum(r['calls']['resources']['CE_solves'] for r in oracle.values()),
        outer_BP_calls=sum(r['calls']['resources']['outer_BP_calls'] for r in oracle.values()),
        terminal_BP_calls=sum(r['calls']['resources']['terminal_BP_calls'] for r in oracle.values()),
        LDPC_calls=sum(r['calls']['resources']['LDPC_calls'] for r in oracle.values()))
    return dict(schema='oracle-one-shot-O3-analysis-v1',status='AUDITED_EXPLORATORY_DEVELOPMENT',
        scope='true-data CE-local mean once at t1; t0 and g_previous retained; t1 legal BP/checkpoint and t2+ ordinary feedback',
        independence='32 exposed development physical blocks, 7/8dB; same-session source/raw review weak; no independent CONF',
        exploratory_interval=dict(unit='32 paired physical channel clusters retaining both SNRs',
            draws=BOOTSTRAP_DRAWS,seed=BOOTSTRAP_SEED,
            method='paired percentile descriptive 95%, no O3 registered confirmation/promotional test'),
        reference=reference,stage_bindings=bindings,release=release,
        aggregate=aggregate,paired=paired,engineering=engineering,
        interpretation='truth-bearing offline intervention, not deployment input, global bound or pure CE causal estimate')


def markdown(result):
    lines=['# O3 一次真数据 CE：开发集描述性结果','',
        '32个已暴露 G1 物理信道、7/8 dB；工程信道0、20包含在32个信道中。O3仅在t=1用真数据替换CE局部均值，保留原g_previous；t=0原接收路径和t≥2普通反馈继续运行。此真值接口不是合法部署输入。','',
        '两阶段64条F和独立raw审计均通过。以下FULL为冻结原G1 FULL端点，逐点以原始记录SHA及分数配对。','',
        '| SNR | 臂 | FER/32 | 信息BER | bit NLL |','|---|---|---:|---:|---:|']
    for snr,arms in result['aggregate'].items():
        for arm,x in arms.items():
            lines.append(f'| {snr} dB | {arm} | {x["FER"]["total"]:.0f}/32 | {x["info_BER"]["mean"]:.6f} | {x["bit_NLL"]["mean"]:.6f} |')
    lines+=['','| SNR | O3−FULL ΔFER及描述性95%区间 | Δ信息BER及描述性95%区间 | Δbit NLL及描述性95%区间 |',
            '|---|---:|---:|---:|']
    for snr,pairs in result['paired'].items():
        cells=[]
        for metric in ('FER','info_BER','bit_NLL'):
            v=pairs[metric];ci=v['percentile_95_CI']
            cells.append(f'{v["mean_after_minus_before"]:+.6f} [{ci[0]:+.6f}, {ci[1]:+.6f}]')
        lines.append(f'| {snr} dB | '+' | '.join(cells)+' |')
    lines+=['','工程4点单列，计入上面的64F与开发32信道；2信道每SNR的均值只供准入描述，不给区间。','',
            '| SNR | FULL FER/2 | O3 FER/2 | O3−FULL Δ信息BER | O3−FULL Δbit NLL |',
            '|---|---:|---:|---:|---:|']
    for snr,e in result['engineering'].items():
        lines.append(f'| {snr} dB | {e["FULL"]["FER"]["total"]:.0f}/2 | {e["O3"]["FER"]["total"]:.0f}/2 | {e["paired"]["info_BER"]["mean_after_minus_before"]:+.6f} | {e["paired"]["bit_NLL"]["mean_after_minus_before"]:+.6f} |')
    r=result['release']
    lines+=['',f'释放行为：{r["t1_true_data_CE"]}次t=1真数据CE，后续{r["normal_feedback_t2_through_t9"]}个普通反馈CE状态；累计CE解{r["CE_solves"]}、外层BP调用{r["outer_BP_calls"]}、终端BP调用{r["terminal_BP_calls"]}、LDPC调用{r["LDPC_calls"]}。审计核对t=1真值均值、零方差、保留previous和重建A；t≥2无oracle均值。','',
        '描述性95%区间对32物理信道成簇重抽样，7/8 dB同步保留；20,000次、seed 202609150601。冻结PRED未注册O3确认主检验或晋级门，此处不作CONF/FER收益推广。','',
        '真值CE能改变后续检测与码反馈，因而整体终端差异不是纯粹孤立CE误差的因果量；O3也不是全局信息论性能上界。','']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--old-root',type=Path,default=OLD)
    p.add_argument('--contract-root',type=Path,default=CONTRACTS)
    p.add_argument('--result-json',type=Path,required=True)
    p.add_argument('--result-md',type=Path,required=True)
    a=p.parse_args()
    result=analyze(a.old_root,a.contract_root)
    for path,content in ((a.result_json,json.dumps(result,indent=2,ensure_ascii=False)+'\n'),
                         (a.result_md,markdown(result))):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as stream:stream.write(content)
    print(json.dumps(dict(status=result['status'],aggregate=result['aggregate'],
        release=result['release']),ensure_ascii=False))


if __name__=='__main__':main()
