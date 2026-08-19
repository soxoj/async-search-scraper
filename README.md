# 🔎 async-search-scraper

[![Python](https://img.shields.io/badge/python-3.9%E2%80%933.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Async](https://img.shields.io/badge/async-aiohttp%20%2B%20curl__cffi-orange.svg)](https://docs.aiohttp.org/)

> Query a dozen search engines from a **single async Python call** — and get back a unified, deduplicated list of results.

- 🧠 One unified async API over a dozen engines — **Brave, Yahoo, DuckDuckGo and Bing** are the ones that reliably return results today.
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
| [Yahoo](https://search.yahoo.com) | ✅ Working | The most reliable of the HTML engines. Clears the GDPR consent redirect for you. |
| [AOL](https://search.aol.com) | ✅ Working | AOL retired its own search and now runs on Yahoo's syndicated index, so expect Yahoo's results. |
| [Brave](https://search.brave.com) | ✅ Working | Official [Brave Search API](https://api.search.brave.com) — the only engine here with no scraping involved. Needs `BRAVE_API_KEY`. |
| [DuckDuckGo](https://duckduckgo.com) | ✅ Working | Occasionally answers with a challenge instead of results; retry or check `is_banned`. |
| [Bing](https://www.bing.com) | ⚠️ Rate-sensitive | Fine for occasional queries, but starts demanding a captcha if you hammer it. Slow the pace down (`min_delay`/`max_delay`) and watch `is_banned`. |
| [Startpage](https://www.startpage.com) | ⚠️ Often blocked | Serves a captcha to most non-browser traffic, including via proxies. Usable if you happen to have a clean address, otherwise prefer Yahoo or Brave. |
| [Mojeek](https://www.mojeek.com) | ⚠️ Often blocked | Same story as Startpage — expect a captcha more often than results. |
| [Torch](http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion) | 🧅 Tor only | Requires a running TOR proxy (`socks5://127.0.0.1:9050`). |
| [SearchApi](https://www.searchapi.io) | 🔑 API key | A paid SERP backend covering Google, Bing, DuckDuckGo, Yahoo, Yandex, Naver and Baidu. Use it to reach engines that block you — Google especially. Needs `SEARCHAPI_KEY`. |
| [Google](https://www.google.com) | ❌ Deprecated | Renders results with JavaScript — the HTML it serves contains none, so there is nothing to scrape. Reachable via `SearchApi(engine="google")`. |
| [Ask](https://www.ask.com) | ❌ Deprecated | IAC shut the search business down; the site is a farewell page. Not coming back. |
| [Dogpile](https://www.dogpile.com) | ❌ Deprecated | Behind a JavaScript bot challenge that needs a real browser to solve. |
| [Qwant](https://www.qwant.com) | ❌ Deprecated | Its API now requires an auth token that is not publicly available. |

Deprecated engines are kept importable and registered — the code still parses their
markup, so if an endpoint comes back, only the transport needs revisiting.

> [!NOTE]
> Empty results are never silent. `is_banned` is set when an engine answers with a
> captcha or block page, including the ones served with HTTP 200, and `http_status`
> holds the last response code — `0` means the request never landed. So a transport
> failure, a ban, and a genuinely empty result set stay distinguishable:
>
> ```python
> if engine.http_status == 0: ...   # proxy/network never got there
> elif engine.is_banned: ...        # the engine blocked us
> elif not len(results): ...        # the query really has no hits
> ```

> [!TIP]
> Blocking depends on where you run from — a cloud server gets challenged far sooner
> than a home connection. If an engine reports `is_banned`, a proxy is worth a try:
> `Bing(proxy="http://user:pass@host:port")` takes any `aiohttp_socks` URL, and both
> `socks5://` and `socks5h://` work. It is not a guaranteed fix — Startpage and Mojeek
> turn away proxy addresses too — so treat engine choice, not proxies, as the main
> lever: Brave (API) and Yahoo are the ones that hold up under volume.

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

- **`BRAVE_API_KEY`** / **`SEARCHAPI_KEY`** — environment variables read by the `Brave` and `SearchApi` engines when `api_key=` isn't passed explicitly. A local `.env` is convenient but git-ignored; the engines read the environment, not the file.
- **Proxy** — any URL supported by [`aiohttp_socks`](https://pypi.org/project/aiohttp-socks/): `http://`, `https://`, `socks4://`, `socks5://`. Pass via `Bing(proxy="socks5://127.0.0.1:9050")` or `-proxy` on the CLI.
- **Tunables** — `TIMEOUT`, `USER_AGENT`, default page count, and output directory live in [`search_engines/config.py`](search_engines/config.py).

---

## 🧩 Extending — adding a new engine

Drop a new class into `search_engines/engines/`, subclass `SearchEngine`, override `_selectors`, `_first_page`, `_next_page`, then register it in `search_engines/engines/__init__.py`'s `search_engines_dict`. Mimic [`bing.py`](search_engines/engines/bing.py) for a pure-HTML engine, or [`brave.py`](search_engines/engines/brave.py) / [`ask.py`](search_engines/engines/ask.py) for JSON-driven ones.

Two class attributes cover the common defences:

- `_http_client_class = CurlHttpClient` — swaps the transport to curl_cffi with a Chrome TLS fingerprint, for engines that reject plain HTTP/1.1 (see [`yahoo.py`](search_engines/engines/yahoo.py)).
- `_block_markers = ('...',)` — strings that identify a captcha/block page served with HTTP 200, so it sets `is_banned` instead of quietly yielding nothing.

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
