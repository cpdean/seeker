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
    qualified_module = _qualified_namespace(source, line, col, identifier)
    if qualified_module:
        paths = _files_of(qualified_module[0], source_path)
        for p in paths:
            log.debug("checking {}".format(p))
            with open(p) as m:
                try:
                    row, col = find_location_in_source(
                        m.read(), line, col, identifier
                    )
                    return [p, row, col]
                except CannotFindIdentifier:
                    log.debug("could not find in {}".format(p))
    try:
        log.debug("looking in the file function is used in")
        row, col = find_location_in_source(source, line, col, identifier)
        return [source_path, row, col]
    except CannotFindIdentifier:
        # TODO: this might be totally redundant
        modules = modules_to_search(source, line, col, identifier)
        for m in modules:
            log.debug("looking for path to {}".format(m))
            paths = _files_of(m, source_path)
            for p in paths:
                log.debug("checking {}".format(p))
                with open(p) as m:
                    try:
                        row, col = find_location_in_source(
                            m.read(), line, col, identifier
                        )
                        return [p, row, col]
                    except CannotFindIdentifier:
                        log.debug("could not find in {}".format(p))
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
    return re.match(r"^import ((\w+\.)*\w+) exposing \(\.\.\)", line)


def _module_name_at_end_of(chopped_line):
    g = re.match(r".*?((\w+\.)*\w+)$", chopped_line).groups()
    return g[0]


def _aliased_module_regex(module_name):
    """
    i curry stuff like this so i can test it
    in isolation
    """
    regular_import = r'^import ({})$'.format(module_name)
    aliased = r'^import ([\w.]+) as {}$'.format(module_name)
    exposing = r'^import ([\w.]+) exposing \([\w, ]+\) as {}$'.format(module_name)  # NOQA
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


def _qualified_namespace(source, line, col, identifier):
    """
    if a given identifier is qualified, trace it to the module which
    was imported
    """
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
        log.debug("found qualified import {}".format(imported_name))
        return [imported_name]


def modules_to_search(source, line, col, identifier):
    """
    given the identifier, give list of module names that you should
    search in for the symbol
    """

    # check if identifier is qualified, if it's
    # like "String.join" instead of just "join"
    qualified_module = _qualified_namespace(source, line, col, identifier)
    if qualified_module:
        return qualified_module
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


def get_package_json(path):
    """
    get elm-package.json as a dict
    """
    with open(os.path.join(path, "elm-package.json")) as p:
        return json.loads(p.read())


def dependency_roots(dir, is_dependency=False):
    log.debug("generating dependencies for {}".format(dir))
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


def _elm_package_for(file_path):
    """
    get the path to the elm-package.json for a given file
    """
    # just troll up the file tree
    parts = file_path.split(os.path.sep)
    for i in list(reversed(range(len(parts))))[:-1]:
        guess_parts = parts[:i] + ["elm-package.json"]
        current_guess = "/" + os.path.join(*guess_parts)
        if os.path.exists(current_guess):
            return current_guess


def _files_of(module, found_in_file):
    """
    :param module:  name of the module to look for
    :param found_in_file: path to the file that imports the module
    :return: path to file that defines the module

    """
    elm_package_path = _elm_package_for(found_in_file)
    sources_to_search = _searchable_sources(elm_package_path)
    return _find_module_definition(module, sources_to_search)


def _searchable_sources(path_to_elm_package_json, is_dependency=False):
    """
    returns a list of the given package's sources and the
    sources of its dependencies.
    """
    # packages_dir = "elm-stuff/packages"
    # is_top_level = packages_dir not in path_to_elm_package_json
    package_root = path_to_elm_package_json.rpartition("elm-package.json")[0]
    with open(path_to_elm_package_json) as p:
        elm_package_info = json.loads(p.read())
    sources = [
        os.path.join(package_root, s)
        for s in elm_package_info["source-directories"]
    ]
    if not is_dependency:
        for dep_path in dependency_roots(package_root, is_dependency=True):
            dep_package_json = os.path.join(dep_path, "elm-package.json")
            dependency_sources = _searchable_sources(
                dep_package_json, is_dependency=True
            )
            log.debug(
                "adding dependency sources: {}".format(dependency_sources)
            )
            sources += dependency_sources
    return sources


def _find_module_definition(module_name, source_dirs):
    """
    look in all the source dirs for the given module by name

    :param module_name: like "Html.Element"
    :param source_dirs: like ["/home/user/code/elm/blah/src"]
    """
    pcomponents = [p for p in module_name.split(".")]
    package_file = os.path.join(*pcomponents) + ".elm"
    paths = []
    for s in source_dirs:
        definition_file = os.path.join(s, package_file)
        log.debug("looking for {} in {}".format(module_name, definition_file))
        if os.path.exists(definition_file):
            paths.append(definition_file)
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
