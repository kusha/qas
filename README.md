
<a href="https://github.com/kusha/qas"><img src="https://cloud.githubusercontent.com/assets/1497090/25505283/66449cc6-2ba1-11e7-9daf-18fde662f651.png"></a>

<a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.6.1-yellow.svg"></a> 
<img src="https://img.shields.io/github/license/kusha/qas.svg">

QAS - question answering system over linked data.

*The system is created as a part of the master's thesis. Abstract:*

> The thesis deals with question answering over structured data. In knowledge databases, a structured data is usually represented by graphs. However, to satisfy information needs using natural language interfaces the system is required to hide the underlying schema from users. A question answering system with a schema-agnostic graph-based approach was developed as a part of this work. In contrast to traditional question answering systems that rely on deep linguistic analysis and statistical methods, the developed system explores provided graph to yield and reuse semantic connection for a known question-answer pair. Lack of large domain-specific structured data made us perform evaluation with the help of prominent open linked datasets such as Wikidata and DBpedia. Quality of separate answering stages and the approach in general was evaluated using adapted evaluation dataset and standard metrics.


## Installation

### Virtual environment installation

Please, make sure, that you have a `python3` *(3.6.1)* and `pip3` and/or `easy_install-3.x` installed. Also `curl` utility is needed.

```
sudo apt-get install python3-setuptools python3.6-dev python3-pip
```

It is possible to create a virtual environment with python dependencies. Make sure, that you have `virtualenv`. To check that `virtualenv` is installed:

```
which virtualenv
```

You should see a path to the executable. If it is available, you can run the initialization script:

```
. ./init.sh
```

`init.sh` file creates a virtual environment, install needed dependencies and download WordNet and spaCy corporas.

After, you can run the system:

```
qa_system --help
```

To leave the virtual environment:

```
deactivate
```

To activate the environment again:

```
source env/bin/activate
```

To leave and delete the virtual environment:

```
. ./clean.sh
```

## Built With

All dependencies will be automatically installed in case of the environment setup. This dependencies required only in case of a custom installation.

The QAS uses spaCy for natural language processing. You can install spaCy using pip:

* [spaCy](https://github.com/explosion/spaCy) - Industrial-strength Natural Language Processing
* [Maven](https://github.com/wordnet/wordnet) - Lexical database of any language


spaCy and NLTK models installation:

```
python3 -m spacy download en_core_web_sm
echo "import nltk; nltk.download('wordnet')" > download_wordnet.py
python download_wordnet.py
```

For WebSocket wrapper you also need a Flask webserver:

```
pip3 install flask
```

## Usage

Generating the evaluation dataset:

```
cd evaluation
python3 generate.py qald/ | tee dataset.test.json
```

Running the evaluation script:

```
python3 evaluate.py dataset.test.json 2> processing.log
```

Generating distribution graphs:

```
python3 processing.py
```

To manually run the system under the environment:

```
qa_system -q "In what city is the Heineken brewery?"
```

Please, provide a question-answer pair to find a semantic path:

```
qa_system -q "In what city is the Heineken brewery?" -a "Amsterdam"
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.txt) file for details

## Authors

Author: Mark Birger.

Supervisor: Doc. RNDr. Pavel Smrž, Ph.D.


