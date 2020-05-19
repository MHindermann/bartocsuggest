"""
bartocsuggest is a Python module that suggests vocabularies given a list of words based on the BARTOC FAST API
(https://bartoc-fast.ub.unibas.ch/bartocfast/api).

Documentation available at: https://bartocsuggest.readthedocs.io/en/latest/

Codebase available at: https://github.com/MHindermann/bartocsuggest
"""

# TODO: update readme with AnnifSession example

from __future__ import annotations
from typing import List, Optional, Dict, Union, Tuple
from time import sleep
from os import path
from datetime import datetime
from annif_client import AnnifClient

from .utility import _Utility
from .jskos import _Concept, _ConceptBundle, _ConceptMapping, _ConceptScheme, _Concordance, _LanguageMap

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

    def get_response(self, verbose: bool = False) -> Dict:
        """ Return the query response. """

        # fetch response if not available:
        if self._response is None:
            self._send()
            if verbose is True:
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
    :param name: the name of the session, defaults to None
    :param preload_folder: the path to the preload folder, defaults to None
    """

    def __init__(self,
                 words: Union[List[str], str, _ConceptScheme],
                 preload_folder: str = None) -> None:
        self._scheme = self._set_input(words)
        self._preload_folder = preload_folder
        self._sources = []

    def _set_input(self, words: Union[list, str, _ConceptScheme]) -> _ConceptScheme:
        """ Set words as concept scheme.

        The input words are transformed into a JSKOS Concept Scheme for internal representation.

        :param words: either a list, or a filename (MUST use complete filepath).
        """

        if type(words) is list:
            scheme = _Utility.list2jskos(words)
        elif type(words) is _ConceptScheme:
            scheme = words
        else:
            scheme = _Utility.load_file(words)

        scheme.uri = "http://123fakestreet.com/" + str(datetime.now()).split(".")[0].replace(" ", "/")

        print(f"{words} loaded successfully, {len(scheme.concepts)} words detected.")
        return scheme

    def _add_source(self, source: _Source) -> None:
        """ Add a source to the store. """

        # TODO: check for duplicate source before adding
        self._sources.append(source)

    def _get_source(self, uri: str) -> Optional[_Source]:
        """ Return source by URI. """

        for source in self._sources:
            if uri == source.uri:
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
                searchword = concept.pref_label.get_value("en")
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

        suggestion = Suggestion(self._scheme, contenders, sensitivity, score_type)

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

            searchword = concept.pref_label.get_value("en")
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
    """ Wrapper for the Annif REST API based on the Annif-client module.

    Annif indexes the input text based on the project identifier with an optional limit or threshold.
    Use this Session to get vocabulary suggestions for full texts instead of words.
    :class:`bartocsuggest.AnnifSession` inherits its methods preload and suggest from :class:`bartocsuggest.Session`.

    :param text: the input text
    :param project_id: the project identifier
    :param limit: the maximum number of results to return, defaults to None
    :param threshold: the minimum score threshold, defaults to None
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
    """ A score.

    The value is derived by a comparison between a search word and a found word elsewhere.

    :param value: the score's numerical value, defaults to None
    :param searchword: the search word, defaults to None
    :param foundword: the found word, defaults to None
    """

    def __init__(self,
                 value: int = None,
                 searchword: str = None,
                 foundword: str = None) -> None:
        self.value = value
        self.searchword = searchword
        self.foundword = foundword


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

        The Levenshtein score is the minimum Levenshtein distance over all labels and languages.

        :param searchword: the word from which the distance is measured
        :param result: contains matches to which the distance is measured
        """

        scores = []
        labels = ["prefLabel", "altLabel", "hiddenLabel", "definition"]

        for label in labels:
            labelstring = result.get(label)
            if labelstring is None:
                continue
            distances = []
            # check if labelstring has more than one language:
            for foundword in labelstring.split(";"):
                distance = Levenshtein.distance(searchword.lower(), foundword.lower())
                distances.append((distance,foundword))
            # add the best foundword and distance tuple per label over all languages:
            scores.append(min(distances))

        # catch malformed (= empty labels) results:
        try:
            min(scores)
        except ValueError:
            return None

        return _Score(value=min(scores)[0], searchword=searchword, foundword=min(scores)[1])

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
                 uri: str,
                 levenshtein_vector: _LevenshteinVector = None,
                 ranking: _Ranking = None) -> None:
        self.uri = uri
        if levenshtein_vector is None:
            self.levenshtein_vector = _LevenshteinVector()
        self.ranking = ranking

    def update_ranking(self, store: Session, sensitivity: int, verbose: bool = False) -> None:
        """ Update the sources ranking. """

        if verbose is True:
            print(f"Updating {self.uri}...")

        best_vector = _Analysis.make_best_vector(self.levenshtein_vector, sensitivity)

        self.ranking = _Ranking()
        self.ranking.score_sum = _Analysis.make_score_sum(best_vector)
        self.ranking.score_average = _Analysis.make_score_average(best_vector)
        self.ranking.score_coverage = _Analysis.make_score_coverage(best_vector)
        self.ranking.recall = _Analysis.make_recall(len(store._scheme.concepts), self.ranking.score_coverage)

        if verbose is True:
            print(f"{self.uri} updated.")


class Suggestion:
    """ A suggestion of vocabularies.

    :param _scheme: the input concept scheme
    :param _vocabularies: the suggested vocabularies
    :param _sensitivity: the used sensitivity
    :param _score_type: the used score type
    """

    def __init__(self,
                 _scheme: _ConceptScheme,
                 _vocabularies: List[_Source],
                 _sensitivity: int,
                 _score_type: ScoreType) -> None:
        self._scheme = _scheme
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
                results.append([source.uri, getattr(source.ranking, self._score_type.__str__())])
            else:
                results.append(source.uri)

        return results

    def print(self):
        """ Print the suggestion to the console. """

        print(f"{len(self._sources)} vocabularies given sensitivity {self._sensitivity}."
              f" From best to worst (vocabularies with no matches are excluded):")
        for source in self._sources:
            print(f"{source.uri}, {self._score_type.__str__()}: {getattr(source.ranking, self._score_type.__str__())}")

    def get_score_type(self) -> ScoreType:
        """ Return the suggestion's score type. """

        return self._score_type

    def get_sensitivity(self) -> int:
        """ Return the suggestion's sensitivity. """

        return self._sensitivity

    def get_concordance(self, vocabulary_uri: str = None, verbose: bool = False) -> Optional[_Concordance]:
        """ Return the concordance between the input words and the vocabulary.

        If no vocabulary URI is selected, the most highly suggested vocabulary is used.
        To see the suggested vocabularies and their URIs, use the print method.

        :param vocabulary_uri: the URI of the vocabulary, defaults to None
        :param verbose: print concordance to console, defaults to False
        """

        # get the correct source (if any) given vocabulary_name:
        vocabulary = None
        if vocabulary_uri is None:
            vocabulary = self._sources[0]
        else:
            for source in self._sources:
                if source.uri == vocabulary_uri:
                    vocabulary = source
        if vocabulary is None:
            print("The selected vocabulary does not exist!")
            return None

        # make the best vector (on which the ranking of self._vocabularies is based):
        best_vector = _Analysis.make_best_vector(vocabulary.levenshtein_vector, self._sensitivity)

        # make concordance:
        source_scheme = self._scheme
        target_scheme = _ConceptScheme(uri=vocabulary.uri)
        concordance = _Concordance(from_scheme=source_scheme, to_scheme=target_scheme, mappings=set())

        # make concept mappings:
        for score in best_vector.get_vector():
            source_concept = _Concept(pref_label=_LanguageMap({"und": score.searchword})) # TODO: ACHTUNG already inverted!
            target_concept = _Concept(pref_label=_LanguageMap({"und": score.foundword})) # TODO: levenshtein score should keep concept with uri etc instead of just foundword!
            source_member_set = {source_concept}
            target_member_set = {target_concept}
            source_bundle = _ConceptBundle(member_set=source_member_set)
            target_bundle = _ConceptBundle(member_set=target_member_set)

            mapping = _ConceptMapping(from_=source_bundle,
                                      to=target_bundle,
                                      from_scheme=source_scheme,
                                      to_scheme=target_scheme)

            concordance.mappings.add(mapping)

        # TODO: print concordance to console, with appropriate functions
        if verbose is True:
            print(f"From {concordance.from_scheme.uri} to {concordance.to_scheme.uri}:")
            for mapping in concordance.mappings:
                for source_concept in mapping.from_.member_set:
                    for target_concept in mapping.to.member_set:
                        print(f"{source_concept.pref_label.get_value('und')} <=> {target_concept.pref_label.get_value('und')}")

        return concordance

    # TODO: save concordance as JSON-LD
    def save_concordance(self, vocabulary_uri: str, save_folder: str) -> None:
        """ Save the concordance between the input words and the vocabulary as JSON-LD to a folder.

        :param vocabulary_uri: the URI of the vocabulary, defaults to None
        :param save_folder: the path to the save folder
        """

        pass
