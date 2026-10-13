"""Uniform outer-BP allocation only; no change to CE, outer count or final decoding."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UniformBPSchedule:
    outer_bp_iterations: int

    def __post_init__(self):
        if type(self.outer_bp_iterations) is not int or not 1<=self.outer_bp_iterations<=20:
            raise ValueError('outer BP iterations must be an integer within1..20')
