"""Run a single query across every working engine, merge by URL, and emit:
1) results_soxoj_account.csv  — merged table with per-engine presence columns
2) stats printed to stdout.

Usage:
    BRAVE_API_KEY=... python tests/cross_engine_search.py
"""
import asyncio
import csv
import os
import sys
from collections import OrderedDict
from itertools import combinations
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, '.')

from search_engines import Bing, Brave, Yahoo, Startpage, Aol

QUERY = 'soxoj account'
PAGES = 2
ENGINES = [
    ('Bing', Bing, {}),
    ('Brave', Brave, {}),
    ('Yahoo', Yahoo, {}),
    ('Startpage', Startpage, {}),
    ('AOL', Aol, {}),
]


def normalize_url(url: str) -> str:
    """Lowercase host, strip trailing slash, drop fragment."""
    if not url:
        return url
    try:
        p = urlparse(url)
    except Exception:
        return url
    netloc = p.netloc.lower()
    path = p.path.rstrip('/') or '/'
    return urlunparse((p.scheme.lower(), netloc, path, p.params, p.query, ''))


async def search_one(name, cls, kwargs):
    print(f'  → {name}...', flush=True)
    try:
        async with cls(timeout=20, **kwargs) as engine:
            engine.print_func = lambda *a, **k: None
            results = await engine.search(QUERY, pages=PAGES)
            items = []
            for r in results:
                real = r['link']
                norm = normalize_url(real)
                items.append({
                    'url': norm,
                    'original_url': real,
                    'title': (r.get('title') or '').strip(),
                    'text': (r.get('text') or '').strip(),
                })
            print(f'    {name}: {len(items)} results', flush=True)
            return items
    except Exception as e:
        print(f'    {name}: ERROR {type(e).__name__}: {e}', flush=True)
        return []


async def main():
    print(f'Query: "{QUERY}"  (pages={PAGES})')
    print('Engines:', ', '.join(name for name, _, _ in ENGINES))
    print()

    per_engine = {}
    for name, cls, kwargs in ENGINES:
        per_engine[name] = await search_one(name, cls, kwargs)

    # ---- merge ----
    merged = OrderedDict()  # normalized url -> row
    for name, items in per_engine.items():
        for it in items:
            row = merged.setdefault(it['url'], {
                'url': it['original_url'],
                'title': '',
                'text': '',
                **{n: '' for n, _, _ in ENGINES},
            })
            if not row['title'] and it['title']:
                row['title'] = it['title']
            if not row['text'] and it['text']:
                row['text'] = it['text']
            row[name] = 'X'

    # ---- write CSV ----
    out_path = 'results_soxoj_account.csv'
    fields = ['url', 'title', 'text'] + [n for n, _, _ in ENGINES]
    header_map = {'url': 'URL', 'title': 'Title', 'text': 'Preview text'}
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([header_map.get(h, h) for h in fields])
        for row in merged.values():
            w.writerow([row[h] for h in fields])
    print(f'\nWrote {out_path} — {len(merged)} unique URLs')

    # ---- stats ----
    sets = {n: {it['url'] for it in items} for n, items in per_engine.items()}

    print('\nPer-engine counts (raw / unique-after-norm):')
    for n, items in per_engine.items():
        print(f'  {n:<10} {len(items):>3} raw   {len(sets[n]):>3} unique')

    if sets:
        leader = max(sets.items(), key=lambda kv: len(kv[1]))
        print(f'\nLeader: {leader[0]} ({len(leader[1])} unique URLs)')

    # appears-in-N-engines histogram
    appearance = {}
    for url in merged:
        n_engines = sum(1 for n in sets if url in sets[n])
        appearance[n_engines] = appearance.get(n_engines, 0) + 1
    print('\nDistribution — URLs found by N engines:')
    for n in sorted(appearance):
        bar = '#' * appearance[n]
        print(f'  {n} engine(s): {appearance[n]:>3}  {bar}')

    # pairwise Jaccard
    print('\nPairwise overlap (Jaccard = |A∩B| / |A∪B|):')
    print(f'  {"pair":<22} {"∩":>3} {"∪":>3} {"jaccard":>8}')
    for (a, sa), (b, sb) in combinations(sets.items(), 2):
        if not (sa or sb):
            continue
        inter = len(sa & sb)
        union = len(sa | sb)
        j = (inter / union * 100) if union else 0
        print(f'  {a + " ∩ " + b:<22} {inter:>3} {union:>3} {j:>7.1f}%')

    total_unique = len(merged)
    in_any = sum(1 for url in merged if any(url in sets[n] for n in sets))
    in_all = sum(1 for url in merged if all(url in sets[n] for n in sets))
    in_2plus = sum(1 for url in merged if sum(url in sets[n] for n in sets) >= 2)
    print(f'\nTotals: {total_unique} unique URLs across all engines')
    print(f'  found by ≥1 engine: {in_any}  (= total)')
    print(f'  found by ≥2 engines: {in_2plus}  ({in_2plus/total_unique*100:.1f}%)')
    print(f'  found by all {len(sets)} engines: {in_all}  ({in_all/total_unique*100:.1f}%)')


if __name__ == '__main__':
    asyncio.run(main())
