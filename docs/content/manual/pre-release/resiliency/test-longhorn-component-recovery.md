---
title: "Test Longhorn components recovery"
---

This is a simple test is check if all the components are recoverable.

#### Test data setup:
1. Deploy Longhorn on a 3 nodes cluster.
1. Create a volume `vol-1` using Longhorn UI.
1. Create a volume `vol-2` using the Longhorn storage class.
1. Create a volume `vol-3` with backing image.
1. Create an RWX volume `vol-4`.
1. Write some data in all the volumes created and compute the md5sum.
1. Have all the volumes in attached state.

#### Test steps:
1. Delete the IM-e from every volume and make sure every volume recovers. Check the data as well.
1. Start replica rebuilding for the aforementioned volumes, and delete the IM-e while it is rebuilding. Verify the recovered volumes.
1. Delete the Share-manager pod and verify the RWX volume `vol-4` is able recover. Verify the data too.
1. Delete the backing image manager pod and verify the pod gets recreated.
1. Delete one pod of all the Longhorn components like longhorn-manager, ui, csi components etc and verify they are able to recover. 
