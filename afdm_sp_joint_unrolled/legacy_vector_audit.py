"""Observe raw/decoded bit vectors while replaying an immutable receiver source.

This observer creates new reference evidence; it does not invent missing
historical bit masks. It returns every original function result unchanged.
"""
import argparse
import inspect
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--vectors',type=Path,required=True)
    parser.add_argument('receiver_args',nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.vectors.exists():
        raise FileExistsError(args.vectors)
    sys.path.insert(0,str(args.source))
    import numpy as np
    from afdm_sp_joint_unrolled import budgeted_support_eval as runner
    original_frame, original_builder, original_decoder = runner.make_frame, runner.build_receiver, runner.decode_llr
    context, records = {}, []

    def frame_observer(*a,**kw):
        bound = inspect.signature(original_frame).bind(*a,**kw)
        frame = original_frame(*a,**kw)
        context.update(frame=frame,replicate=bound.arguments['replicate'],frame_index=bound.arguments['index'])
        return frame

    def builder_observer(*a,**kw):
        model = original_builder(*a,**kw)
        original_forward = model.forward

        def forward_observer(*fa,**fkw):
            output = original_forward(*fa,**fkw)
            raw = runner.e1._bits_of_symbol(output['x_soft'].detach().cpu().numpy()/np.sqrt(1-model.cfg.rho),model.cfg.N)
            records.append(dict(replicate=context['replicate'],frame_index=context['frame_index'],
                                raw_bits=raw.astype(int).tolist(),
                                raw_error_mask=(raw!=context['frame']['coded']).astype(int).tolist()))
            return output
        model.forward = forward_observer
        return model

    def decoder_observer(code,llr,*a,**kw):
        decoded,ok = original_decoder(code,llr,*a,**kw)
        records[-1].update(decoded_bits=decoded.astype(int).tolist(),
                           info_error_mask=(runner.extract_info(code,decoded)!=context['frame']['info']).astype(int).tolist())
        return decoded,ok

    runner.make_frame, runner.build_receiver, runner.decode_llr = frame_observer,builder_observer,decoder_observer
    receiver_args = args.receiver_args[1:] if args.receiver_args[:1]==['--'] else args.receiver_args
    sys.argv = ['budgeted_support_eval',*receiver_args]
    runner.main()
    with args.vectors.open('x') as stream:
        json.dump(dict(source=str(args.source),scope='new instrumented replay of frozen source',records=records),stream,allow_nan=False)


if __name__=='__main__':
    main()
