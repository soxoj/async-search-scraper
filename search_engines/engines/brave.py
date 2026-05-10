import json
import os
from urllib.parse import urlencode

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from .. import utils


class Brave(SearchEngine):
    '''Searches Brave via the official Brave Search API.

    Requires an API key from https://api.search.brave.com. Pass it via the
    ``api_key`` keyword argument or set the ``BRAVE_API_KEY`` environment
    variable.
    '''

    _api_url = 'https://api.search.brave.com/res/v1/web/search'
    _per_page = 20
    _max_offset = 9

    def __init__(self, proxy=PROXY, timeout=TIMEOUT, api_key=None, *args, **kwargs):
        super(Brave, self).__init__(proxy, timeout, *args, **kwargs)
        self._api_key = api_key or os.environ.get('BRAVE_API_KEY')
        if not self._api_key:
            raise ValueError(
                'Brave requires an API key. Set BRAVE_API_KEY '
                'or pass api_key= to the constructor.'
            )
        self._current_page = 0
        self._payload = None
        self.set_headers({
            'X-Subscription-Token': self._api_key,
            'Accept': 'application/json',
        })

    def _selectors(self, element):
        selectors = {
            'url': 'url',
            'title': 'title',
            'text': 'description',
            'links': 'web.results',
        }
        return selectors[element]

    def _build_url(self, offset):
        params = urlencode({
            'q': self._query,
            'count': self._per_page,
            'offset': offset,
        })
        return '{}?{}'.format(self._api_url, params)

    async def _first_page(self):
        self._current_page = 0
        return {'url': self._build_url(0), 'data': None}

    def _next_page(self, tags):
        self._current_page += 1
        if self._current_page > self._max_offset:
            return {'url': None, 'data': None}
        results = (self._payload or {}).get('web', {}).get('results') or []
        if len(results) < self._per_page:
            return {'url': None, 'data': None}
        return {'url': self._build_url(self._current_page), 'data': None}

    async def _get_page(self, page, data=None):
        resp = await self._http_client.get(page)
        if resp.http == 200:
            try:
                self._payload = json.loads(resp.html)
            except ValueError:
                self._payload = None
        else:
            self._payload = None
        return resp

    def _filter_results(self, soup):
        items = (self._payload or {}).get('web', {}).get('results') or []
        results = [self._item_from_dict(r) for r in items]

        if u'url' in self._filters:
            results = [l for l in results if self._query_in(l['link'])]
        if u'title' in self._filters:
            results = [l for l in results if self._query_in(l['title'])]
        if u'text' in self._filters:
            results = [l for l in results if self._query_in(l['text'])]
        if u'host' in self._filters:
            results = [l for l in results if self._query_in(utils.domain(l['link']))]
        return results

    def _item_from_dict(self, r):
        link = utils.unquote_url(r.get('url', u''))
        return {
            'host': utils.domain(link),
            'link': link,
            'title': (r.get('title') or u'').strip(),
            'text': (r.get('description') or u'').strip(),
        }
