"""
Module with classes related to pure NLP processing.
(without linking with the data step)
"""

from qas.noun_phrase import RootNounPhrase


class Sentence():
    def __init__(self, text, nlp, log, settings):

        # save qas services
        self.nlp = nlp
        self.log = log

        self.log.debug(
            "Initializing sentence object for phrase '%s'.",
            text)
        self.text = text

        # parse sentence structure using spaCy
        self.spacy_doc = self.nlp(self.text)
        self.log.debug("Sentence structure parsed using spaCy.")

        # transform to internal unified represe
        self.tree = ParseTree(self.spacy_doc)
        self.log.debug("Helper structure for tree comparison created.")

    def similarity(self, other):
        return self.tree.similarity(other.tree)

    def get_noun_phrases(self):
        self.log.debug("Searching for noun phrases")

        def extend_spacy_token(token):
            def extend_token(token):
                result = [token]
                for child in token.children:
                    result += extend_token(child)
                return result
            tokens = extend_token(token)
            #  rewrite with token subtree
            return sorted(tokens, key=lambda x: x.idx)

        # understand where to disable WordNet permutations
        # self.log.warning("WordNet permutations are disabled at the moment")
        # noun_phrases = []
        indexed_noun_phrases = []
        for possible_noun in self.spacy_doc:
            # the module skips WPs
            if possible_noun.tag_ in ["NN", "NNS", "NNP", "NNPS", "CD"]:
                noun_phrase = RootNounPhrase(extend_spacy_token(possible_noun))
                indexed_noun_phrases.append((possible_noun.i, noun_phrase, ))
        return indexed_noun_phrases

    # def get_question_type(self):
    #     for word in self.spacy_doc:
    #         print(word.i, word.text, word.lemma, word.lemma_, word.tag, word.tag_, word.pos, word.pos_)


class ParseTree():
    """
    Unified representation of a sentence tree.
    """
    def __init__(self, doc):
        """
        Create ParseTree object.

        Args:
            doc (TYPE): spaCy doc object
        """
        self.spacy_doc = self.filter_punctuation(doc)
        self.links = []
        for word in self.spacy_doc:
            self.links.append(Link(word))

    @staticmethod
    def filter_punctuation(doc):
        """
        Remove punctuation tags from spaCy document.
        """
        return [word for word in doc if word.pos_ != 'PUNCT']

    def __str__(self):
        result = "<PARSE_TREE> {} ({} links)"
        return result.format(" ".join([word.text for word in self.spacy_doc]),
                             len(self.links))

    def similarity(self, other):
        """
        Return relative similarity to another ParseTree.

        Args:
            other (ParseTree): other sentence

        Returns:
            float: percentage of similar links
        """
        links_found = 0
        for link1 in self.links:
            for link2 in other.links:
                if link1 == link2:
                    links_found += 1
                    break
        return links_found/float(len(self.links))


class Link():
    """
    Unified link representations.
    """
    def __init__(self, word, flexible=False):
        # change text vars to int
        # word.idx contents position inside of the doc
        self.target = {
            "idx": word.idx,
            "text": word.text,
            "lemma": word.lemma_,
            "pos": word.pos_,
            "tag": word.tag_
        }
        self.type = word.dep_
        self.flexible = flexible
        self.source = {
            "idx": word.head.idx,
            "text": word.head.text,
            "lemma": word.head.lemma_,
            "pos": word.head.pos_,
            "tag": word.head.tag_
        }

    def __eq__(self, other):
        """
        Equalty of links.
        Flexible link is similar if POS tags link type are shared.
        Non-flexible link additionally checks lemmas.

        Args:
            other (Link): other link

        Returns:
            bool: links are same
        """
        target_pos = self.target["pos"] == other.target["pos"]
        source_pos = self.source["pos"] == other.source["pos"]
        link_type = self.type == other.type
        target_lemma = self.target["lemma"] == other.target["lemma"]
        source_lemma = self.source["lemma"] == other.source["lemma"]
        if self.flexible:
            return target_pos and source_pos and link_type
        else:
            return target_pos and source_pos and link_type and \
                   target_lemma and source_lemma

    def __str__(self):
        result = "<LINK> {}.{}.{}#{} ==[{}]==> {}.{}.{}#{}"
        return result.format(self.source["lemma"],
                             self.source["tag"],
                             self.source["pos"],
                             self.source["idx"],
                             self.type,
                             self.target["lemma"],
                             self.target["tag"],
                             self.target["pos"],
                             self.target["idx"])
