""" jskos.py

JSKOS classes. Built based on  https://gbv.github.io/jskos/context.json """

from __future__ import annotations
from typing import Optional, Set, List


class _LanguageMap:
    """ http://gbv.github.io/jskos/jskos.html#language-map """

    def __init__(self, _mapping: dict) -> None:
        self._mapping = _mapping

    def add(self, label: str, language: str):
        """ Add a value for a language"""

        # TODO: this is the wrong way round! Should be language: label
        self._mapping.update({label: language})

    def get_value(self, language: str) -> Optional[str]:
        """ Get the value of a language if any """

        return self._mapping.get(language)


class _Resource:
    """ http://gbv.github.io/jskos/jskos.html#resource """

    def __init__(self,
                 uri: str = None,
                 type_: Set[str] = None,
                 context: str = None
                 ) -> None:
        self.uri = uri
        self.type_ = type_
        if context is None:
            self.context = "https://gbv.github.io/jskos/context.json"


class _Item(_Resource):
    """ http://gbv.github.io/jskos/jskos.html#item """

    def __init__(self,
                 uri: str = None,
                 type_: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 pref_label: _LanguageMap = None
                 ) -> None:
        if url is None:
            self.url = uri
        self.pref_label = pref_label
        super().__init__(uri, type_, context)


class _Concept(_Item):
    """ http://gbv.github.io/jskos/jskos.html#concept """

    def __init__(self,
                 uri: str = None,
                 type_: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 pref_label: _LanguageMap = None,
                 inscheme: Set[_ConceptScheme, str] = None
                 ) -> None:
        self.inscheme = inscheme
        super().__init__(uri, type_, context, url, pref_label)


class _ConceptScheme(_Item):
    """ http://gbv.github.io/jskos/jskos.html#concept-schemes """

    def __init__(self,
                 uri: str = None,
                 type_: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 pref_label: _LanguageMap = None,
                 concepts: List[_Concept] = None
                 ) -> None:
        if concepts is None:
            self.concepts = []
        super().__init__(uri, type_, context, url, pref_label)


class _ConceptBundle:
    """ https://gbv.github.io/jskos/jskos.html#concept-bundles

    :param member_set: concepts in this bundle (unordered)
    """

    def __init__(self,
                 member_set: Set[_Concept]
                 ) -> None:
        self.member_set = member_set


class _ConceptMapping(_Item):
    """ https://gbv.github.io/jskos/jskos.html#concept-mappings

    :param from_:
    :param to:
    :param from_scheme:
    :param to_scheme:
    """

    def __init__(self,
                 from_: _ConceptBundle,
                 to: _ConceptBundle,
                 from_scheme: _ConceptScheme = None,
                 to_scheme: _ConceptScheme = None,
                 uri: str = None,
                 type_: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 pref_label: _LanguageMap = None
                 ) -> None:
        self.from_ = from_
        self.to = to
        self.from_scheme = from_scheme
        self.to_scheme = to_scheme
        super().__init__(uri, type_, context, url, pref_label)


class _Concordance(_Item):
    """ https://gbv.github.io/jskos/jskos.html#concordances

    :param from_scheme:
    :param to_scheme:
    """

    def __init__(self,
                 from_scheme: _ConceptScheme,
                 to_scheme: _ConceptScheme,
                 mappings: Set[_ConceptMapping] = None,
                 uri: str = None,
                 type_: Set[str] = None,
                 context: str = None,
                 url: str = None,
                 pref_label: _LanguageMap = None
                 ) -> None:
        self.from_scheme = from_scheme
        self.to_scheme = to_scheme
        self.mappings = mappings
        super().__init__(uri, type_, context, url, pref_label)


class _TestRessource:
    """ http://gbv.github.io/jskos/jskos.html#resource

    :param context: bla
    """

    def __init__(self, **optional_fields):
        for key, value in optional_fields:
            self.key = value