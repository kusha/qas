"""
Deprecated bindings to the Link Grammar Parser.
"""

import subprocess
import re
import sys


def parse(string):
    """
    Link-parser output data parser.
    """
    proc = subprocess.Popen(
        ['link-parser', 'en', '-postscript', '-graphics', '-verbosity=0'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout_data = proc.communicate(input=string.encode('utf-8'))[0]
    stdout = stdout_data.decode('utf-8')
    if proc.returncode != 0:
        print("ERROR: dialog system is unable to run link-parser")
        sys.exit(1)
    # filter newlines
    r_unwanted = re.compile("[\n\t\r]")
    stdout = r_unwanted.sub("", stdout)
    # find needed information
    parsed = re.findall(r"\[(.*?)\]\[(.*)\]\[.*?\]", stdout)[0]
    result = {}
    # creating structure
    result["words"] = re.findall(r"\((.*?)\)", parsed[0])
    result["links"] = []
    links = re.findall(r"(\[(\d+) (\d+) (\d+) \((.*?)\)\])", parsed[1])
    for link in links:
        link = list(link)  # was returned tuple
        del link[3]  # ignoring height level of the link
        del link[0]
        link[0] = int(link[0])
        link[1] = int(link[1])
        link[2] = generalize_link(link[2])
        result["links"].append(link)
    return result


def generalize_link(link_type):
    return re.findall(r"^[A-Z]*", link_type)[0]
