---
title: Test Frontend Web-socket Data Transfer When Resource Not Updated
---

## Related issue
https://github.com/longhorn/longhorn-manager/pull/918
https://github.com/longhorn/longhorn/issues/2646
https://github.com/longhorn/longhorn/issues/2591

## Test Data Send Over Web-socket When No Resource Updated

**Given** 1 PVC/Pod created.
*And* the Pod is not writing to the mounted volume.

**When** monitor network traffic with browser inspect tool.

**Then** wait for 3 mins
*And* should not see data send over web-socket when there are no updates to the resources.


## Test Data Send Over Web-socket Resource Updated

**Given** monitor network traffic with browser inspect tool.

**When** 1 PVC/Pod created.

**Then** should see data send over event log web-socket.
*And* should see data send over volume web-socket.


## Test Web-socket Keep-alive

**Given** monitor network traffic with browser inspect tool.

**When** wait for 6 minutes.

**Then** should show web-socket connected.
*And* create 1 PVC/Pod.
*And* should see data send over volume web-socket.