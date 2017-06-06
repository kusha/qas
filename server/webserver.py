import json
import eventlet

import time
import multiprocessing
import queue as queue_lib

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from qas.core import QASystem


def watchdog(target, args, queue):
    process = multiprocessing.Process(target=target, args=args)
    process.start()
    while True:
        try:
            data = queue.get_nowait()
        except queue_lib.Empty:
            time.sleep(0.2)
            continue
        emit('output', json.loads(data))
        eventlet.sleep(0)
        if not process.is_alive() and queue.empty():
            break
    process.join()


QAS = QASystem()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('answering')
def answer(message):

    queue = multiprocessing.Queue()
    QAS.add_output_queue(queue)

    watchdog_proc = multiprocessing.Process(target=watchdog,
                                            args=(QAS.answering,
                                                  (message["question"], ),
                                                  queue, ))
    watchdog_proc.start()
    watchdog_proc.join()


@socketio.on('request_examples')
def examples(message):
    filename = "qald-7-train-en-wikidata.json"
    with open("datasets/"+filename) as data_file:
        data = json.load(data_file)
        filtered = {"questions": []}
        for question in data["questions"]:
            filtered["questions"].append(question["question"][0]["string"])
        emit('examples', filtered)


if __name__ == '__main__':
    socketio.run(app)
