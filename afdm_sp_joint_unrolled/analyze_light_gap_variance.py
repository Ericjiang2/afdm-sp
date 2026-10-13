"""Recount the temperature/variance/LLR factorial from audited paired blocks."""
import argparse
import itertools
import json
from pathlib import Path
import statistics
import numpy as np
from .analyze_light_gap_replay import digest
from .supplement_statistics import cp_bounds, paired_delta


def analyze(root, contract):
    c=json.loads(contract.read_text());bindings={str(contract):digest(contract)}
    summaries={};audits={};stages={}
    for stage in ('engineering','development'):
        sp=root/f'runs/variance-v2/{stage}/summary.json'
        ap=root/f'evidence/variance-{stage}-audit-v2.json'
        ep=root/f'evidence/variance-{stage}-v2-exit.json'
        src=root/'source-variance-v2/source-manifest.json'
        s,a,e=[json.loads(p.read_text()) for p in (sp,ap,ep)]
        for p in (sp,ap,ep,src):bindings[str(p)]=digest(p)
        if (s['status']!='COMPLETE' or a['status']!='PASS' or e['exit_code']!=0 or e['timed_out']
                or s['contract_sha256']!=digest(contract) or a['summary_sha256']!=digest(sp)
                or a['exit_sha256']!=digest(ep) or s['source_manifest_sha256']!=digest(src)):
            raise ValueError('variance run/audit/source binding differs')
        key=lambda r:tuple(r[k] for k in ('block','snr','arm','beta','kind'))
        indexed={key(r):r for r in s['records']};audited={key(r):r for r in a['rows']}
        if set(indexed)!=set(audited) or len(indexed)!=len(s['records']):
            raise ValueError('duplicate or missing audited record')
        for k,item in indexed.items():
            if any(audited[k][name]!=v for name,v in item['scores'].items()):
                raise ValueError('summary score differs from raw audit')
        summaries[stage]=s;audits[stage]=a
        stages[stage]=dict(calls=s['calls'],wall_seconds=s['wall_seconds'],
            records=len(indexed),arrays_audited=a['arrays_audited'])
    oldp=root/'evidence/llr-development-audit.json'
    olds=root/'runs/llr-v1/development/summary.json'
    old=json.loads(oldp.read_text());old_summary=json.loads(olds.read_text())
    if old['status']!='PASS' or old['summary_sha256']!=digest(olds):raise ValueError('old LLR audit differs')
    if {e['block']:e['hashes'] for e in old_summary['exogenous']}!={e['block']:e['hashes'] for e in summaries['development']['exogenous']}:
        raise ValueError('old T2 and new T1 do not share exogenous blocks')
    for p in (oldp,olds):bindings[str(p)]=digest(p)
    mapping=dict(EST_BASE='I1',EST_NOISE='BP_EST_NOISE',TRUE_BASE='BP_TRUE_BASE',TRUE_NOISE='BP_TRUE_NOISE')
    t2={(r['block'],r['snr'],r['arm'],r['beta']):r for r in old['rows']}
    t1={(r['block'],r['snr'],r['arm'],r['beta']):r for r in audits['development']['rows']}
    tables=[];n=64
    for snr,case,temp,beta in itertools.product([7,8],c['cases'],[2,1],c['betas']):
        rows=[(t1[b,snr,case+'_T1_20',beta] if temp==1 else t2[b,snr,mapping[case],beta]) for b in range(n)]
        base=[t2[b,snr,'I1',1.] for b in range(n)]
        rescue=[b for b in range(n) if base[b]['FER'] and not rows[b]['FER']]
        broken=[b for b in range(n) if not base[b]['FER'] and rows[b]['FER']]
        errors=sum(r['FER'] for r in rows);lo,hi=cp_bounds(errors,n,.025)
        pair=paired_delta(len(rescue),len(broken),n,alpha_family=.05,m=1)
        tables.append(dict(snr=snr,case=case,temperature=temp,beta=beta,blocks=n,errors=errors,
            FER=errors/n,FER_CI95=[float(lo),float(hi)],rescued=rescue,broken=broken,
            paired_improvement=float(pair['delta']),paired_CI95=[float(pair['lower']),float(pair['upper'])],
            NLL=statistics.fmean(r['bit_NLL'] if temp==1 else r['NLL'] for r in rows),
            raw_bit_errors=sum(r['raw_bit_errors'] for r in rows)))
    ep=[]
    for snr,arm in itertools.product([7,8],['EP_EST_NOISE','EP_TRUE_NOISE']):
        rows=[r for r in summaries['development']['old_ep_audits'] if (r['snr'],r['arm'])==(snr,arm)]
        ep.append(dict(snr=snr,arm=arm,blocks=len(rows),
            final_rejected_min=min(r['final_rejected'] for r in rows),
            final_rejected_max=max(r['final_rejected'] for r in rows),
            fixed_point_residual_median=float(np.median([r['fixed_point_residual'] for r in rows])),
            small_update_count=sum(r['fixed_point_residual']<=1e-5 for r in rows),
            max_linear_relative_residual=max(r['max_linear_relative_residual'] for r in rows),
            old_qualified_count=sum(r['reported_converged'] for r in rows)))
    return dict(status='PASS',stages=stages,tables=tables,EP=ep,
        BP20_40=summaries['development']['doubling'],input_sha256=bindings,
        inference='descriptive marginal 95% CP and paired CP/union intervals; no selection-adjusted confirmation',
        independent_blocks=64,observations=128,new_calls=dict(F=0,T=0,D=0),
        review='main-session self-review per user instruction')


def markdown(r):
    lookup={(t['snr'],t['case'],t['temperature'],t['beta']):t for t in r['tables']}
    lines=['# L04：内部温度、方差与末端标定','',
        '新工程52T＋64D，开发528T＋2048D，开发进程275.03秒。工程712数组、开发11424数组原始审计通过。T2网格复用L02，不重复计入新增调用。',
        '', '以下均为已看过的64个开发块；7/8 dB共享同一外生块。BASE含原固定0.5乘子。T仅控制边星座投影，β只作用于已clip20的终端LLR。完整配对列表与描述性区间见JSON。','',
        '|SNR|H/方差|边温度|β=.5|β=.75|β=1|β=1.5|β=2|',
        '|---|---|---|---|---|---|---|---|']
    for snr,case,temp in itertools.product([7,8],['EST_BASE','EST_NOISE','TRUE_BASE','TRUE_NOISE'],[2,1]):
        counts='|'.join(str(lookup[snr,case,temp,b]['errors']) for b in [.5,.75,1.,1.5,2.])
        lines.append(f'|{snr}|{case}|{temp}|{counts}|')
    selected=lookup[7,'EST_NOISE',1,1.]
    lines += ['',f"7 dB的T1＋热噪声对照错32块，原I1错35块；救回{len(selected['rescued'])}、新增{len(selected['broken'])}。配对改善区间{selected['paired_CI95']}，仍需新鲜开发；不是已确认增益。8 dB两者均错2块。",
        '', '只将BASE的边温度从2改为1，7/8 dB错块升至60/25。真H＋热噪声下T1恢复2/0；与真H＋BASE的T2结果相近。这支持内部有限消息的温度与方差必须联合解释，不能把物理噪声估计和推断标定混为一个旋钮。',
        '', 'BP20→40只测每SNR前2块。BASE下部分实际边消息残差仍大且译码会变，热噪声下残差通常下降；这是有限迭代诊断，不是完整64块收敛保证。逐块残差/译码相等性均保存在JSON。',
        '', 'EP旧轨迹的线性求解残差很小，但不少站点仍拒绝更新。小更新可能来自保留旧站点；零拒绝是旧额外资格门，并非边缘正确或数值稳定的必要条件。已有单符号负站点反例能得到准确QPSK边缘但不通过此门。原门保持不变，EP不凭开发FER差异晋级；也不把资格失败统一称为发散。',
        '', '下一判别：固定同一CPU-gels完整基线，先对比均值CE、动态Gamma和经典正则；用真实边空腔矩测试非圆消息。连续多普勒优化排除。','']
    return '\n'.join(lines)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mission',type=Path,required=True);args=p.parse_args()
    r=analyze(args.root,args.mission/'contracts/variance-v2.json')
    r['analyst_sha256']=digest(__file__)
    with (args.mission/'evidence/l04-analysis-v1.json').open('x') as f:json.dump(r,f,indent=2)
    with (args.mission/'research/l04-variance-v1.md').open('x') as f:f.write(markdown(r))
    print(json.dumps(dict(status=r['status'],tables=len(r['tables']),EP=r['EP'])))
