import seeker

src = """
import List
import String

splitter : String -> List String
splitter = String.split " "

b : String -> String
b input = String.join "." (splitter input)
"""


def test_tokens_wow():
    assert type(src) == str


def test_find_origin():
    location = seeker.find_location(src, 8, 27, "splitter")
    assert location == (5, 0)
