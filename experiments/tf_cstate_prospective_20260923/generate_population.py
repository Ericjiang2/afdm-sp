"""Generate one registered, independent SP-AFDM population without receiver calls.

The observed and truth roots are separate.  This module never scores outcomes.
No directory is reused after a failed or partial attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path[:0] = [str(EXPERIMENTS/'tf_production_gap_audit_20260922'),
                str(EXPERIMENTS/'tf_geometry_reopen_20260922')]
from audit_io import attach, sha256, write_json  # noqa: E402
from analyze_reopening import observation_hash  # noqa: E402

SCHEMA = 'tf-cstate-prospective/1'
CELLS = (600,650,700)
FRAMES = 1024
DISK_CAP = 32*1024**3
DOMAIN = 0x43535441  # "CSTA"; disjoint from all older [20260920,...] streams.
COMPONENTS = {'channel':1,'message':2,'noise':3}


def _inside_experiments(relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('registered source path must be experiments relative')
    resolved = (EXPERIMENTS/path).resolve()
    if not resolved.is_relative_to(EXPERIMENTS.resolve()):
        raise ValueError('registered source path escapes experiments')
    return resolved


def validate_registration(path, source, baseline, evidence):
    """Check the exact precommitted protocol/source/random namespace contract."""
    path = Path(path)
    value = json.loads(path.read_text())
    if value.get('schema') != SCHEMA or value.get('status') != 'locked':
        raise ValueError('prospective registration is not locked')
    if value.get('cells') != [{'snr_centi_db':x,'frames':FRAMES} for x in CELLS]:
        raise ValueError('prospective 6/6.5/7 dB allocation differs')
    protocol = path.parent/'PROTOCOL.md'
    namespace = path.parent/'random_namespace.json'
    random_lock = json.loads(namespace.read_text())
    entropy = value.get('streams', {}).get('entropy_hex')
    if (not isinstance(entropy,str) or re.fullmatch(r'[0-9a-f]{64}',entropy) is None
            or entropy != random_lock.get('entropy_hex')
            or value.get('protocol_sha256') != sha256(protocol)
            or value.get('random_namespace_sha256') != sha256(namespace)
            or value.get('streams', {}).get('algorithm') !=
                'numpy.SeedSequence(8 entropy uint32 words, CSTA domain, snr_centi_db, frame, component)'):
        raise ValueError('prospective protocol or 256-bit random namespace differs')
    if set(value.get('registration_source_hashes', {})) == set():
        raise ValueError('registered executable source inventory is empty')
    for relative, digest in value['registration_source_hashes'].items():
        if sha256(_inside_experiments(relative)) != digest:
            raise ValueError(f'registered executable source changed: {relative}')
    if evidence.source_hashes(source) != value.get('native_source_hashes'):
        raise ValueError('frozen native source differs')
    if evidence.source_hashes(baseline) != value.get('baseline_source_hashes'):
        raise ValueError('frozen baseline source differs')
    if value.get('original_manifest_sha256') != 'de69da6d945cd56f84eb69cc5df814088885c9d28b9375015599c99abefab7d9':
        raise ValueError('original Part-B numerical identity differs')
    cache = baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if sha256(cache) != value.get('ldpc_cache_sha256'):
        raise ValueError('frozen LDPC cache identity differs')
    return value


def seed_words(entropy_hex, snr_centi_db, frame, component):
    if (re.fullmatch(r'[0-9a-f]{64}',entropy_hex) is None
            or snr_centi_db not in CELLS or not 0<=frame<FRAMES
            or component not in COMPONENTS.values()):
        raise ValueError('invalid prospective stream coordinate')
    words = np.frombuffer(bytes.fromhex(entropy_hex),dtype='<u4').astype(np.uint32)
    return [int(x) for x in words] + [DOMAIN,snr_centi_db,frame,component]


def stream_ids(entropy_hex, snr_centi_db, frame):
    return {name:hashlib.sha256(json.dumps(seed_words(entropy_hex,snr_centi_db,
        frame,component),separators=(',',':')).encode()).hexdigest()
        for name,component in COMPONENTS.items()}


def _write_ledger(path, row):
    with path.open('a') as stream:
        stream.write(json.dumps(row,allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def _size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def verify_population_seal(root):
    root = Path(root)
    seal = json.loads((root/'observed_seal.json').read_text())
    actual = {str(p.relative_to(root)):sha256(p) for p in root.rglob('*')
              if p.is_file() and p.name!='observed_seal.json'}
    if seal.get('status')!='pass' or seal.get('schema')!=SCHEMA or seal.get('files')!=actual:
        raise ValueError('prospective observed population seal differs')
    rows = [json.loads(line) for line in (root/'ledger.jsonl').read_text().splitlines()]
    expected = [(snr,frame) for snr in CELLS for frame in range(FRAMES)]
    if (len(rows)!=3072 or [(r['snr_centi_db'],r['frame']) for r in rows]!=expected
            or seal.get('observations')!=3072):
        raise ValueError('prospective observed population allocation differs')
    receipt=json.loads((root/'generation_receipt.json').read_text())
    if (receipt.get('status')!='pass' or receipt.get('schema')!=SCHEMA
            or receipt.get('observations')!=3072
            or receipt.get('cells')!=[{'snr_centi_db':x,'frames':FRAMES} for x in CELLS]
            or receipt.get('observed_ledger_sha256')!=sha256(root/'ledger.jsonl')
            or receipt.get('registration_sha256')!=seal.get('registration_sha256')):
        raise ValueError('prospective generation receipt differs')
    for row in rows:
        if (row['observation_id']!=f"s{row['snr_centi_db']}_f{row['frame']:04d}"
                or actual.get(row['observation_path'])!=row['observation_sha256']):
            raise ValueError('prospective observed input artifact hash differs')
    return seal


def generate(args):
    observed_root, truth_root = args.observed_out.resolve(), args.truth_out.resolve()
    if observed_root.exists() or truth_root.exists():
        raise FileExistsError('prospective output root already exists')
    if observed_root==truth_root or observed_root in truth_root.parents or truth_root in observed_root.parents:
        raise ValueError('observed and truth output roots must be disjoint')
    evidence = attach(args.source,args.baseline)
    registration = validate_registration(args.registration,args.source,args.baseline,evidence)
    if re.fullmatch(r'[0-9a-f]{40}',args.registration_commit) is None:
        raise ValueError('registration commit must be a full Git SHA')
    environment = evidence.bind_runtime_environment()
    from receiver import context
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation

    setup_start = time.perf_counter()
    system, _, code, header = context()
    context_seconds = time.perf_counter()-setup_start
    evidence.verify_runtime_binding()
    if (system.N_total!=1024 or system.l_max_cap!=102 or system.rho!=.5
            or header['code_g_sha256']!=registration['code_g_sha256']):
        raise ValueError('frozen generation context differs')
    observed_root.mkdir(parents=True)
    truth_root.mkdir(parents=True)
    (observed_root/'observed').mkdir()
    (truth_root/'truth').mkdir()
    registration_sha = sha256(args.registration)
    common = dict(schema=SCHEMA,registration_sha256=registration_sha,
        registration_commit=args.registration_commit,
        protocol_sha256=registration['protocol_sha256'],
        random_namespace_sha256=registration['random_namespace_sha256'],
        source_hashes=registration['registration_source_hashes'],
        cells=registration['cells'],stream_algorithm=registration['streams']['algorithm'],
        environment=environment,campaign_setup_seconds=dict(context=context_seconds),
        created_epoch=time.time(),argv=sys.argv[:],
        seconds_limit=args.seconds,disk_cap_bytes=DISK_CAP)
    write_json(observed_root/'manifest.json',dict(common,kind='observed',
        pilot_law='sqrt(rho)*system._zc_seq; unchanged make_frame + physical_observation',
        observed_scale='sqrt(2*(1-rho)) divisor; rho=.5'))
    write_json(truth_root/'manifest.json',dict(common,kind='truth',
        observed_manifest_sha256=sha256(observed_root/'manifest.json')))
    observed_ledger=observed_root/'ledger.jsonl'
    truth_ledger=truth_root/'ledger.jsonl'
    observed_ledger.touch(exist_ok=False)
    truth_ledger.touch(exist_ok=False)
    started=time.perf_counter()
    completed=0
    entropy=registration['streams']['entropy_hex']
    try:
        for snr in CELLS:
            for frame in range(FRAMES):
                if time.perf_counter()-started >= args.seconds:
                    raise TimeoutError('prospective generation time limit reached')
                if _size(observed_root)+_size(truth_root)>=DISK_CAP:
                    raise RuntimeError('prospective 32GiB disk cap reached')
                stem=f's{snr}_f{frame:04d}'
                ids=stream_ids(entropy,snr,frame)
                def rng_factory(_rep,index,component,*,split):
                    if index!=frame or split!=2 or component not in COMPONENTS.values():
                        raise ValueError('generator requested an unregistered random stream')
                    return np.random.default_rng(np.random.SeedSequence(
                        seed_words(entropy,snr,frame,component)))
                # make_frame seeds NumPy's legacy global RNG for the channel
                # generator; confine that side effect to this one frame.
                global_rng_state=np.random.get_state()
                try:
                    raw=make_frame(system,code,0,frame,snr/100,split=2,
                                   rng_factory=rng_factory)
                finally:
                    np.random.set_state(global_rng_state)
                expected_seed=int(np.random.default_rng(np.random.SeedSequence(
                    seed_words(entropy,snr,frame,COMPONENTS['channel']))).integers(0,2**31))
                if raw['channel_seed']!=expected_seed:
                    raise ValueError('channel stream does not match registered descriptor')
                if not np.array_equal(raw['pilot'],np.sqrt(system.rho)*system._zc_seq):
                    raise ValueError('frozen pilot law differs')
                raw,diagnostics=physical_observation(raw,system,prefix_length=system.l_max_cap)
                scale=np.sqrt(2*(1-system.rho))
                obs=dict(y=np.asarray(raw['y'])/scale,
                    pilot=np.asarray(raw['pilot'])/scale,
                    sigma2=float(raw['sigma2'])/scale**2)
                if set(obs)!={'y','pilot','sigma2'} or not np.isfinite(obs['y']).all():
                    raise ValueError('invalid observed frame')
                obs_hash=observation_hash(obs)
                obs_path=observed_root/'observed'/f'{stem}.npz'
                truth_path=truth_root/'truth'/f'{stem}.npz'
                obs_sha=evidence.save_artifact(obs_path,
                    dict(observation=obs,observation_id=stem,stream_ids=ids,
                         observation_hash=obs_hash),
                    dict(schema=SCHEMA,kind='observed',observation_id=stem,
                         registration_sha256=registration_sha))
                truth=dict(coded=np.asarray(raw['coded']),info=np.asarray(raw['info']),
                    l_i=np.asarray(raw['params']['l_i']),
                    k_real=np.asarray(raw['params']['k_real']),
                    g_i=np.asarray(raw['params']['g_i']),
                    observation_hash=obs_hash,stream_ids=ids,
                    channel_seed=expected_seed,diagnostics=diagnostics)
                truth_sha=evidence.save_artifact(truth_path,truth,
                    dict(schema=SCHEMA,kind='truth',observation_id=stem,
                         registration_sha256=registration_sha))
                _write_ledger(observed_ledger,dict(observation_id=stem,
                    snr_centi_db=snr,frame=frame,
                    observation_path=str(obs_path.relative_to(observed_root)),
                    observation_sha256=obs_sha,observation_hash=obs_hash,stream_ids=ids))
                _write_ledger(truth_ledger,dict(observation_id=stem,
                    snr_centi_db=snr,frame=frame,
                    truth_path=str(truth_path.relative_to(truth_root)),
                    truth_sha256=truth_sha,observation_hash=obs_hash,stream_ids=ids))
                completed+=1
        write_json(observed_root/'generation_receipt.json',dict(
            status='pass',schema=SCHEMA,observations=completed,
            cells=[{'snr_centi_db':snr,'frames':FRAMES} for snr in CELLS],
            registration_sha256=registration_sha,
            registration_commit=args.registration_commit,
            protocol_sha256=registration['protocol_sha256'],
            random_namespace_sha256=registration['random_namespace_sha256'],
            source_hashes_sha256=evidence.canonical_hash(
                registration['registration_source_hashes']),
            observed_ledger_sha256=sha256(observed_ledger),
            truth_ledger_sha256=sha256(truth_ledger),
            generation_seconds=time.perf_counter()-started,
            campaign_setup_seconds=dict(context=context_seconds)))
        observed_files={str(p.relative_to(observed_root)):sha256(p)
            for p in observed_root.rglob('*') if p.is_file() and p.name!='observed_seal.json'}
        write_json(observed_root/'observed_seal.json',dict(status='pass',schema=SCHEMA,
            observations=3072,registration_sha256=registration_sha,files=observed_files))
        truth_files={str(p.relative_to(truth_root)):sha256(p)
            for p in truth_root.rglob('*') if p.is_file() and p.name!='truth_seal.json'}
        write_json(truth_root/'truth_seal.json',dict(status='pass',schema=SCHEMA,
            observations=3072,registration_sha256=registration_sha,
            observed_seal_sha256=sha256(observed_root/'observed_seal.json'),
            files=truth_files))
        verify_population_seal(observed_root)
    except BaseException as error:
        failure=dict(status='invalid_partial',reason=repr(error),
            traceback=traceback.format_exc(),completed_observations=completed,
            pid=os.getpid(),seconds=time.perf_counter()-started)
        write_json(observed_root/'invalid_partial.json',failure)
        write_json(truth_root/'invalid_partial.json',failure)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('registration','source','baseline','observed-out','truth-out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--registration-commit',required=True)
    parser.add_argument('--seconds',type=float,default=10800)
    generate(parser.parse_args())
