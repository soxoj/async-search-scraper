import csv
import json
import io
import re
from collections import namedtuple
from shutil import get_terminal_size

from .utils import decode_bytes


def print_results(search_engines):
    '''Prints the search results.'''
    for engine in search_engines:
        console(engine.__class__.__name__ + u' results') 

        for i, v in enumerate(engine.results, 1):
            console(u'{:<4}{}'.format(i, v['link'])) 
        console(u'')

def create_csv_data(search_engines):
    '''CSV formats the search results.'''
    data = [['query', 'engine', 'domain', 'URL', 'title', 'text']]

    for engine in search_engines:
        for i in engine.results:
            row = [
                # Per result, not per engine: with a fallback in play the two
                # differ, and the report must not credit Bing for a paid hit.
                engine._query, i.get('source', engine.__class__.__name__),
                i['host'], i['link'], i['title'], i['text']
            ]
            row = [decode_bytes(i) for i in row]
            data.append(row)
    return data

def create_json_data(search_engines):
    '''JSON formats the search results.'''
    jobj = {
        u'query': search_engines[0]._query, 
        u'results': {
            se.__class__.__name__: [i for i in se.results] 
            for se in search_engines
        }
    }
    return json.dumps(jobj)

def create_html_data(search_engines):
    '''HTML formats the search results.'''
    query = decode_bytes(search_engines[0]._query) if search_engines else u''
    tables = u''

    for engine in search_engines:
        rows = u''
        for i, v in enumerate(engine.results, 1):
            data = u''
            if u'title' in engine._filters:
                data += HtmlTemplate.data.format(_replace_with_bold(query, v['title']))
            if u'text' in engine._filters:
                data += HtmlTemplate.data.format(_replace_with_bold(query, v['text']))
            link = _replace_with_bold(query, v['link']) if u'url' in engine._filters else v['link']
            rows += HtmlTemplate.row.format(number=i, href=v['link'], link=link, data=data)
        
        engine_name = engine.__class__.__name__
        tables += HtmlTemplate.table.format(engine=engine_name, rows=rows)
    return HtmlTemplate.html.format(query=query, table=tables)

def _replace_with_bold(query, data):
    '''Places the query in <b> tags.'''
    for match in re.findall(re.escape(query), data, re.I):
        data = data.replace(match, u'<b>{}</b>'.format(match))
    return data


def write_file(data, path, encoding='utf-8'):
    '''Writes search results data to file.'''
    try:
        f = io.open(path, 'w', encoding=encoding, newline='')

        if type(data) is list:
            writer = csv.writer(f)
            writer.writerows(data)
        else:
            f.write(data)
        f.close()
        console(u'Output file: ' + path)
    except IOError as e:
        console(e, level=Level.error)


def console(msg, end='\n', level=None):
    '''Prints data on the console.'''
    console_len = get_terminal_size().columns
    clear_line = u'\r{}\r'.format(u' ' * (console_len - 1))
    msg = clear_line + (level or u'') + msg
    print(msg, end=end)


def devnull(msg, end='\n', level=None):
    pass


Level = namedtuple('Level', ['info', 'warning', 'error'])(
    info = u'INFO ',
    warning = u'WARNING ',
    error = u'ERROR '
)

PRINT = 'print'
HTML = 'html'
JSON = 'json'
CSV = 'csv'


class HtmlTemplate:
    '''HTML template.'''
    html = u'''<html>
    <head>
    <meta charset="UTF-8">
    <title>Search Results</title>
    <style>
    body {{ background-color:#f5f5f5; font-family:Italic, Charcoal, sans-serif; }} 
    a:link {{ color: #262626; }} 
    a:visited {{ color: #808080; }} 
    th {{ font-size:17px; text-align:left; padding:3px; font-style: italic; }} 
    td {{ font-size:14px; text-align:left; padding:1px; }} 
    </style>
    </head>
    <body>
    <table>
    <tr><th>Query: '{query}'</th></tr>
    <tr><td> </td></tr>
    </table>
    {table}
    </body>
    </html>
    '''
    table = u'''<table>
    <tr><th>{engine} search results </th></tr>
    </table>
    <table>
    {rows}
    </table>
    <br>
    '''
    row = u'''<tr>
    <td>{number})</td>
    <td><a href="{href}" target="_blank">{link}</a></td>
    {data}
    </tr>
    '''
    data = u'''<tr><td></td><td>{}</td></tr>'''

