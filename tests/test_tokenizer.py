import seeker
import pytest

regular = """
import List
import String

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = String.join "." (splitter input)
"""


def test_tokens_wow():
    assert type(regular) == str


def test_find_origin():
    location = seeker.find_location(regular, 8, 27, "splitter")
    assert location == (5, 0)


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
        location = seeker.find_location(too_many, 10, 27, "splitter")
        assert location == (5, 0)


missing = """
import List
import String

b : String -> String
b input = String.join "." (splitter input)
"""


def test_simple_missing():
    with pytest.raises(seeker.CannotFindIdentifier):
        location = seeker.find_location(missing, 4, 27, "splitter")
        assert location == (5, 0)
