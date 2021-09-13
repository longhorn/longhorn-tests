---
title: Upgrade Conflict Handling test
---
### New installation:
1. Create a large cluster of many nodes (about 30 nodes)
2. Install Longhorn `master`
3. Create 100 volumes using volume template claim in statefulSet.
4. Have the backup store configured and create some backups.
5. Set some recurring jobs in the cluster every 1 minute.
6. Observe the setup for 1/2 an hr. Do some operation like attaching detaching the volumes.
7. Verify there is no error in the Longhorn manager.

### Upgrading from old version:
1. Repeat the steps from above test case with Longhorn Prior version.
2. Upgrade Longhorn to `master`.
3. Do some operation like attaching and detaching the volumes.
4. Verify there is no error in the Longhorn manager.

**Success if:** install/upgrade successfully after maximum 15 minutes. 

**Fail if:** The upgrading is blocked after about 17-20 managers are up.
