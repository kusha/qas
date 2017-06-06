#!/usr/bin/env python3

"""
This script performs primary evaluation measures
for the developed question answering system.

Usage:
python3 evaluate.py dataset.json 2> processing.log
"""

import sys
import json
import time
import statistics
import random
from difflib import SequenceMatcher
import spacy

# sys.path.append('/Users/kusha/desktop/github/qas')
import qas.__init__
from qas.core import QASystem, InvalidEntitiesSet
from qas.wikidata import Wikidata
from qas.link_grammar import parse as link_parse

UNKNOWN = "unknown"


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def divide(a, b, p=False):
    try:
        if not p:
            return round(float(a) / float(b), 4)
        else:
            return round(float(a) * 100.0 / float(b), 2)
    except ZeroDivisionError:
        return UNKNOWN


def save_distribution(name, items):
    template = "{} = {}"
    filename = "distribution_{}.py".format(name)
    with open(filename, "w") as text_file:
        print(template.format(name, str(items)), file=text_file)
    print("{} distribution saved to {}\n".format(name, filename))


# LOADING THE DATASET
# check number of arguments
if len(sys.argv) < 2:
    sys.exit("Too few arguments, please sepcify"
             " directory as a first argument.")
dataset_filename = sys.argv[1]
with open(dataset_filename) as data_file:
    dataset = json.load(data_file)


# final dataset metrics (not aggregated by QALD)
def final_dataset_metrics(dataset):
    questions_count = len(dataset['questions'])
    answers = []
    for question in dataset['questions']:
        answers += question['answers']
    answers_count = len(answers)
    answers_per_question = divide(answers_count, questions_count)

    single_factoid = [question
                      for question in dataset['questions']
                      if question['answertype'] == 'resource' and
                      len(question['answers']) == 1]
    multiple_factoid = [question
                        for question in dataset['questions']
                        if question['answertype'] == 'resource' and
                        len(question['answers']) != 1]
    number_questions = [question
                        for question in dataset['questions']
                        if question['answertype'] == 'number']
    date_questions = [question
                      for question in dataset['questions']
                      if question['answertype'] == 'date']
    boolean_questions = [question
                         for question in dataset['questions']
                         if question['answertype'] == 'boolean']
    aggregation_questions = [question
                             for question in dataset['questions']
                             if question['aggregation'] == 'true']

    report_attributes = []
    for metric in [single_factoid, multiple_factoid, number_questions,
                   date_questions, boolean_questions, aggregation_questions]:
        metric_len = len(metric)
        report_attributes.append(metric_len)
        metric_percentage = divide(metric_len, questions_count, p=True)
        report_attributes.append(metric_percentage)

    questions_w_items = [question
                         for question in dataset['questions']
                         if len(question['items']) > 0]
    questions_w_items_len = len(questions_w_items)
    intelinked_questions = [question
                            for question in dataset['questions']
                            if question['answertype'] == 'resource' and
                            len(question['answers']) > 0 and
                            'wikidata' in question['answers'][0] and
                            'dbpedia' in question['answers'][0]]
    intelinked_questions_len = len(intelinked_questions)

    report = """
    FINAL DATASET METRICS
    -------------------------------
    Total amount of questions: {}
    Total amount of answers: {}
    Answers per question: {}
    Single factoid questions: {}, {}%
    Multiple factoid questions: {}, {}%
    Number questions: {}, {}%
    Date questions: {}, {}%
    Boolean questions: {}, {}%
    Aggregation questions: {}, {}%
    Questions with items specified: {}
    Interlinked factoids count: {}
    """

    return report.format(
        questions_count,
        answers_count,
        answers_per_question,
        *report_attributes,
        questions_w_items_len,
        intelinked_questions_len)


print(final_dataset_metrics(dataset))

# PRIMARY CALCULATIONS STEP

LIMIT = None

extension_subset = [question
                    for question in dataset['questions']
                    if question['answertype'] == 'resource' and
                    len(question['answers']) == 1 and
                    'wikidata_label' in question['answers'][0]]
random.shuffle(extension_subset)
if LIMIT is not None:
    extension_subset = extension_subset[:LIMIT]

EXTENSION_SUBSET_COUNT = len(extension_subset)
EXTENSION_LINKED = 0
EXTENSION_PROCESSED = 0

EXTENSION_PROCESSING_TIME = []
EXTENSION_PROCESSING_TIME_SUCC = []
EXTENSION_PROCESSING_TIME_FAIL = []

SOLUTIONS = []

try:
    with QASystem(config="config.ini") as qa_system:
        for question_obj in extension_subset:
            # extracting question and answer
            question = question_obj['string']
            answer = question_obj['answers'][0]['wikidata_label']
            # searching for a semantic path
            print("Extension:", question, answer)
            start_time = time.time()
            semantic_paths = qa_system.extend(question, answer)
            extension_processing_time = time.time() - start_time
            # evaluating found semantic path
            if semantic_paths is not None:
                EXTENSION_LINKED += 1
                EXTENSION_PROCESSING_TIME_SUCC.append(extension_processing_time)
                SOLUTIONS.append(semantic_paths)
            else:
                # semantic path is not found
                EXTENSION_PROCESSING_TIME_FAIL.append(extension_processing_time)
            # for both linked and non-linked
            EXTENSION_PROCESSING_TIME.append(extension_processing_time)
            EXTENSION_PROCESSED += 1
except KeyboardInterrupt:
    print("EVALUATION INTERRUPT")

APPLY_TIME = []


def extension_metrics():

    extension_linked_percentage = divide(EXTENSION_LINKED, EXTENSION_PROCESSED,
                                         p=True)

    # found number of paths / solution
    extension_paths_count = [len(solution) for solution in SOLUTIONS]
    extension_paths_count_avg = round(statistics.mean(extension_paths_count),
                                      2)\
        if len(extension_paths_count) else UNKNOWN
    save_distribution("paths_count", extension_paths_count)

    # count lengths of found pathes
    extension_paths_length = []
    for solution in SOLUTIONS:
        extension_paths_length += [semantic_path.length
                                   for _, semantic_path in solution]
    extension_paths_length_avg = round(statistics.mean(extension_paths_length),
                                       2)\
        if len(extension_paths_length) else UNKNOWN
    save_distribution("paths_length", extension_paths_length)

    # answering evaluation
    # uses found semantic paths
    # amount of possible substitutions -> distribution

    # calculate number of possible substitutions
    sp_substitutes = []
    for solution in SOLUTIONS[:5]:
        for _, semantic_path in solution[:10]:
            print("Evaluating:", str(semantic_path))
            count, _ = semantic_path.substitutes()
            if count is None:
                count = 0
            sp_substitutes.append(count)
            # calculate apply time
            start_time = time.time()
            count, _ = semantic_path.substitutes(strict=True)
            apply_time = time.time() - start_time
            if count is not None and count > 0:
                APPLY_TIME.append(apply_time)

    save_distribution("subs_count", sp_substitutes)

    # remove over and not filled substitutions
    sp_substitutes_over = len([subs for subs in sp_substitutes
                               if subs >= 500])
    sp_substitutes_zero = len([subs for subs in sp_substitutes
                               if subs == 0])
    sp_substitutes = [subs for subs in sp_substitutes
                      if subs > 1 and subs < 500]
    sp_substitutes_count = len(sp_substitutes)
    sp_substitutes_avg = round(statistics.mean(sp_substitutes), 2)\
        if len(sp_substitutes) else UNKNOWN

    report = """
    EXTENSION METRICS
    -------------------------------
    Linked question-answer pairs: {} of {} ({}%)
    Average count of paths in solution: {}
    Average path length: {}
    Oversubstituted paths: {}
    Paths with no substitutions: {}
    Normal substitutions samples: {}
    Average substitutions count: {}
    """

    return report.format(
        EXTENSION_LINKED,
        EXTENSION_PROCESSED,
        extension_linked_percentage,
        extension_paths_count_avg,
        extension_paths_length_avg,
        sp_substitutes_over,
        sp_substitutes_zero,
        sp_substitutes_count,
        sp_substitutes_avg)


print(extension_metrics())

# !!! found semantic paths by connection type 010101 etc. (something extra?)

# answering without a reference
# for every question -> list of items, precision, recall, f-measure
# calculate datasets average
answering_wo_dataset = [question
                        for question in dataset['questions']
                        if question['answertype'] == 'resource' and
                        len(question['answers']) == 1 and
                        'wikidata' in question['answers'][0]]
if LIMIT is not None:
    answering_wo_dataset = answering_wo_dataset[:LIMIT]

ANSWERING_WO_TIME = []
ANSWERING_WO = []

try:
    with QASystem(config="config.ini") as qa_system:
        for question_obj in answering_wo_dataset:
            # extracting datasets' necessary data
            question = question_obj['string']
            answers = [answer['wikidata'].split('/')[-1]
                       for answer in question_obj['answers']]
            # answering process
            print("Answering:", question)
            start_time = time.time()
            system_answers = qa_system.answer_wo_reference(question)
            answering_processing_time = time.time() - start_time
            ANSWERING_WO_TIME.append(answering_processing_time)
            # evaluation
            if system_answers is None:
                continue
            print(answers)
            print(system_answers)
            true_positive = 0
            false_negatives = 0
            false_positives = 0
            for item in answers:
                if item in system_answers:
                    true_positive += 1
                else:
                    false_negatives += 1
            for item in system_answers:
                if item not in answers:
                    false_positives += 1
            try:
                precision = true_positive / \
                            float(true_positive + false_positives)
                recall = true_positive / float(true_positive + false_negatives)
                f1_score = 2 * precision * recall / (precision + recall)
            except ZeroDivisionError:
                precision = 0.0
                recall = 0.0
                f1_score = 0.0
            print('Precision:', precision)
            print('Recall:', recall)
            print('F-measure:', f1_score)
            ANSWERING_WO.append((precision, recall, f1_score, ))
except KeyboardInterrupt:
    print("EVALUATION INTERRUPT")


def answer_wo():

    answering_wo_samples = len(ANSWERING_WO)

    answering_wo_precision = [measure[0] for measure in ANSWERING_WO]
    answering_wo_precision_avg = round(statistics.mean(answering_wo_precision), 2)\
        if len(answering_wo_precision) else UNKNOWN

    answering_wo_recall = [measure[1] for measure in ANSWERING_WO]
    answering_wo_recall_avg = round(statistics.mean(answering_wo_recall), 2)\
        if len(answering_wo_recall) else UNKNOWN

    answering_wo_f1_score = [measure[2] for measure in ANSWERING_WO]
    answering_wo_f1_score_avg = round(statistics.mean(answering_wo_f1_score), 2)\
        if len(answering_wo_f1_score) else UNKNOWN

    report = """
    ANSWERING W/O REFERENCE METRICS
    -------------------------------
    Answering w/o reference samples: {}
    nswering w/o reference average precision: {}
    nswering w/o reference average recall: {}
    nswering w/o reference average F-measure: {}
    """

    return report.format(answering_wo_samples,
                         answering_wo_precision_avg,
                         answering_wo_recall_avg,
                         answering_wo_f1_score_avg)


print(answer_wo())


# matching with data
matching_subset = [question
                   for question in dataset['questions']
                   if len(question['items']) > 0]
random.shuffle(extension_subset)
if LIMIT is not None:
    matching_subset = matching_subset[:LIMIT]

MATCHING = []
MATCHING_TIMES = []


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def mostly_equal(a, b):
    return similar(a, b) > 0.70


def inside(a, b_list):
    for b in b_list:
        if mostly_equal(a, b):
            print("MOSTLY EQUAL", a, b)
            return True


try:
    with QASystem(config="config.ini") as qa_system:
        for question_obj in matching_subset:
            question = question_obj['string']
            qald_items = question_obj['items']
            # searching for a semantic path
            print("Matching:", question)
            start_time = time.time()
            try:
                entities_sets = qa_system.get_entities_set(question)
            except InvalidEntitiesSet:
                continue
            matching_processing_time = time.time() - start_time
            MATCHING_TIMES.append(matching_processing_time)
            # evaluating found semantic path
            # transforming entities set into labels
            items = []
            for entity_set in entities_sets:
                items += entity_set.items
            item_ids = [item.wd_item_id for item in items]
            entities = Wikidata.get_items(item_ids)
            labels = []
            for _, entity in entities.items():
                if 'labels' in entity:
                    if 'en' in entity['labels']:
                        labels.append(entity['labels']['en']['value'])
            unique_labels = list(set(labels))
            print(unique_labels)
            print(qald_items)
            # calculate measures
            unique_labels = [string.lower() for string in unique_labels]
            qald_items = [string.lower() for string in qald_items]
            true_positive = 0
            false_negatives = 0
            false_positives = 0
            for item in qald_items:
                if inside(item, unique_labels):
                    true_positive += 1
                else:
                    false_negatives += 1
            for item in unique_labels:
                if not inside(item, qald_items):
                    false_positives += 1
            try:
                precision = true_positive / \
                            float(true_positive + false_positives)
                recall = true_positive / float(true_positive + false_negatives)
                f1_score = 2 * precision * recall / (precision + recall)
            except ZeroDivisionError:
                continue
            print('Precision:', precision)
            print('Recall:', recall)
            print('F-measure:', f1_score)
            MATCHING.append((precision, recall, f1_score, ))

except KeyboardInterrupt:
    print("EVALUATION INTERRUPT")


def matching_data():

    matching_samples = len(MATCHING)

    matching_precision = [measure[0] for measure in MATCHING]
    matching_precision_avg = round(statistics.mean(matching_precision), 2)\
        if len(matching_precision) else UNKNOWN

    matching_recall = [measure[1] for measure in MATCHING]
    matching_recall_avg = round(statistics.mean(matching_recall), 2)\
        if len(matching_recall) else UNKNOWN

    matching_f1_score = [measure[2] for measure in MATCHING]
    matching_f1_score_avg = round(statistics.mean(matching_f1_score), 2)\
        if len(matching_f1_score) else UNKNOWN

    report = """
    MATCHING METRICS
    -------------------------------
    Matching with data samples: {}
    Matching average precision: {}
    Matching average recall: {}
    Matching average F-measure: {}
    """

    return report.format(matching_samples,
                         matching_precision_avg,
                         matching_recall_avg,
                         matching_f1_score_avg)


print(matching_data())

# tree matching time (requires available pairs database)
# to estimate large matching database
# popizdochat'

# classification metrcis
# recognize type of question
# popizdochat'

# timing calculation
TIME_SPACY = []
TIME_LG = []

SPACY_NLP = spacy.load('en')

syntax_parse_dataset = dataset['questions']
if LIMIT is not None:
    syntax_parse_dataset = syntax_parse_dataset[:LIMIT]

try:
    for question in syntax_parse_dataset:
        question_string = question['string']
        print('Syntax tree parsing:', question_string)
        # spaCy
        start_time = time.time()
        doc = SPACY_NLP(question_string)
        spacy_time = time.time() - start_time
        TIME_SPACY.append(spacy_time)
        # Link Grammar Parser
        start_time = time.time()
        parsed = link_parse(question_string)
        lg_time = time.time() - start_time
        TIME_LG.append(lg_time)
except KeyboardInterrupt:
    print("MEASURE PARSER'S TIME INTERRUPT")


def timing_metrics():

    # initialization time
    initialization_iter = 5
    initialization_times = []
    for _ in range(initialization_iter):
        start_time = time.time()
        with QASystem(config="config.ini") as qa_system:
            initialization_time = time.time() - start_time
            initialization_times.append(initialization_time)
    initialization_avg = round(statistics.mean(initialization_times), 2)\
        if len(initialization_times) else UNKNOWN

    # extension time
    extension_all = round(statistics.mean(EXTENSION_PROCESSING_TIME), 2)\
        if len(EXTENSION_PROCESSING_TIME) else UNKNOWN
    extension_succ = round(statistics.mean(EXTENSION_PROCESSING_TIME_SUCC), 2)\
        if len(EXTENSION_PROCESSING_TIME_SUCC) else UNKNOWN
    extension_fail = round(statistics.mean(EXTENSION_PROCESSING_TIME_FAIL), 2)\
        if len(EXTENSION_PROCESSING_TIME_FAIL) else UNKNOWN

    # syntax tree parsing
    st_spacy_avg = round(statistics.mean(TIME_SPACY), 5)\
        if len(TIME_SPACY) else UNKNOWN
    st_lg_avg = round(statistics.mean(TIME_LG), 5)\
        if len(TIME_LG) else UNKNOWN

    # answering wo reference
    answering_wo_samples = len(ANSWERING_WO_TIME)
    answering_wo_avg = round(statistics.mean(ANSWERING_WO_TIME), 2)\
        if len(ANSWERING_WO_TIME) else UNKNOWN

    # application reference time
    answering_w_samples = len(APPLY_TIME)
    answering_w_avg = round(statistics.mean(APPLY_TIME), 2)\
        if len(APPLY_TIME) else UNKNOWN

    # matching with data
    matching_data_samples = len(MATCHING_TIMES)
    matching_data_avg = round(statistics.mean(MATCHING_TIMES), 2)\
        if len(MATCHING_TIMES) else UNKNOWN

    report = """
    TIMING METRICS
    -------------------------------------------------
    Average initialization time: {}s @ {} iterations
    Extension average time (all): {}s
    Extension average time (success only): {}s
    Extension average time (failure only): {}s
    spaCy average parsing time: {}
    Link Grammar Parser average parsing time: {}
    Answering w/o reference samples: {}
    Answering w/o reference time: {}s
    Answering with reference samples: {}
    Answering with reference time: {}s
    Matching with data samples: {}
    Matching with data time: {}s
    """

    return report.format(
        initialization_avg,
        initialization_iter,
        extension_all,
        extension_succ,
        extension_fail,
        st_spacy_avg,
        st_lg_avg,
        answering_wo_samples,
        answering_wo_avg,
        answering_w_samples,
        answering_w_avg,
        matching_data_samples,
        matching_data_avg)


print(timing_metrics())
