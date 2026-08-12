"""Live check against the real search engines. Not part of the pytest suite:
it needs network, and the engines' answers depend on the address you run from.

    python tests/run_all.py            # every engine, summary table
    python tests/run_all.py bing       # just one
    python tests/run_all.py bing yahoo # or a few

Exits non-zero if any requested engine failed to return results, so it is
usable as a smoke check.
"""
import asyncio
import sys

sys.path.insert(0, '.')

from search_engines import Google, Bing, Brave, Yahoo, Duckduckgo, Startpage, Aol, Dogpile, Ask, Mojeek, Qwant, Torch


ENGINES = [
    ("Google", Google),
    ("Bing", Bing),
    ("Brave", Brave),
    ("Yahoo", Yahoo),
    ("DuckDuckGo", Duckduckgo),
    ("Startpage", Startpage),
    ("AOL", Aol),
    ("Dogpile", Dogpile),
    ("Ask", Ask),
    ("Mojeek", Mojeek),
    ("Qwant", Qwant),
    ("Torch", Torch),
]

QUERY = "python programming"
PAGES = 1
TIMEOUT = 15


async def test_engine(name, engine_class):
    """Test a single engine and return (name, status, detail)."""
    try:
        kwargs = {"timeout": TIMEOUT}
        # Torch needs TOR proxy — use default from config
        async with engine_class(**kwargs) as engine:
            results = await engine.search(QUERY, pages=PAGES)
            count = len(results)
            banned = engine.is_banned

            if banned:
                return (name, "BROKEN", "Banned by the search engine")
            elif count > 0:
                return (name, "OK", f"{count} results")
            else:
                return (name, "NO RESULTS", "Search returned 0 results")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        # Detect TOR/proxy issues for Torch
        if any(kw in error_msg.lower() for kw in ("proxy", "socks", "connect", "refused")):
            return (name, "REQUIRES PROXY", f"{error_type}: {error_msg}")
        return (name, "ERROR", f"{error_type}: {error_msg}")


def select(names):
    """Picks the requested engines, case-insensitively."""
    if not names:
        return ENGINES
    wanted = [n.lower() for n in names]
    chosen = [(name, cls) for name, cls in ENGINES if name.lower() in wanted]
    unknown = set(wanted) - {name.lower() for name, _ in ENGINES}
    if unknown:
        known = ', '.join(name.lower() for name, _ in ENGINES)
        sys.exit(f"Unknown engine(s): {', '.join(sorted(unknown))}\nAvailable: {known}")
    return chosen


async def main(names):
    engines = select(names)
    results = []
    for name, engine_class in engines:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        name, status, detail = await test_engine(name, engine_class)
        results.append((name, status, detail))
        print(f"  => {status}: {detail}")

    if len(results) > 1:
        print(f"\n\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"{'Engine':<15} {'Status':<18} {'Detail'}")
        print(f"{'-'*15} {'-'*18} {'-'*35}")
        for name, status, detail in results:
            print(f"{name:<15} {status:<18} {detail}")
        print(f"{'='*70}")

    return 0 if all(status == "OK" for _, status, _ in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
