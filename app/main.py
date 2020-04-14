""" main.py

Main module. Outline:
MODULE 1: read input data from local file
MODULE 2: send request to FAST
MODULE 3: analyse result
MODULE 4: output result as x """

# TODO: add documentation with sphinx

from __future__ import annotations
from typing import List, Optional, Dict, Union

from utility import Utility

import Levenshtein
import requests
import urllib.parse

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
                 _response: Union[Dict, requests.models.Response] = None) -> None:
        self.searchword = searchword
        self.maxsearchtime = maxsearchtime
        self.duplicates = duplicates
        if disabled is None:
            self.disabled = ["Research-Vocabularies-Australia", "Loterre"]
        self._response = _response

    def send(self) -> None:
        """ Send query as HTTP request to BARTOC FAST API """

        payload = self.get_payload()
        self._response = requests.get(url=FAST_API, params=payload)

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

    def get_response(self, verbose: int = 0) -> Dict:
        """ Return the query response """

        # fetch response if not available:
        if self._response is None:
            self.send()
            if verbose == 1:
                print(self._response.text)
            return self._response.json()

        # response is cached:
        elif self._response is requests.models.Response:
            return self._response.json()

        # response is preloaded:
        else:
            return self._response

    def get_searchword(self):
        """ Return the query searchword """

        return self.searchword

    def update_sources(self, store: Store) -> None:
        """ Update score vectors of sources based on query response """

        # extract results from response:
        response = self.get_response()
        results = response.get("results")

        if results is None:
            return None

        for result in results:
            # get source:
            name = result.get("source")
            source = store.get_source(name)
            # update score vector:
            searchword = self.get_searchword()
            source.score_vector.update_distance_score(searchword, result)

    @classmethod
    def make_query_from_json(cls, json_object: Dict) -> Optional[Query]:
        """ Load query object from preloaded query response """

        # extract query parameters from json object:
        context = json_object.get("@context")
        url = context.get("results").get("@id")
        parsed_url = urllib.parse.urlparse(url)
        parsed_query = (urllib.parse.parse_qs(parsed_url.query))

        # make query object from instantiated parameters and json object:
        try:
            searchword = parsed_query.get("searchword")[0]
            maxsearchtime = parsed_query.get("maxsearchtime")[0]
            duplicates = parsed_query.get("duplicates")[0]
            if duplicates == "on":
                duplicates = True
            else:
                duplicates = False
            disabled = parsed_query.get("disabled")
            query = Query(searchword, int(maxsearchtime), duplicates, disabled, _response=json_object)
        except IndexError:
            return None

        return query


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
        """ Use name to get source from store. """

        for source in self._sources:
            if name == source.name:
                return source

        return None

    def preload(self, maximum: int = 100000, minimum: int = 0) -> None:
        """ Preload all query responses for the concept scheme in the store. """

        counter = 0

        for concept in self.scheme.concepts:

            if counter > maximum:  # debug
                break
            elif counter < minimum:
                counter += 1
                continue

            searchword = concept.preflabel.get_value("en")
            query = Query(searchword)
            response = query.get_response()
            Utility.save_json(response, counter)
            counter += 1

        print(f"{minimum + 1} query responses preloaded")

    def fetch_and_update(self, remote: bool = True, maximum: int = 5, verbose: bool = False) -> None:
        """ Fetch query responses and update sources. """

        counter = 0

        # fetch from preload:
        if remote is False:

            while True:

                if counter > maximum:  # debug
                    break

                try:
                    json_object = Utility.load_json(counter)
                    query = Query.make_query_from_json(json_object)
                    query.update_sources(self)
                    counter += 1

                except FileNotFoundError:
                    break

        # fetch from remote:
        else:
            for concept in self.scheme.concepts:

                if counter > maximum:  # debug
                    break

                searchword = concept.preflabel.get_value("en")  # TODO: generalize this

                if verbose is True:
                    print(f"Concept being fetched is {searchword}")

                query = Query(searchword)
                query.update_sources(self)
                counter += 1


class ScoreVector:
    """ A vector for distance scores. """

    def __init__(self,
                 distance: List[int] = None) -> None:
        if distance is None:
            self._distance = []
        else:
            self._distance = distance

    def make_distance_score(self, searchword: str, result: dict) -> Optional[int]:
        """ Make the distance score for a result which is the minimum Levenshtein distance over all labels """

        scores = []
        labels = ["prefLabel", "altLabel", "hiddenLabel", "definition"]

        for label in labels:
            label_value = result.get(label)
            if label_value is None:
                continue
            distance = Levenshtein.distance(searchword, label_value)
            scores.append(distance)

        try:
            return min(scores)
        except ValueError:
            return None

    def update_distance_score(self, searchword: str, result: dict) -> None:
        """ Update the distance vector with the distance score from searchword and result """

        distance_score = self.make_distance_score(searchword, result)
        if distance_score is None:
            pass
        else:
            self._distance.append(distance_score)

    def get_distance_score(self) -> Optional[str]:

        if len(self._distance) is 0:
            return None

        score_sum = sum(self._distance)
        score_average = score_sum/len(self._distance)
        score_coverage = len(self._distance)

        # TODO: implement option of only taking best result per concept per source (and not multiple)

        return f"sum: {score_sum}, average score: {round(score_average, 2)}, coverage: {score_coverage}"


class Source:
    """ A BARTOC FAST source. """

    def __init__(self,
                 name: str,
                 score_vector: ScoreVector = None) -> None:
        self.name = name
        if score_vector is None:
            self.score_vector = ScoreVector()


def main(preload: bool = False, remote: bool = True) -> None:
    """ Main function. """

    store = Store("owcm_index.xlsx")
    print(f"{len(store.scheme.concepts)} concepts in {store.scheme}")

    if preload is True:
        store.preload(minimum=2337)

    store.fetch_and_update(remote, maximum=2000, verbose=True)

    # TODO: do some magic on score vectors (precision, recall)
    for source in store._sources:
        #print(f"{source.name}'s score vector: {source.score_vector._distance}")
        print(f"{source.name}'s score: {source.score_vector.get_distance_score()}")

main(preload=False, remote=False)
