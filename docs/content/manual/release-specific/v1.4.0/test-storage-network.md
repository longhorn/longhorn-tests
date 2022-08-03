---
title: Test replica scale-down warning
---

## Related issue
https://github.com/longhorn/longhorn/issues/4120

## Steps

**Given** `Replica Auto Balance` set to `least-effort` or `best-effort`.

*And* Volume with 3 replicas created.

*And* Volume attached to `node-1`.

*And* Monitor `node-1` manager pod events.
```
kubectl alpha events -n longhorn-system pod <node-1 manager pod> -w
```

**When** Update replica count to 1.

**Then** Should see `Normal` replice delete event.
```
Normal    Delete                   Engine/t1-e-6a846a7a                                Removed unknown replica tcp://10.42.2.94:10000 from engine
```

*And* Should not see `Warning` unknown replica detect event.
```
Warning   Faulted                  Engine/t1-e-6a846a7a                                   Detected replica UNKNOWN-tcp://10.42.1.98:10000 (10.42.1.98:10000) in error
```
