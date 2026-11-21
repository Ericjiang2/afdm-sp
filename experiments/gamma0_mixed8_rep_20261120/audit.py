"""Find the next untouched contiguous S8D2 cohort from both archive inventories."""
import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEG2 = HERE.parent/'gamma0_mixed8_20261120'
SCANNER_SHA256 = '5fd24241245c6a2c1a9dc9d63c2018e5f2345be031462edeaa73e76162f1f9a3'
LEG2_G3_SHA256 = '2387b0014df45e2cdb1a5612881e5a67e6e4e08e264b5b68b7cd771a22dfb306'
LEG2_FRESH = (2200, 2799)
LEG2_SMOKE = (208, 209, 210)
N_FRAMES = 2400


def prior_scanner():
    path = LEG2/'audit.py'
    if sha256(path.read_bytes()).hexdigest() != SCANNER_SHA256:
        raise ValueError('The leg 2 scanner differs from its frozen source')
    spec = spec_from_file_location('_gamma0_leg2_scanner', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    # In this private instance, exclude the new experiment, so the original
    # scanner also finds leg 2's subsequent main artifacts and smoke claims.
    module.HERE = HERE
    return module


def scan(scanner, root, site):
    receipt = scanner.scan(root, site)
    receipt.update(scanner_sha256=SCANNER_SHA256, excluded_current_experiment=HERE.name)
    return receipt


def select(scanner, receipts):
    qualification = (LEG2/'out/g3.json').read_bytes()
    if sha256(qualification).hexdigest() != LEG2_G3_SHA256:
        raise ValueError('Leg 2 G3 receipt differs from freeze')
    prior = json.loads(qualification)
    if (prior['status'] != 'PASS' or tuple(prior['fresh']) != LEG2_FRESH
            or tuple(prior['smoke']) != LEG2_SMOKE):
        raise ValueError('Expected frozen leg 2 frame reservations')
    if len(receipts) != 2 or {r['scope'] for r in receipts} != {'local', 'deinlab'}:
        raise ValueError('Expected local and deinlab audit receipts')
    occupied = set(LEG2_SMOKE)
    registered = (*scanner.REGISTERED, (LEG2_SMOKE[0], LEG2_SMOKE[-1]), LEG2_FRESH)
    for lo, hi in registered:
        occupied.update(scanner.interval(lo, hi))
    for receipt in receipts:
        if (receipt['entropy'], receipt['domain']) != (scanner.ENTROPY, scanner.DOMAIN):
            raise ValueError('Audit RNG identity differs from S8D2')
        if (receipt['scanner_sha256'] != SCANNER_SHA256 or receipt['excluded_current_experiment'] != HERE.name
                or receipt['errors']):
            raise ValueError(f'Unqualified {receipt["scope"]} audit: {receipt["errors"]}')
        for blocks in receipt['hits'].values():
            for lo, hi in blocks:
                occupied.update(scanner.interval(lo, hi))

    start = LEG2_FRESH[-1] + 1
    while overlap := occupied.intersection(range(start, start + N_FRAMES)):
        start = max(overlap) + 1
    smoke = sorted(set(range(LEG2_SMOKE[-1] + 1, 1000)) - occupied)[:3]
    if len(smoke) != 3:
        raise ValueError('Fewer than three unallocated smoke IDs below the evaluation reservations')
    return dict(status='PASS', entropy=scanner.ENTROPY, domain=scanner.DOMAIN,
                scanner_sha256=SCANNER_SHA256, leg2_g3_sha256=LEG2_G3_SHA256,
                fresh=[start, start + N_FRAMES - 1], smoke=smoke,
                registered=scanner.ranges(occupied.intersection(set().union(
                    *(scanner.interval(lo, hi) for lo, hi in registered)))),
                occupied=scanner.ranges(occupied))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--site', choices=('local', 'deinlab'))
    mode.add_argument('--merge', nargs=2, type=Path, metavar=('LOCAL', 'DEINLAB'))
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    args = parser.parse_args()
    scanner = prior_scanner()
    if args.merge:
        evidence = [path.read_bytes() for path in args.merge]
        result = select(scanner, list(map(json.loads, evidence)))
        result['audit_sha256'] = {path.name: sha256(raw).hexdigest()
                                  for path, raw in zip(args.merge, evidence, strict=True)}
    else:
        result = scan(scanner, args.root, args.site)
    print(json.dumps(result, indent=2, sort_keys=True))
    return bool(result.get('errors'))


if __name__ == '__main__':
    raise SystemExit(main())
