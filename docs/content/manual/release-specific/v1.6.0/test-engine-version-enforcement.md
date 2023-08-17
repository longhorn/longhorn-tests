---
title: Test engine version enforcement
---

## Related issue
https://github.com/longhorn/longhorn/issues/5842

## Test step

**Given** Longhorn v1.4.x cluster running  
And create and attach a volume (volume-1)  
And upgraded Longhorn to v1.5.x  
And create and attach a volume (volume-2)

**When** upgraded Longhorn to v1.6.0  
**Then** v1.6.0 longhorn-manager Pods should be in crashloop
```
longhorn-manager-zrf8r                                0/1     CrashLoopBackOff   2 (10s ago)   52s
longhorn-manager-zsph2                                0/1     CrashLoopBackOff   2 (8s ago)    52s
longhorn-manager-grhsf                                0/1     CrashLoopBackOff   2 (8s ago)    51s
```
And should see incompatible version error in longhorn-manager Pod logs
```
time="2023-08-17T03:03:20Z" level=fatal msg="Error starting manager: failed checking Engine upgarde path: incompatible Engine ei-7fa7c208 client API version: found version 7 is below required minimal version 8"
```

**When** downgraded Longhorn to v1.5.x  
**Then** Longhorn components should be running

**When** upgraded v1.4.1 volume (volume-1) engine  
And upgraded Longhorn to v1.6.0
**Then** Longhorn components should be running  
And v1.4.x EngineImage state should be incompatible
```
NAME          STATE          IMAGE                               REFCOUNT   BUILDDATE   AGE
ei-74783864   deployed       longhornio/longhorn-engine:v1.5.1   10         28d         12m
ei-7fa7c208   incompatible   longhornio/longhorn-engine:v1.4.1   0          157d        13m
ei-ad420081   deployed       c3y1huang/research:2017-lh-ei       0          44h         24s
```

**When** update existing volume/engine/replica custom resourcs `spec.image` with `longhornio/longhorn-engine:v1.4.x`  
**Then** should be blocked  
