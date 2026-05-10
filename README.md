# 🔎 async-search-scraper

[![Python](https://img.shields.io/badge/python-3.9%E2%80%933.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Async](https://img.shields.io/badge/async-aiohttp%20%2B%20curl__cffi-orange.svg)](https://docs.aiohttp.org/)

> Query a dozen search engines from a **single async Python call** — and get back a unified, deduplicated list of results.

- 🧠 One unified async API over **12 engines** (Bing, Brave, Yahoo, Startpage, AOL, Ask, Tor's Torch, …).
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

That's it — `results.links()` gives you a flat `list[str]` of URLs; `results` itself iterates over `{host, link, title, text}` dicts.

---

## 🧭 Supported engines

| Engine | Status | Notes |
|---|---|---|
| [Bing](https://www.bing.com) | ✅ Working | |
| [Brave](https://search.brave.com) | ✅ Working | Uses the official [Brave Search API](https://api.search.brave.com); set `BRAVE_API_KEY` or pass `api_key=...`. |
| [Yahoo](https://search.yahoo.com) | ✅ Working | Handles the GDPR consent redirect automatically. |
| [Startpage](https://www.startpage.com) | ✅ Working | |
| [AOL](https://search.aol.com) | ✅ Working | |
| [Torch](http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion) | 🧅 Tor only | Requires a running TOR proxy (`socks5://127.0.0.1:9050`). |
| [Ask](https://www.ask.com) | ❌ Deprecated | |
| [Google](https://www.google.com) | ❌ Deprecated | |
| [DuckDuckGo](https://duckduckgo.com) | ❌ Deprecated | |
| [Dogpile](https://www.dogpile.com) | ❌ Deprecated | |
| [Mojeek](https://www.mojeek.com) | ❌ Deprecated | |
| [Qwant](https://www.qwant.com) | ❌ Deprecated | |

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

- **`BRAVE_API_KEY`** — environment variable read by the `Brave` engine when `api_key=` isn't passed explicitly.
- **Proxy** — any URL supported by [`aiohttp_socks`](https://pypi.org/project/aiohttp-socks/): `http://`, `https://`, `socks4://`, `socks5://`. Pass via `Bing(proxy="socks5://127.0.0.1:9050")` or `-proxy` on the CLI.
- **Tunables** — `TIMEOUT`, `USER_AGENT`, default page count, and output directory live in [`search_engines/config.py`](search_engines/config.py).

---

## 🧩 Extending — adding a new engine

Drop a new class into `search_engines/engines/`, subclass `SearchEngine`, override `_selectors`, `_first_page`, `_next_page`, then register it in `search_engines/engines/__init__.py`'s `search_engines_dict`. Mimic [`bing.py`](search_engines/engines/bing.py) for a pure-HTML engine, or [`brave.py`](search_engines/engines/brave.py) / [`ask.py`](search_engines/engines/ask.py) for JSON-driven ones.

---

## 📦 Requirements

Python 3.9–3.13, plus the pinned dependencies in [`requirements.txt`](requirements.txt) (`aiohttp`, `aiohttp_socks`, `beautifulsoup4`, `curl_cffi`, `requests`).

```bash
pip install -r requirements.txt
python setup.py install   # optional, to install the package itself
```

---

## 📄 License

MIT — see [`LICENSE`](LICENSE).

Originally created by [Tasos M. Adamopoulos](https://github.com/tasos-py) — see [Search-Engines-Scraper](https://github.com/tasos-py/Search-Engines-Scraper) for the upstream repo.
