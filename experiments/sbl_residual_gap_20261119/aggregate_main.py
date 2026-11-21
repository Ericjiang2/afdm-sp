"""Validate the complete paired frozen run and write its registered readout."""

import argparse
from hashlib import md5, sha256
import json
from math import isfinite
from pathlib import Path
import re
from statistics import mean
import sys

import verdict
import sampling
from launch_main import FREEZE, REASON, local_runners
from kprime import CAP_KIND, CENSUS_COUNTS, CENSUS_MEASURES, summarize_census


HERE = Path(__file__).resolve().parent
FROZEN_VERDICT_SHA256 = '02cac73df0999be625f3faa4884789294ce4dbe9dd2e9fa1de09583bc107727c'
FROZEN_SAMPLING_SHA256 = 'b27b70ef42c247b4dfc81d382131880c08ca630b3b9d675f67730946be9b97a3'
P1_ENTROPY = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
P1_DOMAIN = str(0x54435246)
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
RUN_ID_FIELDS = ('snapshot_sha256', 'producing_commit', 'freeze_commit', 'glue_commit')
ARM_LABEL = {'K': 'K′', 'KM': 'KM′'}


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def hex_digest(value, length=64):
    return isinstance(value, str) and re.fullmatch(rf'[0-9a-f]{{{length}}}', value) is not None


def count(value, minimum=0):
    return type(value) is int and value >= minimum


def finite(value):
    return type(value) in (float, int) and isfinite(value)


def verify_analysis_identity():
    dependencies = (
        (verdict, HERE / 'verdict.py', FROZEN_VERDICT_SHA256),
        (sampling, HERE.parent / 'tf_covariance_audit_20261018' / 'sampling.py', FROZEN_SAMPLING_SHA256),
    )
    for module, path, digest in dependencies:
        actual = Path(module.__file__).resolve()
        require(actual == path and sha256(actual.read_bytes()).hexdigest() == digest,
                f'Frozen analysis source mismatch: {actual}')
    return {path.name: digest for _, path, digest in dependencies}


def verify_pairing(row, key, fingerprints):
    scenario, rho, _, frame = key
    pair = row['pairing']
    common = tuple(pair[name] for name in ('info_sha256', 'coded_sha256', 'noise_sha256'))
    inputs = row['input_sha256']
    signal = (pair['physical_gains_sha256'], inputs['pilot'], inputs['data_true'])
    require(all(map(hex_digest, (*common, *signal))), f'Invalid exogenous hashes at {key}')
    for group, hashes in ((frame, common), ((scenario, rho, frame), signal)):
        require(fingerprints.setdefault(group, hashes) == hashes, f'Exogenous pairing changed at {key}')


def validate_row(row, key, fingerprints):
    variants = row['variants']
    require(row['family'] == 'P1' and tuple(row['key']) == key
            and tuple(row[name] for name in KEY_FIELDS) == key and set(variants) == set(verdict.ARMS)
            and row.get('status') not in ('error', 'failed') and 'error' not in row,
            f'Unexpected or failed receiver row at {key}')
    require(row['rng_entropy'] == P1_ENTROPY and row['rng_domain'] == P1_DOMAIN
            and finite(row['sigma2']) and row['sigma2'] > 0,
            f'P1 stream or noise variance mismatch at {key}')
    verify_pairing(row, key, fingerprints)

    for arm, score in variants.items():
        errors, fit = score['info_errors'], score['sbl']
        require(count(errors) and type(score['fer']) is int and score['fer'] == int(errors > 0)
                and hex_digest(score['decoded_sha256']) and finite(score['nmse']) and score['nmse'] >= 0
                and count(score['n_atoms'], 1) and len(score['atoms']) == score['n_atoms']
                and count(score['n_pair']) and len(score['pairs']) == score['n_pair']
                and fit['max_iter'] == 100 and count(fit['iterations'], 1) and fit['iterations'] <= 100
                and type(fit['converged']) is bool and finite(fit['beta']) and fit['beta'] > 0,
                f'Invalid FER, error count, NMSE, support or EM metrics at {key}/{arm}')
        state = score['sbl_state_sha256']
        require(set(state) == {'idx', 'gamma', 'mu'} and all(map(hex_digest, state.values()))
                and hex_digest(score['sbl_gain_sha256']) and len(score['atoms_ongrid']) == score['n_atoms'],
                f'Invalid EM state receipt at {key}/{arm}')
    for arm, source in (('M', 'U2'), ('KM', 'K')):
        fields = ('sbl', 'sbl_state_sha256', 'sbl_gain_sha256', 'atoms_ongrid')
        require(all(variants[arm][field] == variants[source][field] for field in fields),
                f'Shared EM changed at {key}/{source}/{arm}')

    psd, census = row['k_psd'], row['k_census']
    minimum, u, tolerance = psd['lambda_min'], psd['u'], psd['relative_tolerance']
    require(finite(minimum) and finite(u) and u >= 0 and u == row['sum_v']
            and tolerance == 1e-10 and minimum >= -tolerance * u and psd['cap_kind'] == CAP_KIND
            and psd['lambda_min_over_u'] == (minimum / u if u else None),
            f'Invalid full K covariance PSD receipt at {key}')
    total, within = census['removed_frobenius_squared'], census['removed_codelay_frobenius_squared']
    require(all(count(census[name]) for name in CENSUS_COUNTS)
            and all(finite(census[name]) and census[name] >= 0 for name in CENSUS_MEASURES)
            and census['eigenvalues_capped'] <= census['eigenvalues_total']
            and within <= total * (1 + 1e-12)
            and census['removed_codelay_share'] == (within / total if total else None)
            and census['eigenvalues_total'] == row['n_candidates_stage2'],
            f'Invalid K cap census at {key}')


def read_inputs(out, expected_keys):
    provenance = json.loads((out / 'config.json').read_text())
    cfg = provenance['_config']
    snapshot, producing, frozen, glue = (cfg[name] for name in RUN_ID_FIELDS)
    marker = f'Freeze commit {frozen}\nProducing commit {producing}\nGlue commit {glue}\nGlue reason {REASON}\n'
    require(hex_digest(snapshot) and frozen == producing == FREEZE and hex_digest(glue, 40)
            and cfg['glue_reason'] == REASON and (out / 'PRODUCING_COMMIT.txt').read_text() == marker,
            'Main producing commit, freeze commit or source snapshot mismatch')
    require(provenance['_argv'] and cfg['keys'] == len(expected_keys)
            and tuple(cfg['arms']) == verdict.ARMS and cfg['max_iter'] == 100
            and cfg['cap_kind'] == CAP_KIND and cfg['arm_labels'] == ARM_LABEL,
            'Main configuration does not match the frozen schedule')
    workers = cfg['workers']
    require(count(workers, 1) and workers <= 32, 'Invalid worker count in main configuration')
    manifest = (out / 'REMOTE_ROWS_MD5.txt').read_bytes()
    entries = [line.split() for line in manifest.decode('ascii').splitlines()]
    names = {name for _, name in entries}
    expected_files = {f'rows_shard{index:03d}.jsonl' for index in range(workers)}
    require(len(entries) == len(names) and names == expected_files == {p.name for p in out.glob('rows_shard*.jsonl')},
            'Main row manifest and shard inventory differ')

    rows, fingerprints = {}, {}
    for checksum, name in entries:
        blob = (out / name).read_bytes()
        require(md5(blob).hexdigest() == checksum, f'Row shard MD5 mismatch: {name}')
        for line in blob.splitlines():
            wrapper = json.loads(line)
            key, row = tuple(wrapper['key']), wrapper['row']
            require(key in expected_keys and key not in rows
                    and all(type(value) is int for value in key[1:])
                    and all(wrapper[field] == cfg[field] for field in RUN_ID_FIELDS),
                    f'Unexpected, duplicate or mixed-provenance row {key} in {name}')
            validate_row(row, key, fingerprints)
            rows[key] = row
    require(rows.keys() == expected_keys, f'Incomplete frozen key grid: {len(rows)}/{len(expected_keys)}')
    return [rows[key] for key in sorted(rows)], provenance, md5(manifest).hexdigest()


def summarize(rows):
    fer = {arm: [row['variants'][arm]['fer'] for row in rows] for arm in verdict.ARMS}
    result = verdict.readout(fer, [row['frame'] for row in rows])
    diagnostics = {}
    for arm in verdict.ARMS:
        scores = [row['variants'][arm] for row in rows]
        diagnostics[arm] = dict(
            failures=sum(fer[arm]), information_errors=sum(score['info_errors'] for score in scores),
            mean_nmse=mean(score['nmse'] for score in scores), mean_beta=mean(score['sbl']['beta'] for score in scores),
            mean_iterations=mean(score['sbl']['iterations'] for score in scores),
            convergence_rate=mean(score['sbl']['converged'] for score in scores),
            co_delay_pairs=sum(score['n_pair'] for score in scores),
            keys_with_co_delay_pairs=sum(score['n_pair'] > 0 for score in scores),
        )
    census = summarize_census([row['k_census'] for row in rows])
    psd = dict(keys_checked=len(rows), relative_tolerance=1e-10,
               min_lambda_over_u=min((row['k_psd']['lambda_min_over_u'] for row in rows
                                      if row['k_psd']['u'] > 0), default=None))
    return dict(**result, keys=len(rows), arm_diagnostics=diagnostics, K_census=census, K_psd=psd)


def estimate(stats, scale=1.0, digits=4):
    def display(value):
        return 'NA' if value is None else f'{scale * value:.{digits}f}'

    return f"{display(stats['point'])} [{display(stats['ci_lo'])}, {display(stats['ci_hi'])}]"


def markdown(result):
    gap, decision = result['gap'], result['verdict']
    cutoffs, ratios = result['cutoff_contrasts'], result['recovery']
    lines = [
        '# SBL residual gap — frozen main run', '',
        f"{result['keys']:,} keys in {result['n_frame_clusters']} physical frames. "
        f"Paired frame-cluster bootstrap with {result['bootstrap']['draws']:,} draws and seed {result['bootstrap']['seed']}.",
        '', '## Primary verdict', '',
        f"The gap G = FER(U2) − FER(R0) was {estimate(gap, 100)} pp (95% CI). "
        f"The premise {'passed' if decision['gap_established'] else 'failed'}.",
        f"Observed G was {'positive' if decision['premise_checks']['point_positive'] else 'nonpositive'}. "
        f"Its 95% lower bound was {'positive' if decision['premise_checks']['lower_bound_positive'] else 'nonpositive'}. "
        f"The share of draws with nonpositive denominators was {gap['denominator_nonpositive_fraction']:.3%} "
        f"({'within' if decision['premise_checks']['denominator_failure_within_limit'] else 'above'} the 1% limit).", '',
        '| Arm | Δ − .5G (pp, 97.5% CI) | Δ − .25G (pp, 97.5% CI) | κ (unclipped, 95% CI) | Discordant frames | Verdict |',
        '|---|---:|---:|---:|---:|---|',
    ]
    for arm in verdict.INTERVENTIONS:
        lines.append(f"| {ARM_LABEL.get(arm, arm)} | {estimate(cutoffs[arm]['half'], 100)} | {estimate(cutoffs[arm]['quarter'], 100)} "
                     f"| {estimate(ratios[arm])} | {result['discordant_frame_clusters'][arm]} | {decision['by_arm'][arm]} |")
    lines += ['', f"The joint verdict is **{decision['verdict']}**.",
              'The κ intervals use positive-denominator draws.', '', '## Secondary readouts', '',
              '| Arm | FER (%, 95% CI) | Failed keys | Information errors | Mean NMSE | Mean β | Mean EM iterations | Converged (%) | Co-delay pairs | Keys with pairs |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for arm, stats in result['arm_diagnostics'].items():
        lines.append(f"| {ARM_LABEL.get(arm, arm)} | {estimate(result['fer'][arm], 100)} | {stats['failures']} | {stats['information_errors']} "
                     f"| {stats['mean_nmse']:.6g} | {stats['mean_beta']:.6g} | {stats['mean_iterations']:.3f} "
                     f"| {100 * stats['convergence_rate']:.3f} | {stats['co_delay_pairs']} | {stats['keys_with_co_delay_pairs']} |")
    lines += ['', '| Paired contrast | FER difference (pp, 95% CI) |', '|---|---:|']
    for arm, stats in result['difference_vs_R0'].items():
        lines.append(f'| {ARM_LABEL.get(arm, arm)} − R0 | {estimate(stats, 100)} |')
    lines.append(f"| Cap × refinement interaction, (KM′ − M) − (K′ − U2) | {estimate(result['cap_by_refinement_interaction'], 100)} |")

    census, psd = result['K_census'], result['K_psd']
    lines += ['', '### K′ covariance census', '',
              f"K′ capped {census['eigenvalues_capped']:,} of {census['eigenvalues_total']:,} initial-grid eigenvalues.",
              f"Trace removed {census['trace_removed']:.6g}, exact trace {census['trace_exact']:.6g}, "
              f"and uncapped U2 trace {census['trace_u2']:.6g}."]
    for field, label in (('trace_removed_share_of_U2', 'Trace removed relative to uncapped U2 covariance'),
                         ('pooled_removed_codelay_share', 'Co-delay squared Frobenius share, pooled'),
                         ('median_per_key_removed_codelay_share', 'Co-delay squared Frobenius share, median across keys')):
        value = census[field]
        lines.append(f"- {label} — " + ('NA' if value is None else f'{value:.4%}') + '.')
    min_scaled = psd['min_lambda_over_u']
    lines += ['', f"Full K′ covariance PSD checks passed on {psd['keys_checked']:,} keys. "
              + ('' if min_scaled is None else f'Minimum λ_min / u was {min_scaled:.6g}.'), '',
              '## Provenance', '',
              f"Freeze commit `{result['_config']['freeze_commit']}` and "
              f"producing commit `{result['_config']['producing_commit']}`. "
              f"Launch glue `{result['_config']['glue_commit']}`.",
              f"Raw row manifest `REMOTE_ROWS_MD5.txt` (MD5 `{result['remote_rows_manifest_md5']}`).", '']
    return '\n'.join(lines)


def main():
    launcher, _ = local_runners()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    require(out == launcher.MAIN_OUT, 'Expected the registered main output directory')
    analysis_hashes = verify_analysis_identity()
    require(not any((out / name).exists() for name in ('results.json', 'RESULTS.md')),
            'Main output already contains an analysis result')
    rows, provenance, manifest_digest = read_inputs(out, launcher.MAIN_KEYS)
    result = dict(summarize(rows), **provenance, _aggregate_argv=sys.argv,
                  remote_rows_manifest_md5=manifest_digest, frozen_analysis_sha256=analysis_hashes)
    report = markdown(result)
    with launcher.publish(out / 'results.json') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    with launcher.publish(out / 'RESULTS.md') as handle:
        handle.write(report)
    print(f"Validated {len(rows)} complete paired rows and applied the frozen verdict.", flush=True)


if __name__ == '__main__':
    main()
