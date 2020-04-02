""" main.py """

from __future__ import annotations
from typing import Union, Optional


""" outline of modules
----------------------
MODULE 1: read input data from local file
MODULE 2: send request to FAST
MODULE 3: analyse result
MODULE 4: output result as x
"""


"""
MODULE 1
--------
1. define which files can be used and what format is required; provide template
2. json, excel should be fine for starters
"""


def open(file) -> Union[list, str]:
    pass


def parse(file):
    """ """
    data = open(file)


""" JSKOS classes 

Built based on  https://gbv.github.io/jskos/context.json """


class LanguageMap:
    """ http://gbv.github.io/jskos/jskos.html#language-map """

    def __init__(self, _mapping: dict) -> None:
        self._mapping = _mapping

    def add(self, label: str, language: str):
        """ Add a value for a language"""

        self._mapping.update({label: language})

    def get_value(self, language: str) -> Optional[str]:
        """ Get the value of a language if any """

        return self._mapping.get(language)


class Concept:
    """ http://gbv.github.io/jskos/jskos.html#concept """

    def __init__(self,
                 uri: str,
                 jtype: set = None,
                 url: str = None,
                 preflabel: LanguageMap = None,
                 inscheme: set = None,
                 ) -> None:
        self.uri = uri
        if jtype is None:
            self.jtype = set("http://www.w3.org/2004/02/skos/core#Concept")
        if url is None:
            self.url = self.uri
        self.preflabel = preflabel
        self.inscheme = inscheme

