"""Engineering evidence and prospective fixed-sample resource estimate."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    here = Path(__file__).resolve().parent
    root = Path('afdm_sp_joint_unrolled/outputs_unified_exploration_20260914')
    audit_path = root/'evidence/a03-engineering-v1-audit.json'
    audit = json.loads(audit_path.read_text())
    timing_path = root/'evidence/a03-timing-v1.json'
    timing = json.loads(timing_path.read_text())
    summary_path = root/'runs/a03-engineering-v1/engineering/summary.json'
    summary = json.loads(summary_path.read_text())
    assert audit['status'] == 'PASS'
    assert audit['summary_sha256'] == timing['summary_sha256'] == hashlib.sha256(summary_path.read_bytes()).hexdigest()
    receipts = {tag: json.loads((root/'evidence'/(tag+'-exit.json')).read_text())
                for tag in ('a03-unit-v1', 'a03-engineering-v1', 'a03-engineering-v1-audit')}
    assert all(r['exit_code'] == 0 and not r['timed_out'] for r in receipts.values())
    rows = [r for r in timing['rows'] if len(r['arm'].split('__')) == 2]
    assert len(rows) == 104
    groups = defaultdict(list)
    contexts = defaultdict(list)
    for row in rows:
        pilot, arm = row['arm'].split('__')
        groups[arm].append(row)
        contexts[arm, pilot, row['snr']].append(row)
    assert len(groups) == 13 and len(contexts) == 52
    means = []
    for arm, values in sorted(groups.items()):
        means.append(dict(arm=arm, frames=len(values), mean_seconds=float(np.mean([r['seconds'] for r in values])),
            max_seconds=max(r['seconds'] for r in values),
            mean_cpu_seconds=float(np.mean([r['cpu_seconds'] for r in values])),
            mean_coefficients=float(np.mean([r['active_coefficients'] for r in values])),
            mean_edges=float(np.mean([np.mean(r['edges']) for r in values])),
            mean_record_bytes=float(np.mean([r['bytes'] for r in values])),
            mean_times={k: float(np.mean([r['times'][k] for r in values])) for k in values[0]['times']}))
    full_calls = 64*4*13
    max_context_seconds = 64*sum(max(r['seconds'] for r in v) for v in contexts.values())
    max_context_cpu = 64*sum(max(r['cpu_seconds'] for r in v) for v in contexts.values())
    max_context_bytes = 64*sum(max(r['bytes'] for r in v) for v in contexts.values())
    # Double the observed context maxima, include measured archival/guard
    # overhead, then reserve a separate full-size raw audit allowance.
    frame_total = sum(e['seconds'] for e in summary['records'])
    archive_factor = max(1., summary['wall_seconds']/frame_total)
    cpu_upper = 2*max_context_cpu*archive_factor+600
    serial_upper = 2*max_context_seconds*archive_factor+600
    bytes_upper = 2*max_context_bytes+100*1024**2
    quote = dict(full_calls=full_calls, new_channels=0, reused_A02_development_channels=64,
        workers_initial=2, workers_max=4, threads_per_worker=1,
        measured_context_max_projection_seconds=max_context_seconds,
        archive_and_guard_factor=archive_factor, conservative_cpu_seconds=cpu_upper,
        conservative_wall_seconds_two_workers=serial_upper/2+120,
        conservative_wall_seconds_four_workers=serial_upper/4+120,
        conservative_bytes=bytes_upper, existing_root_bytes=timing['root_bytes'],
        total_peak_projection_bytes=timing['root_bytes']+bytes_upper,
        justification='2x each arm/endpoint observed maximum, measured archive factor, 600 seconds raw audit allowance; no engineering BER selection')
    quote['within_frozen_limits'] = bool(cpu_upper <= 28800 and serial_upper/2+120 <= 7200
        and bytes_upper <= 20*1024**3 and quote['total_peak_projection_bytes'] <= 80*1024**3)
    assert quote['within_frozen_limits']
    report = dict(status='A03_PASS_A04_RESOURCE_QUALIFIED', raw_audit=audit,
        timing_sha256=hashlib.sha256(timing_path.read_bytes()).hexdigest(), receipts=receipts,
        per_arm=means, development_quote=quote, review_independence='weak',
        tests=dict(local_small_receiver=8, server_targeted=43),
        experiment_calls=dict(F=125, T=13, outer_BP=1250, terminal_BP_replays=13, CE=1125, coding=0),
        default_replay='eight legacy frames: H/soft/sigma/gains/support/bits exact',
        repeats='13 same-input full pairs; core complex64/discrete exact, double diagnostics tolerance 1e-11; 13 last-detector outputs exact',
        limitations=['two engineering channels, not performance evidence',
            'complex64 receiver frontend; BP promotes working arrays to complex128',
            'component times are nested; archival I/O external to frame timer',
            'no formal cost, fresh confirmation or code scope qualification'])
    (here/'a03-results-v1.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    lines = ['# A-03 共同检测器工程结果', '',
        '裁决：工程与原始核验通过，九种固定基和四个经典控制全部进入A04。没有按工程BER筛臂。', '',
        '实际125F＋13T，producer 95.849秒、独立原始审计6.681秒；138条记录全部回读。共1125次CE、1250次外循环BP、13次末级BP重放，0编码调用。',
        '8个旧参考输出严格相等；13组完整接收重复一致；13个固定末级H的实际BP重放硬判和软矩严格相等。',
        f"complex128算子闭合最大误差 {audit['max_operator_closure']:.4g}；complex64设计/H按实际存储舍入回核。", '',
        '| 臂 | 平均完整秒/帧 | 最大秒/帧 | 平均系数数 | 平均BP边数 |', '|---|---:|---:|---:|---:|']
    for row in means:
        lines.append(f"| {row['arm']} | {row['mean_seconds']:.5f} | {row['max_seconds']:.5f} | {row['mean_coefficients']:.2f} | {row['mean_edges']:.1f} |")
    lines += ['', '耗时包含公开基/字典构造、初始选择/拟合、共同CE/BP及返回校验。图前端和消息迭代分别实测；各嵌套时间不能相加。checkpoint装载单列，原始归档I/O在帧计时外、已纳入阶段报价。', '',
        f"A04固定3328F、复用64个A02开发信道；保守CPU {cpu_upper/3600:.3f}核时，两worker墙钟 {quote['conservative_wall_seconds_two_workers']/60:.1f}分钟，四worker {quote['conservative_wall_seconds_four_workers']/60:.1f}分钟；写入上界 {bytes_upper/1024**3:.3f}GiB。均在原预算内。", '',
        '- 初始2个单线程worker；CPU余量满足保留16核后，可按合同扩到4。样本量、臂、终点和统计门不变。',
        '- 参数少未必更快：固定基的实际BP图更稠密。最终BER和每bit成本仍需A04完整开发。',
        '- 接收前端/系数complex64，固定基几何与原BP内部complex128；没有声称整条链都是complex64。',
        '- 本地8个真实小接收测试、服务器43个相关测试通过；N256资格来自上述实测，不由单元测试替代。',
        '- 主会话自审weak。此处仅工程资格/开发预算，未验证新颖贡献、独立确认或正式COST。', '']
    (here/'a03-results-v1.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status=report['status'], quote=quote), ensure_ascii=False))


if __name__ == '__main__':
    main()
