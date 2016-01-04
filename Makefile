ELMSRC = $(wildcard src/**/*.elm, src/*.elm)
JSSRC = $(wildcard src/**/*.js)
MAIN = src/Main.elm
ELM = elm make
BIN = build/seeker.js


ELMTEST ?= ./node_modules/.bin/elm-test

all: $(BIN)

test: node_modules
	${ELMTEST} src/TestRunner.elm

node_modules:
	npm install

$(BIN): $(ELMSRC) $(JSSRC)
	# i feel like the compiler should just support making something
	# a script
	$(ELM) $(MAIN) --output $(BIN)
	echo "Elm.worker(Elm.Main);" >> $(BIN)

build: $(BIN)

clean:
	rm $(BIN)


.PHONY: test clean
