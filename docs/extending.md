# Adding a new engine

Drop a new class into `search_engines/engines/`, subclass `SearchEngine`,
override `_selectors`, `_first_page` and `_next_page`, then register it in
`search_engines/engines/__init__.py`'s `search_engines_dict`.

Copy the closest existing engine rather than starting from the base class:

- [`bing.py`](../search_engines/engines/bing.py) — a pure-HTML engine, including
  how to unwrap the redirect links a search engine wraps its results in.
- [`brave.py`](../search_engines/engines/brave.py) — a JSON API. Overrides
  `_filter_results` instead of using CSS selectors.
- [`searchapi.py`](../search_engines/engines/searchapi.py) — a JSON API with an
  API key, several upstreams behind one class, and error reporting.

## Class attributes that cover the common cases

Most of what an engine needs to survive contact with a real site is declarative:

| Attribute | What it does |
|---|---|
| `_http_client_class = CurlHttpClient` | Swaps the transport to curl_cffi with a Chrome TLS fingerprint, for engines that reject plain HTTP/1.1. DuckDuckGo and Yahoo both need this — see [`yahoo.py`](../search_engines/engines/yahoo.py). |
| `_block_markers = ('...',)` | Strings that identify a captcha or block page served with HTTP 200, so the engine sets `is_banned` instead of quietly yielding nothing. |
| `_per_page = 10` | Results per page, where pagination is built by offset rather than by following a "next" link. |

## Overrides worth knowing about

- **`_get_url`** — for engines that wrap result links in their own redirector.
  `bing.py` decodes a base64 payload here; `duckduckgo.py` unwraps a query
  parameter. Do this in `_get_url` and every consumer gets clean URLs for free.
- **`_source`** — the name recorded on each result. Override it when one class
  serves several upstreams: `SearchApi` returns `searchapi:google` rather than
  a bare `searchapi`, so a report says which index a hit came from.
- **`_get_page`** — override to parse a JSON body once per page, or to run a
  consent/session handshake before the real request (see `yahoo.py`).

## What you get without doing anything

Subclassing `SearchEngine` already gives you pagination, result filtering,
deduplication, delays between requests, proxy support, the `is_banned` /
`is_degraded` / `http_status` reporting described in
[engines.md](engines.md#telling-failures-apart), and the ability to take a
`fallback=` engine.

## Testing it

`tests/test_engines_mocked.py` patches `_get_page` (or the transport's `get`,
where the JSON parsing itself is under test) and feeds the parser canned HTML.
No network, so it runs in CI on every supported Python version. Add a payload
constant and one test that asserts real links, titles and text come out.

```bash
pytest tests/ -q               # the hermetic suite
python tests/run_all.py bing   # one engine against the live site
```
