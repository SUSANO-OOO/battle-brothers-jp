from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_runtime_translations.py"
SPEC = importlib.util.spec_from_file_location("generate_runtime_translations", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeGenerationTests(unittest.TestCase):
    def test_only_reviewed_literals_are_emitted(self) -> None:
        ledger = {
            "entries": [
                {"stable_key": "v", "module": "vanilla", "channel": "squirrel"},
                {"stable_key": "j", "module": "vanilla_ui", "channel": "javascript"},
                {"stable_key": "p", "module": "vanilla", "channel": "squirrel"},
            ]
        }
        units = {
            "units": [
                {"translation_unit": "literal", "english": "Save", "japanese": "保存", "mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["v", "j"]},
                {"translation_unit": "pattern", "english": "<raw.Expression> hits", "japanese": "<raw.Expression>が命中", "mode": "pattern", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["p"]},
                {"translation_unit": "draft", "english": "Draft", "japanese": "草稿", "mode": "literal", "status": "TRANSLATED", "review_status": "DRAFT_INDEPENDENT_REVIEW_REQUIRED", "occurrences": ["v"]},
            ]
        }
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel["vanilla"], [{"en": "Save", "ja": "保存"}])
        self.assertEqual(javascript, {"Save": "保存"})
        self.assertEqual(emitted, ["literal"])
        self.assertEqual(pending, ["pattern"])
        self.assertEqual(boundary, [])

    def test_boundary_hook_strategy_is_not_emitted_as_global_literal(self) -> None:
        ledger = {"entries": [{"stable_key": "g", "module": "vanilla", "channel": "squirrel"}]}
        units = {"units": [{"translation_unit": "general-title", "english": "General", "japanese": "将軍", "mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["g"], "runtime_strategy": "BOUNDARY_HOOK"}]}
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {})
        self.assertEqual(javascript, {})
        self.assertEqual(emitted, [])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, ["general-title"])

    def test_actor_title_display_strategy_uses_registry_not_global_literal(self) -> None:
        ledger = {
            "entries": [
                {
                    "stable_key": "w",
                    "module": "vanilla",
                    "channel": "squirrel",
                    "source": "scripts/events/events/fisherman_vs_farmer_event.nut",
                    "context": "fisherman_vs_farmer_event.start.titles",
                }
            ]
        }
        units = {
            "units": [
                {
                    "translation_unit": "weeds",
                    "english": "Weeds",
                    "japanese": "雑草",
                    "mode": "literal",
                    "status": "TRANSLATED",
                    "review_status": "REVIEWED",
                    "occurrences": ["w"],
                    "runtime_strategy": "ACTOR_TITLE_DISPLAY_FRAGMENT",
                }
            ]
        }
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {})
        self.assertEqual(javascript, {})
        self.assertEqual(emitted, ["weeds"])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, [])
        fragments, fragment_units = MODULE.reviewed_actor_title_fragments(units, ledger)
        self.assertEqual(fragments, {"Weeds": "雑草"})
        self.assertEqual(fragment_units, ["weeds"])
        generic_fragments, generic_units = MODULE.reviewed_generic_actor_title_fragments(units, ledger)
        self.assertEqual(generic_fragments, {"Weeds": "雑草"})
        self.assertEqual(generic_units, ["weeds"])

    def test_literal_source_can_emit_only_an_anchored_final_display_pattern(self) -> None:
        ledger = {"entries": [{"stable_key": "d", "module": "legends", "channel": "squirrel"}]}
        units = {"units": [{
            "translation_unit": "dame-title",
            "english": "Dame",
            "japanese": "デイム",
            "mode": "literal",
            "status": "TRANSLATED",
            "review_status": "REVIEWED",
            "occurrences": ["d"],
            "runtime_strategy": "ROSETTA_PATTERN",
            "runtime_contract": {
                "strategy": "ROSETTA_PATTERN",
                "resolution_status": "RESOLVED",
                "runtime_en": "Dame <first:word><rest:str>",
                "runtime_ja": "デイム・<first><rest>",
                "samples": [{"english": "Dame Roderick", "japanese": "デイム・Roderick"}],
            },
        }]}
        squirrel, javascript, emitted, pending, boundary = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {})
        self.assertEqual(javascript, {})
        self.assertEqual(emitted, [])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, [])
        patterns, emitted, pending, boundary, samples = MODULE.reviewed_pattern_units(units, ledger)
        self.assertEqual(patterns["legends"], [{"en": "Dame <first:word><rest:str>", "ja": "デイム・<first><rest>", "mode": "pattern"}])
        self.assertEqual(emitted, ["dame-title"])
        self.assertEqual(pending, [])
        self.assertEqual(boundary, [])
        self.assertEqual(samples, [{"translation_unit": "dame-title", "english": "Dame Roderick", "japanese": "デイム・Roderick"}])

    def test_literal_source_captureless_runtime_rule_is_rejected(self) -> None:
        ledger = {"entries": [{"stable_key": "d", "module": "legends", "channel": "squirrel"}]}
        units = {"units": [{
            "translation_unit": "dame-title",
            "english": "Dame",
            "japanese": "デイム",
            "mode": "literal",
            "status": "TRANSLATED",
            "review_status": "REVIEWED",
            "occurrences": ["d"],
            "runtime_strategy": "ROSETTA_PATTERN",
            "runtime_contract": {
                "strategy": "ROSETTA_PATTERN",
                "resolution_status": "RESOLVED",
                "runtime_en": "Dame",
                "runtime_ja": "デイム",
                "samples": [{"english": "Dame", "japanese": "デイム"}],
            },
        }]}
        with self.assertRaisesRegex(ValueError, "at least one capture"):
            MODULE.reviewed_pattern_units(units, ledger)

    def test_cross_module_squirrel_literal_is_registered_once(self) -> None:
        ledger = {"entries": [
            {"stable_key": "v", "module": "vanilla", "channel": "squirrel"},
            {"stable_key": "l", "module": "legends", "channel": "squirrel"},
        ]}
        units = {"units": [{"translation_unit": "shared", "english": "Retreat", "japanese": "撤退", "mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED", "occurrences": ["v", "l"]}]}
        squirrel, _, emitted, _, _ = MODULE.reviewed_literal_units(units, ledger)
        self.assertEqual(squirrel, {"vanilla": [{"en": "Retreat", "ja": "撤退"}]})
        self.assertEqual(emitted, ["shared"])

    def test_squirrel_quoting_is_json_compatible(self) -> None:
        self.assertEqual(MODULE.quoted('A "quoted" line\n'), '"A \\"quoted\\" line\\n"')

    def test_actor_title_occurrence_uses_source_context_not_english_shape(self) -> None:
        base = {"channel": "squirrel", "module": "legends"}
        positives = [
            {**base, "source": "mod_legends/scripts/skills/backgrounds/legend_adventurous_noble_background.nut", "context": "legend_adventurous_noble_background.m.Titles.[]"},
            {**base, "source": "mod_legends/hooks/events/lone_wolf_event.nut", "context": "lone_wolf_event.m.Dude.setTitle()"},
            {**base, "source": "mod_legends/scripts/entity/tactical/enemies/bandit.nut", "context": "bandit.m.Title"},
            {**base, "source": "mod_legends/scripts/skills/traits/legend_named_trait.nut", "context": "legend_named_trait.m.Title"},
            {**base, "source": "mod_legends/!!config/_global.nut", "context": "::Const.Strings.HedgeKnightTitles.[]"},
        ]
        negatives = [
            {**base, "source": "mod_legends/hooks/events/location_event.nut", "context": "location_event.m.Title"},
            {**base, "source": "mod_legends/scripts/items/legend_named_item.nut", "context": "legend_named_item.m.Title"},
            {**base, "source": "mod_legends/scripts/ui/screens/world/world_screen.nut", "context": "world_screen.m.Title"},
            {**base, "channel": "javascript", "source": "ui/mods/legends/main.js", "context": "titles"},
        ]
        self.assertTrue(all(MODULE.is_actor_title_occurrence(item) for item in positives))
        self.assertFalse(any(MODULE.is_actor_title_occurrence(item) for item in negatives))

    def test_actor_title_registry_contains_only_reviewed_squirrel_titles(self) -> None:
        ledger = {
            "entries": [
                {"stable_key": "titles", "module": "vanilla", "channel": "squirrel", "source": "scripts/skills/backgrounds/hunter_background.nut", "context": "hunter_background.m.Titles.[]"},
                {"stable_key": "setter", "module": "legends", "channel": "squirrel", "source": "mod_legends/hooks/events/lone_wolf_event.nut", "context": "lone_wolf_event.m.Dude.setTitle()"},
                {"stable_key": "event", "module": "legends", "channel": "squirrel", "source": "mod_legends/hooks/events/location_event.nut", "context": "location_event.m.Title"},
                {"stable_key": "js", "module": "vanilla_ui", "channel": "javascript", "source": "ui/screens/world/world_screen.js", "context": "titles"},
                {"stable_key": "draft", "module": "vanilla", "channel": "squirrel", "source": "scripts/entity/tactical/humans/lone_wolf.nut", "context": "lone_wolf.m.Title"},
                {"stable_key": "pattern", "module": "legends", "channel": "squirrel", "source": "mod_legends/scripts/skills/backgrounds/legend_commander_background.nut", "context": "legend_commander_background.m.Titles.[]"},
            ]
        }
        reviewed = {"mode": "literal", "status": "TRANSLATED", "review_status": "REVIEWED"}
        units = {
            "units": [
                {**reviewed, "translation_unit": "hunter", "english": "the Hunter", "japanese": "狩人", "occurrences": ["titles"]},
                {**reviewed, "translation_unit": "squire", "english": "the Squire", "japanese": "従士", "occurrences": ["setter"]},
                {**reviewed, "translation_unit": "approach", "english": "As you approach...", "japanese": "接近すると……", "occurrences": ["event"]},
                {**reviewed, "translation_unit": "js-title", "english": "Title", "japanese": "称号", "occurrences": ["js"]},
                {"translation_unit": "lone-wolf", "english": "The Lone Wolf", "japanese": "一匹狼", "mode": "literal", "status": "TRANSLATED", "review_status": "DRAFT_INDEPENDENT_REVIEW_REQUIRED", "occurrences": ["draft"]},
                {**reviewed, "translation_unit": "dame", "english": "Dame", "japanese": "デイム", "occurrences": ["pattern"], "runtime_strategy": "ROSETTA_PATTERN"},
            ]
        }
        fragments, emitted = MODULE.reviewed_actor_title_fragments(units, ledger)
        self.assertEqual(fragments, {"the Hunter": "狩人", "the Squire": "従士"})
        self.assertEqual(emitted, ["hunter", "squire"])

    def test_actor_title_registry_is_rendered_for_both_runtime_layers(self) -> None:
        titles = {
            "the Holy": "聖なる者",
            "the Holy Avenger": "聖なる復讐者",
            "the Old": "老人",
            "the Old Guard": "古参兵",
            "the Lone Wolf": "一匹狼",
            "the White": "白き者",
            "the White Death": "白き死",
        }
        generic_titles = {"the Old Guard": "古参兵"}
        squirrel = MODULE.render_squirrel({}, titles, generic_titles)
        javascript = MODULE.render_javascript({}, titles, generic_titles)
        self.assertIn("::BattleBrothersJP.ActorTitleDisplayFragments <- [", squirrel)
        self.assertIn('english = "the Lone Wolf"', squirrel)
        self.assertIn('japanese = "一匹狼"', squirrel)
        self.assertIn("window.BattleBrothersJPActorTitleFragments", javascript)
        self.assertIn("window.BattleBrothersJPGenericActorTitleFragments", javascript)
        self.assertIn('"the Lone Wolf": "一匹狼"', javascript)
        self.assertIn("::BattleBrothersJP.ActorTitleGenericDisplayFragments <- [", squirrel)
        self.assertLess(squirrel.index('english = "the Old Guard"'), squirrel.index('english = "the Old"'))
        self.assertLess(javascript.index('"the Old Guard"'), javascript.index('"the Old"'))
        self.assertLess(squirrel.index('english = "the Holy Avenger"'), squirrel.index('english = "the Holy"'))
        self.assertLess(javascript.index('"the Holy Avenger"'), javascript.index('"the Holy"'))
        self.assertLess(squirrel.index('english = "the White Death"'), squirrel.index('english = "the White"'))
        self.assertLess(javascript.index('"the White Death"'), javascript.index('"the White"'))

    def test_regex_equivalent_capture_names_are_rejected(self) -> None:
        ledger = {"entries": [
            {"stable_key": "a", "module": "vanilla", "channel": "squirrel"},
            {"stable_key": "b", "module": "legends", "channel": "squirrel"},
        ]}
        base = {"mode": "pattern", "status": "TRANSLATED", "review_status": "REVIEWED"}
        units = {"units": [
            {**base, "translation_unit": "a", "occurrences": ["a"], "runtime_contract": {
                "resolution_status": "RESOLVED", "strategy": "ROSETTA_PATTERN",
                "runtime_en": "<value:val_tag> Resolve", "runtime_ja": "精神力 <value>", "samples": []}},
            {**base, "translation_unit": "b", "occurrences": ["b"], "runtime_contract": {
                "resolution_status": "RESOLVED", "strategy": "ROSETTA_PATTERN",
                "runtime_en": "<bonus:val_tag> Resolve", "runtime_ja": "精神力 <bonus>", "samples": []}},
        ]}
        with self.assertRaisesRegex(ValueError, "Regex-equivalent"):
            MODULE.reviewed_pattern_units(units, ledger)


if __name__ == "__main__":
    unittest.main()
