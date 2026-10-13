"""Frozen 16-channel paired N256/N1024 UWA analysis after independent raw audits."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
REGISTRATION=HERE/'nsize-uwa-1024-contract-v1.json'
OLD_RESULTS=HERE/'physical-transfer-v1-results.json'
OLD_RISK=HERE.parents[3]/'afdm_sp_joint_unrolled/outputs_ce_state_20260915/pred-old-risk-v1/summary.json'


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text())


def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _old_rows(registration,old_results,old_risk):
    _require(old_results['status']=='LIMITED_UWA_TRANSFER_COMPLETE',
        'old physical-transfer result status differs')
    old={}
    for row in old_results['rows']:
        if row.get('domain')!='uwa' or row.get('arm')!='OMP_BASE':
            continue
        key=(row['block'],row['pilot'],row['snr'])
        _require(key not in old,'duplicate old physical endpoint')
        score=row['scores']
        _require(score['bit_count']==2*registration['N_old'],
                 'old N256 denominator differs')
        old[key]=row
    risk={}
    for row in old_risk['rows']:
        if row.get('arm')!='OMP_BASE':
            continue
        key=(row['block'],row['pilot'],row['snr'])
        _require(key not in risk,'duplicate old risk endpoint')
        risk[key]=row
    expected={(b,p,s) for b in registration['existing_blocks']
              for p in registration['pilots'] for s in registration['snrs']}
    _require(set(old)==expected and set(risk)==expected,
        'old N256 physical/risk endpoint inventory is incomplete')
    _require(old_risk['scope'].startswith('retrospective N256 UWA'),
        'old risk evidence scope differs')
    for key,row in old.items():
        scores=row['scores']; companion=risk[key]
        _require(np.isclose(scores['bit_errors']/scores['bit_count'],companion['BER'],atol=0,rtol=0)
            and np.isclose(scores['channel_nmse'],companion['H_NMSE'],atol=1e-12,rtol=0)
            and scores['active_atoms']==companion['support_size'],
            'old physical result and retrospective risk mismatch')
    return old,risk


def _new_rows(registration,stages):
    rows={}
    expected_stage={'engineering':set(registration['engineering_blocks']),
        'development':set(registration['existing_blocks'])-set(registration['engineering_blocks'])}
    for stage,data in stages.items():
        _require(data['summary']['status']=='COMPLETE' and
                 data['summary']['calls']=={'A':len(expected_stage[stage]),
                                           'F':4*len(expected_stage[stage])},
            'new producer stage incomplete or reservation count differs')
        stage_rows=data['audit']['rows']
        _require(len(stage_rows)==4*len(expected_stage[stage]) and
                 data['audit']['new_F']==len(stage_rows) and
                 data['audit']['same_channel_operator_constructions']==len(expected_stage[stage]),
            'new audited F/operator count differs')
        for row in stage_rows:
            key=(row['block'],row['pilot'],row['snr'])
            _require(row['block'] in expected_stage[stage] and key not in rows,
                'new endpoint duplicated or assigned to wrong stage')
            scores=row['scores']
            _require(scores['bit_count']==2*registration['N_new'] and
                     scores['bit_errors'] in range(scores['bit_count']+1) and
                     row['CE_states']==9,
                'new bit denominator or actual CE state count differs')
            rows[key]=row
    expected={(b,p,s) for b in registration['existing_blocks']
              for p in registration['pilots'] for s in registration['snrs']}
    _require(set(rows)==expected,'new N1024 endpoint inventory is incomplete')
    return rows


def paired_primary(old,new,registration):
    blocks=registration['existing_blocks'];pilots=registration['pilots'];snrs=registration['snrs']
    _require(len(blocks)==16 and len(pilots)==2 and len(snrs)==2,
        'frozen clustered primary design differs')
    expected={(b,p,s) for b in blocks for p in pilots for s in snrs}
    _require(set(old)==expected and set(new)==expected,
        'paired primary endpoint inventory differs')
    per_block=np.empty((len(blocks),len(pilots)),float)
    for i,block in enumerate(blocks):
        for j,pilot in enumerate(pilots):
            differences=[]
            for snr in snrs:
                key=(block,pilot,snr)
                old_ber=old[key]['scores']['bit_errors']/old[key]['scores']['bit_count']
                new_ber=new[key]['scores']['bit_errors']/new[key]['scores']['bit_count']
                differences.append(new_ber-old_ber)
            per_block[i,j]=np.mean(differences)
    draws=registration['bootstrap_draws'];seed=registration['bootstrap_seed']
    _require(draws==20000 and seed==202609150502 and registration['primary_contrasts']==2,
        'bootstrap registration differs')
    indices=np.random.default_rng(seed).integers(0,len(blocks),(draws,len(blocks)))
    sampled=per_block[indices].mean(axis=1)
    tails=.05/(2*len(pilots))
    result={}
    for j,pilot in enumerate(pilots):
        lo,hi=np.quantile(sampled[:,j],[tails,1-tails],method='linear')
        point=float(per_block[:,j].mean())
        result[pilot]=dict(point_difference_N1024_minus_N256=point,
            simultaneous_95_percentile_Bonferroni_CI=[float(lo),float(hi)],
            channel_differences=per_block[:,j].tolist(),
            interval_includes_zero=bool(lo<=0<=hi))
    return result


def secondary(old,new,registration):
    out={}
    for pilot in registration['pilots']:
        for snr in registration['snrs']:
            keys=[(b,pilot,snr) for b in registration['existing_blocks']]
            old_rows=[old[k] for k in keys];new_rows=[new[k] for k in keys]
            old_ber=np.array([r['scores']['bit_errors']/r['scores']['bit_count'] for r in old_rows])
            new_ber=np.array([r['scores']['bit_errors']/r['scores']['bit_count'] for r in new_rows])
            old_h=np.array([r['scores']['channel_nmse'] for r in old_rows])
            new_h=np.array([r['scores']['channel_nmse'] for r in new_rows])
            old_hp=np.array([r['scores']['pilot_nmse'] for r in old_rows])
            new_hp=np.array([r['scores']['pilot_nmse'] for r in new_rows])
            old_support=np.array([r['scores']['active_atoms'] for r in old_rows])
            new_support=np.array([r['scores']['active_atoms'] for r in new_rows])
            old_bit_cpu=np.array([1000*r['CPU_seconds']/r['scores']['bit_count'] for r in old_rows])
            new_bit_cpu=np.array([r['receiver_cpu_ms_bit'] for r in new_rows])
            out[f'{pilot}/{snr}dB']=dict(channels=16,
                BER_old=float(old_ber.mean()),BER_new=float(new_ber.mean()),
                BER_paired_difference=float((new_ber-old_ber).mean()),
                BER_paired_difference_range=[float((new_ber-old_ber).min()),
                                             float((new_ber-old_ber).max())],
                H_NMSE_old=float(old_h.mean()),H_NMSE_new=float(new_h.mean()),
                Hp_NMSE_old=float(old_hp.mean()),Hp_NMSE_new=float(new_hp.mean()),
                active_atoms_old=float(old_support.mean()),active_atoms_new=float(new_support.mean()),
                receiver_CPU_ms_bit_old=float(old_bit_cpu.mean()),
                receiver_CPU_ms_bit_new=float(new_bit_cpu.mean()),
                new_initial_Gram_full_rank_all=all(r['initial_feedback_Gram']['rank']==r['initial_feedback_Gram']['active_columns'] for r in new_rows),
                new_final_Gram_full_rank_all=all(r['final_feedback_Gram']['rank']==r['final_feedback_Gram']['active_columns'] for r in new_rows),
                new_initial_Gram_rank_min=int(min(r['initial_feedback_Gram']['rank'] for r in new_rows)),
                new_final_Gram_rank_min=int(min(r['final_feedback_Gram']['rank'] for r in new_rows)),
                new_initial_Gram_condition_median=float(np.median([r['initial_feedback_Gram']['Gram_condition'] for r in new_rows])),
                new_final_Gram_condition_median=float(np.median([r['final_feedback_Gram']['Gram_condition'] for r in new_rows])),
                new_terminal_residual_sq_mean=float(np.mean([r['terminal_residual']['residual_sq'] for r in new_rows])))
    return out


def _validated_stage(summary_path,audit_path,registration,stage):
    summary=_json(summary_path);audit=_json(audit_path)
    _require(audit.get('status')=='PASS' and audit.get('summary_sha256')==digest(summary_path),
        'independent new raw audit missing/failed or summary hash differs')
    _require(audit.get('registration_sha256')==digest(REGISTRATION),
        'new audit registration hash differs')
    _require(summary.get('registration_sha256')==digest(REGISTRATION),
        'new summary registration hash differs')
    for name in ('contract_sha256','runner_sha256','source_sha256','checkpoint_sha256'):
        _require(audit.get(name)==summary.get(name),
            'new stage summary/audit source binding differs: '+name)
    _require(summary.get('stage')==stage and
        audit.get('new_F')==(8 if stage=='engineering' else 56),
        'stage identity or F count differs')
    _require(audit['rows']==summary['raw_checks']['rows'] and
        audit['input_checks']==summary['raw_checks']['input_checks'] and
        audit['arrays_audited']==summary['raw_checks']['arrays_audited'],
        'independent raw audit differs from producer recorded checks')
    return dict(summary=summary,audit=audit,
                summary_sha256=digest(summary_path),audit_sha256=digest(audit_path))


def analyze(paths):
    registration=_json(REGISTRATION)
    old_results=_json(OLD_RESULTS);old_risk=_json(OLD_RISK)
    _require(registration['schema']=='nsize-uwa-1024-v1' and
        registration['N_old']==256 and registration['N_new']==1024 and
        registration['coding'] is False,
        'frozen registered N/coding scope differs')
    stages={stage:_validated_stage(paths[stage]['summary'],paths[stage]['audit'],registration,stage)
            for stage in ('engineering','development')}
    _require(stages['engineering']['summary']['runner_sha256']==
             stages['development']['summary']['runner_sha256'] and
             stages['engineering']['summary']['source_sha256']==
             stages['development']['summary']['source_sha256'] and
             stages['engineering']['summary']['checkpoint_sha256']==
             stages['development']['summary']['checkpoint_sha256'],
        'engineering/development source or checkpoint differs')
    old,risk=_old_rows(registration,old_results,old_risk)
    new=_new_rows(registration,stages)
    primary=paired_primary(old,new,registration)
    result=dict(schema='nsize-uwa-1024-analysis-v1',status='AUDITED_DEVELOPMENT_ANALYSIS',
        scope='same physical UWA channels; N, c1, normalized Doppler and W dictionary change together; uncoded OMP_BASE',
        old_evidence_scope='N256 terminal endpoints only; no old per-round CE/Gram reconstruction',
        comparison_scope='paired configuration contrast, not a pure-N causal effect or independent confirmation',
        primary=dict(unit='16 independently generated physical channels; two SNR observations stay within each channel',
            statistic='within-channel mean of 10/20 dB BER difference, then equal channel mean',
            bootstrap_draws=registration['bootstrap_draws'],seed=registration['bootstrap_seed'],
            method='percentile; two Bonferroni simultaneous 95% intervals',contrasts=primary),
        secondary=secondary(old,new,registration),
        resources=dict(new_F=64,new_operator_constructions=16,
            engineering_full_stage_CPU_ms_bit=stages['engineering']['audit']['full_stage_CPU_ms_bit'],
            development_full_stage_CPU_ms_bit=stages['development']['audit']['full_stage_CPU_ms_bit'],
            full_stage_CPU_scope=stages['development']['summary']['CPU_scope'],
            old_receiver_source_sha256=old_results['evidence']['development']['recipe']['source_sha256'],
            new_receiver_source_sha256=stages['development']['summary']['source_sha256'],
            cost_comparison_limit='per-call CPU uses the same process-time unit, but source versions, N and dictionaries differ; it is descriptive, not a pure-N cost effect. New full-stage CPU includes old raw readback and archival I/O and has no matching old full-stage quote'),
        hashes=dict(registration=digest(REGISTRATION),old_results=digest(OLD_RESULTS),
            old_risk=digest(OLD_RISK),new_stages={stage:{k:v for k,v in stages[stage].items()
                if k.endswith('_sha256')} for stage in stages}),
        independence='weak scientific self-review; audits verify saved arrays, not new independent confirmation')
    return result


def markdown(result):
    lines=['# 同水声物理信道 N256/N1024 配对开发结果','',
        '范围：16个相同物理水声信道，未编码 OMP_BASE；N1024 使用 W5/q11/D275，N256 使用 W2/q5/D125。块长、c1、归一化多普勒和字典共同变化，因此这是配置对照，不能称纯 N 因果效应。','',
        '两阶段独立 raw 审计均 PASS 后才生成此报告；旧 N256 只有终端证据，未补造逐轮 CE 状态。','',
        '## 冻结主对比','',
        '| 导频 | N1024−N256 平均 BER | 同时95%区间 | 方向 |','|---|---:|---:|---|']
    for pilot,item in result['primary']['contrasts'].items():
        lo,hi=item['simultaneous_95_percentile_Bonferroni_CI']
        direction='不确定（跨零）' if item['interval_includes_zero'] else ('N1024较低' if hi<0 else 'N1024较高')
        lines.append(f'| {pilot} | {item["point_difference_N1024_minus_N256"]:+.6f} | [{lo:+.6f}, {hi:+.6f}] | {direction} |')
    lines+=['','区间以16个物理信道为重抽样单位，10/20 dB 观测在每次抽样中一起保留；20000次固定 bootstrap，seed 202609150502，两个导频使用 Bonferroni 同时95%区间。','',
        '## 分 SNR 次分析','',
        '| 导频/SNR | BER N256 | BER N1024 | 配对差 | H NMSE N256→N1024 | Hp NMSE N256→N1024 | 活动原子 N256→N1024 |','|---|---:|---:|---:|---:|---:|---:|']
    for key,item in result['secondary'].items():
        lines.append(f'| {key} | {item["BER_old"]:.6f} | {item["BER_new"]:.6f} | {item["BER_paired_difference"]:+.6f} | {item["H_NMSE_old"]:.6f}→{item["H_NMSE_new"]:.6f} | {item["Hp_NMSE_old"]:.6f}→{item["Hp_NMSE_new"]:.6f} | {item["active_atoms_old"]:.2f}→{item["active_atoms_new"]:.2f} |')
    lines+=['','N1024保存了实际9轮 CE observer 的 A/μ/previous/解及终端 H、soft 状态；Gram 与终端残差仅是 N1024 次分析，不能与缺失逐轮状态的旧 N256 做对称风险比较。','',
        '| 导频/SNR | N1024初/末Gram均满秩 | 初/末Gram条件数中位数 | N1024终端残差平方均值 | receiver CPU ms/bit N256→N1024 |','|---|---|---:|---:|---:|']
    for key,item in result['secondary'].items():
        full='是/是' if item['new_initial_Gram_full_rank_all'] and item['new_final_Gram_full_rank_all'] else f'{"是" if item["new_initial_Gram_full_rank_all"] else "否"}/{"是" if item["new_final_Gram_full_rank_all"] else "否"}'
        lines.append(f'| {key} | {full} | {item["new_initial_Gram_condition_median"]:.3f}/{item["new_final_Gram_condition_median"]:.3f} | {item["new_terminal_residual_sq_mean"]:.3f} | {item["receiver_CPU_ms_bit_old"]:.6f}→{item["receiver_CPU_ms_bit_new"]:.6f} |')
    lines+=['',
        '## 成本与证据范围','',
        f'新增完整接收机调用64F，同信道算子构建16次。N1024工程/开发阶段全CPU分别为 {result["resources"]["engineering_full_stage_CPU_ms_bit"]:.6f}/{result["resources"]["development_full_stage_CPU_ms_bit"]:.6f} ms/bit，含原始输入回读、模型设置、算子、接收机与归档I/O；旧N256没有同口径全阶段报价。',
        '逐调用 receiver CPU ms/bit 使用同一 process-time 单位，但两阶段源码版本、N和字典不同；它是描述性成本，不能解释为纯N效应，也不能替代正式 COST 或部署时延。结果属于开发且科学自审独立性 weak，不作为方法独立确认或 Transactions 闭合证据。','']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser()
    for stage in ('engineering','development'):
        p.add_argument('--'+stage+'-summary',type=Path,required=True)
        p.add_argument('--'+stage+'-audit',type=Path,required=True)
    p.add_argument('--result-json',type=Path,required=True)
    p.add_argument('--result-md',type=Path,required=True)
    args=p.parse_args()
    paths={stage:dict(summary=getattr(args,stage+'_summary'),
                      audit=getattr(args,stage+'_audit'))
           for stage in ('engineering','development')}
    result=analyze(paths)
    for target,content in ((args.result_json,json.dumps(result,indent=2,ensure_ascii=False)+'\n'),
                           (args.result_md,markdown(result))):
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:stream.write(content)
    print(json.dumps(dict(status=result['status'],contrasts=result['primary']['contrasts'],
                          hashes=result['hashes']),ensure_ascii=False))


if __name__=='__main__':main()
