"""One campaign ledger: atomic reservations survive crashes and failed runs."""
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path


@contextmanager
def locked(path):
    path=Path(path)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        state=json.loads(path.read_text())
        yield state
        temporary=path.with_suffix('.tmp')
        with temporary.open('w') as out:
            json.dump(state,out,indent=2,allow_nan=False)
            out.flush();os.fsync(out.fileno())
        os.replace(temporary,path)


def valid_resources(resources,limits):
    if set(resources)!=set(limits) or any(type(v) not in (int,float) or not math.isfinite(v)
                                         or v<0 for v in resources.values()):
        raise ValueError('invalid resource accounting')


def reserve(path,run_id,*,campaign_id,protocol_sha256,cap_key,calls,resources,allocation=None):
    return reserve_many(path,run_id,campaign_id=campaign_id,protocol_sha256=protocol_sha256,
                        calls={cap_key:calls},resources=resources,allocation=allocation)


def reserve_many(path,run_id,*,campaign_id,protocol_sha256,calls,resources,allocation=None):
    with locked(path) as ledger:
        if ledger['campaign_id']!=campaign_id or ledger['protocol_sha256']!=protocol_sha256:
            raise ValueError('campaign/protocol ledger mismatch')
        rows=ledger['completed']+ledger['reservations']
        if any(row['id']==run_id for row in rows):
            raise ValueError('run identity already reserved or attempted')
        if not isinstance(calls,dict) or not calls:
            raise ValueError('nonempty stage call reservation required')
        for cap_key,count in calls.items():
            if type(count) is not int or count<1 or cap_key not in ledger['calls_caps']:
                raise ValueError('invalid stage call reservation')
            if count+sum(row.get('calls',{}).get(cap_key,0) for row in rows)>ledger['calls_caps'][cap_key]:
                raise ValueError('cumulative stage call budget exhausted')
        if allocation is not None:
            if (not isinstance(allocation,dict) or set(allocation)!={'id','cap'}
                    or not isinstance(allocation['id'],str) or not allocation['id'].strip()
                    or type(allocation['cap']) is not int or allocation['cap']<=0):
                raise ValueError('invalid allocation reservation')
            allocated=[r for r in rows if r.get('allocation',{}).get('id')==allocation['id']]
            if any(r['allocation']['cap']!=allocation['cap'] for r in allocated):
                raise ValueError('allocation cap cannot change')
            if sum(calls.values())+sum(sum(r['calls'].values()) for r in allocated)>allocation['cap']:
                raise ValueError('cumulative allocation call budget exhausted')
        valid_resources(resources,ledger['limits'])
        for key,limit in ledger['limits'].items():
            if resources[key]+sum(row[key] for row in rows)>limit:
                raise ValueError('cumulative resource budget exhausted: '+key)
        reservation=dict(id=run_id,calls=dict(calls),**resources)
        if allocation is not None:reservation['allocation']=dict(allocation)
        ledger['reservations'].append(reservation)


def settle(path,run_id,*,calls,resources,evidence,status):
    return settle_many(path,run_id,calls=calls,resources=resources,evidence=evidence,status=status)


def settle_many(path,run_id,*,calls,resources,evidence,status):
    with locked(path) as ledger:
        row=next(r for r in ledger['reservations'] if r['id']==run_id)
        if type(calls) is int and len(row['calls'])==1:
            calls={next(iter(row['calls'])):calls}
        valid_resources(resources,ledger['limits'])
        if not isinstance(calls,dict) or set(calls)!=set(row['calls']) or any(
                type(v) is not int or not 0<=v<=row['calls'][k] for k,v in calls.items()):
            raise ValueError('actual calls outside reservation')
        # Preserve measured overrun honestly; later reservations reject exhausted balances.
        overruns={k:resources[k]-row[k] for k in resources if resources[k]>row[k]}
        completed=dict(id=run_id,calls=dict(calls),evidence=evidence,
            status=status,reservation_overruns=overruns,**resources)
        if 'allocation' in row:completed['allocation']=dict(row['allocation'])
        ledger['completed'].append(completed)
        ledger['reservations'].remove(row)
