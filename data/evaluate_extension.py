import json
import sys
import os
import time
import random

sys.path.append('/Users/kusha/qas')
from qas.wikidata import Wikidata
from qas.core import QASystem

with open("dataset.json") as data_file:
    data = json.load(data_file)

pairs = []
for question in data['questions']:
    if question['answertype'] == 'resource':
        if len(question['answers']) == 1:
            if "wikidata" in question['answers'][0]:
                answer_uri = question['answers'][0]["wikidata"]
                answer_label = Wikidata.get_label_by_uri(answer_uri)
                print(answer_uri, answer_label)
                pairs.append((question['string'], answer_label, ))

random.shuffle(pairs)

success = 0
processed = 0
with QASystem(db_filename="knowledge.db") as qa_system:
    for question, answer in pairs:
        print("suppress output")
        # sys.stdout = os.devnull
        # sys.stderr = os.devnull
        start_time = time.time()
        result = qa_system.extend(question, answer)
        end_time = time.time()
        spent_time = end_time - start_time
        # sys.stdout = sys.__stdout__
        # sys.stderr = sys.__stderr__
        # print("back")
        print(result)
        if result:
            success += 1
        processed += 1
        print("RECORD", spent_time, success, processed, len(pairs))