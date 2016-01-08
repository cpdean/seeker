from __future__ import print_function
import re


class CannotFindIdentifier(Exception):
    pass


class SearchError(Exception):
    pass


def find_location(source, line, col, identifier):
    """
    assume source is a string

    maybe should be a file
    """
    id_regex = re.compile(identifier + r"\s+=")
    defs = []
    lines = source.split("\n")
    for ix, line in enumerate(lines):
        found = id_regex.search(line)
        if found:
            defs.append((ix, found.start()))
    if len(defs) == 0:
        raise CannotFindIdentifier(
            "could not find {} in here".format(identifier))
    if len(defs) > 1:
        raise SearchError(
            "too many matches: {}".format([lines[r] for r, c in defs]))
    return defs[0]


def main():
    print("sup")
