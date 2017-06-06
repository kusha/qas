"""
Main module with QA system implementation.
"""

import shelve
import spacy
import time
import itertools
import configparser
import operator

from nltk import word_tokenize
from nltk.tokenize import sent_tokenize
import langdetect

import qas.logs
import qas.graph
import qas.sentence
import qas.items


class InvalidSentence(Exception):
    pass


class NoEnglishLabelAvailable(Exception):
    pass


class InvalidEntitiesSet(Exception):
    pass


class MultipleSentences(Exception):
    """
    Exception for the multiple sentences per input.

    Attributes:
        sentences (list of strings): splitted list of sentences.
    """
    def __init__(self, sentences):
        self.sentences = sentences


class QASystem(qas.logs.LoggingService):

    def __init__(self,
                 db_filename=None,
                 disable_wordnet=False,
                 config=None,
                 *args, **kwargs):
        """
        Initialize new question answering system.

        Args:
            *args: positional arguments.
            **kwargs: keyword arguments.
        """
        # init logging service
        super(QASystem, self).__init__(*args, **kwargs)

        # load option from the config file
        self.settings = None
        self.settings = configparser.ConfigParser()
        if config is None:
            config = 'config.ini'  # default.ini
        self.settings.read(config)

        # catch output queue for manual manipulations with output
        # (server mode only)
        self.output_queue = kwargs.get('logging_queue', None)

        # database initialization
        self.log.debug('Loading database...')
        self.db = shelve.open(self.settings['DEFAULT']['db_filename'],
                              flag="c")
        # prefill database if newly initialized
        if 'knowledge' in self.db:
            self.log.info('Database loaded')
        else:
            self.log.info('Creating new database')
            self.db['knowledge'] = []
        self.log.info('%s known questions', len(self.db['knowledge']))

        # spaCy initialization
        self.log.debug('Loading spaCy NLP')
        self.nlp = spacy.load(self.settings['DEFAULT']['spacy_model'])
        self.log.debug('spaCy loaded')

    def __enter__(self):
        """
        Allow to use QASystem with a context.

        Returns:
            QASystem: object itself.
        """
        return self

    def __exit__(self, _, __, ___):
        """
        Clean up while closing the dialog system.

        Args:
            _ (TYPE): unused argument.
            __ (TYPE): unused argument.
            ___ (TYPE): unused argument.
        """
        self.log.info('Cleaning it up...')
        self.db.close()

    def add_output_queue(self, logging_queue):
        """
        Add another ouput queue to existing QA system.
        (webserver only, for multiple output systems)

        Args:
            logging_queue (multiprocessing.queue): queue to send logs.
        """
        self.output_queue = logging_queue
        super(QASystem, self).add_output_queue(logging_queue)

    def process_sentence(self, text):
        """
        Process sentence (question/answer).

        Args:
            text (str): sentence text.

        Returns:
            qas.sentence.Sentence, qas.items.EntitySet:
                parsed sentence, entities set or None.
        """

        # check, that the text is in English
        text_language = self.check_language(text)
        if text_language != 'en':
            self.log.warning(
                "Detected language (%s) isn't supported. \
At the moment the system supports only English language.",
                text_language)
            raise InvalidSentence()

        # check that it is one sentence
        try:
            self.check_sentence(text)
        except MultipleSentences as exception:
            self.log.warning(
                'Found %d sentences in the request: %s. \
Please use one sentence per request.',
                len(exception.sentences),
                str(exception.sentences))
            raise InvalidSentence()

        # parse sentence by creating Sentence object
        sentence = qas.sentence.Sentence(
            text,
            nlp=self.nlp,
            log=self.log,
            settings=self.settings)
        # extract noun phrases
        indexed_noun_phrases = sentence.get_noun_phrases()
        self.log.debug('%d noun phrases extracted from the sentence.',
                       len(indexed_noun_phrases))

        # print parsed tree
        root_np_idxs = [np[0] for np in indexed_noun_phrases]
        for token in sentence.spacy_doc:
            if token.i in root_np_idxs:
                print("{}*".format(token.text, token.i), end=" ")
            else:
                print(token.text, end=" ")
        print("")

        # parallel enitites linking
        permuted_noun_phrases, matching = \
            qas.items.matching_parallel(
                indexed_noun_phrases,
                disable_wordnet=self.settings['DEFAULT']['disable_wordnet'])

        # converting noun phrases into enitites
        # (objects linked with a knowledge base)
        entities = []
        for idx, noun_phrase, permutations in permuted_noun_phrases:
            try:
                entity = qas.items.Entity(noun_phrase,
                                          permutations=permutations,
                                          matching=matching,
                                          log=self.log)
            except qas.items.EmptyEntity:
                self.log.debug(
                    "Noun phrase '%s' skipped (empty entities set).",
                    noun_phrase.text)
                continue
            entities.append((idx, entity, ))
            self.log.debug("Entity created for '%s'.", noun_phrase.text)
        self.log.info('%d entities linked in total.', len(entities))

        # print found entities
        # for idx in sorted(root_np_idxs):
        #     for token in sentence.spacy_doc:
        #         if token.i == idx:
        #             print("Root Noun: {}".format(token.text))
        #     for idx2, noun_phrase in indexed_noun_phrases:
        #         if idx == idx2:
        #             print("Root Noun phrase: {}".format(noun_phrase.text))
        # # test

        # entities sets is merged enitities
        # create initial list (enitity to enities set)
        entities_sets = [qas.items.EntitySet([entity[1]], log=self.log)
                         for entity in entities]
        # merge while possible (safe for an empty set)
        entities_sets = qas.items.EntitySet.merge(entities_sets)
        self.log.info('%d enitites sets after merge.', len(entities_sets))

        # strictify enities
        for entities_set in entities_sets:
            for entity in entities_set.set:
                entity.strictify()

        # log special widget with entities set
        # for entity_set in entities_sets:
        #     print(entity_set)

        return sentence, entities_sets

    def lookup(self, sentence, enitites_sets_count=None):
        # implement parse tree constructing via classmethod
        threshold = float(self.settings['DEFAULT']['similarity_threshold'])
        sentence_doc = self.nlp(sentence.text)
        print("Score\t| Reference")
        print("-" * 20)
        for reference in self.db['knowledge']:
            ref_doc = self.nlp(reference['question'])
            similarity = sentence_doc.similarity(ref_doc)
            print("{:.4f}\t| {}".format(similarity, reference['question']))
            if similarity > threshold:
                return reference
        return None

    def answer(self, question):
        """
        Primary method to answer a question.
        Continues processing in a regular of blind manner.

        Args:
            question (str): input sentence.

        Returns:
            TYPE: Description
        """

        self.log.info("Processing question: '%s'", question)
        try:
            question_sentence, entities_sets = self.process_sentence(question)
        except InvalidSentence:
            return None

        if len(entities_sets) == 0:
            self.log.error("System wasn't able to find noun entities in"
                           " the sentence.")
            return

        print("==== MATCHED QUESTION ====")
        for entity_set in entities_sets:
            print(entity_set)

        self.log.info('Looking for a refrence sentence.')
        reference = self.lookup(question_sentence,
                                enitites_sets_count=len(entities_sets))

        if reference is not None:
            self.log.info('Applying knownledge path')
            result = self.reference_answering(question_sentence,
                                              entities_sets,
                                              reference)
            if result is not None:
                return result

        # if no reference or reference is not applicable
        result = self.blind_answer(question_sentence, entities_sets)
        return result

    def reference_answering(self, question_sentence, entities_sets, reference):
        items_list = []
        for entities_set in entities_sets:
            items_list += entities_set.items
        print("==== APPLICATION ATTEMPTS ====")
        answers_score = {}
        for item in items_list:
            wd_item_id = item.wd_item_id
            label = item.wikidata_item.label
            answers = None
            for solution in reference['solution']:
                path = solution['path']
                config = solution['config']
                graph_path = qas.graph.Path(path,
                                            tuple(config),
                                            None,
                                            None)
                _, answers = graph_path.apply_path(wd_item_id)
                if len(answers):
                    for answer in answers:
                        if answer not in answers_score:
                            answers_score[answer] = 1
                        else:
                            answers_score[answer] += 1
                        print("{} ({}) -> {}\n\t{}".format(
                            label,
                            wd_item_id,
                            answer,
                            str(graph_path)))
        if not bool(answers_score):
            return None
        print('Most common answer:',
              max(answers_score.items(), key=operator.itemgetter(1))[0])
        return answers_score.keys()

    def answer_wo_reference(self, question):
        self.log.info("Processing question: '%s'", question)
        try:
            question_sentence, entities_sets = self.process_sentence(question)
        except InvalidSentence:
            return None

        if len(entities_sets) == 0:
            self.log.error("System wasn't able to find noun entities in"
                           " the sentence.")
            return None

        result = self.blind_answer(question_sentence, entities_sets)
        return result

    def blind_answer(self, question_sentence, entities_sets):
        self.log.info('Trying to resolve answer without reference question.')

        # classify question
        # question_type = question_sentence.get_question_type()

        # assign labels (each to each)
        labels = []
        labeled_entities = []
        for idx, entities_set in enumerate(entities_sets):
            for entity in entities_set.set:
                label = "item{}".format(idx)
                labels.append(label)
                labeled_entities.append((label, entity, ))

        graph_ = qas.graph.Graph(labeled_entities)
        combinations = itertools.combinations(labels, 2)
        solutions = {}
        for direction_from, direction_to in combinations:
            print("Processing direction:", direction_from, direction_to)
            solutions.update(graph_.connect(direction_from, direction_to))

        if len(solutions) == 0:
            self.log.error("Connection at graph wasn't found.")
            return
        self.log.info('%d connections found', len(solutions))

        for key, pathes in solutions.items():
            print(key)
            for path in pathes:
                print(path)

        solutions = qas.graph.Graph.evaluate_solutions(solutions)
        print("==== PATHS ====")
        print("Score\t| Length, Path")
        print("----------------")
        for score, solution in solutions[-10:]:
            print("{:.5f}\t| {}".format(score, str(solution)))

        result = []
        valuable_count = int(
            self.settings['DEFAULT']['wo_reference_pathes_valuable_count'])
        for _, path in solutions[-valuable_count:]:
            result += path.items

        result = list(set(result))

        # print candidates
        print("==== RESULTS ====")
        for item in result:
            print("https://www.wikidata.org/wiki/{}".format(item))
        return result

    @staticmethod
    def check_sentence(text):
        """
        Check, that only one sentence was provided.

        >>> QASystem.check_sentence("Example sentence.")
        >>> QASystem.check_sentence("Example sentence. Another example.")
        Traceback (most recent call last):
        core.MultipleSentences: ['Example sentence.', 'Another example.']

        Args:
            text (str): provided question/answer.

        Returns:
            None

        Raises:
            MultipleSentenceQuestion: in case of more than one sentence inside
            of the text string.
        """
        sent_tokenize_list = sent_tokenize(text)  # nltk tokenize sentence
        if len(sent_tokenize_list) > 1:
            raise MultipleSentences(sent_tokenize_list)

    @staticmethod
    def check_language(text):
        """
        Get sentence language.

        >>> QASystem.check_language("John have a dog.")
        'en'
        >>> QASystem.check_language("Jak se máš?")
        'cs'
        >>> QASystem.check_language("Amsterdam.")  # holland language
        'en'

        Args:
            text (str): sentence string.

        Returns:
            str: language code (for example 'en'), returns 'en' for sentences
            shorter than 3 words.
        """
        # possibly langdetect.detect_langs(text)
        if len(word_tokenize(text)) <= 2:
            return 'en'
        return langdetect.detect(text)

    def extend(self, question, answer,
               question_entities_sets=None,
               answer_entities_sets=None):
        """
        Try to learn a new knowledge from question-answer pair.
        """

        # process question
        try:
            if question_entities_sets is None:
                question_entities_sets = self.get_entities_set(question)
            if answer_entities_sets is None:
                answer_entities_sets = self.get_entities_set(answer)
        except InvalidEntitiesSet:
            self.log.error("System is unable to process the question-answer pair.")
            return None

        result = self.extend_sets(question_entities_sets, answer_entities_sets)

        # save data to the database
        skip_flag = False
        for pair in self.db['knowledge']:
            if pair['question'] == question:
                skip_flag = True
        if not skip_flag:
            record = {}
            record['question'] = question
            record['answer'] = answer
            items = []
            for entities_set in question_entities_sets + answer_entities_sets:
                items += [item.wd_item_id for item in entities_set.items]
            record['items'] = items
            record['solution'] = [{
                                    "path": sol[1].path,
                                    "config": list(sol[1].config)
                                  }
                                  for sol in result[-10:]]
            temporary = self.db['knowledge']
            temporary.append(record)
            self.db['knowledge'] = temporary
            print("* pairs db updated *")
        else:
            print("* extension skipped *")

        return result

    def get_entities_set(self, sentence):
        """
        Produce entities set based on items list.
        """
        # process sentence
        self.log.info('Processing sentence: %s', sentence)
        try:
            _, entities_sets = self.process_sentence(sentence)
        except InvalidSentence:
            raise InvalidEntitiesSet()
        if entities_sets is None:
            self.log.error("System is unable to process the sentence.")
            raise InvalidEntitiesSet()

        # check found enities length
        if len(entities_sets) == 0:
            self.log.error("System wasn't able to find noun entities in \
the sentence.")
            raise InvalidEntitiesSet()

        return entities_sets

    def extend_sets(self,
                    question_entities_sets,
                    answer_entities_sets):

        # assign group label for enitites
        labeled_entities = []
        for entities_set in question_entities_sets:
            for entity in entities_set.set:
                # entity.strictify()
                labeled_entities.append(("question", entity, ))
        for entities_set in answer_entities_sets:
            for entity in entities_set.set:
                # entity.strictify()
                labeled_entities.append(("answer", entity, ))

        # return widget
        print("==== MATCHED QUESTION ====")
        for entity_set in question_entities_sets:
            print(entity_set)
        print("===== MATCHED ANSWER =====")
        for entity_set in answer_entities_sets:
            print(entity_set)

        graph_ = qas.graph.Graph(labeled_entities)
        solutions = graph_.connect("question", "answer")
        if len(solutions) == 0:
            self.log.error("Connection at graph wasn't found.")
            return None
        self.log.info('%d connections found', len(solutions))

        # print pathes in a widget
        # for key, pathes in solutions.items():
        #     print(key)
        #     for path in pathes:
        #         print(path)

        solutions = qas.graph.Graph.evaluate_solutions(solutions)
        print("==== RESULTS ====")
        print("Score\t| Length, Path")
        print("-----------------")
        for score, solution in solutions[-10:]:
            print("{:.5f}\t| {}".format(score, str(solution)))
        print(solution.pp_links())  # solution is last == best

        # print suns
        substitutions_examples = int(
            self.settings['DEFAULT']['substitutions_examples'])
        if substitutions_examples:
            for _, solution in solutions[-substitutions_examples:]:
                print("--- POSSIBLE SUBS ---")
                strict = False
                count, substitutes = solution.substitutes()
                if count is None:
                    strict = True
                    count, substitutes = solution.substitutes(strict=True)
                count = "N/A" if count is None else count
                print("strict:", strict, "count:", count)
                for question, answer in substitutes[:10]:
                    print("{} --- {}".format(question, answer))
                    print("\thttps://www.wikidata.org/wiki/{}".format(question))
                    print("\thttps://www.wikidata.org/wiki/{}".format(answer))

        return solutions

    @classmethod
    def process_args(cls, args):
        options = {
            'config': args.config,
            # 'debug': False  # True if args.debug else False
        }
        return cls(**options, debug=False) 


if __name__ == '__main__':
    with QASystem(config="config.ini", debug=False) as qa_system:
        start_time = time.time()
        # qa_system.answer("Who were generals of the battle of Gettynsburg?")
        qa_system.extend("In what city is the Heineken brewery?",
                         "Amsterdam")
        # qa_system.answering("Show me Hemingway's autobiography")
        # qa_system.answer("Who is the founder of Penguin Books?")
        # qa_system.answer("In what city is the Heineken brewery?")
        # res = qa_system.answer_wo_reference(
        #     "In what city is the Heineken brewery?")
        # print(res)
        # qa_system.extend("Who is the president of Eritrea?",
        #                  "Isaias Afewerki")
        # qa_system.answer("Who is the president of Eritrea?")
        # qa_system.extend("In which U.S. state is Fort Knox located?",
        #     "Kentucky")
        # qa_system.answer("In what city is the Heineken brewery?")
        # qa_system.answer("Who is the founder of Penguin Books?")
        # qa_system.answer("In what city is the Heineken brewery?")

        end_time = time.time()
        print("Elapsed time:", (end_time - start_time))
