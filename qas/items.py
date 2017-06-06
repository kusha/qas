"""
Entities of a dataset classes.
"""

from qas.wikidata import Wikidata, WikidataItemsNotFound

STRICT_NAME = False  # filter not same Wikidata
PRIMARY_COUNT = 1
RETRY_PARALLEL_MATCHING = False


def matching_parallel(indexed_noun_phrases, disable_wordnet=False):
    # optimization step
    # parallel enitites linking
    # building paired permutation initially
    permuted_noun_phrases = []
    matching_queries = []
    for idx, noun_phrase in indexed_noun_phrases:
        permutations = noun_phrase.get_permutations(
            disable_wordnet=disable_wordnet)
        permuted_noun_phrases.append((idx, noun_phrase, permutations, ))
        for permutation in permutations:
            matching_queries.append(permutation.text)
    # parallel linking step
    matching = Wikidata.search_by_label_parallel(matching_queries)
    return permuted_noun_phrases, matching


class Item():
    pass


class NoEnglishLabelAvailable(Exception):
    pass


class WikidataItem(Item):
    def __init__(self, item_id, label=None, description=None, claims={}):
        self.item_id = item_id
        self.label = label
        self.description = description
        self.claims = claims

    @classmethod
    def from_search_result(cls, data):
        item_id = data['id']
        label = None
        if 'label' in data:
            label = data['label']
        description = None
        if 'description' in data:
            description = data['description']
        return cls(item_id, label=label, description=description)

    @classmethod
    def from_get_result(cls, data):
        item_id = data['id']
        label = None
        try:
            label = data['labels']['en']['value']
        except KeyError:
            raise NoEnglishLabelAvailable()
        description = None
        try:
            description = data['description']['en']['value']
        except KeyError:
            pass
        if 'claims' in data:
            claims = Wikidata.extract_claims(data)
        # print(item_id, label, claims)
        return cls(item_id,
                   label=label,
                   description=description,
                   claims=claims)

    def __str__(self):
        return str(self.item_id)

    def __hash__(self):
        return hash(self.item_id)


class UniversalItem():
    def __init__(self, wikidata_item, dbpedia_item):
        self.wikidata_item = wikidata_item
        self.dbpedia_item = dbpedia_item
        self.primary = False

    @classmethod
    def from_wikidata_item(cls, wikidata_item):
        dbpedia_item = None
        return cls(wikidata_item, dbpedia_item)

    @property
    def label(self):
        # resit chto delat s raznymi labely? s searchu?
        return self.wikidata_item.label

    @property
    def wd_item_id(self):
        return self.wikidata_item.item_id

    def __str__(self):
        result = "( {}, {}, {})"
        return result.format(
            str(self.wikidata_item),
            str(self.wikidata_item.label) if self.wikidata_item.label
            is not None else "-",
            "https://www.wikidata.org/wiki/{} ".format(str(self.wikidata_item)))

    def __eq__(self, other):
        if self.wikidata_item is not None and other.wikidata_item is not None:
            if self.wikidata_item.item_id == other.wikidata_item.item_id:
                return True
        return False

    def __hash__(self):
        # return hash((hash(self.wikidata_item), hash(self.dbpedia_item)))
        return self.wikidata_item.__hash__()


class EmptyItemsBatch(Exception):
    pass


class ItemsBatch(object):
    def __init__(self, noun_phrase, matching={}):
        self.noun_phrase = noun_phrase
        wikidata_results = []
        try:
            results = None
            if noun_phrase.text in matching:
                results = matching[noun_phrase.text]
                if results is None:
                    if RETRY_PARALLEL_MATCHING:
                        results = Wikidata.search_by_label(noun_phrase.text)
                    else:
                        raise WikidataItemsNotFound()
            else:
                results = Wikidata.search_by_label(noun_phrase.text)
            for result in results:
                wikidata_item = WikidataItem.from_search_result(result)
                wikidata_results.append(wikidata_item)
        except WikidataItemsNotFound:
            # print("WikidataItemsNotFound ", noun_phrase)
            pass
        # DBpedia items
        self.batch = []
        for item in wikidata_results:
            self.batch.append(UniversalItem.from_wikidata_item(item))
        if len(self.batch) == 0:
            raise EmptyItemsBatch()
        for i in range(PRIMARY_COUNT):
            try:
                self.batch[i].primary = True
            except IndexError:
                break
        # self.strict = []
        # self.strict_filter()
        # self.super_strict()

    def strict_filter(self):
        strict = []
        for item in self.batch:
            if item.wikidata_item.label is None:
                continue
            if item.wikidata_item.label.lower() == \
               self.noun_phrase.text.lower():
                strict.append(item)
        return strict

    @staticmethod
    def super_strict(batch):
        return [item for item in batch if item.primary]

    def strictify(self):
        # print("called on", self.noun_phrase.text, [str(x) for x in self.batch])
        if STRICT_NAME:
            self.batch = self.strict_filter()
        self.batch = self.super_strict(self.batch)

    def __str__(self):
        result = "<BATCH> {} ({})\n\t\t" + "{} " * len(self.batch)
        return result.format(
            self.noun_phrase.text,
            len(self.batch),
            *self.batch)


class EmptyEntity(Exception):
    pass


class Entity():
    def __init__(self, noun_phrase, permutations=None,
                 matching=None, log=None):
        self.log = log
        self.noun_phrase = noun_phrase

        # parse permutation in case of non-optimzied and non-parallel
        if permutations is None:
            permutations = noun_phrase.get_permutations()

        # # widget with permutations
        # print(self.noun_phrase.text)
        # for permutation in permutations:
        #     print("\t"+str(permutation))

        self.candidates = []
        for permutation in permutations:
            try:
                self.candidates.append(ItemsBatch(permutation,
                                                  matching=matching))
            except EmptyItemsBatch:
                # print("empty items batch for", permutation)
                pass
        if len(self.candidates) == 0:
            raise EmptyEntity()

    @property
    def items(self):
        result = []
        for candidate in self.candidates:
            for item in candidate.batch:
                result.append(item)
        return result

    def strictify(self):
        for candidate in self.candidates:
            candidate.strictify()

    def __str__(self):
        result = "<ENTITY> {} ({})\n" + "\t{}\n" * len(self.candidates)
        return result.format(
            self.noun_phrase.text,
            len(self.candidates),
            *self.candidates)


class EntitySet():
    def __init__(self, entities, log=None):
        self.log = log
        self.set = entities

    @property
    def items(self):
        result = []
        for entity in self.set:
            for item in entity.items:
                result.append(item)
        return result

    @classmethod
    def merge(cls, entities_sets):
        # for idx, entity_set in enumerate(entities_sets):
        #     print(idx, [entity.noun_phrase.text for entity in entity_set.set])
        for idx1, entity_set1 in enumerate(entities_sets):
            for idx2, entity_set2 in enumerate(entities_sets):
                if idx1 != idx2:
                    intersection = set(entity_set1.items).intersection(entity_set2.items)
                    for shared_item in intersection:
                        entity_set1.log.debug("Merging two sets beacause of shared %s",
                                              str(shared_item))
                    if len(intersection):
                        merged_entity_sets = [entity_set
                                              for idx, entity_set in enumerate(entities_sets)
                                              if idx not in [idx1, idx2]]
                        merged_set = cls(entity_set1.set + entity_set2.set,
                                         log=entity_set1.log)
                        # print(merged_set)
                        merged_entity_sets.append(merged_set)
                        # print(merged_entity_sets)
                        return cls.merge(merged_entity_sets)
        return entities_sets

    def __str__(self):
        result = "<ENTITY_SET>\n" + "{}\n" * len(self.set)
        return result.format(*self.set)
