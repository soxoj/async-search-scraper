from .aol import Aol
from .ask import Ask
from .bing import Bing
from .brave import Brave
from .dogpile import Dogpile
from .duckduckgo import Duckduckgo
from .google import Google
from .mojeek import Mojeek
from .startpage import Startpage
from .torch import Torch
from .yahoo import Yahoo
from .qwant import Qwant
from .searchapi import SearchApi


search_engines_dict = {
    'searchapi': SearchApi,
    'google': Google,
    'bing': Bing,
    'yahoo': Yahoo,
    'aol': Aol,
    'brave': Brave,
    'duckduckgo': Duckduckgo,
    'startpage': Startpage,
    'dogpile': Dogpile,
    'ask': Ask,
    'mojeek': Mojeek,
    'qwant': Qwant,
    'torch': Torch
}
