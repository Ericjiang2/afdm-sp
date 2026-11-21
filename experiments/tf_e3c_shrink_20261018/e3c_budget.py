"""Conservative single-thread elapsed core-second ledger, including failed leases.

All engineering and production receiver invocations must share this directory.
A reservation prevents aggregate concurrent leases from exceeding 15 core-hours.
Interrupted/killed leases remain charged at their full reservation until reviewed.
"""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import signal
import time
import uuid

LIMIT_SECONDS = 15 * 3600.


class BudgetLease:
    def __init__(self, directory, seconds, argv, started=None):
        self.directory=Path(directory)
        self.seconds=float(seconds)
        self.argv=argv
        self.started=time.perf_counter() if started is None else started
        self.token=uuid.uuid4().hex

    def update(self, finish=False, error=None):
        self.directory.mkdir(parents=True,exist_ok=True)
        ledger=self.directory/'budget.json'
        with (self.directory/'budget.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=json.loads(ledger.read_text()) if ledger.exists() else dict(limit_seconds=LIMIT_SECONDS,leases={})
            if state['limit_seconds'] != LIMIT_SECONDS:
                raise RuntimeError('budget limit may not be changed')
            if not finish:
                charged=sum(x.get('actual_seconds',x['reserved_seconds']) for x in state['leases'].values())
                if charged+self.seconds>LIMIT_SECONDS:
                    raise RuntimeError(f'budget reservation denied: {charged}+{self.seconds}>{LIMIT_SECONDS}')
                state['leases'][self.token]=dict(pid=os.getpid(),argv=self.argv,reserved_seconds=self.seconds,status='running',start_unix=time.time())
            else:
                actual=time.perf_counter()-self.started
                state['leases'][self.token].update(status='failed' if error else 'complete',actual_seconds=actual,error=error)
            tmp=ledger.with_suffix('.tmp')
            tmp.write_text(json.dumps(state,indent=1,allow_nan=False)+'\n')
            os.replace(tmp,ledger)

    def __enter__(self):
        self.update()
        self.previous=signal.getsignal(signal.SIGALRM)
        def expired(signum,frame):
            raise TimeoutError('E3c reserved elapsed core-second lease expired')
        signal.signal(signal.SIGALRM,expired)
        remaining=self.seconds-(time.perf_counter()-self.started)
        if remaining<=0:
            self.update(finish=True,error='import/startup exceeded lease')
            raise TimeoutError('startup exceeded lease')
        signal.setitimer(signal.ITIMER_REAL,remaining)
        return self

    def __exit__(self,kind,error,tb):
        signal.setitimer(signal.ITIMER_REAL,0.)
        signal.signal(signal.SIGALRM,self.previous)
        self.update(finish=True,error=None if kind is None else repr(error))
        return False
