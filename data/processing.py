#!/usr/bin/env python3

"""
This script processes generated distributions
and generates graphs.

Usage:
python3 processing.py
"""

# time processing
from distribution_processing_time import processing_time

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
