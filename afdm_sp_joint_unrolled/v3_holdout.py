"""Namespaced diagnostic holdout, reusing the actual coded frame generator."""
import numpy as np
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.v3_protocol import seed_words


def holdout_rng(replicate,index,component,*,split=2):
    if replicate not in (0,1,2) or not 0<=index<128 or component not in (1,2,3):
        raise ValueError('unregistered holdout identity')
    return np.random.default_rng(seed_words('holdout',replicate,index,('channel','message','noise')[component-1]))


def make_holdout_frame(system,code,replicate,index):
    frame=make_frame(system,code,replicate,index,8.,split=2,rng_factory=holdout_rng)
    frame['dataset']='D_v3_hold'
    frame['order_seed_words']=seed_words('holdout',replicate,index,'order')
    return frame
