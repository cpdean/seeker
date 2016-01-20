import seeker
import pytest
import mock
import json

todo = True

regular = """
import List
import String

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = String.join "." (splitter input)
"""


def test_find_origin():
    location = seeker.find_location_in_source(regular, 8, 27, "splitter")
    assert location == (5, 0)


with_argument = """
import List
import String

splitter : String -> List String
splitter s = String.split " " s

b : String -> String
b input = String.join "." (splitter input)
"""


def test_find_when_def_has_arg():
    location = seeker.find_location_in_source(with_argument, 8, 27, "splitter")
    assert location == (5, 0)


@pytest.mark.parametrize(
    "line",
    [
        'splitter = String.split " "',
        'splitter s = String.split " " s',
        'splitter whatabout = String.split " " whatabout',
        'splitter s a = String.split " " s a',
        'splitter more a = String.split " " more a',
        'splitter more a third = String.split " " more a third',
        'splitter {you, can, do, this} = String.split " "',
        'splitter {single} = String.split " "',
    ])
def test_indentifier_searcher(line):
    """
    let's hope this doesn't match on let blocks, lol
    """
    identifier = "splitter"
    match = seeker._id_regex_from(identifier)(line)
    assert bool(match) is True


def test_type_alias_matches():
    line = 'type alias Index doc = Model.Index doc'
    identifier = "Index"
    match = seeker._id_regex_from(identifier)(line)
    assert bool(match) is True


too_many = """
import List
import String

splitter : String -> List String
splitter = String.split " "

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = String.join "." (splitter input)
"""


def test_too_many_should_fail():
    with pytest.raises(seeker.SearchError):
        location = seeker.find_location_in_source(too_many, 10, 27, "splitter")
        assert location == (5, 0)


extra_def_in_comment = """
import List
import String

{-| this def is offset and in a comment:
    splitter : String -> List String
    splitter = String.split " "
-}

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = String.join "." (splitter input)
"""


def test_comment_should_hide_multiple_defs():
    """
    TODO: failing test, the def is both indented and in a comment

    some of elm-lang/core does this to express how things work in their docs
    while i could filter based on how its indented, that doesn't guarantee
    some docs may not do that. if a def is ingored by the compiler in a comment
    it should be ignored in this tool
    """
    location = seeker.find_location_in_source(
        extra_def_in_comment, 10, 27, "splitter"
    )
    assert location == (10, 0)


missing = """
import List
import String

b : String -> String
b input = String.join "." (splitter input)
"""


def test_simple_missing():
    with pytest.raises(seeker.CannotFindIdentifier):
        location = seeker.find_location_in_source(missing, 4, 27, "splitter")
        assert location == (5, 0)


package_json = """
{
    "version": "0.0.1",
    "summary": "datastructures",
    "repository": "https://github.com/user/project.git",
    "license": "MIT",
    "source-directories": [
        "src"
    ],
    "exposed-modules": [
        "Seeker"
    ],
    "native-modules": true,
    "dependencies": {
        "deadfoxygrandpa/elm-test": "3.0.1 <= v < 4.0.0",
        "elm-lang/core": "3.0.0 <= v < 4.0.0",
        "laszlopandy/elm-console": "1.0.3 <= v < 2.0.0"
    },
    "elm-version": "0.16.0 <= v < 0.17.0"
}
"""


def test_get_dependencies_of_project(tmpdir):
    assert sorted(seeker.dependencies(json.loads(package_json))) == [
        ("deadfoxygrandpa", "elm-test"),
        ("elm-lang", "core"),
        ("laszlopandy", "elm-console")
    ]


def test_get_modules_of_package(tmpdir):
    assert seeker.modules_of(json.loads(package_json)) == [
        "Seeker"
    ]


def test_get_imported_packages():
    assert seeker.imported_packages(regular) == ["List", "String"]


def get_file_path_to_module():
    """
    for a given module name in a project, traverse through
    the elm-stuff dir to the file that defines the module.
    """
    pass


qualified = """
import List
import String

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = String.join "." (splitter input)
"""


@pytest.mark.skipif("True")
def test_query_string_when_qualified(monkeypatch):
    m = mock.Mock()
    monkeypatch.setattr(seeker, 'def_of', m)
    seeker.find_location(".", qualified, 8, 17, "join")
    assert m.called


@pytest.mark.skipif("True")
def test_module_lister_works_with_qualified():
    assert seeker.modules_to_search(qualified, 8, 17, "join") == "String"


exposing = """
import List
import String exposing (join)

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = join "." (splitter input)
"""


def test_module_lister_works_with_exposed():
    assert seeker.modules_to_search(exposing, 8, 10, "join") == ["String"]


@pytest.mark.parametrize(
    "line",
    [
        "import String exposing (join)",
        "import String exposing (join, womp)",
        "import String exposing (womp, join, womp)",
        "import String exposing (womp, join)",
    ])
def test_importer_finder(line):
    fn = "join"
    match = seeker._imports_function(line, fn)
    importer, = match.groups()
    assert importer == "String"


def test_importer_finder_doesnt_match_substr():
    line = "import Wumpus exposing (ajoinb)"
    fn = "join"
    match = seeker._imports_function(line, fn)
    assert match is None


@pytest.mark.skipif("True")
def test_query_string_when_exposing_qualified():
    pass


@pytest.mark.parametrize(
    "line,input,expected", [
        ("import String", "String", "String"),
        ("import String as Derp", "Derp", "String"),
        ("import Nested.Module as Derp", "Derp", "Nested.Module"),
        ("import RenameAndExpose exposing (whatever, blah) as Whoa", "Whoa", "RenameAndExpose"),  # NOQA
        ("import RenameAndExpose exposing (single) as Whoa", "Whoa", "RenameAndExpose"),  # NOQA
    ])
def test_module_alias_check(line, input, expected):
    assert seeker._aliased_module_regex(input)(line) == expected


aliased = """
import List
import String as Derp

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = Derp.join "." (splitter input)
"""


def test_module_lister_works_when_module_aliased():
    assert seeker.modules_to_search(aliased, 8, 15, "join") == ["String"]


@pytest.mark.parametrize(
    "chopped,expected", [
        ("regular name String", "String"),
        ("nested ElmTest.Assertion", "ElmTest.Assertion"),
        ("double nest SomethingElse.ElmTest.Assertion", "SomethingElse.ElmTest.Assertion")  # NOQA
    ])
def test_name_getter(chopped, expected):
    assert seeker._module_name_at_end_of(chopped) == expected


@pytest.mark.skipif("todo == True")
def test_module_lister_searches_nested_module():
    """
    example, ElmTest.Assert.assertEqual, should jump in that folder to
    look at that file
    """
    assert False


@pytest.mark.skipif("todo == True")
def test_module_lister_searches_Native_js():
    """
    at worst it should at least give a meaningful error
    """
    assert False


wildcard = """
import List
import String exposing (..)

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = join "." (splitter input)
"""


def test_module_lister_works_with_wildcarded():
    assert seeker.modules_to_search(wildcard, 8, 11, "join") == ["String"]


wildcard2 = """
import List exposing (..)
import String exposing (..)

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = join "." (splitter input)
"""


def test_query_string_when_there_are_two_wildcards():
    modules = seeker.modules_to_search(wildcard2, 8, 10, "join")
    assert modules == ["List", "String"]


def test_mask_comments():
    before = """
    import List exposing (..)
    import String exposing (..)

    {-| these comments should be removed

        splitter : String -> List String
        splitter = String.split " "

    lol
    -}

    splitter : String -> List String
    splitter = String.split " "

    b : String -> String
    b input = join "." (splitter input)
    """

    after = """
    import List exposing (..)
    import String exposing (..)

    {-----------------------------------

----------------------------------------
-----------------------------------

-------
-----}

    splitter : String -> List String
    splitter = String.split " "

    b : String -> String
    b input = join "." (splitter input)
    """
    assert seeker._mask_comments(before) == after


@pytest.mark.parametrize(
    "line", [
        'newWith {indexType, ref, fields, transformFactories, filterFactories} =',  # NOQA
        '      , corpusTokensIndex = Dict.empty'
    ])
def test_regarding_my_current_gripe_none_should_match(line):
    """
    let's hope this doesn't match on let blocks, lol
    """
    identifier = "Index"
    match = seeker._id_regex_from(identifier)(line)
    assert bool(match) is False


def xtest_dunno():
    """
    regression: on this code sample the function def finder is
    overmatching on a bunch of things.

    also looks like i need to do some more testing around
    type and type alias defs
    """
    current_gripe = """
type alias Index doc = Model.Index doc
type alias Config doc = Model.Config doc
type alias SimpleConfig doc = Model.SimpleConfig doc


{-| Create new index.
-}
new : SimpleConfig doc -> Index doc
new simpleConfig  =
    newWith
      (Defaults.getDefaultIndexConfig simpleConfig)


{-| Create new index with control of transformers and filters.
-}
newWith : Config doc -> Index doc
newWith {indexType, ref, fields, transformFactories, filterFactories} =
    Index
      { indexVersion = Defaults.indexVersion
      , indexType = indexType
      , ref = ref
      , fields = fields
      , transformFactories = transformFactories
      , filterFactories = filterFactories

      , transforms = Nothing
      , filters = Nothing
      , corpusTokens = Set.empty
      , corpusTokensIndex = Dict.empty
      , documentStore = Dict.empty
      , tokenStore = Trie.empty
      , idfCache = Dict.empty
      }
    """
    seeker.find_location_in_source(current_gripe, 18, 4, "Index")
