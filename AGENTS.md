# Project execution rules

This repository is only for the independent Battle Brothers comprehensive Japanese localization MOD described in `docs/MASTER_DIRECTIVE.md`.

## Non-negotiable boundaries

- Treat the installed Battle Brothers directory, its `data` directory, all game and MOD archives, user configuration, logs, profiles, saves, and Battle Brothers user-data as strictly read-only.
- Never install the generated MOD into the user's real game directory. Never rename, move, disable, delete, replace, patch, or repackage anything there.
- Copy required analysis material only into ignored paths under `work/`.
- Do not commit proprietary game source, game assets, full decompiled source, third-party MOD archives, existing Japanese MOD material, or unlicensed fonts/assets.
- Do not depend on or copy text, code, fonts, or assets from an existing Japanese localization without explicit permission.
- Localization hooks must not change gameplay, balance, AI, probabilities, stats, save semantics, or load order beyond the minimum ordering required for localization.
- Do not report an unexecuted test as passing.

## Release discipline

- `PROJECT_STATE.md` is the resumable source of truth and must be updated after material evidence, failures, fixes, and gates.
- The supported snapshot is identified by actual installed file fingerprints, not by web versions.
- A release candidate requires zero unresolved player-facing strings and zero unreviewed drafts for the supported snapshot.
- If a fully isolated runtime cannot guarantee that Documents/config/saves/logs/profile are isolated, stop at `RC_READY / MANUAL_INSTALL_VERIFICATION_REQUIRED`.
