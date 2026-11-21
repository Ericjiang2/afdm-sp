"""Immutable completed receiver frames; JSONL is a derived ordered export."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def publish_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.frame-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, allow_nan=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


class FrameStore:
    def __init__(self, root, contract, resume=False):
        self.root = Path(root)
        self.contract = contract
        self.digest = hashlib.sha256(json.dumps(contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
        path = self.root/'run-contract.json'
        if resume:
            if json.loads(path.read_text()) != contract:
                raise ValueError('receiver resume contract mismatch')
        else:
            publish_json(path, contract)
        (self.root/'completed-frames').mkdir(exist_ok=resume)

    def load(self, index, expected):
        path = self.root/'completed-frames'/f'{index:06d}.json'
        if not path.exists():
            return None
        value = json.loads(path.read_text())
        if value['contract_sha256'] != self.digest:
            raise ValueError('completed frame contract mismatch')
        record = value['record']
        if any(record.get(k) != v for k, v in expected.items()):
            raise ValueError('completed frame identity/input mismatch')
        if set(record['arms']) != set(self.contract['config']['arms']):
            raise ValueError('completed frame arm set mismatch')
        json.dumps(record, allow_nan=False)
        if any(not arm['finite'] for arm in record['arms'].values()):
            raise ValueError('completed frame is nonfinite')
        return record

    def save(self, index, record):
        publish_json(self.root/'completed-frames'/f'{index:06d}.json',
                     dict(contract_sha256=self.digest, record=record))
