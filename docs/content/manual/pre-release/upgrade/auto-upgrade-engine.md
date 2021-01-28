---
title: Automatically Upgrading Longhorn Engine Test
---

### Test basic upgrade
1. Install old Longhorn version. E.g., <= `v1.0.2`
1. Create a volume, attach it to a pod, write some data. Create a DR volume. Create volume and leave it in the detached state.
1. Upgrade to  Longhorn master
1. Set setting `concurrent automatic engine upgrade per node limit` to 3
1. Verify that volumes' engines are upgraded automatically.

### Test concurrent upgrade
1. Create a StatefulSet of scale 10 using 10 Longhorn volume. Set node selector so that all pods land on the same node.
2. Upgrade Longhorn to use a newer default engine image
3. In Longhorn UI and Longhorn manager logs, Verify that Longhorn doesn't upgrade all volumes at the same time. Only 3 at a time.

### Test degraded volume
1. Verify that Longhorn doesn't upgrade engine image for degraded volume

### Test DR volume
1. Verify that Longhorn doesn't upgrade engine image for DR volume 

### Test expanding volume
1. Verify that Longhorn doesn't upgrade engine image for volume which is expanding
