---
title: ui sanity check
---

1. Access Longhorn UI on `Chrome`, `Firefox` and `Safari` latest/stable version.
1. Check the pages. All the text, form, tables should be proper.
1. Verify all the links at the bottom, they shouldn't be broken and redirects to right pages.
1. Check the setting page, all the settings's text, values should be proper.
1. Create `Backing Image`, `volume`, `pv`, `pvc` and `recurring jobs` using UI.
1. Take `volume snapshot`, create `volume backup`, and `system backup` using UI.
1. Restore `Backup` and `system backup` using UI.
1. Check the `events` on dashboard, they should be normal.
1. Check the logs on the volume detail page, there shouldn't be any error.
1. Check the browser's console, there shouldn't be any error.