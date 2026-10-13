"""Independent design verification inside D; P/A only verify its saved binding."""
import hashlib
import json
from pathlib import Path

import numpy as np

N = 128
DESIGN_PROBES = 130*127*32
DESIGN_ARRAYS = ('current', 'quadratic', 'random', 'candidate_c2',
                 'candidate_objectives', 'random_objective')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_hash(value):
    value = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(value.dtype).encode())
    h.update(json.dumps(list(value.shape)).encode())
    h.update(value.tobytes())
    return h.hexdigest()


def close(actual, expected, label, atol=1e-8):
    actual, expected = np.asarray(actual), np.asarray(expected)
    require(actual.shape == expected.shape, f'{label}: shape mismatch')
    require(np.isfinite(actual).all() and np.isfinite(expected).all(), f'{label}: nonfinite')
    require(np.allclose(actual, expected, atol=atol, rtol=1e-10), f'{label}: mismatch')


def read_json(path):
    return json.loads(Path(path).read_text())


def read_npz(path):
    with np.load(path, allow_pickle=False) as source:
        require(len(source.files) == len(set(source.files)), 'duplicate archive array')
        return {key: source[key] for key in source.files}


def verify_stage_completion(stage_root, consumed_files):
    """Bind consumed bytes to the original completion receipt, including copies."""
    root = Path(stage_root).resolve()
    completion = read_json(root/'attempt.json')
    require(completion['status'] == 'complete', f'incomplete source {root.name}')
    require(type(completion.get('exit_code')) is int and completion['exit_code'] == 0,
            f'nonzero or missing completion exit code {root.name}')
    artifacts = completion['artifact_sha256']
    require(isinstance(artifacts, dict) and artifacts, 'missing completion artifact inventory')
    for name in consumed_files:
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts,
                'invalid consumed artifact path')
        path = (root/relative).resolve()
        require(path.is_relative_to(root), 'consumed artifact escapes stage')
        suffix = ('execution', root.name, *relative.parts)
        # Recorder keys are project-relative or absolute. A copied stage keeps
        # its execution/<stage>/<relative> identity; never match a basename only.
        matches = [digest for key, digest in artifacts.items()
                   if '..' not in Path(key).parts and
                   (Path(key) == path or Path(key).parts[-len(suffix):] == suffix)]
        require(len(matches) == 1, f'completion artifact match must be unique: {root.name}/{name}')
        require(file_hash(path) == matches[0], f'completion artifact hash: {root.name}/{name}')
    return completion


def independent_geometry(v):
    """Positive-frequency ambiguity via forward FFT; no producer helper calls."""
    v = np.asarray(v)
    require(v.ndim == 1 and len(v) >= 4 and len(v) % 4 == 0, 'geometry code shape')
    require(np.isfinite(v).all(), 'geometry code nonfinite')
    close(abs(v), np.ones(len(v)), 'geometry unit code', 1e-12)
    n = len(v)
    w = v**4
    products = np.stack([w*np.conj(np.roll(w, a)) for a in range(1, n)])
    values = abs(np.fft.fft(products, axis=1)[:, (-4*np.arange(n//4)) % n])/n
    require(values.shape == (n-1, n//4) and np.isfinite(values).all(), 'geometry values')
    return float(values.max()), values


def check_design_arrays(codes, record, n=N):
    """Validate bytes and saved selection without evaluating any geometry."""
    expected_keys = {f'n{n}_{name}' for name in DESIGN_ARRAYS}
    require(set(codes) == set(record['array_sha256']) == expected_keys, 'design array inventory')
    for key, value in codes.items():
        require(np.isfinite(value).all(), f'design nonfinite {key}')
        require(array_hash(value) == record['array_sha256'][key], f'design array hash {key}')
    candidates = codes[f'n{n}_candidate_c2']
    objectives = codes[f'n{n}_candidate_objectives']
    expected = np.r_[1/(10*n*n), (np.arange(128)+np.sqrt(2))/(4*129)]
    close(candidates, expected, 'quadratic candidates', 1e-15)
    require(objectives.shape == (129,) and not np.iscomplexobj(objectives), 'candidate objectives shape/type')
    require(np.all((objectives >= 0) & (objectives <= 1+1e-12)), 'candidate objective range')
    require(len(record['designs']) == 1 and record['designs'][0]['N'] == n, 'design row inventory')
    row = record['designs'][0]
    choice = int(np.argmin(objectives))
    require(type(row['quadratic_index']) is int and row['quadratic_index'] == choice, 'design earliest selection')
    require(row['quadratic_c2'] == candidates[choice] and
            row['quadratic_objective'] == objectives[choice], 'selected design score')
    random_objective = codes[f'n{n}_random_objective']
    require(random_objective.shape == () and not np.iscomplexobj(random_objective), 'random objective scalar')
    require(0 <= random_objective.item() <= 1+1e-12, 'random objective range')
    require(row['current_objective'] == objectives[0] and
            row['random_objective'] == random_objective.item(), 'design score fields')
    for arm in ('current', 'quadratic', 'random'):
        value = codes[f'n{n}_{arm}']
        require(value.shape == (n,), 'code shape')
        close(abs(value), np.ones(n), 'unit code', 1e-12)
    for arm, idx in (('current', 0), ('quadratic', choice)):
        close(codes[f'n{n}_{arm}'], np.exp(-2j*np.pi*candidates[idx]*np.arange(n)**2),
              'quadratic code', 1e-12)
    random = codes[f'n{n}_random']
    close(random, np.exp(.25j*np.angle(random**4)), 'principal fourth-root code', 1e-12)
    require(record['design_phase_draws'] == n and record['new_observations'] == 0 and
            record['geometry_probes'] == 130*(n-1)*(n//4), 'design counts')
    return candidates, objectives, choice


def calculate_design_check(design_root):
    """Recompute exactly 130 objectives before D becomes complete; no RNG."""
    root = Path(design_root)
    record = read_json(root/'design.json')
    code_hash = file_hash(root/'codes.npz')
    require(code_hash == record['code_file_sha256'], 'design file binding')
    codes = read_npz(root/'codes.npz')
    candidates, objectives, choice = check_design_arrays(codes, record, n=N)
    verified = []
    probes = 0
    for c2 in candidates:
        objective, values = independent_geometry(np.exp(-2j*np.pi*c2*np.arange(N)**2))
        verified.append(objective)
        probes += values.size
    random_objective, values = independent_geometry(codes[f'n{N}_random'])
    probes += values.size
    close(verified, objectives, 'independent quadratic objectives', 1e-12)
    close(random_objective, codes[f'n{N}_random_objective'], 'independent random objective', 1e-12)
    require(int(np.argmin(verified)) == choice, 'independent earliest selection')
    require(probes == DESIGN_PROBES, 'independent geometry count')
    result = dict(audit_pass=True, geometry_probes=probes, design_phase_draws=0,
                  new_observations=0, acquisition_calls=0, verified_objectives=130,
                  quadratic_index=choice, candidate_objectives=verified,
                  random_objective=random_objective,
                  max_objective_abs_error=float(np.max(abs(np.asarray(verified)-objectives))),
                  code_file_sha256=code_hash, design_json_sha256=file_hash(root/'design.json'),
                  array_sha256=record['array_sha256'],
                  scope='All 129 quadratic objectives and the one saved general-phase objective; independent forward FFT, no producer ambiguity helper, new code search, RNG or observations.')
    with (root/'design_audit.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result


def load_verified_design(design_root):
    """Shared P/A boundary: verify D receipt and hashes, never repeat geometry."""
    root = Path(design_root)
    verify_stage_completion(root, ('results.json', 'codes.npz', 'design.json', 'design_audit.json',
                                   'registration.json', 'committed_project_sources.json'))
    receipt, record = read_json(root/'results.json'), read_json(root/'design.json')
    checked = read_json(root/'design_audit.json')
    require(receipt['design_audit_pass'] is True and checked['audit_pass'] is True, 'design audit not passed')
    require(file_hash(root/'design_audit.json') == receipt['design_audit_sha256'], 'design audit file binding')
    require(file_hash(root/'design.json') == checked['design_json_sha256'], 'design record file binding')
    require(file_hash(root/'codes.npz') == checked['code_file_sha256'] ==
            receipt['code_file_sha256'] == record['code_file_sha256'], 'design file binding')
    require(receipt['designs'] == record['designs'] and receipt['array_sha256'] ==
            checked['array_sha256'] == record['array_sha256'], 'design record binding')
    require(receipt['geometry_probes'] == 2*DESIGN_PROBES and
            receipt['design_geometry_probes'] == DESIGN_PROBES and
            receipt['design_verification_geometry_probes'] == DESIGN_PROBES and
            receipt['design_phase_draws'] == N and receipt['new_observations'] == 0, 'completed design counts')
    require(checked['geometry_probes'] == DESIGN_PROBES and checked['verified_objectives'] == 130 and
            checked['design_phase_draws'] == checked['new_observations'] == checked['acquisition_calls'] == 0,
            'design audit counts')
    codes = read_npz(root/'codes.npz')
    _, objectives, choice = check_design_arrays(codes, record)
    close(checked['candidate_objectives'], objectives, 'saved verified quadratic objectives', 1e-12)
    close(checked['random_objective'], codes[f'n{N}_random_objective'], 'saved verified random objective', 1e-12)
    require(checked['quadratic_index'] == choice == int(np.argmin(checked['candidate_objectives'])),
            'saved verified selection')
    return codes, receipt
