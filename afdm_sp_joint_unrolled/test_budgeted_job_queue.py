import copy
import unittest

from afdm_sp_joint_unrolled.budgeted_job_queue import validate_packet


class PacketTests(unittest.TestCase):
    def test_new_campaign_uses_separate_ledger_and_single_thread_workers(self):
        packet = dict(stage='DIRECTION', reserved_seconds=126,
            remaining_seconds_at_registration=300, registered_unix=100,
            deadline_unix=226, estimated_seconds=100, margin_fraction=.2,
            slots=2, cpu_sets=[[0,1,2,3],[4,5,6,7]], blas_threads=1,
            campaign_remaining=dict(host_seconds=28800,gpu_seconds=28800,cpu_core_seconds=460800),
            jobs=[dict(name='new-campaign',argv=['python','probe.py'],device='cpu')])
        validate_packet(packet,110)
        for threads in (0, 2, 128, True, '1'):
            bad=copy.deepcopy(packet);bad['blas_threads']=threads
            with self.subTest(threads=threads), self.assertRaises(ValueError):
                validate_packet(bad,110)
        exhausted=copy.deepcopy(packet)
        exhausted['campaign_remaining']['host_seconds']=100
        # A generous old-v3 ledger must never authorize a new campaign packet.
        exhausted['v3_remaining']=packet['campaign_remaining'].copy()
        with self.assertRaises(ValueError):validate_packet(exhausted,110)

    def test_budget_deadline_and_resource_contracts(self):
        good = dict(stage='S3S4', reserved_seconds=126, remaining_seconds_at_registration=300,
                    registered_unix=100, deadline_unix=226, estimated_seconds=100,
                    margin_fraction=.2, slots=2, cpu_sets=[[0,1,2,3],[4,5,6,7]],
                    jobs=[dict(name='probe',argv=['python','probe.py'],device='cpu')])
        validate_packet(good, 110)
        v3=copy.deepcopy(good)
        v3.update(stage='V3',v3_remaining=dict(host_seconds=28800,gpu_seconds=28800,cpu_core_seconds=460800))
        validate_packet(v3,110)
        v3['v3_remaining']['cpu_core_seconds']=1000
        with self.assertRaises(ValueError):validate_packet(v3,110)
        for key, value in [('stage','S1'),('remaining_seconds_at_registration',119),
                           ('deadline_unix',227),('margin_fraction',.19),('estimated_seconds',101),
                           ('slots',3),('cpu_sets',[[0,1,2,3],[3,4,5,6]])]:
            bad = copy.deepcopy(good)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_packet(bad, 110)
        with self.assertRaises(ValueError):
            validate_packet(good, 226)


if __name__ == '__main__':
    unittest.main()
