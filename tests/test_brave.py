import asyncio
import sys
sys.path.insert(0, '.')
from search_engines import Brave


async def test():
    status = "unknown"
    try:
        async with Brave(timeout=15) as engine:
            results = await engine.search("python programming", pages=1)
            count = len(results)
            banned = engine.is_banned
            if banned:
                status = "BANNED"
            elif count > 0:
                status = f"OK ({count} results)"
            else:
                status = "NO RESULTS"
    except Exception as e:
        status = f"ERROR: {type(e).__name__}: {e}"
    print(f"Brave: {status}")


asyncio.run(test())
