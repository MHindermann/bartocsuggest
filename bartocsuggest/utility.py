""" utility.py

Utility functions. """

from __future__ import annotations
from typing import Optional, Dict, List
from os import path
from datetime import datetime
from openpyxl import load_workbook
from json import dump, dumps, load
from annif_client import AnnifClient

from .jskos import _Concept, _ConceptScheme, _LanguageMap


class _Utility:
    """ Utility functions """

    @classmethod
    def load_file(cls, filename: str) -> Optional[_ConceptScheme]:
        """ Load a file.

        filename: MUST use complete file path. """

        # stop if file does not exist
        if path.exists(filename) is False:
            print(f"ERROR: File {filename} does not exist!")
            return None

        # choose method depending on file type:
        if filename.endswith(".xlsx"):
            workbook = load_workbook(filename)
            return cls.xlsx2jskos(workbook)
        elif filename.endswith(".json"):
            # TODO: add JSON support
            pass
        else:
            pass

    @classmethod
    def xlsx2jskos(cls, workbook) -> _ConceptScheme:
        """ Transform XLSX to JSKOS """

        scheme = _ConceptScheme()
        for worksheet in workbook:
            for row in worksheet.iter_rows(min_row=1, min_col=1, max_col=1, values_only=True):
                if row[0] is None:
                    continue
                else:
                    concept = _Concept(pref_label=_LanguageMap({"und": row[0]}))  # TODO: automate language detection
                    scheme.concepts.append(concept)

        return scheme

    @classmethod
    def list2jskos(cls, input_list: list) -> _ConceptScheme:
        """ Transform list to JSKOS """

        scheme = _ConceptScheme()
        for item in input_list:
            concept = _Concept(pref_label=_LanguageMap({"und": item}))  # TODO: automate language detection
            scheme.concepts.append(concept)

        return scheme

    @classmethod
    def annif2jskos(cls, annif_suggestion: List[dict], annif_project_id: str) -> _ConceptScheme:
        """ Transform an Annif suggestion to JSKOS.

        :param annif_suggestion: the output of calling AnnifClient.suggest
        :param annif_project_id: Annif API project identifier
        """

        # get project details:
        annif = AnnifClient()
        project = annif.get_project(annif_project_id)
        language = project.get("language")
        name = project.get("name")

        # setup concept scheme based on project details:
        # TODO: add project uri
        scheme = _ConceptScheme(pref_label=_LanguageMap({language: name}))

        # make concept from result and add to concept scheme:
        for result in annif_suggestion:
            label = result.get("label")
            uri = result.get("uri")
            # TODO: add inscheme = concept scheme's uri
            concept = _Concept(uri=uri, pref_label=_LanguageMap({language: label}))
            scheme.concepts.append(concept)

        return scheme

    @classmethod
    def save_json(cls, dictionary: Dict, folder: str, filename: str = None):
        """ Save a dictionary as JSON file.

        :param dictionary: the dictionary to be saved
        :param folder: the folder to write the JSON file in (MUST use complete folder path)
        :param filename: the name of the file, defaults to None
        """

        if filename is None:
            filename = str(datetime.now()).split(".")[0].replace(":", "-")

        full_filename = folder + f"{filename}.json"
        with open(full_filename, "w") as file:
            dump(dictionary, file)


    @classmethod
    def load_json(cls, preload_folder: str, number: int) -> Dict:
        """ Load a JSON object as Python dictionary from a file """

        filename = preload_folder + f"query_{number}.json"

        with open(filename) as file:

            json_object = load(file)

            return json_object
