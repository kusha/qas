#!/usr/bin/env python3

"""
This script processes generated distributions
and generates graphs.

Usage:
python3 processing.py
"""

import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

from distribution_processing_time import processing_time
from distribution_paths_length import paths_length
from distribution_paths_count import paths_count


# timing by semantic path length
pt_samples = {}
pt_values = {}
lengths = []
for pt_length, pt_time in processing_time:
    key = str(pt_length)
    if key not in lengths:
        lengths.append(key)
    if key not in pt_samples:
        pt_samples[key] = 0
    pt_samples[key] += 1
    if key not in pt_values:
        pt_values[key] = 0.0
    pt_values[key] += pt_time
for length in sorted(lengths):
    avg = round(pt_values[length] / float(pt_samples[length]), 4)
    print("Length: {} - {} s".format(length, avg))

# drawing distribution graphs

figure = plt.figure()
plt.title("Distribution of semantic paths' lengths")
plt.xlabel("Semantic path length")
plt.ylabel("Number of paths (normalized)")
plt.xticks([1, 2, 3, 4])
plt.hist(paths_length, normed=True)
plt.show()
figure.savefig("eval_paths_length.pdf", bbox_inches='tight')

paths_count = [value for value in paths_count
               if value < 100]
figure = plt.figure()
plt.title("Paths per solution distribution")
plt.xlabel("Paths per solution")
plt.ylabel("Number of paths per solution (normalized)")
plt.hist(paths_count, bins=20, normed=True)
plt.show()
figure.savefig("eval_paths_count.pdf", bbox_inches='tight')