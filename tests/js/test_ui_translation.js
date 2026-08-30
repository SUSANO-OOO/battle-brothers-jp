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

assert.strictEqual(jquery.fn.html.call(receiver, '<span>Aldric the Lone Wolf</span>'), "html-result");
assert.strictEqual(calls[7].args[0], '<span>Aldric the Lone Wolf</span>');
assert.strictEqual(jquery.fn.text.call(receiver, "Aldric the Lone Wolf"), "text-result");
assert.strictEqual(calls[8].args[0], "Aldric the Lone Wolf");
assert.strictEqual(jquery.fn.append.call(receiver, "Aldric the Lone Wolf's Relic"), "append-result");
assert.strictEqual(calls[9].args[0], "Aldric the Lone Wolf's Relic");
assert.strictEqual(jquery.fn.text.call(receiver, "Wolfgangthe Lone Wolf"), "text-result");
assert.strictEqual(calls[10].args[0], "Wolfgangthe Lone Wolf");
assert.strictEqual(jquery.fn.text.call(receiver, "the Lone Wolf and the Lone Wolf"), "text-result");
assert.strictEqual(calls[11].args[0], "the Lone Wolf and the Lone Wolf");
assert.strictEqual(jquery.fn.text.call(receiver, "Aldric the Lone Wolf has left"), "text-result");
assert.strictEqual(calls[12].args[0], "Aldric the Lone Wolf has left");

assert.strictEqual(windowObject.BattleBrothersJP.translate("Retreat"), "撤退");
assert.strictEqual(windowObject.BattleBrothersJP.translate("InternalIdentifier"), "InternalIdentifier");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Aldric the Lone Wolf"), "Aldric the Lone Wolf");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Killed by the Lone Wolf."), "Killed by the Lone Wolf.");
assert.strictEqual(windowObject.BattleBrothersJPActorTitleFragments["the Lone Wolf"], "一匹狼");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Aldric the Holy Avenger"), "Aldric the Holy Avenger");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Aldric the Old Guard"), "Aldric the Old Guard");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Aldric the White Death"), "Aldric the White Death");
var titleOrder = Object.keys(windowObject.BattleBrothersJPActorTitleFragments);
assert.ok(titleOrder.indexOf("the Holy Avenger") < titleOrder.indexOf("the Holy"));
assert.ok(titleOrder.indexOf("the Old Guard") < titleOrder.indexOf("the Old"));
assert.ok(titleOrder.indexOf("the White Death") < titleOrder.indexOf("the White"));
assert.strictEqual(Object.prototype.hasOwnProperty.call(windowObject.BattleBrothersJPActorTitleFragments, "Dame"), false);
assert.deepStrictEqual(Object.keys(windowObject.BattleBrothersJPGenericActorTitleFragments), ["The Lone Wolf", "Weeds"]);
assert.strictEqual(windowObject.BattleBrothersJP.translate("The Lone Wolf"), "一匹狼");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Aldric The Lone Wolf"), "Aldric 一匹狼");
assert.strictEqual(windowObject.BattleBrothersJP.translate("The Lone Wolf has left"), "The Lone Wolf has left");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Weeds"), "雑草");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Asta Weeds"), "Asta 雑草");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Weeds and Weeds"), "Weeds and Weeds");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Blood Vial of the Holy Mother"), "Blood Vial of the Holy Mother");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Honor and fear of the Old Gods"), "Honor and fear of the Old Gods");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Dame"), "Dame");
assert.strictEqual(windowObject.BattleBrothersJP.translate("Dame Roderick"), "Dame Roderick");

console.log("UI_TRANSLATION_TEST_OK");
