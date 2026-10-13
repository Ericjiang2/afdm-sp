"""Compare decoder semantics, excluding only measured metadata.seconds."""
import math
from score_development import same


def same_decoder(left,right):
    if left.keys()!=right.keys():return False
    copies=[]
    for value in (left,right):
        item=dict(value)
        if 'metadata' in item:
            metadata=dict(item['metadata'])
            if 'seconds' in metadata:
                seconds=metadata['seconds']
                if not math.isfinite(seconds) or seconds<0:raise ValueError('invalid decoder duration')
                metadata['seconds']='measured duration checked separately'
            item['metadata']=metadata
        copies.append(item)
    return same(*copies)
