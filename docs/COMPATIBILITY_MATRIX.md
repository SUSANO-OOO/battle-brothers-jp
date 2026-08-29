# Compatibility Matrix

Target snapshot: `BBJP-CF88150E7B355ECD32D9`

| Component | State | Translation scope | Compatibility action |
|---|---|---|---|
| Vanilla `1.5.2-3` | `KNOWN_ACTIVE` | Full player-facing Squirrel + JS/UI | exact source pin; Rosetta + JS overlay |
| Five official DLCs `1.0.0` | `KNOWN_ACTIVE` | Full player-facing content | included in Vanilla ledger; required transitively by Legends |
| Legends `19.4.20` | `KNOWN_ACTIVE` | Full player-facing Squirrel + custom JS/UI | exact source pin; load translation after Legends registration |
| Legends Assets `19.4.3` | `KNOWN_ACTIVE` | friendly name only; remaining archive is resource content | exact dependency pin; no asset copying |
| MSU `1.9.0` | `FRAMEWORK` | player-facing settings/registry UI; internal diagnostics excluded with reasons | Rosetta MSU boundary + JS audit |
| Modern Hooks `0.6.0` | `FRAMEWORK` | player-visible framework errors only; IDs/debug/internal copy excluded | minimum version; JS/CSS registration provider |
| mod_hooks `21.1` | `FRAMEWORK` | no independent content module | consumed by bundled compatibility code |
| Events/Ambitions Delayed Fix `0.7` | `KNOWN_ACTIVE_BUNDLED` | no new player-facing copy detected beyond hooked Vanilla flow | retain graph edge; no gameplay hook copied |
| Jimmy's Tooltips `1.0.5` | `KNOWN_ACTIVE_BUNDLED` | setting labels/tooltips | translate through Rosetta/MSU path |
| Legends load-order-fix / compat-check `19.4.20` | `KNOWN_ACTIVE_INTERNAL` | no standalone player copy | preserve queue graph; no localization hook |
| Existing Japanese MOD | `KNOWN_INACTIVE / NOT_PRESENT` | none | new MOD has no hidden dependency |
| Rosetta `0.5.0` | `PROPOSED_DEPENDENCY_NOT_INSTALLED` | Squirrel translation runtime | required for RC architecture; needs stdlib `>=2.5` |
| stdlib `>=2.5` | `TRANSITIVE_DEPENDENCY_NOT_INSTALLED` | no translation content | external dependency of Rosetta |
| Future added MOD | `LOAD_STATE_UNKNOWN` until scan | none until dependency audit | graph first, extraction second |

`data` presence aloneではactive判定していない。runtime registrationがあるものだけを`KNOWN_ACTIVE`/`FRAMEWORK`とし、projectでまだ導入されていないdependencyは明確に`NOT_INSTALLED`とした。
