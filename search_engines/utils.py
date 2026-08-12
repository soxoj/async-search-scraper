from urllib.parse import quote, unquote, urlparse


def quote_url(url):
    '''encodes URLs.'''
    return quote(url, safe=';/?:@&=+$,#')

def unquote_url(url):
    '''decodes URLs.'''
    return decode_bytes(unquote(url))

def is_url(link):
    '''Checks if link is URL'''
    parts = urlparse(link)
    return bool(parts.scheme and parts.netloc)

def domain(url):
    '''Returns domain form URL'''
    host = urlparse(url).netloc
    return host.lower().split(':')[0].replace('www.', '')

def decode_bytes(s, encoding='utf-8', errors='replace'):
    '''Decodes bytes to str.'''
    return s.decode(encoding, errors=errors) if type(s) is bytes else s
