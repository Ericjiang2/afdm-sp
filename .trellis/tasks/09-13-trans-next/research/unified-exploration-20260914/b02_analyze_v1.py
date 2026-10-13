"""Frozen one-feature ridge predictions; held-out channel-cluster inference."""
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from ab_statistics_v1 import cluster_intervals

FEATURES = ('nmse', 'hp', 'residual', 'margin')
TARGETS = ('rescued', 'added')


def fit_predict(x_fit, y_fit, x_test):
    """Standardize on fit only; unpenalized intercept, unit slope penalty."""
    x = np.asarray(x_fit, dtype=float)
    y = np.asarray(y_fit, dtype=float)
    test = np.asarray(x_test, dtype=float)
    if x.ndim != 1 or y.shape != (len(x), 2) or test.ndim != 1:
        raise ValueError('one feature and two targets required')
    if not len(x) or not all(np.isfinite(v).all() for v in (x, y, test)):
        raise ValueError('nonempty finite fit data and finite test feature required')
    center = float(x.mean())
    scale = float(x.std())
    constant = bool(np.all(x == x[0]))
    intercept = y.mean(axis=0)
    if constant:
        slope = np.zeros(2)
        prediction = np.broadcast_to(intercept, (len(test), 2)).copy()
    else:
        z = (x - center) / scale
        slope = z @ (y - intercept) / (z @ z + 1.)
        prediction = intercept + ((test - center) / scale)[:, None] * slope
    return prediction, dict(center=center, scale=scale, constant_predictor=constant,
                            intercept=intercept.tolist(), slope=slope.tolist(),
                            slope_penalty=1., clipping=False, fit_rows=len(x))


def correlation(left, right):
    left, right = np.asarray(left), np.asarray(right)
    if np.all(left == left[0]) or np.all(right == right[0]):
        return dict(value=None, status='constant_channel_mean')
    return dict(value=float(np.corrcoef(left, right)[0, 1]), status='descriptive')


def analyze_domain(rows, domain):
    subset = [r for r in rows if r['domain'] == domain]
    number, per_block = (16, 16) if domain == 'uncoded256' else (32, 20)
    assert len(subset) == number * per_block
    groups = defaultdict(list)
    for row in subset:
        assert row['partition'] == ('fit' if row['block'] % 2 == 0 else 'heldout')
        assert row['errors'] - row['reference_errors'] == row['added'] - row['rescued']
        groups[row['block']].append(row)
    assert sorted(groups) == list(range(number)) and all(len(v) == per_block for v in groups.values())
    fit = [r for r in subset if r['partition'] == 'fit']
    test = [r for r in subset if r['partition'] == 'heldout']
    y_fit = np.array([[r[k] / r['bits'] for k in TARGETS] for r in fit])
    y_test = np.array([[r[k] / r['bits'] for k in TARGETS] for r in test])
    blocks = list(range(1, number, 2))
    block_ids = np.array([r['block'] for r in test])
    predictions, models, losses, table = {}, {}, {}, []
    for feature in FEATURES:
        prediction, models[feature] = fit_predict([r['features'][feature] for r in fit], y_fit,
                                                 [r['features'][feature] for r in test])
        predictions[feature] = prediction
        observed = np.column_stack((y_test, y_test[:, 1] - y_test[:, 0]))
        predicted = np.column_stack((prediction, prediction[:, 1] - prediction[:, 0]))
        delta = predicted - observed
        losses[feature] = np.array([np.mean(delta[block_ids == b, :2] ** 2, axis=0) for b in blocks])
        channel_true, channel_pred = [], []
        for b in blocks:
            mask = block_ids == b
            channel_true.append(observed[mask].mean(0))
            channel_pred.append(predicted[mask].mean(0))
            for j, target in enumerate((*TARGETS, 'net_added_minus_rescued')):
                table.append(dict(domain=domain, block=b, feature=feature, target=target,
                                  mse=float(np.mean(delta[mask, j] ** 2)),
                                  mae=float(np.mean(abs(delta[mask, j]))),
                                  truth_mean=float(observed[mask, j].mean()),
                                  prediction_mean=float(predicted[mask, j].mean())))
        channel_true, channel_pred = np.array(channel_true), np.array(channel_pred)
        models[feature]['heldout'] = {
            target: dict(mse=float(np.mean(delta[:, j] ** 2)), mae=float(np.mean(abs(delta[:, j]))),
                         channel_mean_correlation=correlation(channel_true[:, j], channel_pred[:, j]))
            for j, target in enumerate((*TARGETS, 'net_added_minus_rescued'))}
    labels, comparisons = [], []
    for target_index, target in enumerate(TARGETS):
        for reference in FEATURES[:-1]:
            labels.append(dict(target=target, reference=reference))
            comparisons.append(losses['margin'][:, target_index] - losses[reference][:, target_index])
    ci = cluster_intervals(np.array(comparisons).T, seed=(20260914, 125851, 92), draws=20000)
    contrasts = [dict(**label, **interval) for label, interval in zip(labels, ci['rows'])]
    changed = [b for b in blocks if any(r['rescued'] + r['added'] > 0 for r in groups[b])]
    usable = all(r['inference_usable'] for r in contrasts)
    wins = usable and all(r['simultaneous_95'][1] < 0 for r in contrasts)
    opposite = any(r['inference_usable'] and r['simultaneous_95'][0] > 0 for r in contrasts)
    supported = wins and len(changed) >= 5
    status = ('SUPPORTED' if supported else 'NOT_SUPPORTED' if opposite else 'STATISTICALLY_UNCERTAIN')
    coverage = [dict(block=b, fraction=float(np.mean([r['coverage_fraction'] for r in groups[b]])),
                     min_fraction=min(r['coverage_fraction'] for r in groups[b]),
                     certified_fraction=float(np.mean([r['certified_fraction'] for r in groups[b]])),
                     winner_changed_fraction=float(np.mean([r['winner_changed_fraction'] for r in groups[b]])),
                     rescued=sum(r['rescued'] for r in groups[b]), added=sum(r['added'] for r in groups[b]),
                     ties=sum(r['ties'] for r in groups[b])) for b in blocks]
    arm_counts = []
    for arm in sorted({r['arm'] for r in test}):
        arm_rows = [r for r in test if r['arm'] == arm]
        arm_counts.append(dict(arm=arm, rescued=sum(r['rescued'] for r in arm_rows),
                               added=sum(r['added'] for r in arm_rows),
                               reference_errors=sum(r['reference_errors'] for r in arm_rows),
                               errors=sum(r['errors'] for r in arm_rows),
                               bits=sum(r['bits'] for r in arm_rows)))
    prediction_rows = []
    for index, row in enumerate(test):
        result = {k: row[k] for k in ('domain', 'block', 'pilot', 'snr', 'arm', 'bits', 'rescued', 'added',
                                     'reference_errors', 'errors', 'coverage_fraction', 'record_sha256')}
        for feature in FEATURES:
            result[feature] = row['features'][feature]
            for j, target in enumerate(TARGETS):
                result[feature + '_' + target + '_prediction'] = float(predictions[feature][index, j])
        prediction_rows.append(result)
    return dict(domain=domain, status=status, gate_supported=supported, fit_blocks=list(range(0, number, 2)),
                heldout_blocks=blocks, fit_rows=len(fit), heldout_rows=len(test), models=models,
                contrasts=contrasts, bootstrap={k: v for k, v in ci.items() if k != 'rows'},
                changed_heldout_blocks=changed, event_gate=len(changed) >= 5,
                coverage_by_channel=coverage, heldout_arm_counts=arm_counts,
                count_scope='summed paired arm comparisons; same reference repeated across arms'), table, prediction_rows


def main():
    here = Path(__file__).resolve().parent
    root = Path('afdm_sp_joint_unrolled/outputs_unified_exploration_20260914')
    path = root / 'runs/b02-v1/analysis/summary.json'
    archived = path.with_suffix('.json.gz')
    data = path.read_bytes() if path.exists() else gzip.decompress(archived.read_bytes())
    if not archived.exists():
        archived.write_bytes(gzip.compress(data, mtime=0))
    assert gzip.decompress(archived.read_bytes()) == data
    digest = hashlib.sha256(data).hexdigest()
    audit_path = root / 'evidence/b02-v1-audit.json'
    audit = json.loads(audit_path.read_text())
    contract_path = root / 'contracts/b02-v1.json'
    contract = json.loads(contract_path.read_text())
    assert audit['status'] == 'PASS' and audit['summary_sha256'] == digest
    assert audit['contract_sha256'] == hashlib.sha256(contract_path.read_bytes()).hexdigest()
    for tag in ('b02-v1', 'b02-v1-audit'):
        receipt = json.loads((root / 'evidence' / (tag + '-exit.json')).read_text())
        assert receipt['exit_code'] == 0 and not receipt['timed_out']
    source = json.loads(data)
    assert source['calls'] == {'A': 48} and len(source['rows']) == 896
    report = dict(status='B02_DIAGNOSTIC_COMPLETE', summary_sha256=digest,
                  audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                  contract_sha256=audit['contract_sha256'], input_summaries=contract['input_summaries'],
                  input_audits=contract['input_audits'], new_receiver_calls=0, new_decoder_calls=0,
                  review_independence='weak', domains=[],
                  interpretation_sha256=hashlib.sha256((here / 'b02-statistics-interpretation-v1.md').read_bytes()).hexdigest(),
                  limitations=['historical split, not fresh confirmation or causality',
                               'NMSE and Hp are external oracle explanatory features',
                               'local four-symbol hypotheses do not guarantee full-vector truth coverage',
                               'uncoded and coded targets are different; no information-bit/symbol mapping',
                               'predictions intentionally unclipped; constant inputs and degenerate CIs explicit'])
    tables, predictions = [], []
    for domain in ('uncoded256', 'coded1024'):
        result, table, prediction = analyze_domain(source['rows'], domain)
        report['domains'].append(result)
        tables += table
        predictions += prediction
    report['B03_diagnostic_admission'] = report['domains'][0]['gate_supported']
    for name, rows in [('b02-channel-losses-v1.csv', tables), ('b02-heldout-predictions-v1.csv', predictions)]:
        with (here / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    (here / 'b02-results-v1.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    lines = ['# B-02 历史候选间隔诊断', '',
             f"N256裁决：{report['domains'][0]['status']}；B-03诊断准入：{report['B03_diagnostic_admission']}。", '',
             '48条分析记录、896个臂/端点样本，原始候选/证书/覆盖率独立进程回放PASS；0新接收/译码调用。主会话自审，独立性weak。', '',
             '每域偶数信道拟合、奇数留出。四个代理各拟合两个一维ridge；标准化只用拟合组、斜率罚1，无截断或调参。',
             '先按信道平均损失；救回/新增×三个代理共六个比较，20,000次信道簇bootstrap-t、max-|t|同时95%区间。', '']
    for domain in report['domains']:
        lines += [f"## {domain['domain']}", '',
                  f"拟合/留出信道 {len(domain['fit_blocks'])}/{len(domain['heldout_blocks'])}；发生错误变化的留出信道 {len(domain['changed_heldout_blocks'])}；裁决 {domain['status']}。", '',
                  '| 代理 | 救回MSE | 新增MSE | 救回MAE | 新增MAE |', '|---|---:|---:|---:|---:|']
        for feature, model in domain['models'].items():
            rescue, added = model['heldout']['rescued'], model['heldout']['added']
            lines.append(f"| {feature} | {rescue['mse']:.7g} | {added['mse']:.7g} | {rescue['mae']:.7g} | {added['mae']:.7g} |")
        lines += ['', '| 目标 | margin减对照 | MSE差 | 同时95%区间 |', '|---|---|---:|---|']
        for row in domain['contrasts']:
            interval = row['simultaneous_95']
            label = '不可推断' if interval is None else f"[{interval[0]:.7g}, {interval[1]:.7g}]"
            lines.append(f"| {row['target']} | {row['reference']} | {row['mean']:.7g} | {label} |")
        cover = domain['coverage_by_channel']
        lines += ['', f"留出完整真向量覆盖率均值 {np.mean([r['fraction'] for r in cover]):.6g}，最小 {min(r['min_fraction'] for r in cover):.6g}。", '',
                  '| 臂 | 救回bit | 新增bit | 参考错误bit | 当前错误bit |', '|---|---:|---:|---:|---:|']
        for row in domain['heldout_arm_counts']:
            lines.append(f"| {row['arm']} | {row['rescued']} | {row['added']} | {row['reference_errors']} | {row['errors']} |")
        lines += ['']
    lines += ['## 边界与下一步', '',
              '- N256只有8个诊断留出信道；区间跨零为未确定，不表示等价。已有总体结果曾被查看，奇偶划分不能升级为独立确认。',
              '- 编码结果只解释旧N1024块级信息错误；不得替代当前N256准入。NMSE/Hp不可用于在线规则。',
              '- 全部模型参数、常量/相关退化状态、分割、计数和源哈希见JSON；逐信道损失与逐行预测见CSV。',
              '- EDGE只选q，不选择图边，按预定条件形成不适用处置。B03仍须等待A04；诊断门失败时不拟合或运行选择器。', '']
    (here / 'b02-results-v1.md').write_text('\n'.join(lines))
    print(json.dumps(dict(admission=report['B03_diagnostic_admission'],
                          domains=[dict(domain=d['domain'], status=d['status'], changed=len(d['changed_heldout_blocks']))
                                   for d in report['domains']]), ensure_ascii=False))


if __name__ == '__main__':
    main()
