---
title: Test instance manager cleanup during uninstall
---

1. Deploy Longhorn v1.1.2
2. Launch some running volumes.
3. Upgrade to v1.1.3. ==> All old unused engine managers should be cleaned up automatically.
4. Make sure all running volumes keep state `running`.
5. Upgrade all volumes. ==> All old replica managers should be cleaned up automatically.
6. Detach all running volumes. ==> All old engine managers should be cleaned up automatically.
7. do offline upgrade then reattach these volumes.
8. Directly uninstall the Longhorn system.
   And use `kubectl -n longhorn-system get lhim -w` to verify that the system doesn't loop in instance manager cleanup-recreation.
   ==> The uninstaller should work fine.
