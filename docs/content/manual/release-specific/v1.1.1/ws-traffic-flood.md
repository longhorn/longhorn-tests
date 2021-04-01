---
title: Test Frontend Traffic
---

## Related issue
https://github.com/longhorn/longhorn/issues/2372

## Test Frontend Traffic

**Given** 100 pvc created.

*And* all pvcs deployed and detached.

**When** monitor traffic in frontend pod with nload.
```
apk add nload
nload
```

**Then** should not see a continuing large amount of traffic when there is no operation happening. The smaller spikes are mostly coming from event resources which possibly could be enhanced later (https://github.com/longhorn/longhorn/issues/2433).
