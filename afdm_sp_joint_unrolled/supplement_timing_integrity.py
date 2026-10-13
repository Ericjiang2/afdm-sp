"""Immutable file guards and byte accounting outside the COST02 receiver timer."""
import hashlib
from pathlib import Path
import stat


def _signature(path):
    value = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(value.st_mode):
        raise ValueError('timing artifact must be a regular file: '+str(path))
    return (value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


class BoundFiles:
    """Full SHA at entry/exit; fast metadata checks can miss timestamp collisions.

    A successful ``check`` is not a content proof. Call ``verify`` before
    accepting a completed collection, including on coarse-timestamp filesystems.
    """
    def __init__(self, files):
        self.files = {Path(path): digest for path, digest in files.items()}
        self.signatures = {path: _signature(path) for path in self.files}
        self.verify()

    def check(self):
        for path, expected in self.signatures.items():
            if _signature(path) != expected:
                raise ValueError('timing bound input file changed: '+str(path))

    def verify(self):
        self.check()
        for path, digest in self.files.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('timing bound input content changed: '+str(path))
        self.check()


class OutputMeter:
    """Charge each publication once; reconcile the complete tree at closure."""
    def __init__(self, root, limit):
        if type(limit) is not int or limit <= 0:
            raise ValueError('positive integer timing output limit required')
        self.root, self.limit = Path(root).resolve(), limit
        self.files, self.used = {}, 0

    def require_space(self, size):
        if type(size) is not int or size < 0:
            raise ValueError('nonnegative publication size required')
        if self.used + size > self.limit:
            raise OSError('timing output publication exceeds frozen budget')

    def record(self, path):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root) or path in self.files:
            raise ValueError('duplicate or out-of-root timing output')
        size = _signature(path)[2]
        self.require_space(size)
        self.files[path] = size
        self.used += size

    def adopt_tree(self, directory):
        directory = Path(directory).resolve()
        if not directory.is_relative_to(self.root):
            raise ValueError('setup output outside timing root')
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                self.record(path)

    def verify(self):
        actual = {path.resolve(): _signature(path)[2]
                  for path in self.root.rglob('*') if path.is_file()}
        if actual != self.files or sum(actual.values()) != self.used:
            raise ValueError('timing output inventory differs from publication accounting')
        self.require_space(0)
