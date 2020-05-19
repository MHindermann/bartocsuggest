""" examples_script.py """

from os import path
from bartocsuggest import Session, AnnifSession, Suggestion

DIR = path.dirname(path.abspath(__file__))

def session_make_preload():
    """ Example session. """

    mywords = ["telefon", "wurst"]
    folder = path.join(DIR, "preload/")

    session = Session(mywords, folder)

    # load responses for mywords into folder:
    session.preload(verbose=True)


def session_from_preload():
    """ Example session. """

    mywords = ["telefon", "wurst"]
    folder = path.join(DIR, "preload/")

    session = Session(mywords, folder)

    # make suggestion from folder:
    suggestion = session.suggest(remote=False, verbose=False)

    # print suggestion:
    suggestion.print()

    # get the concordance:
    suggestion.get_concordance(verbose=True)
    suggestion.get_concordance("psh.ntkcz.cz", verbose=True)


def session_from_remote():
    """ Example session. """

    mywords = ["telefon", "wurst"]
    session = Session(mywords)

    # make suggestion from remote:
    suggestion = session.suggest(remote=True, verbose=False)

    # get the concordance:
    suggestion.get_concordance("psh.ntkcz.cz", verbose=True)


def example_session_owcm():
    """ Example session with preloaded OWCM data."""

    mywords = path.join(DIR, "input_owcm.xlsx")
    folder = path.join(DIR, "preload_owcm/")

    session = Session(mywords, folder)

    # make suggestion from folder (already preloaded):
    session.suggest(remote=False, verbose=True)

def example_annif_session():
    """ Example Annif session. """

    mytext = """Plant viruses are widespread and economically important pathogens. Currently, there are more than one thousand viruses that are known to be potentially capable of infecting plants and new viruses are being discovered every day. Many of them could cause important diseases of various cultivated plants that humans grow for food, fiber, feed, construction material and biofuel. Therefore understanding the biology of plant viruses is important for development and improvement of cultivated plant resistance to viral pathogens.
    A major role in plant resistance against viruses belongs to the process called RNA silencing, that targets both RNA and DNA viruses through the small RNA-directed RNA degradation and DNA methylation pathways. In addition, plants respond to virus infection using an innate immune system that recognizes microbe-associated molecular patterns (MAMPs) of potential pathogens and elicits both local and systemic defense responses. However, in order to be succesfull and break the host resistance, plant viruses have evolved a variety of counter-defense mechanisms such as expressing effector proteins, which are used to downregulate plant antiviral responses. Here, we performed comparative investigation of viral effector proteins from two distanly-related pararetroviruses, Cauliflower mosaic virus (CaMV) and Rice tungro bacilliform virus (RTBV), to understand their role in the suppression of plant antiviral defenses based on RNA silencing and innate immunity. The CaMV P6 protein has previously been shown to serve as a silencing suppressor, while the function of RTBV P4 protein was unknown. Through the use of a classical transient assay in leaves of the N. benthamiana transgenic line 16c we show that RTBV P4 can suppress cell-to-cell spread of transgene silencing, but enhance cell autonomous transgene silencing, which correlates with reduced accumulation of 21-nt siRNAs and increased accumulation of 22-nt siRNAs, respectively. Furthermore, we demonstrate that CaMV P6 from strain CM1841 and RTBV P4 proteins are able to suppress the early plant innate immunity responses, such as oxidative burst. In contrast, CaMV P6 from strain D4 failed to suppress innate immunity, but was capable of suppressing RNA silencing as P6 protein from strain CM1841.
    We also elucidated the role of P4 F-box-like motif and N-terminal domain that are required for RTBV P4 effector functions and protein stability, respectively.
    Finally, through the use of agroinoculation of Oryza sativa plants with RTBV infectious clone we tested if the P4 F-box motif is required for infectivity and our preliminary results show that the F-box mutant virus exhibts drastically reduced infectivity. Furthermore, we found that RTBV circular double-stranded DNA evades siRNA-directed cytosine methylation in infected rice plants and that rice plants overexpressing an OsAGO18 protein are resistant to RTBV infection."""

    # let Annif index mytext:
    annif_session = AnnifSession(mytext, "yso-en")

    # make suggestion for index:
    suggestion = annif_session.suggest(verbose=True)

    # get the concordance:
    suggestion.get_concordance(verbose=True)


session_from_preload()