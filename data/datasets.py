"""
Generate evaluation dataset from multiple QALD datasets.
"""

import json
import logging
import os

logging.basicConfig(level=logging.INFO)


def qald_json(filename, extended=False):
    questions = []
    with open(filename) as data_file:
        data = json.load(data_file)
        for qald_question in data["questions"]:
            # preprocessing
            if extended:
                qald_question = qald_question["question"]
                # compatability to other datasets
                qald_answer = qald_question["answers"]
                qald_question["answers"] = [qald_answer]
            # question processing
            question = {}
            if extended:
                question["question"] = qald_question["language"][0]["question"]
                assert qald_question["language"][0]["language"] == "en"
            else:
                question["question"] = qald_question["question"][0]["string"]
                assert qald_question["question"][0]["language"] == "en"
            # filter questions without answer
            if len(qald_question["answers"]) == 0:
                continue
            # question type processing
            if "boolean" in qald_question["answers"][0]:
                question["answertype"] = "boolean"
            else:
                if "head" in qald_question["answers"][0] and \
                   "vars" in qald_question["answers"][0]["head"]:
                    if len(qald_question["answers"][0]["head"]["vars"]) < 1:
                        continue
                    question["answertype"] = \
                        qald_question["answers"][0]["head"]["vars"][0]
                else:
                    question["answertype"] = "unknown"
            if question["answertype"] == "callret-0":
                question["answertype"] = "\"callret-0\""
            # answer processing
            question["answers"] = []
            if question["answertype"] == "unknown":
                pass
            elif question["answertype"] == "boolean":
                question["answers"].append(qald_question["answers"][0]["boolean"])
            else:
                for qald_answer in \
                   qald_question["answers"][0]["results"]["bindings"]:
                    question["answers"].append(
                        qald_answer[question["answertype"]]["value"])
            questions.append(question)

    not_parsed = [question for question in questions
                  if question["answertype"] == "unknown" or
                  len(question["answers"]) == 0]
    assert len(not_parsed) == 0

    return questions


def main():
    datasets = [
        "qald-6-test-hybrid.json",
        "qald-6-train-hybrid.json",
        "qald-7-train-hybrid-extended-json.json",
        "qald-6-test-multilingual.json",
        "qald-6-train-multilingual.json",
        "qald-7-train-largescale.json",
        "qald-7-train-en-wikidata.json",
        "qald-7-train-multilingual-extended-json.json"
    ]
    dataset = {"questions": []}
    dir_ = os.path.dirname(__file__)
    for filename in datasets:
        filename = os.path.join(dir_, "./qald/{}".format(filename))
        data = qald_json(
            filename,
            extended=True if "-extended-" in filename else False)
        for question in data:
            question["dataset"] = filename
        logging.info("Dataset '%s' parsed with %d questions",
                     filename, len(data))
        dataset["questions"] += data

    logging.info("Total number of questions: %d",
                 len(dataset["questions"]))

    # filter unique questions
    seen = set()
    seen_add = seen.add
    dataset["questions"] = [question for question in dataset["questions"]
                            if not (question["question"] in seen or
                                    seen_add(question["question"]))]
    logging.info("Filtered number of questions: %d",
                 len(dataset["questions"]))

    # print(len(dataset["questions"]))
    # print(len([q for q in dataset["questions"] if q["answertype"] == "uri"]))
    # print(len([q for q in dataset["questions"] if q["answertype"] == "uri" and len(q["answers"]) == 1]))

    # simple factoid
    data = [q for q in dataset["questions"] if q["answertype"] == "uri" and len(q["answers"]) == 1]

    # non factoid
    data = [q for q in dataset["questions"] if q["answertype"] != "uri"]

    print(json.dumps(data, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
