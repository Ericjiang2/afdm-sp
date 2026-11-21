"""Synthetic contracts for the frozen A transfer analysis; never runs a receiver."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import c1A_io as IO
import numpy as np
import c1A_stats as S
import c1A_transfer as T


class ArchiveIsolation(unittest.TestCase):
    def test_excluded_SOURCE_truth_never_decoded_fixed_endpoint_retained(self):
        meta=dict(status='ok',frame=200,arm='E10',snr_centi_db=650,rho_permille=300,
                  L=16,K=128,sigma2=10**(-.65),info_sha256='i',noise_sha256='n',
                  physical_gains_sha256='g',channel_seed=3,syn1=0,dsha1='d'*64,
                  R=10,schedule=[20]*10)
        full=dict(meta)
        for r in range(1,11):
            full.update({f'ierr{r}':int(r>1),f'syn{r}':0,f'dsha{r}':'d'*64})
        excluded=dict(meta,frame=0)
        doc={'_config':dict(nshard=1,shard=0,frame_offset=0,
                           resolved=dict(cells=[[6.5,.3,[16]]],frames=600,arms=['E10']))}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); directory=root/'out'/'fixture'; directory.mkdir(parents=True)
            cp=directory/'config_shard000.json'; cp.write_text(json.dumps(doc))
            (directory/'REMOTE_ROWS_MD5.txt').write_text('fixture')
            with patch.object(T,'_config_inventory',return_value=([(directory/'rows',cp,{})],[(cp,doc)])), \
                 patch.object(IO,'rows',return_value=iter([(1,excluded,b'TRUTH_MUST_STAY_OPAQUE'),
                     (2,meta,json.dumps(full).encode())])):
                records,_,_=T._load_archive(root,'fixture',[(650,300,16)],('E10',),range(200,201),10,'source')
            labels=records[(650,300,16,'E10',200)]['labels']
            self.assertEqual(labels,[0]+[1]*9) # syn1=0 cannot override future error

    def test_projector_decodes_only_top_level_allowlist(self):
        forbidden = "NEVER_DECODE_THIS_LABEL"
        row = (
            '{"syn1":3,"\\u0069err1":"' + forbidden + '",'
            '"future":{"syn2":"' + forbidden + '","nested":{"syn1":99}},'
            '"ignored":["' + forbidden + '",{"deep":[1,2]}],'
            '"arm":"R4T20"}'
        )
        loads = json.loads
        decoded = []

        def observe(value, *args, **kwargs):
            self.assertNotIn(forbidden, value)
            decoded.append(value)
            return loads(value, *args, **kwargs)

        with patch.object(IO.json, "loads", side_effect=observe):
            projected = IO.project(row)
        self.assertEqual(projected, {"syn1": 3, "arm": "R4T20"})
        self.assertNotIn("99", decoded)

    def test_projector_rejects_duplicate_allowed_and_malformed_outer_json(self):
        for row in ('{"syn1":1,"syn1":2}', '{"syn1":1} false', '{"syn1":1',
                    '{"syn1":1 "arm":"R4T20"}'):
            with self.subTest(row=row), self.assertRaises(ValueError):
                IO.project(row)

    def test_gzip_plain_dedup_is_based_on_uncompressed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            raw = b'{"syn1":2,"ierr1":0}\n'
            plain = base / "rows_shard000.jsonl"
            zipped = base / "rows_shard000.jsonl.gz"
            plain.write_bytes(raw)
            with gzip.open(zipped, "wb") as stream:
                stream.write(raw)
            (base / "config_shard000.json").write_text("{}")
            (base / 'REMOTE_ROWS_MD5.txt').write_text(hashlib.md5(raw).hexdigest()+'  rows_shard000.jsonl\n')
            found = IO.shard_files(base)
            self.assertEqual(len(found), 1)
            selected, _, hashes = found[0]
            self.assertEqual(selected, zipped)
            self.assertEqual({item["uncompressed_md5"] for item in hashes.values()},
                             {hashlib.md5(raw).hexdigest()})
            self.assertEqual([meta for _, meta in IO.rows(selected)], [{"syn1": 2}])
            with gzip.open(zipped, "wb") as stream:
                stream.write(raw.replace(b'"syn1":2', b'"syn1":3'))
            with self.assertRaisesRegex(ValueError, "conflicting"):
                IO.shard_files(base)


def primary_configs():
    out=[]
    for f,(s,r,loads) in T.PRIMARY.items():
        for L in loads:
            for inner in (20,40):
                for cap in range(1,5):
                    out.append(dict(id=f'{f}_{L}_{inner}_{cap}',cohort='primary',family=f,
                                    snr_centi_db=s,rho_permille=r,L=L,K=8*L,T=inner,Rc=cap,nframes=200))
    return out


class PredictiveContracts(unittest.TestCase):
    def test_features_have_correct_receiver_units_and_remaining_budget(self):
        x=T.model_features('A',[3],650,300,16,40,4)[0]
        np.testing.assert_allclose(x,[np.log(4),1,.4,.125,np.log(10**(-.65)/1.4),.3,.0375])
        self.assertEqual(T.model_features('G',[3],650,300,16,40,4).shape,(1,3))
        self.assertEqual(T.model_features('C',[3],650,300,16,40,4).shape,(1,4))

    def test_exact_constant_drop_and_C_bounds(self):
        x=np.column_stack((np.linspace(-2,2,30),np.full(30,50.)))
        y=np.array([0]*15+[1]*15,float)
        m=T._fit_once(x,y,np.ones(30),.1,'A')
        self.assertEqual(m['columns_dropped'],[1])
        self.assertEqual(m['columns_kept'],[0])
        self.assertAlmostEqual(m['mean'][0],0.)
        xx=np.random.default_rng(8).normal(size=(80,4))
        yy=(xx[:,0]+xx[:,1]-xx[:,2]-xx[:,3]>0).astype(float)
        c=T._fit_once(xx,yy,np.ones(80),.1,'C')
        for index,value in zip(c['columns_kept'],c['coef']):
            self.assertGreaterEqual(value,0) if index<2 else self.assertLessEqual(value,0)

    def test_source_groupCV_standardises_training_only(self):
        frame=np.repeat(np.arange(200,210),2)
        x=np.column_stack((frame,frame%3)).astype(float)
        y=(frame%2).astype(float)
        seen=[]
        def fit(xx,yy,ww,lam,name):
            seen.append(set(xx[:,0]))
            return dict(columns_kept=[0,1],mean=[0.,0.],sd=[1.,1.],intercept=0.,coef=[0.,0.],ridge=lam)
        with patch.object(T,'_fit_once',side_effect=fit):
            m=T.fit_model(x,y,frame,np.ones(20),'A')
        self.assertEqual(len(seen),26)
        for j,s in enumerate(seen[:-1]):
            self.assertEqual(s,set(f for f in range(200,210) if f%5!=j%5))
        self.assertEqual(m['ridge'],10.)  # all CV scores tie -> larger lambda

    def test_truth_future_and_row_order_cannot_enter_predictions(self):
        cfg=primary_configs()
        model=dict(columns_kept=[0,1,2],mean=[0]*3,sd=[1]*3,coef=[-.1,.2,-.3],intercept=0.)
        models={name:dict(model,columns_kept=list(range(7 if name=='A' else 4 if name=='C' else 3)),
                           mean=[0.]*(7 if name=='A' else 4 if name=='C' else 3),
                           sd=[1.]*(7 if name=='A' else 4 if name=='C' else 3),
                           coef=[.1]*(7 if name=='A' else 4 if name=='C' else 3)) for name in ('A','G','C')}
        rows={c['id']:[dict(syn1=j%10,ierr1=0,syn4=1026) for j in range(200)] for c in cfg}
        with patch.object(T,'_nearest',return_value=.1):
            a=T.predict_all(models,{},cfg,rows)
            for rr in rows.values():
                for r in rr:
                    r['ierr1']=987
                    r.pop('syn4')
            b=T.predict_all(models,{},cfg,rows)
            rev=T.predict_all(models,{},list(reversed(cfg)),rows)
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(a,rev[:,::-1])
        self.assertEqual(S.static_predictions(cfg,a),S.static_predictions(cfg,b))

    def test_wrong_seal_rejected_before_target_reader(self):
        args=argparse.Namespace(out=Path('never_existing_A_unit_out'),seal=Path('unused'),seal_md5='wrong')
        with patch.object(T,'_verify_protocol'),patch.object(T.io,'digest',return_value='actual'), \
             patch.object(T,'_eval_labels',side_effect=AssertionError('truth opened')):
            with self.assertRaisesRegex(ValueError,'seal MD5 mismatch'):
                T.evaluate(args)

    def test_margin_ties_and_alias_schema(self):
        cfg=primary_configs()
        task=S.design_tasks(cfg)[0]
        pe=np.full(len(cfg),.081)
        self.assertIsNone(S.select_config(pe,task['candidate_indices']))
        pe[task['candidate_indices'][-1]]=.08
        self.assertEqual(S.select_config(pe,task['candidate_indices']),task['candidate_indices'][-1])
        pe[task['candidate_indices']]=.01
        i=S.select_config(pe,task['candidate_indices'])
        self.assertEqual((cfg[i]['T'],cfg[i]['Rc']),(20,1))

    def test_fixed_endpoint_and_unsafe_cost_accounting(self):
        cfg=primary_configs()
        qbar=np.ones((1,4,len(cfg)))
        ybar=np.ones((1,len(cfg)))
        task=S.design_tasks(cfg)[0]
        cheap,expensive=task['candidate_indices'][0],task['candidate_indices'][-1]
        qbar[:,:,cheap]=.01
        ybar[:,expensive]=0.
        p=S.design_batch(cfg,qbar,ybar)
        self.assertEqual(p['J'][0,0,0],1.) # cheapest prediction is unsafe: no credit
        self.assertTrue(p['false_feasible'][0,0,0])
        qbar[:,:,cheap]=1.
        p=S.design_batch(cfg,qbar,ybar)
        self.assertTrue(p['false_abstention'][0,0,0])
        ybar[:,expensive]=1.
        self.assertEqual(S.design_batch(cfg,qbar,ybar)['J'][0,0,0],0.)

    def test_syn_zero_does_not_force_terminal_error_zero(self):
        a=T.model_features('A',[0],800,300,28,20,1)
        b=T.model_features('A',[0],800,300,28,20,4)
        self.assertNotEqual(a[0,2],b[0,2])
        self.assertNotEqual(a[0,5],b[0,5])
        # Fixed endpoint labels stay separate from syndrome, no early-stop helper.
        self.assertNotIn('terminal_labels',T._eval_labels.__code__.co_names)

    def test_global_parent_bootstrap_sync_and_reselection(self):
        w=S.frame_weights(80,20261017)
        np.testing.assert_allclose(w.sum(axis=1),1.)
        cfg=primary_configs()
        q=np.full((4,len(cfg),200),.1)
        y=np.zeros((len(cfg),200))
        q[:,:,0]=.9
        y[:,0]=1.
        qb=np.stack([w@q[m].T for m in range(4)],axis=1)
        yb=w@y.T
        np.testing.assert_allclose(qb[:,:,0],qb[:,:,20])
        np.testing.assert_allclose(yb[:,0],yb[:,20])
        # Two draws force different forecast-selected configs and references.
        task=S.design_tasks(cfg)[0]; ids=task['candidate_indices']
        qm=np.full((2,4,len(cfg)),1.); ym=np.ones((2,len(cfg)))
        qm[0,:,ids[0]]=.02; qm[1,:,ids[-1]]=.02
        ym[0,ids[0]]=0.; ym[1,ids[-1]]=0.
        p=S.design_batch(cfg,qm,ym)
        self.assertEqual(p['picked'][0,0,0],ids[0]); self.assertEqual(p['picked'][1,0,0],ids[-1])
        self.assertEqual(p['oracle'][0,0],ids[0]); self.assertEqual(p['oracle'][1,0],ids[-1])

    def test_CP_known_edges_and_population_oracle_bounds(self):
        a=.01/576
        self.assertAlmostEqual(S.cp_band(0)['upper'],1-a**(1/200))
        self.assertEqual(S.cp_band(200)['upper'],1.)
        cfg=primary_configs(); ids=S.design_tasks(cfg)[0]['candidate_indices']
        bands={i:dict(lower=.05,upper=.15) for i in ids}
        bands[ids[-1]]=dict(lower=.01,upper=.09)
        pop=S.population_task(cfg,ids,bands,ids[-1])
        self.assertEqual(pop['definite_min_cost'],160)
        self.assertEqual(pop['possible_min_cost'],20)
        self.assertEqual(pop['regret_upper'],7.)
        self.assertFalse(pop['certified'])
        self.assertEqual(S.population_task(cfg,ids,bands,-1)['status'],'UNRESOLVED_REJECTION')

    def test_PAVA_upward_crossing_and_censor(self):
        np.testing.assert_allclose(S.pava([.55,.45,.8],[1,1,1]),[.5,.5,.8])
        self.assertEqual(S.crossing_05([1,2,3],[.5,.5,.8])['status'],'left_censored')
        self.assertEqual(S.crossing_05([1,2,3],[.1,.2,.4])['status'],'right_censored')
        self.assertAlmostEqual(S.crossing_05([1,2,3],[.2,.6,.8])['Kc'],1.75)

    def test_primary_counts_weights_and_boundary_union(self):
        cfg=primary_configs(); weights=S._risk_weights(cfg)
        self.assertEqual(np.count_nonzero(weights),204)
        self.assertEqual(len(S.design_tasks(cfg)),23)
        for f in S.FAMILIES:
            self.assertAlmostEqual(sum(weights[i] for i,c in enumerate(cfg) if c['family']==f),.2)
        self.assertAlmostEqual(S._task_weights(S.design_tasks(cfg)).sum(),1.)
        qb=np.full((4,len(cfg)),.1)
        panel=S.boundary_panel(cfg,qb)
        self.assertEqual(len(panel),34)
        self.assertTrue(all(cfg[i]['Rc']==2 and cfg[i]['T']==20 for i in panel))
        self.assertEqual(S.GAIN_ALPHA,.04/12)
        self.assertEqual(S.KILL_ALPHA,.05/7)

    def test_full_stats_smoke_zero_effect_no_fake_PASS(self):
        cfg=primary_configs()
        q=np.full((4,len(cfg),200),.02)
        y=np.zeros((len(cfg),200))
        a=S.evaluate(cfg,q,y,audit=dict(integrity_pass=True),bootstrap_draws=24)
        self.assertTrue(a['gates']['A0']['pass_gate'])
        self.assertFalse(a['gates']['A2']['pass_gate'])
        self.assertFalse(a['gates']['A3']['pass_gate'])
        self.assertTrue(a['kills']['K-A2']['triggered'])
        self.assertEqual(a['J']['A']['point'],0.)
        self.assertEqual(a['Brier_gains']['G']['point'],0.)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "ok": result.wasSuccessful(),
        "tests": result.testsRun,
        "failures": [str(test) + ": " + message for test, message in result.failures],
        "errors": [str(test) + ": " + message for test, message in result.errors],
        "_argv": sys.argv,
        "_config": {"synthetic_only": True, "receiver_execution": False},
        "input": {"kind": "generated_in_memory", "external_rows": 0},
        "code_md5": {path.name: hashlib.md5(path.read_bytes()).hexdigest()
                     for path in (Path(__file__),
                                  *(Path(__file__).with_name(name) for name in
                                    ("c1A_io.py", "c1A_transfer.py", "c1A_stats.py")))
                     if path.is_file()},
        "thread_env": {key: os.environ.get(key) for key in
                       ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
    }
    if args.out is not None:
        args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
