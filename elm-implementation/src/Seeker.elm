module Seeker (tests) where

{-| Immutable Persistent Data Structures

@docs tests
-}

import ElmTest
import Native.Core


{-| functional tests for the top level module
-}
tests : ElmTest.Test
tests =
    ElmTest.suite
        "stub"
        [ ElmTest.test "one" (ElmTest.assertEqual 1 1)
        , ElmTest.test "lol" (ElmTest.assertEqual 3 (Native.Core.addOne 2))
        ]
