import re
from html import unescape

from curl_cffi.requests import AsyncSession

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from ..utils import unquote_url


class Yahoo(SearchEngine):
    '''Searches yahoo.com.

    Yahoo's frontend rejects plain HTTP/1.1 requests with HTTP 500 and
    requires a browser-like TLS fingerprint (HTTP/2 + Chrome ALPN/JA3).
    Tested with aiohttp (HTTP/1.1) and httpx http2: both fail. We use
    curl_cffi with Chrome impersonation for the engine's transport, and
    submit the GDPR consent form on first request so the resulting
    EuConsent/GUC cookies stick on the session.
    '''

    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Yahoo, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://search.yahoo.com'
        self._proxy = proxy
        self._yahoo_session = None
        self._consent_done = False

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'div.compTitle a',
            'title': 'div.compTitle h3.title',
            'text': 'div.compText',
            'links': 'div#web li div.dd.algo.algo-sr',
            'next': 'a.next'
        }
        return selectors[element]

    async def _first_page(self):
        '''Returns the initial page and query.'''
        url_str = u'{}/search?p={}&ei=UTF-8&nojs=1'
        url = url_str.format(self._base_url, self._query)
        return {'url': url, 'data': None}

    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        url = self._get_tag_item(tags.select_one(selector), 'href') or None
        return {'url': url, 'data': None}

    async def _ensure_session(self):
        if self._yahoo_session is None:
            kwargs = {'impersonate': 'chrome120'}
            if self._proxy:
                kwargs['proxies'] = {'http': self._proxy, 'https': self._proxy}
            self._yahoo_session = AsyncSession(**kwargs)

    async def close(self):
        await super(Yahoo, self).close()
        if self._yahoo_session is not None:
            await self._yahoo_session.close()
            self._yahoo_session = None

    async def _get_page(self, page, data=None):
        await self._ensure_session()
        await self._accept_consent()
        response_t = self._http_client.response
        try:
            if data:
                r = await self._yahoo_session.post(
                    page, data=data, timeout=self._http_client.timeout, allow_redirects=True,
                )
            else:
                r = await self._yahoo_session.get(
                    page, timeout=self._http_client.timeout, allow_redirects=True,
                )
        except Exception as e:
            return response_t(http=0, html=type(e).__name__)
        return response_t(http=r.status_code, html=r.text)

    async def _accept_consent(self):
        '''Yahoo redirects EU visitors through a GDPR consent page that must
        be accepted before search results are served. Submit it once so the
        resulting EuConsent/GUC cookies stick on the session.
        '''
        if self._consent_done:
            return

        probe_url = '{}/search?p=python'.format(self._base_url)
        try:
            r = await self._yahoo_session.get(
                probe_url, timeout=self._http_client.timeout, allow_redirects=True,
            )
        except Exception:
            return
        if r.status_code != 200:
            return

        text = r.text
        if 'csrfToken' not in text:
            self._consent_done = True
            return

        csrf = re.search(r'name="csrfToken" value="([^"]+)"', text)
        sid = re.search(r'name="sessionId" value="([^"]+)"', text)
        original = re.search(r'name="originalDoneUrl" value="([^"]+)"', text)
        ns = re.search(r'name="namespace" value="([^"]+)"', text)
        if not (csrf and sid and original and ns):
            return

        data = {
            'csrfToken': csrf.group(1),
            'sessionId': sid.group(1),
            'originalDoneUrl': unescape(original.group(1)),
            'namespace': ns.group(1),
            'agree': 'agree',
        }
        try:
            await self._yahoo_session.post(
                str(r.url), data=data,
                timeout=self._http_client.timeout, allow_redirects=True,
            )
        except Exception:
            return
        self._consent_done = True

    def _get_url(self, link, item='href'):
        selector = self._selectors('url')
        url = self._get_tag_item(link.select_one(selector), 'href')
        if u'/RU=' in url:
            url = url.split(u'/RU=')[-1].split(u'/R')[0]
        return unquote_url(url)

    def _get_title(self, tag, item='text'):
        '''Returns the title of search results items.'''
        title = tag.select_one(self._selectors('title'))
        return self._get_tag_item(title, item)
