#!/bin/bash
python3.6 -m venv --no-site-packages env
source env/bin/activate
# install dependencies
pip3 install --no-cache-dir -r requirements.txt
# download spacy model
python3 -m spacy download en_core_web_sm
# download wordnet model
mkdir env/nltk
export NLTK_DATA=env/nltk
echo "export NLTK_DATA=env/nltk" >> env/bin/activate
echo "import nltk; nltk.download('wordnet')" > download_wordnet.py
python3 download_wordnet.py
# install qas
python3 setup.py install --force
echo "Environment setup complete."
echo "Use qa_system command to run the system."
