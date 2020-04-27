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
folder = path.join(DIR, "preload/")

mywords = ["telefon", "wurst"]

# don't load responses for data into preload_folder, make suggestion from remote:
# main(data=mywords)

# load responses for data into preload_folder, make suggestion from remote:
# main(data=mywords, preload_folder=folder, preload=True)

# load responses for data into preload_folder, make suggestion preload folder:
main(data=mywords, preload_folder=folder, preload=True, remote=False)

# don't load responses for data into preload_folder, make suggestion from preload folder:
# main(data=mywords, preload_folder=folder, preload=False, remote=False)

#main(preload=False, remote=False, sensitivity=1)

#   store = Store("owcm_index.xlsx")