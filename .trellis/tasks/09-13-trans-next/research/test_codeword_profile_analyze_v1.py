from __future__ import annotations

import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('codeword_profile_analyze_v1',HERE/'codeword_profile_analyze_v1.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_ranking_rescue_excludes_preexisting_true_preferred():
    rows=[]
    for fixed,profile in ((True,True),(False,True),(True,False)):
        rows.append(dict(margins={'reencoded_info_hat':dict(fixed_true_preferred=fixed,
            profile_true_preferred=profile,fixed_H_margin=1. if fixed else -1.,
            profile_margin=1. if profile else -1.)},
            status={'reencoded_info_hat':dict(valid=True)}))
    result=module.classify(rows,'reencoded_info_hat')
    assert result['fixed_H_true_preferred']==2
    assert result['profile_true_preferred']==2
    assert result['profile_ranking_rescue']==1
    assert result['profile_ranking_worsening']==1
    assert result['preexisting_true_preferred_both']==1
