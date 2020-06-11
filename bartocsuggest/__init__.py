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
from datetime import datetime
from annif_client import AnnifClient

from .utility import _Utility
from .jskos import _Concept, _ConceptBundle, _ConceptMapping, _ConceptScheme, _Concordance, _LanguageMap

import Levenshtein
import requests
import urllib.parse

FAST_API = "https://bartoc-fast.ub.unibas.ch/bartocfast/api"


class _Result:
    """ A BARTOC FAST result.

    :param uri: the result's URI
    :param pref_label: https://www.w3.org/2009/08/skos-reference/skos.html#prefLabel, defaults to None
    :param alt_label: https://www.w3.org/2009/08/skos-reference/skos.html#altLabel, defaults to None
    :param hidden_label: https://www.w3.org/2009/08/skos-reference/skos.html#hiddenLabel, defaults to None
    :param definition: https://www.w3.org/2009/08/skos-reference/skos.html#definition, defaults to None
    """

    def __init__(self,
                 uri: str,
                 pref_label: str = None,
                 alt_label: str = None,
                 hidden_label: str = None,
                 definition: str = None) -> None:
        self.uri = uri
        self.pref_label = pref_label
        self.alt_label = alt_label
        self.hidden_label = hidden_label
        self.definition = definition

    def get_concept(self) -> _Concept:
        """ Return the result as JSKOS concept. """

        concept = _Concept(uri=self.uri)
        labels = ["pref_label", "alt_label", "hidden_label", "definition"]  # i.e., relevant attributes

        for label in labels:
            label_value = self.__getattribute__(label)
            if label_value is None:
                continue
            else:
                concept.__setattr__(label, _LanguageMap({"und": label_value}))

        return concept


class _Query:
    """ A BARTOC FAST query, see https://bartoc-fast.ub.unibas.ch/bartocfast/api (version 1.0.3).

    :param concept: the input JSKOS concept
    :param searchword: the search word, defaults to None
    :param maxsearchtime: the threshold search time in seconds, defaults to 5
    :param duplicates: toggle keeping duplicates between resources, defaults to True
    :param disabled: the disabled resources, defaults to None
    :param response: the query response, defaults to None
    """

    def __init__(self,
                 concept: _Concept,
                 searchword: str = None,
                 maxsearchtime: int = 5,
                 duplicates: bool = True,
                 disabled: List[str] = None,
                 response: Union[Dict, requests.models.Response] = None) -> None:
        self.concept = concept
        if searchword is None:
            self.searchword = concept.get_pref_label()
        else:
            self.searchword = searchword
        self.maxsearchtime = maxsearchtime
        self.duplicates = duplicates
        if disabled is None:
            self.disabled = ["Research-Vocabularies-Australia", "Loterre"]
        else:
            self.disabled = disabled
        self.response = response

    def send(self) -> None:
        """ Send query as HTTP request to BARTOC FAST API.

        The response is saved to the response attribute.
        """

        payload = self.get_payload()
        try:
            self.response = requests.get(url=FAST_API, params=payload)
        except requests.exceptions.ConnectionError:
            print(f"requests.exceptions.ConnectionError! Trying again in 5 seconds...")
            sleep(5)
            self.send()

    def dict2result(self, dictionary: dict) -> _Result:
        """ Transform a raw result into a result object.

        :param dictionary: the raw result
        """

        result = _Result(uri=dictionary.get("uri"),
                         pref_label=dictionary.get("prefLabel"),
                         alt_label=dictionary.get("altLabel"),
                         hidden_label=dictionary.get("hiddenLabel"),
                         definition=dictionary.get("definition"))

        return result

    def update_sources(self, session: Session) -> None:
        """ Update the score vectors of a session's sources based on the query response.

        :param session: the active session
        """

        # extract results from response:
        response = self.get_response()
        results = response.get("results")

        if results is None:
            return None

        for dictionary in results:
            # transform raw result into object:
            result = self.dict2result(dictionary)
            # get source, add if new:
            name = self.result2name(result)
            source = session._get_source(name)
            if source is None:
                source = _Source(name)
                session._add_source(source)
            # update source's score vector:
            source.levenshtein_vector.update_score(self.concept, result)

    def result2name(self, result: _Result) -> str:
        """ Return the source name based on the result.

         :param result: a result
         """
        parsed_uri = urllib.parse.urlparse(result.uri)

        # define (categories of) aggregated sources and split them accordingly:
        if parsed_uri.netloc in ["bartoc-skosmos.unibas.ch", "data.ub.uio.no", "vocab.getty.edu"]:
            return self.uri2name(parsed_uri, n=1)
        elif parsed_uri.netloc in ["isl.ics.forth.gr", "linkeddata.ge.imati.cnr.it", "www.yso.fi"]:
            return self.uri2name(parsed_uri, n=2)
        elif parsed_uri.netloc in ["vocabs.ands.org.au"]:
            return self.uri2name(parsed_uri, n=5)
        else:
            return parsed_uri.netloc

    def uri2name(self, parsed_uri: urllib.parse.ParseResult, n: int = 1) -> str:
        """ Return the source name based on the parsed URI.

        The source name is a substring of the URI.

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
        """ Return the payload (i.e., parameters passed in the URL) of the query. """

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
        """ Return the query response.

        :param verbose: toggle status updates along the way, defaults to False
        """

        # fetch response if not available:
        if self.response is None:
            self.send()
            if verbose is True:
                print(self.response.text)
            return self.response.json()

        # response is cached:
        elif self.response is requests.models.Response:
            return self.response.json()

        # response is preloaded:
        else:
            return self.response

    @classmethod
    def make_query_from_json(cls, json_object: Dict) -> Optional[_Query]:
        """ Return query object initialized from a preloaded query response.

         :param json_object: the preloaded response
         """

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
            scheme = _Utility.words2scheme([searchword])
            concept = _Utility.word2concept(word=searchword, scheme_uri=scheme.uri)
            query = _Query(concept=concept,
                           maxsearchtime=int(maxsearchtime),
                           duplicates=duplicates,
                           disabled=disabled,
                           response=json_object)
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

    :param words: the input words (list of strings, or path to XLSX file, or JSKOS concept scheme)
    :param preload_folder: the path to the preload folder, defaults to None
    :param language: the language of the words given as RFC 3066 language tag, defaults to "und" (for undefined)
    """

    def __init__(self,
                 words: Union[List[str], str, _ConceptScheme],
                 preload_folder: str = None,
                 language: str = "und") -> None:
        self._scheme = self._set_input(words, language)
        self._preload_folder = preload_folder
        self._sources = []

    def _set_input(self, words: Union[list, str, _ConceptScheme], language) -> _ConceptScheme:
        """ Set words as JSKOS concept scheme.

        If the words are not yet a JSKOS concept scheme, they are transformed into one.

        :param words: the input words (list of strings, or path to XLSX file, or JSKOS concept scheme)
        :param language: the language of the words given as RFC 3066 language tag, defaults to "und"
        """

        if type(words) is list:
            scheme = _Utility.words2scheme(words=words, language=language)
        elif type(words) is _ConceptScheme:
            scheme = words
        else:
            scheme = _Utility.load_file(words)

        print(f"{words} loaded successfully, {len(scheme.concepts)} words detected.")
        return scheme

    def _add_source(self, source: _Source) -> None:
        """ Add a source to the session.

         :param source: the source to be added
         """

        self._sources.append(source)

    def _get_source(self, uri: str) -> Optional[_Source]:
        """ Return source by URI.

         :param uri: the URI
         """

        for source in self._sources:
            if uri == source.uri:
                return source

        return None

    def _fetch_and_update(self, remote: bool = True, maximum: int = 100000, verbose: bool = False) -> None:
        """ Fetch query responses and update sources.

        :param remote: toggle fetching responses from BARTOC FAST or preload folder, defaults to True
        :param maximum: the maximum number of responses fetched, defualts to 10000
        :param verbose: toggle status updates along the way, defaults to False
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
                    filename = f"query_{counter}"
                    json_object = _Utility.load_json(self._preload_folder, filename)
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
                if verbose is True:
                    searchword = concept.get_pref_label()
                    print(f"Fetching '{searchword}'...", end=" ")
                query = _Query(concept=concept)
                query.update_sources(self)
                counter += 1
                if verbose is True:
                    print("done.")

        if verbose is True:
            print("Responses collected.")

    def _update_rankings(self, sensitivity: int, verbose: bool = False):
        """ Update the sources' rankings.

        :param sensitivity: the used sensitivity
        :param verbose: toggle status updates along the way, defaults to False
        """

        if verbose is True:
            print("Updating source rankings...")

        for source in self._sources:
            source.update_ranking(self, sensitivity, verbose)

        if verbose is True:
            print("Source rankings updated.")

    def _make_suggestion(self, sensitivity: int, score_type: ScoreType, verbose: bool = False) -> Suggestion:
        """ Return sources from best to worst base on score type.

        :param sensitivity: the used sensitivity
        :param score_type: the used score type
        :param verbose: toggle status updates along the way, defaults to False
        """

        if verbose is True:
            print("Calculating suggestions...", end=" ")

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
            print("calculated.")
            suggestion.print()

        return suggestion

    def preload(self,
                max: int = 100000,
                min: int = 0,
                verbose: bool = False) -> None:
        """ Preload responses.

        For each word in :attr:`self.words`, a query is sent to the BARTOC FAST API.
        The response is saved to :attr:`self.preload_folder`. Use this method for batchwise handling of large
        (>100) :attr:`self.words`.

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

            if verbose is True:
                searchword = concept.get_pref_label()
                print(f"Preloading word number {counter + 1} '{searchword}'...", end=" ")
            _Utility.save_json(_Query(concept=concept).get_response(), self._preload_folder, f"query_{counter}")
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

    The score's value is derived by a comparison between a concept and a BARTOC FAST result.

    :param value: the score's numerical value, defaults to None
    :param comparandum: a concept, defaults to None
    :param comparans: a result, defaults to None
    """

    def __init__(self,
                 value: int = None,
                 comparandum: _Concept = None,
                 comparans: _Result = None) -> None:
        self.value = value
        self.comparandum = comparandum
        self.comparans = comparans


class _Vector:
    """ A vector of scores.

    :param vector: the vector
    """

    def __init__(self,
                 vector: List[_Score] = None) -> None:
        if vector is None:
            self._vector = []
        else:
            self._vector = vector

    def get_vector(self) -> Optional[List[_Score]]:
        """ Return the vector (if any). """

        if len(self._vector) is 0:
            return None
        else:
            return self._vector


class _LevenshteinVector(_Vector):
    """ A vector of Levenshtein distance scores. """

    def make_score(self, concept: _Concept, result: _Result) -> Optional[_Score]:
        """ Make the Levenshtein score for a result.

        The Levenshtein score is the minimum Levenshtein distance over all labels and languages.

        :param concept: the concept from which the distance is measured
        :param result: contains matches to which the distance is measured
        """

        scores = []
        labels = ["pref_label", "alt_label", "hidden_label", "definition"]  # i.e., relevant attributes

        for label in labels:
            label_string = result.__getattribute__(label)
            if label_string is None:
                continue
            distances = []
            # check if label_string has more than one language:
            for foundword in label_string.split(";"):
                distance = Levenshtein.distance(concept.get_pref_label().lower(), foundword.lower())
                distances.append((distance, foundword))
            # add the best foundword and distance tuple per label over all languages:
            scores.append(min(distances))

        # catch malformed (= empty labels) results:
        try:
            min(scores)
        except ValueError:
            return None

        return _Score(value=min(scores)[0], comparandum=concept, comparans=result)

    def update_score(self, concept: _Concept, result: _Result) -> None:
        """ Update the Levenshtein vector with the Levenshtein score for the concept and result.

        :param concept: the concept from which the distance is measured
        :param result: contains matches to which the distance is measured
        """

        score = self.make_score(concept, result)
        if score is None:
            pass
        else:
            self._vector.append(score)


class _Ranking:
    """ The ranking of a source given its best Levenshtein vector.

    :param score_sum: the sum of all scores in the vector, defaults to None
    :param score_average: the vector's average score, defaults to None
    :param score_coverage: the number of scores in the vector, defaults to None
    :param recall: the recall, defaults to None
    """

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
    """ A collection of methods for analyzing score vectors. """

    @classmethod
    def make_score_sum(cls, vector: _LevenshteinVector) -> Optional[int]:
        """ Return the sum of all scores in the vector.

        The lower the sum the better.

        :param vector: the vector
        """

        try:
            return sum(score.value for score in vector.get_vector())
        except (TypeError, AttributeError):
            return None

    @classmethod
    def make_score_average(cls, vector: _LevenshteinVector) -> Optional[float]:
        """ Return the vector's average score.

        The lower the average the better.

        :param vector: the vector
        """

        score_sum = cls.make_score_sum(vector)
        if score_sum is None:
            return None
        else:
            return round(score_sum / len(vector.get_vector()), 2)

    @classmethod
    def make_score_coverage(cls, vector: _LevenshteinVector) -> Optional[int]:
        """ Return the number of scores in the vector.

        :param vector: the vector
        """

        try:
            return len(vector.get_vector())
        except (TypeError, AttributeError):
            return None

    @classmethod
    def make_best_vector(cls, vector: _LevenshteinVector, sensitivity: int) -> Optional[_LevenshteinVector]:
        """ Return the best vector of a vector.

        The best vector has the best score for each search word.

        :param vector: the vector
        :param sensitivity: the used sensitivity
        """

        # collect all unique searchwords in vector:
        initial_vector = vector.get_vector()
        if initial_vector is None:
            return None
        else:
            searchwords = set(score.comparandum.get_pref_label() for score in initial_vector)

        # choose best (=lowest) score for each seachword:
        best_vector = []
        for word in searchwords:
            scores = [score for score in initial_vector if score.comparandum.get_pref_label() == word]
            best_score = sorted(scores, key=lambda x: x.value)[0]
            # check sensitivity:
            if best_score.value <= sensitivity:
                best_vector.append(best_score)

        return _LevenshteinVector(best_vector)

    @classmethod
    def make_recall(cls, relevant: int, retrieved: int) -> Optional[float]:
        """ Return recall.

        See https://en.wikipedia.org/wiki/Precision_and_recall#Recall.

        :param relevant: the number of relevant hits
        :param retrieved: the number of retrieved hits
        """

        try:
            return retrieved / relevant
        except (TypeError, AttributeError):
            return None


class _Source:
    """ A BARTOC FAST source.

    :param uri: the source's URI
    :param levenshtein_vector: the source's Levenshtein vector, defaults to None
    :param ranking: the source's ranking, defaults to None
    """

    def __init__(self,
                 uri: str,
                 levenshtein_vector: _LevenshteinVector = None,
                 ranking: _Ranking = None) -> None:
        self.uri = uri
        if levenshtein_vector is None:
            self.levenshtein_vector = _LevenshteinVector()
        self.ranking = ranking

    def update_ranking(self, session: Session, sensitivity: int, verbose: bool = False) -> None:
        """ Update the sources ranking. """

        if verbose is True:
            print(f"Updating {self.uri}...", end=" ")

        best_vector = _Analysis.make_best_vector(self.levenshtein_vector, sensitivity)

        self.ranking = _Ranking()
        self.ranking.score_sum = _Analysis.make_score_sum(best_vector)
        self.ranking.score_average = _Analysis.make_score_average(best_vector)
        self.ranking.score_coverage = _Analysis.make_score_coverage(best_vector)
        self.ranking.recall = _Analysis.make_recall(len(session._scheme.concepts), self.ranking.score_coverage)

        if verbose is True:
            print("updated.")


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
        :param max: limit the number of suggestions to max, defaults to None
        """

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

    def _get_concordance(self, vocabulary_uri: str = None) -> Optional[_Concordance]:
        """ Return the concordance between the input words and the vocabulary.

        If no vocabulary URI is selected, the most highly suggested vocabulary is used.
        To see the suggested vocabularies and their URIs, use the print method of this class.

        :param vocabulary_uri: the URI of the vocabulary, defaults to None
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
            source_concept = score.comparandum
            target_concept = score.comparans.get_concept()
            source_member_set = {source_concept}
            target_member_set = {target_concept}
            source_bundle = _ConceptBundle(member_set=source_member_set)
            target_bundle = _ConceptBundle(member_set=target_member_set)

            mapping = _ConceptMapping(from_=source_bundle,
                                      to=target_bundle,
                                      from_scheme=source_scheme,
                                      to_scheme=target_scheme)

            concordance.mappings.add(mapping)

        return concordance

    def print_concordance(self, vocabulary_uri: str = None) -> None:
        """ Print the concordance as JSKOS to the console.

        The concordance is between the session's input words from which this suggestion was derived and a vocabulary
        to be chosen by URI. If no vocabulary URI is selected, the most highly suggested vocabulary is used.
        To see the suggested vocabularies and their URIs, use the print method of this class.
        For JSKOS, see https://gbv.github.io/jskos/jskos.html (version 0.4.6).

        :param vocabulary_uri: the URI of the vocabulary, defaults to None
        """

        concordance = self._get_concordance(vocabulary_uri)
        _Utility.print_json(concordance.get_dict())

    def save_concordance(self, folder: str, filename: str = None, vocabulary_uri: str = None) -> None:
        """ Save the concordance as JSKOS in the JSON format.

        :param folder: the path to the save folder
        :param filename: the name of the file, defaults to None
        :param vocabulary_uri: the URI of the vocabulary, defaults to None
        """

        concordance = self._get_concordance(vocabulary_uri)
        _Utility.save_json(dictionary=concordance.get_dict(), filename=filename, folder=folder)

    def save_mappings(self, folder: str, filename: str = None, vocabulary_uri: str = None) -> None:
        """ Save the mappings as JSKOS in the NDJSON format.

        Mappings in this format can be used in the Cocoda Mapping Tool, see https://coli-conc.gbv.de/cocoda/app/
        (version 1.3.6). For NDJSON, see https://github.com/ndjson/ndjson-spec (version 1.0.0).

        :param folder: the path to the save folder
        :param filename: the name of the file, defaults to None
        :param vocabulary_uri: the URI of the vocabulary, defaults to None
        """

        concordance = self._get_concordance(vocabulary_uri)

        if filename is None:
            filename = str(datetime.now()).split(".")[0].replace(":", "-")

        full_filename = folder + f"{filename}.ndjson"
        with open(full_filename, "w") as file:
            for mapping in concordance.mappings:
                print(f"{mapping.get_dict()}".replace("'", '"').replace(" ", ""), file=file)
