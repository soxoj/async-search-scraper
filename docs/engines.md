# Engines

Which engine to reach for, what each one does when it does not want to answer,
and how to tell those cases apart in code.

Short version: **Brave** and **Yahoo** are the ones that hold up under volume,
**DuckDuckGo** is close behind, and **SearchApi** buys you the rest — Google
included — for money.

## The list

| Engine | Status | Notes |
|---|---|---|
| [Yahoo](https://search.yahoo.com) | ✅ Working | The most reliable of the HTML engines. Clears the GDPR consent redirect for you. |
| [AOL](https://search.aol.com) | ✅ Working | AOL retired its own search and now runs on Yahoo's syndicated index, so expect Yahoo's results. |
| [Brave](https://search.brave.com) | ✅ Working | Official [Brave Search API](https://api.search.brave.com) — the only engine here with no scraping involved. Needs `BRAVE_API_KEY`. |
| [DuckDuckGo](https://duckduckgo.com) | ✅ Working | Occasionally answers with a challenge instead of results; retry or check `is_banned`. |
| [Bing](https://www.bing.com) | ⚠️ Answers with junk | Sometimes returns `200 OK` and ten real-looking links that have nothing to do with your query — no captcha, no error code. The library catches that and reports `is_degraded` rather than handing you the junk, so check it before trusting a Bing result set. Prefer Yahoo or DuckDuckGo where you can. |
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

## Telling failures apart

Failures are never silent, and never dressed up as results. Four different things
can go wrong, and each has its own answer:

```python
if engine.http_status == 0: ...   # proxy/network never got there
elif engine.is_banned: ...        # the engine blocked us
elif engine.is_degraded: ...      # it answered, but not about your query
elif not len(results): ...        # the query really has no hits
```

- **`http_status`** holds the last response code. `0` means the request never
  landed at all — a proxy, DNS or TLS failure rather than anything the engine did.
- **`is_banned`** covers captcha and block pages, including the ones served with
  HTTP 200, and challenge responses like HTTP 202.
- **`is_degraded`** covers an engine that answered normally but returned a full
  page of results matching your query nowhere. Those results are dropped rather
  than reported: a fabricated hit in a report is worse than no hit at all. The
  test is deliberately blunt — a full page and not one query word anywhere in it —
  so a thin tail of genuine results cannot trip it.

Every result also carries **`source`**, naming the engine that actually produced
it. With a fallback in play that differs from the engine you asked, and reports
should record what really happened.

## Where you run from matters

Blocking depends on your address, not just your code. A cloud server gets
challenged far sooner than a home connection, and the same query can return
results from one exit and a captcha from another. An engine reporting
`is_banned` is not evidence that its parser broke.

A proxy is worth a try — `Bing(proxy="http://user:pass@host:port")` takes any
[`aiohttp_socks`](https://pypi.org/project/aiohttp-socks/) URL, and both
`socks5://` and `socks5h://` work — but it is not a guaranteed fix. Startpage
and Mojeek turn away proxy addresses too.

Treat engine choice, not proxies, as the main lever. Where an engine has to
work, [use a fallback](../README.md#falling-back-to-the-paid-api-when-an-engine-fails).
