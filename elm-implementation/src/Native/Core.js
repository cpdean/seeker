var make = function make(elm) {
    elm.Native = elm.Native || {};
    elm.Native.Core = elm.Native.Core || {};

    if (elm.Native.Core.values) return elm.Native.Core.values;


    return {
        addOne: function addOne(n){ return n + 1; },
        addTwo: function addTwo(n){ return n + 2; }
    };
};

Elm.Native.Core = {};
Elm.Native.Core.make = make;
