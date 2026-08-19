"""Mocked engine tests — no real HTTP. Each engine's `_get_page` is patched
to return canned HTML/JSON so we exercise selector / parser logic only.
Runs on every supported Python version in CI.
"""
import asyncio
import json
import sys
from collections import namedtuple
from pathlib import Path

import pytest
from aiohttp_socks import ProxyConnectionError, ProxyTimeoutError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from search_engines import Aol, Bing, Brave, Duckduckgo, SearchApi, Startpage, Yahoo  # noqa: E402
from search_engines.http_client import HttpClient  # noqa: E402
from search_engines.multiple_search_engines import (  # noqa: E402
    AllSearchEngines, MultipleSearchEngines,
)

Response = namedtuple('Response', ['http', 'html'])


# ---------- canned payloads ----------

BING_HTML = """
<html><body><ol id="b_results">
  <li class="b_algo">
    <h2><a href="https://example.com/bing-1">Bing Result 1</a></h2>
    <p>Bing snippet 1</p>
  </li>
  <li class="b_algo">
    <h2><a href="https://example.com/bing-2">Bing Result 2</a></h2>
    <p>Bing snippet 2</p>
  </li>
</ol></body></html>
"""

BRAVE_PAYLOAD = {
    "web": {
        "results": [
            {"url": "https://example.com/brave-1", "title": "Brave 1", "description": "Brave snippet 1"},
            {"url": "https://example.com/brave-2", "title": "Brave 2", "description": "Brave snippet 2"},
        ]
    }
}

YAHOO_HTML = """
<html><body><div id="web"><ol>
  <li>
    <div class="dd algo algo-sr">
      <div class="compTitle">
        <a href="https://example.com/yahoo-1">link</a>
        <h3 class="title"><a href="https://example.com/yahoo-1">Yahoo 1</a></h3>
      </div>
      <div class="compText">Yahoo snippet 1</div>
    </div>
  </li>
  <li>
    <div class="dd algo algo-sr">
      <div class="compTitle">
        <a href="https://example.com/yahoo-2">link</a>
        <h3 class="title"><a href="https://example.com/yahoo-2">Yahoo 2</a></h3>
      </div>
      <div class="compText">Yahoo snippet 2</div>
    </div>
  </li>
</ol></div></body></html>
"""

# Startpage's _first_page hits the homepage to harvest hidden form inputs,
# then POSTs to /sp/search. One HTML doc serves both: it has both the form
# AND the result block, so whichever URL the patched _get_page is asked for
# returns something the parser can use.
STARTPAGE_HTML = """
<html><body>
  <form id="search">
    <input name="cat" value="web"/>
    <input name="cmd" value="process_search"/>
  </form>
  <div class="result">
    <a class="result-title" href="https://example.com/sp-1">Startpage 1</a>
    <p class="description">Startpage snippet 1</p>
  </div>
  <div class="result">
    <a class="result-title" href="https://example.com/sp-2">Startpage 2</a>
    <p class="description">Startpage snippet 2</p>
  </div>
</body></html>
"""


# Shape copied from a live SearchAPI response; every upstream returns this.
SEARCHAPI_PAYLOAD = {
    "search_metadata": {"status": "Success"},
    "organic_results": [
        {"position": 1, "title": "SearchAPI 1", "link": "https://example.com/sa-1",
         "snippet": "SearchAPI snippet 1"},
        {"position": 2, "title": "SearchAPI 2", "link": "https://example.com/sa-2",
         "snippet": "SearchAPI snippet 2"},
    ],
    "pagination": {"current": 1},
}


# ---------- helpers ----------

def _silence(engine):
    engine.print_func = lambda *a, **k: None


def _patch_get_page(monkeypatch, cls, html):
    async def fake(self, page, data=None):
        return Response(http=200, html=html)
    monkeypatch.setattr(cls, '_get_page', fake)


# ---------- tests ----------

async def test_bing(monkeypatch):
    _patch_get_page(monkeypatch, Bing, BING_HTML)
    async with Bing() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    links = results.links()
    assert len(links) == 2
    assert 'https://example.com/bing-1' in links
    assert any('Bing Result 1' in r['title'] for r in results)
    assert any('Bing snippet 1' in r['text'] for r in results)


async def test_brave(monkeypatch):
    monkeypatch.setenv('BRAVE_API_KEY', 'fake-key-for-tests')

    async def fake(self, page, data=None):
        self._payload = BRAVE_PAYLOAD
        return Response(http=200, html=json.dumps(BRAVE_PAYLOAD))

    monkeypatch.setattr(Brave, '_get_page', fake)
    async with Brave() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    links = results.links()
    assert len(links) == 2
    assert links[0] == 'https://example.com/brave-1'
    assert results._results[0]['title'] == 'Brave 1'
    assert results._results[0]['text'] == 'Brave snippet 1'


async def test_brave_requires_api_key(monkeypatch):
    monkeypatch.delenv('BRAVE_API_KEY', raising=False)
    with pytest.raises(ValueError):
        Brave()


def _patch_http_get(monkeypatch, http, body):
    """Patches the transport, not _get_page, so the JSON parsing runs for real."""
    async def fake(self, page, data=None):
        return Response(http=http, html=body)
    monkeypatch.setattr(HttpClient, 'get', fake)


async def test_searchapi(monkeypatch):
    monkeypatch.setenv('SEARCHAPI_KEY', 'fake-key-for-tests')
    _patch_http_get(monkeypatch, 200, json.dumps(SEARCHAPI_PAYLOAD))
    async with SearchApi(engine='duckduckgo') as e:
        _silence(e)
        results = await e.search('test', pages=1)
    assert results.links() == ['https://example.com/sa-1', 'https://example.com/sa-2']
    assert results._results[0]['title'] == 'SearchAPI 1'
    assert results._results[0]['text'] == 'SearchAPI snippet 1'
    assert results._results[0]['host'] == 'example.com'


async def test_searchapi_reports_the_api_error(monkeypatch):
    """A dead key and an exhausted balance must not look like an empty result."""
    monkeypatch.setenv('SEARCHAPI_KEY', 'fake-key-for-tests')
    _patch_http_get(monkeypatch, 401, '{"error": "Invalid API key."}')
    logged = []
    async with SearchApi() as e:
        e.print_func = lambda msg, **k: logged.append(msg)
        results = await e.search('test', pages=1)
    assert len(results) == 0
    assert e.http_status == 401
    assert any('Invalid API key.' in m for m in logged)


async def test_searchapi_empty_page_stops_pagination(monkeypatch):
    monkeypatch.setenv('SEARCHAPI_KEY', 'fake-key-for-tests')
    calls = []

    async def fake(self, page, data=None):
        calls.append(page)
        return Response(http=200, html='{"organic_results": []}')

    monkeypatch.setattr(HttpClient, 'get', fake)
    async with SearchApi() as e:
        _silence(e)
        await e.search('test', pages=5)
    assert len(calls) == 1


async def test_searchapi_requires_api_key(monkeypatch):
    monkeypatch.delenv('SEARCHAPI_KEY', raising=False)
    with pytest.raises(ValueError):
        SearchApi()


async def test_searchapi_rejects_upstream_it_does_not_offer(monkeypatch):
    """Brave, Mojeek and Startpage are not proxied - fail loudly, not at runtime."""
    monkeypatch.setenv('SEARCHAPI_KEY', 'fake-key-for-tests')
    with pytest.raises(ValueError):
        SearchApi(engine='brave')


async def test_results_carry_their_source(monkeypatch):
    _patch_get_page(monkeypatch, Bing, BING_HTML)
    async with Bing() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    assert all(r['source'] == 'bing' for r in results)


async def test_yahoo(monkeypatch):
    _patch_get_page(monkeypatch, Yahoo, YAHOO_HTML)
    async with Yahoo() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    links = results.links()
    assert len(links) == 2
    assert 'https://example.com/yahoo-1' in links
    assert any('Yahoo 1' in r['title'] for r in results)
    assert any('Yahoo snippet 1' in r['text'] for r in results)


async def test_aol(monkeypatch):
    _patch_get_page(monkeypatch, Aol, YAHOO_HTML)

    async def fake_first(self):
        return {'url': self._base_url + '/aol/search?q=test', 'data': None}

    monkeypatch.setattr(Aol, '_first_page', fake_first)
    async with Aol() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    links = results.links()
    assert len(links) == 2
    assert 'https://example.com/yahoo-1' in links


async def test_startpage(monkeypatch):
    _patch_get_page(monkeypatch, Startpage, STARTPAGE_HTML)
    async with Startpage() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    links = results.links()
    assert len(links) == 2
    assert 'https://example.com/sp-1' in links
    assert any('Startpage 1' in r['title'] for r in results)


# ---------- regression tests ----------

BING_REDIRECT_HTML = """
<html><body><ol id="b_results">
  <li class="b_algo">
    <h2><a href="https://www.bing.com/ck/a?!&amp;&amp;p=abc&amp;u=a1aHR0cHM6Ly93d3cucHl0aG9uLm9yZy8&amp;ntb=1">Python</a></h2>
    <p>snippet</p>
  </li>
</ol></body></html>
"""

DDG_REDIRECT_HTML = """
<html><body><div class="results">
  <div class="result results_links results_links_deep web-result">
    <h2 class="result__title"><a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.python.org%2F&amp;rut=x">Python</a></h2>
    <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.python.org%2F&amp;rut=x">snippet</a>
  </div>
</div></body></html>
"""


async def test_bing_unwraps_redirect(monkeypatch):
    '''Bing hands out bing.com/ck/a redirects; the real URL is base64 in `u`.'''
    _patch_get_page(monkeypatch, Bing, BING_REDIRECT_HTML)
    async with Bing() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    assert results.links() == ['https://www.python.org/']


async def test_duckduckgo_unwraps_redirect(monkeypatch):
    '''GET responses wrap links in a protocol-relative /l/?uddg= redirect.'''
    _patch_get_page(monkeypatch, Duckduckgo, DDG_REDIRECT_HTML)
    async with Duckduckgo() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    assert results.links() == ['https://www.python.org/']


async def test_block_page_with_http_200_is_a_ban(monkeypatch):
    '''A captcha served with HTTP 200 must not read as "no results".'''
    _patch_get_page(monkeypatch, Startpage, '<html><body>sp/captcha-block</body></html>')
    async with Startpage() as e:
        _silence(e)
        results = await e.search('test', pages=1)
    assert len(results) == 0
    assert e.is_banned


async def test_empty_page_stops_pagination(monkeypatch):
    '''A page with no new results must not burn the remaining page budget.'''
    calls = []

    async def fake(self, page, data=None):
        calls.append(page)
        return Response(http=200, html='<html><body></body></html>')

    monkeypatch.setattr(Bing, '_get_page', fake)
    async with Bing() as e:
        _silence(e)
        await e.search('test', pages=20)
    assert len(calls) == 1


@pytest.mark.parametrize('exc', [
    asyncio.TimeoutError(),                  # not an aiohttp.ClientError
    ProxyTimeoutError('Proxy connection timed out: 60'),   # subclasses plain Exception
    ProxyConnectionError('refused'),
])
async def test_transport_errors_do_not_raise(monkeypatch, exc):
    '''Transport failures must surface as http=0, not escape search().'''

    class Boom:
        async def get(self, *a, **k):
            raise exc

    async with Bing() as e:
        _silence(e)
        monkeypatch.setattr(HttpClient, '_session', lambda self: Boom())
        results = await e.search('test', pages=1)
    assert len(results) == 0
    assert not e.is_banned          # a broken path is not a ban
    assert e.http_status == 0       # ...and is distinguishable from empty


async def test_engine_constructs_outside_event_loop():
    '''aiohttp needs a running loop; the session must be created lazily.'''
    engine = await asyncio.get_running_loop().run_in_executor(None, Bing)
    await engine.close()


async def test_multiple_engines_is_async_context_manager(monkeypatch):
    _patch_get_page(monkeypatch, Bing, BING_HTML)
    async with MultipleSearchEngines(['bing']) as engines:
        results = await engines.search('test', pages=1)
    assert len(results) == 2


async def test_all_engines_skips_unconfigured(monkeypatch):
    '''Brave raises without an API key; that must not sink the whole run.'''
    monkeypatch.delenv('BRAVE_API_KEY', raising=False)
    engines = AllSearchEngines()
    await engines.close()
    names = [e.__class__.__name__ for e in engines._engines]
    assert 'Brave' not in names
    assert 'Bing' in names


def test_filters_apply_to_json_engines(monkeypatch):
    '''The host filter used to NameError on the JSON engines.'''
    monkeypatch.setenv('BRAVE_API_KEY', 'fake-key-for-tests')
    e = Brave()
    e._filters = ['host']
    e._query = 'python.org'
    items = [
        {'host': 'python.org', 'link': 'https://python.org/a', 'title': '', 'text': ''},
        {'host': 'example.com', 'link': 'https://example.com/b', 'title': '', 'text': ''},
    ]
    assert e._apply_filters(items) == items[:1]


# ---------- degraded results ----------

# Ten real-looking links with nothing to do with the query: what Bing serves a
# datacenter address instead of a captcha. Shape copied from a live response.
JUNK_HTML = '<html><body><ol id="b_results">' + ''.join(
    '<li class="b_algo"><h2><a href="https://mlb.com/news/{n}">Baseball story {n}'
    '</a></h2><p>Scores and standings</p></li>'.format(n=n)
    for n in range(1, 11)
) + '</ol></body></html>'


async def test_unrelated_results_are_not_reported_as_findings(monkeypatch):
    """A full page matching the query nowhere is junk, not a result set."""
    _patch_get_page(monkeypatch, Bing, JUNK_HTML)
    async with Bing() as e:
        _silence(e)
        results = await e.search('soxoj maigret', pages=1)

    assert e.is_degraded is True
    assert len(results) == 0, 'fabricated hits must not reach the report'
    assert e.http_status == 200 and e.is_banned is False


async def test_relevant_results_are_not_flagged(monkeypatch):
    """The guard must stay quiet on a healthy page."""
    _patch_get_page(monkeypatch, Bing, JUNK_HTML)
    async with Bing() as e:
        _silence(e)
        results = await e.search('baseball', pages=1)

    assert e.is_degraded is False
    assert len(results) == 10


async def test_thin_result_sets_are_never_flagged(monkeypatch):
    """Judging relevance off a couple of tail results is noise, not signal."""
    _patch_get_page(monkeypatch, Bing, BING_HTML)
    async with Bing() as e:
        _silence(e)
        results = await e.search('something else entirely', pages=1)

    assert e.is_degraded is False
    assert len(results) == 2


def test_query_terms_ignore_operators():
    e = Bing()
    e._query = 'site:github.com "soxoj" a -maigret'
    terms = e._query_terms()
    assert 'github.com' in terms
    assert 'soxoj' in terms
    assert 'maigret' in terms
    assert 'a' not in terms, 'too short to carry signal'
