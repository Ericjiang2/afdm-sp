"""Admission fixtures only, not structural fitting or receiver experiments."""
import json
from pathlib import Path
import tempfile
import unittest
from afdm_sp_joint_unrolled.direction_structure_run import admission,locate_normal


class AdmissionTests(unittest.TestCase):
    def test_frozen_prefix_and_engineering_block(self):
        a={'status':'algorithm_preregistered_before_structure_results','group':{
            'iterations_max':2000,'absolute_tolerance':1e-7,'relative_tolerance':1e-6}}
        r={'status':'allocation_frozen_before_structure_results','protocol_sha256':'fixture',
            'blocks':list(range(255)),'SNR':[7,8,9],'arms':['M_free','M_group','M_link','M_sham']}
        admission(a,r,'fixture','engineering',17,18,8)
        admission(a,r,'fixture','mechanism',0,255,9)
        for split,start,stop,snr in [('engineering',16,17,8),('engineering',17,18,7),
                                     ('mechanism',0,256,8),('design',0,1,8)]:
            with self.assertRaises(ValueError):admission(a,r,'fixture',split,start,stop,snr)
        with self.assertRaises(ValueError):admission(a,r,'wrong','mechanism',0,1,8)

    def test_normal_input_unique_and_bound(self):
        row={'split':'engineering','SNR':8,'block_id':17,'protocol_sha256':'fixture',
             'call_type':'full','failure':None,'evidence_kind':'unit-fixture'}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'normal-full-000017.json';p.write_text(json.dumps(row))
            self.assertEqual(locate_normal([root],17,'engineering',8,'fixture'),p)
            with self.assertRaises(ValueError):locate_normal([root,root],17,'engineering',8,'fixture')
            with self.assertRaises(ValueError):locate_normal([root],18,'engineering',8,'fixture')
            with self.assertRaises(ValueError):locate_normal([root],17,'engineering',8,'wrong')


    def test_actual_cpu_device_replaces_normal_cuda_metadata(self):
        import numpy as np
        from unittest.mock import patch
        from afdm_sp_joint_unrolled.direction_structure_run import terminal_record
        normal={'device':'cuda','dtype':'inherited_outer_complex64','S_submitted':[1,2],
                'arm_id':'Bstar-fixture','input_hashes':{}}
        snapshot={'Htrue':np.eye(2,dtype=complex),'coded':np.zeros(4,int)}
        prepared={'normal':normal,'snapshot':snapshot,'basis':np.eye(2), 'normal_record_sha256':'fixture'}
        result={'device':'cpu','atom_ids':[1,2],'Hfit':np.eye(2,dtype=complex),
            'sigma2_terminal':.1,'llr':np.ones(4),'x_hard':np.ones(2,complex),
            'arm_id':'M_free','oracle_information':'support','Hfit_sha256':'fixture',
            'coefficients':np.ones(2),'graphs':[],'info_errors':0,'FER':0,
            'decoded':np.zeros(4,int),'decode_ok':True,'mu':np.ones(2,complex),'var':np.ones(2),
            'residual':{'relative_vector_closure':0.,'energies':{'pilot_channel_error':0.}},
            'terminal_seconds':.1,'terminal_cpu_seconds':.1,'peak_gpu_bytes':0,
            'fit_seconds':.1,'fit_cpu_seconds':.1,'fit_diagnostics':{},'z_sha256':'fixture'}
        with patch('afdm_sp_joint_unrolled.direction_structure_run.validate_record',side_effect=lambda x,**k:x):
            row=terminal_record(prepared,result,'fixture','fixture',{}, {}, {})
        self.assertEqual(row['device'],'cpu')
        self.assertEqual(row['dtype'],{'fit':'complex128','terminal':'complex128'})
        self.assertEqual(normal['device'],'cuda')


if __name__=='__main__':unittest.main()
