import asyncio
from collections import namedtuple

import aiohttp
from aiohttp_socks import ProxyConnector

from .config import TIMEOUT, PROXY, USER_AGENT
from . import utils as utl


response = namedtuple('response', ['http', 'html'])


class HttpClient(object):
    '''Performs HTTP requests. A `aiohttp` wrapper, essentialy'''
    def __init__(self, timeout=TIMEOUT, proxy=PROXY):
        self.proxy = proxy
        self.session = None

        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
        }

        self.timeout = timeout
        self.response = response

    def _proxy_url(self):
        '''python_socks rejects the socks5h scheme outright, and does not need
        it: it resolves DNS on the proxy (rdns=True) either way.
        '''
        if self.proxy and self.proxy.startswith('socks5h://'):
            return 'socks5://' + self.proxy[len('socks5h://'):]
        return self.proxy

    def _session(self):
        '''Creates the session on first use: aiohttp requires a running loop.'''
        if self.session is None:
            proxy = self._proxy_url()
            connector = ProxyConnector.from_url(proxy) if proxy else None
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def close(self):
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def get(self, page):
        '''Submits a HTTP GET request.'''
        return await self._request('get', page)

    async def post(self, page, data):
        '''Submits a HTTP POST request.'''
        return await self._request('post', page, data)

    async def _request(self, method, page, data=None):
        page = self._quote(page)
        kwargs = {'headers': self.headers, 'timeout': aiohttp.ClientTimeout(total=self.timeout)}
        if data is not None:
            kwargs['data'] = data
        try:
            req = await getattr(self._session(), method)(page, **kwargs)
            text = await req.text()
            self.headers['Referer'] = page
        except Exception as e:
            # Any transport failure is reported as http=0, never raised: one
            # unreachable engine must not sink a multi-engine search. Note that
            # aiohttp_socks errors subclass plain Exception - not ClientError,
            # not TimeoutError, not OSError - so nothing narrower catches them.
            # CancelledError is a BaseException and still propagates.
            return self.response(http=0, html=_error_msg(e))
        return self.response(http=req.status, html=text)

    def _quote(self, url):
        '''URL-encodes URLs.'''
        if utl.decode_bytes(utl.unquote_url(url)) == utl.decode_bytes(url):
            url = utl.quote_url(url)
        return url


class CurlHttpClient(HttpClient):
    '''Same interface as HttpClient, but talks through curl_cffi with a Chrome
    TLS fingerprint. Engines behind a HTTP/2 + JA3 check (Yahoo, DuckDuckGo)
    get plain HTTP/1.1 requests rejected outright.
    '''
    impersonate = 'chrome'

    def __init__(self, timeout=TIMEOUT, proxy=PROXY):
        super(CurlHttpClient, self).__init__(timeout, proxy)
        # curl_cffi supplies the browser headers; ours would break the disguise.
        # Anything an engine adds later via set_headers() is still sent.
        self.headers = {}

    def _proxy_url(self):
        '''curl needs socks5h to resolve DNS through the proxy; plain socks5
        fails with "Failed to receive SOCKS response". Opposite of aiohttp,
        so the same proxy string works for every engine either way.
        '''
        if self.proxy and self.proxy.startswith('socks5://'):
            return 'socks5h://' + self.proxy[len('socks5://'):]
        return self.proxy

    def _session(self):
        if self.session is None:
            from curl_cffi.requests import AsyncSession

            kwargs = {'impersonate': self.impersonate}
            proxy = self._proxy_url()
            if proxy:
                kwargs['proxies'] = {'http': proxy, 'https': proxy}
            self.session = AsyncSession(**kwargs)
        return self.session

    async def _request(self, method, page, data=None):
        page = self._quote(page)
        kwargs = {'timeout': self.timeout, 'allow_redirects': True}
        if self.headers:
            kwargs['headers'] = self.headers
        if data is not None:
            kwargs['data'] = data
        try:
            req = await getattr(self._session(), method)(page, **kwargs)
        except Exception as e:
            return self.response(http=0, html=_error_msg(e))
        self.headers['Referer'] = page
        return self.response(http=req.status_code, html=req.text)


def _error_msg(e):
    return '{}: {}'.format(type(e).__name__, e) if str(e) else type(e).__name__
