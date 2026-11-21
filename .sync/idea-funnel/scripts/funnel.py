#!/usr/bin/env python3
"""Idea funnel helper (protocol: ../SKILL.md). Cards are the only source of truth; BOARD.md is generated.

  python3 funnel.py init  <funnel dir> --project NAME
  python3 funnel.py new   <funnel dir> --title T --anchor A|B|C|D [--parent ID] [--runner c] [--generator MODEL]   (prints the new card path)
  python3 funnel.py board <funnel dir>                                (validate cards, rewrite BOARD.md; exit 1 on errors)
  python3 funnel.py import <funnel dir> --src <cards dir from elsewhere>   (copy cards, keep local eric: marks)
"""
import argparse, datetime, re, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FIELDS = ('id', 'title', 'layer', 'status', 'anchor_type', 'value', 'next_cost', 'eric', 'updated')
ALLOWED = dict(layer={'L0', 'L1', 'L2', 'L3', 'L4'}, status={'active', 'killed', 'parked', 'promoted'},
               anchor_type={'A', 'B', 'C', 'D'}, value={'0', '1', '2', '3'})
SECTIONS = ('## 问题（一句话）', '## 白话与类比', '## 锚点（出处）', '## 去壳三句', '## 最接近的已有工作',
            '## 价值与代价', '## 筛选记录')


def today():
    return datetime.date.today().isoformat()


def parse(path):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not m:
        return None, text, ['no frontmatter']
    meta = {}
    for line in m.group(1).splitlines():
        key, _, val = line.partition(':')
        meta[key.strip()] = val.strip()
    errors = [f'missing field {f}' for f in FIELDS if f not in meta]
    errors += [f'{k}={meta[k]!r} not in {sorted(v)}' for k, v in ALLOWED.items() if k in meta and meta[k] not in v]
    errors += [f'missing section {s}' for s in SECTIONS if s not in text]
    if meta.get('parent') and not (path.parent / f"{meta['parent']}.md").exists():
        errors.append(f'parent {meta["parent"]} not found')
    if meta.get('id') and meta['id'] != path.stem:
        errors.append(f'id {meta["id"]} does not match file name')
    return meta, text, errors


def last_log(text):
    lines = [l for l in text.split('## 筛选记录', 1)[-1].splitlines() if l.startswith('- ')]
    return lines[-1][2:] if lines else ''


def init(d, project):
    (d / 'cards').mkdir(parents=True, exist_ok=True)
    if not (d / 'FUNNEL.md').exists():
        (d / 'FUNNEL.md').write_text((SKILL / 'templates/FUNNEL.md').read_text(encoding='utf-8').replace('{project}', project),
                                     encoding='utf-8')
    if not (d / 'runs.md').exists():
        (d / 'runs.md').write_text('# Runs（每次运行一行：日期、工具/模型、各层数量、淘汰数、丢弃的草稿）\n', encoding='utf-8')
    board(d)


def new(d, title, anchor, parent='', runner='', generator=''):
    stamp = datetime.date.today().strftime('%Y%m%d')
    tpl = (SKILL / 'templates/card.md').read_text(encoding='utf-8')
    for n in range(1, 1000):
        path = d / 'cards' / f'I-{stamp}-{runner}{n:02d}.md'   # runner letter keeps parallel runs from colliding
        try:
            with open(path, 'x', encoding='utf-8') as fh:    # exclusive create: parallel agents never share an id
                fh.write(tpl.format(id=path.stem, title=title, anchor_type=anchor, parent=parent, generator=generator, date=today()))
            print(path)
            return
        except FileExistsError:
            continue
    sys.exit('no free id today')


def import_cards(d, src):
    """Take cards from src (a cloud run); a local non-empty eric: mark always wins over the incoming one."""
    added = updated = 0
    for p in sorted(Path(src).glob('*.md')):
        text = p.read_text(encoding='utf-8'); dest = d / 'cards' / p.name
        if dest.exists():
            mark = re.search(r'^eric:(.*)$', dest.read_text(encoding='utf-8'), re.M)
            if mark and mark.group(1).strip():
                text = re.sub(r'^eric:.*$', f'eric:{mark.group(1)}', text, count=1, flags=re.M)
            updated += dest.read_text(encoding='utf-8') != text
        else:
            added += 1
        dest.write_text(text, encoding='utf-8')
    print(f'import: {added} new, {updated} updated')
    board(d)


def board(d):
    cards, bad = [], []
    for p in sorted((d / 'cards').glob('*.md')):
        meta, text, errors = parse(p)
        if errors:
            bad.append(f'{p.name}: ' + '; '.join(errors))
        else:
            cards.append(dict(meta, log=last_log(text), file=f'cards/{p.name}'))
    if bad:
        print('\n'.join(bad), file=sys.stderr)
        sys.exit(1)

    def row(c):
        mark = f' · Eric：{c["eric"]}' if c['eric'] else ''
        mark += f' · 来自 {c["parent"]}' if c.get('parent') else ''
        mark += f' · 出题 {c["generator"]}' if c.get('generator') else ''
        return f'- [{c["id"]}]({c["file"]}) {c["title"]} — {c["layer"]}，价值 {c["value"]}{mark}\n  - {c["log"]}'

    groups = [('等你看（L3）', lambda c: c['status'] == 'active' and c['layer'] == 'L3'),
              ('筛选中（L0–L2）', lambda c: c['status'] == 'active' and c['layer'] in ('L0', 'L1', 'L2')),
              ('停放（下一步检验超出预算）', lambda c: c['status'] == 'parked'),
              ('已晋级（转 Trellis 任务）', lambda c: c['status'] == 'promoted'),
              ('已淘汰', lambda c: c['status'] == 'killed')]
    counts = {s: sum(c['status'] == s for c in cards) for s in ('active', 'parked', 'promoted', 'killed')}
    out = [f'# 看板（自动生成，{today()}；不要手改，改卡片后运行 funnel.py board）', '',
           f'共 {len(cards)} 张：进行中 {counts["active"]}，停放 {counts["parked"]}，晋级 {counts["promoted"]}，淘汰 {counts["killed"]}。',
           '在卡片的 `eric:` 一栏写 `继续` / `停` / `改：…`，下次运行时生效。']
    for name, keep in groups:
        rows = [row(c) for c in cards if keep(c)]
        out += ['', f'## {name}（{len(rows)}）', *(rows or ['- 无'])]
    (d / 'BOARD.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'BOARD.md: {len(cards)} cards')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('init', 'new', 'board', 'import'))
    ap.add_argument('dir', type=Path)
    ap.add_argument('--project', default='')
    ap.add_argument('--title', default='')
    ap.add_argument('--anchor', choices=sorted(ALLOWED['anchor_type']))
    ap.add_argument('--parent', default='')
    ap.add_argument('--generator', default='', help='model that generated the idea, e.g. claude-opus-5-5, gpt-6.2-sol')
    ap.add_argument('--runner', default='', help='one lowercase letter per parallel runner, e.g. l (local) or c (cloud)')
    ap.add_argument('--src', type=Path)
    a = ap.parse_args()
    if a.cmd == 'init':
        init(a.dir, a.project or a.dir.resolve().parent.name)
    elif a.cmd == 'new':
        if not a.title or not a.anchor:
            sys.exit('new needs --title and --anchor')
        new(a.dir, a.title, a.anchor, a.parent, a.runner, a.generator)
    elif a.cmd == 'import':
        if not a.src:
            sys.exit('import needs --src')
        import_cards(a.dir, a.src)
    else:
        board(a.dir)
