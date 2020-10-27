---
title: Test Engine Crash During Live Upgrade
---

1. Create and attach a volume.
2. Deploy an extra engine image.
3. Send live upgrade request then immediately delete the related engine manager pod/engine process (The new replicas are not in active in this case).
4. Verify the volume will detach then reattach automatically.
5. Verify the upgrade is done during the reattachment. (It actually becomes offline upgrade.)
