"""A-transfer archive reader. Target prelabel path projects only audited keys."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

OLD = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
CODE = 'bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'
NUMERIC = ('native_twofft', 'receiver', 'dpss_rx.py', 'tapchannel.py', 'physical', 'messages', 'interventions')
META = frozenset(('status', 'frame', 'arm', 'snr_centi_db', 'rho_permille', 'L', 'K', 'n_cols', 'sigma2',
                  'R', 'rounds', 'T', 'schedule', 'inner_iters', 'info_sha256', 'noise_sha256',
                  'physical_gains_sha256', 'channel_seed', 'tap_delays', 'syn1', 'dsha1'))


def digest(path):
    h = hashlib.md5()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _space(s, i):
    while i < len(s) and s[i] in ' \t\r\n':
        i += 1
    return i


def _string_end(s, i):
    if s[i] != '"':
        raise ValueError('expected JSON string')
    i += 1
    while i < len(s):
        if s[i] == '\\':
            i += 2
        elif s[i] == '"':
            return i + 1
        else:
            i += 1
    raise ValueError('unterminated JSON string')


def _value_end(s, i):
    i = _space(s, i)
    if i >= len(s):
        raise ValueError('missing JSON value')
    if s[i] == '"':
        return _string_end(s, i)
    if s[i] in '[{':
        stack = [']' if s[i] == '[' else '}']
        i += 1
        while i < len(s) and stack:
            c = s[i]
            if c == '"':
                i = _string_end(s, i)
                continue
            if c in '[{':
                stack.append(']' if c == '[' else '}')
            elif c in ']}':
                if stack.pop() != c:
                    raise ValueError('malformed JSON nesting')
            i += 1
        if stack:
            raise ValueError('unterminated JSON value')
        return i
    while i < len(s) and s[i] not in ',}] \t\r\n':
        i += 1
    return i


def project(line, allowed=META):
    """Decode named top-level fields; opaque values are scanned, never deserialized."""
    s = line.decode('utf-8') if isinstance(line, bytes) else line
    i = _space(s, 0)
    if i >= len(s) or s[i] != '{':
        raise ValueError('row must be JSON object')
    i += 1
    result = {}
    while True:
        i = _space(s, i)
        if i >= len(s):
            raise ValueError('unterminated row')
        if s[i] == '}':
            if s[_space(s, i + 1):].strip():
                raise ValueError('trailing JSON data')
            return result
        end = _string_end(s, i)
        key = json.loads(s[i:end])
        i = _space(s, end)
        if i >= len(s) or s[i] != ':':
            raise ValueError('missing colon')
        i = _space(s, i + 1)
        end = _value_end(s, i)
        if key in allowed:
            if key in result:
                raise ValueError(f'duplicate projected key {key}')
            result[key] = json.loads(s[i:end])
        i = _space(s, end)
        if i >= len(s):
            raise ValueError('unterminated row')
        if s[i] == ',':
            i += 1
        elif s[i] == '}':
            if s[_space(s, i + 1):].strip():
                raise ValueError('trailing JSON data')
            return result
        else:
            raise ValueError('malformed row separator')


def shard_files(directory):
    directory = Path(directory)
    names = {}
    for p in sorted(directory.glob('rows_shard*.jsonl*')):
        if not (p.name.endswith('.jsonl') or p.name.endswith('.jsonl.gz')):
            continue
        stem = p.name.removeprefix('rows_').removesuffix('.gz').removesuffix('.jsonl')
        names.setdefault(stem, []).append(p)
    if not names:
        raise ValueError(f'no rows in {directory}')
    ledger = directory / 'REMOTE_ROWS_MD5.txt'
    if not ledger.is_file():
        raise ValueError(f'missing uncompressed digest ledger {ledger}')
    reference = {}
    for line in ledger.read_text().splitlines():
        fields = line.split()
        if len(fields) != 2 or len(fields[0]) != 32:
            raise ValueError(f'invalid digest ledger {ledger}')
        key = Path(fields[1].lstrip('*')).name.removesuffix('.gz')
        if key in reference:
            raise ValueError(f'duplicate digest ledger entry {key}')
        reference[key] = fields[0]
    result = []
    for stem, variants in sorted(names.items()):
        cp = directory / f'config_{stem}.json'
        if not cp.is_file():
            raise ValueError(f'missing {cp}')
        md5s = {}
        for path in variants:
            compressed = digest(path)
            raw = hashlib.md5()
            opener = gzip.open if path.suffix == '.gz' else open
            with opener(path, 'rb') as stream:
                for line in stream:
                    raw.update(line)
            md5s[str(path)] = {'compressed_md5': compressed, 'uncompressed_md5': raw.hexdigest()}
        if len({v['uncompressed_md5'] for v in md5s.values()}) != 1:
            raise ValueError(f'conflicting plain/gzip shard {stem}')
        raw_name = f'rows_{stem}.jsonl'
        if reference.get(raw_name) != next(iter(md5s.values()))['uncompressed_md5']:
            raise ValueError(f'archive digest mismatch {directory}/{raw_name}')
        selected = next((p for p in variants if p.suffix == '.gz'), variants[0])
        result.append((selected, cp, md5s))
    return result


def rows(path, mode='prelabel'):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f'blank row {path}:{number}')
            meta = project(line)
            if mode == 'prelabel':
                yield number, meta
            elif mode == 'source':
                yield number, meta, line
            elif mode == 'evaluate':
                yield number, meta, line
            else:
                raise ValueError(mode)


def validate_context(configs):
    common = {}
    for path, doc in configs:
        c = doc['_config']
        if c['entropy_hex'] != OLD or c['code_g_sha256'] != CODE:
            raise ValueError(f'entropy/code mismatch {path}')
        keys = ['m2_config_sha256', 'checkpoint_sha256', 'code_g_sha256', 'sp_cfg', 'dpss_defaults']
        values = {k: c[k] for k in keys if k != 'sp_cfg'}
        values['sp_cfg'] = c['sp_cfg'] if 'sp_cfg' in c else c['sp_cfgs']['SPg_flat']
        if values['sp_cfg'] != dict(mode='full', kappa=1.0, drop=0.0):
            raise ValueError(f'wrong fixed full receiver {path}')
        values['numeric_sha256'] = {k: c['source_sha256'][k] for k in NUMERIC}
        if not common:
            common = values
        elif values != common:
            raise ValueError(f'context mismatch {path}')
    return common


def validate_row(meta, expected, max_rounds):
    for key in ('status', 'frame', 'arm', 'snr_centi_db', 'rho_permille', 'L', 'K', 'sigma2',
                'info_sha256', 'noise_sha256', 'physical_gains_sha256', 'channel_seed', 'syn1', 'dsha1'):
        if key not in meta:
            raise ValueError(f'missing row field {key}')
    if meta['status'] != 'ok':
        raise ValueError(f'error row: {expected}')
    if (meta['snr_centi_db'], meta['rho_permille'], meta['L']) != expected[:3]:
        raise ValueError(f'cell mismatch: {expected}')
    if meta['arm'] != expected[3]:
        raise ValueError(f'arm mismatch: {expected}')
    L = meta['L']
    if meta['K'] != 8 * L or ('n_cols' in meta and meta['n_cols'] != 8 * L):
        raise ValueError(f'K/columns mismatch: {expected}')
    if not 0 <= meta['syn1'] <= 1026 or not isinstance(meta['dsha1'], str) or len(meta['dsha1']) != 64:
        raise ValueError(f'invalid prefix: {expected}')
    sigma = 10 ** (-meta['snr_centi_db'] / 1000)
    if abs(meta['sigma2'] / sigma - 1) > 1e-9:
        raise ValueError(f'raw sigma mismatch: {expected}')
    arm = meta['arm']
    T = 20 if arm in ('E10', 'FULL_R10', 'FULL_R4') or arm.endswith('T20') else 40
    if arm.startswith('E'):
        if meta.get('R') != 10 or meta.get('schedule') != [T] * 10:
            raise ValueError(f'wrong SOURCE schedule: {expected}')
    elif meta.get('R', max_rounds) != max_rounds:
        raise ValueError(f'wrong R: {expected}')
    if 'T' in meta and meta['T'] != T:
        raise ValueError(f'wrong T: {expected}')
    if 'rounds' in meta and meta['rounds'] != max_rounds:
        raise ValueError(f'wrong rounds: {expected}')
    if 'inner_iters' in meta and meta['inner_iters'] != [T] * max_rounds:
        raise ValueError(f'wrong inner iterations: {expected}')
    return T
