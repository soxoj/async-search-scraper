# 🔎 async-search-scraper

[![Python](https://img.shields.io/badge/python-3.9%E2%80%933.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Async](https://img.shields.io/badge/async-aiohttp%20%2B%20curl__cffi-orange.svg)](https://docs.aiohttp.org/)

> Query a dozen search engines from a **single async Python call** — and get back a unified, deduplicated list of results.

- 🧠 One unified async API over a dozen engines — **Brave, Yahoo and DuckDuckGo** are the ones that reliably return results today.
- ⚡ Drop-in **CLI** for one-shot searches with `print` / `html` / `csv` / `json` output.
- 🧰 Built-in **pagination, deduplication, result filtering**, and HTTP/SOCKS proxy support.

---

## 🚀 Quick start

```bash
pip install -r requirements.txt
```

```python
import asyncio
from search_engines import Bing

async def main():
    async with Bing() as engine:
        results = await engine.search("my query")
        print(results.links())

asyncio.run(main())
```

That's it — `results.links()` gives you a flat `list[str]` of URLs; `results` itself iterates over `{host, link, title, text, source}` dicts.

---

## 🧭 Supported engines

| | Engines |
|---|---|
| ✅ **Reliable** | Yahoo, AOL, Brave (API key), DuckDuckGo |
| ⚠️ **Fights back** | Bing, Startpage, Mojeek |
| 🔑 **Paid** | SearchApi — Google, Bing, DuckDuckGo, Yahoo, Yandex, Naver, Baidu |
| ❌ **Deprecated** | Google, Ask, Dogpile, Qwant — still importable, see the reasons |
| 🧅 **Tor** | Torch |

**→ [docs/engines.md](docs/engines.md)** for what each one does, why the deprecated
ones are dead, and how to tell a block from an empty result set.

> [!NOTE]
> Failures are never silent, and never dressed up as results. `is_banned` covers
> captcha and block pages, including the ones served with HTTP 200; `http_status`
> holds the last response code, where `0` means the request never landed; and
> `is_degraded` covers an engine that answered normally but returned a full page
> matching your query nowhere — those results are dropped rather than reported.

---

## 📚 Usage as a library

### Single engine

```python
import asyncio
from search_engines import Bing

async def main():
    async with Bing() as engine:
        results = await engine.search("my query", pages=2)
        for item in results:
            print(item["title"], "→", item["link"])

asyncio.run(main())
```

### Multiple engines, deduplicated

```python
import asyncio
from search_engines import Bing, Yahoo, Startpage

async def main():
    all_links = set()
    for cls in (Bing, Yahoo, Startpage):
        async with cls() as engine:
            engine.ignore_duplicate_urls = True
            results = await engine.search("python programming", pages=1)
            all_links.update(results.links())
    print(f"{len(all_links)} unique URLs")

asyncio.run(main())
```

### SearchApi (API key)

Reaches the engines that block scrapers — Google above all. One class, pick the
upstream with `engine=`: `google`, `bing`, `duckduckgo`, `yahoo`, `yandex`,
`naver`, `baidu`.

```python
import asyncio
from search_engines import SearchApi

async def main():
    async with SearchApi(engine="google") as engine:   # reads SEARCHAPI_KEY
        results = await engine.search("my query", pages=2)
        print(results.links())

asyncio.run(main())
```

Calls are metered, so an exhausted balance is reported rather than swallowed:
the reason comes back on `print_func` and `http_status` holds the code.

### Falling back to the paid API when an engine fails

Any engine accepts a `fallback=`. It runs only when the primary engine gave you
nothing usable — blocked, unreachable, or answering with results unrelated to
your query — and never when the primary already returned something.

```python
import asyncio
from search_engines import Bing, SearchApi

async def main():
    async with Bing(fallback=SearchApi(engine="bing")) as engine:
        results = await engine.search("my query")
        print(engine.fell_back)                 # True if the fallback answered
        for r in results:
            print(r["source"], r["link"])       # 'bing' or 'searchapi:bing'

asyncio.run(main())
```

Every result carries `source`, with or without a fallback, so a report always
records which engine actually found each hit — and the CSV `engine` column
follows it rather than the engine you asked for.

On the CLI it is a flag, never automatic:

```bash
python search_engines_cli.py -e bing,duckduckgo -q "my query" --fallback searchapi
```

> [!IMPORTANT]
> Having `SEARCHAPI_KEY` set does **not** enable the fallback. Spending credits
> is always something you asked for explicitly.

### Brave (API key)

> [!NOTE]
> Brave uses the official Search API. Get a free key at [api.search.brave.com](https://api.search.brave.com) and either export `BRAVE_API_KEY` or pass `api_key=...` to the constructor.

```python
import asyncio, os
from search_engines import Brave

async def main():
    async with Brave(api_key=os.environ["BRAVE_API_KEY"]) as engine:
        results = await engine.search("my query")
        print(results.links())

asyncio.run(main())
```

---

## 🖥️ Usage as a CLI

```bash
python search_engines_cli.py -e bing,yahoo -q "my query" -o json,print
```

| Flag | Purpose | Default |
|---|---|---|
| `-q` | Search query (**required**) | — |
| `-e` | Engine(s), comma-separated, or `all` | `google` |
| `-p` | Number of pages to fetch | `20` |
| `-o` | Output: any combination of `print`, `html`, `csv`, `json` | `print` |
| `-n` | Output filename (without extension) | `search_results/output` |
| `-f` | Filter results by `url` / `title` / `text` / `host` | none |
| `-i` | Drop duplicate URLs across engines | off |
| `-proxy` | HTTP/SOCKS proxy URL (`protocol://ip:port`) | none |
| `--fallback` | Retry blocked engines through a paid API (`searchapi`) | off |

Typical output:

```
Searching Bing
page: 1        links: 10
page: 2        links: 20
1  https://www.python.org/                          Welcome to Python.org
2  https://en.wikipedia.org/wiki/Python_(...)       Python (programming language) - Wikipedia
...
```

---

## ⚙️ Configuration

- **`BRAVE_API_KEY`** / **`SEARCHAPI_KEY`** — environment variables read by the `Brave` and `SearchApi` engines when `api_key=` isn't passed explicitly. A local `.env` is convenient but git-ignored; the engines read the environment, not the file.
- **Proxy** — any URL supported by [`aiohttp_socks`](https://pypi.org/project/aiohttp-socks/): `http://`, `https://`, `socks4://`, `socks5://`. Pass via `Bing(proxy="socks5://127.0.0.1:9050")` or `-proxy` on the CLI.
- **Tunables** — `TIMEOUT`, `USER_AGENT`, default page count, and output directory live in [`search_engines/config.py`](search_engines/config.py).

---

## 🧩 Extending

New engines are a subclass plus a line in a registry, and the base class already
covers pagination, filtering, dedup, proxies and block detection.

**→ [docs/extending.md](docs/extending.md)**

---

## 📦 Requirements

Python 3.9–3.13, plus the pinned dependencies in [`requirements.txt`](requirements.txt) (`aiohttp`, `aiohttp_socks`, `beautifulsoup4`, `curl_cffi`).

```bash
pip install -r requirements.txt
python setup.py install   # optional, to install the package itself
```

---

## 📄 License

MIT — see [`LICENSE`](LICENSE).

Originally created by [Tasos M. Adamopoulos](https://github.com/tasos-py) — see [Search-Engines-Scraper](https://github.com/tasos-py/Search-Engines-Scraper) for the upstream repo.
