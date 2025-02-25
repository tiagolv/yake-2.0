"""Module for keyword extraction from text documents."""

import os
from .Levenshtein import Levenshtein
from .datarepresentation import DataCore


class KeywordExtractor:
    """Class to extract and process keywords from text."""

    def __init__(
        self,
        lan="en",
        n=3,
        dedup_lim=0.9,
        dedup_func="seqm",
        window_size=1,
        top=20,
        features=None,
        stopwords=None,
    ):
        """Initialize the KeywordExtractor with the given parameters.

        Args:
            lan (str): Language code for stopwords
            n (int): N-gram size
            dedup_lim (float): Deduplication threshold
            dedup_func (str): Deduplication function to use
            window_size (int): Size of text window
            top (int): Number of top keywords to return
            features (list): Features to consider
            stopwords (set): Custom stopwords set
        """
        self.lan = lan
        self.n = n
        self.top = top
        self.dedup_lim = dedup_lim
        self.features = features
        self.window_size = window_size

        dir_path = os.path.dirname(os.path.realpath(__file__))
        local_path = os.path.join(
            "StopwordsList",
            f"stopwords_{lan[:2].lower()}.txt"
        )

        if not os.path.exists(os.path.join(dir_path, local_path)):
            local_path = os.path.join("StopwordsList", "stopwords_noLang.txt")

        resource_path = os.path.join(dir_path, local_path)

        if stopwords is None:
            try:
                with open(resource_path, encoding="utf-8") as stop_file:
                    self.stopword_set = set(stop_file.read().lower().split("\n"))
            except UnicodeDecodeError:
                print("Warning: reading stopword list as ISO-8859-1")
                with open(resource_path, encoding="ISO-8859-1") as stop_file:
                    self.stopword_set = set(stop_file.read().lower().split("\n"))
        else:
            self.stopword_set = set(stopwords)

        # Set deduplication function
        if dedup_func in ("jaro_winkler", "jaro"):
            self.dedup_function = self.jaro
        elif dedup_func.lower() in ("sequencematcher", "seqm"):
            self.dedup_function = self.seqm
        else:
            self.dedup_function = self.levs

    def jaro(self, cand1, cand2):
        """Calculate Jaro-Winkler distance between candidates."""
        return jellyfish.jaro_winkler(cand1, cand2)

    def levs(self, cand1, cand2):
        """Calculate normalized Levenshtein distance."""
        distance = Levenshtein.distance(cand1, cand2)
        return 1 - distance / max(len(cand1), len(cand2))

    def seqm(self, cand1, cand2):
        """Calculate sequence matcher ratio."""
        return Levenshtein.ratio(cand1, cand2)

    def extract_keywords(self, text):
        """Extract keywords from the given text.

        Args:
            text (str): Input text to extract keywords from

        Returns:
            list: List of tuples containing (keyword, score)
        """
        try:
            if not text:
                return []

            text = text.replace("\n", " ")
            dc = DataCore(
                text=text,
                stopword_set=self.stopword_set,
                windows_size=self.window_size,
                n=self.n,
            )

            dc.build_single_terms_features(features=self.features)
            dc.build_mult_terms_features(features=self.features)

            result_set = []
            candidates_sorted = sorted(
                [cc for cc in dc.candidates.values() if cc.is_valid()],
                key=lambda c: c.h
            )

            if self.dedup_lim >= 1.0:
                return [(cand.unique_kw, cand.h) for cand in candidates_sorted][
                    :self.top
                    ]

            for cand in candidates_sorted:
                should_add = True
                for (h, cand_result) in result_set:
                    dist = self.dedup_function(
                        cand.unique_kw,
                        cand_result.unique_kw
                    )
                    if dist > self.dedup_lim:
                        should_add = False
                        break

                if should_add:
                    result_set.append((cand.h, cand))
                if len(result_set) == self.top:
                    break

            return [(cand.kw, h) for (h, cand) in result_set]

        except (IOError, ValueError) as e:
            print(f"Warning! Exception: {e} generated by text: '{text}'")
            return []
