""" examples_script.py """

from __future__ import annotations
from typing import Union
from os import path

from bartocsuggest import Session


def main(data: Union[str, list],
         preload_folder: str = None,
         preload: bool = False,
         sensitivity: int = 0,
         score_type: str = "recall",
         remote: bool = True,
         maximum_responses: int = 100000,
         verbose: bool = True) -> None:
    """ Main function. """

    session = Session(data, preload_folder)

    if preload is True:
        session.preload()

    session.suggest(sensitivity, score_type, remote, maximum_responses, verbose)


DIR = path.dirname(path.abspath(__file__))


def test_preload():
    """ Preload test. """

    folder = path.join(DIR, "prelowqdqwdwsad/")
    mywords = ["telefon", "wurst"]

    session = Session(mywords, folder)
    session.preload(verbose=True)

def test_basic():
    """ Basic high level test. """

    folder = path.join(DIR, "preload/")
    mywords = ["telefon", "wurst"]

    # don't load responses for data into preload_folder, make suggestion from remote:
    main(data=mywords)

    # load responses for data into preload_folder, make suggestion from remote:
    main(data=mywords, preload_folder=folder, preload=True)

    # load responses for data into preload_folder, make suggestion from preload folder:
    main(data=mywords, preload_folder=folder, preload=True, remote=False)

    # don't load responses for data into preload_folder, make suggestion from preload folder:
    main(data=mywords, preload_folder=folder, preload=False, remote=False)


def test_owcm():
    """ OWCM high level test."""

    folder = path.join(DIR, "preload_owcm/")
    mywords = path.join(DIR, "input_owcm.xlsx")

    # don't load responses for data into preload_folder, make suggestion from preload folder:
    main(data=mywords, preload_folder=folder, preload=False, remote=False)


def test_annif():
    """ Annif high level test. """

    # Annif YSO + https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0232391
    # mywords = ["viruses", "bioinformatics", "molecular biology", "genetics", "sequence analysis"]

    # Annif Wikidata + https://edoc.unibas.ch/37670/
    mywords = ["auction", "market", "free market", "marketing mix", "marketing", "market economy", "black market",
               "perfect competition", "capitalism", "stock market"]
    # don't load responses for data into preload_folder, make suggestion from remote:
    main(data=mywords)


test_preload()
