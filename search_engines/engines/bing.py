import base64
import binascii
from urllib.parse import urlparse, parse_qs

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT
from ..utils import unquote_url


class Bing(SearchEngine):
    '''Searches bing.com'''

    _block_markers = ('Please solve the challenge below',)
    _per_page = 10

    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Bing, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.bing.com'
        self._offset = 0
        self.set_headers({'User-Agent':FAKE_USER_AGENT})

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a[href]', 
            'title': 'h2', 
            'text': 'p', 
            'links': 'ol#b_results > li.b_algo', 
            'next': 'div#b_content nav[role="navigation"] a.sb_pagN'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        url = u'{}/search?q={}'.format(self._base_url, self._query)
        return {'url':url, 'data':None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        next_page = self._get_tag_item(tags.select_one(selector), 'href')
        self._offset += self._per_page
        if next_page:
            url = self._base_url + next_page
        else:
            # Bing serves plain clients a page with no pagination nav. `first`
            # is the offset param those links carry anyway, so build it by hand.
            url = u'{}/search?q={}&first={}'.format(
                self._base_url, self._query, self._offset + 1
            )
        return {'url':url, 'data':None}

    def _get_url(self, tag, item='href'):
        '''Returns the URL of search results item, unwrapping Bing's redirect.'''
        selector = self._selectors('url')
        url = self._get_tag_item(tag.select_one(selector), item)
        return unquote_url(unwrap_redirect(url))


def unwrap_redirect(url):
    '''Bing serves results as bing.com/ck/a?...&u=a1<base64> redirects.
    Decodes the `u` param to recover the real target URL.
    '''
    parts = urlparse(url)
    if 'bing.com' not in parts.netloc or '/ck/' not in parts.path:
        return url
    encoded = parse_qs(parts.query).get('u', [u''])[0]
    if not encoded.startswith('a1'):
        return url
    encoded = encoded[2:]
    try:
        padded = encoded + '=' * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(padded).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return url

