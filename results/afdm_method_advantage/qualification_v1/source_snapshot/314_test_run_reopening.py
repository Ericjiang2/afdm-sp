"""Synthetic contracts only; these tests do not call the production receiver."""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import json
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'sp_afdm_frozen_20260920'/'src')]
import run_reopening as runner  # noqa: E402
from audit_io import sha256, write_json  # noqa: E402


def packed(bits):
    return dict(packed=np.packbits(bits), length=len(bits))


def test_selection_uses_saved_syndrome_and_actual_1026_by_2048_H(tmp_path,
                                                                  monkeypatch):
    H = np.zeros((1026, 2048), np.uint8)
    H[0, 0] = 1
    run = tmp_path/'run'
    run.mkdir()
    records = []
    for frame in range(1024):
        bad = frame % 17 == 0 and frame < 731  # exactly 43
        decoded = np.zeros(2048, np.uint8)
        decoded[0] = bad
        cp = dict(round=1, path=f'cp{frame}', artifact_sha256='unused',
                  syndrome_weight=int(bad))
        records.append(dict(snr_centi_db=650, arm='TF_J20_R2', frame=frame,
                            status='ok', checkpoints=[dict(cp, round=0), cp]))
        (run/f'cp{frame}').write_bytes(np.packbits(decoded).tobytes())
    (run/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    def fake_bound(_, path, __):
        return dict(decoded=packed(np.unpackbits(np.frombuffer(
            path.read_bytes(), dtype=np.uint8))[:2048]))
    monkeypatch.setattr(runner, 'load_bound', fake_bound)
    chosen = runner.select_observations(run, None, H)
    assert sum(s['kind'] == 'trigger' for s in chosen) == 43
    assert [s['record']['frame'] for s in chosen if s['kind'] == 'control'] == [
        i for i in range(1024) if not (i % 17 == 0 and i < 731)][:32]
    assert len(runner.arm_schedule(chosen)) == 150
    assert runner.arm_schedule(chosen)[:4][1::2][0][1] == 'GLOBAL20'
    assert runner.arm_schedule(chosen)[2:4][0][1] == 'GLOBAL20'
    with pytest.raises(ValueError, match='actual parity-check'):
        runner.syndrome_weight(np.zeros((1024, 2048)), np.zeros(2048))


@dataclass
class FakeResult:
    paths: list
    gains: np.ndarray
    objective_before: float
    objective_after: float
    edits: list
    evaluations: dict
    elapsed_seconds: float
    condition_number: float
    coefficient_power: float
    global_trace: list
    local_trace: list
    diagnostics: dict


def test_geometry_round_preserves_slots_and_separates_app_from_check():
    from physical import daft
    from messages import moments
    n = 8
    system = SimpleNamespace(c1=1/(2*n), c2=1/(3*n), rho=.5)
    obs = dict(y=np.arange(n, dtype=complex), pilot=np.ones(n, complex)*.2,
               sigma2=.1)
    arrays = dict(r1_app=np.full(2*n, 100.),
                  r1_check=np.full(2*n, -100.),
                  r1_delays=np.array([2, 2]),
                  r1_dopplers=np.array([.25, -.25]),
                  r1_gains=np.array([.3+.1j, .2-.1j]),
                  r1_ce_gains=np.array([.1, .2]),
                  r1_mu=np.zeros(n, complex),
                  r1_variance=np.full(n, .5))
    seen = []
    class Geometry:
        @dataclass
        class Path:
            delay: int
            doppler: float
        @staticmethod
        def reopen_geometry(Y, x, v, paths, **kwargs):
            seen.append(dict(Y=Y, x=x, v=v, paths=paths, kwargs=kwargs))
            return FakeResult(paths, np.array([.4, .5], complex), 5., 4., [], {},
                              .01, 2., .41, [], [], {})
    class Native:
        @staticmethod
        def scalar_joint(y, pilot, channel, noise, **kwargs):
            seen.append(dict(channel=channel, scalar=kwargs))
            return dict(extrinsic=np.full(2*n, 30.), gains=np.array([.6, .7]),
                        trace=[], fft_count=41)
        @staticmethod
        def decoder_messages(code, llr, maxiter):
            np.testing.assert_array_equal(llr, np.full(2*n, 20.))
            assert maxiter == 50
            return dict(decoded=np.zeros(2*n, np.uint8), incoming_llr=llr,
                        raw_app=llr, raw_check_extrinsic=llr, iterations=1)
    result = runner._geometry_round(obs, system, None, Native, Geometry,
                                    arrays, 102, 'GLOBAL20')
    mu, v, _ = moments(np.full(2*n, 20.), .5)
    np.testing.assert_allclose(seen[0]['Y'], daft(obs['y'], system.c1, system.c2, True))
    np.testing.assert_allclose(seen[0]['x'], obs['pilot']+mu)
    np.testing.assert_allclose(seen[0]['v'], v)
    assert [p.delay for p in seen[0]['paths']] == [2, 2]
    assert seen[0]['kwargs']['max_edits'] == 2
    assert seen[0]['kwargs']['top_k'] == 20
    assert seen[0]['kwargs']['ridge'] == .1
    np.testing.assert_array_equal(seen[1]['scalar']['prior'], np.full(2*n, -20.))
    assert seen[1]['scalar']['gain_mode'] == 'joint'
    assert seen[1]['scalar']['iterations'] == 20
    assert result['result'].gains.tolist() == [.4, .5]
    assert result['detector']['gains'].tolist() == [.6, .7]
    assert result['timing']['branch_seconds'] >= result['timing']['geometry_seconds']


def test_replay_preserves_both_rounds_and_exact_continuous_tolerance(tmp_path,
                                                                      monkeypatch):
    record = dict(checkpoints=[dict(round=i, path=f'cp{i}', artifact_sha256='x')
                               for i in range(2)])
    snapshot = {k: np.array([1., 2.]) for k in ('input_llr', 'app', 'check',
        'delays', 'dopplers', 'gains', 'mu', 'variance')}
    saved = dict(decoded=packed(np.zeros(2048, np.uint8)), snapshot=snapshot)
    monkeypatch.setattr(runner, 'load_bound', lambda *_: saved)
    arrays = {f'r{i}_{k}': v.copy() for i in range(2)
              for k, v in snapshot.items()}
    arrays.update({f'r{i}_decoded': np.zeros(2048, np.uint8) for i in range(2)})
    assert runner.compare_replay(arrays, record, tmp_path, None) == 0.
    arrays['r1_mu'][0] += 1e-8
    with pytest.raises(ValueError, match='replay differs'):
        runner.compare_replay(arrays, record, tmp_path, None)


def test_seal_rejects_modified_file_and_missing_call(tmp_path):
    out = tmp_path/'out'
    out.mkdir()
    (out/'payload').write_text('original')
    payload_hash = sha256(out/'payload')
    selected = [dict(observation_id=f'f{i}', kind='trigger' if i<43 else 'control')
                for i in range(75)]
    write_json(out/'selection.json', selected)
    rows = [dict(observation_id=s['observation_id'], arm=arm,
                 status='ok', receiver_started=True,
                 raw_path='payload', raw_sha256=payload_hash,
                 wrapper_seconds=4., checkpoints=[dict(round=i, path='payload',
                     artifact_sha256=payload_hash,
                     decision_ready_seconds=float(i),
                     artifact_ready_seconds=float(i)+.5) for i in range(3)])
            for s, arm in runner.arm_schedule(selected)]
    (out/'ledger.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    write_json(out/'observed_seal.json', dict(status='pass',
        selection_sha256=sha256(out/'selection.json'), files={
        p.name:sha256(p) for p in out.iterdir() if p.name!='observed_seal.json'}))
    runner.verify_seal(out)
    (out/'payload').write_text('modified')
    with pytest.raises(ValueError, match='seal/hash'):
        runner.verify_seal(out)
