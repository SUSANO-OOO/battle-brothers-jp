# Compatibility Matrix

Target snapshot: `BBJP-CF88150E7B355ECD32D9`

| Component | Public status | JP requirement | Translation behavior |
|---|---|---|---|
| Vanilla `1.5.2-3` | `VERIFIED_STATIC` | required base game | reviewed Core exact/pattern/display tranche enabled; release coverage is not met |
| Five official DLCs `1.0.0` | `VERIFIED_STATIC` when owned | optional for Vanilla JP | each DLC enabled independently; an unowned DLC does not block startup |
| Legends `19.4.20` | `VERIFIED_STATIC` | optional | reviewed tranche enabled only with its audited Assets/MSU/DLC/framework composition |
| Legends Assets `19.4.3` | `VERIFIED_STATIC` | optional; required by Legends itself | no third-party assets copied |
| MSU `1.9.0` | `VERIFIED_STATIC` | optional | reviewed MSU/Jimmy display module enabled only on exact profile |
| Modern Hooks `0.6.0` | `HARD_DEPENDENCY` | required (`>=0.6.0`) | loader, hooks, JS/CSS registration |
| legacy mod_hooks `21.1` | `UNVERIFIED_COMPATIBLE` for JP Core | optional | namespace preserved; needed by installed Legends composition |
| Events/Ambitions Delayed Fix `0.7` | `VERIFIED_STATIC` bundled Legends component | optional | no independent player-facing scope detected |
| Jimmy's Tooltips `1.0.5` | `VERIFIED_STATIC` bundled Legends component | optional | reviewed UI strings through conditional MSU/Legends boundaries |
| Rosetta `0.5.0` | `UNVERIFIED_COMPATIBLE` when used by another MOD | not required | JP registers no `::Rosetta`; an active old JP language pack is a known conflict |
| stdlib `>=2.5` | `UNVERIFIED_COMPATIBLE` when used by another MOD | not required | JP registers no `::std` |
| Legends `19.4.21` | `UNSUPPORTED` for current artifact | optional | semantic delta audited; changed/revalidated scope remains English until closed |
| Future/unknown MOD | `UNVERIFIED_MOD` | never auto-required | no runtime source scan or guess translation; unknown text passes through |
| Existing Japanese MOD | `KNOWN_CONFLICT` if active | must be removed by user | new MOD has no hidden dependency on it |

`VERIFIED_STATIC` means repository-owned syntax, contracts, mock composition, source fingerprints, and archive QA passed. It does not mean a real game boot/render/save test was performed. Runtime state remains `NOT_TESTED`.

Different version numbers do not by themselves crash/block the entire JP MOD. Current sensitive partitions require their verified profile; a mismatch disables that partition and preserves original English. The packaged machine-readable contract is `battle_brothers_jp/compatibility.json`.
