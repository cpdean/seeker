module Main (..) where

import Signal exposing (Signal)
import Console
import Task


console : Console.IO ()
console =
    Console.putStrLn "sup homies"


port runner : Signal (Task.Task x ())
port runner =
    Console.run console
