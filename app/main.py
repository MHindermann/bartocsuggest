""" main.py

Main module. Outline:
MODULE 1: read input data from local file
MODULE 2: send request to FAST
MODULE 3: analyse result
MODULE 4: output result as x """

from __future__ import annotations
from typing import List, Optional

from utility import Utility
from jskos import ConceptScheme

import Levenshtein
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
        self._response = _response  # TODO: save/cache response in DB/in RAM/on HD for further analysis

    def get_payload(self):
        """ Return the payload (parameters passed in URL) of the query """

        if self.duplicates is True:
            duplicates = "on"
        else:
            duplicates = "off"

        payload = {"searchword": self.searchword,
                   "maxsearchtime": self.maxsearchtime,
                   "duplicates": duplicates,
                   "disabled": self.disabled}

        return payload

    def send(self) -> None:
        """ Send query as HTTP request to BARTOC FAST API """

        payload = self.get_payload()
        self._response = requests.get(url=FAST_API, params=payload)

    def get_response(self, verbose: int = 0) -> requests.models.Response:
        """ Return the query response """

        if self._response is None:
            self.send()
            if verbose == 1:
                print(self._response.text)

        return self._response

    def get_searchword(self):
        """ Return the query searchword """

        return self.searchword


class Store:
    """ Stores everything! """

    def __init__(self,
                 filename: str,
                 sources: List[Source] = None) -> None:
        self.scheme = Utility.load_file(filename)
        if sources is None:
            self._sources = self.make_sources()

    def make_sources(self):
        """ Populate the store with sources """

        sources = []
        for name in FAST_SOURCES:
            sources.append(Source(name))  # TODO: add uri, etc.

        return sources

    def get_source(self, name: str) -> Optional[Source]:
        """ Use name to get source from store """

        for source in self._sources:
            if name == source.name:
                return source

        return None

    def preload(self, maximum: int = 100000):
        """ Preload all query responses for a concept scheme """

        counter = 0

        for concept in self.scheme.concepts:

            if counter > maximum:  # debug
                break

            searchword = concept.preflabel.get_value("en")
            query = Query(searchword)
            response = query.get_response()
            Utility.save_json(response.json(), counter)
            counter += 1



def analyze(store: Store, query: Query) -> None:
    """ Analyze a query response by assigning scores """

    # extract results from response:
    response = query.get_response().json()
    results = response.get("results")

    if results is None:
        return None

    for result in results:
        # get source:
        name = result.get("source")
        source = store.get_source(name)
        # update score vector:
        searchword = query.get_searchword()
        source.score_vector.update_distance(searchword, result)


class ScoreVector:
    """ A vector for distance scores """

    def __init__(self,
                 distance: List[int] = None) -> None:
        if distance is None:
            self._distance = []

    @classmethod
    def make_distance_score(cls, searchword: str, result: dict) -> int:
        """ Make the distance score for a result which is the minimum Levenshtein distance over all labels """

        scores = []
        labels = ["prefLabel", "altLabel", "hiddenLabel", "definition"]

        for label in labels:
            label_value = result.get(label)
            if label_value is None:
                continue
            distance = Levenshtein.distance(searchword, label_value)
            scores.append(distance)

        return min(scores)

    def update_distance(self, searchword: str, result: dict) -> None:
        """ Update the distance vector with the distance score from searchword and result """

        distance_score = self.make_distance_score(searchword, result)
        self._distance.append(distance_score)


class Source:
    """ A BARTOC FAST source """

    def __init__(self,
                 name: str,
                 score_vector: ScoreVector = None) -> None:
        self.name = name
        if score_vector is None:
            self.score_vector = ScoreVector()


def collect(store: Store, scheme: ConceptScheme, maximum: int = 5, verbose: int = 0) -> None:
    """ Collect results for concepts in scheme """

    cutoff = 0
    for concept in scheme.concepts:

        if cutoff > maximum:  # debug
            break

        searchword = concept.preflabel.get_value("en")  # TODO: generalize this
        if verbose == 1:
            print(f"Searchword being collected is {searchword}")

        query = Query(searchword)
        analyze(store, query)

        cutoff += 1

    for source in store._sources:
        print(f"{source.name}'s score vector: {source.score_vector._distance}")

def run():
    """ Run the app """

    store = Store("owcm_index.xlsx")

    print(f"{len(store.scheme.concepts)} concepts in {store.scheme}")
    #collect(store, store.scheme, verbose=1)
    store.preload()

run()