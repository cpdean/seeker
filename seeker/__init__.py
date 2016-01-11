from __future__ import print_function
import os
import re
import json


class CannotFindIdentifier(Exception):
    pass


class SearchError(Exception):
    pass


def find_location_in_source(source, line, col, identifier):
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


def find_location(path, source_path, line, col, identifier):
    """
    source is path to file
    """
    with open(source_path) as s:
        source = s.read()
    try:
        return find_location_in_source(source, line, col, identifier)
    except CannotFindIdentifier:
        print("could not find in {}".format(source_path))
        for m in modules_to_search(source, line, col, identifier):
            paths = files_of(m, path)
            for p in paths:
                with open(p) as m:
                    try:
                        return find_location_in_source(
                            m.read(), line, col, identifier
                        )
                    except CannotFindIdentifier:
                        print("could not find in {}".format(p))
    # well you got this far...
    raise CannotFindIdentifier("sorry")


def _imports_function(line, identifier):
    return re.match(
        (
            r"^import (\w+) exposing "
            r"\([\w, ]*"  # zero or more character/space/commas
            r"\b{}\b"  # the thing we're looking for
            r"[\w, ]*\)"  # zero or more other fns
        ).format(identifier),
        line
    )


def _wildcard_import(line):
    return re.match(r"^import (\w+) exposing \(\.\.\)", line)


def modules_to_search(source, line, col, identifier):
    """
    given the identifier, give list of module names that you should
    search in for the symbol
    """
    """
    source = exposing
    line = 8
    col = 10
    identifier = 'join'
    """

    # check if identifier is qualified, if it's
    # like "String.join" instead of just "join"
    if source.split("\n")[line][col - 1] == ".":
        until = source.split("\n")[line][:col - 1]
        module = re.match(r"^.*?(\w*)$", until).groups()[0]
        return [module]
    # search for explicit import
    importers = [_imports_function(i, identifier) for i in source.split("\n")]
    modules = [i.groups()[0] for i in importers if i]
    if len(modules) > 0:
        return modules
    # if nothing obvious is left, do all wildcards
    wild = [_wildcard_import(i) for i in source.split("\n")]
    return [i.groups()[0] for i in wild if i]


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


def main():
    path = "src/Seeker.elm"
    print(find_location(".", path, 17, 18, "test"))


if __name__ == '__main__':
    main()
