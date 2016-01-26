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


def test_type_alias_with_new_line():
    type_def = """
type alias Index =
    { x : Float
    , y : Float
    , radius : Float
    }

b : String -> String
b input = huh Index
"""
    location = seeker.find_location_in_source(type_def, 8, 14, "Index")
    assert location == (1, 0)


@pytest.mark.skipif("todo == True")
def test_type_with_new_line():
    """
    current bug, not sure how to get around it given it searches things
    linewise...
    maybe i need to write a mini-parser to filter things expressionwise?
    """
    type_def = """
type Boolean
    = Literal Bool
    | Not Boolean
    | And Boolean Boolean
    | Or Boolean Boolean

b : String -> String
b input = huh Boolean
"""
    location = seeker.find_location_in_source(type_def, 8, 14, "Boolean")
    assert location == (1, 0)


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
def test_non_matches_dont_match(line):
    """
    had a bad regex that was overmatching, so test that some things
    do not match
    """
    identifier = "wowgoats"
    match = seeker._id_regex_from(identifier)(line)
    assert bool(match) is False


def test_type_alias_matches():
    line = 'type alias Index doc = Model.Index doc'
    identifier = "Index"
    match = seeker._id_regex_from(identifier)(line)
    assert bool(match) is True


def test_type_matches():
    line = 'type Index doc = Model.Index doc'
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
    print(match.groups())
    importer = match.groups()[0]
    assert importer == "String"


@pytest.mark.parametrize(
    "line,module",
    [
        ("import Graphics exposing (show)", "Graphics"),
        ("import Graphics.Element exposing (show)", "Graphics.Element"),
        ("import Graphics.Element.More exposing (show)", "Graphics.Element.More"),  # NOQA
        ("import Graphics.Element exposing (Element, show)", "Graphics.Element"),  # NOQA
        ("import Graphics.Element exposing (show, Element)", "Graphics.Element"),  # NOQA
        ("import Graphics.Element exposing (show, Element, blah)", "Graphics.Element"),  # NOQA
    ])
def test_import_finder_matches_nested_module(line, module):
    fn = "show"
    match = seeker._imports_function(line, fn)
    importer = match.groups()[0]
    assert importer == module


@pytest.mark.parametrize(
    "line,module",
    [
        ("import Html exposing (..)", "Html"),
        ("import Html.Events exposing (..)", "Html.Events"),
        ("import Html.Attributes exposing (..)", "Html.Attributes"),
        ("import Html.Attributes.More exposing (..)", "Html.Attributes.More"),
        ("import Html.Attributes.M exposing (..)", "Html.Attributes.M"),
    ])
def test_wildcard_importer_nested_mod(line, module):
    match = seeker._wildcard_import(line)
    importer = match.groups()[0]
    assert importer == module


def test_importer_finder_doesnt_match_substr():
    line = "import Wumpus exposing (ajoinb)"
    fn = "join"
    match = seeker._imports_function(line, fn)
    assert match is None


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


def test_function_is_qualified():
    assert seeker._qualified_namespace(aliased, 8, 15, "join") == ["String"]


@pytest.mark.parametrize(
    "chopped,expected", [
        ("regular name String", "String"),
        ("nested ElmTest.Assertion", "ElmTest.Assertion"),
        ("double nest SomethingElse.ElmTest.Assertion", "SomethingElse.ElmTest.Assertion")  # NOQA
    ])
def test_name_getter(chopped, expected):
    assert seeker._module_name_at_end_of(chopped) == expected


@pytest.mark.parametrize(
    "inpath,package",
    [
        ("/Users/conrad/dev/elm-commithero/elm-stuff/packages/evancz/elm-html/4.0.2/src/Html/Events.elm",  # NOQA
         "/Users/conrad/dev/elm-commithero/elm-stuff/packages/evancz/elm-html/4.0.2/elm-package.json"),  # NOQA
    ]
)
def test_package_path_getter(inpath, package):
    assert seeker._elm_package_for(inpath) == package


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


css_regression = """
module RandomGifList (..) where

import Effects exposing (Effects, map, batch, Never)
import Html exposing (..)


-- TODO seeker can't find 'class' or 'style' etc without the explicit imports
-- import Html.Attributes exposing (style, class, value, placeholder, id, href, rel)

import Html.Attributes exposing (..)
import Html.Events exposing (..)
import Json.Decode as Json
import RandomGif

css : String -> Html
css path =
    node "link" [ rel "stylesheet", href path ] []


view : Signal.Address Action -> Model -> Html
view address model =
    div
        [ id "an_app" ]
        [ css "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css"
        , div
            [ class "container" ]
"""  # NOQA


def test_multiple_wildcards_are_matching():
    modules = seeker.modules_to_search(css_regression, 24, 10, "css")
    assert modules == ["Html", "Html.Attributes", "Html.Events"]


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
