"""Scientific choices have one JSON source, bound before source admission."""
import hashlib
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name('STUDY_CONFIG.json')
CONFIG_SHA256 = '9603b3320d50c1d81256f31cc710f743b08ce3aee48d840aa89fb4fbc1678b68'


def load_config(path=CONFIG_PATH):
    payload = Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != CONFIG_SHA256:
        raise ValueError('pilot config differs from frozen SHA-256')
    return json.loads(payload)
