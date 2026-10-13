"""Synthetic runner contracts; no production receiver calls."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import time

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'sp_afdm_frozen_20260920'/'src')]
import run_validation as runner  # noqa: E402
from audit_io import sha256, write_json  # noqa: E402


def selection():
    return [dict(observation_id=f'f{i}', kind='trigger' if i<43 else 'control')
            for i in range(75)]


def test_fixed_225_call_rotation():
    sequence = runner.arm_schedule(selection())
    assert len(sequence) == 225
    assert [arm for _,arm in sequence[:9]] == [
        'LOCAL20','GLOBAL20','CSTATE20','GLOBAL20','CSTATE20','LOCAL20',
        'CSTATE20','LOCAL20','GLOBAL20']
    with pytest.raises(ValueError, match=r'43\+32'):
        runner.arm_schedule(selection()[:-1])


def test_branch_uses_identical_messages_and_full_stage_accounting():
    n = 8
    obs = dict(y=np.arange(n, dtype=complex), pilot=np.full(n, .2+0j), sigma2=.1)
    system = SimpleNamespace(c1=1/(2*n), c2=1/(3*n), rho=.5, l_max_cap=102)
    arrays = dict(r1_app=np.full(2*n, 100.), r1_check=np.full(2*n, -100.),
                  r1_delays=np.array([2,2]), r1_dopplers=np.array([.25,-.25]),
                  r1_gains=np.array([.1+.1j,.2-.1j]))
    captured = []
    class Kernel:
        @staticmethod
        def Path(delay, doppler):
            return SimpleNamespace(delay=delay, doppler=doppler)
        @staticmethod
        def reopen_geometry(Y, x, v, paths, **kwargs):
            start = time.perf_counter()
            captured.append(dict(Y=Y,x=x,v=v,paths=paths,kwargs=kwargs))
            stages = {key:0. for key in (
                'geometry_setup','structural_field_build','structural_scoring',
                'structural_selection_trace','structural_refit_refresh',
                'structural_fallback_direct','local_refinement',
                'geometry_finalization')}
            elapsed = time.perf_counter()-start
            stages['geometry_setup'] = elapsed
            time.sleep(.002)  # The wrapper must record scheduling/return overhead.
            return SimpleNamespace(paths=paths,gains=np.array([.3,.4]),
                diagnostics=dict(stage_timing=dict(exclusive_seconds=stages,
                    total_seconds=elapsed)))
    class Native:
        @staticmethod
        def scalar_joint(y, pilot, channel, noise, **kwargs):
            captured.append(dict(channel=channel, detector_kwargs=kwargs))
            return dict(extrinsic=np.full(2*n, 30.))
        @staticmethod
        def decoder_messages(code, llr, maxiter):
            np.testing.assert_array_equal(llr, np.full(2*n, 20.))
            assert maxiter == 50
            return dict(decoded=np.zeros(2*n, np.uint8))
    for arm, expected in [('LOCAL20',('direct',0)),
                          ('GLOBAL20',('direct',2)),
                          ('CSTATE20',('compact',2))]:
        result = runner._branch(obs, system, None, Native, Kernel, arrays, arm)
        call, detector = captured[-2:]
        assert (call['kwargs']['strategy'],call['kwargs']['max_edits']) == expected
        assert [p.delay for p in call['paths']] == [2,2]
        np.testing.assert_array_equal(detector['detector_kwargs']['prior'],
                                      np.full(2*n, -20.))
        assert detector['detector_kwargs']['gain_mode'] == 'joint'
        assert detector['detector_kwargs']['iterations'] == 20
        assert abs(sum(result['exclusive_stages'].values())-
                   result['branch_decision_seconds']) < 1e-7
        assert result['exclusive_stages']['geometry_wrapper_overhead'] >= .002
        assert result['exclusive_stages']['wrapper_validation'] >= 0
        assert result['exclusive_stages']['channel_construction'] >= 0

    class OverstatedKernel(Kernel):
        @staticmethod
        def reopen_geometry(Y, x, v, paths, **kwargs):
            result = Kernel.reopen_geometry(Y, x, v, paths, **kwargs)
            stage = result.diagnostics['stage_timing']
            stage['exclusive_seconds']['geometry_setup'] += 1.
            stage['total_seconds'] += 1.
            return result

    with pytest.raises(ValueError, match='exceeds wrapper geometry wall'):
        runner._branch(obs, system, None, Native, OverstatedKernel, arrays, 'CSTATE20')


def test_seal_requires_225_ordered_calls_and_675_checkpoints(tmp_path):
    out = tmp_path/'observed'
    out.mkdir()
    (out/'artifact').write_bytes(b'synthetic')
    digest = sha256(out/'artifact')
    chosen = selection()
    write_json(out/'selection.json', chosen)
    rows = [dict(observation_id=s['observation_id'],arm=arm,status='ok',
                 receiver_started=True,raw_path='artifact',raw_sha256=digest,
                 replay_ready_seconds=1.,raw_artifact_ready_seconds=2.,
                 added_complete_branch_seconds=1.,checkpoints=[
                     dict(round=i,path='artifact',artifact_sha256=digest)
                     for i in range(3)])
            for s,arm in runner.arm_schedule(chosen)]
    (out/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write_json(out/'observed_seal.json',dict(status='pass',schema=runner.SCHEMA,
        completed_calls=225,selection_sha256=sha256(out/'selection.json'),
        files={p.name:sha256(p) for p in out.iterdir()
               if p.name!='observed_seal.json'}))
    runner.verify_seal(out)
    (out/'artifact').write_bytes(b'modified')
    with pytest.raises(ValueError,match='seal'):
        runner.verify_seal(out)
