"""Synthetic contract tests; these do not execute an AFDM receiver."""
import hashlib
import json
from types import SimpleNamespace
import time
import unittest
import tempfile
from pathlib import Path

class Raises:
    @staticmethod
    def raises(kind, match=None):
        case=unittest.TestCase()
        return case.assertRaisesRegex(kind,match) if match else case.assertRaises(kind)
pytest=Raises()
from .supplement_pilot_run import identities, validate_args, reserve, assert_unchanged, CAMPAIGN_ID, validate_geometry


def contract(ids,key='a',bindings=None):
    return dict(campaign_id=CAMPAIGN_ID,identities=ids,max_full_calls=len(ids),
                bindings=bindings or {'frozen':'same'},config_sha256=key,calls_reserved={'F':len(ids),'T':0,'E':0})


def test_frozen_counts_and_distinct_modes():
    fixed=sum((identities('Pfixed',b,b+16) for b in range(0,192,16)),[])
    matched=sum((identities('Pmatched',b,b+16) for b in range(0,192,16)),[])
    assert len(fixed)==1728 and len(matched)==4608
    assert len(set(fixed+matched))==6336


def test_reject_identity_boundaries():
    for mode,start,stop in [('confirm',0,1),('Pfixed',0,17),('Pmatched',191,193),('Pfixed',3,3)]:
        with pytest.raises(ValueError):identities(mode,start,stop)


def test_budget_and_deadline():
    args=SimpleNamespace(mode='Pfixed',start=0,stop=1,max_full_calls=9,
                         deadline_unix=time.time()+60,max_output_bytes=300*1024**2)
    assert len(validate_args(args))==9
    for key,value in [('max_full_calls',10),('deadline_unix',float('inf')),('max_output_bytes',1)]:
        bad=SimpleNamespace(**vars(args));setattr(bad,key,value)
        with pytest.raises(ValueError):validate_args(bad)


def test_duplicate_and_binding_rejection(tmp_path):
    ids=identities('Pfixed',0,1);reserve(tmp_path,contract(ids))
    with pytest.raises(ValueError,match='already reserved'):reserve(tmp_path,contract(ids,'b'))
    with pytest.raises(ValueError,match='binding'):
        reserve(tmp_path,contract(identities('Pfixed',1,2),'c',{'frozen':'changed'}))
    reserve(tmp_path,contract(identities('Pmatched',0,1),'d'))


def test_full_ledger_and_cap(tmp_path):
    for mode in ('Pfixed','Pmatched'):
        for b in range(0,192,16):reserve(tmp_path,contract(identities(mode,b,b+16),f'{mode}-{b}'))
    assert sum(json.loads(p.read_text())['max_full_calls'] for p in tmp_path.glob('reservation-*.json'))==6336
    with pytest.raises(ValueError):reserve(tmp_path,contract([('invalid',0,8,'p0','x')],'overflow'))


def test_missing_input_never_falls_back(tmp_path):
    args=SimpleNamespace(protocol=tmp_path/'missing')
    with pytest.raises(FileNotFoundError):assert_unchanged(args,{'files':{},'source_sha256':{}})


def test_corrupt_historical_ledger(tmp_path):
    row=contract(identities('Pfixed',0,1));row['identities'].append(row['identities'][0])
    (tmp_path/'reservation-corrupt.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='accounting'):reserve(tmp_path,contract(identities('Pfixed',1,2),'next'))


def test_geometry_contract():
    protocol=dict(N=1024,l_max=102,k_max=2,rho=.5,prefix_length=102,papr_limit_db=12.,peak_power_limit=16.)
    manifest={'geometry':dict(N=1024,l_max=102,k_max=2,c1=.01,c2=.02)}
    system=SimpleNamespace(c1=.01,c2=.02,rho=.5)
    assert validate_geometry(manifest,protocol,system)['prefix_length']==102
    protocol['papr_limit_db']=13
    with pytest.raises(ValueError):validate_geometry(manifest,protocol,system)


def test_historical_overlap(tmp_path):
    row=contract(identities('Pfixed',0,1))
    for key in ('a','b'):(tmp_path/f'reservation-{key}.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='overlap'):reserve(tmp_path,contract(identities('Pfixed',1,2),'next'))


def test_summary_binding_structure():
    # Static sequence contract only: no receiver or synthetic execution claimed.
    import ast
    import inspect
    from .supplement_pilot_run import execute
    source=inspect.getsource(execute)
    assert source.index('publish(name,row)')<source.index('records.append(')<source.index('completed.append(identity)')
    tree=ast.parse(source)
    summary=next(node for node in ast.walk(tree) if isinstance(node,ast.Call)
                 and isinstance(node.func,ast.Name) and node.func.id=='publish'
                 and node.args and isinstance(node.args[0],ast.Constant)
                 and node.args[0].value=='summary.json')
    fields={item.arg:ast.unparse(item.value) for item in summary.args[1].keywords}
    assert fields['records']=='records' and fields['exitcode']=='int(bool(failures))'
    assert 'sha256=sha(path)' in source


class PilotRunnerContracts(unittest.TestCase):
    pass


def _wrap(fn):
    def run(self):
        if fn.__code__.co_argcount:
            with tempfile.TemporaryDirectory() as directory:fn(Path(directory))
        else:fn()
    return run


for _name,_fn in list(globals().items()):
    if _name.startswith('test_') and callable(_fn):setattr(PilotRunnerContracts,_name,_wrap(_fn))


if __name__=='__main__':unittest.main()
