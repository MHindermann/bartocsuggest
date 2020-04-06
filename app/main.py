""" main.py

Main module. Outline:
MODULE 1: read input data from local file
MODULE 2: send request to FAST
MODULE 3: analyse result
MODULE 4: output result as x """

from __future__ import annotations
from typing import List

from utility import Utility

import requests

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

    def __init__(self, searchword: str, maxsearchtime: int = 5, disabled: List[str] = None) -> None:
        self.searchword = searchword
        self.maxsearchtime = maxsearchtime
        if disabled is None:
            self.disabled = ["Research-Vocabularies-Australia", "Loterre"]

    def get(self) -> requests.models.Response:
        """ Send query as HTTP request to BARTOC FAST API """

        payload = {"searchword": self.searchword,
                   "maxsearchtime": self.maxsearchtime,
                   "disabled": self.disabled}

        return requests.get(url=FAST_API, params=payload)


Utility.load_file("owcm_index.xlsx")
print("OK")