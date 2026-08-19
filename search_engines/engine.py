import asyncio
import re

from bs4 import BeautifulSoup
from random import uniform as random_uniform

from .results import SearchResults
from .http_client import HttpClient
from . import utils
from . import output as out
from . import config as cfg


class SearchEngine(object):
    '''The base class for all Search Engines.'''

    _http_client_class = HttpClient
    '''The transport. Engines behind a TLS fingerprint check swap in CurlHttpClient.'''
    _block_markers = ()
    '''Strings that mark a captcha/block page served with HTTP 200.'''

    def __init__(self, proxy=cfg.PROXY, timeout=cfg.TIMEOUT, *args, **kwargs):
        '''
        :param str proxy: optional, a proxy server
        :param int timeout: optional, the HTTP timeout
        '''
        self._http_client = self._http_client_class(timeout, proxy)
        self._query = ''
        self._filters = []

        self._min_delay = kwargs.get('min_delay', 1)
        _max_delay = kwargs.get('max_delay', 4)
        self._max_delay = max(self._min_delay, _max_delay)
        self._delay = (self._min_delay, self._max_delay)

        self.print_func = kwargs.get('print_func')
        if not self.print_func:
            self.print_func = out.console

        if kwargs.get('suppress_console_output'):
            self.print_func = out.devnull

        self.results = SearchResults()
        '''The search results.'''
        self.ignore_duplicate_urls = False
        '''Collects only unique URLs.'''
        self.ignore_duplicate_domains = False
        '''Collects only unique domains.'''
        self.is_banned = False
        '''Indicates if a ban occured'''
        self.http_status = None
        '''HTTP status of the last response; 0 means the request never landed.
        Tells a transport failure apart from a genuinely empty result set.'''

        self.is_degraded = False
        '''True when the engine answered 200 with results unrelated to the query.
        Bing does this to addresses it dislikes instead of showing a captcha.'''

    @property
    def _source(self):
        '''Names the engine that produced a result, for the `source` field.'''
        return self.__class__.__name__.lower()

    async def __aenter__(self):
        return self

    async def close(self):
        await self._http_client.close()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _selectors(self, element):
        '''Returns the appropriate CSS selector.'''
        raise NotImplementedError()
    
    async def _first_page(self):
        '''Returns the initial page URL.'''
        raise NotImplementedError()
    
    def _next_page(self, tags):
        '''Returns the next page URL and post data.'''
        raise NotImplementedError()
    
    def _get_url(self, tag, item='href'):
        '''Returns the URL of search results items.'''
        selector = self._selectors('url')
        url = self._get_tag_item(tag.select_one(selector), item)
        return utils.unquote_url(url)
    
    def _get_title(self, tag, item='text'):
        '''Returns the title of search results items.'''
        selector = self._selectors('title')
        return self._get_tag_item(tag.select_one(selector), item)
    
    def _get_text(self, tag, item='text'):
        '''Returns the text of search results items.'''
        selector = self._selectors('text')
        return self._get_tag_item(tag.select_one(selector), item)
    
    def _get_page(self, page, data=None):
        '''Gets pagination links.'''
        if data:
            return self._http_client.post(page, data)
        return self._http_client.get(page)
    
    def _get_tag_item(self, tag, item):
        '''Returns Tag attributes.'''
        if not tag:
            return u''
        return tag.text if item == 'text' else tag.get(item, u'')

    def _item(self, link):
        '''Returns a dictionary of the link data.'''
        return {
            'host': utils.domain(self._get_url(link)), 
            'link': self._get_url(link), 
            'title': self._get_title(link).strip(), 
            'text': self._get_text(link).strip()
        } 

    def _query_in(self, item):
        '''Checks if query is contained in the item.'''
        return self._query.lower() in item.lower()

    def _query_terms(self):
        '''The query words worth matching against, operators stripped.'''
        terms = []
        for term in re.split(r'\s+', self._query.lower()):
            term = term.strip(u'"\'()').lstrip(u'+-')
            if u':' in term:
                # site:github.com - the value is the part that shows up in results
                term = term.split(u':', 1)[-1]
            if len(term) >= 3:
                terms.append(term)
        return terms

    def _looks_degraded(self, items):
        '''True when a full page of results mentions the query nowhere.

        Bing serves addresses it dislikes a page of real-looking but unrelated
        links under HTTP 200 - no captcha, no error code, different junk every
        time. Nothing in the markup distinguishes it, so the query itself is
        the only available signal.
        '''
        # ponytail: needs a FULL page with zero term hits, so a thin tail of
        # genuine results cannot trip it. Tighten only if false positives show
        # up in practice - the cost of a miss here is a fabricated finding.
        terms = self._query_terms()
        if len(items) < 5 or not terms:
            return False
        haystack = u' '.join(
            u'{} {} {}'.format(i['title'], i['text'], i['link']) for i in items
        ).lower()
        return not any(term in haystack for term in terms)
    
    def _apply_filters(self, results):
        '''Applies the active search operators to parsed results.'''
        if u'url' in self._filters:
            results = [l for l in results if self._query_in(l['link'])]
        if u'title' in self._filters:
            results = [l for l in results if self._query_in(l['title'])]
        if u'text' in self._filters:
            results = [l for l in results if self._query_in(l['text'])]
        if u'host' in self._filters:
            results = [l for l in results if self._query_in(utils.domain(l['link']))]
        return results

    def _filter_results(self, soup):
        '''Processes and filters the search results.'''
        tags = soup.select(self._selectors('links'))
        return self._apply_filters([self._item(l) for l in tags])

    def _collect_results(self, items):
        '''Colects the search results items. Returns the number kept.'''
        collected = 0
        for item in items:
            if not utils.is_url(item['link']):
                continue
            # Stamped before the dedup checks below, so stored and incoming
            # items stay comparable.
            item.setdefault('source', self._source)
            if item in self.results:
                continue
            if self.ignore_duplicate_urls and item['link'] in self.results.links():
                continue
            if self.ignore_duplicate_domains and item['host'] in self.results.hosts():
                continue
            self.results.append(item)
            collected += 1
        return collected

    def _is_ok(self, response):
        '''Checks if the HTTP response is 200 OK and not a block page.'''
        # 202 is what DuckDuckGo and Dogpile answer with when they serve a
        # challenge page instead of results.
        blocked = any(m in (response.html or u'') for m in self._block_markers)
        self.http_status = response.http
        self.is_banned = response.http in [202, 403, 429, 503] or blocked

        if response.http == 200 and not blocked:
            return True
        if blocked:
            msg = u'Blocked by ' + self.__class__.__name__
        else:
            msg = ('HTTP ' + str(response.http)) if response.http else response.html
        self.print_func(msg, level=out.Level.error)
        return False

    def set_headers(self, headers):
        '''Sets HTTP headers.
        
        :param headers: dict The headers 
        '''
        self._http_client.headers.update(headers)
    
    def set_search_operator(self, operator):
        '''Filters search results based on the operator. 
        Supported operators: 'url', 'title', 'text', 'host'

        :param operator: str The search operator(s)
        '''
        operators = utils.decode_bytes(operator or u'').lower().split(u',')
        supported_operators = [u'url', u'title', u'text', u'host']

        for operator in operators:
            if operator not in supported_operators:
                msg = u'Ignoring unsupported operator "{}"'.format(operator)
                self.print_func(msg, level=out.Level.warning)
            else:
                self._filters += [operator]
    
    async def search(self, query, pages=cfg.SEARCH_ENGINE_RESULTS_PAGES):
        '''Queries the search engine, goes through the pages and collects the results.
        
        :param query: str The search query  
        :param pages: int Optional, the maximum number of results pages to search  
        :returns SearchResults object
        '''
        self.print_func('Searching {}'.format(self.__class__.__name__))
        self._query = utils.decode_bytes(query)
        request = await self._first_page()

        for page in range(1, pages + 1):
            try:
                response = await self._get_page(request['url'], request['data'])
                if not self._is_ok(response):
                    break
                tags = BeautifulSoup(response.html, "html.parser")
                items = self._filter_results(tags)

                if self._looks_degraded(items):
                    self.is_degraded = True
                    self.print_func(
                        u'{} returned results unrelated to the query - treat them '
                        u'as unreliable'.format(self._source),
                        level=out.Level.warning
                    )
                    break

                collected = self._collect_results(items)

                msg = 'page: {:<8} links: {}'.format(page, len(self.results))
                self.print_func(msg, end='')

                # Nothing new on this page: results ran out, the selectors went
                # stale, or pagination is looping. Either way the remaining pages
                # are wasted requests. Skipped when filters are on, since those
                # can legitimately empty out a page that has more behind it.
                if not collected and not self._filters:
                    break
                request = self._next_page(tags)

                if not request['url']:
                    break
                if page < pages:
                    await asyncio.sleep(random_uniform(*self._delay))
            except KeyboardInterrupt:
                break
        self.print_func('', end='')

        return self.results

    def output(self, output=out.PRINT, path=None):
        '''Prints search results and/or creates report files.
        Supported output format: html, csv, json.
        
        :param output: str Optional, the output format  
        :param path: str Optional, the file to save the report  
        '''
        output = (output or '').lower()
        if not path:
            path = cfg.os_path.join(cfg.OUTPUT_DIR, u'_'.join(self._query.split()))
        self.print_func('')

        if out.PRINT in output:
            out.print_results([self])
        if out.HTML in output:
            out.write_file(out.create_html_data([self]), path + u'.html') 
        if out.CSV in output:
            out.write_file(out.create_csv_data([self]), path + u'.csv') 
        if out.JSON in output:
            out.write_file(out.create_json_data([self]), path + u'.json')
