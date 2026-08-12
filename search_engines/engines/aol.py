from .yahoo import Yahoo
from ..config import PROXY, TIMEOUT


class Aol(Yahoo):
    '''Searches aol.com.

    AOL retired its own search: `search.aol.com/aol/search` is a hard 404 and
    the host now redirects to Yahoo's syndicated-search (YHS) endpoint, which
    is what this queries. Same index and markup as Yahoo, different partner tag.
    '''
    def __init__(self, proxy=PROXY, timeout=TIMEOUT, *args, **kwargs):
        super(Aol, self).__init__(proxy, timeout, *args, **kwargs)
        self._base_url = u'https://search.yahoo.com'

    async def _first_page(self):
        '''Returns the initial page and query.'''
        url_str = u'{}/yhs/search?p={}&hspart=aol&hsimp=yhs-aol_catch&ei=UTF-8&nojs=1'
        url = url_str.format(self._base_url, self._query)
        return {'url':url, 'data':None}
