import json
import os
from urllib.parse import urlencode

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from .. import utils
from .. import output as out


class SearchApi(SearchEngine):
    '''Searches via the SearchAPI.io SERP API.

    One class covers every upstream engine they proxy, because the response
    shape is the same for all of them: ``organic_results`` with ``link``,
    ``title`` and ``snippet``. Pick the upstream with ``engine=``::

        SearchApi(engine='google')

    Requires an API key from https://www.searchapi.io. Pass it via the
    ``api_key`` keyword argument or set the ``SEARCHAPI_KEY`` environment
    variable.
    '''

    _api_url = 'https://www.searchapi.io/api/v1/search'
    _upstream = 'google'
    _per_page = 10
    engines = ('google', 'bing', 'duckduckgo', 'yahoo', 'yandex', 'naver', 'baidu')
    '''Upstreams verified to exist. Brave, Mojeek and Startpage are not offered.'''

    def __init__(self, proxy=PROXY, timeout=TIMEOUT, api_key=None, engine=None,
                 *args, **kwargs):
        super(SearchApi, self).__init__(proxy, timeout, *args, **kwargs)
        self._api_key = api_key or os.environ.get('SEARCHAPI_KEY')
        if not self._api_key:
            raise ValueError(
                'SearchApi requires an API key. Set SEARCHAPI_KEY '
                'or pass api_key= to the constructor.'
            )
        self._upstream = engine or self._upstream
        if self._upstream not in self.engines:
            raise ValueError('Unsupported upstream engine "{}". Available: {}'.format(
                self._upstream, ', '.join(self.engines)
            ))
        self._current_page = 1
        self._payload = None

    @property
    def _source(self):
        # Which upstream answered matters: 'searchapi' alone would not say
        # whether a hit came from Google or from Yandex.
        return 'searchapi:' + self._upstream

    def _selectors(self, element):
        selectors = {
            'url': 'link',
            'title': 'title',
            'text': 'snippet',
            'links': 'organic_results',
        }
        return selectors[element]

    def _build_url(self, page):
        params = urlencode({
            'engine': self._upstream,
            'q': self._query,
            'page': page,
            'api_key': self._api_key,
        })
        return '{}?{}'.format(self._api_url, params)

    async def _first_page(self):
        self._current_page = 1
        return {'url': self._build_url(1), 'data': None}

    def _next_page(self, tags):
        # Stop on an empty page rather than trusting the pagination block: its
        # shape differs per upstream (DuckDuckGo hands back a token, Yandex a
        # URL), while `page` counts the same way for all of them.
        if not self._organic():
            return {'url': None, 'data': None}
        self._current_page += 1
        return {'url': self._build_url(self._current_page), 'data': None}

    async def _get_page(self, page, data=None):
        resp = await self._http_client.get(page)
        try:
            self._payload = json.loads(resp.html)
        except ValueError:
            self._payload = None
        if resp.http != 200:
            # The body carries the reason - a bare "HTTP 401" would leave the
            # user guessing between a bad key and an exhausted balance.
            error = (self._payload or {}).get('error')
            if error:
                self.print_func(u'SearchAPI: ' + error, level=out.Level.error)
        return resp

    def _organic(self):
        return (self._payload or {}).get('organic_results') or []

    def _filter_results(self, soup):
        return self._apply_filters([self._item_from_dict(r) for r in self._organic()])

    def _item_from_dict(self, r):
        link = utils.unquote_url(r.get('link', u''))
        return {
            'host': utils.domain(link),
            'link': link,
            'title': (r.get('title') or u'').strip(),
            'text': (r.get('snippet') or u'').strip(),
        }

