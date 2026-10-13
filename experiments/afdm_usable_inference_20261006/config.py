"""One scientific config source, bound by its pre-execution SHA-256."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT/'afdm_sp_joint_unrolled/outputs_usable_inference_20261006/STUDY_CONFIG.json'
CONFIG_SHA256 = 'c4f416af16ace8b98897d452a1e884a1002f0f7de835e7e2d8b9cee159f9c850'


def load_config(path=DEFAULT_PATH):
    payload = Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != CONFIG_SHA256:
        raise ValueError('scientific config bytes differ from frozen SHA-256')
    return json.loads(payload)
