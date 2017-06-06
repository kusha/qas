"""
Noun phrases and permutations.
"""

import spacy
from nltk.corpus import wordnet

import itertools

MAX_STRUCT_PERMUTATIONS = 50


def get_synonyms(word, pos=None):
    wordnet_pos = {
        "NOUN": wordnet.NOUN,
        "VERB": wordnet.VERB,
        "ADJ": wordnet.ADJ,
        "ADV": wordnet.ADV
    }
    if pos:
        synsets = wordnet.synsets(word, pos=wordnet_pos[pos])
    else:
        synsets = wordnet.synsets(word)
    synonyms = []
    for synset in synsets:
        synonyms += [str(lemma.name()) for lemma in synset.lemmas()]
    synonyms = [synonym.replace("_", " ") for synonym in synonyms]
    synonyms = list(set(synonyms))
    synonyms = [synonym for synonym in synonyms if synonym != word]
    return synonyms


def get_synonyms_for_token(token):
    pos = token.pos_ if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV"] else None
    return get_synonyms(token.text, pos=pos)


class NounPhrase():
    def __init__(self, tokens):
        self.tokens = tokens
        text = []
        for token in tokens:
            if isinstance(token, spacy.tokens.token.Token):
                text.append(token.text)
            else:
                text.append(str(token))
                self.dependable = False
        self.text = " ".join(text)

    def __str__(self):
        return "<NOUN_PHRASE> {}".format(self.text)

    def get_permutations(self, disable_wordnet=False):
        # structural permutations
        # LOG.info("creating noun phrase permutations")
        permutations = [self]
        permutations += self.structural_permutations()

        if disable_wordnet:
            return permutations

        # continue with permutations generation
        result = []
        for permutation in permutations:
            result += permutation.synonymic_permutations()
        return result

    def synonymic_permutations(self):
        variations = []
        for token in self.tokens:
            variation = []
            variation.append(token)
            for synonym in get_synonyms_for_token(token):
                variation.append(synonym)
            variations.append(variation)
            # print(variation)
        tokens_tuples = list(itertools.product(*variations))
        return [NounPhrase(tokens_tuple) for tokens_tuple in tokens_tuples]


class RootNounPhrase(NounPhrase):
    def __init__(self, tokens):
        super(RootNounPhrase, self).__init__(tokens)
        # LOG.info("Parsing item candidates")
        # self.candidates = self.get_items_set()
        # LOG.info("Finished")

    def structural_permutations(self):
        # allow structural permutatations only for root NP,
        # only root NP contains spaCy doc inside
        tokens = self.tokens
        # calculate dependencies list
        indexes = [token.i for token in tokens]
        # print(indexes)
        dependencies = []
        for idx, token in enumerate(tokens):
            try:
                dependencies.append(indexes.index(token.head.i))
            except ValueError:
                dependencies.append(idx)
        # print("dependencies", dependencies)
        # get skipping variations
        indexes = list(range(len(tokens)))
        # print(indexes)
        skip_variations = []
        for length in range(1, len(tokens)):
            skip_variations.extend(itertools.combinations(indexes, length))
        # extend skip variations using dependencies
        skip_variations = [set(skip_variation)
                           for skip_variation in skip_variations]

        # print("skip_variations", skip_variations)
        def extend_skip_variation(skip_variation):
            new_skips = []
            for index in skip_variation:
                new_skips += [i for i, x in enumerate(dependencies)
                              if x == index]
            new_skips = set(new_skips)
            # print(new_skips, skip_variation)
            if len(new_skips) == 0 or new_skips <= skip_variation:
                return skip_variation
            else:
                return extend_skip_variation(new_skips | skip_variation)
        skip_variations = [extend_skip_variation(skip_variation)
                           for skip_variation in skip_variations]
        # filter skip variations
        # to allow set(sets) we need to move to frozensets
        skip_variations = [frozenset(x) for x in skip_variations]
        skip_variations = list(set(skip_variations))
        skip_variations = [skip_variation for skip_variation in skip_variations
                           if len(skip_variation) < len(tokens)]
        # print("processed skip_variations", skip_variations)
        # apply eligable skip variations
        permutations = []
        for skip_variation in skip_variations:
            def apply_skip_variation(tokens, variation):
                result = []
                for idx, element in enumerate(tokens):
                    if idx not in list(variation):
                        result.append(element)
                return result
            permutations.append(apply_skip_variation(tokens, skip_variation))
        if len(permutations) > MAX_STRUCT_PERMUTATIONS:
            return [self]
        else:
            return [NounPhrase(permutation) for permutation in permutations]
