"""Read-only, reproducible summary of the saved Gamma crossfit diagnostics."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

PILOTS=('p0','pZ')
SNRS=(10,20)
STATES=(1,9)
INDICES=tuple(range(40))
TERMS={
    'fixed_mean':'delta_frozen_covariance_mean',
    'inverse_covariance':'delta_inverse_covariance_change',
    'logdet':'delta_logdet_change',
    'total':'delta_total_NLL',
}


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distribution(values):
    arr=np.asarray(values,dtype=np.float64)
    require(arr.ndim==1 and len(arr)>0 and np.isfinite(arr).all(),
            'finite nonempty distribution required')
    absolute=np.abs(arr)
    return dict(n=len(arr),absolute_mean=float(absolute.mean()),
        absolute_min=float(absolute.min()),absolute_p50=float(np.quantile(absolute,.50)),
        absolute_p90=float(np.quantile(absolute,.90)),
        absolute_p99=float(np.quantile(absolute,.99)),
        absolute_max=float(absolute.max()),signed_mean=float(arr.mean()))


def input_records(source):
    summary_path=source/'summary.json'
    summary=json.loads(summary_path.read_text())
    require(summary['status']=='COMPLETE' and summary['schema']=='gamma-crossfit-v1'
        and summary['saved_folds']==128
        and summary['candidate_pair_differences']==5120
        and summary['baseline_C_mu_factors']==128
        and summary['candidate_C_factors']==10240
        and summary['new_F']==summary['new_BP']==summary['new_LDPC']==0
        and summary['new_physical_channels']==0,
        'saved Gamma run scope/counts differ')
    paths={name:source/(name+'.json') for name in
        ('folds','evaluation','engineering','raw-audit')}
    paths['comparisons']=source/'comparisons.jsonl'
    for name,key in [('folds','folds_sha256'),('evaluation','evaluation_sha256'),
                     ('engineering','engineering_sha256'),('comparisons','comparisons_sha256')]:
        require(sha(paths[name])==summary[key],name+' does not match saved run hash')
    audit=json.loads(paths['raw-audit'].read_text())
    require(audit['status']=='PASS' and audit['schema']=='gamma-crossfit-v1-raw-audit'
        and audit['summary_sha256']==sha(summary_path)
        and audit['scope_binding']==summary['scope_binding']
        and audit['fold_array_recomputations']==128
        and audit['scalar_closure_recomputations']==5120
        and audit['candidate_covariance_recomputations']==0,
        'saved raw audit does not bind Gamma run')
    evidence=source.parent/'evidence'
    exits={name:json.loads((evidence/name).read_text()) for name in
        ('gamma-crossfit-v1-exit.json','gamma-crossfit-v1-audit-exit.json')}
    require(all(v['exit_code']==0 and v['timed_out'] is False for v in exits.values()),
        'saved remote run/audit exit did not succeed')
    return summary,audit,paths,exits,dict(
        summary_sha256=sha(summary_path),
        raw_audit_sha256=sha(paths['raw-audit']),
        comparisons_sha256=sha(paths['comparisons']),
        folds_sha256=sha(paths['folds']),
        evaluation_sha256=sha(paths['evaluation']),
        run_exit_sha256=sha(evidence/'gamma-crossfit-v1-exit.json'),
        audit_exit_sha256=sha(evidence/'gamma-crossfit-v1-audit-exit.json'))


def summarize(source):
    summary,audit,paths,exits,hashes=input_records(source)
    folds=json.loads(paths['folds'].read_text())
    require(len(folds)==128,'128 saved folds required')
    fold_keys=set();ranks=[];pseudo=[]
    for row in folds:
        key=(row['block'],row['pilot'],row['snr'],row['t'])
        require(key not in fold_keys and row['block'] in range(16)
            and row['pilot'] in PILOTS and row['snr'] in SNRS and row['t'] in STATES
            and row['channels']==[j for j in range(16) if j!=row['block']]
            and 0<=row['factor_rank']<=14,
            'saved fold grid/exclusion/rank differs')
        fold_keys.add(key);ranks.append(row['factor_rank'])
        ratio=row['pseudo_to_Gamma']
        require(ratio is None or np.isfinite(ratio),
                'saved pseudo-covariance ratio invalid')
        if ratio is not None:pseudo.append(ratio)
    expected_folds={(b,p,s,t) for b in range(16) for p in PILOTS
                    for s in SNRS for t in STATES}
    require(fold_keys==expected_folds,'saved fold grid incomplete')

    terms=defaultdict(list)
    grouped=defaultdict(lambda:defaultdict(list))
    changed=Counter();channel_changed=Counter();seen=set()
    with paths['comparisons'].open() as handle:
        for line in handle:
            row=json.loads(line)
            key=(row['block'],row['pilot'],row['snr'],row['t'],row['index'])
            require(key not in seen and key[:4] in expected_folds
                and row['index'] in INDICES,'saved comparison identity differs')
            seen.add(key)
            for label,field in TERMS.items():
                value=float(row[field]);require(np.isfinite(value),'nonfinite saved score term')
                terms[label].append(value)
                grouped[key[1:4]][label].append(value)
            closure=sum(row[TERMS[k]] for k in
                        ('fixed_mean','inverse_covariance','logdet'))
            require(abs(closure-row['delta_total_NLL'])<=1e-9*max(1.,abs(row['delta_total_NLL'])),
                    'saved three-term score does not close')
            if row['baseline_real_choice']!=row['corrected_real_choice']:
                changed[key[1:4]]+=1;channel_changed[row['block']]+=1
    expected={(b,p,s,t,i) for b in range(16) for p in PILOTS
              for s in SNRS for t in STATES for i in INDICES}
    require(seen==expected,'5120 comparison grid incomplete')

    evaluation=json.loads(paths['evaluation'].read_text())
    rows=evaluation['channel_rows'];require(len(rows)==16,'16 evaluation channels required')
    by_channel={row['block']:row for row in rows}
    require(set(by_channel)==set(range(16)),'evaluation physical channel identity differs')
    channel_rows=[];overall=Counter()
    projection=summary['physical_projection']
    require(set(projection)=={str(b) for b in range(16)},'16 projected physical H required')
    tails=[]
    for b in range(16):
        row=by_channel[b];tail=projection[str(b)]
        require(row['pairs']==320 and row['changed_choices']==channel_changed[b]
            and row['rescued']+row['new_errors']==row['changed_choices']
            and row['baseline_real_errors']-row['corrected_real_errors']
                ==row['rescued']-row['new_errors']
            and 0<=tail['tail_relative_squared']<=1+1e-8,
            'evaluation/channel tail arithmetic differs')
        for k in ('pairs','baseline_real_errors','corrected_real_errors',
                  'rescued','new_errors','changed_choices'):
            overall[k]+=row[k]
        tail_percent=100*tail['tail_relative_squared'];tails.append(tail_percent)
        channel_rows.append(dict(**row,physical_H_tail_percent=tail_percent,
            physical_H_tail_frobenius_squared=tail['tail_frobenius_squared']))
    require(overall['pairs']==5120 and overall['changed_choices']==
        overall['rescued']+overall['new_errors'],
        'overall real-choice evaluation arithmetic differs')
    groups=[]
    for p in PILOTS:
        for s in SNRS:
            for t in STATES:
                key=(p,s,t);num=len(grouped[key]['total'])
                require(num==640,'pilot/SNR/state comparison grid differs')
                groups.append(dict(pilot=p,snr=s,state=t,comparisons=num,
                    choice_changes=changed[key],
                    choice_change_percent=100*changed[key]/num,
                    absolute_term_distributions={label:distribution(grouped[key][label])
                        for label in TERMS}))
    result=dict(schema='gamma-crossfit-results-v1',status='SUMMARIZED',
        input_directory=str(source.resolve()),input_sha256=hashes,
        scope_binding=summary['scope_binding'],
        original_receiver_source_sha256=summary['original_receiver_source_sha256'],
        evidence=dict(remote_run_exit_code=0,
            remote_run_wall_seconds=exits['gamma-crossfit-v1-exit.json']['wall_seconds'],
            remote_audit_exit_code=0,
            remote_audit_wall_seconds=exits['gamma-crossfit-v1-audit-exit.json']['wall_seconds'],
            raw_audit_status=audit['status'],raw_audit_independence=audit['independence'],
            new_F=0,new_BP=0,new_LDPC=0,new_physical_channels=0,
            baseline_C_mu_factors=128,candidate_C_factors=10240,
            candidate_pair_differences=5120),
        overall_evaluation=dict(overall),
        absolute_term_distributions={label:distribution(terms[label]) for label in TERMS},
        fold_diagnostics=dict(n=128,rank_counts={str(k):v for k,v in sorted(Counter(ranks).items())},
            rank_min=min(ranks),rank_median=float(np.median(ranks)),rank_max=max(ranks),
            pseudo_to_Gamma_available=len(pseudo),
            pseudo_to_Gamma_absolute_distribution=distribution(pseudo) if pseudo else None),
        physical_H_tail_percent_distribution=distribution(tails),
        channel_rows=channel_rows,pilot_snr_state_rows=groups,
        interpretation_scope='same calibrated Gamma in frozen C(mu) baseline and candidate-varying C(+/-); offline real-component single-symbol comparisons only; no FER/CONF/independent likelihood')
    return result


def fmt(value):return f'{value:.3g}'


def render(result):
    overall=result['overall_evaluation'];evidence=result['evidence']
    lines=['# Γ crossfit：离线候选差结果', '',
        f"远端 run {fmt(evidence['remote_run_wall_seconds'])} 秒、audit {fmt(evidence['remote_audit_wall_seconds'])} 秒，exit 均为0；raw audit 为 **{evidence['raw_audit_status']}**。读取16个物理信道、64个既有F的首/末 CE 状态，产生128折、5120个固定实部候选差（10240个候选协方差计算，另有128个固定 `C(mu)`）。新增 F/BP/LDPC/物理信道均为0。审计是同会话保存数组的自审，不构成独立科学 CONF。",
        '',
        f"固定 `C(mu)` 选择错 {overall['baseline_real_errors']}/{overall['pairs']}，允许协方差随候选变化后错 {overall['corrected_real_errors']}/{overall['pairs']}；共改变 {overall['changed_choices']} 个实部选择，其中挽救 {overall['rescued']}、新增错误 {overall['new_errors']}。同一40个符号在导频、SNR和两个状态中重复比较，这些计数不是独立 BER，也不是 FER。",
        '',
        '固定协方差基准仍使用其他15信道校准的同一个 Γ、同一均值修正和 `C(mu)`；变化项只检验把 `C` 随两个候选更新的影响。它不与 Γ=0、原检测器或无信道不确定性的接收链比较。',
        '', '## 三项绝对差分', '',
        '| 项 | 中位数 | p90 | p99 | 最大 |',
        '|---|---:|---:|---:|---:|']
    labels={'fixed_mean':'固定 C(mu) 的均值','inverse_covariance':'逆协方差变化',
            'logdet':'logdet 变化','total':'总 NLL 差'}
    for name,dist in result['absolute_term_distributions'].items():
        lines.append(f"| {labels[name]} | {fmt(dist['absolute_p50'])} | {fmt(dist['absolute_p90'])} | {fmt(dist['absolute_p99'])} | {fmt(dist['absolute_max'])} |")
    fold=result['fold_diagnostics'];tail=result['physical_H_tail_percent_distribution']
    pseudo=fold['pseudo_to_Gamma_absolute_distribution']
    lines += ['',
        f"128折的低秩 Γ rank 分布：{fold['rank_counts']}；伪协方差/Γ Frobenius 比在 {fold['pseudo_to_Gamma_available']}/128 折可计算，中位数 {fmt(pseudo['absolute_p50']) if pseudo else '不可得'}、p90 {fmt(pseudo['absolute_p90']) if pseudo else '不可得'}。proper complex 评分忽略伪协方差，不能据此认定误差圆对称。",
        f"16个真实 H 的有限 D275 表示尾项 `||H-P_DH||²/||H||²`：中位数 {fmt(tail['absolute_p50'])}%、p90 {fmt(tail['absolute_p90'])}%、最大 {fmt(tail['absolute_max'])}%。未计算尾项对候选的响应或其他软数据误差。",
        '', '## 按物理信道', '',
        '| b | H尾项% | 固定C错 | 候选C错 | 改变 | 挽救 | 新增错 |',
        '|---:|---:|---:|---:|---:|---:|---:|']
    for row in result['channel_rows']:
        lines.append(f"| {row['block']} | {fmt(row['physical_H_tail_percent'])} | {row['baseline_real_errors']} | {row['corrected_real_errors']} | {row['changed_choices']} | {row['rescued']} | {row['new_errors']} |")
    lines += ['', '## 按导频、SNR和状态', '',
        '每行640个比较。三项列为绝对差的中位数（p90）；完整分布在配套 JSON。这里只能按这些条件统计选择改变，既有 `evaluation.json` 只给物理信道级错误计数，不能推断条件级挽救或新增错误。',
        '', '| pilot | dB | t | 改变 | 固定均值 | 逆协方差 | logdet |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in result['pilot_snr_state_rows']:
        d=row['absolute_term_distributions']
        cell=lambda name:f"{fmt(d[name]['absolute_p50'])} ({fmt(d[name]['absolute_p90'])})"
        lines.append(f"| {row['pilot']} | {row['snr']} | {row['state']} | {row['choice_changes']} | {cell('fixed_mean')} | {cell('inverse_covariance')} | {cell('logdet')} |")
    lines += ['',
        '这些分数是同一 `y` 上的 oracle 校准 proper complex plug-in 工作模型，候选先验按定义省略；跨折训练重叠、低秩 Γ 最多14维，且目标软数据/支撑来自同帧。结果只描述固定候选集合的离线选择变化，不能称精确后验、Γ整体有无效、检测器 FER 改善或 CONF 证据。',
        '',
        f"来源：`summary.json` SHA256 `{result['input_sha256']['summary_sha256']}`；`comparisons.jsonl` `{result['input_sha256']['comparisons_sha256']}`；`raw-audit.json` `{result['input_sha256']['raw_audit_sha256']}`。",
        '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    result=summarize(args.source)
    args.out_dir.mkdir(parents=True,exist_ok=True)
    (args.out_dir/'gamma-crossfit-results-v1.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.out_dir/'gamma-crossfit-results-v1.md').write_text(render(result))
    print(json.dumps(dict(status='SUMMARIZED',pairs=5120,
        overall_evaluation=result['overall_evaluation'],
        out_dir=str(args.out_dir.resolve()))))


if __name__=='__main__':main()
