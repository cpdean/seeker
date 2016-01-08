module Tests (..) where

import ElmTest exposing (..)
import String
import Seeker exposing (tests)


all : Test
all =
    suite
        "A Test Suite"
        [ test "Addition" (assertEqual (3 + 7) 10)
        , test "String.left" (assertEqual "a" (String.left 1 "abcdefg"))
        , tests
        ]
