"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
var vm = require("vm");

var calls = [];
var jquery = function (selector, context) {
    return new jquery.fn.init(selector, context);
};
jquery.fn = {
    init: function () {
        calls.push({ method: "init", receiver: this, args: Array.prototype.slice.call(arguments) });
        return this;
    },
    createTextButton: function () {
        calls.push({ method: "button", receiver: this, args: Array.prototype.slice.call(arguments) });
        return "button-result";
    },
    createDialog: function () {
        calls.push({ method: "dialog", receiver: this, args: Array.prototype.slice.call(arguments) });
        return "dialog-result";
    },
    createPopupDialog: function () {
        calls.push({ method: "popup", receiver: this, args: Array.prototype.slice.call(arguments) });
        return "popup-result";
    },
    html: function () {
        calls.push({ method: "html", receiver: this, args: Array.prototype.slice.call(arguments) });
        return "html-result";
    },
    text: function () {
        calls.push({ method: "text", receiver: this, args: Array.prototype.slice.call(arguments) });
        return "text-result";
    },
    append: function () {
        calls.push({ method: "append", receiver: this, args: Array.prototype.slice.call(arguments) });
        return "append-result";
    }
};
jquery.fn.init.prototype = jquery.fn;

var windowObject = {};
var context = {
    jQuery: jquery,
    window: windowObject,
    Object: Object,
    Array: Array
};
var sourcePath = path.resolve(__dirname, "../../src/ui/mods/mod_battle_brothers_jp/main.js");
var stringsPath = path.resolve(__dirname, "../../src/ui/mods/mod_battle_brothers_jp/generated_strings.js");
vm.runInNewContext(fs.readFileSync(stringsPath, "utf8"), context, { filename: stringsPath });
vm.runInNewContext(fs.readFileSync(sourcePath, "utf8"), context, { filename: sourcePath });

var receiver = { id: "control" };
var callback = function () {};
assert.strictEqual(jquery.fn.createTextButton.call(receiver, "New Campaign", callback), "button-result");
assert.strictEqual(calls[0].args[0], "新しい戦役");
assert.strictEqual(calls[0].args[1], callback);
assert.strictEqual(calls[0].receiver, receiver);

assert.strictEqual(jquery.fn.createDialog.call(receiver, "Options", "Unknown subtitle"), "dialog-result");
assert.strictEqual(calls[1].args[0], "設定");
assert.strictEqual(calls[1].args[1], "Unknown subtitle");

assert.strictEqual(jquery.fn.createPopupDialog.call(receiver, "Retire", "Unknown subtitle"), "popup-result");
assert.strictEqual(calls[2].args[0], "引退");
assert.strictEqual(calls[2].args[1], "Unknown subtitle");
assert.strictEqual(calls[2].receiver, receiver);

assert.strictEqual(jquery.fn.html.call(receiver, "Scenarios"), "html-result");
assert.strictEqual(calls[3].args[0], "シナリオ");
assert.strictEqual(jquery.fn.text.call(receiver), "text-result");
assert.strictEqual(calls[4].args.length, 0);
assert.strictEqual(jquery.fn.append.call(receiver, { nodeType: 1 }), "append-result");
assert.strictEqual(calls[5].args[0].nodeType, 1);

var constructed = jquery('<div class="title title-font-big font-color-title">Ironman Mode</div>');
assert.strictEqual(calls[6].method, "init");
assert.strictEqual(calls[6].args[0], '<div class="title title-font-big font-color-title">アイアンマンモード</div>');
assert.strictEqual(Object.getPrototypeOf(constructed), jquery.fn);

assert.strictEqual(windowObject.BattleBrothersJP.translate("Retreat"), "撤退");
assert.strictEqual(windowObject.BattleBrothersJP.translate("InternalIdentifier"), "InternalIdentifier");

console.log("UI_TRANSLATION_TEST_OK");
