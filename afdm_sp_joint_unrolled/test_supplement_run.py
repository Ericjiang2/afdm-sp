"""Unit fixtures only; these tests do not certify real full-receiver execution."""
import json
from pathlib import Path
from types import SimpleNamespace
import time
from unittest.mock import patch

import numpy as np
import unittest
import tempfile

from . import supplement_run as runner


def args(tmp_path, **changes):
    values = dict(start=0, stop=1, snr=8., max_full_calls=1,
        deadline_unix=time.time()+300, recipes=json.dumps([
            dict(id='b0', family='b0', parameter=None, terminal_scale=1.)]),
        out=tmp_path/'batch', device='cpu', protocol=tmp_path/'p.json', checkpoint=tmp_path/'c.pt')
    values.update(changes)
    return SimpleNamespace(**values)


def test_invalid_contract(tmp_path):
    for changes in [dict(stop=33), dict(start=-1), dict(max_full_calls=129),
        dict(max_full_calls=0), dict(stop=2), dict(snr=8.5), dict(deadline_unix=0),
        dict(recipes='all'), dict(recipes='[]'), dict(recipes='[{}]')]:
        with unittest.TestCase().assertRaises(ValueError):
            runner.validate_request(args(tmp_path, **changes))


def test_shared_budget_and_duplicate_reservation(tmp_path):
    contract = dict(max_full_calls=100, config_sha256='a'*64)
    runner.reserve(tmp_path/'one', contract)
    with unittest.TestCase().assertRaises(FileExistsError):
        runner.reserve(tmp_path/'one', dict(contract, max_full_calls=1))
    with unittest.TestCase().assertRaisesRegex(ValueError, '128F'):
        runner.reserve(tmp_path/'two', dict(contract, max_full_calls=29))
    runner.reserve(tmp_path/'two', dict(contract, max_full_calls=28))


def test_failure_and_existing_output(tmp_path):
    a = args(tmp_path, stop=33)
    with unittest.TestCase().assertRaises(ValueError):
        runner.execute(a)
    original = (a.out/'failure.json').read_bytes()
    assert json.loads(original)['calls_attempted'] == 0
    with unittest.TestCase().assertRaises(FileExistsError):
        runner.execute(a)
    assert (a.out/'failure.json').read_bytes() == original


def fixture_code(**kwargs):
    assert kwargs['cache_dir'].is_dir(), 'runner must create code cache before build_code'
    return {'G': np.eye(4), 'H': np.eye(4)}


def fixture_frame():
    observed = dict(y=np.ones(2, complex), pilot=np.zeros(2, complex), sigma2=1.,
                    constellation=np.array([1+1j]))
    truth = dict(H=np.eye(2), coded=np.zeros(4, np.uint8), info=np.zeros(2, np.uint8),
                 data=np.ones(2, complex))
    meta = dict(input_hashes={k: runner.array_hash(v) for k, v in truth.items()},
                protocol_sha256='a'*64, block=0, snr_db=8)
    return SimpleNamespace(observed=observed, _truth=truth, metadata=meta)


def test_schema_and_truth_boundary(tmp_path):
    a = args(tmp_path)
    a.protocol.write_text(json.dumps({'system': {'ldpc': dict(n=4, dv=1, dc=2, seed=1, maxiter=50)}}))
    a.checkpoint.write_bytes(b'unit fixture')
    frame = fixture_frame()
    result = dict(H=np.eye(2), x_hard=np.ones(2, complex), info_hat=np.zeros(2, np.uint8),
        decoded=np.zeros(4, np.uint8), decode_ok=True, sigma2=1., sigma2_terminal=1.,
        seconds=.1, transfer_seconds=.01, inclusive_seconds=.11, support=[0],
        capacity_trace=[], graphs=[], initial_estimator={}, mu=np.ones(2), var=np.ones(2),
        llr=np.ones(4))
    class FakeReceiver:
        def run(self, observed, **kw):
            assert observed is frame.observed
            assert set(observed) == {'y','pilot','sigma2','constellation'}
            return result
    with patch.object(runner, 'build_code', side_effect=fixture_code), \
         patch.object(runner, 'SupplementData') as data, \
         patch.object(runner, '_make_config_a'), \
         patch.object(runner.ObservedReceiver, 'build', return_value=FakeReceiver()):
        data.return_value.make_frame.return_value = frame
        assert runner.execute(a) == 0
    row = json.loads(next(a.out.glob('frame-*.json')).read_text())
    assert runner.validate_record(row)['FER'] == 0
    for key, value in [('block_id', 1), ('SNR', 9), ('protocol_sha256', 'b'*64), ('arm_id', 'other')]:
        changed = dict(row, **{key: value})
        with unittest.TestCase().assertRaisesRegex(ValueError, 'identity'):
            runner.validate_record(changed)
    with unittest.TestCase().assertRaisesRegex(ValueError, 'dimensions'):
        runner.frame_record(frame, dict(result, decoded=np.zeros((4, 1))),
                            row['recipe'], row, .1, .1, 0)
    row['coded_bit_errors'] = 1
    with unittest.TestCase().assertRaisesRegex(ValueError, 'FER'):
        runner.validate_record(row)
    del row['source_sha256']
    with unittest.TestCase().assertRaisesRegex(ValueError, 'incomplete'):
        runner.validate_record(row)


def test_receiver_failure_preserves_attempt_identity(tmp_path):
    a = args(tmp_path)
    a.protocol.write_text(json.dumps({'system': {'ldpc': dict(n=4, dv=1, dc=2, seed=1, maxiter=50)}}))
    a.checkpoint.write_bytes(b'fixture')
    with patch.object(runner, 'build_code', side_effect=fixture_code), \
         patch.object(runner, 'SupplementData') as data, \
         patch.object(runner, '_make_config_a'), \
         patch.object(runner.ObservedReceiver, 'build') as build:
        data.return_value.make_frame.return_value = fixture_frame()
        build.return_value.run.side_effect = RuntimeError('receiver failure')
        with unittest.TestCase().assertRaisesRegex(RuntimeError, 'receiver failure'):
            runner.execute(a)
    failure = json.loads((a.out/'failure.json').read_text())
    assert failure['calls_attempted'] == 1 and failure['calls_completed'] == 0
    assert failure['active_attempt']['block_id'] == 0
    assert not (a.out/'complete.json').exists()


def test_generation_failure_preserves_block_without_full_call(tmp_path):
    a = args(tmp_path)
    a.protocol.write_text(json.dumps({'system': {'ldpc': dict(n=4, dv=1, dc=2, seed=1, maxiter=50)}}))
    a.checkpoint.write_bytes(b'fixture')
    with patch.object(runner, 'build_code', side_effect=fixture_code), \
         patch.object(runner, 'SupplementData') as data, \
         patch.object(runner, '_make_config_a'), \
         patch.object(runner.ObservedReceiver, 'build') as build:
        data.return_value.make_frame.side_effect = RuntimeError('generation failure')
        with unittest.TestCase().assertRaisesRegex(RuntimeError, 'generation failure'):
            runner.execute(a)
        build.return_value.run.assert_not_called()
    failure = json.loads((a.out/'failure.json').read_text())
    assert failure['calls_attempted'] == 0 and failure['calls_completed'] == 0
    assert failure['active_attempt']['stage'] == 'generation'
    assert failure['active_attempt']['block_id'] == 0
    assert not (a.out/'complete.json').exists()


class EngineeringContracts(unittest.TestCase):
    pass


def _case(function):
    def run(self):
        with tempfile.TemporaryDirectory() as temporary:
            function(Path(temporary))
    return run


for _name, _function in list(globals().items()):
    if _name.startswith('test_') and callable(_function):
        setattr(EngineeringContracts, _name, _case(_function))

if __name__ == '__main__':
    unittest.main()
