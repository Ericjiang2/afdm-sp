"""Replay 20 archived baseline keys, count subgroup leverage, and project cost."""

import argparse
from collections import Counter
from itertools import product
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import mean
import sys
import time

from budget_receiver import ARMS, SWEEP, archives, context, run_key, stage3, sweep

ARCHIVE = SWEEP / 'out/main_20261119'
ROWS_SHA = '75912eae581034d22878e68b68a0f84aff0d6414f62b332058307bc86663307e'
CONFIG_SHA = '62eb3602a39217bcda4ff89f0241c6ea14227d3c051837e0d366f247dd395c9b'
ARCHIVE_FRAMES = range(5400, 5800)
RHO = (150, 200, 300)
SNR = (300, 400, 450, 500, 550, 600, 650, 700, 800, 1000)
CELL = tuple(product(('U', 'G'), RHO))
BRANCHES = {'CD2': 'CD', 'A2-2': 'A2'}
PRIMARY_SNR = (600, 650, 700, 800)
THREADS = (*sweep.THREADS, 'CUDA_VISIBLE_DEVICES')


def archive_rows(config):
    frozen = config['_config']
    expected = set(product(frozen['scenarios'], frozen['rhos'], frozen['snrs'], ARCHIVE_FRAMES))
    keep, seen = {}, set()
    manifest = ARCHIVE / 'ROWS_SHA256.txt'
    archives.verify(manifest, ROWS_SHA)
    for record in manifest.read_text().splitlines():
        digest, filename = record.split()
        path = ARCHIVE / filename
        archives.verify(path, digest)
        for row in archives.read_rows(path):
            key = archives.key(row)
            if (key not in expected or key in seen or row['snapshot_sha256'] != frozen['snapshot_sha256']
                    or row['triggered'] != bool(row['syndrome'])
                    or set(row['arms']) != {'F0', 'CD', 'A2'}):
                raise archives.FrozenEvidenceError(f'Unexpected archive row {key}')
            seen.add(key)
            if key[:2] in CELL and key[2] in SNR:
                keep[key] = row
    if seen != expected:
        raise archives.FrozenEvidenceError('Incomplete rho-sweep archive')
    return keep


def miss_bounds(row):
    """Recover unchanged entering slots from both baseline arm traces.

    Local refinement changes Dopplers only. A slot edited by both arms may
    have lost its entering delay. Use saved paired candidates as extra bounds.
    """
    cd, a2 = (row['arms'][name] for name in ('CD', 'A2'))
    cd_edits, a2_edits = ({edit[0] for _, edit in arm['decision'] if edit is not None}
                           for arm in (cd, a2))
    known = set()
    for slot, (cd_path, a2_path) in enumerate(zip(cd['state']['paths'], a2['state']['paths'], strict=True)):
        if slot not in cd_edits and slot not in a2_edits and cd_path[0] != a2_path[0]:
            raise archives.FrozenEvidenceError('Archived unchanged paths disagree')
        if slot not in cd_edits:
            known.add(cd_path[0])
        if slot not in a2_edits:
            known.add(a2_path[0])
    unknown_slots = cd_edits & a2_edits
    true_delays = set(row['truth']['delays'])
    known_missing = set()
    for name, arm in (('CD', cd), ('A2', a2)):
        first = arm['decision'][0][1]
        if first is None:
            continue
        slot, new = first
        incoming = new['delay']
        label = row['mechanism']['first_edit'][name]
        if label == 'true_delay':
            known_missing.add(incoming)
        elif label == 'phantom':
            known.add(incoming)
        elif label == 'other' and incoming in true_delays:
            # A true delay with neither of the earlier labels was
            # already present in the slot the first edit replaced.
            known.add(incoming)
            unknown_slots.discard(slot)
    if pair := row['mechanism']['paired_candidates']:
        known.add(pair['phantom']['delay'])
        known_missing.add(pair['true_delay']['delay'])
    if not known_missing <= true_delays or known_missing & known:
        raise archives.FrozenEvidenceError('Archived candidate and support labels disagree')
    missing_without_unknown_slots = len(true_delays - known)
    return max(len(known_missing), missing_without_unknown_slots - len(unknown_slots)), missing_without_unknown_slots


def calibration(rows):
    result = {}
    for rho in (150, 300):
        counts = Counter()
        bounds = Counter()
        for (scenario, fraction, snr, _), row in rows.items():
            if fraction != rho or snr not in PRIMARY_SNR or not row['triggered']:
                continue
            counts['triggered'] += 1
            if not row['arms']['CD']['errors']:
                continue
            counts['cd2_failed'] += 1
            lower, upper = miss_bounds(row)
            bounds[f'{lower}:{upper}'] += 1
            counts['exactly_identified'] += lower == upper
            counts['definitely_eligible'] += 3 <= lower <= upper <= 4
            counts['possibly_eligible'] += lower <= 4 and upper >= 3
        result[rho] = {name: counts[name] for name in (
            'triggered', 'cd2_failed', 'exactly_identified', 'definitely_eligible', 'possibly_eligible',
        )} | dict(missed_delay_bounds=dict(sorted(bounds.items())))
    return result


def gate_keys(rows):
    # Fix selection before replay: each cell covers two triggered SNRs and one
    # bypass; both low-rho scenarios add a middle/high SNR trigger.
    keys = []
    for scenario, rho in CELL:
        for snr, triggered in ((300, True), (600, True), (1000, False)):
            keys.append(min(key for key, row in rows.items()
                            if key[:3] == (scenario, rho, snr) and row['triggered'] == triggered))
        if rho == 150:
            keys.append(min(key for key, row in rows.items()
                            if key[:3] == (scenario, rho, 800) and row['triggered']))
    if len(set(keys)) != 20:
        raise AssertionError('Expected 20 distinct archived gate keys')
    return keys


def gates(ctx, kernels, old):
    cases = []
    for key in gate_keys(old):
        if key[-1] not in ARCHIVE_FRAMES:
            raise AssertionError(f'Phase 1 may only generate archived gate keys: {key}')
        scenario, rho, _, frame = key
        begin = time.process_time()
        base = stage3.inputs(ctx, frame, scenario, rho)
        base_cpu = time.process_time() - begin
        timing = {}
        live = run_key(ctx, kernels, base, key, gate_timing=timing)
        ref = old[key]
        for field in ('syndrome', 'triggered', 'truth', 'inputs'):
            if ref[field] != live[field]:
                raise archives.FrozenEvidenceError(f'{key}: observed {field} differs from rho sweep')
        for name, source in {'F0': 'F0', **BRANCHES}.items():
            compared = {k: live['arms'][name][k] for k in ref['arms'][source]}
            if ref['arms'][source] != compared:
                raise AssertionError(f'{key}: {name} disagrees with immutable {source} archive')
        if ref['triggered']:
            low, high = miss_bounds(ref)
            if not low <= len(live['missed_true_delays']) <= high:
                raise AssertionError(f'{key}: exact entering misses outside archive bounds')
        cases.append(dict(key=key, base_cpu_seconds=base_cpu, branches_cpu=timing, row=live))
    return cases


def project(rows, cases):
    # Each extra branch pays its CPU-measured geometry time plus the same
    # covariance arm's measured budget-2 wrapper/detector/decoder residual.
    # Reweight capped/early-stop samples to their observed archived frequencies.
    rates = {}
    for arm, larger_budgets in (('CD2', (4, 6)), ('A2-2', (6,))):
        for budget in larger_budgets:
            for capped in (False, True):
                samples = [case['branches_cpu'][arm] for case in cases if case['branches_cpu']
                           and (len(case['row']['arms'][arm]['accepted_edits']) == 2) == capped]
                if not samples:
                    raise ValueError(f'No gate cost samples for {arm}, capped={capped}')
                rates[arm, budget, capped] = dict(samples=len(samples), cpu_seconds=mean(
                    sample['non_geometry_cpu_seconds']
                    + sample['extended_geometry'][budget]['cpu_seconds'] for sample in samples))
    totals = {}
    for key, row in rows.items():
        cell = '/'.join(map(str, key[:3]))
        cell_total = totals.setdefault(cell, dict(baseline_cpu_seconds=0., extra_cpu_seconds=0.,
                                                  keys=0, triggers=0))
        cell_total['keys'] += 1
        cell_total['baseline_cpu_seconds'] += row['cpu_seconds']
        if row['triggered']:
            cell_total['triggers'] += 1
            for arm, source in BRANCHES.items():
                capped = sum(edit is not None for _, edit in row['arms'][source]['decision']) == 2
                cell_total['extra_cpu_seconds'] += sum(
                    rates[arm, budget, capped]['cpu_seconds'] for budget in (4, 6)
                    if (arm, budget, capped) in rates)
    base_generation = mean(case['base_cpu_seconds'] for case in cases) * len(CELL) * len(ARCHIVE_FRAMES)
    baseline = sum(cell['baseline_cpu_seconds'] for cell in totals.values())
    extra = sum(cell['extra_cpu_seconds'] for cell in totals.values())
    estimate = 1.3 * (baseline + extra + base_generation) / 3600
    return dict(keys=len(rows), triggers=sum(cell['triggers'] for cell in totals.values()),
                baseline_cpu_seconds=baseline, extra_cpu_seconds=extra,
                base_generation_cpu_seconds=base_generation, multiplier=1.3,
                projected_core_hours=estimate, cap_core_hours=6,
                cap_result='PASS' if estimate <= 6 else 'STOP',
                branch_rates={'/'.join(map(str, key)): values for key, values in rates.items()},
                cells=totals)


def qualified_inputs():
    if any(os.environ.get(name) != '1' for name in sweep.THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Phase 1 requires a single numerical thread and CPU only')
    archives.verify(ARCHIVE / 'config.json', CONFIG_SHA)
    config = json.loads((ARCHIVE / 'config.json').read_text())
    frozen = config['_config']
    pins = frozen['qualified_sources']
    for name, digest in (
        (SWEEP / 'phase1.py', frozen['source_sha256']['phase1.py']),
        *((SWEEP.parent / name, digest) for name, digest in archives.STAGE3_FILES.items()),
        *((SWEEP.parent / 'unified_cov_prospective_20261119' / name, digest)
          for name, digest in sweep.UNIFIED_SOURCES.items()),
    ):
        archives.verify(name, digest)
    ctx, kernels, sources = context()
    for name, check in sources.items():
        if check['actual'] != pins['context'][name]['actual']:
            raise archives.FrozenEvidenceError(f'Receiver dependency changed at {name}')
    for name in ('python', 'machine', 'numpy', 'scipy', 'torch'):
        if ctx.environment[name] != pins['environment'][name]:
            raise archives.FrozenEvidenceError(f'Receiver environment changed at {name}')
    rows = archive_rows(config)
    common = dict(_argv=sys.argv, _config=dict(archive=str(ARCHIVE), rows_manifest_sha256=ROWS_SHA,
                 archive_config_sha256=CONFIG_SHA, readout_rhos=RHO, readout_snr=SNR, arms=ARMS,
                 threads={name: os.environ[name] for name in THREADS}, archive_frames=[5400, 5799],
                 code_sha256={name: sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                              for name in ('budget_receiver.py', 'qualify.py')}))
    return ctx, kernels, sources, rows, common


def main(out):
    ctx, kernels, sources, rows, common = qualified_inputs()
    stage3.write_json(out / 'calibration.json', common | dict(by_rho=calibration(rows)))
    cases = gates(ctx, kernels, rows)
    for arm, budget in (('CD2', 4), ('CD2', 6), ('A2-2', 6)):
        if not any(case['branches_cpu'][arm]['extended_geometry'][budget]['steps'] > 2
                   for case in cases if case['branches_cpu']):
            raise AssertionError(f'Gate did not exercise the extended search for {arm}/{budget}')
    stage3.write_json(out / 'gates.json', common | dict(passed=True, cases=cases,
                                                      sources=sources, environment=ctx.environment))
    stage3.write_json(out / 'cost.json', common | project(rows, cases))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.out)
