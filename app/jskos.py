""" jskos.py

JSKOS classes. Built based on  https://gbv.github.io/jskos/context.json """

from __future__ import annotations
from typing import Optional, Set


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


class Resource:
    """ http://gbv.github.io/jskos/jskos.html#resource """

    def __init__(self,
                 uri: str = None,
                 form: Set[str] = None,  # form = type
                 context: str = None
                 ) -> None:
        self.uri = uri
        self.form = form
        if context is None:
            self.context = "https://gbv.github.io/jskos/context.json"


class Item(Resource):
    """ http://gbv.github.io/jskos/jskos.html#item """

    def __init__(self,
                 uri: str = None,
                 form: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 preflabel: LanguageMap = None
                 ) -> None:
        if url is None:
            self.url = uri
        self.preflabel = preflabel
        super().__init__(uri, form, context)


class Concept(Item):
    """ http://gbv.github.io/jskos/jskos.html#concept """

    def __init__(self,
                 uri: str = None,
                 form: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 preflabel: LanguageMap = None,
                 inscheme: set = None
                 ) -> None:
        self.inscheme = inscheme
        super().__init__(uri, form, context, url, preflabel)


class ConceptScheme(Item):
    """ http://gbv.github.io/jskos/jskos.html#concept-schemes """

    def __init__(self,
                 uri: str = None,
                 form: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 preflabel: LanguageMap = None,
                 concepts: Set[Concept] = None
                 ) -> None:
        self.concepts = concepts
        super().__init__(uri, form, context, url, preflabel)
