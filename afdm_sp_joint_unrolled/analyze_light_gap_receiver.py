"""Paired descriptive analysis of audited full or noncircular receiver probes."""
import argparse
import json
from pathlib import Path
import statistics
from .analyze_light_gap_replay import digest
from .supplement_statistics import cp_bounds,paired_delta


def analyze(root,mission,tag):
    cp=mission/'contracts'/(tag+'.json');c=json.loads(cp.read_text())
    if c['schema'] not in ('i1-light-full-v1','i1-light-noncircular-v1'):raise ValueError('unsupported campaign')
    bindings={str(cp):digest(cp)};stages={};development=None
    for stage in ['engineering','development']:
        sp=root/'runs'/tag/stage/'summary.json';ap=root/'evidence'/f'{tag}-{stage}-audit.json'
        ep=root/'evidence'/f'{tag}-{stage}-exit.json';src=root/('source-'+tag)/'source-manifest.json'
        s,a,e=[json.loads(p.read_text()) for p in [sp,ap,ep]]
        for p in [sp,ap,ep,src]:bindings[str(p)]=digest(p)
        if (s['status']!='COMPLETE' or a['status']!='PASS' or e['exit_code']!=0 or e['timed_out']
                or a['summary_sha256']!=digest(sp) or a['exit_sha256']!=digest(ep)
                or s['contract_sha256']!=digest(cp) or a['contract_sha256']!=digest(cp)
                or s['source_manifest_sha256']!=digest(src)):
            raise ValueError('source/contract/summary/audit/exit binding differs')
        key=lambda r:tuple(r[k] for k in ('block','snr','arm'))
        indexed={key(r):r for r in s['records']};audited={key(r):r for r in a['rows']}
        if len(indexed)!=len(s['records']) or set(indexed)!=set(audited):raise ValueError('record inventory differs')
        for k,row in indexed.items():
            if row['scores']!=audited[k]['scores']:raise ValueError('raw and summary scores differ')
        stages[stage]=dict(blocks=s['blocks'],calls=s['calls'],nested_LDPC=s['nested_LDPC'],
            process_seconds=e['wall_seconds'],measured_stage_seconds=s['wall_seconds'],arrays_audited=a['arrays_audited'])
        if stage=='development':development=(s,indexed,audited)
    s,indexed,audited=development;n=s['blocks'];tables=[];profiles=[]
    for snr in [7,8]:
        for arm in sorted({r['arm'] for r in s['records']}):
            reference=(next(case+'_CIRC' for case in c['cases'] if arm.startswith(case+'_'))
                       if c['schema']=='i1-light-noncircular-v1' else 'MEAN')
            values=[indexed[b,snr,arm] for b in range(n)];base=[indexed[b,snr,reference] for b in range(n)]
            rescued=[b for b in range(n) if base[b]['scores']['FER'] and not values[b]['scores']['FER']]
            broken=[b for b in range(n) if not base[b]['scores']['FER'] and values[b]['scores']['FER']]
            errors=sum(r['scores']['FER'] for r in values);lo,hi=cp_bounds(errors,n,.025)
            paired=paired_delta(len(rescued),len(broken),n,alpha_family=.05,m=1)
            table=dict(snr=snr,arm=arm,reference=reference,blocks=n,errors=errors,FER=errors/n,
                FER_CI95=[float(lo),float(hi)],rescued=rescued,broken=broken,
                paired_improvement=float(paired['delta']),paired_CI95=[float(paired['lower']),float(paired['upper'])],
                NLL=statistics.fmean(r['scores']['bit_NLL'] for r in values),
                mean_seconds=statistics.fmean(r['seconds'] for r in values),
                mean_CPU_seconds=statistics.fmean(r['CPU_seconds'] for r in values))
            if 'channel_NMSE' in values[0]['scores']:
                table['channel_NMSE']=statistics.fmean(r['scores']['channel_NMSE'] for r in values)
            tables.append(table)
            details=[audited[b,snr,arm] for b in range(n)]
            if 'CE' in details[0]:
                for iteration in sorted({x['iteration'] for r in details for x in r['CE']}):
                    states=[x for r in details for x in r['CE'] if x['iteration']==iteration]
                    profiles.append(dict(snr=snr,arm=arm,iteration=iteration,kind='CE',
                        mean_variance=statistics.fmean(x['mean_variance'] for x in states),
                        gamma_relative_scale=statistics.fmean(x['gamma_relative_scale'] for x in states),
                        normal_residual_max=max(x['normal_relative_residual'] for x in states)))
            else:
                for iteration in range(1,21):
                    states=[x for r in details for x in r['trace'] if x['iteration']==iteration]
                    edges=sum(x['edges'] for x in states)
                    profiles.append(dict(snr=snr,arm=arm,iteration=iteration,kind='actual_BP_cavity',edges=edges,
                        **{k:sum(x[k]*x['edges'] for x in states)/edges for k in ['zeta_mean','zeta_gt01','zeta_gt02','KL_mean']}))
    return dict(status='PASS',tag=tag,stages=stages,tables=tables,profiles=profiles,input_sha256=bindings,
        independent_blocks=n,observations=2*n,new_calls=dict(F=0,T=0,D=0),
        inference='descriptive 95% marginal CP and paired CP/union intervals; no selection-adjusted independent confirmation',
        reviewer='main-session self-review per user instruction',analyst_sha256=digest(__file__))


def markdown(r):
    n=r['independent_blocks'];lines=[f"# {r['tag']}：开发配对结果",'',
        f'{n} 个独立外生块；7/8 dB共享同一块。原始审计、摘要分数和输入哈希一致。区间为描述性95%区间，开发筛选不构成独立确认。','',
        '|SNR|方法|错块|救回/新增|NMSE|平均秒/F或T|',
        '|---|---|---|---|---|---|']
    for t in r['tables']:
        nmse=f"{t['channel_NMSE']:.6f}" if 'channel_NMSE' in t else '—'
        lines.append(f"|{t['snr']}|{t['arm']}|{t['errors']}/{n}|{len(t['rescued'])}/{len(t['broken'])}|{nmse}|{t['mean_seconds']:.3f}|")
    lines+=['','救回/新增相对表中所属基线（完整链为MEAN；非圆终端为同温度、同方差CIRC）。完整逐块列表、描述性区间、NLL和逐轮统计见同名JSON。',
        '', '时间包括所启用的审计拷贝；不是独占资源正式COST验证。无新增调用，也没有使用独立子代理审查。','']
    return '\n'.join(lines)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mission',type=Path,required=True);p.add_argument('--tag',required=True);args=p.parse_args()
    r=analyze(args.root,args.mission,args.tag)
    with (args.mission/'evidence'/(args.tag+'-analysis-v1.json')).open('x') as f:json.dump(r,f,indent=2)
    with (args.mission/'research'/(args.tag+'-results-v1.md')).open('x') as f:f.write(markdown(r))
    print(json.dumps(dict(status=r['status'],tag=r['tag'],tables=[{k:t[k] for k in ['snr','arm','errors','rescued','broken']} for t in r['tables']])))
