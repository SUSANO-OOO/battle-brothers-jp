/* Battle Brothers Integrated Japanese Localization - JS/UI Vertical Slice */
(function ($) {
    "use strict";

    var strings = window.BattleBrothersJPStrings || {};
    // The full title registry is reserved for Squirrel fields with proven
    // actor provenance. This global renderer uses only explicit opt-ins so an
    // unknown item/prose suffix cannot be partially rewritten as an actor.
    var actorTitleFragments = window.BattleBrothersJPGenericActorTitleFragments || {};

    function translateReviewedActorName(value) {
        var translated = value;
        var reviewedTitles = Object.keys(actorTitleFragments);
        var beforeBoundaries = [" ", "\n", ">", "]", "(", ":", "\"", "'"];

        reviewedTitles.forEach(function (english) {
            var japanese = actorTitleFragments[english];
            if (typeof japanese !== "string" || japanese === english) {
                return;
            }

            var at = translated.indexOf(english);
            if (at < 0 || translated.indexOf(english, at + english.length) >= 0) {
                return;
            }
            var after = at + english.length;
            var beforeChar = at === 0 ? "" : translated.charAt(at - 1);
            var afterChar = after === translated.length ? "" : translated.charAt(after);
            var beforeOK = at === 0 || beforeBoundaries.indexOf(beforeChar) >= 0;
            // This global fallback is intentionally suffix-only. Actor-specific
            // Squirrel DTO/tooltip boundaries handle embedded names. Restricting
            // JS replacement to an exact final value or an HTML closing tag
            // prevents common titles such as "the Hunter" from rewriting prose.
            var afterOK = after === translated.length || afterChar === "<";
            if (!beforeOK || !afterOK) {
                return;
            }
            translated = translated.slice(0, at) + japanese + translated.slice(after);
        });
        return translated;
    }

    function translate(value) {
        if (typeof value !== "string") {
            return value;
        }
        var exact = Object.prototype.hasOwnProperty.call(strings, value) ? strings[value] : value;
        return translateReviewedActorName(exact);
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
