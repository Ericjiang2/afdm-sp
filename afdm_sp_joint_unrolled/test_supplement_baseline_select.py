"""Synthetic fixtures only: no real receiver or development-data validation."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import supplement_baseline_select as select


def synthetic_rows():
    rows=[]
    for block in range(192):
        for recipe in select.catalogue():
            rows.append(dict(block_id=block,arm_id=recipe['id'],recipe=recipe,
                input_hashes={'synthetic_block':str(block)},source_sha256='synthetic-source',
                protocol_sha256='synthetic-protocol',checkpoint_sha256='synthetic-checkpoint',
                code_sha256='synthetic-code',FER=int(block==0),elapsed_seconds=1.,
                baseline_eligible=True,initial_estimator={'converged':True},
                channel_refit={'converged':True,'query_count':73}))
    return rows


def metric(family,fer,cost,qualified=True):
    return dict(family=family,FER=fer,mean_seconds=cost,qualified=qualified,budget_screen=True)


class SyntheticSelectionTests(unittest.TestCase):
    def test_complete_and_missing_and_duplicate(self):
        rows=synthetic_rows()
        self.assertEqual(len(select.index_complete(rows)),7680)
        for invalid in (rows[:-1],rows+[rows[0]]):
            with self.assertRaises(ValueError):select.index_complete(invalid)

    def test_same_block_and_source_required(self):
        for key,value in [('input_hashes',{'synthetic_block':'different'}),('source_sha256','different')]:
            rows=synthetic_rows();rows[0][key]=value
            with self.assertRaises(ValueError):select.index_complete(rows)

    def test_all780_actual_paired_bounds_and_direction(self):
        table=select.index_complete(synthetic_rows())
        ids=sorted(r['id'] for r in select.catalogue())
        table[1,ids[0]]['FER']=1
        result=select.paired_intervals(table)
        self.assertEqual(len(result),780)
        ci=result[ids[0],ids[1]]
        self.assertEqual((ci['W'],ci['L'],ci['n']),(1,0,192))
        self.assertAlmostEqual(ci['delta'],1/192)
        self.assertAlmostEqual(ci['tail_alpha'],.05/(4*780))
        self.assertLess(ci['lower'],ci['delta']);self.assertGreater(ci['upper'],ci['delta'])

    def test_unqualified_keeps_denominator(self):
        table=select.index_complete(synthetic_rows());identifier=select.catalogue()[0]['id']
        table[0,identifier]['baseline_eligible']=False
        table[0,identifier]['initial_estimator']['converged']=False
        with patch.object(select,'paired_intervals',return_value={}):
            with patch.object(select,'select_references',return_value={}):
                output=select.analyze(table,{'mean_seconds':1.})
        m=output['metrics'][identifier]
        self.assertEqual((m['n'],m['frame_errors'],m['qualification_failures']),(192,1,1))
        self.assertFalse(m['qualified'])
        self.assertEqual(m['qualification_failure_rate'],1/192)

    def test_bounded_stationarity_is_not_eligibility(self):
        row=next(r for r in synthetic_rows() if r['recipe']['family']=='bounded-param')
        row['channel_refit']['converged']=False
        self.assertTrue(select.qualification(row))
        row['channel_refit']['query_count']=74
        with self.assertRaises(ValueError):select.qualification(row)

    def test_false_qualification_cannot_contradict_diagnostics(self):
        row=synthetic_rows()[0];row['baseline_eligible']=False
        with self.assertRaises(ValueError):select.qualification(row)

    def test_direction_and_pareto_preference(self):
        metrics={'z':metric('first',.1,2),'a':metric('other',.2,1),'b':metric('third',.15,3)}
        intervals={('a','z'):{'lower':-.1,'upper':.3},('b','z'):{'lower':-.1,'upper':.3}}
        result=select.select_references(metrics,intervals)
        self.assertEqual(result['references'],['z','a'])
        intervals['a','z']['lower']=.001
        self.assertEqual(select.select_references(metrics,intervals)['references'],['z','b'])

    def test_reverse_interval_orientation_and_zero_gate(self):
        metrics={'a':metric('first',.1,1),'z':metric('other',.2,2)}
        self.assertEqual(select.select_references(metrics,{('a','z'):{'lower':-.3,'upper':0}})['references'],['a','z'])
        self.assertEqual(select.select_references(metrics,{('a','z'):{'lower':-.3,'upper':-.001}})['references'],['a'])

    def test_no_qualified_reference_fails(self):
        result=select.select_references({'a':metric('B0',0,1,False)}, {})
        self.assertEqual(result['references'],[])
        self.assertEqual(result['status'],'no_qualified_budget_reference')

    def test_raw_terminal_hash_and_count_validation(self):
        np=select.np
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'synthetic.npz'
            arrays={k:np.zeros(shape,dtype=complex) for k,shape in
                {'H':(1024,1024),'x_soft':(1024,),'mu':(1024,), 'llr':(2048,),
                 'y':(1024,),'pilot':(1024,),'constellation':(4,)}.items()}
            arrays.update(support=np.array([2]),gains=np.ones(1,dtype=complex),var=np.ones(1024),sigma2=np.array(1.),sigma2_terminal=np.array(1.),
                sigma2_thermal=np.array(1.),info=np.zeros(4,dtype=int),info_hat=np.zeros(4,dtype=int),
                coded=np.zeros(2048,dtype=int),decoded=np.zeros(2048,dtype=int),x_hard=np.ones(1024,dtype=complex))
            np.savez_compressed(path,**arrays)
            row=dict(terminal={'path':str(path),'sha256':select.file_hash(path),'bytes':path.stat().st_size},
                input_hashes={k:select.array_hash(arrays[k]) for k in ('info','coded','y','pilot')},
                H_data_source={'sha256':select.array_hash(arrays['H'])},sigma_value=1.,FER=0,
                coded_bit_errors=0,raw_bit_errors=0,decoded_codeword_bit_errors=0,
                raw_bits_denominator=2048,coded_bits_denominator=4)
            select.verify_terminal(root,row)
            row['FER']=1
            with self.assertRaises(ValueError):select.verify_terminal(root,row)
            row['FER']=0;row['terminal']['sha256']='tampered'
            with self.assertRaises(ValueError):select.verify_terminal(root,row)

    def test_a2_quote_binds_completed_sample_and_same_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def save(name,value):
                path=root/name;path.write_text(json.dumps(value))
                return {'path':str(path),'sha256':select.file_hash(path)}
            contract=dict(A2_source=select.A2_SOURCE,checkpoint_sha256=select.CHECKPOINT_HASH,
                prior_sha256=select.PRIOR_HASH,device='cuda:0',threads=1)
            contract['config_sha256']=select.config_hash(contract);config=contract['config_sha256']
            snapshot={'exitcode':0,'stdout':'0, GPU-abcdef-1234, 0, 0, 24564\n'}
            sample=save('sample.json',dict(attempt={'kind':'F','arm':'A2'},config_sha256=config,seconds=2.,
                gpu_occupancy_before=snapshot,gpu_occupancy_after=snapshot))
            log=root/'ssh-source.txt';log.write_text('unit fixture: BASE GPU-abcdef-1234')
            host=save('host.json',dict(base_ssh_captures=[dict(config_sha256='BASE',gpu_uuid='GPU-abcdef-1234',
                ssh_alias='unit-fixture',source={'path':str(log),'sha256':select.file_hash(log)})]))
            quote=dict(schema='supplement-A2-cost-quote-v1',campaign_id=select.CAMPAIGN_ID,
                reference='A2',boundary=select.COST_BOUNDARY,a2_contract=save('contract.json',contract),
                a2_complete=save('complete.json',dict(status='complete',exitcode=0,config_sha256=config,records=[sample])),
                host_binding=host,
                samples=[sample])
            batches=[dict(config_sha256='BASE',contract={'device':'cuda:0','threads':1})]
            path=root/'quote.json';path.write_text(json.dumps(quote))
            self.assertEqual(select.read_a2_quote(path,batches)['mean_seconds'],2.)
            good_host=quote['host_binding']
            quote['host_binding']=save('thin-host.json',dict(host_id='synthetic-host',config_sha256_to_host={config:'synthetic-host','BASE':'synthetic-host'}))
            path.write_text(json.dumps(quote))
            with self.assertRaisesRegex(ValueError,'SSH source'):select.read_a2_quote(path,batches)
            quote['host_binding']=good_host;path.write_text(json.dumps(quote))
            batches[0]['config_sha256']='unbound'
            with self.assertRaises(ValueError):select.read_a2_quote(path,batches)
            batches[0]['config_sha256']='BASE'
            quote['a2_complete']=save('complete.json',dict(status='complete',exitcode=0,config_sha256=config,records=[]))
            path.write_text(json.dumps(quote))
            with self.assertRaises(ValueError):select.read_a2_quote(path,batches)

    def test_hash_and_protocol_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'fixture.json';p.write_text('{}')
            with self.assertRaises(ValueError):select.read_json(p,'bad-sha')
            with self.assertRaises(ValueError):select.validate_selection_protocol(p)
            with self.assertRaises(ValueError):select.read_a2_quote(p,[])

    def test_existing_profile_v1_contract_and_samples_are_compatible(self):
        profile=Path(__file__).resolve().parent/'outputs_comprehensive_supplement_20260909/profile-v1'
        if not (profile/'contract.json').exists():self.skipTest('real profile artifact not available on this checkout')
        contract=json.loads((profile/'contract.json').read_text())
        self.assertEqual(select.config_hash(contract),contract['config_sha256'])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            def spec(path):return {'path':str(path),'sha256':select.file_hash(path)}
            log=root/'base-ssh-fixture.txt'
            log.write_text('synthetic BASE config only; BASE GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2')
            host=root/'host.json';host.write_text(json.dumps({'base_ssh_captures':[
                {'config_sha256':'BASE','gpu_uuid':'GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2',
                 'ssh_alias':'unit-fixture','source':spec(log)}]}))
            quote={'schema':'supplement-A2-cost-quote-v1','campaign_id':select.CAMPAIGN_ID,
                'reference':'A2','boundary':select.COST_BOUNDARY,'a2_contract':spec(profile/'contract.json'),
                'a2_complete':spec(profile/'complete.json'),'host_binding':spec(host),
                'samples':[spec(profile/'sample-F-001.json')]}
            path=root/'quote.json';path.write_text(json.dumps(quote))
            result=select.read_a2_quote(path,[{'config_sha256':'BASE','contract':{
                'device':contract['device'],'threads':contract['threads']}}])
            self.assertAlmostEqual(result['mean_seconds'],1.4238285649917088)
            self.assertEqual(result['n'],1)


if __name__=='__main__':unittest.main()
