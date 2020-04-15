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
            searchword = self.searchword
            source.levenshtein_vector.update_score(searchword, result)

    @classmethod
    def make_query_from_json(cls, json_object: Dict) -> Optional[Query]:
        """ Return query object initialized from preloaded query response """

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
        """ Return initialized sources from constant. """

        sources = []
        for name in FAST_SOURCES:
            sources.append(Source(name))  # TODO: add uri, etc.

        return sources

    def get_source(self, name: str) -> Optional[Source]:
        """ Return source by name. """

        for source in self._sources:
            if name == source.name:
                return source

        return None

    def preload(self, maximum: int = 100000, minimum: int = 0) -> None:
        """ Save to HD the concept scheme's query responses. """

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

        if verbose is True:
            print(f"Querying BARTOC FAST...")

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

        if verbose is True:
            print("Responses collected.")

    def update_rankings(self, sensitivity: int, verbose: bool = False):
        """ Update the sources' rankings. """

        if verbose is True:
            print("Updating source rankings...")

        for source in self._sources:
            source.update_ranking(self, sensitivity)

        if verbose is True:
            print("Source rankings updated.")

    def make_suggestion(self, score_type: str = "score_average"): # TODO: rather print_suggestion(...)
        """ Return sources from best to worst base on score type. """

        # fix sorting direction:
        high_to_low = False
        if score_type is "recall":
            high_to_low = True

        # sort sources by score type:
        contenders = []
        disqualified = []
        for source in self._sources:
            if getattr(source.ranking, score_type) is None:
                disqualified.append(source)
            else:
                contenders.append(source)
        contenders.sort(key=lambda x: getattr(x.ranking, score_type), reverse=high_to_low)

        # print:
        for source in contenders:
            print(f"{source.name} {source.ranking.str()}")
        for source in disqualified:
            print(f"{source.name} {source.ranking.str()}")


class Score:
    """ A score. """

    def __init__(self,
                 value: int = None,
                 searchword: str = None) -> None:
        self.value = value
        self.searchword = searchword


class Vector:
    """ A vector of scores. """

    def __init__(self,
                 vector: List[Score] = None) -> None:
        if vector is None:
            self._vector = []
        else:
            self._vector = vector

    def get_vector(self) -> Optional[List[Score]]:
        """ Get the vector if any. """

        if len(self._vector) is 0:
            return None
        else:
            return self._vector


class LevenshteinVector(Vector):
    """ A vector of Levenshtein distance scores """

    def make_score(self, searchword: str, result: dict) -> Optional[Score]:
        """ Make the Levenshtein score for a result.
        The Levenshtein score is the minimum Levenshtein distance over all labels. """

        scores = []
        labels = ["prefLabel", "altLabel", "hiddenLabel", "definition"]

        for label in labels:
            label_value = result.get(label)
            if label_value is None:
                continue
            distance = Levenshtein.distance(searchword, label_value)
            scores.append(distance)

        # catch malformed (= empty labels) results:
        try:
            min(scores)
        except ValueError:
            return None

        return Score(min(scores), searchword)

    def update_score(self, searchword: str, result: dict) -> None:
        """ Update the Levenshtein vector with the Levenshtein score from searchword and result """

        score = self.make_score(searchword, result)
        if score is None:
            pass
        else:
            self._vector.append(score)


class Ranking:
    """ The ranking of a source given its best Levenshtein vector. """

    def __init__(self,
                 score_sum: int = None,
                 score_average: float = None,
                 score_coverage: int = None,
                 recall: float = None) -> None:
        self.score_sum = score_sum
        self.score_average = score_average
        self.score_coverage = score_coverage
        self.recall = recall

    def str(self) -> str:
        return f"Sum: {self.score_sum} / Average: {self.score_average} / Coverage: {self.score_coverage} / Recall: {self.recall}"


class Analysis:
    """ A collection of methods for analyzing score vectors. """

    @classmethod
    def make_score_sum(cls, vector: LevenshteinVector) -> Optional[int]:
        """ Return the sum of all scores in the vector.
        The lower the sum the better. """

        try:
            return sum(score.value for score in vector.get_vector())
        except (TypeError, AttributeError):
            return None

    @classmethod
    def make_score_average(cls, vector: LevenshteinVector) -> Optional[float]:
        """ Return the vector's average score.
         The lower the average the better. """

        score_sum = cls.make_score_sum(vector)
        if score_sum is None:
            return None
        else:
            return round(score_sum/len(vector.get_vector()), 2)

    @classmethod
    def make_score_coverage(cls, vector: LevenshteinVector) -> Optional[int]:
        """ Return the number of scores in the vector. """

        try:
            return len(vector.get_vector())
        except (TypeError, AttributeError):
            return None

    @classmethod
    def make_best_vector(cls, vector: LevenshteinVector, sensitivity: int) -> Optional[LevenshteinVector]:
        """ Return the best vector of a vector.
         The best vector has the best score for each searchword. """

        # collect all unique searchwords in vector:
        initial_vector = vector.get_vector()
        if initial_vector is None:
            return None
        else:
            searchwords = set(score.searchword for score in initial_vector)

        # choose best score for each seachword:
        best_vector = []
        for word in searchwords:
            scores = [score for score in initial_vector if score.searchword == word]
            best_score = sorted(scores, key=lambda x: x.value)[0]
            # check sensitivity:
            if best_score.value <= sensitivity:
                best_vector.append(best_score)

        return LevenshteinVector(best_vector)

    @classmethod
    def make_recall(cls, relevant: int, retrieved: int) -> Optional[float]:
        """ Return recall.
         See https://en.wikipedia.org/wiki/Precision_and_recall#Recall """

        try:
            return retrieved/relevant
        except (TypeError, AttributeError):
            return None


class Source:
    """ A BARTOC FAST source. """

    def __init__(self,
                 name: str,
                 levenshtein_vector: LevenshteinVector = None,
                 ranking: Ranking = None) -> None:
        self.name = name
        if levenshtein_vector is None:
            self.levenshtein_vector = LevenshteinVector()
        self.ranking = ranking

    def update_ranking(self, store: Store, sensitivity: int):
        """ Update the sources ranking. """

        best_vector = Analysis.make_best_vector(self.levenshtein_vector, sensitivity)

        self.ranking = Ranking()
        self.ranking.score_sum = Analysis.make_score_sum(best_vector)
        self.ranking.score_average = Analysis.make_score_average(best_vector)
        self.ranking.score_coverage = Analysis.make_score_coverage(best_vector)
        self.ranking.recall = Analysis.make_recall(len(store.scheme.concepts), self.ranking.score_coverage)


def main(preload: bool = False, remote: bool = True, sensitivity: int = 5) -> None:
    """ Main function. """

    store = Store("owcm_index.xlsx")
    print(f"{len(store.scheme.concepts)} concepts in {store.scheme}")

    if preload is True:
        store.preload(minimum=5000)

    store.fetch_and_update(remote, maximum=5000, verbose=True)

    store.update_rankings(sensitivity=sensitivity, verbose=True)

    print("Calculating suggestions...")
    store.make_suggestion("recall")


main(preload=False, remote=False, sensitivity=1)


# TODO: have some metric that has a cutoff for scores (e.g., 3) in order to calculate recall et al.
# perhaps call it sensitivity and use it as argument

# TODO: implement multilanguage result parser

# TODO: for maximim=2000:
# FORTH's score: sum: 156, best sum: 67 // average: 1.15, best average: 1.46 // coverage: 136, best coverage: 46
# here best average is higher than average?!
