---
title: Test Backing Image during Longhorn upgrade
---

## System upgrade with compatible backing image manager image
1. Deploy Longhorn. Then set `Concurrent Automatic Engine Upgrade Per Node Limit` to a positive value to enable volume engine auto upgrade.
2. Create 2 backing images: a large one and a small one.
3. Create and attach volumes with the small backing image.
4. Wait for volumes attachment. Then verify the backing image content then write random data in the volumes.
5. Create and attach one more volume with the large backing image.
6. Before the large backing image is downloaded and the volume becomes attached, upgrade the whole Longhorn system:
    1. A new engine image will be used.
    2. The default backing image manager image will be updated.
    3. The new longhorn manager is compatible with the old backing image manager.
7. Wait for system upgrade complete. Then verify:
    1. All old backing image manager and the related pod will be cleaned up automatically after the current downloading is complete. And the existing backing image files won't be removed.
    2. New default backing image manager will take over all backing image ownerships and show the info in the status map. 
    3. All attached volumes still work fine without replica crash, and the content is correct in the volumes during/after the upgrade.
    4. The last volume get attached successfully without replica crash, and the content is correct.
8. Verify volumes and backing images can be deleted.

## System upgrade with incompatible backing image manager image
1. Deploy Longhorn.
2. Create a backing images.
3. Create and attach volumes with the backing image.
4. Wait for volumes attachment. Then verify the backing image content then write random data in the volumes.
5. Upgrade the whole Longhorn system:
    1. The default backing image manager image will be updated.
    2. The new longhorn manager is not compatible with the old backing image manager.
6. Wait for system upgrade complete. Then verify:
    1. All old incompatible backing image manager and the related pod will be cleaned up automatically.
    2. New default backing image manager will take over all backing image ownerships and show the info in the status map.
    3. All attached volumes still work fine without replica crash, and the content is correct in the volumes during/after the upgrade.

#### Available test backing image URLs:
```
https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.raw
https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img
https://github.com/rancher/k3os/releases/download/v0.11.0/k3os-amd64.iso 
```
    
#### The way to generate a longhorn-manager image with higher API version
1. Download longhorn manager repo with command `git clone https://github.com/longhorn/longhorn-manager.git`.
2. Increase the constant `CurrentBackingImageManagerAPIVersion` in `longhorn-manager/engineapi/backing_image_manager.go` by 1.
3. Run `make` to build a longhorn-manager image then push it to docker hub.

#### The way to generate a backing-image-manager image with higher API version
1. Download backing image manager repo with command `git clone https://github.com/longhorn/backing-image-manager.git`.
2. Increase the constants `BackingImageManagerAPIVersion` and `BackingImageManagerAPIMinVersion` in `backing-image-manager/pkg/meta/version.go` by 1.
3. Run `make` to build a longhorn-manager image then push it to docker hub.

