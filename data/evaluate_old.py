
import json

from qas import core
from qas import wikidata


def wd_to_label(enitiy_id):
    response = wikidata.Wikidata.get_items([enitiy_id])
    print(response)


def qald(filename):
    with open("datasets/"+filename) as data_file:    
        data = json.load(data_file)

    training = []

    for question in data['questions']:
        text = None
        for subquestion in question['question']:
            if subquestion["language"] == "en":
                text = subquestion["string"]
        question_type = 'other'
        if question["query"]["sparql"].startswith("SELECT DISTINCT ?uri WHERE "):
            question_type = 'factoid'

        answers = []
        if "results" in question["answers"][0] and \
           "bindings" in question["answers"][0]["results"]:
            for result in question["answers"][0]["results"]["bindings"]:
                if "uri" in result and "value" in result["uri"]:
                    answers.append(result["uri"]["value"])

        if len(answers) == 1 and question_type == 'factoid':
            print("{}\t{}\n\t{}".format(question_type, text, answers))
            answer = answers[0].split("/")[-1]
            training.append((text, answer, ))

    # qa_system = core.QASystem()

    for question, answer in training:
        # qa_system.answering(question)
        print(question)
        print(answer)
        label = wd_to_label(answer)
        # print label

def main():
    # TODO parsing filename and format of dataset
    # print(arguments)
    filename = "qald-7-train-en-wikidata.json"
    qald(filename)


if __name__ == '__main__':
    main()
