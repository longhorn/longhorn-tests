---
title: Test Backing Image during Longhorn upgrade
---

1. Deploy an old version Longhorn. Then set `Concurrent Automatic Engine Upgrade Per Node Limit` to a positive value to enable volume engine auto upgrade.
2. Create a backing image.
3. Create and attach volumes with the backing image.
4. Verify the backing image content then write random data in the volumes.
5. Upgrade the whole Longhorn system with a new engine image.
6. Verify the volumes still work fine, and the content is correct in the volumes during/after the upgrade.
