import hashlib,json,os,shlex,subprocess,time
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908'); ev=root/'evidence'; src=root/'source-runtime-v10'
expected=json.loads((ev/'source-snapshot-runtime-v10.json').read_text())
actual={str(f.relative_to(src)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((src/'afdm_sp_joint_unrolled').rglob('*.py'))}
assert actual==expected,'source changed'
assert not (root/'physical-design-v10').exists(),'existing run: inspect, never restart'
ledger=json.loads((root/'resource-ledger.json').read_text());assert not ledger['reservations']
assert sum(r.get('calls',{}).get('prototype_full',0) for r in ledger['completed'])+768<=2304
assert not subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip(),'GPU occupied'
worker=ev/'physical-development-worker-v10.py'
assert not worker.exists(),'worker already exists'
worker.write_text(r'''import json,os,subprocess,time,traceback
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908');ev=root/'evidence';src=root/'source-runtime-v10'
state={'status':'running','pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().split()[21],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'started_unix':time.time()}
def save():
 p=ev/'physical-development-v10-status.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(ev/'physical-development-v10-status.json')
save();deadline=time.time()+2400
cmd=['timeout','--kill-after=5','2410','taskset','-c','0-3','/home/guoyikun/.conda/envs/AFDM/bin/python','-m','afdm_sp_joint_unrolled.direction_run','--protocol',str(src/'issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/campaign-protocol.json'),'--checkpoint','/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk','--split','design','--start','0','--stop','192','--snr','8','--recipes','all','--out',str(root/'physical-design-v10'),'--device','cuda','--deadline-unix',str(deadline),'--max-full-calls','768','--ledger',str(root/'resource-ledger.json'),'--physical-registry',str(src/'issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/physical-algorithm-preregister.json'),'--physical-admission',str(ev/'physical-development-admission-v10.json'),'--physical-admission-sha256','8f5f2490683bd5b9f33fe65957b2d50d5fe29d1bc6c1a1609180cb9904e49a48']
state.update(command=cmd,deadline_unix=deadline);save()
try:
 with (ev/'physical-development-v10.log').open('w') as log:
  child=subprocess.Popen(cmd,cwd=src,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT)
  state['child_pid']=child.pid;state['child_start_ticks']=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21];save()
  rc=child.wait()
 state.update(exit_code=rc,status='complete' if rc==0 else 'failed')
except BaseException as exc:state.update(status='failed',error=repr(exc),traceback=traceback.format_exc())
finally:state['finished_unix']=time.time();save()
''')
receipt={'status':'launching','tmux':'g_direction_physical_development_v10','worker':str(worker),'status_path':str(ev/'physical-development-v10-status.json'),'source':'source-runtime-v10','job':'physical-design-v10','calls_max':768,'stage':'prototype_full','log':str(ev/'physical-development-v10.log'),'scope':'frozen192 paired blocks at8dB, four arms, no interim selection'}
(ev/'active-physical-development-v10.json').write_text(json.dumps(receipt,indent=2)+'\n')
subprocess.run(['tmux','new-session','-d','-s',receipt['tmux'],'exec /home/guoyikun/.conda/envs/AFDM/bin/python '+shlex.quote(str(worker))],check=True)
print(json.dumps(receipt))
