"""Frozen cluster-paired four-contrast promotion rule."""
import importlib.util
import json
from pathlib import Path
import unittest


SPEC=importlib.util.spec_from_file_location('pilot_initial_promotion_eval_v1',
    Path(__file__).with_name('pilot_initial_promotion_eval_v1.py'))
promotion=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(promotion)
STAGE=json.loads(Path(__file__).with_name('ce-state-predictions-v1.json').read_text())['pilot_stage']


def rows(candidate33=.8,candidate54=1.1):
    all_rows=[]
    for block in range(32):
        for snr in (7,8):
            for arm in promotion.ARMS:
                value=1. if arm not in ('C33','C54') else (
                    candidate33 if arm=='C33' else candidate54)
                all_rows.append(dict(block=block,snr=snr,arm=arm,
                    H_NMSE=value,Hp_NMSE=value,native_gate=True))
    eng=[r for r in all_rows if r['block'] in (0,20)]
    dev=[r for r in all_rows if r['block'] not in (0,20)]
    return eng,dev


class PromotionRule(unittest.TestCase):
    def test_single_candidate_requires_both_related_contrasts(self):
        eng,dev=rows()
        out=promotion.evaluate(eng,dev,STAGE)
        self.assertEqual(out['selected'],'C33')
        self.assertTrue(out['eligible']['C33'])
        self.assertFalse(out['eligible']['C54'])
        for limit in out['contrasts']['C33-P03']['simultaneous_95_CI']:
            self.assertAlmostEqual(limit,-.2)
        self.assertEqual(out['native_waveform_pass_count_of_64']['C33'],64)

    def test_waveform_failure_or_missing_pair_blocks_promotion(self):
        eng,dev=rows()
        next(r for r in dev if r['arm']=='C33')['native_gate']=False
        out=promotion.evaluate(eng,dev,STAGE)
        self.assertIsNone(out['selected'])
        with self.assertRaises(ValueError):
            promotion.evaluate(eng,dev[:-1],STAGE)


if __name__=='__main__':unittest.main()
