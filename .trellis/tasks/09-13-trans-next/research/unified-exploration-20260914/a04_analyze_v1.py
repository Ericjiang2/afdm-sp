"""Registered paired BER family and complete-frame development cost gates."""
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from ab_statistics_v1 import cluster_intervals


def candidate_decision(contrasts, cost_ratio, minimum_errors):
    """Apply frozen effect/noninferiority/equivalence gates without selection."""
    if len(contrasts) != 16 or not np.isfinite(cost_ratio) or cost_ratio <= 0:
        raise ValueError('four references by four endpoints and finite positive cost required')
    main = [r for r in contrasts if (r['pilot'], r['snr']) == ('pZ', 20)]
    other = [r for r in contrasts if (r['pilot'], r['snr']) != ('pZ', 20)]
    usable = all(r['inference_usable'] for r in contrasts)
    effect = usable and all(r['mean'] <= -.01 and r['simultaneous_95'][1] < 0 for r in main)
    noninferior = usable and all(r['simultaneous_95'][1] < .01 for r in other)
    equivalent = usable and all(r['simultaneous_95'][0] > -.005 and r['simultaneous_95'][1] < .005 for r in contrasts)
    enough = minimum_errors >= 100
    benefit = effect and noninferior and cost_ratio <= 1.25
    reduction = equivalent and enough and cost_ratio <= .75
    supported = benefit or reduction
    cost_excludes_both = cost_ratio > 1.25
    meaningful_effect_excluded = any(r['inference_usable'] and r['simultaneous_95'][0] > -.01 for r in main)
    other_safety_excluded = any(r['inference_usable'] and r['simultaneous_95'][0] >= .01 for r in other)
    equivalence_excluded = any(r['inference_usable'] and
        (r['simultaneous_95'][0] > .005 or r['simultaneous_95'][1] < -.005) for r in contrasts)
    benefit_excluded = cost_excludes_both or meaningful_effect_excluded or other_safety_excluded
    reduction_excluded = cost_ratio > .75 or equivalence_excluded
    status = ('QUALIFIED' if supported else 'NOT_SUPPORTED' if benefit_excluded and reduction_excluded
              else 'STATISTICALLY_UNCERTAIN')
    return dict(status=status, usable=supported, benefit_ber_gate=bool(effect and noninferior),
                primary_effect_gate=bool(effect), other_endpoint_gate=bool(noninferior),
                benefit_cost_gate=bool(cost_ratio <= 1.25), equivalence_gate=bool(equivalent),
                minimum_errors=minimum_errors, sufficient_errors=bool(enough),
                reduction_cost_gate=bool(cost_ratio <= .75), cost_ratio_to_fastest_control=cost_ratio,
                measured_cost_excludes_both_routes=bool(cost_excludes_both),
                meaningful_primary_effect_excluded=bool(meaningful_effect_excluded),
                other_endpoint_safety_excluded=bool(other_safety_excluded),
                equivalence_excluded=bool(equivalence_excluded))


def read_bound_json(path):
    data = path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes())
    return json.loads(data), hashlib.sha256(data).hexdigest()


def main():
    here = Path(__file__).resolve().parent
    root = Path('afdm_sp_joint_unrolled/outputs_unified_exploration_20260914')
    contract = json.loads((here/'ab-contract-v1.json').read_text())
    controls = tuple(contract['references'])
    bases = tuple(f'{family}_q{q}' for family in contract['bases'] for q in contract['q'])
    arms = controls+bases
    tags = [f'a04-development-{start:02d}-{start+15:02d}-v1' for start in (0, 16, 32, 48)]
    rows, inputs, receipts = [], {}, {}
    for tag in tags:
        metrics_path = root/'evidence'/(tag+'-metrics.json')
        metrics, digest = read_bound_json(metrics_path)
        audit = json.loads((root/'evidence'/(tag+'-audit.json')).read_text())
        assert audit['status'] == 'PASS' and audit['metrics_sha256'] == digest
        assert audit['summary_sha256'] == metrics['summary_sha256']
        for suffix in ('', '-audit'):
            receipt = json.loads((root/'evidence'/(tag+suffix+'-exit.json')).read_text())
            assert receipt['exit_code'] == 0 and not receipt['timed_out']
            receipts[tag+suffix] = receipt
        rows += metrics['rows']
        inputs[tag] = dict(metrics_sha256=digest, summary_sha256=audit['summary_sha256'],
                          audit_sha256=hashlib.sha256((root/'evidence'/(tag+'-audit.json')).read_bytes()).hexdigest())
    index, grouped = {}, defaultdict(list)
    for row in rows:
        key = row['arm'], row['pilot'], row['snr'], row['block']
        assert key not in index and row['arm'] in arms and row['scores']['bits'] == 512
        index[key] = row
        grouped[key[:3]].append(row)
        for reference, paired in row['by_reference'].items():
            assert row['scores']['errors']-paired['reference_errors'] == paired['added']-paired['rescued']
    assert len(rows) == 3328 and len(grouped) == 52
    assert all(sorted(r['block'] for r in values) == list(range(64)) for values in grouped.values())
    means = []
    for (arm, pilot, snr), values in sorted(grouped.items()):
        errors = sum(r['scores']['errors'] for r in values)
        seconds = np.array([r['seconds'] for r in values])
        means.append(dict(arm=arm, pilot=pilot, snr=snr, errors=errors, bits=64*512,
            ber=errors/(64*512), mean_seconds=float(seconds.mean()), p95_seconds=float(np.quantile(seconds, .95)),
            seconds_per_bit=float(seconds.sum()/(64*512)),
            mean_coefficients=float(np.mean([r['scores']['active_coefficients'] for r in values])),
            mean_edges=float(np.mean([np.mean(r['scores']['edges']) for r in values])),
            by_reference={ref: {metric: sum(r['by_reference'][ref][metric] for r in values)
                               for metric in ('rescued', 'added', 'reference_errors')} for ref in controls}))
    lookup = {(r['arm'], r['pilot'], r['snr']): r for r in means}

    def compare(pairs):
        labels, samples = [], []
        for left, right in pairs:
            for pilot in ('p0', 'pZ'):
                for snr in (10, 20):
                    labels.append(dict(left=left, right=right, pilot=pilot, snr=snr))
                    samples.append([(index[left, pilot, snr, b]['scores']['errors']-
                                     index[right, pilot, snr, b]['scores']['errors'])/512 for b in range(64)])
        intervals = cluster_intervals(np.array(samples).T)
        return [dict(**label, **interval) for label, interval in zip(labels, intervals['rows'])], {
            k: v for k, v in intervals.items() if k != 'rows'}

    contrasts, primary_bootstrap = compare([(base, control) for base in bases for control in controls])
    same_q, same_q_bootstrap = compare([(f'{left}_q{q}', f'{right}_q{q}') for q in (3, 5, 7)
                                       for left, right in (('gce', 'fourier'), ('dpss', 'fourier'), ('dpss', 'gce'))])
    assert len(contrasts) == 144 and len(same_q) == 36
    cost = {arm: float(np.mean([r['seconds'] for r in rows if r['arm'] == arm]))/512 for arm in arms}
    fastest = min(controls, key=lambda arm: cost[arm])
    empty_graphs = [dict(block=r['block'], pilot=r['pilot'], snr=r['snr'], arm=r['arm'],
                        outer_iterations=[i for i, edges in enumerate(r['scores']['edges']) if edges == 0],
                        errors=r['scores']['errors'], record_sha256=r['record_sha256'])
                    for r in rows if 0 in r['scores']['edges']]
    candidates, budget_pairs = [], []
    for arm in bases:
        relevant = [r for r in contrasts if r['left'] == arm]
        minimum_errors = min(r['errors'] for r in means if r['arm'] in (arm, *controls))
        decision = candidate_decision(relevant, cost[arm]/cost[fastest], minimum_errors)
        candidates.append(dict(arm=arm, **decision))
        for control in controls:
            budget_pairs.append(dict(arm=arm, reference=control, cost_ratio=cost[arm]/cost[control],
                within_same_measured_budget=cost[arm] <= cost[control],
                primary_BER_contrast=next(r for r in relevant if r['right'] == control and r['pilot'] == 'pZ' and r['snr'] == 20),
                scope='fixed complete runs constrained by measured mean cost; not reruns with a common time cutoff'))
    report = dict(status='A04_COMPLETE', channels=64, full_receiver_calls=3328, new_channels=0,
        calibration_channels=0, holdout_channels=0, coding_calls=0, means=means, contrasts=contrasts,
        primary_bootstrap=primary_bootstrap, same_q_contrasts=same_q, same_q_bootstrap=same_q_bootstrap,
        complete_cost_per_bit=cost, fastest_qualified_classic=fastest, candidates=candidates,
        usable_candidates=[r['arm'] for r in candidates if r['usable']], same_measured_budget=budget_pairs,
        source_inputs=inputs, receipts=receipts, review_independence='weak',
        actual_calls=dict(CE=sum(r['scores']['counts']['ce_solves'] for r in rows),
                          outer_BP=sum(r['scores']['counts']['bp_calls'] for r in rows),
                          BP_inner_iterations=sum(r['scores']['bp_iterations'] for r in rows)),
        measured_frame_cpu_seconds=sum(r['cpu_seconds'] for r in rows),
        measured_frame_seconds=sum(r['seconds'] for r in rows),
        producer_audit_wall_span=max(v['finished_at'] for v in receipts.values())-min(v['started_at'] for v in receipts.values()),
        summed_single_thread_job_wall_seconds=sum(v['wall_seconds'] for v in receipts.values()),
        empty_graph_records=empty_graphs,
        empty_graph_outer_calls=sum(len(r['outer_iterations']) for r in empty_graphs),
        limitations=['A02 and A04 share development channels; not independent replication',
                     'all candidates measured, simultaneous intervals across 144 primary comparisons',
                     'same q, same iteration count, and same measured cost are distinct comparisons',
                     'timing includes instrumented receiver; model loading and archival I/O separate; no formal COST',
                     'B02 remains a separate historical diagnostic gate; no selector inferred from fixed-arm results'])
    (here/'a04-results-v1.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    flat = []
    for row in rows:
        value = {k: row[k] for k in ('block', 'snr', 'pilot', 'arm', 'seconds', 'cpu_seconds', 'record_sha256', 'input_sha256')}
        value.update({k: row['scores'][k] for k in ('errors', 'bits', 'channel_nmse', 'active_coefficients')})
        value['mean_edges'] = float(np.mean(row['scores']['edges']))
        for ref, pairs in row['by_reference'].items():
            for key, number in pairs.items():
                value[ref+'_'+key] = number
        flat.append(value)
    with (here/'a04-block-results-v1.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(flat)
    lines = ['# A-04 固定表示完整开发结果', '',
        f"裁决：{len(report['usable_candidates'])}个配置满足预定可用性门。可用配置：{report['usable_candidates']}。", '',
        '64个A02已保存开发信道；四端点、13臂，共3328F。全部原始数组独立进程回读与评分重算通过。',
        '这是开发筛选；没有校准、最终留出、编码或独立确认。主会话自审，独立性weak。', '',
        '## BER与完整成本', '',
        '| 臂 | p0@10 BER | p0@20 BER | pZ@10 BER | pZ@20 BER | 平均毫秒/bit |', '|---|---:|---:|---:|---:|---:|']
    for arm in arms:
        values = [lookup[arm, pilot, snr]['ber'] for pilot, snr in (('p0', 10), ('p0', 20), ('pZ', 10), ('pZ', 20))]
        lines.append('| '+arm+' | '+' | '.join(f'{v:.6f}' for v in values)+f' | {1000*cost[arm]:.5f} |')
    lines += ['', f"成本检验采用全部工程合格控制中最快的 {fastest}，全部控制倍率亦保留；不因BER结果换成本参照。", '',
        '| 配置 | 主BER门 | 其他端点门 | 误差改善成本门 | 等效门 | 等效降本门 | 裁决 |', '|---|---|---|---|---|---|---|']
    for row in candidates:
        lines.append(f"| {row['arm']} | {row['primary_effect_gate']} | {row['other_endpoint_gate']} | {row['benefit_cost_gate']} | {row['equivalence_gate']} | {row['reduction_cost_gate']} | {row['status']} |")
    lines += ['', '## 主端点的预定配对区间', '',
        '九种基×四控制×四端点共144个比较统一同时95%区间；以下只展示主端点，完整表在JSON。差值为基减控制，负值较好。', '',
        '| 基 | 控制 | BER差 | 同时95%区间 | 救回bit | 新增bit |', '|---|---|---:|---|---:|---:|']
    for row in contrasts:
        if (row['pilot'], row['snr']) != ('pZ', 20):
            continue
        interval = row['simultaneous_95']
        label = '不可推断' if interval is None else f'[{interval[0]:.6f}, {interval[1]:.6f}]'
        pairs = lookup[row['left'], 'pZ', 20]['by_reference'][row['right']]
        lines.append(f"| {row['left']} | {row['right']} | {row['mean']:.6f} | {label} | {pairs['rescued']} | {pairs['added']} |")
    lines += ['', '## 计算与证据边界', '',
        f"实际CE {report['actual_calls']['CE']}、外循环BP {report['actual_calls']['outer_BP']}、BP内部迭代 {report['actual_calls']['BP_inner_iterations']}；0编码。",
        f"其中{report['empty_graph_outer_calls']}次BP调用遇到空图，按既有检测器返回无观测软状态、实际内部迭代为0；涉及{len(empty_graphs)}条完整接收，全部保留错误与成本，不算完整20步。",
        f"完整帧CPU合计 {report['measured_frame_cpu_seconds']/3600:.4f}核时；producer＋audit墙钟跨度 {report['producer_audit_wall_span']:.2f}秒；各单线程作业墙钟和 {report['summed_single_thread_job_wall_seconds']:.2f}秒。", '',
        '- 同q基族比较单列36个诊断区间；相同10×20循环不等于相同墙钟成本。每一对候选/控制都给出实际成本内/超预算标记，不声称做过额外等时截断试验。',
        '- 逐端点p95耗时、活动系数、实际BP边、逐信道救回/新增、全部源哈希见JSON/CSV。随机臂序固定，不根据中途BER停止或补样本。',
        '- 区间跨零、未达最小效应或高成本分别记录；不据未显著宣布等价。所有零方差不可推断和错误量门显式保留。',
        '- 空图出现在pZ@10的GCE/q7与DPSS/q7（信道28、54）；这是当前冻结构造的失效表现，未通过改阈值或删记录修饰结果。',
        '- A与B的准入相互独立：固定表示结果不能修补B02的历史诊断门。下一步按两者结果处理B03/B04，再作SYN裁决。', '']
    (here/'a04-results-v1.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status=report['status'], usable=report['usable_candidates'],
                          fastest_classic=fastest, calls=report['actual_calls']), ensure_ascii=False))


if __name__ == '__main__':
    main()
