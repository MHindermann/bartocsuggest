""" test_jskos.py

Minimal tests for JSKOS classes and methods.
"""

import unittest
import bartocsuggest.jskos


class TestConcordance(unittest.TestCase):

    def setUp(self) -> None:




        from_scheme = bartocsuggest.jskos._ConceptScheme(uri="https://www.source-scheme.ch", )
        to_scheme = bartocsuggest.jskos._ConceptScheme(uri="https://www.target-scheme.ch")
        mappings = set(bartocsuggest.jskos._ConceptMapping())
        self.concordance = bartocsuggest.jskos._Concordance(from_scheme=from_scheme,
                                                            to_scheme=to_scheme,
                                                            mappings=mappings)

