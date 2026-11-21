"""Small immutable phase-1 qualification receipts."""

import json
from pathlib import Path
import socket
import sys


def write_receipt(path, config, payload):
    path = Path(path)
    with path.open('x') as handle:
        json.dump(dict(_argv=sys.argv, _config=dict(host=socket.gethostname(), **config), **payload),
                  handle, indent=2, allow_nan=False)
        handle.write('\n')
