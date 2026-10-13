"""Constructor and code-domain precheck; no channel generation or receiver F."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root):
    started=time.monotonic()
    source=root/'source-execution-count-v1';package=source/'afdm_sp_joint_unrolled'
    manifest=source/'source-manifest.json'
    def verify():
        assert sha(manifest)=='678b4d1997031d775239964edfc90daca81b0ad2349a8bc9c8dc841aa4e04921'
        assert json.loads(manifest.read_text())=={str(p.relative_to(package)):sha(p) for p in package.rglob('*.py')}
    verify();sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    c=json.loads((root/'contracts/execution-count-engineering-v1.json').read_text())
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    cache=Path(os.environ['XDG_CACHE_HOME'])/'codes';cache.mkdir()
    rows=[]
    for N,v in [(512,2.),(1024,2.),(2048,2.),(1024,0.),(1024,4.)]:
        assert time.monotonic()-started<120
        system=_make_config_a(N,v,8,10.,4.)
        code=build_code(n=2*N,cache_dir=cache)
        model=build_receiver(c['checkpoint_path'],system,N,'cpu',receiver_shell='direct40',active_cap=40)
        k=int(code['G'].shape[1]);K=2*system.k_max_cap+1
        assert model.cfg.N==N and model.cfg.k_max==system.k_max_cap
        rows.append(dict(N=N,v_mean=v,fs=system.fs,l_max=system.l_max_cap,
            k_max=system.k_max_cap,K=K,dictionary_columns=(system.l_max_cap+1)*K,
            delta_max=system.delta_max,nonoverlap_domain=bool(system.delta_max<N),
            c1=system.c1,c2=system.c2,code_n=code['n'],code_k=k,actual_code_rate=k/code['n'],
            code_identity=hashes({key:code[key] for key in CODE_KEYS}),checkpoint_load_success=True))
        del model,system,code
    verify()
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    assert sum(p.stat().st_size for p in cache.rglob('*') if p.is_file())<2*1024**3
    result=dict(status='COMPLETE',calls=dict(A=5,F=0,D=0),source_sha256=sha(manifest),
        script_sha256=sha(Path(__file__)),checkpoint_sha256=c['checkpoint_sha256'],rows=rows,
        wall_seconds=time.monotonic()-started,
        scope='actual constructor/code/checkpoint domain only; no generated channels, receiver simulation or scale timing')
    with (root/'evidence/scale-domain-precheck-v1.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main(Path(sys.argv[1]))
