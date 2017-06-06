#!/bin/bash
qa_system_env --help
qa_system_env -q "In what city is the Heineken brewery?" -a "Amsterdam"
qa_system_env -q "In what city is the Heineken brewery?"
qa_system_env -q "Who is the founder of Penguin Books?"
rm knowledge.dat
qa_system_env -q "In what city is the Heineken brewery?"
# substitutions_examples = 3