from __future__ import print_function
import os
import re
import json
import logging

log = logging.getLogger(__name__)


class CannotFindIdentifier(Exception):
    pass


class SearchError(Exception):
    pass


def _id_regex_from(identifier):
    regular = r"^(type( alias)? )?" + identifier + r"\s+(\w+\s)*="
    weird_record_based = identifier + r"\s+\{\w+(,\s+\w+)*\}\s+="
    _regex = re.compile(r'|'.join([regular, weird_record_based]))

    def fn(line):
        return _regex.search(line)
    return fn


def find_location_in_source(source, line, col, identifier):
    """
    assume source is a string

    maybe should be a file
    """
    id_regex = _id_regex_from(identifier)
    defs = []
    masked = _mask_comments(source)
    lines = masked.split("\n")
    for ix, line in enumerate(lines):
        found = id_regex(line)
        if found:
            defs.append((ix, found.start()))
    if len(defs) == 0:
        raise CannotFindIdentifier(
            "could not find {} in here".format(identifier))
    if len(defs) > 1:
        raise SearchError(
            "too many matches: {}".format([lines[r] for r, c in defs]))
    return defs[0]


def find_location(path, source_path, line, col, identifier):
    """
    source is path to file
    """
    log.debug("searching in {}".format(source_path))
    with open(source_path) as s:
        source = s.read()
    this_line = source.split("\n")[line]
    assert identifier in this_line, "{} should be in '{}'".format(identifier, this_line)  # NOQA
    # changed this to search external first
    # because of :
    # module_fn = ExternalMod.module_fn
    modules = modules_to_search(source, line, col, identifier)
    for m in modules:
        log.debug("looking for path to {}".format(m))
        paths = files_of(m, path)
        for p in paths:
            log.debug("checking {}".format(p))
            with open(p) as m:
                try:
                    row, col = find_location_in_source(
                        m.read(), line, col, identifier
                    )
                    return [p, row, col]
                except CannotFindIdentifier:
                    print("could not find in {}".format(p))
    if len(modules) == 0:
        log.debug("looking in the file function is used in")
        row, col = find_location_in_source(source, line, col, identifier)
        return [source_path, row, col]
    raise CannotFindIdentifier(
        "could not find {} in here".format(identifier))


def _imports_function(line, identifier):
    return re.match(
        (
            r"^import ((\w(\.\w+)*)+) exposing "
            r"\([\w, ]*"  # zero or more character/space/commas
            r"\b{}\b"  # the thing we're looking for
            r"[\w, ]*\)"  # zero or more other fns
        ).format(identifier),
        line
    )


def _wildcard_import(line):
    return re.match(r"^import (\w+) exposing \(\.\.\)", line)


def _module_name_at_end_of(chopped_line):
    g = re.match(r".*?((\w+\.)*\w+)$", chopped_line).groups()
    return g[0]


def _aliased_module_regex(module_name):
    """
    i curry stuff like this so i can test it
    in isolation
    """
    regular_import = r'^import ({})'.format(module_name)
    aliased = r'^import ([\w.]+) as {}'.format(module_name)
    exposing = r'^import ([\w.]+) exposing \([\w, ]+\) as {}'.format(module_name)  # NOQA
    together = r'|'.join((
        regular_import,
        aliased,
        exposing
    ))
    _r = re.compile(together)

    def f(line):
        m = _r.match(line)
        if m:
            # you only match one of the sub patterns...
            # leap of faith:
            return [i for i in m.groups() if i][0]
        else:
            return m
    return f


def _module_from_alias(source, module_name):
    """
    search the source for the original name of a module
    if it was aliased.  if the module is instead simply found,
    return that.
    """
    regular_or_aliased = _aliased_module_regex(module_name)
    _search = [regular_or_aliased(i) for i in source.split("\n")]
    matches = [i for i in _search if i is not None]
    assert len(matches) == 1, ("only mode module name "
                               "should match '{}', instead "
                               "found: {}".format(module_name, [i.string for i in matches]))  # NOQA
    return matches[0]


def modules_to_search(source, line, col, identifier):
    """
    given the identifier, give list of module names that you should
    search in for the symbol
    """

    # check if identifier is qualified, if it's
    # like "String.join" instead of just "join"
    lines = source.split("\n")
    line_of_id = lines[line]
    try:
        just_before_id = line_of_id[col - 1]
    except IndexError:
        print({
            "line_of_id": line_of_id,
            "line": line,
            "col": col,
            "identifier": identifier
        })
        raise
    if just_before_id == ".":
        until = source.split("\n")[line][:col - 1]
        module = _module_name_at_end_of(until)
        imported_name = _module_from_alias(source, module)
        log.debug("searching qualified import")
        log.debug([imported_name])
        return [imported_name]
    # search for explicit import
    importers = [_imports_function(i, identifier) for i in source.split("\n")]
    modules = [i.groups()[0] for i in importers if i]
    if len(modules) > 0:
        log.debug("searching exposing imports")
        log.debug(modules)
        return modules
    # if nothing obvious is left, do all wildcards
    wild = [_wildcard_import(i) for i in source.split("\n")]
    mods = [i.groups()[0] for i in wild if i]
    log.debug("searching wildcard imports")
    log.debug(mods)
    return mods


def dependencies(package_json):
    packages = package_json['dependencies'].keys()
    return [tuple(p.split("/")) for p in packages]


def modules_of(package_json):
    modules = package_json['exposed-modules']
    return modules


def imported_packages(source):
    import_line_regex = re.compile(r"^import\s+(\w+)")
    import_lines = [import_line_regex.match(i) for i in source.split("\n")]
    return [p.groups()[0] for p in import_lines if p]


def get_package_json(path):
    """
    get elm-package.json as a dict
    """
    with open(os.path.join(path, "elm-package.json")) as p:
        return json.loads(p.read())


def modules_of_this_project():
    """
    """
    with open("./elm-package.json") as p:
        root = json.loads(p.read())
        modules = root["exposed-modules"]
        for author, package in dependencies(root):
            p_path = os.path.join(
                "elm-stuff",
                "packages",
                author,
                package,
            )
            versions = os.listdir(p_path)
            path_to_package_json = os.path.join(
                p_path, versions[0], "elm-package.json"
            )
            with open(path_to_package_json) as dependency:
                modules += modules_of(json.loads(dependency.read()))
        return modules


def dependency_roots(dir):
    package_json = get_package_json(dir)
    roots = []
    for author, package in dependencies(package_json):
        p_path = os.path.join(
            "elm-stuff",
            "packages",
            author,
            package,
        )
        versions = os.listdir(p_path)
        path_to_package = os.path.join(
            p_path, versions[0]
        )
        roots.append(path_to_package)
    return roots


def def_of(path, identifier):
    """
    search for the symbol in the file
    """
    pass


def files_of(module, package_root, depth=1):
    """
    for a given module name, return the path to the file

    problems: i am looking for a module only defined local to
              a project, how do i return a path that makes sense from
              where i am searching.
    """
    package_json = get_package_json(package_root)
    pcomponents = [p for p in module.split(".")]
    package_file = os.path.join(*pcomponents) + ".elm"
    sources = [
        os.path.join(package_root, s)
        for s in package_json["source-directories"]
    ]
    paths = [
        os.path.join(s, package_file)
        for s in sources
        if os.path.exists(os.path.join(s, package_file))
    ]
    if depth > 0:
        # TODO: could probably just do a set() compression at
        #       the end but whatever
        for dep_path in dependency_roots(package_root):
            module_paths = files_of(module, dep_path, depth=depth-1)
            paths += module_paths
    if len(paths) > 1:
        raise RuntimeError("too many matches!!! :((((: {}".format(paths))
    return paths


def _mask_comments(src):

    """
    erase content of comments so they stop matching in my search
    results
    """

    enter_comment_block = "{-"
    exit_comment_block = "-}"
    # enter_comment_line = "--"
    # exit_comment_line = "\n"
    newline = re.compile(r'\n')

    comment_mode = []  # push/pop states, only out of comment mode when empty
    out = []
    for i in range(len(src)):
        # using slice + 2 width to get a sliding window
        this_chunk = src[i:i+2]
        if this_chunk == enter_comment_block:
            comment_mode.append(enter_comment_block)
            out.append(enter_comment_block[0])
            continue
        if this_chunk == exit_comment_block:
            comment_mode.pop()
        # reproduce source
        if len(comment_mode) > 0:
            if newline.match(this_chunk[0]):
                out.append(this_chunk[0])
            else:
                out.append("-")
        else:
            out.append(this_chunk[0])
    return "".join(out)


def arg_parser():
    import argparse
    p = argparse.ArgumentParser(
        description="Find the definition of an elm function"
    )
    p.add_argument("cwd", metavar="CURRENT_DIR", type=str,
                   help="dir of elm project")
    p.add_argument("file", metavar="FILE", type=str,
                   help="path to file function is used in")
    p.add_argument("row", metavar="ROW", type=int)
    p.add_argument("col", metavar="COLUMN", type=int)
    p.add_argument("identifier", metavar="IDENTIFIER", type=str,
                   help="name of thing you're looking for")
    p.add_argument("-d", "--debug", dest="debug",
                   const=True, default=False, action="store_const",
                   help="turn on debug logging")
    return p


def main():
    args = arg_parser().parse_args()
    cwd = args.cwd
    path = args.file
    row = args.row
    col = args.col
    identifier = args.identifier
    debug = args.debug
    level = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(level=level)
    print(" ".join(
        map(str, ["MATCH"] + find_location(cwd, path, row, col, identifier))
    ))


if __name__ == '__main__':
    main()
