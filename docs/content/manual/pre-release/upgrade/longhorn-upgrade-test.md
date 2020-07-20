---
title: Longhorn Upgrade test
---
### Setup
1. 2 attached volumes with data. 2 detached volumes with data. 2 new volumes without data.
2. 2 deployments of one pod. 1 statefulset of 10 pods.
3. `Auto Salvage` set to disable.
### Test
After upgrade:
1. Make sure the existing instance managers didn't restart.
1. Make sure pods didn't restart.
1. Check the contents of the volumes.
1. If the Engine API version is incompatible, manager cannot do anything about the attached volumes except detaching it.
1. If the Engine API version is incompatible, manager cannot live-upgrade the attached volumes.
1. If the Engine API version is incompatible, manager cannot reattach an existing volume until the user has upgraded the engine image to a manager supported version.
1. After offline or online (live) engine upgrade, check the contents of the volumes are valid.
1. For the volume never been attached in the old version, check it's attachable after the upgrade.
