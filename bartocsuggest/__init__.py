"""
bartocsuggest is a Python module that suggests vocabularies given a list of words based on the BARTOC FAST API
(https://bartoc-fast.ub.unibas.ch/bartocfast/api).

Documentation available at: https://bartocsuggest.readthedocs.io/en/latest/

Codebase available at: https://github.com/MHindermann/bartocsuggest
"""

from __future__ import annotations
from typing import List, Optional, Dict, Union, Tuple
from time import sleep
from os import path
from annif_client import AnnifClient

from .utility import _Utility
from .jskos import _ConceptScheme

import Levenshtein
import requests
import urllib.parse

FAST_API = "https://bartoc-fast.ub.unibas.ch/bartocfast/api"


class _Query:
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

    def update_sources(self, store: Session) -> None:
        """ Update score vectors of sources based on query response. """

        # extract results from response:
        response = self.get_response()
        results = response.get("results")

        if results is None:
            return None

        for result in results:
            # get source, add if new:
            name = self._result2name(result)
            source = store._get_source(name)
            if source is None:
                source = _Source(name)
                store._add_source(source)
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

        :param parsed_uri: the path
        :param n: the number of identifying components on the path
        """

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
    def make_query_from_json(cls, json_object: Dict) -> Optional[_Query]:
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
            query = _Query(searchword, int(maxsearchtime), duplicates, disabled, _response=json_object)
        except IndexError:
            return None

        return query


class ScoreType:
    """ A score type.

    All score types are relative to a specific vocabulary and a list of words.
    There are four score type classes: :class:`bartocsuggest.Recall`, :class:`bartocsuggest.Average`,
    :class:`bartocsuggest.Coverage`, :class:`bartocsuggest.Sum`.
    Use the help method on these classes for more information.
    """

    pass
    # TODO: implement measure for noise


class Recall(ScoreType):
    """ The number of words over a vocabulary's coverage.

    The lower the better (minimum is 1). See https://en.wikipedia.org/wiki/Precision_and_recall#Recall.

    For example, for words [a,b,c] and coverage 2, recall is len(words)/coverage = len([a,b,c])/2 = 1.5.
    """

    @classmethod
    def __str__(cls) -> str:
        return "recall"


class Average(ScoreType):
    """ The average over a vocabulary's match scores.

    The lower the the better (minimum is 0).
    The score of a match is defined by the Levenshtein distance between word and match.

    For example, for scores [1,1,4], the average is scores/len(scores) = (1+1+4)/3 = 2.
    """

    @classmethod
    def __str__(cls) -> str:
        return "score_average"


class Coverage(ScoreType):
    """ The number of a vocabulary's matches in the list of words.

    Note that this is dependent on the sensitivity parameter of :meth:`bartocsuggest.Session.suggest`.

    For example, for words [a,b,c] and vocabulary matches a,c, the coverage is a,c in [a,b,c] = 2.
    """

    @classmethod
    def __str__(cls) -> str:
        return "score_coverage"


class Sum(ScoreType):
    """ The sum over a vocabulary's match scores.

    The lower the average the better (minimum is 0).
    The score of a match is defined by the Levenshtein distance between word and match.

    For example, for scores [1,1,4], the sum is (1+1+4) = 6.
    """

    @classmethod
    def __str__(cls) -> str:
        return "score_sum"


class Session:
    """ Vocabulary suggestion session using the BARTOC FAST API.

    :param words: input words (list of strings or path to XLSX file)
    :param preload_folder: path to preload folder, defaults to None
    """

    def __init__(self,
                 words: Union[List[str], str, _ConceptScheme],
                 preload_folder: str = None) -> None:
        self._scheme = self._set_input(words)
        self._preload_folder = preload_folder
        self._sources = []

    def _set_input(self, words: Union[list, str, _ConceptScheme]) -> _ConceptScheme:
        """ Set words as Concept Scheme.

        The input words are transformed into a JSKOS Concept Scheme for internal representation.

        :param words: either a list, or a filename (MUST use complete filepath).
        :param **kawrgs: forward compatibility for subclasses.
        """

        if type(words) is list:
            scheme = _Utility.list2jskos(words)
        elif type(words) is _ConceptScheme:
            scheme = words
        else:
            scheme = _Utility.load_file(words)

        print(f"{words} loaded successfully, {len(scheme.concepts)} words detected.")
        return scheme

    def _add_source(self, source: _Source) -> None:
        """ Add a source to the store. """

        # TODO: check for duplicate source before adding
        self._sources.append(source)

    def _get_source(self, name: str) -> Optional[_Source]:
        """ Return source by name. """

        for source in self._sources:
            if name == source.name:
                return source

        return None

    def _fetch_and_update(self, remote: bool = True, maximum: int = 100000, verbose: bool = False) -> None:
        """ Fetch query responses and update sources.

        :param remote: toggle fetching responses from BARTOC FAST or preload folder.
        :param maximum: the maximum number of responses fetched.
        :param verbose: toggle status updates along the way.
        """

        if verbose is True:
            print(f"Querying BARTOC FAST...")

        counter = 0

        # fetch from preload:
        if remote is False:
            while True:
                if counter > maximum:  # debug
                    break
                try:
                    json_object = _Utility.load_json(self._preload_folder, counter)
                    query = _Query.make_query_from_json(json_object)
                    query.update_sources(self)
                    counter += 1
                except FileNotFoundError:
                    break

        # fetch from remote:
        else:
            for concept in self._scheme.concepts:
                if counter > maximum:  # debug
                    break
                # TODO: generalize this for multi-language support
                searchword = concept.preflabel.get_value("en")
                if verbose is True:
                    print(f"Word being fetched is {searchword}")
                query = _Query(searchword)
                query.update_sources(self)
                counter += 1

        if verbose is True:
            print("Responses collected.")

    def _update_rankings(self, sensitivity: int, verbose: bool = False):
        """ Update the sources' rankings. """

        if verbose is True:
            print("Updating source rankings...")

        for source in self._sources:
            source.update_ranking(self, sensitivity, verbose)

        if verbose is True:
            print("Source rankings updated.")

    def _make_suggestion(self, sensitivity: int, score_type: ScoreType, verbose: bool = False) -> Suggestion:
        """ Return sources from best to worst base on score type. """

        if verbose is True:
            print("Calculating suggestions...")

        # determine sorting direction:
        high_to_low = False
        if score_type is Recall:
            high_to_low = True

        # sort sources by score type:
        contenders = []
        disqualified = []
        for source in self._sources:
            if getattr(source.ranking, score_type.__str__()) is None:
                disqualified.append(source)
            else:
                contenders.append(source)
        contenders.sort(key=lambda x: getattr(x.ranking, score_type.__str__()), reverse=high_to_low)

        suggestion = Suggestion(contenders, sensitivity, score_type)

        if verbose is True:
            print(f"Suggestions calculated.")
            suggestion.print()

        return suggestion

    def preload(self,
                max: int = 100000,
                min: int = 0,
                verbose: bool = False) -> None:
        """ Preload responses.

        For each word in :attr:`self.words`, a query is sent to the BARTOC FAST API.
        The response is saved to :attr:`self.preload_folder`. Use this method for batchwise handling of large (>100) :attr:`self.words`.

        :param max: stop with the max-th word in self.words, defaults to 100000
        :param min: start with min-th word in self.words, defaults to 0
        :param verbose: toggle running comment printed to console, defaults to False
        """

        if self._preload_folder is None:
            print("ERROR: No preload folder specified! Specify preload folder before calling Session.preload!")
            return None
        elif path.exists(self._preload_folder) is False:
            raise FileExistsError(self._preload_folder)

        counter = 0

        for concept in self._scheme.concepts:

            if counter > max:  # debug
                break
            elif counter < min:
                counter += 1
                continue

            searchword = concept.preflabel.get_value("en")
            if verbose is True:
                print(f"Preloading word number {counter} '{searchword}'...", end=" ")
            query = _Query(searchword)
            response = query.get_response()
            _Utility.save_json(response, self._preload_folder, counter)
            counter += 1
            if verbose is True:
                print(f"done.")

        if verbose is True:
            print(f"{(counter - min)} responses preloaded.")

    def suggest(self,
                remote: bool = True,
                sensitivity: int = 1,
                score_type: ScoreType = Recall,
                verbose: bool = False) -> Suggestion:
        """ Suggest vocabularies based on :attr:`self.words`.

        :param remote: toggle between remote BARTOC FAST querying and preload folder, defaults to True
        :param sensitivity: set the maximum allowed Levenshtein distance between word and result, defaults to 1
        :param score_type: set the score type on which the suggestion is based, defaults to :class:`bartocsuggest.Recall`
        :param verbose: toggle running comment printed to console, defaults to False
        """
        self._fetch_and_update(remote=remote, verbose=verbose)
        self._update_rankings(sensitivity=sensitivity, verbose=verbose)
        suggestion = self._make_suggestion(sensitivity=sensitivity, score_type=score_type, verbose=verbose)

        return suggestion


class AnnifSession(Session):
    """ bla
    see https://api.annif.org/v1/ui/#!/Automatic32subject32indexing/annif_rest_suggest
    """

    def __init__(self,
                 text: str,
                 project_id: str,
                 limit: int = None,
                 threshold: int = None,
                 preload_folder: str = None) -> None:
        self._scheme = self._set_input(text, project_id=project_id, limit=limit, threshold=threshold)
        self._preload_folder = preload_folder
        self._sources = []

    def _set_input(self, text: str, **kwargs) -> _ConceptScheme:
        """ Use words suggested by Annif on the basis of text to set JSKOS Concept Scheme.

        :param text: input text
        :param **kwargs: required or optional Annif parameters
        """

        annif = AnnifClient()
        annif_suggestion = annif.suggest(project_id=kwargs.get("project_id"),
                                         text=text,
                                         limit=kwargs.get("limit"),
                                         threshold=kwargs.get("threshold"))

        scheme = _Utility.annif2jskos(annif_suggestion, kwargs.get("project_id"))

        return scheme


class _Score:
    """ A score. """

    def __init__(self,
                 value: int = None,
                 searchword: str = None) -> None:
        self.value = value
        self.searchword = searchword


class _Vector:
    """ A vector of scores. """

    def __init__(self,
                 vector: List[_Score] = None) -> None:
        if vector is None:
            self._vector = []
        else:
            self._vector = vector

    def get_vector(self) -> Optional[List[_Score]]:
        """ Get the vector if any. """

        if len(self._vector) is 0:
            return None
        else:
            return self._vector


class _LevenshteinVector(_Vector):
    """ A vector of Levenshtein distance scores """

    def make_score(self, searchword: str, result: dict) -> Optional[_Score]:
        """ Make the Levenshtein score for a result.

        The Levenshtein score is the minimum Levenshtein distance over all labels.

        :param searchword: the word from which the distance is measured
        :param result: contains matches to which the distance is measured
        """

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

        return _Score(min(scores), searchword)

    def update_score(self, searchword: str, result: dict) -> None:
        """ Update the Levenshtein vector with the Levenshtein score from searchword and result. """

        score = self.make_score(searchword, result)
        if score is None:
            pass
        else:
            self._vector.append(score)


class _Ranking:
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


class _Analysis:
    # TODO: move classmethods to appropriate classes
    """ A collection of methods for analyzing score vectors. """

    @classmethod
    def make_score_sum(cls, vector: _LevenshteinVector) -> Optional[int]:
        """ Return the sum of all scores in the vector.
        The lower the sum the better. """

        try:
            return sum(score.value for score in vector.get_vector())
        except (TypeError, AttributeError):
            return None

    @classmethod
    def make_score_average(cls, vector: _LevenshteinVector) -> Optional[float]:
        """ Return the vector's average score.
         The lower the average the better. """

        score_sum = cls.make_score_sum(vector)
        if score_sum is None:
            return None
        else:
            return round(score_sum / len(vector.get_vector()), 2)

    @classmethod
    def make_score_coverage(cls, vector: _LevenshteinVector) -> Optional[int]:
        """ Return the number of scores in the vector. """

        try:
            return len(vector.get_vector())
        except (TypeError, AttributeError):
            return None

    @classmethod
    def make_best_vector(cls, vector: _LevenshteinVector, sensitivity: int) -> Optional[_LevenshteinVector]:
        """ Return the best vector of a vector.
         The best vector has the best score for each searchword. """

        # collect all unique searchwords in vector:
        initial_vector = vector.get_vector()
        if initial_vector is None:
            return None
        else:
            searchwords = set(score.searchword for score in initial_vector)

        # choose best (=lowest) score for each seachword:
        best_vector = []
        for word in searchwords:
            scores = [score for score in initial_vector if score.searchword == word]
            best_score = sorted(scores, key=lambda x: x.value)[0]
            # check sensitivity:
            if best_score.value <= sensitivity:
                best_vector.append(best_score)

        return _LevenshteinVector(best_vector)

    @classmethod
    def make_recall(cls, relevant: int, retrieved: int) -> Optional[float]:
        """ Return recall.
         See https://en.wikipedia.org/wiki/Precision_and_recall#Recall """

        try:
            return retrieved / relevant
        except (TypeError, AttributeError):
            return None


class _Source:
    """ A BARTOC FAST source. """

    def __init__(self,
                 name: str,
                 levenshtein_vector: _LevenshteinVector = None,
                 ranking: _Ranking = None) -> None:
        self.name = name
        if levenshtein_vector is None:
            self.levenshtein_vector = _LevenshteinVector()
        self.ranking = ranking

    def update_ranking(self, store: Session, sensitivity: int, verbose: bool = False):
        """ Update the sources ranking. """

        if verbose is True:
            print(f"Updating {self.name}...")

        best_vector = _Analysis.make_best_vector(self.levenshtein_vector, sensitivity)

        self.ranking = _Ranking()
        self.ranking.score_sum = _Analysis.make_score_sum(best_vector)
        self.ranking.score_average = _Analysis.make_score_average(best_vector)
        self.ranking.score_coverage = _Analysis.make_score_coverage(best_vector)
        self.ranking.recall = _Analysis.make_recall(len(store._scheme.concepts), self.ranking.score_coverage)

        if verbose is True:
            print(f"{self.name} updated.")


class Suggestion:
    """ A suggestion of vocabularies. """

    def __init__(self,
                 _vocabularies: List[_Source],
                 _sensitivity: int,
                 _score_type: ScoreType) -> None:
        self._sources = _vocabularies
        self._sensitivity = _sensitivity
        self._score_type = _score_type

    def get(self, scores: bool = False, max: int = None) -> Union[List[str], List[Tuple[str, int]]]:
        """ Return the suggested vocabularies sorted from best to worst.

        :param scores: toggle returning results and their scores, defaults to False
        :param max: limit the number of suggestions to max, defaults to None """

        results = []

        for source in self._sources:
            try:
                if len(results) + 1 > max:
                    break
            except TypeError:
                pass
            if scores is True:
                results.append([source.name, getattr(source.ranking, self._score_type.__str__())])
            else:
                results.append(source.name)

        return results

    def print(self):
        """ Print the suggestion to the console. """

        print(f"{len(self._sources)} vocabularies given sensitivity {self._sensitivity}."
              f" From best to worst (vocabularies with no matches are excluded):")
        for source in self._sources:
            print(f"{source.name}, {self._score_type.__str__()}: {getattr(source.ranking, self._score_type.__str__())}")

    def get_score_type(self) -> ScoreType:
        """ Return the suggestion's score type. """

        return self._score_type

    def get_sensitivity(self) -> int:
        """ Return the suggestion's sensitivity. """

        return self._sensitivity
