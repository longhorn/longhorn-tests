---
title: Test Node ID Change During Backing Image Creation
---

## Related issue
https://github.com/longhorn/longhorn/issues/4887

## Steps

**Given** A relatively large file so that uploading it would take several minutes at least.

*And* Upload the file as a backing image.

*And* Monitor the longhorn manager pod logs.

**When** Add new nodes for the cluster or new disks for the existing Longhorn nodes during the upload.

**Then** Should see the upload success.

*And* Should not see error messages like below in the longhorn manager pods.
```
2022-11-07T21:03:30.772022890Z time="2022-11-07T21:03:30Z" level=error msg="Backing Image Data Source was state in-progress but the pod became not ready, the state will be updated to failed, message: pod spec node ID vsh01ha doesn't match the desired node ID vsh01hc" backingImageDataSource=default-image-zxgnk controller=longhorn-backing-image-data-source diskUUID=588588f4-1bec-41c8-9fde-936d5a7bf492 node=vsh01hc nodeID=vsh01hc parameters="map[url:http://10.89.4.53/wsp.raw]" sourceType=download

```
