""" dev.py """

from __future__ import annotations

from bartocsuggest import Session, Suggestion

"""
DIR = path.dirname(path.abspath(__file__))
folder = path.join(DIR, "preload_owcm/")
mywords = path.join(DIR, "input_owcm.xlsx")

session = bartocsuggest.Session(mywords, folder)
suggestion = session.suggest(remote=False, verbose=True)


Outline of stuff to do:

1. Output mapping for best vocabulary given an input. That mapping is most likely partial. For this,
concept matched and searchword must be added to vector, I think. https://gbv.github.io/jskos/jskos.html#concept-mappings

2. Use Annif for suggestions based on some text. Problem here is that BARTOC is not really needed, i.e., why not simply
 use the vocabulary used by Annif for topic modelling also for indexing?

"""
'''
text = """Plant viruses are widespread and economically important pathogens. Currently, there are more than one thousand viruses that are known to be potentially capable of infecting plants and new viruses are being discovered every day. Many of them could cause important diseases of various cultivated plants that humans grow for food, fiber, feed, construction material and biofuel. Therefore understanding the biology of plant viruses is important for development and improvement of cultivated plant resistance to viral pathogens.
A major role in plant resistance against viruses belongs to the process called RNA silencing, that targets both RNA and DNA viruses through the small RNA-directed RNA degradation and DNA methylation pathways. In addition, plants respond to virus infection using an innate immune system that recognizes microbe-associated molecular patterns (MAMPs) of potential pathogens and elicits both local and systemic defense responses. However, in order to be succesfull and break the host resistance, plant viruses have evolved a variety of counter-defense mechanisms such as expressing effector proteins, which are used to downregulate plant antiviral responses. Here, we performed comparative investigation of viral effector proteins from two distanly-related pararetroviruses, Cauliflower mosaic virus (CaMV) and Rice tungro bacilliform virus (RTBV), to understand their role in the suppression of plant antiviral defenses based on RNA silencing and innate immunity. The CaMV P6 protein has previously been shown to serve as a silencing suppressor, while the function of RTBV P4 protein was unknown. Through the use of a classical transient assay in leaves of the N. benthamiana transgenic line 16c we show that RTBV P4 can suppress cell-to-cell spread of transgene silencing, but enhance cell autonomous transgene silencing, which correlates with reduced accumulation of 21-nt siRNAs and increased accumulation of 22-nt siRNAs, respectively. Furthermore, we demonstrate that CaMV P6 from strain CM1841 and RTBV P4 proteins are able to suppress the early plant innate immunity responses, such as oxidative burst. In contrast, CaMV P6 from strain D4 failed to suppress innate immunity, but was capable of suppressing RNA silencing as P6 protein from strain CM1841.
We also elucidated the role of P4 F-box-like motif and N-terminal domain that are required for RTBV P4 effector functions and protein stability, respectively.
Finally, through the use of agroinoculation of Oryza sativa plants with RTBV infectious clone we tested if the P4 F-box motif is required for infectivity and our preliminary results show that the F-box mutant virus exhibts drastically reduced infectivity. Furthermore, we found that RTBV circular double-stranded DNA evades siRNA-directed cytosine methylation in infected rice plants and that rice plants overexpressing an OsAGO18 protein are resistant to RTBV infection."""

annif = AnnifSession(text, "yso-en")
suggestion = annif.suggest(verbose=True)
suggestion.get_mapping()
'''
"""
exit()

# get a suggestion from Annif
annif = AnnifClient()
annif_suggestion = annif.suggest(project_id="yso-en", text=text)

# turn it into jskos
scheme = DevUtility.annif2jskos(annif_suggestion, "yso-en")

# suggest vocabularies
session = Session(words=scheme)
session.suggest(verbose=True)
"""
"""
something completely different: zenodo 
https://developers.zenodo.org/#introduction

query sample articles and looks vor vocabs with keywords input
"""

# Here we test the examples from the readme:

from bartocsuggest import Session

mywords = ["auction", "market", "marketing", "market economy", "perfect competition", "capitalism", "stock market"]

session = Session(mywords)
session.suggest(verbose=True)