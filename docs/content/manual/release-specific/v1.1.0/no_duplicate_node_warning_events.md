---
title: Test no duplicate node warning events
---

1. Deploy Longhorn.
2. Reboot one node.
3. Get node events with:
```
kubectl get events -n longhorn-system | grep node
```
4. Make sure no duplicate node warning events.
5. Repeat test from step 2 with shutdown a node, and follow step 3 and 4. Makure sure no dplicate node warning events and Longhorn logs look good.
