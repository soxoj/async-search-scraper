import re
from json import loads

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT
from .. import utils


class Ask(SearchEngine):
    '''Searches ask.com'''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Ask, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.ask.com'
        self._current_page = 1
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'url', 
            'title': 'title', 
            'text': 'abstract', 
            'links': 'webResults'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        url_str = u'{}/web?q={}'
        url = url_str.format(self._base_url, self._query)
        return {'url':url, 'data':None}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        self._current_page += 1
        url = u'{}/web?q={}&page={}'.format(
            self._base_url, self._query, self._current_page
        )
        return {'url':url, 'data':None}

    def _get_url(self, tag, item='href'):
        '''Returns the URL of search results item.'''
        return utils.unquote_url(tag.get('url', u''))

    def _get_title(self, tag, item='text'):
        '''Returns the title of search results items.'''
        return tag.get('title', u'')

    def _get_text(self, tag, item='text'):
        '''Returns the text of search results items.'''
        return tag.get('abstract', u'')

    def _filter_results(self, soup):
        '''Processes and filters the search results from embedded JSON.'''
        data = None
        for script in soup.select('script'):
            text = script.string or ''
            match = re.search(r'window\.MESON\.initialState\s*=\s*(\{.+)', text)
            if match:
                raw = match.group(1).rstrip().rstrip(';')
                try:
                    data = loads(raw)
                except Exception:
                    continue
                break
        if not data:
            return []
        results_data = data.get('search', {}).get('webResults', {}).get('results', [])
        return self._apply_filters([self._item(r) for r in results_data])

