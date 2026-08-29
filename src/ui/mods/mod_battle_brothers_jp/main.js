/* Battle Brothers Integrated Japanese Localization - JS/UI Vertical Slice */
(function ($) {
    "use strict";

    var strings = window.BattleBrothersJPStrings || {};

    function translate(value) {
        return typeof value === "string" && Object.prototype.hasOwnProperty.call(strings, value)
            ? strings[value]
            : value;
    }

    window.BattleBrothersJP = window.BattleBrothersJP || {};
    window.BattleBrothersJP.translate = translate;

    function translateFirstArgument(method) {
        var original = $.fn[method];
        if (typeof original !== "function") {
            return;
        }
        $.fn[method] = function () {
            var args = Array.prototype.slice.call(arguments);
            if (args.length > 0) {
                args[0] = translate(args[0]);
            }
            return original.apply(this, args);
        };
    }

    var originalCreateTextButton = $.fn.createTextButton;
    $.fn.createTextButton = function () {
        var args = Array.prototype.slice.call(arguments);
        args[0] = translate(args[0]);
        return originalCreateTextButton.apply(this, args);
    };

    var originalCreateDialog = $.fn.createDialog;
    $.fn.createDialog = function () {
        var args = Array.prototype.slice.call(arguments);
        args[0] = translate(args[0]);
        args[1] = translate(args[1]);
        return originalCreateDialog.apply(this, args);
    };

    var originalCreatePopupDialog = $.fn.createPopupDialog;
    $.fn.createPopupDialog = function () {
        var args = Array.prototype.slice.call(arguments);
        args[0] = translate(args[0]);
        args[1] = translate(args[1]);
        return originalCreatePopupDialog.apply(this, args);
    };

    // Exact-string display boundaries used by Vanilla, Legends, and MSU.
    // Getter calls and non-string values pass through unchanged.
    translateFirstArgument("html");
    translateFirstArgument("text");
    translateFirstArgument("append");

    // jQuery HTML constructor calls, e.g. $("<div>Visible label</div>"), do
    // not pass through $.fn.html(). Translate only exact reviewed strings.
    var originalInit = $.fn.init;
    if (typeof originalInit === "function") {
        $.fn.init = function () {
            var args = Array.prototype.slice.call(arguments);
            if (args.length > 0) {
                args[0] = translate(args[0]);
            }
            return originalInit.apply(this, args);
        };
        $.fn.init.prototype = $.fn;
    }
}(jQuery));
