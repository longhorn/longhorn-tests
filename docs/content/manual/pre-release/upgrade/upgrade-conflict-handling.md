### New installation:
1. create a large cluster of many nodes (about 30 nodes)
1. Install Longhorn `master`

### Upgrading from old version:
1. create a large cluster of many nodes (about 30 nodes)
1. Install Longhorn v1.0.0
1. Upgrade Longhorn to `master`

**Success if:** install/upgrade successfully after maximum 15 minutes. 

**Fail if:** The upgrading is blocked after about 17-20 managers are up.

**Note:** This is a race condition, so we need to try multiple times to validate the fix.
