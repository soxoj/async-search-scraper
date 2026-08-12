from os import path as os_path


## Maximum number or pages to search
SEARCH_ENGINE_RESULTS_PAGES = 20

## HTTP request timeout 
TIMEOUT = 10

## Default User-Agent string 
USER_AGENT = 'search_engines/0.5 Repo: https://github.com/tasos-py/Search-Engines-Scraper'

## Fake User-Agent string - search engines don't like the default user-agent.
## Keep this current: Mojeek answers stale UAs with HTTP 403.
FAKE_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
)

## Proxy server 
PROXY = None

## TOR proxy server 
TOR = 'socks5://127.0.0.1:9050'

_base_dir = os_path.abspath(os_path.dirname(os_path.abspath(__file__)))

## Path to output files 
OUTPUT_DIR = os_path.join(_base_dir, 'search_results') + os_path.sep

