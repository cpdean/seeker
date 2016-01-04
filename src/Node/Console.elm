module Console (log, error, fatal, stdin) where

{-| Console

@docs log, error, fatal, stdin

-}

import Native.Console
import Task exposing (Task)


{-| Prints to stdout with a newline.
-}
log : a -> Task x ()
log value =
    Native.Console.log value


{-| Prints to stderr with a newline.
-}
error : a -> Task x ()
error value =
    Native.Console.error value


{-| Prints to stderr with a newline, then exits with an error code of 1.
-}
fatal : a -> Task x ()
fatal value =
    Native.Console.fatal value


{-| The current input on stdin. Event triggers on each new line.
-}
stdin : Signal String
stdin =
    Native.Console.stdin
