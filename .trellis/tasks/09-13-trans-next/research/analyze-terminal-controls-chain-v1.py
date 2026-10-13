"""Summarize already harvested, audited chain evidence; no simulation."""
import hashlib
import json
from pathlib import Path
import statistics
import sys


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(tag):
    m = Path('.mission/20260913_00-48-38-afdm-trans-next')
    e = m/'evidence/exact-harvest-v1'
    c = json.loads((e/'contracts'/(tag+'.json')).read_text())
    path = e/'runs'/tag/c['stage']/'summary.json'
    s = json.loads(path.read_text())
    audit_path = e/'evidence'/(tag+'-raw-audit.json')
    a = json.loads(audit_path.read_text())
    end = json.loads((e/'evidence'/(tag+'-exit.json')).read_text())
    assert s['status'] == 'COMPLETE' and a['status'] == 'PASS'
    assert end['exit_code'] == 0 and not end['timed_out']
    assert a['summary_sha256'] == sha(path)
    assert s['raw_checks'] == {k: a[k] for k in ('rows', 'arrays', 'saved_records')}
    assert a['contract_sha256'] == sha(e/'contracts'/(tag+'.json'))
    old = json.loads((e/'runs/retained-chain-development-v1/development/summary.json').read_text())
    old_index = {(r['block'], r['snr'], r['arm']): r for r in old['records']}
    records = {(r['block'], r['snr'], r['arm']): r for r in s['records'] if r['kind'] == 'F'}
    aggregates = []
    for snr in c['snrs']:
        for arm in c['arms']:
            rows = [r for r in a['rows'] if r['snr'] == snr and r['arm'] == arm]
            assert len(rows) == len(c['blocks'])
            compare = 'BP_RETAIN_STOP' if 'STOP' in arm else 'BP_RETAIN'
            old_fail = {b for b in c['blocks'] if old_index[b, snr, compare]['scores']['FER']}
            failed = {r['block'] for r in rows if r['scores']['FER']}
            counts = {k: sum(r['resources'][k] for r in rows) for k in rows[0]['resources']}
            valid_stops = [r for r in rows if r.get('terminal_executed') is False]
            aggregates.append(dict(snr=snr, arm=arm, n=len(rows), failed_blocks=sorted(failed),
                info_bit_errors=sum(r['scores']['coded_bit_errors'] for r in rows),
                rescued_vs_old=sorted(old_fail-failed), new_failures_vs_old=sorted(failed-old_fail),
                early_stops=len(valid_stops), wrong_valid_stops=sum(r['scores']['FER'] for r in valid_stops),
                actual_resources=counts, mean_NLL=statistics.mean(r['scores']['bit_NLL'] for r in rows),
                instrumented_full_seconds=statistics.mean(records[r['block'],snr,arm]['seconds'] for r in rows)))
    result = dict(status='PASS', tag=tag, calls=s['calls'], raw_records=a['saved_records'], arrays=a['arrays'],
        run_seconds=end['wall_seconds'], raw_audit_seconds=a['wall_seconds'], aggregates=aggregates,
        source_sha256=s['source_sha256'], script_sha256=s['script_sha256'], summary_sha256=sha(path),
        raw_audit_sha256=sha(audit_path), contract_sha256=a['contract_sha256'], scope=c['scope'],
        limitations='Same old development blocks. Ordinary classical controls; no new method, CONF, formal COST, G1 or cross-scene claim. Self-review independence weak.')
    if 'recovered_calls' in s:
        result.update(new_calls=s['new_calls'], recovered_calls=s['recovered_calls'],
            preserved_failed_attempts=s['preserved_failed_attempts'], original_batch_status=s['original_batch_status'])
        original_exit = e/'evidence/terminal-controls-development-v1-exit.json'
        result['original_failed_batch_seconds'] = json.loads(original_exit.read_text())['wall_seconds']
        result['run_seconds_scope'] = 'Recovery only; original failed batch time is reported separately, not discarded.'
    out = Path('.trellis/tasks/09-13-trans-next/research')/(tag+'-results.json')
    with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main(sys.argv[1])
