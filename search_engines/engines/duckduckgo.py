from urllib.parse import urlparse, parse_qs

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from ..http_client import CurlHttpClient


class Duckduckgo(SearchEngine):
    '''Searches duckduckgo.com.

    The HTML endpoint answers plain HTTP/1.1 requests with an HTTP 202
    challenge page, so it needs the same Chrome TLS fingerprint as Yahoo.
    '''

    _http_client_class = CurlHttpClient

    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Duckduckgo, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://html.duckduckgo.com/html/'
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a.result__snippet', 
            'title': 'h2.result__title a', 
            'text': 'a.result__snippet', 
            'links': 'div.results div.result.results_links.results_links_deep.web-result', 
            'next': {'forms':'div.nav-link > form', 'inputs':'input[name]'}
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        data = {'q':self._query, 'b':'', 'kl':'us-en'} 
        return {'url':self._base_url, 'data':data}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        forms = tags.select(selector['forms'])
        url, data = None, None

        if forms:
            form = forms[-1]
            data = {i['name']:i.get('value', '') for i in form.select(selector['inputs'])}
            url = self._base_url
        return {'url':url, 'data':data}

    def _get_url(self, tag, item='href'):
        '''Returns the URL of search results item.

        GET responses wrap links in a protocol-relative
        `//duckduckgo.com/l/?uddg=<target>` redirect; POST ones do not.
        '''
        url = super(Duckduckgo, self)._get_url(tag, item)
        if '/l/?' in url:
            target = parse_qs(urlparse(url).query).get('uddg', [u''])[0]
            url = target or url
        return url
