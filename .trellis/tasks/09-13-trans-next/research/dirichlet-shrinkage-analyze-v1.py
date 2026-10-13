"""Paired development summaries; never promote these intervals to confirmation."""
import hashlib
import json
from pathlib import Path
import numpy as np

base = Path('.trellis/tasks/09-13-trans-next/research')
raw_root = Path('afdm_sp_joint_unrolled/outputs_dirichlet_shrinkage_20260914')
summaries = []
audits = []
for phase in ('engineering', 'development'):
    audit = json.loads((raw_root/'audit'/f'{phase}.json').read_text())
    path = raw_root/phase/'summary.json'
    assert audit['status'] == 'PASS'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == audit['summary_sha256']
    summaries.append(json.loads(path.read_text()))
    audits.append(audit)
reference = json.loads((raw_root/'reference-full-index-v1.json').read_text())
online = [row for summary in summaries for row in summary['online_rows']]
offline = [row for summary in summaries for row in summary['offline_rows']]
assert len(online) == 192 and len(offline) == 5184
rng = np.random.default_rng(202609141902)
resamples = rng.integers(0,32,size=(20000,32))

def interval(delta, family):
    values = np.asarray(delta)[resamples].mean(axis=1)
    return np.quantile(values,[.025/family,1-.025/family]).tolist()

online_index = {(r['block'],r['snr'],r['kind']):r for r in online}
assert len(online_index)==192
report=dict(scope='32 reused G1 development blocks; engineering not independent; descriptive paired inference only',
            bootstrap=dict(seed=202609141902,replicates=20000,unit='channel block shared across SNR',
                           FER_family=6,offline_HNMSE_family=24),FER=[],FER_pairs=[],offline=[])
report['provenance'] = dict(raw_root=str(raw_root), audits=audits,
    reference_source=reference['source_path'], reference_sha256=reference['source_sha256'],
    analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    exposure='Retrospective: generated results and some endpoints were read before this analysis.')
report['accounting'] = dict(offline_CE_solves=5184, new_full_receivers=192,
    default_full_replays=4, audited_raw_records=sum(a['raw_records'] for a in audits),
    independent_LDPC_replays=sum(a['independent_LDPC_replays'] for a in audits),
    new_physical_channels=0, original_engineering_final_meter_failure_retained=True)
for snr in (7,8):
    for kind in ('ridge','diagonal','dirichlet'):
        rows=[online_index[b,snr,kind] for b in range(32)]
        assert all(r['resource_counts'] == rows[0]['resource_counts'] for r in rows)
        report['FER'].append(dict(snr=snr,kind=kind,frames=32,failures=sum(r['scores']['FER'] for r in rows),
            info_bit_errors=sum(r['scores']['coded_bit_errors'] for r in rows),
            H_NMSE=float(np.mean([r['scores']['channel_NMSE'] for r in rows])),
            receiver_seconds=float(np.mean([r['receiver_wall_seconds'] for r in rows])),
            prior_seconds=float(np.mean([r['prior_construction_seconds'] for r in rows])),
            resource_counts=rows[0]['resource_counts']))
    for a,b in (('dirichlet','ridge'),('diagonal','ridge'),('dirichlet','diagonal')):
        ea=np.array([online_index[i,snr,a]['scores']['FER'] for i in range(32)])
        eb=np.array([online_index[i,snr,b]['scores']['FER'] for i in range(32)])
        report['FER_pairs'].append(dict(snr=snr,arm=a,reference=b,delta=float((ea-eb).mean()),
            simultaneous95=interval(ea-eb,6),rescued=np.flatnonzero((ea==0)&(eb==1)).tolist(),
            harmed=np.flatnonzero((ea==1)&(eb==0)).tolist()))
offline_index={(r['block'],r['snr'],r['kind'],r['strength'],r['ce_index']):r for r in offline}
assert len(offline_index)==5184
for block in range(32):
    for snr in (7,8):
        assert len({r['scores']['projection_floor'] for r in offline if r['block']==block and r['snr']==snr}) == 1
for aggregate,ces in [('mean9',range(1,10)),('last', [9])]:
    for snr in (7,8):
        for strength in (.01,.1,1.):
            vectors={kind:np.array([np.mean([offline_index[i,snr,kind,strength,ce]['scores']['H_NMSE'] for ce in ces]) for i in range(32)]) for kind in ('ridge','diagonal','dirichlet')}
            for kind in ('diagonal','dirichlet'):
                delta=vectors[kind]-vectors['ridge']
                hp={k:float(np.mean([offline_index[i,snr,k,strength,ce]['scores']['Hp_NMSE'] for i in range(32) for ce in ces])) for k in (kind,'ridge')}
                report['offline'].append(dict(aggregate=aggregate,snr=snr,strength=strength,kind=kind,
                    mean_H_NMSE=float(vectors[kind].mean()),ridge_H_NMSE=float(vectors['ridge'].mean()),
                    delta=float(delta.mean()),relative_delta=float(delta.mean()/vectors['ridge'].mean()),simultaneous95=interval(delta,24),
                    mean_Hp_NMSE=hp[kind],ridge_Hp_NMSE=hp['ridge']))
assert len(reference['records']) == 64
report['historical_G1_FULL']={str(snr):dict(failures=sum(r['scores']['FER'] for r in reference['records'] if r['snr']==snr)) for snr in (7,8)}
report['offline_means'] = []
for aggregate, ces in [('mean9', range(1, 10)), ('last', [9])]:
    for snr in (7, 8):
        for strength in (.01, .1, 1.):
            for kind in ('ridge', 'diagonal', 'dirichlet'):
                rows = [offline_index[b, snr, kind, strength, ce] for b in range(32) for ce in ces]
                report['offline_means'].append(dict(aggregate=aggregate, snr=snr,
                    strength=strength, kind=kind, **{key:float(np.mean([r['scores'][key] for r in rows]))
                    for key in ('coefficient_risk', 'H_NMSE', 'Hp_NMSE', 'projection_floor')}))
report['decision'] = dict(dirichlet_qualified=False,
    reason='No FER advantage over ridge/diagonal; 7 dB is worse than ridge in the registered comparison.',
    future_strong_classical='Frozen ridge strength 0.1 is an ordinary reference, not a novel contribution.',
    no_online_strength_reselection=True, formal_COST_CONF_passed=False)
output = base/'dirichlet-shrinkage-results-v1.json'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
lines = [
    '# Dirichlet 固定相关收缩：开发结果', '',
    '2026-09-14。主会话自审，独立性 weak。原始数组与译码由另一个进程回读；这不构成独立科学审查。', '',
    '**当前相关收缩不晋级。** 固定 strength=0.1 时，7 dB 的 Dirichlet 比 ridge 多错8块；8 dB差异区间跨零。'
    '离线强正则下的 NMSE 改善不替代完整 FER 收益，也不用于事后改选在线强度。', '',
    'G1/N1024，32个既有开发信道，7/8 dB。所有臂使用相同观测、初始支撑、九次CE及完整迭代预算；'
    '工程块0/20包含在32块内。不是新确认集。', '',
    '## 完整链结果', '',
    '| SNR | 惩罚 | 错块/32 | 信息bit错误 | 最终H-NMSE | 完整接收秒/块 | 先验构造秒/块 |',
    '|---|---|---|---|---|---|---|']
for r in report['FER']:
    lines.append(f"| {r['snr']} | {r['kind']} | {r['failures']} | {r['info_bit_errors']} | {r['H_NMSE']:.6f} | {r['receiver_seconds']:.4f} | {r['prior_seconds']:.4f} |")
lines += ['', '原G1_FULL历史参照为7/8 dB错25/6块。普通ridge构成更强经典对照；这些开发数不建立方法新颖性。', '',
    '每链实际9次CE、10次外层BP/120迭代、1次终端BP/20迭代、4次LDPC。先验构造属于完整接收计时，不能重复相加。'
    '运行顺序未随机化、包含诊断插桩，所列时间只描述本批执行，不证明等时预算或正式部署降本。', '',
    '## 配对FER差', '',
    '差为候选减参照；负值较好。以32个信道重采样，跨SNR共用抽样索引，20000次，种子202609141902。'
    '三种对比×两SNR共六个端点，Bonferroni调整的百分位bootstrap名义同时95%区间。小样本覆盖近似；跨零不证明等效。', '',
    '| SNR | 对比 | FER差 | 区间 | 救回块 | 新增错块 |', '|---|---|---|---|---|---|']
for r in report['FER_pairs']:
    lo,hi=r['simultaneous95']
    lines.append(f"| {r['snr']} | {r['arm']} − {r['reference']} | {r['delta']:.5f} | [{lo:.5f}, {hi:.5f}] | {r['rescued']} | {r['harmed']} |")
lines += ['', '## 同状态CE全部预定比较', '',
    '复用原FULL九次CE输入。mean9先在同信道内平均九轮；last仅末次。24个H-NMSE对ridge比较共同校正。'
    '真值仅用于离线评分。完整三臂的系数风险、H/Hp误差和表示地板在同名JSON的offline_means中；共同支撑的表示地板不变。', '',
    '| 聚合 | SNR | 强度 | 候选 | H-NMSE | ridge | 相对差 | H-NMSE差区间 |', '|---|---|---|---|---|---|---|---|']
for r in report['offline']:
    lo,hi=r['simultaneous95']
    lines.append(f"| {r['aggregate']} | {r['snr']} | {r['strength']} | {r['kind']} | {r['mean_H_NMSE']:.6f} | {r['ridge_H_NMSE']:.6f} | {100*r['relative_delta']:.2f}% | [{lo:.6f}, {hi:.6f}] |")
lines += ['', '固定0.1的Dirichlet在7 dB平均九轮H-NMSE恶化4.03%，8 dB改善4.82%；'
    '强度1时相对过强ridge的改善约59%–62%，不能解释为相对最佳普通正则的同等收益。'
    '单中心先验、选支撑、反馈轨迹和偏差均可能影响结果，本批未单独识别失败原因。', '',
    '## 原始核验、成本与复现', '',
    '5184次离线CE + 192新完整链 + 4默认回放；5380条raw记录、196次末端LDPC独立进程回放PASS。'
    '原工程末尾计量失败完整保留；恢复未重复任何已完成F/O。工程/开发执行墙钟78.986/949.821秒，'
    '对应审计32.395/401.604秒；远端目录约2.0GiB，均未超原阶段限额。没有新物理信道。', '',
    '本地原始小文件：`afdm_sp_joint_unrolled/outputs_dirichlet_shrinkage_20260914/`；'
    '远端完整raw：`deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_dirichlet_shrinkage_20260914/`。'
    'harvest-final-v1.json记录24个原始小文件的SHA-256，下载逐文件核对；全部大数组留远端并由记录哈希及审计绑定。', '',
    '源码manifest SHA-256：`50fb12ce9f4846a30a7d5644782ad6bd71afaadac70ca84629560804a31628df`。'
    '工程与开发summary分别为`8c9ee40c…`、`04cfa02b…`，完整值见JSON和审计收据。', '',
    '复现分析：', '', '```sh',
    '.mission/20260914_12-58-51-afdm-unified-exploration/.venv/bin/python .trellis/tasks/09-13-trans-next/research/dirichlet-shrinkage-analyze-v1.py',
    '```', '',
    '分析为回溯：数据已生成且部分端点在预测冻结前读取。后续P3不得倒签独立预测。'
    'DIR两项的有界实验交付已完成；独立CONF、正式COST、总体理论预测能力和论文贡献仍未证明。', '']
(base/'dirichlet-shrinkage-results-v1.md').write_text('\n'.join(lines))
print(json.dumps(dict(output=str(output), FER=report['FER'], decision=report['decision']),ensure_ascii=False))
