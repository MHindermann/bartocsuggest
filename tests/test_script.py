from __future__ import annotations
from typing import List, Optional, Dict, Union

from core import Store


def main(data: Union[str, list],
         preload_folder: str = None,
         preload: bool = False,
         remote: bool = True,
         sensitivity: int = 1,
         score_type: str = "recall") -> None:
    """ Test script. """

    store = Store(data, preload_folder)

    if preload is True:
        store.preload()

    store._fetch_and_update(remote, maximum=10173, verbose=True)

    store.update_rankings(sensitivity=sensitivity, verbose=True)

    store.make_suggestion(sensitivity=sensitivity, score_type=score_type, verbose=True)


#main(preload=False, remote=False, sensitivity=1)

#   store = Store("owcm_index.xlsx")