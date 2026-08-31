::MSUCalls <- {Element = 0, Title = 0, Page = 0, Panel = 0};
::PageOriginal <- {
    name = "Settings",
    settings = [
        {name = "Slider", labels = ["Low", "High"], value = 5},
        {name = "No labels", value = 7}
    ]
};
::MSUTooltipFactory <- null;

::MSU <- {
    Class = {
        SettingsElement = {
            getUIData = function (_flags = []) { ::MSUCalls.Element += 1; return {name = "Element"}; }
        },
        SettingsTitle = {
            getUIData = function (_flags = []) { ::MSUCalls.Title += 1; return {name = "Title"}; }
        },
        SettingsPage = {
            getUIData = function (_flags = []) { ::MSUCalls.Page += 1; return ::PageOriginal; }
        },
        SettingsPanel = {
            getUIData = function (_flags = []) { ::MSUCalls.Panel += 1; return {name = "Panel"}; }
        }
    }
};

::BattleBrothersJP <- {
    Mod = {
        hook = function (_target, _callback) {
            local q = {
                onQueryMSUTooltipData = null
                contains = function (_name) { return _name in this; }
            };
            _callback(q);
            ::MSUTooltipFactory = q.onQueryMSUTooltipData;
        }
    }
    Runtime = {
        ThrowOn = null,
        translate = function (_value) {
            if (_value == this.ThrowOn) throw "JP_FAILURE";
            local pairs = {
                Settings = "設定", Element = "要素", Title = "見出し", Panel = "パネル",
                Low = "低", High = "高", ["Mod Settings"] = "MOD設定"
            };
            return typeof _value == "string" && _value in pairs ? pairs[_value] : _value;
        }
    }
};

dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/msu_display_boundaries.nut", true);
local firstPageWrapper = ::MSU.Class.SettingsPage.getUIData;
dofile(getenv("BBJP_ROOT") + "src/battle_brothers_jp/hooks/msu_display_boundaries.nut", true);
if (::MSU.Class.SettingsPage.getUIData != firstPageWrapper) throw "MSU boundary initialized twice";

function assertEqual(_actual, _expected, _label)
{
    if (_actual != _expected) throw _label + " expected '" + _expected + "', got '" + _actual + "'";
}

local page = ::MSU.Class.SettingsPage.getUIData();
assertEqual(page.name, "設定", "page name");
assertEqual(page.settings[0].labels[0], "低", "first label");
assertEqual(page.settings[0].labels[1], "高", "second label");
assertEqual(::PageOriginal.name, "Settings", "page source name immutable");
assertEqual(::PageOriginal.settings[0].labels[0], "Low", "page source labels immutable");
if (page == ::PageOriginal || page.settings == ::PageOriginal.settings
    || page.settings[0] == ::PageOriginal.settings[0]
    || page.settings[0].labels == ::PageOriginal.settings[0].labels)
    throw "MSU page projection was not cloned";
assertEqual(::MSUCalls.Page, 1, "page original once");

assertEqual(::MSU.Class.SettingsElement.getUIData().name, "要素", "element name");
assertEqual(::MSU.Class.SettingsTitle.getUIData().name, "見出し", "title name");
assertEqual(::MSU.Class.SettingsPanel.getUIData().name, "パネル", "panel name");
assertEqual(::MSUCalls.Element, 1, "element original once");
assertEqual(::MSUCalls.Title, 1, "title original once");
assertEqual(::MSUCalls.Panel, 1, "panel original once");

local tooltipOriginal = [{id = 1, text = "Mod Settings"}, {id = 2, text = "Unknown"}];
local tooltipCalls = 0;
local tooltip = ::MSUTooltipFactory(function (_id) {
    tooltipCalls += 1;
    return tooltipOriginal;
});
local tooltipResult = tooltip("settings");
assertEqual(tooltipResult[0].text, "MOD設定", "MSU tooltip text");
assertEqual(tooltipOriginal[0].text, "Mod Settings", "MSU tooltip source immutable");
if (tooltipResult == tooltipOriginal || tooltipResult[0] == tooltipOriginal[0])
    throw "MSU tooltip projection was not cloned";
assertEqual(tooltipCalls, 1, "MSU tooltip original once");

::BattleBrothersJP.Runtime.ThrowOn = "Settings";
local failed = ::MSU.Class.SettingsPage.getUIData();
if (failed != ::PageOriginal) throw "MSU JP failure did not return original reference";
assertEqual(::MSUCalls.Page, 2, "MSU JP failure original once");

::BattleBrothersJP.Runtime.ThrowOn = "Mod Settings";
local failedTooltip = tooltip("settings");
if (failedTooltip != tooltipOriginal) throw "MSU tooltip JP failure did not return original reference";
assertEqual(tooltipCalls, 2, "MSU tooltip JP failure original once");

print("MSU_DISPLAY_BOUNDARIES_TEST_OK\n");
