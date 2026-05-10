"""Mocked engine tests — no real HTTP. Each engine's `_get_page` is patched
to return canned HTML/JSON so we exercise selector / parser logic only.
Runs on every supported Python version in CI.
"""
import json
import sys
from collections import namedtuple
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from search_engines import Aol, Bing, Brave, Startpage, Yahoo  # noqa: E402

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
