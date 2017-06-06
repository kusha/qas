#!/usr/bin/env python3

"""
This script generates evaluation dataset
by merging and interlinked available QALD datasets.

Usage:
python3 generate.py foler-with-qald-datsets/ | tee dataset.v2.json
"""

import sys
import json
import pathlib  # part of stdlib from Python 3.4
import nltk

# import modules for wikidata/dbpedia manipulations
# sys.path.append('/Users/kusha/qas')
from qas.dbpedia import DBpedia
from qas.wikidata import Wikidata, NoSPARQLResponse

ANSWERS_LIMIT = 30


def info(*args, **kwargs):
    """
    Print data to stderr.
    """
    print(*args, file=sys.stderr, **kwargs)


def main():
    """
    Generation of the dataset.
    """
    # check number of arguments
    if len(sys.argv) < 2:
        sys.exit("Too few arguments, please sepcify"
                 " directory as a first argument.")
    # select QALD dataset
    directory = sys.argv[1]
    files_json = list(pathlib.Path(directory).glob('*.json'))

    # resulting dataset
    result = {}
    result["questions"] = []

    # for every dataset
    for file_json in files_json:
        info('Opening', file_json)
        with open(file_json) as data_file:
            data = json.load(data_file)

        dataset_id = data['dataset']['id']
        info("Dataset:\t", dataset_id)

        extended = False
        if isinstance(data['questions'][0]['question'], dict):
            extended = True
        info("Extended:\t", extended)

        question_number = len(data['questions'])
        info("Questions:\t", question_number)

        # dataset metrics
        skipped = 0
        interlinked = 0
        resources_questions = 0

        # for every question from the dataset
        for question in data['questions']:
            # get question
            string = None
            keywords = []
            multilingual = None
            if not extended:
                multilingual = question['question']
            else:
                multilingual = question['question']['language']
            for lang_question in multilingual:
                if lang_question["language"] == "en":
                    if not extended:
                        string = lang_question['string']
                    else:
                        string = lang_question['question']
                    if 'keywords' in lang_question:
                        keywords = lang_question['keywords'].split(',')
            keywords = [keyword.strip() for keyword in keywords]

            # check skip
            skip_flag = False
            for added_question in result["questions"]:
                if string == added_question["string"]:
                    skip_flag = True
                    break
            if skip_flag:
                skipped += 1
                continue

            # filter keywords
            items = []
            for keyword in keywords:
                in_question = True
                for word in keyword.split(' '):
                    if not word.lower() in string.lower():
                        in_question = False
                is_noun_phrase = False
                collocation = nltk.word_tokenize(keyword)
                for word in nltk.pos_tag(collocation):
                    if word[1] in ["NN", "NNS", "NNP", "NNPS"]:
                        is_noun_phrase = True
                if in_question and is_noun_phrase:
                    items.append(keyword)

            # answer metadata
            if not extended:
                answertype = question["answertype"]
            else:
                answertype = question["question"]["answertype"]
            if not extended:
                aggregation = question["aggregation"]
            else:
                aggregation = question["question"]["metadata"]["aggregation"]

            if answertype == 'resource':
                resources_questions += 1

            # get answers
            result_answers = []
            answers = None
            try:
                if not extended:
                    answers = question["answers"][0]
                else:
                    answers = question["question"]["answers"]
                skip_answers_flag = False
                try:
                    answer_attr = answers['head']['vars'][0]
                except KeyError:
                    if 'boolean' in answers:
                        answertype = 'boolean'
                        result_answers.append(answers['boolean'])
                        skip_answers_flag = True
                    else:
                        raise
                if not skip_answers_flag:
                    answers = answers['results']['bindings']
                    if len(answers) > ANSWERS_LIMIT:
                        skipped += 1
                        continue
                    every_answer_interlinked = True
                    for answer in answers:
                        if answer_attr not in answer:
                            answer_attr = '"' + answer_attr + '"'
                        value = answer[answer_attr]['value']
                        result_answer = {
                            'answertype': answertype
                        }
                        if answertype != 'resource':
                            result_answer['value'] = value
                        else:
                            if value.startswith('http://dbpedia.org/'):
                                result_answer['dbpedia'] = value
                                try:
                                    wikidata = DBpedia.wd_from_link(value)
                                except NoSPARQLResponse:
                                    wikidata = None
                                if wikidata is not None:
                                    result_answer['wikidata'] = wikidata
                                else:
                                    every_answer_interlinked = False
                            elif value.startswith('http://www.wikidata.org/'):
                                result_answer['wikidata'] = value
                        # append labels
                        if 'wikidata' in result_answer:
                            answer_label = Wikidata.get_label_by_uri(
                                result_answer['wikidata'])
                            result_answer['wikidata_label'] = answer_label
                        result_answers.append(result_answer)
                    # count interlinked values
                    if every_answer_interlinked and (answertype == 'resource'):
                        interlinked += 1
            except IndexError:
                pass  # no answer available

            # add question
            result_question = {
                'string': string,
                'keywords': keywords,
                'items': items,
                'answertype': answertype,
                'aggregation': aggregation,
                'answers': result_answers,
                'dataset': dataset_id
            }
            result["questions"].append(result_question)

        info("Skipped:\t", skipped)
        info("Added:\t", question_number-skipped)
        info("Interlinked:\t", interlinked)
        info("Resources:\t", resources_questions)

    # print the final dataset to STDOUT
    print(json.dumps(result, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
