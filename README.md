# async-search-scraper  

A Python library that queries Google, Bing, Yahoo and other search engines and collects the results from multiple search engine results pages.  
Please note that web-scraping may be against the TOS of some search engines, and may result in a temporary ban.

## Supported search engines  

_[Google](https://www.google.com)_  
_[Bing](https://www.bing.com)_  
_[Yahoo](https://search.yahoo.com)_  
_[Duckduckgo](https://duckduckgo.com)_  
_[Startpage](https://www.startpage.com)_  
_[Aol](https://search.aol.com)_  
_[Dogpile](https://www.dogpile.com)_  
_[Ask](https://uk.ask.com)_  
_[Mojeek](https://www.mojeek.com)_  
_[Torch](http://xmh57jrzrnw6insl.onion/4a1f6b371c/search.cgi)_  

## Features  

 - Creates output files (html, csv, json).  
 - Supports search filters (url, title, text).  
 - HTTP and SOCKS proxy support.  
 - Collects dark web links with Torch.  
 - Easy to add new search engines. You can add a new engine by creating a new class in `search_engines/engines/` and add it to the  `search_engines_dict` dictionary in `search_engines/engines/__init__.py`. The new class should subclass `SearchEngine`, and override the following methods: `_selectors`, `_first_page`, `_next_page`. 
 - Python3 only compatible.  

## Requirements  

- Python 3.6+  
- [Aiohttp](https://docs.aiohttp.org/en/stable/index.html)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

Install the dependencies this way: `$ pip3 install -r requirements.txt`

## Installation  

Run the setup file: `$ python setup.py install`.  

## Usage  

As a library:  

```
from search_engines import Google

engine = Google()
results = engine.search("my query")
links = results.links()

print(links)
```

As a CLI script:  

```  
$ python search_engines_cli.py -e google,bing -q "my query" -o json,print
```

## License

MIT © [Search-Engines-Scraper](https://github.com/tasos-py/Search-Engines-Scraper)

Original creator - Tasos M Adamopoulos
