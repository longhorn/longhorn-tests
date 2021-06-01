---
title: Test Frontend Payload Data When Resource Not Updated
---

## Related issue
https://github.com/longhorn/longhorn/issues/2646
https://github.com/longhorn/longhorn/issues/2591

## Test Frontend Payload Data

**Given** 1 PVC/Pod created.

**When** monitor traffic in frontend pod with browser inspect tool.

**Then** wait for 3 mins
*And* should see empty data list in volume payloads. Example: https://github.com/longhorn/longhorn-manager/pull/905#issuecomment-851391374
