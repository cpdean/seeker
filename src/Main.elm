module Main (..) where

import Signal exposing (Signal)
import Console
import Task
import Node.Process as Process
import String exposing (join)


console : Console.IO ()
console =
    let
        guys = join " " Process.args

        out = join " " [ "sup:", guys, "end." ]
    in
        Console.putStrLn out


port runner : Signal (Task.Task x ())
port runner =
    Console.run console
