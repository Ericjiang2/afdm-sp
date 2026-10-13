import json
from pathlib import Path
import tempfile
import unittest

from afdm_sp_joint_unrolled.direction_budget import reserve, settle, reserve_many, settle_many


class CampaignBudget(unittest.TestCase):
    def test_multi_stage_reservation_is_all_or_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json'
            resources=dict(host_seconds=10,gpu_seconds=10,cpu_core_seconds=40)
            p.write_text(json.dumps(dict(campaign_id='test',protocol_sha256='a'*64,
                limits=resources,completed=[],reservations=[],calls_caps={'full':2,'terminal':1})))
            common=dict(campaign_id='test',protocol_sha256='a'*64,resources=resources)
            with self.assertRaises(ValueError):
                reserve_many(p,'bad',calls={'full':1,'terminal':2},**common)
            self.assertEqual(json.loads(p.read_text())['reservations'],[])
            reserve_many(p,'good',calls={'full':2,'terminal':1},**common)
            settle_many(p,'good',calls={'full':1,'terminal':0},resources=resources,evidence='failure',status='failed')
            self.assertEqual(json.loads(p.read_text())['completed'][0]['calls'],{'full':1,'terminal':0})

    def test_shared_reservations_failure_and_duplicate_are_charged(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json'
            limits=dict(host_seconds=100,gpu_seconds=100,cpu_core_seconds=400)
            p.write_text(json.dumps(dict(campaign_id='test',protocol_sha256='a'*64,
                limits=limits,completed=[],reservations=[],calls_caps={'engineering_full':3})))
            args=dict(campaign_id='test',protocol_sha256='a'*64,cap_key='engineering_full',
                      calls=2,resources=dict(host_seconds=40,gpu_seconds=40,cpu_core_seconds=160))
            reserve(p,'first',**args)
            with self.assertRaises(ValueError):reserve(p,'second',**args)
            with self.assertRaises(ValueError):reserve(p,'first',**args)
            settle(p,'first',calls=1,resources=dict(host_seconds=10,gpu_seconds=10,cpu_core_seconds=12),
                   evidence='failure.json',status='failed')
            reserve(p,'second',**args)
            with self.assertRaises(ValueError):reserve(p,'third',**dict(args,calls=1))
            ledger=json.loads(p.read_text())
            self.assertEqual(ledger['completed'][0]['calls'],{'engineering_full':1})
            self.assertEqual(len(ledger['reservations']),1)

    def test_resources_and_protocol_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json'
            p.write_text(json.dumps(dict(campaign_id='test',protocol_sha256='a'*64,
                limits=dict(host_seconds=10,gpu_seconds=10,cpu_core_seconds=40),
                completed=[],reservations=[],calls_caps={'full':100})))
            args=dict(campaign_id='test',protocol_sha256='a'*64,cap_key='full',calls=1,
                      resources=dict(host_seconds=10,gpu_seconds=10,cpu_core_seconds=40))
            reserve(p,'first',**args)
            with self.assertRaises(ValueError):reserve(p,'second',**args)
            with self.assertRaises(ValueError):reserve(p,'wrong',**dict(args,protocol_sha256='b'*64))

    def test_allocation_atomic_concurrent_reservations_and_failed_attempts(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json'
            p.write_text(json.dumps(dict(campaign_id='test',protocol_sha256='a'*64,
                limits={'host_seconds':100},completed=[],reservations=[],calls_caps={'full':100,'terminal':100})))
            args=dict(campaign_id='test',protocol_sha256='a'*64,resources={'host_seconds':1},
                      allocation={'id':'probe','cap':3})
            def attempt(run_id):
                try:
                    reserve_many(p,run_id,calls={'full':1,'terminal':1},**args)
                    return run_id
                except ValueError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes=list(pool.map(attempt,['first','second']))
            winners=[x for x in outcomes if x is not None]
            self.assertEqual(len(winners),1)
            settle_many(p,winners[0],calls={'full':1,'terminal':0},resources={'host_seconds':1},
                        evidence='fixture failure',status='failed')
            completed=json.loads(p.read_text())['completed'][0]
            self.assertEqual(completed['allocation'],args['allocation'])
            with self.assertRaisesRegex(ValueError,'cap cannot change'):
                reserve_many(p,'inflate',calls={'full':1},**dict(args,allocation={'id':'probe','cap':4}))
            reserve_many(p,'remaining',calls={'terminal':2},**args)
            with self.assertRaisesRegex(ValueError,'allocation call budget'):
                reserve_many(p,'excess',calls={'full':1},**args)

    def test_allocation_does_not_override_global_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json'
            p.write_text(json.dumps(dict(campaign_id='test',protocol_sha256='a'*64,
                limits={'host_seconds':100},completed=[],reservations=[],calls_caps={'full':1})))
            args=dict(campaign_id='test',protocol_sha256='a'*64,resources={'host_seconds':1},
                      allocation={'id':'probe','cap':100},cap_key='full',calls=1)
            reserve(p,'first',**args)
            with self.assertRaisesRegex(ValueError,'stage call budget'):
                reserve(p,'second',**args)


if __name__=='__main__':unittest.main()
