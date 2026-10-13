"""P2 frozen cluster bootstrap; analyzes audited CE records, no receiver calls."""
import hashlib
import json
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
audit_path = ROOT/'afdm_sp_joint_unrolled/outputs_trans_next_20260913/evidence/ce-oracle-fixed-ce-v1-raw-audit.json'
pred_path = BASE/'ce-state-predictions-v1.json'
audit = json.loads(audit_path.read_text())
pred = next(q for q in json.loads(pred_path.read_text())['questions'] if q['id']=='P2')
assert audit['status']=='PASS' and audit['new_CE']==64 and audit['new_F']==0
rows = {(r['block'], r['snr']):r for r in audit['rows']}
assert set(rows)=={(b,s) for b in range(32) for s in (7,8)}
rng=np.random.default_rng(pred['interval']['seed'])
idx=rng.integers(0,32,size=(20000,32))

def stats(before,after,draws,alpha):
    den=before[draws].sum(axis=1)
    invalid=int(np.count_nonzero(den==0))
    diff=(after-before)[draws].mean(axis=1)
    ratio=None if before.sum()==0 else float(1-after.sum()/before.sum())
    ci=None if invalid else np.quantile(1-after[draws].sum(axis=1)/den,[alpha/2,1-alpha/2]).tolist()
    return dict(n=len(before),before_mean=float(before.mean()),after_mean=float(after.mean()),
        absolute_after_minus_before=float((after-before).mean()),absolute_ci=np.quantile(diff,[alpha/2,1-alpha/2]).tolist(),
        proportional_reduction=ratio,ratio_ci=ci,undefined_ratio_bootstrap_draws=invalid)

result=dict(schema='oracle-ce-P2-analysis-v1',audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
    predictions_sha256=hashlib.sha256(pred_path.read_bytes()).hexdigest(),bootstrap=pred['interval'],primary={},subgroups={},new_receiver_calls=0,
    scope='Undirected intervention on exposed development channels; A/B/c and projected disturbances change jointly; no dominant-cause attribution.')
for s in (7,8):
    before=np.array([rows[b,s]['error_before'] for b in range(32)])
    after=np.array([rows[b,s]['error_after'] for b in range(32)])
    result['primary'][str(s)]=stats(before,after,idx,.05/4)
    result['subgroups'][str(s)]={}
    for name,ids in pred['groups'][str(s)].items():
        draws=rng.integers(0,len(ids),size=(20000,len(ids)))
        result['subgroups'][str(s)][name]=stats(before[ids],after[ids],draws,.05)
(BASE/'oracle-ce-results-v1.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# 固定支持真数据 CE：冻结 P2 结果','', '64 个工作点原始方程审计通过。每点仅一次真数据 CE；无新增 BP、LDPC 或完整接收。', '', '| SNR | 原误差均值 | 真数据 CE 后 | 差值及同时95%区间 | 比例降幅及同时95%区间 |','|---|---:|---:|---|---|']
for s,r in result['primary'].items():
    lines.append(f"| {s} dB | {r['before_mean']:.6g} | {r['after_mean']:.6g} | {r['absolute_after_minus_before']:.6g} [{r['absolute_ci'][0]:.6g}, {r['absolute_ci'][1]:.6g}] | {r['proportional_reduction']:.2%} [{r['ratio_ci'][0]:.2%}, {r['ratio_ci'][1]:.2%}] |")
lines += ['', '32 个独立物理信道整组重采样，两 SNR 同步；20,000 次，seed=202609150302；四个主量采用 Bonferroni 同时95%区间。零分母抽样次数见 JSON；不静默剔除。原 FULL 成败分组保持冻结定义，仅报告描述性95%区间。', '', '这是已暴露开发信道上的无方向 oracle 干预。重建 A 同时改变 B、c 与扰动投影，不能据降幅认定某误差源主导，也不能推断闭环 FER 改善。生产337.932秒，独立进程审计44.021秒；审查独立性仍标 weak。', '', '证据：`oracle-ce-results-v1.json` 与 `ce-oracle-fixed-ce-v1-raw-audit.json`；原始记录留在冻结远端目录，摘要哈希绑定审计。']
(BASE/'oracle-ce-results-v1.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(result['primary'],indent=2))
