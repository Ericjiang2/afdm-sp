"""Channel-paired initial-estimation tables, with no BER extrapolation."""
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

from ab_statistics_v1 import cluster_intervals


def main():
    here=Path(__file__).resolve().parent
    root=Path('afdm_sp_joint_unrolled/outputs_unified_exploration_20260914')
    path=root/'evidence/a02-metrics-v3.json'
    archived=path.with_suffix('.json.gz')
    if path.exists():
        data=path.read_bytes()
        if not archived.exists():archived.write_bytes(gzip.compress(data,mtime=0))
    else:data=gzip.decompress(archived.read_bytes())
    source=json.loads(data);rows=source['rows']
    assert len(rows)==5120 and len(source['inputs'])==64
    for tag,digest in source['input_summaries'].items():
        a=json.loads((root/'evidence'/(tag+'-audit.json')).read_text())
        assert a['status']=='PASS' and a['summary_sha256']==digest
    grouped=defaultdict(list);indexed={}
    for r in rows:
        key=r['family'],r['q'],r['fit'],r['pilot'],r['snr']
        grouped[key].append(r)
        indexed[(*key,r['block'])]=r
    assert len(grouped)==80 and all(sorted(r['block'] for r in v)==list(range(64)) for v in grouped.values())
    means=[]
    for key,values in sorted(grouped.items()):
        means.append(dict(family=key[0],q=key[1],fit=key[2],pilot=key[3],snr=key[4],
            coefficients=values[0]['columns'],
            scores={name:float(np.mean([r['scores'][name] for r in values])) for name in values[0]['scores'] if name!='components'},
            components={name:float(np.mean([r['scores']['components'][name] for r in values])) for name in values[0]['scores']['components']},
            max_condition=max(r['geometry']['condition'] for r in values),
            rejected_candidates=sum(r['rejected_groups'] for r in values),
            oracle_qualified=sum(r['oracle_status']=='QUALIFIED' for r in values),
            oracle_nmse_qualified_mean=float(np.mean([r['oracle_nmse'] for r in values if r['oracle_status']=='QUALIFIED'])) if any(r['oracle_status']=='QUALIFIED' for r in values) else None))
    contrasts=[];samples=[]
    def add(left,right,label):
        a=np.array([indexed[(*left,b)]['scores']['channel_nmse'] for b in range(64)])
        b=np.array([indexed[(*right,k)]['scores']['channel_nmse'] for k in range(64)])
        contrasts.append(dict(kind=label,left=list(left),right=list(right),relative_mean_change=float((a.mean()-b.mean())/b.mean())))
        samples.append(a-b)
    for family in ('fourier','gce','dpss'):
        for q in (3,5,7):
            for fit in ('ls','ridge'):
                for pilot in ('p0','pZ'):
                    for snr in (10,20):
                        for reference in ('ls','ridge'):
                            add((family,q,fit,pilot,snr),('small',5,reference,pilot,snr),'different_capacity_classic')
    for q in (3,5,7):
        for left,right in [('gce','fourier'),('dpss','fourier'),('dpss','gce')]:
            for fit in ('ls','ridge'):
                for pilot in ('p0','pZ'):
                    for snr in (10,20):add((left,q,fit,pilot,snr),(right,q,fit,pilot,snr),'same_q')
    for family,q in [(f,q) for f in ('fourier','gce','dpss') for q in (3,5,7)]+[('small',5)]:
        for pilot in ('p0','pZ'):
            for snr in (10,20):add((family,q,'ridge',pilot,snr),(family,q,'ls',pilot,snr),'paired_shrinkage')
    intervals=cluster_intervals(np.array(samples).T)
    for c,i in zip(contrasts,intervals['rows']):c.update(i)
    report=dict(status='A02_NUMERIC_PASS_CONTINUE_A03',channels=64,records=2624,paired_fits=5120,
        full_receiver_calls=0,BP_calls=0,raw_export_sha256=hashlib.sha256(data).hexdigest(),
        compressed_export_sha256=hashlib.sha256(archived.read_bytes()).hexdigest(),
        input_summaries=source['input_summaries'],means=means,contrasts=contrasts,
        bootstrap={k:v for k,v in intervals.items() if k!='rows'},
        max_error_accounting_closure=max(r['scores']['closure_error'] for r in rows),
        all_active_geometries_qualified=all(r['geometry']['qualified'] for r in rows),
        max_active_condition=max(r['geometry']['condition'] for r in rows),
        continuation='All nine basis configurations proceed to detector compatibility; no BER selection here.',
        review_independence='weak',
        limitations=['same development channels may be reused in A04, not independent replication',
            'oracle supports only outside estimator','initial estimates, no full receiver performance/cost',
            'metrics-v2 derived oracle_columns used shape rank instead of length; v3 corrects that export field only; raw unchanged'])
    assert report['all_active_geometries_qualified']
    (here/'a02-results-v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    table=here/'a02-block-results-v2.csv'
    fields=['family','q','fit','pilot','snr','block','columns','channel_nmse','pilot_nmse','representation','selection','shrink','pilot_alias','data_interference','noise','numerical','cross_terms','closure_error','oracle_status','oracle_nmse','oracle_columns','record_sha256']
    with table.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            values={k:r[k] for k in fields if k in r}
            values.update({k:r['scores'][k] for k in fields if k in r['scores']})
            values.update(r['scores']['components']);writer.writerow(values)
    lines=['# A-02 带噪估计结果','',
        '裁决：九种基配置数值合格，进入A-03。带限投影误差不是带噪估计误差，本行没有BER/检测调用。','',
        '64个独立开发信道；4个pilot/SNR端点配对；10种支撑选择×LS/ridge，共5,120拟合。2,624条原始记录独立进程回放通过。主会话自审，独立性weak。','',
        '## 主端点 pZ@20dB 的初始信道NMSE','',
        '| 基/q | 系数数 | LS | ridge0.1 | 表示误差 | LS支撑误差 | LS数据干扰项 | LS噪声项 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    lookup={(m['family'],m['q'],m['fit'],m['pilot'],m['snr']):m for m in means}
    for family,q in [(f,q) for f in ('fourier','gce','dpss') for q in (3,5,7)]+[('small',5)]:
        ls=lookup[family,q,'ls','pZ',20];ridge=lookup[family,q,'ridge','pZ',20]
        lines.append(f"| {family}/{q} | {ls['coefficients']} | {ls['scores']['channel_nmse']:.6g} | {ridge['scores']['channel_nmse']:.6g} | {ls['scores']['representation']:.5g} | {ls['scores']['selection']:.5g} | {ls['components']['data_interference']:.5g} | {ls['components']['noise']:.5g} |")
    lines+=['','各项并非可直接相加：pilot别名、收缩和交叉项完整保留在CSV/JSON。真时延oracle单列；rank/condition失败不计入oracle均值。',
        '', '1. q5 DPSS表示误差约3.84e-5，但初始LS NMSE约0.411，高于Fourier/q5的0.338和小支撑的0.164。表示优势没有直接转成带噪估计优势。',
        '2. q7 GCE/DPSS的LS严重放大干扰；ridge压到约0.267，仍高于普通小支撑ridge的0.155。该端点下新增表示自由度尚无初始估计收益。',
        '3. q5 DPSS的数据干扰项约0.392、噪声项约0.0081，表明本层的主要负担不是纯白噪声。分账固定在noisy选择支撑上，不能据此推出软反馈后的BER。',
        '',f"最大分账闭合差 {report['max_error_accounting_closure']:.3g}，最大合法活动条件数 {report['max_active_condition']:.5g}，保持原1e8门。",'',
        '## 证据范围','',
        '- 全部四端点均值、256个预定NMSE对比及20,000次信道簇bootstrap同时区间见JSON；逐信道数表见a02-block-results-v2.csv。',
        '- 同q比较、小支撑不同自由度比较、同支撑收缩分别标记。此处不声称同时间预算，也不按NMSE选择BER获胜臂。',
        '- 源快照source-a02-v2；工程92A含10次重复，另有失败v1的23A。失败版本不混入开发统计。',
        '- 开发两个producer实际140.597/144.796秒；独立audit实际108.170/107.530秒；无BP/编码调用。',
        '- 服务器44项单元通过。本地43项通过，另1项因runner传递导入matplotlib缺包未运行；同项在服务器真实环境通过，未将本地静态检查冒充运行。',
        '- 原始NPZ留服务器，source/export/record哈希和路径均保存。v2导出中oracle列数误写成shape长度，v3已按shape[0]纠正；不改原始数组或NMSE。',
        '- A-04可使用同一64开发信道，但两层结果不能称独立重复。下一步核验共同接收循环兼容性及完整成本。','']
    (here/'a02-results-v2.md').write_text('\n'.join(lines))
    print(json.dumps({k:report[k] for k in ('status','channels','paired_fits','max_error_accounting_closure','max_active_condition')},ensure_ascii=False))


if __name__=='__main__':main()
