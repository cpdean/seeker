module Main (..) where

import Signal exposing (Signal)
import Console exposing ((>>>))
import Task exposing (andThen)
import Node.Process as Process
import Node.File as File
import Node.Path as Path
import Node.Url as Url
import Node.Console
import String exposing (join)
import Json.Encode as Encode
import Json.Decode as Decode


withError : Task.Task x a -> y -> Task.Task y a
withError task error =
    Task.mapError (\_ -> error) task


loadDeps : Task.Task String String
loadDeps =
    File.read (Path.resolve [ "elm-stuff", "exact-dependencies.json" ])
        `withError` "Dependencies file is missing. Perhaps you need to run `elm-package install`?"


loadSource : String -> Task.Task String String
loadSource path =
    File.read (Path.normalize path)
        `withError` ("Could not find the give source file: " ++ path)


type alias DocPaths =
    List { local : String, network : String }


parseDeps : String -> Result String DocPaths
parseDeps json =
    let
        deps = Decode.decodeString (Decode.keyValuePairs Decode.string) json

        buildDocPath ( name, version ) =
            let
                docFile = "documentation.json"

                local = Path.resolve [ "elm-stuff", "packages", name, version, docFile ]

                network = Url.join [ "http://package.elm-lang.org", "packages", name, version, docFile ]
            in
                { local = local, network = network }
    in
        case deps of
            Ok packages ->
                Ok <| List.map buildDocPath packages

            Err _ ->
                Err "Could not decode the dependencies file."


console : Console.IO ()
console =
    let
        guys = join " " Process.args

        out = join " " [ "sup:", guys, "end." ]
    in
        Console.putStrLn out



--port runner : Task.Task String ()
--port runner =
--loadSource "README.md" `andThen` (\s -> Node.Console.log s)


port runner : Task.Task String ()
port runner =
    let
        one = Node.Console.log "fuck you"
    in
        Process.exit 0



--port runner : Signal (Task.Task x ())
--port runner =
--Console.run console
