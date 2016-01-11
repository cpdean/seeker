module Seeker (tests) where

{-| Immutable Persistent Data Structures

@docs tests
-}

import ElmTest
import Native.Core
import List
import String


wordCount : String -> Int
wordCount s =
    List.length (words s)


words : String -> List String
words s =
    String.split " " s


{-| functional tests for the top level module
-}
tests : ElmTest.Test
tests =
    ElmTest.suite
        "stub"
        [ ElmTest.test "one" (ElmTest.assertEqual 1 1)
        , ElmTest.test "lol" (ElmTest.assertEqual 3 (Native.Core.addOne 2))
        ]
