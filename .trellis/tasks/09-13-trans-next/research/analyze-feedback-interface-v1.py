"""Raw checkpoint interface diagnosis; no receiver or LDPC execution."""
import argparse
import importlib.util
import json
from pathlib import Path
import numpy as np
from afdm_sp_joint_unrolled.bottleneck_pilot import sha


def analyze(root):
    helper_path = Path(__file__).with_name('analyze-checkpoint-syndromes-v1.py')
    spec = importlib.util.spec_from_file_location('checkpoint_reader', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    path = root/'evidence/checkpoint-syndromes-v1.json'
    if sha(path) != '1bad89858eb0b3a4e403104b4d619a5f187f4b0541dfe3a43924b63f10cff14f':
        raise ValueError('changed preexisting checkpoint diagnosis')
    old = json.loads(path.read_text())
    expected = {(r['block'], r['snr'], r['arm']): r for r in old['rows']}
    rows = []
    for tag in ('refs-v1', 'siso-development-v1'):
        summary_path = root/'runs'/tag/'development/summary.json'
        if sha(summary_path) != old['bindings'][tag]['summary_sha256']:
            raise ValueError('changed reference summary')
        summary = json.loads(summary_path.read_text())
        for entry in summary['records']:
            key = entry['block'], entry['snr'], entry['arm']
            if key not in expected:
                continue
            previous = expected[key]
            if sha(entry['record']) != entry['sha256'] or entry['sha256'] != previous['record_sha256']:
                raise ValueError('changed raw record')
            record = json.loads(Path(entry['record']).read_text())
            value = helper.selected(record['state'], ['code_feedback_records'])
            prior_checks = {r['iteration']: r for r in previous['checkpoints']}
            for state in value['code_feedback_records']:
                if state['stage'] != 'decoder':
                    continue
                raw, channel, external = (state[k] for k in ('raw_app', 'channel_llr', 'raw_check_extrinsic'))
                np.testing.assert_array_equal(state['decoder_input'], channel)
                np.testing.assert_array_equal(raw, channel+external)
                np.testing.assert_array_equal(state['prior_after'], np.clip(external, -20, 20))
                delivered = channel+state['prior_after']
                hard = raw < 0
                sign = 1-2*hard.astype(float)
                prior = prior_checks[state['iteration']]
                rows.append(dict(block=key[0], snr=key[1], arm=key[2], iteration=state['iteration'],
                    checkpoint_valid=prior['unsatisfied_checks'] == 0,
                    offline_checkpoint_errors=prior['offline_codeword_bit_errors'], terminal_FER=entry['scores']['FER'],
                    max_abs_channel=float(np.max(abs(channel))), max_abs_extrinsic=float(np.max(abs(external))),
                    clipped_extrinsic_bits=int(np.count_nonzero(abs(external) > 20)),
                    raw_to_delivered_sign_flips=int(np.count_nonzero(hard != (delivered < 0))),
                    minimum_raw_margin=float(np.min(sign*raw)),
                    minimum_delivered_margin=float(np.min(sign*delivered)),
                    raw_finite_symbol_variance_sum=float(.25*np.sum(1-np.tanh(np.clip(raw,-20,20)/2)**2)),
                    delivered_finite_symbol_variance_sum=float(.25*np.sum(1-np.tanh(np.clip(delivered,-20,20)/2)**2))))
    if len(rows) != 512:
        raise ValueError('incomplete checkpoint inventory')
    valid = [r for r in rows if r['checkpoint_valid']]
    return dict(scope='saved interface diagnosis; no new F/T/LDPC calls; clipping effects do not prove FER causality',
        checkpoint_analysis_sha256=sha(path), script_sha256=sha(__file__), checkpoints=len(rows),
        sign_flips=sum(r['raw_to_delivered_sign_flips'] for r in rows),
        valid_checkpoints=len(valid), valid_checkpoint_sign_flips=sum(r['raw_to_delivered_sign_flips'] for r in valid),
        valid_then_failed=[r for r in valid if r['terminal_FER']], rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
