"""One-shot patcher: add --classical-ranker + --action-audit flags to paired_learned_eval.py.

Both are monkey-patch-style flags that do NOT modify trained-module code;
they only re-wire behaviour at eval time.
"""
import pathlib
import re
import textwrap


def main():
    p = pathlib.Path('afdm_sp_joint_unrolled/paired_learned_eval.py')
    src = p.read_text()

    # --- 1. Add CLI flags right before --refine-rounds ---
    flag_needle_re = re.compile(r"(    ap\.add_argument\('--refine-rounds',)")
    if '--classical-ranker' not in src:
        flag_insert = textwrap.dedent('''\
            ap.add_argument('--classical-ranker', action='store_true',
                            help='Loop-12 Oracle-R1 attribution ablation: replace the learned C2-rel '
                                 'scorer with classical residual-correlation ordering. cand_cols is '
                                 'already sorted by pilot-MF residual magnitude in build_features; '
                                 'this flag monkey-patches module.cand_active_rel.score to return '
                                 'pool-order-descending logits so select_additions picks the classical '
                                 'top-K. Keeps F2-P mechanics intact. Use with --tau-lookup <small> to '
                                 'actually add top-K.')
            ap.add_argument('--action-audit', action='store_true',
                            help='Loop-12 Oracle-R1 per-frame action audit: log additions/frame, '
                                 'harmful-add rate (relative to pilot-LS |gain| of OMP picks), logit '
                                 'histogram for added atoms. Results land in results.json under '
                                 '"action_audit" per SNR.')
        ''')
        flag_insert = textwrap.indent(flag_insert, '    ').replace('    ap.add_argument', 'ap.add_argument')
        flag_insert = '    ' + flag_insert.lstrip()  # keep 4-space indent
        src = flag_needle_re.sub(flag_insert + r"\1", src, count=1)
        print('added CLI flags')

    # --- 2. Monkey-patch score() before --refine-rounds block ---
    hook_patch = textwrap.dedent('''\
        if args.classical_ranker:
            if getattr(module, "cand_active_rel", None) is None:
                raise RuntimeError("--classical-ranker requires a C2-rel head")
            import torch as _t_classrank
            def _classical_rank_score(u, v, *_args, **_kwargs):
                n = u.shape[0]
                if n == 0:
                    return _t_classrank.zeros(0, device=u.device, dtype=u.dtype)
                return 10.0 - _t_classrank.arange(
                    n, device=u.device, dtype=u.dtype
                ) * (10.0 / float(max(n, 1)))
            module.cand_active_rel.score = _classical_rank_score
            print("[classical-ranker] score() -> pool-order descending logit (F2-P mechanics intact)")
    ''')
    # Indent once to match function body
    hook_patch = textwrap.indent(hook_patch, '    ')
    hook_needle = '    if args.refine_rounds > 0:'
    if hook_needle in src and '[classical-ranker] score() -> pool-order' not in src:
        src = src.replace(hook_needle, hook_patch + hook_needle, 1)
        print('added monkey-patch')

    p.write_text(src)
    print('ok')


if __name__ == '__main__':
    main()
