"""Recount saved LLR replay summaries against the separate raw-audit receipt.

This does not repeat decoding or replace the remote raw-array audit. All rows
are development diagnostics; scales selected here are not independent claims.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(row):
    return row['block'], row['snr'], row['arm'], row['beta']


def analyze(root, contract_path):
    contract = json.loads(contract_path.read_text())
    fingerprints = {str(contract_path): digest(contract_path)}
    stages = {}
    for stage in ('engineering', 'development'):
        summary_path = root / 'runs/llr-v1' / stage / 'summary.json'
        audit_path = root / 'evidence' / f'llr-{stage}-audit.json'
        exit_path = root / 'evidence' / f'llr-{stage}-v1-exit.json'
        source_path = root / 'source-llr-v1/source-manifest.json'
        for path in (summary_path, audit_path, exit_path, source_path):
            fingerprints[str(path)] = digest(path)
        summary = json.loads(summary_path.read_text())
        audit = json.loads(audit_path.read_text())
        exit_receipt = json.loads(exit_path.read_text())
        blocks = contract[stage + '_blocks']
        expected = set(itertools.product(range(blocks), contract['snrs'],
                                         contract['arms'], contract['betas']))
        if summary['status'] != 'COMPLETE' or audit['status'] != 'PASS':
            raise ValueError(f'{stage}: incomplete run or failed audit')
        if exit_receipt['exit_code'] != 0 or exit_receipt['timed_out']:
            raise ValueError(f'{stage}: invalid process exit')
        if (summary['contract_sha256'] != digest(contract_path)
                or audit['contract_sha256'] != digest(contract_path)
                or audit['summary_sha256'] != digest(summary_path)
                or summary['source_manifest_sha256'] != digest(source_path)):
            raise ValueError(f'{stage}: input binding mismatch')
        if summary['calls'] != {'D': len(expected), 'F': 0, 'T': 0}:
            raise ValueError(f'{stage}: call inventory differs')
        indexed = {key(r): r for r in summary['records']}
        audited = {key(r): r for r in audit['rows']}
        if (set(indexed) != expected or set(audited) != expected
                or len(indexed) != len(summary['records'])
                or len(audited) != len(audit['rows'])):
            raise ValueError(f'{stage}: duplicate or missing observation')
        if summary['beta_one_exact_replays'] != blocks * len(contract['snrs']) * len(contract['arms']):
            raise ValueError(f'{stage}: beta-one replay count differs')
        for identity, item in indexed.items():
            score, row = item['scores'], audited[identity]
            mapping = {'FER': 'FER', 'info_bit_errors': 'info_bit_errors',
                       'raw_bit_errors': 'raw_bit_errors', 'decode_ok': 'decode_ok',
                       'bit_NLL': 'NLL', 'bit_Brier': 'Brier'}
            if any(score[s] != row[a] for s, a in mapping.items()):
                raise ValueError(f'{stage}: score disagrees with audit at {identity}')
            if score['FER'] not in (0, 1) or not all(math.isfinite(score[s]) for s in ('bit_NLL', 'bit_Brier')):
                raise ValueError(f'{stage}: invalid score')
        table_lookup = {(t['snr'], t['arm'], t['beta']): t for t in audit['tables']}
        if len(table_lookup) != len(contract['snrs']) * len(contract['arms']) * len(contract['betas']):
            raise ValueError(f'{stage}: missing audit table')
        tables = []
        for snr, arm, beta in itertools.product(contract['snrs'], contract['arms'], contract['betas']):
            rows = [audited[b, snr, arm, beta] for b in range(blocks)]
            base = [audited[b, snr, arm, 1.] for b in range(blocks)]
            rescued = [b for b in range(blocks) if base[b]['FER'] and not rows[b]['FER']]
            broken = [b for b in range(blocks) if not base[b]['FER'] and rows[b]['FER']]
            if any(rows[b]['raw_bit_errors'] != base[b]['raw_bit_errors'] for b in range(blocks)):
                raise ValueError('positive LLR scaling changed raw hard decisions')
            t = dict(snr=snr, arm=arm, beta=beta, blocks=blocks,
                     errors=sum(r['FER'] for r in rows),
                     info_errors=sum(r['info_bit_errors'] for r in rows),
                     rescued=len(rescued), broken=len(broken),
                     mean_NLL=statistics.fmean(r['NLL'] for r in rows))
            original = table_lookup[snr, arm, beta]
            if any(not math.isclose(t[k], original[k], rel_tol=1e-12, abs_tol=1e-12)
                   if isinstance(t[k], (float, int)) else t[k] != original[k] for k in t):
                raise ValueError('recomputed aggregate differs from raw auditor')
            t.update(mean_Brier=statistics.fmean(r['Brier'] for r in rows),
                     raw_bit_errors=sum(r['raw_bit_errors'] for r in rows),
                     rescue_blocks=rescued, broken_blocks=broken)
            tables.append(t)
        stages[stage] = dict(blocks=blocks, calls=summary['calls'],
                             wall_seconds=summary['wall_seconds'],
                             beta_one_exact_replays=summary['beta_one_exact_replays'],
                             prior_raw_audit_arrays=audit['arrays_audited'], tables=tables)
    return dict(status='PASS', input_sha256=fingerprints, stages=stages,
                evidence_scope='local complete score recount and artifact binding; remote raw audit received separately',
                scientific_scope='64 shared development blocks; all scales disclosed; no independent confirmation',
                new_calls={'D': 0, 'F': 0, 'T': 0}, analyst='main session; no independent reviewer')


def markdown(result):
    tables = result['stages']['development']['tables']
    lookup = {(t['snr'], t['arm'], t['beta']): t for t in tables}
    def errors(arm, beta=1., snr=7):
        return lookup[snr, arm, beta]['errors']
    i1_curve = [(t['beta'], t['errors']) for t in tables if t['snr'] == 7 and t['arm'] == 'I1']
    true_noise_min = min(t['errors'] for t in tables if t['snr'] == 7 and t['arm'] == 'BP_TRUE_NOISE')
    out = ['# LLR回放分析', '',
           '现有120次工程和3840次开发译码已收齐。原始审计记录为PASS；本次重新核对所有分数、配对身份、退出状态及输入哈希，60组汇总与审计表一致。没有新增译码或接收调用。', '',
           '7/8 dB共享64个独立开发块。救回/新增错误均相对同一终态的β=1；不是相对I1。以下是开发全曲线，不做事后赢家的确认性检验。', '',
           '|SNR|终态|β|错块/64|救回|新增|信息bit错|NLL|Brier|',
           '|---|---|---|---|---|---|---|---|---|']
    for t in tables:
        out.append(f"|{t['snr']}|{t['arm']}|{t['beta']:g}|{t['errors']}/64|{t['rescued']}|{t['broken']}|{t['info_errors']}|{t['mean_NLL']:.6f}|{t['mean_Brier']:.6f}|")
    out += ['', '## Interpretation and next discrimination', '',
            f'- I1在7 dB的预设(β,错块数)曲线为{i1_curve}；β=1错{errors("I1")}块。网格中的最小值仍仅是开发结果，不能排除更细、分帧或非线性校准。',
            f'- 真H＋热噪声BP：β=1错{errors("BP_TRUE_NOISE")}块，网格最少{true_noise_min}块；真H＋I1终端方差在β=1错{errors("BP_TRUE_BASE")}块。两种设置还需L04交叉控制，不能用末端校准代替内部推断诊断。',
            f'- 估计H＋热噪声BP在β=1.5错{errors("BP_EST_NOISE",1.5)}块，原I1错{errors("I1")}块。EP估计H在β=0.75错{errors("EP_EST_NOISE",.75)}块；EP未通过原稳定性资格，开发小差异不能作为晋级证据。',
            f'- β=0.5使I1在7/8 dB错块{errors("I1")}→{errors("I1",.5)}、{errors("I1",snr=8)}→{errors("I1",.5,8)}。置信度缩放的作用必须按工作点判断。',
            '- 正的β没有改变原始硬判；FER变化发生在有限LDPC译码。原缓存LLR已clip20，无法恢复截断前信息。I1终端BASE方差含历史0.5乘子。',
            '- 下一步核单位及真实软矩，随后做支撑/系数分解和内部方差×LLR测试；连续多普勒估计排除。', '',
            '验证范围：本地重算摘要与原始审计收据。此次没有再次读取远端全部NPZ，也没有独立审查代理。源文件哈希、各块救回/新增列表见同名JSON。', '']
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--json-output', type=Path, required=True)
    p.add_argument('--markdown-output', type=Path, required=True)
    args = p.parse_args()
    result = analyze(args.root, args.contract)
    result.update(_argv=sys.argv, _config={k: str(v) for k, v in vars(args).items()},
                  source_sha256=digest(__file__))
    with args.json_output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    with args.markdown_output.open('x') as f:
        f.write(markdown(result))
    print(json.dumps({k: result[k] for k in ('status', 'new_calls', 'evidence_scope')}))


if __name__ == '__main__':
    main()
