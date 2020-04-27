""" main.py  """

# TODO: package: https://packaging.python.org/tutorials/packaging-projects/
# TODO: sphinx documentation: https://packaging.python.org/tutorials/creating-documentation/

from __future__ import annotations
from typing import List, Optional, Dict, Union
from time import sleep

from utility import Utility

import Levenshtein
import requests
import urllib.parse

FAST_API = "https://bartoc-fast.ub.unibas.ch/bartocfast/api?"


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

    def _send(self) -> None:
        """ Send query as HTTP request to BARTOC FAST API.

         Response is saved in _response."""

        payload = self.get_payload()
        try:
            self._response = requests.get(url=FAST_API, params=payload)
        except requests.exceptions.ConnectionError:
            print(f"requests.exceptions.ConnectionError! Trying again in 5 seconds...")
            sleep(5)
            self._send()

    def _update_sources(self, store: Store) -> None:
        """ Update score vectors of sources based on query response. """

        # extract results from response:
        response = self.get_response()
        results = response.get("results")

        if results is None:
            return None

        for result in results:
            # get source, add if new:
            name = self._result2name(result)
            source = store.get_source(name)
            if source is None:
                source = Source(name)
                store.add_source(source)
            # update source's score vector:
            searchword = self.searchword
            source.levenshtein_vector.update_score(searchword, result)

    def _result2name(self, result: Dict) -> str:
        """ Return source name based on result. """

        # TODO: add all relevant sources
        # define (categories of) aggregated sources:
        agg_1 = ["bartoc-skosmos.unibas.ch",
                 "data.ub.uio.no",
                 "vocab.getty.edu"]
        agg_2 = ["isl.ics.forth.gr,"
                 "linkeddata.ge.imati.cnr.it",
                 "www.yso.fi"]
        agg_5 = ["vocabs.ands.org.au"]

        uri = result.get("uri")
        parsed_uri = urllib.parse.urlparse(uri)

        # only aggregated sources need splitting:
        if parsed_uri.netloc in agg_1:
            return self._uri2name(parsed_uri, n=1)
        elif parsed_uri.netloc in agg_2:
            return self._uri2name(parsed_uri, n=2)
        elif parsed_uri.netloc in agg_5:
            return self._uri2name(parsed_uri, n=5)
        else:
            return parsed_uri.netloc

    def _uri2name(self, parsed_uri: urllib.parse.ParseResult, n: int = 1) -> str:
        """ Return source name based on parsed URI.

         n is the number of identifying components on the path."""

        path = parsed_uri.path
        components = path.split("/")
        name = parsed_uri.netloc

        i = 1
        while True:
            if i > n:
                break
            else:
                identifier = components[i]
                name = name + f"/{identifier}"
                i += 1

        return name

    def get_payload(self) -> Dict:
        """ Return the payload (parameters passed in URL) of the query. """

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
        """ Return the query response. """

        # fetch response if not available:
        if self._response is None:
            self._send()
            if verbose == 1:
                print(self._response.text)
            return self._response.json()

        # response is cached:
        elif self._response is requests.models.Response:
            return self._response.json()

        # response is preloaded:
        else:
            return self._response

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
            self._sources = []

    def add_source(self, source: Source) -> None:
        """ Add a source to the store. """

        # TODO: check for duplicate source before adding
        self._sources.append(source)

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
                    query._update_sources(self)
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
                query._update_sources(self)
                counter += 1

        if verbose is True:
            print("Responses collected.")

    def update_rankings(self, sensitivity: int, verbose: bool = False):
        """ Update the sources' rankings. """

        if verbose is True:
            print("Updating source rankings...")

        for source in self._sources:
            source.update_ranking(self, sensitivity, verbose)

        if verbose is True:
            print("Source rankings updated.")

    def make_suggestion(self, sensitivity: int, score_type: str, verbose: bool = False) -> Suggestion:
        """ Return sources from best to worst base on score type. """

        if verbose is True:
            print("Calculating suggestions...")

        # determine sorting direction:
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

        suggestion = Suggestion(contenders, sensitivity, score_type)

        if verbose is True:
            print("Suggestions calculated.")
            for source in suggestion.sources:
                print(f"{source.name} {score_type}: {getattr(source.ranking, score_type)}")

        return suggestion


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
            distances = []
            # check if label is multilingual:
            for language_value in label_value.split(";"):
                # clean searchword and language_value before measuring distance:
                distances.append(Levenshtein.distance(searchword.lower(), language_value.lower()))
            scores.append(min(distances))

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
            return round(score_sum / len(vector.get_vector()), 2)

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
            return retrieved / relevant
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

    def update_ranking(self, store: Store, sensitivity: int, verbose: bool = False):
        """ Update the sources ranking. """

        if verbose is True:
            print(f"Updating {self.name}...")

        best_vector = Analysis.make_best_vector(self.levenshtein_vector, sensitivity)

        self.ranking = Ranking()
        self.ranking.score_sum = Analysis.make_score_sum(best_vector)
        self.ranking.score_average = Analysis.make_score_average(best_vector)
        self.ranking.score_coverage = Analysis.make_score_coverage(best_vector)
        self.ranking.recall = Analysis.make_recall(len(store.scheme.concepts), self.ranking.score_coverage)

        if verbose is True:
            print(f"{self.name} updated.")


class Suggestion:
    """ A suggestion. """

    def __init__(self,
                 sources: List[Source],
                 sensitivity: int,
                 score_type: str) -> None:
        self.sources = sources
        self.sensitivity = sensitivity
        self.score_type = score_type


def main(preload: bool = False, remote: bool = True, sensitivity: int = 1, score_type: str = "recall") -> None:
    """ Main function. """

    store = Store("owcm_index.xlsx")
    print(f"{len(store.scheme.concepts)} concepts in {store.scheme}")

    if preload is True:
        store.preload(minimum=10173)

    store.fetch_and_update(remote, maximum=10173, verbose=True)

    store.update_rankings(sensitivity=sensitivity, verbose=True)

    store.make_suggestion(sensitivity=sensitivity, score_type=score_type, verbose=True)


#main(preload=False, remote=False, sensitivity=1)

# TODO: implement measure for noise
# TODO: refactor all class methods into public and private
