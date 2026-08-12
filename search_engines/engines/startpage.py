from bs4 import BeautifulSoup

from ..engine import SearchEngine
from ..config import PROXY, TIMEOUT, FAKE_USER_AGENT


class Startpage(SearchEngine):
    '''Searches startpage.com'''

    # Startpage answers a block with HTTP 200 and a captcha page. It rejects
    # datacenter IPs outright, so this fires often.
    _block_markers = ('blocked_feedback_form', 'sp/captcha-block', 'Startpage Blocked')

    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Startpage, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = 'https://www.startpage.com'
        self.set_headers({'User-Agent':FAKE_USER_AGENT})
    
    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        selectors = {
            'url': 'a[href]', 
            'title': 'a.result-title, div.headline a', 
            'text': 'p.description', 
            'links': 'div.result', 
            'next': 'div.pagination form',
            'search_form': 'form#search input[name]'
        }
        return selectors[element]
    
    async def _first_page(self):
        '''Returns the initial page and query.'''
        response = await self._get_page(self._base_url)
        tags = BeautifulSoup(response.html, "html.parser")
        selector = self._selectors('search_form')

        data = {
            i['name']: i.get('value', '') 
            for i in tags.select(selector)
        }
        data['query'] = self._query
        url = self._base_url + '/sp/search'
        return {'url':url, 'data':data}
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data (if any)'''
        selector = self._selectors('next')
        forms = tags.select(selector)
        url, data = None, None
        # Find the current page number, then pick the next page form
        current_page = None
        for form in forms:
            aria = form.get('aria-label', '')
            if 'current page' in aria:
                page_input = form.select_one('input[name=page]')
                if page_input:
                    current_page = int(page_input.get('value', 0))
                break
        if current_page is not None:
            next_page_num = current_page + 1
            for form in forms:
                page_input = form.select_one('input[name=page]')
                if page_input and int(page_input.get('value', 0)) == next_page_num:
                    url = self._base_url + form.get('action', '/sp/search')
                    data = {
                        i['name']:i.get('value', '') 
                        for i in form.select('input')
                    }
                    break
        return {'url':url, 'data':data}
