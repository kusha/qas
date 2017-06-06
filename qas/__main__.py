#!/usr/bin/env python3

import sys
import argparse

from qas.core import QASystem


class InvalidArguments(Exception):
    def __init__(self, message):
        super(InvalidArguments, self).__init__(message)
        self.message = message


def parse_action(args):
    # validate arguments
    if args.question is not None:
        if args.answer is not None:
            return "train", (args.question, args.answer)
        else:
            return "answer", args.question
    raise InvalidArguments("No action, please specify appropriate flag."
                           " (use --help to learn more)")


def main():
    parser = argparse.ArgumentParser(
        description='Question answering system over linked data.')
    parser.add_argument(
        "-q", "--question",
        action="store",
        help="question in the natural language")
    parser.add_argument(
        "-a", "--answer",
        action="store",
        help="answer to provided question"
             " (add new question-answer pair)")
    parser.add_argument(
        "-d", "--debug",
        action="store_false",
        help="print debug output")
    # parser.add_argument(
    #     "-i", "--interactive",
    #     action="store_true",
    #     help="run interactive mode")
    parser.add_argument(
        "-c", "--config",
        action="store",
        default="config.ini",
        help="configuration file")
    # parser.add_argument(
    #     "--disable-wikidata",
    #     action="store_true",
    #     default=False,
    #     help="disabled linking via Wikidata")
    # parser.add_argument(
    #     "--disable-dbpedia",
    #     action="store_true",
    #     default=False,
    #     help="disabled linking via DBPedia")
    # parser.add_argument(
    #     "--disable-interlinking",
    #     action="store_true",
    #     default=False,
    #     help="disabled interlinking")
    # parser.add_argument(
    #     "--max-depth",
    #     type=int,
    #     default=6,
    #     help="max depth while connecting entities")
    args = parser.parse_args()

    try:
        action, parameter = parse_action(args)
    except InvalidArguments as exception:
        sys.exit(exception.message)

    # print(action)

    qa_system = QASystem.process_args(args)

    # perform action
    if action == "answer":
        question = parameter
        result = qa_system.answer(question)
        print(result)
    elif action == "train":
        question, answer = parameter
        result = qa_system.extend(question, answer)
        print(result)


if __name__ == '__main__':
    main()
