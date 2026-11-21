"""Use the qualified Phase 1 receiver with the Phase 2 key and arm schedule."""

from hashlib import sha256
from importlib import import_module
from pathlib import Path

_RECEIVER_PATH = Path(__file__).resolve().with_name('spectral_receiver.py')
PHASE1_RECEIVER_SHA256 = 'bf7579010358b5c2772127eb2b24bbfce84581c2ec34570956fee35af8fad24c'
_receiver_bytes = _RECEIVER_PATH.read_bytes()
if sha256(_receiver_bytes).hexdigest() != PHASE1_RECEIVER_SHA256:
    raise RuntimeError('Phase 1 receiver SHA256 does not match the qualified source')

phase1 = import_module('spectral_receiver')

if Path(phase1.__file__).resolve() != _RECEIVER_PATH:
    raise RuntimeError('Phase 1 receiver imported from an unexpected path')

MAIN_ARMS = {100: phase1.NEW_ARMS, 400: ('R1', 'S0', 'S-lo', 'S-hi')}
_MAIN_KEYS = frozenset(phase1.lib.main_keys())
_LONG_FRAMES = range(4000, 4050)


def main_budgets(key):
    """Reject keys outside the 1,200-key protocol before receiver work."""
    if key not in _MAIN_KEYS:
        raise ValueError(f'Phase 2 key disallowed: {key}')
    return (100, 400) if key[3] in _LONG_FRAMES else (100,)


def _replace_section(source, start_line, next_line, replacement):
    start = source.index(start_line)
    stop = source.index(next_line, start + len(start_line))
    return source[:start] + replacement + source[stop:]


def _build_main_receiver():
    # The pin makes the five scheduling edits fail closed. Preparation and
    # per-arm receiver calculations come from the qualified source verbatim.
    frozen = _receiver_bytes.decode('utf-8')
    start = frozen.index('def process_key(')
    stop = frozen.index('\ndef check_forced_pruning(', start)
    source = frozen[start:stop]
    source = _replace_section(
        source, 'def process_key(', '    shared_start =',
        '''def process_main_key(ctx, cache, grid, key):
    budgets = main_budgets(key)
''',
    )
    source = _replace_section(
        source, '    specs, matrices, ridges, blocks, census =', '    def run_budget(max_iter):',
        '''    specs, matrices, ridges, _, census = arm_settings(v, sigma2, delays, dopplers, c1, True)
    row['seconds'] = dict(total=time.perf_counter() - shared_start)
    row['sum_v'] = specs['R1']['sum_vec']
    row['census'] = census

''',
    )
    source = _replace_section(
        source, '        variants, results, refinement_errors, pruning =', '            arm_start =',
        '''        variants, results = {}, {}
        r1_sbl_seconds = 0.
        if max_iter == 100:
            r1_start = time.perf_counter()
            fit_sbl(results, 'R1', B, Y, beta0, matrices['R1'], max_iter)
            r1_sbl_seconds = time.perf_counter() - r1_start
        for name in MAIN_ARMS[max_iter]:
''',
    )
    source = _replace_section(
        source, '            if smoke:', '    if smoke:\n        row[\'budgets\']',
        '''            score['census'] = census

        return dict(variants=variants, seconds=dict(r1_sbl_only=r1_sbl_seconds))

''',
    )
    source = _replace_section(
        source, '    if smoke:\n        row[\'budgets\']', '    return row',
        "    row['budgets'] = {str(max_iter): run_budget(max_iter) for max_iter in budgets}\n",
    )
    namespace = dict(vars(phase1), main_budgets=main_budgets, MAIN_ARMS=MAIN_ARMS)
    exec(compile(source, '<qualified spectral_receiver.py with Phase 2 schedule>', 'exec'), namespace)
    return namespace['process_main_key']


process_main_key = _build_main_receiver()
