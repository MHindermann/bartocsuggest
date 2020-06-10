# bartocsuggest

A Python module that suggests vocabularies given a list of words based on the BARTOC FAST API (https://bartoc-fast.ub.unibas.ch/bartocfast/api).

## Installation

```
pip install bartocsuggest
```

## Example
```
from bartocsuggest import Session

my_words = ["auction", "market", "marketing", "market economy", "perfect competition", "capitalism", "stock market"]

session = Session(my_words)
session.suggest(verbose=True)
```

The output to the console should look something like this:

```
73 vocabularies given sensitivity 1. From best to worst (vocabularies with no matches are excluded):
psh.ntkcz.cz, recall: 1.0
vocabulary.worldbank.org, recall: 1.0
zbw.eu, recall: 1.0
eurovoc.europa.eu, recall: 0.8571428571428571
lod.gesis.org, recall: 0.8571428571428571
www.yso.fi/onto/yso, recall: 0.7142857142857143
www.yso.fi/onto/koko, recall: 0.7142857142857143
www.yso.fi/onto/liito, recall: 0.7142857142857143
data.bibliotheken.nl, recall: 0.7142857142857143
lod.nal.usda.gov, recall: 0.7142857142857143
www.yso.fi/onto/juho, recall: 0.5714285714285714
crai.ub.edu, recall: 0.5714285714285714
www.twse.info, recall: 0.5714285714285714
thesaurus.web.ined.fr, recall: 0.5714285714285714
aims.fao.org, recall: 0.5714285714285714
...
```

## Preloading responses
The latency for a response from BARTOC FAST is about 5 seconds per word. Preloading responses is hence useful for dealing with long lists of words or for trying out different types of suggestions for a given list of words without having to resend each query.

```
from bartocsuggest import Session, Average

# preload words:
session = Session(300_word_list, "my/preload/folder")
session.preload(0-99)
session.preload(100-199)
session.preload(200-299)

# try out different suggestions:
suggestion = session.suggest(remote=False, verbose=True)
suggestion_low_sensitivity = session.suggest(remote=False, sensitivity=5, verbose=True)
suggestion_average = session.suggest(remote=False, score_type="Average", verbose=True)
```

## Exporting suggestions 
The input words and the suggested vocabularies are modelled as JSKOS concept schemes (see https://gbv.github.io/jskos/jskos.html). The the concordance between the input words and any suggested vocabulary can be exported as JSON-file. Similarily, the mappings between the input words and any suggested vocabulary can be exported as NDJSON-file (e.g., for use in the Concoda Mapping Tool, see https://coli-conc.gbv.de/cocoda/app/).
```
suggestion.save_concordance("my/save/folder")
suggestion.save_mappings("my/save/folder", vocabulary_uri="vocabulary.worldbank.org")
```

## Annif wrapper
The Annif wrapper is built using the Annif-client module and enables bartocsuggest to suggest vocabularies based on texts:
```
from bartocsuggest import AnnifSession

my_text = "Plant viruses are widespread and economically important pathogens..."

# generate subject indexing for my_text:
annif_session = AnnifSession(my_text, project_id="yso-en")

# make suggestion based on subject indexing:
annif_session.suggest(verbose=True)
```

## Documentation
Documentation available at: https://readthedocs.org/projects/bartocsuggest/

## License
bartocsuggest is released under the MIT License.

## Contact
Maximilian Hindermann  
maximilian.hindermann@unibas.ch  
https://orcid.org/0000-0002-9337-4655
