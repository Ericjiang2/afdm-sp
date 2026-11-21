"""Finite BASE queue. No receiver implementation, retries, or quota replacement."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import tempfile

R=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909')
SOCKET='/data/guoyikun/tmp/g_afdm_supp0909.sock'
ADMISSION_SHA='ef352c5766c68825c7f33b5580cadf6c258d33f601e44efee27674cf95077a39'
RANGES=[(34,50),(50,66),(66,82),(82,98),(98,114),(114,130),(130,146),(146,162),(162,178),(178,192)]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):return json.loads(Path(path).read_text())


def atomic(path,value):
    path=Path(path)
    fd,temporary=tempfile.mkstemp(prefix=path.name+'.',suffix='.pending',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,indent=2,allow_nan=False);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def allowed(path):
    p=Path(path).resolve()
    if not p.is_relative_to(R):raise ValueError('path outside fixed output root')
    return p


def validate_manifest(path):
    m=read(path)
    if m.get('schema')!='baseline-queue-manifest-v1' or m.get('admission_sha256')!=ADMISSION_SHA:
        raise ValueError('fixed admission identity required')
    admission=allowed(m['admission'])
    if sha(admission)!=ADMISSION_SHA:raise ValueError('admission content mismatch')
    recipes=read(admission)['recipes']
    jobs=m['jobs']
    if [(j['start'],j['stop']) for j in jobs]!=RANGES:raise ValueError('exact ten remaining batches required')
    names=[];outputs=[];artifacts=[]
    for job in jobs:
        if not re.fullmatch(r'g_afdm_supp_base[A-Za-z0-9_]*',job['session']):raise ValueError('invalid task tmux name')
        names.append(job['session']);outputs.append(str(allowed(job['out'])))
        for k in ('script','exit','pid','log'):artifacts.append(str(allowed(job[k])))
        if not re.fullmatch('[0-9a-f]{64}',job['script_sha256']) or sha(job['script'])!=job['script_sha256']:
            raise ValueError('batch shell hash mismatch')
        if job['full_calls']!=(job['stop']-job['start'])*40:raise ValueError('wrong batch budget')
    if len(set(names))!=10 or len(set(outputs))!=10:raise ValueError('duplicate queue job/output')
    if len(set(artifacts+outputs))!=50:raise ValueError('queue artifact paths must be distinct')
    if len(recipes)!=40 or len({r['id'] for r in recipes})!=40:raise ValueError('exact forty unique recipes required')
    return m,recipes


def command(argv):
    return subprocess.run(argv,capture_output=True,text=True,timeout=15,check=False)


def snapshot(run=command):
    response=run(['tmux','-S',SOCKET,'list-panes','-a','-F','#{session_name}\t#{pane_pid}\t#{pane_dead}\t#{pane_id}'])
    if response.returncode:
        # Only the documented no-server response is an empty inventory. All
        # other observation failures remain unknown, never inferred as exit.
        if 'no server running' in response.stderr or 'No such file or directory' in response.stderr:
            return {}
        raise RuntimeError('tmux observation failed: '+response.stderr)
    rows={}
    for line in response.stdout.splitlines():
        name,pid,dead,pane=line.split('\t')
        if name in rows:raise RuntimeError('multiple panes in receiver session: '+name)
        rows[name]=dict(pid=int(pid),dead=bool(int(dead)),pane=pane)
    return rows


def receiver_count(rows):
    return sum(not v['dead'] and (name.startswith('g_afdm_supp_base') or name.startswith('g_afdm_supp_detector_'))
               for name,v in rows.items())


def process_identity(pid):
    try:text=Path(f'/proc/{pid}/stat').read_text()
    except FileNotFoundError:return None
    fields=text[text.rfind(')')+2:].split()
    if fields[0]=='Z':return None
    return dict(pid=pid,start_ticks=fields[19])


def gpu_conflict(run=command):
    value=run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used','--format=csv,noheader,nounits'])
    if value.returncode:raise RuntimeError('GPU observation failed: '+value.stderr)
    rows=[tuple(float(v.strip()) for v in line.split(',')) for line in value.stdout.splitlines()]
    if not rows or any(len(v)!=2 for v in rows):raise RuntimeError('invalid GPU observation')
    return any(util>90 and used>18*1024 for util,used in rows)


def validate_success(job,recipes):
    if Path(job['exit']).read_text().strip()!='0':raise ValueError('batch nonzero exit')
    out=Path(job['out']);summary=read(out/'summary.json');contract=read(out/'contract.json')
    payload={k:v for k,v in contract.items() if k not in ('config_sha256','ledger')}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    expected={(b,r['id']) for b in range(job['start'],job['stop']) for r in recipes}
    if (summary.get('status')!='complete' or summary.get('exitcode')!=0 or summary.get('failures') or
        summary.get('missing_or_failed_identities') or summary.get('calls_attempted')!=len(expected) or
        summary.get('calls_completed')!=len(expected) or summary.get('config_sha256')!=digest or
        contract.get('config_sha256')!=digest or contract.get('recipes')!=recipes or
        contract.get('start')!=job['start'] or contract.get('stop')!=job['stop'] or
        contract.get('split')!='design' or contract.get('snr')!=8 or contract.get('max_full_calls')!=len(expected)):
        raise ValueError('batch summary/configuration incomplete or mismatched')
    listed={Path(v['path']).resolve() for v in summary['records']}
    if listed!={p.resolve() for p in out.glob('frame-*.json')} or list(out.glob('failure-*.json')) or (out/'batch-failure.json').exists():
        raise ValueError('uncommitted extra frames or failure artifacts')
    seen=set();inputs={};recipe_by_id={r['id']:r for r in recipes}
    for record in summary['records']:
        path=Path(record['path']).resolve()
        if not path.is_relative_to(out.resolve()) or sha(path)!=record['sha256']:raise ValueError('record path/hash mismatch')
        row=read(path);key=(row['block_id'],row['arm_id'])
        if key not in expected or key in seen or row.get('failure') is not None or row.get('config_sha256')!=digest:
            raise ValueError('duplicate/mismatched/failed frame identity')
        if row.get('split')!='design' or row.get('SNR')!=8 or type(row.get('baseline_eligible')) is not bool:
            raise ValueError('frame domain/qualification missing')
        metadata=row.get('metadata',{})
        if (row.get('recipe')!=recipe_by_id[key[1]] or row.get('scenario')!='G0' or
            row.get('campaign_id')!=contract.get('campaign_id') or
            metadata.get('block')!=key[0] or metadata.get('split')!='design' or metadata.get('snr_db')!=8 or
            metadata.get('input_hashes')!=row.get('input_hashes') or
            metadata.get('protocol_sha256')!=contract.get('protocol_sha256') or
            any(row.get(k)!=contract.get(k) or k not in row or k not in contract
                for k in ('source_sha256','checkpoint_sha256','code_sha256','protocol_sha256'))):
            raise ValueError('frame source/recipe/metadata identity mismatch')
        if key[0] in inputs and inputs[key[0]]!=row['input_hashes']:raise ValueError('unpaired block inputs')
        inputs[key[0]]=row['input_hashes'];seen.add(key)
    if seen!=expected:raise ValueError('missing frame identities')
    return dict(summary_sha256=sha(out/'summary.json'),config_sha256=digest,full_calls=len(expected))


def validate_state(state,manifest,recipes,digest,deadline):
    if (state.get('schema')!='baseline-queue-state-v1' or state.get('manifest_sha256')!=digest or
        state.get('deadline_unix')!=deadline or not state['started_unix']<deadline<=state['started_unix']+4*3600 or
        type(state.get('halt_new')) is not bool):
        raise ValueError('restart must preserve exact manifest/deadline/state')
    jobs={j['session']:j for j in manifest['jobs']}
    if not set(state['jobs']).issubset(jobs):raise ValueError('unknown persisted job')
    for name,record in state['jobs'].items():
        if record.get('script_sha256')!=jobs[name]['script_sha256']:
            raise ValueError('persisted shell identity mismatch')
        if record.get('status') not in ('intent','running','complete','failed'):
            raise ValueError('unknown persisted job status')
        if record['status']!='intent':
            identity=record.get('process_identity',{})
            if (type(record.get('pid')) is not int or record['pid']<=0 or identity.get('pid')!=record['pid'] or
                not re.fullmatch(r'[0-9]+',str(identity.get('start_ticks',''))) or
                not re.fullmatch(r'%[0-9]+',str(record.get('pane','')))):
                raise ValueError('missing exact persisted process handle')
        if record['status']=='complete' and record.get('proof')!=validate_success(jobs[name],recipes):
            raise ValueError('completed proof changed since restart')


class Queue:
    def __init__(self,manifest,recipes,state,save,run=command,now=time.time,identity=process_identity):
        self.m,self.recipes,self.state,self.save=manifest,recipes,state,save
        self.run,self.now,self.identity=run,now,identity

    def halt(self,message):
        self.state['halt_new']=True
        self.state.setdefault('errors',[]).append(dict(unix=self.now(),message=str(message)))
        self.save(self.state)

    def observe(self,rows):
        for job in self.m['jobs']:
            record=self.state['jobs'].get(job['session'])
            if not record or record['status'] in ('complete','failed'):continue
            if record['status']=='intent':
                self.halt('unresolved launch intent; never automatically relaunch '+job['session']);continue
            current=rows.get(job['session']);identity=self.identity(record['pid'])
            if current and not current['dead']:
                if current['pid']!=record['pid'] or current['pane']!=record['pane'] or identity!=record['process_identity']:
                    self.halt('registered process identity conflict '+job['session'])
                continue
            if identity is not None:
                self.halt(('PID reuse conflict ' if identity!=record['process_identity'] else 'live registered process missing live tmux pane ')+job['session'])
                continue
            try:
                if int(Path(job['pid']).read_text().strip())!=record['pid']:raise ValueError('shell PID evidence mismatch')
                record['proof']=validate_success(job,self.recipes);record['status']='complete'
            except Exception as exc:
                record['status']='failed';record['failure']=str(exc);self.halt(str(exc))
            self.save(self.state)

    def step(self):
        if self.now()>=self.state['deadline_unix']:
            self.halt('queue deadline reached; running jobs are not killed');return 'deadline'
        try:rows=snapshot(self.run)
        except Exception as exc:self.halt(exc);return 'wait'
        self.state['last_observation']=dict(unix=self.now(),tmux=rows);self.save(self.state)
        try:self.observe(rows)
        except Exception as exc:self.halt('process observation failed: '+str(exc));return 'wait'
        unfinished=[v for v in self.state['jobs'].values() if v['status'] in ('running','intent')]
        if self.state['halt_new']:return 'wait' if unfinished else 'failed'
        pending=[j for j in self.m['jobs'] if j['session'] not in self.state['jobs']]
        if not pending:return 'wait' if unfinished else 'complete'
        capacity=max(0,2-receiver_count(rows))
        if not capacity:return 'wait'
        try:
            if gpu_conflict(self.run):return 'wait'
            if shutil.disk_usage(R).free<16*1024**3:return 'wait'
        except Exception as exc:self.halt(exc);return 'wait'
        for job in pending[:capacity]:
            if self.now()>=self.state['deadline_unix']:return 'wait'
            if receiver_count(rows)>=2:break
            if job['session'] in rows or any(Path(job[k]).exists() for k in ('out','exit','pid','log')):
                self.halt('unknown existing output/session; no retry '+job['session']);break
            if sha(job['script'])!=job['script_sha256'] or sha(self.m['admission'])!=ADMISSION_SHA:
                self.halt('shell/admission changed before launch');break
            self.state['jobs'][job['session']]=dict(status='intent',script_sha256=job['script_sha256'],started_unix=self.now())
            self.save(self.state)
            try:launch=self.run(['tmux','-S',SOCKET,'new-session','-d','-s',job['session'],'/bin/bash',job['script']])
            except Exception as exc:self.halt('tmux launch observation uncertain: '+str(exc));break
            if launch.returncode:
                self.halt('tmux launch uncertain/failed '+launch.stderr);break
            try:
                fresh=snapshot(self.run);pane=fresh[job['session']];identity=self.identity(pane['pid'])
                if pane['dead'] or identity is None:raise RuntimeError('launch identity unavailable')
                self.state['jobs'][job['session']].update(status='running',pid=pane['pid'],pane=pane['pane'],process_identity=identity)
                self.save(self.state);rows=fresh
            except Exception as exc:self.halt(exc);break
        return 'wait'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--state-dir',type=Path,required=True);p.add_argument('--deadline-unix',type=float,required=True)
    args=p.parse_args();manifest,recipes=validate_manifest(args.manifest);root=allowed(args.state_dir)
    root.mkdir(exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=root/'state.json';digest=sha(args.manifest)
        if path.exists():
            state=read(path)
            validate_state(state,manifest,recipes,digest,args.deadline_unix)
        else:
            now=time.time()
            if not now<args.deadline_unix<=now+4*3600:raise ValueError('deadline must be finite future within4hours')
            state=dict(schema='baseline-queue-state-v1',manifest_sha256=digest,deadline_unix=args.deadline_unix,
                started_unix=now,jobs={},halt_new=False,errors=[])
            atomic(path,state)
        queue=Queue(manifest,recipes,state,lambda value:atomic(path,value))
        while True:
            status=queue.step()
            if status in ('complete','failed','deadline'):
                atomic(root/'result.json',dict(status=status,exitcode=0 if status=='complete' else 1,state=state,
                    policy='no kills, no retries, no failed quota reclaim; active jobs may finish after deadline'))
                return 0 if status=='complete' else 1
            time.sleep(min(30,max(0,args.deadline_unix-time.time())))


if __name__=='__main__':raise SystemExit(main())
