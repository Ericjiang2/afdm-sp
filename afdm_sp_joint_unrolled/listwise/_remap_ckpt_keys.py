"""One-off: remap 5-seed listwise ckpts to add cand_active_rel. prefix in-place.

Used to make pre-fix-commit ckpts compatible with paired_learned_eval.
After this runs once, future train_listwise.py runs save with the prefix
already (see commit fixing the prefix).
"""
import argparse
import pathlib
import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True,
                    help='dir containing seed_<N>/ckpt_listwise.pt subdirs')
    ap.add_argument('--prefix', default='cand_active_rel.')
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    for ckpt_path in sorted(root.glob('seed_*/ckpt_listwise.pt')):
        ckpt = torch.load(ckpt_path, weights_only=False)
        sd = ckpt['state_dict']
        if any(k.startswith(args.prefix) for k in sd):
            print(f'[skip] {ckpt_path}  already has prefix')
            continue
        sd_new = {f'{args.prefix}{k}': v for k, v in sd.items()}
        ckpt['state_dict'] = sd_new
        torch.save(ckpt, ckpt_path)
        print(f'[remap] {ckpt_path}  added prefix to {len(sd_new)} keys')


if __name__ == '__main__':
    main()
