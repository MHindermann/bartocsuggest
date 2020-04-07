""" main.py

Main module. Outline:
MODULE 1: read input data from local file
MODULE 2: send request to FAST
MODULE 3: analyse result
MODULE 4: output result as x """

from __future__ import annotations
from typing import List

from utility import Utility
from jskos import ConceptScheme

import requests
import json

""" BARTOC FAST query module

This module sends queries to BARTOC FAST API and retrieves the results.
"""

FAST_API = "https://bartoc-fast.ub.unibas.ch/bartocfast/api?"

FAST_SOURCES = ["LuSTRE",
                "GettyULAN",
                "GettyAAT",
                "GettyTGN",
                "AgroVoc",
                "Bartoc",
                "data.ub.uio.no",
                "Finto",
                "Legilux",
                "MIMO",
                "UNESCO",
                "OZCAR-Theia",
                "GACS",
                "51.15.194.251",
                "UAAV",
                "HTW-Chur",
                "FORTH",
                "Irstea",
                "DemoVoc",
                "ScoLOMFR",
                "lobid-gnd",
                "Research-Vocabularies-Australia",
                "Loterre"]


class Query:
    """ A BARTOC FAST query """

    def __init__(self,
                 searchword: str,
                 maxsearchtime: int = 5,
                 duplicates: bool = True,
                 disabled: List[str] = None,
                 _response: requests.models.Response = None) -> None:
        self.searchword = searchword
        self.maxsearchtime = maxsearchtime
        self.duplicates = duplicates
        if disabled is None:
            self.disabled = ["Research-Vocabularies-Australia", "Loterre"]
        self._response = _response

    def send(self) -> None:
        """ Send query as HTTP request to BARTOC FAST API """

        payload = {"searchword": self.searchword,
                   "maxsearchtime": self.maxsearchtime,
                   "duplicates": "on",  # TODO: transform parameter into payload
                   "disabled": self.disabled}

        self._response = requests.get(url=FAST_API, params=payload)

    def get_response(self, verbose: str = 0) -> requests.models.Response:
        """ Return the query response """

        if self._response is None:
            self.send()
            if verbose == 1:
                print(self._response.text)

        return self._response


class Store:
    """ Stores everything! """

    def __init__(self,
                 filename: str,
                 sources: List[Source] = None) -> None:
        self.scheme = Utility.load_file(filename)
        if sources is None:
            self.sources = self.make_sources()

    def make_sources(self):
        """ Populate the store with sources """

        sources = []
        for name in FAST_SOURCES:
            sources.append(Source(name))  # TODO: add uri, etc.

        return sources

    def update_score(response: requests.models.Response) -> None:
        """ bla """

        print(response.json())


class Score:
    """ Bla """

    def __init__(self,
                 preflabel: int = None,
                 altlabel: int = None,
                 hiddenlabel: int = None,
                 definition: int = None) -> None:
        self.preflabel = preflabel
        self.altlabel = altlabel
        self.hiddenlabel = hiddenlabel
        self.definition = definition

        def compute(input: str, output: str) -> None:
            """ bla """
            pass


class Source:
    """ Bla """

    def __init__(self,
                 name: str,
                 score: Score = None) -> None:
        self.name = name
        self.score = score

    def update_score(self):
        pass



def collect(scheme: ConceptScheme, maximum: int = 10) -> None:
    """ Collect results for concepts in scheme """

    cutoff = 0
    for concept in scheme.concepts:

        if cutoff > maximum:  # debug:
            break

        searchword = concept.preflabel.get_value("en")  # TODO: generalize this
        print(searchword)

        query = Query(searchword)
        response = query.get_response()

        cutoff += 1

def analyze(result: requests.models.Response):
    """ """

    pass


# TODO: add analyse function for collected results


def run():
    """ Run the app """

    store = Store("owcm_index.xlsx")

    print(f"{len(store.scheme.concepts)} concepts in {store.scheme}")
    collect(store.scheme)

run()