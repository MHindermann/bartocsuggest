# bartocsuggest documentation

core.py


### class bartocsuggest.core.Bartoc(data, preload_folder=None)
Vocabulary suggestions using the BARTOC FAST API.


* **Parameters**

    
    * **data** (`Union`[`list`, `str`]) – input data (MUST use complete path)


    * **preload_folder** (`Optional`[`str`]) – folder to save preloaded responses in (MUST use complete path), defaults to None



#### preload(maximum=100000, minimum=0)
Save the concept scheme’s query responses to the preload folder.


* **Parameters**

    
    * **maximum** (`int`) – stop with the maximum-th concept, defaults to 100000


    * **minimum** (`int`) – start with the minimum-th concept, defaults to 0



* **Return type**

    `None`



#### suggest(sensitivity=1, score_type='recall', remote=True, maximum_responses=100000, verbose=False)
Suggest vocabularies based on `scheme`.


* **Parameters**

    
    * **sensitivity** (`int`) – set the maximum allowed Levenshtein distance between concept and result, defaults to 1


    * **score_type** (`str`) – set the score type on which the suggestion is beased, defaults to “recall”


    * **remote** (`bool`) – toggle remote BARTOC FAST querying, defaults to True


    * **maximum_responses** (`int`) – set a maximum number of queries sent resp. responses analyzed, defaults to 100000


    * **verbose** (`bool`) – toggle comments, defaults to False



* **Return type**

    `None`
