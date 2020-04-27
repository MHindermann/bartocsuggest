""" test_script.py """

from __future__ import annotations
from typing import Union
from os import path

from core import Bartoc


def main(data: Union[str, list],
         preload_folder: str = None,
         preload: bool = False,
         sensitivity: int = 0,
         score_type: str = "recall",
         remote: bool = True,
         maximum_responses: int = 5,
         verbose: bool = True) -> None:
    """ Main function. """

    bartoc = Bartoc(data, preload_folder)

    if preload is True:
        bartoc.preload()

    bartoc.suggest(sensitivity, score_type, remote, maximum_responses, verbose)


DIR = path.dirname(path.abspath(__file__))

data = ["telefon", "wurst"]

main(data)

#main(preload=False, remote=False, sensitivity=1)

#   store = Store("owcm_index.xlsx")