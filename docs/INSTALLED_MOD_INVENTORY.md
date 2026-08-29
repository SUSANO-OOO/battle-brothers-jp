# Installed MOD Inventory

Source of truth: actual installed files plus the current read-only runtime log. Machine-readable evidence is `reports/source-snapshot.json`。snapshot IDは`BBJP-CF88150E7B355ECD32D9`。

## Game and DLC

| Component | Detected version/build | Classification |
|---|---:|---|
| Battle Brothers | executable `1.5.2.3`; runtime `vanilla 1.5.2-3`; Steam build `23856902` | `KNOWN_ACTIVE` |
| Lindwurm | `dlc_lindwurm 1.0.0` | `KNOWN_ACTIVE` |
| Beasts & Exploration | `dlc_unhold 1.0.0` | `KNOWN_ACTIVE` |
| Warriors of the North | `dlc_wildmen 1.0.0` | `KNOWN_ACTIVE` |
| Blazing Deserts | `dlc_desert 1.0.0` | `KNOWN_ACTIVE` |
| Of Flesh and Faith | `dlc_paladins 1.0.0` | `KNOWN_ACTIVE` |

Official content archivesは`data_001.dat`, `data_003.dat`, `data_004.dat`, `data_006.dat`, `data_008.dat`, `data_010.dat`。各size/SHA-256はsource-snapshotに固定した。

## Installed MOD archives

| Archive | Size | SHA-256 | Runtime classification |
|---|---:|---|---|
| `mod_legends-19.4.20 60 19.4.20 2026-08-15T12-57Z qTxKH71VJ.zip` | 5,453,255 | `6A1E1482BF909EEC2E0ECE70C3992BA80FAB5A948B9CD0625063B1729B002A71` | `KNOWN_ACTIVE` |
| `mod_legends-assets-19.4.3 60 19.4.3 2026-06-26T21-39Z tSEX1vInI.zip` | 357,981,216 | `0B0BADFC70B615828020A69BBE2A085F377F8564EB8390F8C12D62DAFD260C8C` | `KNOWN_ACTIVE` |
| `mod_modern_hooks-685-0-6-0-1748620177.zip` | 25,220 | `18FBF059480A09483693B8EEF9C97C3A32450885B1971DDA49B5CC14A66D7ED1` | `FRAMEWORK` |
| `mod_msu 479 1.9.0 2026-06-23T04-27Z eVJjKbX9c.zip` | 2,453,031 | `617AF64BD4B354408B91F8B8618F94F664491EDCD2CF4649B8AD52673C81B37B` | `FRAMEWORK` |

Runtime logからさらに`mod_hooks 21.1`、Legends同梱`mod_events_delayed_fix_legends 0.7`、`mod_Jimmys_Tooltips_legends 1.0.5`、Legends内部load-order-fix/compat-checkを別登録componentとして確認した。

## Existing Japanese MOD audit

`data`内に日本語化MOD archiveは存在せず、runtime logにも日本語化component登録は無い。loose `data/gfx/fonts`は全ファイルをofficial `data_001.dat`内entryとSHA-256比較し、一致した。したがってcurrent snapshotで既存日本語化MODは`NOT_PRESENT`であり、流用対象も存在しない。

ゲームrootにある`BattleBrothers_Localization_Audit_Collector`は`data`外でruntime MOD登録もないため、`NON_RUNTIME_DIAGNOSTIC / NOT_A_TRANSLATION_SOURCE`とした。その内容を本projectへ流用していない。

## Runtime evidence boundary

current logでは15 component registration、error 0、warning 15、critical 0を観測した。これはユーザーの既存構成の証拠であり、新日本語化MODのruntime QAではない。

scan前後のgame root/user-data path/size/mtime tree digestは一致し、write countは0。
