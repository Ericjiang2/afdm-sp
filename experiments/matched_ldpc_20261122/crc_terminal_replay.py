#!/usr/bin/env python3
"""Check a CRC-filtered weight-four repair on archived C1 terminal decisions."""
import argparse
from collections import defaultdict
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys
import time

import numpy as np

import forest_minimal as frozen
from analyze import crossing, json_bounds

POLYNOMIAL = 0x11021
PAYLOAD, TRAILER = 1008, 16
L16_DIGEST = 'a6b6f34262dbf1e092424a979521e81d7cd6a753da6e057224dea9bb44442a64'
CODE_MD5 = '601d12c9f2351a33ec6e429ff49fbb4f'


def remainder(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
        if value >= 1 << TRAILER:
            value ^= POLYNOMIAL
    return value


def short_supports(H):
    """Each degree-two column is an edge between two check vertices."""
    neighbors = [dict() for _ in range(H.shape[0])]
    for bit in np.flatnonzero(H.sum(axis=0) == 2):
        a, b = np.flatnonzero(H[:, bit]).tolist()
        if b in neighbors[a]:
            raise ValueError('parallel degree-two edges imply a weight-two word')
        neighbors[a][b] = neighbors[b][a] = int(bit)
    wedges = defaultdict(list)
    supports = set()
    for node, adjacent in enumerate(neighbors):
        for a, b in combinations(sorted(adjacent), 2):
            for other in wedges[(a, b)]:
                supports.add(tuple(sorted((adjacent[a], adjacent[b], neighbors[other][a], neighbors[other][b]))))
            wedges[(a, b)].append(node)
    if len(supports) != 281:
        raise ValueError('archived weight-four enumeration changed')
    return sorted(supports)


def load_archive():
    cells = {(28, snr): rows for snr, rows in frozen.old_rows().items()}
    manifest = hashlib.sha256()
    for part in sorted(frozen.ARCHIVE.glob('rows_L16_*_part*.jsonl')):
        blob = part.read_bytes()
        manifest.update(f'{hashlib.md5(blob).hexdigest()}  {part.name}\n'.encode())
        for row in map(json.loads, blob.splitlines()):
            framed = cells.setdefault((row['load'], row['snr_centi_db']), {})
            if row['load'] != 16 or row['frame'] in framed:
                raise ValueError('invalid archived L16 row')
            framed[row['frame']] = row
    if (manifest.hexdigest() != L16_DIGEST or
            set(cells) != {(28, snr) for snr in frozen.GRID} | {(16, snr) for snr in (650, 675, 700)} or
            any(set(rows) != set(frozen.FRAMES) for rows in cells.values())):
        raise ValueError('archived paired cohort differs from the published manifest')
    path = frozen.ARCHIVE / 'codes.npz'
    if hashlib.md5(path.read_bytes()).hexdigest() != CODE_MD5:
        raise ValueError('matched-code archive does not match its recorded digest')
    with np.load(path, allow_pickle=False) as arrays:
        H, G, free = [arrays[f'matched_{key}'] for key in ('H', 'G', 'free_cols')]
    return cells, H, G, free


def run():
    cells, H, G, free = load_archive()
    supports = short_supports(H)
    signatures = {}
    inverse = defaultdict(list)
    for support in supports:
        e = np.zeros(2048, dtype=np.uint8)
        e[list(support)] = 1
        if np.any(H @ e % 2):
            raise ValueError('support does not define a codeword')
        signatures[support] = remainder(e[free])
        inverse[signatures[support]].append(support)

    raw_mat = frozen.c1run.c1
    source = frozen.c1run.c1i
    cache = {}
    results = {}
    for (load, snr), rows in sorted(cells.items()):
        repaired, observed, collisions, missed_crc = [], [], [], []
        outcomes = dict(regular_errors=0, matched_errors=0, matched_only_errors=0,
                        matched_only_repaired=0, other_wrong_parity_valid=0)
        for frame, row in sorted(rows.items()):
            old, regular = row['arms']['matched'], row['arms']['regular']
            regular_error, old_error = frozen.error(regular), frozen.error(old)
            outcomes['regular_errors'] += int(regular_error)
            outcomes['matched_errors'] += int(old_error)
            outcomes['matched_only_errors'] += int(old_error and not regular_error)
            if not old_error or old['syndrome'] != 0:
                continue
            if old['coded_errors'] != 4:
                outcomes['other_wrong_parity_valid'] += 1
                continue
            if frame not in cache:
                info = raw_mat.c1_rng(source.C1_MAP_ENTROPY, frame, 0, raw_mat.C1_COMPONENTS['message'])
                info = info.integers(0, 2, size=1024).astype(np.uint8)
                word = G @ info % 2
                if not np.array_equal(word[free], info):
                    raise ValueError('regenerated systematic word is inconsistent')
                hashes = {}
                for support in supports:
                    trial = word.copy()
                    trial[list(support)] ^= 1
                    hashes[hashlib.sha256(trial.tobytes()).hexdigest()] = support
                coded = hashlib.sha256(str(word.dtype).encode() + str(word.shape).encode() + word.tobytes())
                cache[frame] = (word, coded.hexdigest(), hashlib.sha256(info.tobytes()).hexdigest(), hashes)
            word, coded_hash, info_hash, hashes = cache[frame]
            if (coded_hash, info_hash) != (old['coded_sha256'], row['info_sha256']):
                raise ValueError('the regenerated original word does not match the archive')
            support = hashes[old['round_decoded_sha256'][-1]]
            observed.append(frame)
            wrong = word.copy()
            wrong[list(support)] ^= 1
            residual = remainder(wrong[free]) ^ remainder(word[free])
            if residual != signatures[support]:
                raise ValueError('affine CRC remainder does not match support signature')
            if residual == 0:
                missed_crc.append(frame)
            elif len(inverse[residual]) != 1:
                collisions.append(frame)
            else:
                wrong[list(inverse[residual][0])] ^= 1
                if not np.array_equal(wrong, word):
                    raise ValueError('unique CRC support did not recover the archived word')
                repaired.append(frame)
                outcomes['matched_only_repaired'] += int(not regular_error)
        results[f'L{load}_{snr / 100:.2f}'] = dict(
            **outcomes, observed_w4=len(observed), certified_repairs=len(repaired), repaired_frames=repaired,
            undetected_w4=missed_crc, collision_w4=collisions,
            accounting_errors=outcomes['matched_errors']-len(repaired))

    snrs = np.asarray(frozen.GRID) / 100
    high = [results[f'L28_{snr:.2f}'] for snr in snrs]
    regular = crossing(snrs, np.array([row['regular_errors'] for row in high]) / 200, .1)
    corrected = crossing(snrs, np.array([row['accounting_errors'] for row in high]) / 200, .1)
    if regular != (8.4375, 8.4375):
        raise ValueError('regular FER reference changed')
    gain = frozen.difference(regular, corrected)
    tax = 10 * np.log10((PAYLOAD+TRAILER) / PAYLOAD)
    return dict(supports=[dict(indices=list(s), crc=signatures[s]) for s in supports],
                zero_signature_supports=len(inverse.get(0, ())),
                collision_buckets={hex(key): val for key, val in inverse.items() if len(val) > 1},
                observed_w4=sum(row['observed_w4'] for row in results.values()),
                certified_repairs=sum(row['certified_repairs'] for row in results.values()), cells=results,
                regular_10_db=json_bounds(regular), accounting_10_db=json_bounds(corrected),
                accounting_gain_10_db=json_bounds(gain), payload_energy_tax_db=float(tax),
                accounting_payload_gain_10_db=json_bounds([bound-tax for bound in gain]), receiver_calls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    frozen.c1run.set_cpu_limit(180)
    args.out.mkdir()
    result = dict(_argv=sys.argv, _config=dict(commit=args.commit, protocol='terminal affine CRC replay',
                  payload_bits=PAYLOAD, crc_bits=TRAILER, polynomial=hex(POLYNOMIAL),
                  code_md5=CODE_MD5, original_l28_rows_digest=frozen.ROWS_DIGEST, original_l16_rows_digest=L16_DIGEST))
    try:
        result.update(run(), status='DONE')
    except Exception as exc:
        result.update(status='STOPPED', reason=f'{type(exc).__name__}: {exc}')
    result['cpu_seconds'] = time.process_time()
    frozen.c1run.write_json(args.out / 'results.json', result)
    print(result['status'], result.get('reason', ''), result['cpu_seconds'], flush=True)
    if result['status'] != 'DONE':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
