import hashlib,json,os,shlex,subprocess,time
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908')
src=root/'source-runtime-v9'; ev=root/'evidence'; task='issues/2026-09-08_21-06-44-afdm-direction-decision/evidence'
expected=json.loads((ev/'source-snapshot-runtime-v9.json').read_text())
actual={str(f.relative_to(src)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((src/'afdm_sp_joint_unrolled').rglob('*.py'))}
assert actual==expected, {'missing':list(set(expected)-set(actual)), 'extra':list(set(actual)-set(expected)), 'different':[k for k in expected if actual.get(k)!=expected[k]]}
ledger=json.loads((root/'resource-ledger.json').read_text());assert not ledger['reservations']
assert sum(r.get('calls',{}).get('engineering_full',0) for r in ledger['completed'])+18<=128
for name in ('physical-baseline-v8','physical-baseline-v9','physical-engineering-v9'):
    assert not (root/name).exists(), name+' already exists; inspect rather than restart'
apps=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip()
assert not apps, 'GPU occupied: '+apps
# Conservative bounded setup debit, separate from actual receiver cost.
import sys
sys.path.insert(0,str(src))
from afdm_sp_joint_unrolled.direction_budget import locked
with locked(root/'resource-ledger.json') as state:
    assert not any(r['id']=='physical-v9-setup-overhead' for r in state['completed'])
    resources=dict(host_seconds=180.,gpu_seconds=0.,cpu_core_seconds=180.)
    for key,limit in state['limits'].items():assert sum(r[key] for r in state['completed'])+resources[key]+(600 if key!='cpu_core_seconds' else 2400)<=limit
    state['completed'].append(dict(id='physical-v9-setup-overhead',calls={},evidence='evidence/physical-engineering-admission-v9.json',status='conservative_setup_bound',**resources))
worker=ev/'physical-engineering-worker-v9.py'
worker.write_text(r'''import json,os,subprocess,time,traceback
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908'); ev=root/'evidence'
py='/home/guoyikun/.conda/envs/AFDM/bin/python'; task='issues/2026-09-08_21-06-44-afdm-direction-decision/evidence'
state={'status':'running','pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().split()[21],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'started_unix':time.time(),'jobs':[]}
def save():
    temp=ev/'physical-engineering-v9-status.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(ev/'physical-engineering-v9-status.json')
save();deadline=time.time()+600
try:
    for name,version,stop,recipes,calls in [('physical-baseline-v8',8,23,'sbl-s0.5',1),('physical-baseline-v9',9,23,'sbl-s0.5',1),('physical-engineering-v9',9,26,'all',16)]:
        src=root/f'source-runtime-v{version}'
        cmd=['taskset','-c','0-3',py,'-m','afdm_sp_joint_unrolled.direction_run','--protocol',str(src/task/'campaign-protocol.json'),'--checkpoint','/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk','--split','engineering','--start','22','--stop',str(stop),'--snr','8','--recipes',recipes,'--out',str(root/name),'--device','cuda','--deadline-unix',str(deadline),'--max-full-calls',str(calls),'--ledger',str(root/'resource-ledger.json')]
        if name=='physical-engineering-v9':cmd+=['--physical-registry',str(src/task/'physical-algorithm-preregister.json')]
        job={'id':name,'command':cmd,'status':'running'};state['jobs'].append(job);save()
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with (ev/(name+'.log')).open('w') as log:
            child=subprocess.Popen(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT)
            job['pid']=child.pid;save()
            rc=child.wait(timeout=max(1.,deadline-time.time()+10))
        job.update(exit_code=rc,status='complete' if rc==0 else 'failed');save()
        if rc:raise RuntimeError('job failed: '+name)
    state['status']='complete'
except Exception as exc:
    state.update(status='failed',error=repr(exc),traceback=traceback.format_exc())
finally:
    state['finished_unix']=time.time();save()
''')
receipt={'status':'launching','tmux':'g_direction_physical_engineering_v9','worker':str(worker),'status_path':str(ev/'physical-engineering-v9-status.json'),'calls_max':18,'engineering_before':110,'engineering_after_max':128,'source_manifest':str(ev/'source-snapshot-runtime-v9.json'),'gpu_apps_before':apps,'scope':'two same-frame B_star source-regression controls then16full four-arm engineering calls; no development population'}
(ev/'active-physical-engineering-v9.json').write_text(json.dumps(receipt,indent=2)+'\n')
subprocess.run(['tmux','new-session','-d','-s',receipt['tmux'],'exec /home/guoyikun/.conda/envs/AFDM/bin/python '+shlex.quote(str(worker))],check=True)
print(json.dumps(receipt))
