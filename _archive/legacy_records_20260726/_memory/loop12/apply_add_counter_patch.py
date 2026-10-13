"""Add a CLI flag --count-adds to paired_learned_eval.py that monkey-patches
select_additions to record per-frame (n_adds, logit_mean_of_adds).
Exports as `add_stats` in each SNR block of results.json.
"""
import pathlib
import re
import textwrap


def main():
    p = pathlib.Path('afdm_sp_joint_unrolled/paired_learned_eval.py')
    src = p.read_text()

    if '--count-adds' not in src:
        # Add CLI flag after --classical-ranker
        anchor = "    ap.add_argument('--classical-ranker', action='store_true',"
        insert = textwrap.dedent('''\
            ap.add_argument('--count-adds', action='store_true',
                            help='Loop-12 action-counter: monkey-patch select_additions to log '
                                 'per-frame n_adds and logit_mean_of_adds, dumped into per-SNR '
                                 'results.json under "add_stats".')
        ''')
        insert = '    ' + insert.lstrip()
        src = src.replace(anchor, insert + anchor, 1)
        print('added --count-adds CLI flag')

    if '# [count-adds] monkey' not in src:
        # Hook: after classical-ranker block, monkey-patch select_additions.
        # A module-level list _LOOP12_ADD_STATS accumulates records.
        anchor = '    if args.refine_rounds > 0:'
        hook = textwrap.dedent('''\
            # [count-adds] monkey-patch select_additions to record per-call stats.
            _LOOP12_ADD_STATS = []
            if args.count_adds:
                if getattr(module, "cand_active_rel", None) is None:
                    raise RuntimeError("--count-adds requires a C2-rel head")
                _orig_select_adds = module.cand_active_rel.select_additions
                def _tracked_select(logits, cand_cols, tau=0.0):
                    picks = _orig_select_adds(logits, cand_cols, tau=tau)
                    if picks.numel() > 0:
                        mask = logits > float(tau)
                        pos_logits = logits[mask]
                        _, topi = pos_logits.topk(
                            k=min(module.cand_active_rel.k_add_max, pos_logits.numel()),
                            sorted=True)
                        picked_logits = pos_logits[topi]
                        _LOOP12_ADD_STATS.append(dict(
                            n_adds=int(picks.numel()),
                            logit_mean=float(picked_logits.mean().item()),
                            logit_min=float(picked_logits.min().item()),
                            logit_max=float(picked_logits.max().item()),
                        ))
                    else:
                        _LOOP12_ADD_STATS.append(dict(
                            n_adds=0, logit_mean=float("nan"),
                            logit_min=float("nan"), logit_max=float("nan")))
                    return picks
                module.cand_active_rel.select_additions = _tracked_select
                print("[count-adds] monkey-patched select_additions -> _LOOP12_ADD_STATS")
        ''')
        hook = textwrap.indent(hook, '    ')
        src = src.replace(anchor, hook + anchor, 1)
        print('added monkey-patch')

    # Also: drop _LOOP12_ADD_STATS into per-SNR results block, then clear.
    if 'add_stats=list(_LOOP12_ADD_STATS)' not in src:
        # Find the per-SNR results assembly where we do:
        #     results[str(snr)] = dict(
        # We patch by replacing the closing `)` and adding add_stats key
        anchor = '            paired_diff_per_frame=[int(x) for x in paired_diff_per_frame],'
        hook = anchor + '\n            add_stats=list(_LOOP12_ADD_STATS),'
        src = src.replace(anchor, hook, 1)
        # And clear after each SNR iter
        # Insert `_LOOP12_ADD_STATS.clear()` after the results[str(snr)] = dict(...) block
        # Easiest: clear at start of each frame loop (fi=0). Find `for fi in range(args.frames_per_snr):`
        inner_anchor = '        for fi in range(args.frames_per_snr):'
        inner_hook = '        _LOOP12_ADD_STATS.clear()\n' + inner_anchor
        src = src.replace(inner_anchor, inner_hook, 1)
        print('wired add_stats into results + per-SNR clear')

    p.write_text(src)
    print('ok')


if __name__ == '__main__':
    main()
