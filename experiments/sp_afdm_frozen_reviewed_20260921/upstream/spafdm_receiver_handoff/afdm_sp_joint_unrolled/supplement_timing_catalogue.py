"""Resolve F_C roles and reuse their existing observed-only receiver adapters."""
from __future__ import annotations

from .direction_cancel_receiver import CancellationTransform
from .direction_receiver import ObservedReceiver
from .supplement_baselines import BaselineReceiver
from .supplement_feedback import CodeFeedback
from .supplement_feedback_schedule import UniformBPSchedule
from .supplement_profile import ARMS
from .supplement_scene_candidates import validate_freeze

ALIASES = {'bounded_hard': 'B_star_2', 'Pfixed:p0': 'B_star_1',
           'Pmatched:p0': 'B_star_1'}
ARM_IDS = ('A2', 'B0', 'old_B_star', 'B_star_1', 'B_star_2',
           'group_or_hierarchical', 'legal_soft', 'I1', 'scalar_calibrated',
           'diagonal', 'low_rank', 'Pfixed:p1', 'Pfixed:p2',
           'Pmatched:p1', 'Pmatched:p2')
ROLE_IDS = (*ARM_IDS, *ALIASES)


def resolve_catalogue(freeze, inputs):
    candidates = validate_freeze(freeze, inputs)
    registry = inputs['global_contrasts']['families']['F_C']
    contrasts = registry['contrasts']
    roles = {arm for row in contrasts for arm in row['arms']}
    if (registry.get('m_max') != 102 or len(contrasts) != 102 or
            len({row['id'] for row in contrasts}) != 102 or
            registry.get('alpha') != .05/7 or roles != set(ROLE_IDS)):
        raise ValueError('F_C must retain all 102 endpoints and 18-role coverage')
    methods = {'A2': {'pilot': 'p0', 'interface': 'A2',
                     'adapter': 'supplement_profile.A2Model/A2Receiver'}}
    for symbol, legacy in (('B0', 'B0'), ('old_B_star', 'old-Bstar')):
        methods[symbol] = {'pilot': 'p0', 'interface': 'legacy',
                           'parameters': list(ARMS[legacy])}
    for symbol in ARM_IDS[3:]:
        methods[symbol] = dict(candidates[freeze['symbolic_aliases'][symbol]])
    for alias, target in ALIASES.items():
        if candidates[freeze['symbolic_aliases'][alias]] != methods[target]:
            raise ValueError('F_C exact alias differs from its frozen target')
    return {'schema': 'COST02-retained-catalogue-v2', 'family': 'F_C',
            'm': 102, 'alpha_family': .05/7, 'role_ids': list(ROLE_IDS),
            'arm_ids': list(ARM_IDS), 'aliases': dict(ALIASES), 'methods': methods}


class TimingReceiver:
    """Bind existing adapters; all online interface work stays in run()."""
    def __init__(self, model, code, system, descriptor):
        self.code, self.system = code, system
        self.descriptor = descriptor
        interface = descriptor['interface']
        if interface == 'legacy':
            self.receiver = ObservedReceiver(model, code)
        elif interface in ('baseline', 'I1', 'scalar', 'diagonal', 'lowrank'):
            self.receiver = BaselineReceiver(model, code, descriptor['recipe'],
                                             system=system)
        else:
            raise ValueError('unsupported timing receiver interface: ' + interface)

    def run(self, observed, *, audit=False):
        if audit is not False:
            raise ValueError('timing adapters require audit=False')
        descriptor = self.descriptor
        interface = descriptor['interface']
        kwargs = {}
        if interface == 'legacy':
            family, parameter, scale = descriptor['parameters']
            kwargs.update(family=family, parameter=parameter, terminal_scale=scale)
        elif interface == 'I1':
            kwargs.update(code_feedback=CodeFeedback(self.code,
                checkpoint=descriptor['checkpoint'], control='legal'),
                bp_schedule=UniformBPSchedule(outer_bp_iterations=descriptor['outer_BP']))
        elif interface in ('scalar', 'diagonal', 'lowrank'):
            kwargs['terminal_transform'] = CancellationTransform(self.system, interface)
        return self.receiver.run(observed, audit=False, **kwargs)
