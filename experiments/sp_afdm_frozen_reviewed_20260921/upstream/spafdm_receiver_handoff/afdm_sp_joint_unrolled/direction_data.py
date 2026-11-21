"""Campaign-specific simulation boundary. Only ``frame.observed`` enters receivers."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import numpy as np

CAMPAIGN_ID = 'afdm-direction-20260908-v1'
NAMESPACE = (20260908, 210644, 731901)
SPLITS = {'engineering': 90, 'design': 91, 'mechanism': 92, 'confirm': 93,
          'counterexample': 94, 'timing': 95}
COMPONENTS = {'channel': 1, 'data': 2, 'noise': 3, 'code': 4,
              'interleaver': 5, 'pilot-design': 6, 'order': 7}
CODE_HASH = 'bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'
OBSERVED_KEYS = frozenset(('y', 'pilot', 'sigma2', 'constellation'))


def campaign_rng(split, block, component):
    """SNR is deliberately absent; no legacy split aliases are accepted."""
    if split not in SPLITS or component not in COMPONENTS:
        raise ValueError('unknown campaign split or RNG component')
    if type(block) is not int or block < 0:
        raise ValueError('block must be a nonnegative integer')
    return np.random.default_rng(np.random.SeedSequence(
        [*NAMESPACE, SPLITS[split], block, COMPONENTS[component]]))


def source_manifest():
    """Content snapshot, including imports in Python subpackages; not just HEAD."""
    root = Path(__file__).resolve().parent
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*.py'))}


@dataclass(frozen=True)
class ReceiverDomain:
    """Explicit geometry and generator identity from a bound experiment contract."""
    N: int
    l_max: int
    k_max: int
    code_G_sha256: str

    def __post_init__(self):
        if (type(self.N) is not int or self.N <= 0
                or type(self.l_max) is not int or self.l_max < 0
                or type(self.k_max) is not int or self.k_max < 0
                or not isinstance(self.code_G_sha256, str)
                or len(self.code_G_sha256) != 64
                or any(c not in '0123456789abcdef' for c in self.code_G_sha256)):
            raise ValueError('explicit finite receiver domain and generator SHA256 required')

    @property
    def dictionary_columns(self):
        return (self.l_max + 1) * (2*self.k_max + 1)


FROZEN_RECEIVER_DOMAIN = ReceiverDomain(1024, 102, 2, CODE_HASH)


def validate_code(code, *, domain=None):
    expected = FROZEN_RECEIVER_DOMAIN if domain is None else domain
    if type(expected) is not ReceiverDomain:
        raise ValueError('explicit ReceiverDomain required')
    if ((code['n'], code['d_v'], code['d_c'], code['seed']) != (2*expected.N, 3, 6, 20260726)
            or np.asarray(code['G']).shape != (2*expected.N, code['k'])
            or hashlib.sha256(np.ascontiguousarray(code['G']).tobytes()).hexdigest() != expected.code_G_sha256):
        raise ValueError('frozen LDPC dimensions/seed/generator mismatch')


def validate_observed(observed, N=None):
    """Reject extra fields BEFORE converting arrays or executing any receiver."""
    if not isinstance(observed, Mapping) or frozenset(observed) != OBSERVED_KEYS:
        raise ValueError('observed input must contain exactly y, pilot, sigma2, constellation')
    y, p, c = (np.asarray(observed[k]) for k in ('y', 'pilot', 'constellation'))
    if (y.ndim != 1 or p.shape != y.shape or c.shape != (4,)
            or (N is not None and y.shape != (N,))
            or any(not np.iscomplexobj(a) or not np.isfinite(a).all() for a in (y,p,c))):
        raise ValueError('invalid finite complex observed shapes')
    sigma = np.asarray(observed['sigma2'])
    if sigma.ndim != 0 or np.iscomplexobj(sigma) or not np.isfinite(sigma) or sigma <= 0:
        raise ValueError('sigma2 must be a positive finite scalar variance')
    return y, p, float(sigma), c


@dataclass(frozen=True)
class CampaignFrame:
    observed: Mapping
    metadata: dict
    _truth: dict = field(repr=False)


class CampaignData:
    def __init__(self, protocol_path, code, *, freeze_token=None):
        raw = Path(protocol_path).read_bytes()
        self.protocol = json.loads(raw)
        self.protocol_sha256 = hashlib.sha256(raw).hexdigest()
        p = self.protocol
        if (p['campaign_id'] != CAMPAIGN_ID or tuple(p['rng']['namespace_words']) != NAMESPACE
                or p['rng']['components'] != COMPONENTS
                or {k:v['id'] for k,v in p['splits'].items()} != SPLITS):
            raise ValueError('campaign namespace differs from implemented frozen contract')
        validate_code(code)
        if p['system']['ldpc']['G_sha256'] != CODE_HASH or p['system']['interleaver'] != 'identity, current code convention; no random extra interleaver':
            raise ValueError('code/interleaver protocol drift')
        self.code = code
        self.freeze_token = freeze_token
        self.sources = source_manifest()

    def _validate_request(self, split, block, snr, *, arm_id=None):
        if split not in SPLITS or type(block) is not int or block < 0:
            raise ValueError('invalid campaign split/block; legacy D_test is forbidden')
        limits = {'engineering':32, 'design':192, 'mechanism':256, 'confirm':4096}
        if split not in limits:
            raise ValueError('counterexample/timing require their own frozen sample manifests')
        if block >= limits[split] or snr not in ((8,) if split == 'design' else (7,8,9)):
            raise ValueError('block/SNR outside frozen split domain')
        if split == 'confirm':
            token = self.freeze_token
            if not isinstance(token, dict):
                raise ValueError('confirmation locked until actual FREEZE-01 manifest')
            def read_verified(path_value, expected_hash):
                if not isinstance(path_value, (str, Path)) or not str(path_value):
                    raise ValueError('frozen evidence path missing')
                path = Path(path_value)
                try:
                    raw = path.read_bytes()
                except OSError as exc:
                    raise ValueError(f'cannot read frozen evidence: {path}') from exc
                if (not isinstance(expected_hash,str) or len(expected_hash)!=64
                        or hashlib.sha256(raw).hexdigest()!=expected_hash):
                    raise ValueError('frozen evidence SHA-256 mismatch')
                document = json.loads(raw)
                if not isinstance(document,dict):
                    raise ValueError('frozen evidence must be a JSON object')
                return document
            manifest = read_verified(token.get('frozen_manifest_path'),
                                     token.get('frozen_manifest_sha256'))
            if (manifest.get('campaign_id') != CAMPAIGN_ID
                    or manifest.get('protocol_sha256') != self.protocol_sha256
                    or manifest.get('proceed_confirmation') is not True):
                raise ValueError('manifest does not authorize this campaign/protocol confirmation')
            arms = manifest.get('arm_ids')
            if (not isinstance(arms,list) or not 1<=len(arms)<=3
                    or any(not isinstance(a,str) or not a for a in arms)
                    or len(set(arms))!=len(arms) or not isinstance(arm_id,str) or arm_id not in arms):
                raise ValueError('explicit confirmation arm must belong to frozen unique arm IDs')
            counts = manifest.get('n_by_snr')
            if (not isinstance(counts,dict) or set(counts)!={'7','8','9'}
                    or any(type(counts[k]) is not int or not 1<=counts[k]<=limit
                           for k,limit in (('7',2048),('8',4096),('9',2048)))
                    or block>=counts[str(int(snr))]):
                raise ValueError('confirmation sample counts/request violate frozen SNR bounds')
            authorization = manifest.get('authorization')
            if not isinstance(authorization,dict) or authorization.get('status')!='accepted':
                raise ValueError('confirmation authorization has not been accepted')
            auth_path = authorization.get('evidence_path')
            if not isinstance(auth_path,str) or not auth_path:
                raise ValueError('authorization evidence path missing')
            auth_path = Path(auth_path)
            if not auth_path.is_absolute():
                auth_path = Path(token['frozen_manifest_path']).parent/auth_path
            evidence = read_verified(auth_path,authorization.get('evidence_sha256'))
            if (not isinstance(evidence.get('source'),str) or not evidence['source'].strip()
                    or not isinstance(evidence.get('authorized'),list) or not evidence['authorized']
                    or any(not isinstance(a,str) or not a.strip() for a in evidence['authorized'])):
                raise ValueError('authorization evidence does not record accepted user authority')
            return {'manifest_path':str(Path(token['frozen_manifest_path']).resolve()),
                    'manifest_sha256':token['frozen_manifest_sha256'],
                    'authorization_sha256':authorization['evidence_sha256'],
                    'arm_id':arm_id,'n_by_snr':dict(counts)}
        return None

    def make_frame(self, system, split, block, snr, *, arm_id=None):
        confirmation = self._validate_request(split, block, snr, arm_id=arm_id)
        expected = {'N_total':1024, 'P_paths':8, 'rho':.5, 'k_max_cap':2,
                    'l_max_cap':102, 'k_leak':2, 'frac_prune_rel_thres':.01,
                    'use_frac_doppler':True, 'gen_h_daft_convention':'python',
                    'v_mean':2., 'tau_spread':.01, 'fs':16000.}
        if any(getattr(system,k) != v for k,v in expected.items()):
            raise ValueError('generator configuration differs from campaign')
        from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
        from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
        component_names = {v:k for k,v in COMPONENTS.items()}
        def rng_factory(replicate, index, stream, *, split):
            if replicate != 0 or index != block or split != SPLITS[split_name]:
                raise ValueError('legacy generator requested a different identity')
            return campaign_rng(split_name, block, component_names[stream])
        split_name = split
        # Existing generator uses NumPy's global state. Restore it after generation;
        # this boundary is process-local and must not be called concurrently in threads.
        before = np.random.get_state()
        try:
            raw = make_frame(system, self.code, 0, block, snr, split=SPLITS[split],
                             rng_factory=rng_factory)
        finally:
            np.random.set_state(before)
        constellation = np.sqrt(.5)*np.array([1+1j,1-1j,-1+1j,-1-1j])/np.sqrt(2)
        observed = {k:raw[k] for k in ('y','pilot','sigma2')}
        observed['constellation'] = constellation
        for key in ('y','pilot','constellation'):
            observed[key] = np.array(observed[key], copy=True)
            observed[key].flags.writeable = False
        validate_observed(observed, 1024)
        metadata = {'campaign_id':CAMPAIGN_ID, 'split':split, 'block':block, 'snr_db':snr,
                    'cluster_id':[CAMPAIGN_ID, split, block], 'protocol_sha256':self.protocol_sha256,
                    'confirmation_authority':confirmation,
                    'source_sha256':dict(self.sources), 'code_G_sha256':CODE_HASH,
                    'channel_seed':raw['channel_seed'],
                    'data_seed':{'seed_words':[*NAMESPACE,SPLITS[split],block,COMPONENTS['data']]},
                    'code_id':'ldpc-n2048-dv3-dc6-seed20260726-G-'+CODE_HASH,
                    'interleaver_id':'identity-n2048', 'interleaver':'identity',
                    'rng_words':{c:[*NAMESPACE,SPLITS[split],block,v] for c,v in COMPONENTS.items()},
                    'input_hashes':{k:array_hash(raw[k]) for k in ('y','H','info','coded','noise','pilot','data')},
                    'actual_tx_energy':float(np.mean(abs(raw['pilot']+raw['data'])**2)),
                    'pilot_data_cross_term':float(2*np.vdot(raw['pilot'],raw['data']).real/1024),
                    'data_snr_db':float(snr+10*np.log10(.5))}
        truth = {k:raw[k] for k in ('H','params','info','coded','data','noise')}
        return CampaignFrame(MappingProxyType(observed), metadata, truth)
