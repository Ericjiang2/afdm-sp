"""Read-only actual-file/ledger verification after the complete raw audit."""
import argparse
import hashlib
import json
from pathlib import Path

ARMS = ('I0', 'Irealloc', 'Isham', 'I1', 'I2', 'I2realloc')
RANGES = [(0, 1), (1, 17), (17, 33)] + [(a, min(a + 16, 192)) for a in range(33, 192, 16)]


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root, audit_path):
    root = root.resolve()
    audit = read(audit_path)
    require(audit['status'] == 'passed' and audit['F_audited'] == 3456 and
            len(audit['batches']) == 13, 'complete raw audit required')
    source = root / 'source-i01-development-v1/source/afdm_sp_joint_unrolled'
    bindings = audit['bindings']
    actual_sources = {str(p.relative_to(source)): sha(p) for p in source.rglob('*.py')}
    require(len(actual_sources) == 228 and actual_sources == bindings['source_sha256'],
            'actual source files differ from audited source bindings')
    ledger = root / 'i01-development-inputs-v1/i01-development-ledger'
    expected_roots = {root / f'i01-development-b{a:03d}-{b:03d}-v1' for a, b in RANGES}
    require({Path(b['root']).resolve() for b in audit['batches']} == expected_roots,
            'audited batch root inventory differs')
    identities = set()
    reservations = set()
    proofs = []
    for batch in audit['batches']:
        path = Path(batch['root']).resolve()
        require(sha(path / 'contract.json') == batch['contract_sha256'] and
                sha(path / 'summary.json') == batch['summary_sha256'], 'batch files changed after audit')
        contract = read(path / 'contract.json')
        require(contract['bindings'] == bindings and contract['code_sha256'] == audit['code_sha256'],
                'contract bindings differ')
        require((contract['start'], contract['stop']) in RANGES, 'unexpected batch range')
        expected = {(b, s, a) for b in range(contract['start'], contract['stop'])
                    for s in (7, 8, 9) for a in ARMS}
        ids = [tuple(i) for i in contract['identities']]
        require(len(ids) == len(expected) and set(ids) == expected and not identities.intersection(ids),
                'reservation identity mismatch or overlap')
        require(contract['calls_reserved'] == {'E': 0, 'F': len(ids), 'T': 0}
                and contract['max_full_calls'] == len(ids), 'reserved budget mismatch')
        raw_ids = [tuple(p['identity']) for p in batch['proofs']]
        require(batch['F_audited'] == len(expected) and len(raw_ids) == len(expected)
                and set(raw_ids) == expected, 'raw audit proof identities differ from batch contract')
        identities.update(ids)
        require(Path(contract['ledger']).resolve() == ledger, 'unexpected shared ledger')
        reservation = ledger / ('reservation-' + contract['config_sha256'] + '.json')
        require(read(reservation) == {k: v for k, v in contract.items() if k != 'ledger'},
                'actual reservation differs from contract')
        reservations.add(reservation)
        command = contract['command']
        inputs = {}
        for key, flag in [('protocol', '--protocol'), ('development_protocol', '--development-protocol'),
                          ('quote', '--quote'), ('checkpoint', '--checkpoint')]:
            require(command.count(flag) == 1, 'missing/duplicate input flag')
            file = Path(command[command.index(flag) + 1])
            require(sha(file) == bindings['files'][key], 'actual input file changed: ' + key)
            inputs[key] = str(file)
        require((root / (path.name + '.exit')).read_text().strip() == '0', 'batch exit is not successful')
        require(not list(path.glob('*failure*.json')), 'failure artifact exists')
        proofs.append(dict(root=str(path), reservation_sha256=sha(reservation), inputs=inputs,
                           F=len(ids), contract_sha256=sha(path / 'contract.json')))
    require(set(ledger.glob('reservation-*.json')) == reservations, 'extra or missing ledger reservation')
    require(identities == {(b, s, a) for b in range(192) for s in (7, 8, 9) for a in ARMS},
            'whole-design identity mismatch')
    return dict(status='passed', actual_source_files=228, input_files_per_batch=4,
                reservations=13, unique_F=3456, raw_audit_sha256=sha(audit_path), batches=proofs,
                scope='actual source/input/ledger/exit verification; complements raw terminal audit; no receiver calls')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root, args.audit)
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result['status'], F=result['unique_F'], sha256=sha(args.out))))

if __name__ == '__main__':
    main()
