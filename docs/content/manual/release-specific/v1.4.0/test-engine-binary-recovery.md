---
title: Test engine binary recovery
---

## Related issue
https://github.com/longhorn/longhorn/issues/4380

## Steps
### Test remove engine binary on host should recover

**Given** EngineImage custom resource deployed
```
> kubectl -n longhorn-system get engineimage
NAME          STATE      IMAGE                                    REFCOUNT   BUILDDATE   AGE
ei-b907910b   deployed   longhornio/longhorn-engine:master-head   0          3d23h       2m25s
```
And engine image pods `Ready` are `1/1`.
```
> kubectl -n longhorn-system get pod | grep engine-image
engine-image-ei-b907910b-g4kpd  1/1   Running   0   2m43s
engine-image-ei-b907910b-46k6t  1/1   Running   0   2m43s
engine-image-ei-b907910b-t6wnd  1/1   Running   0   2m43s
```
**When** Delete engine binary on host
```
> rm -rf /var/lib/longhorn/engine-binaries/*
```
**Then** engine image pod restarted
And engine image pods `Ready` are `1/1`.
```
> kubectl -n longhorn-system get pod | grep engine-image
engine-image-ei-b907910b-g4kpd   1/1   Running   0             4m3s
engine-image-ei-b907910b-46k6t   1/1   Running   0             4m3s
engine-image-ei-b907910b-t6wnd   1/1   Running   1 (17s ago)   4m3s

```
And EngineImage custom resource state `deployed`
```
> kubectl -n longhorn-system get engineimage
NAME          STATE      IMAGE                                    REFCOUNT   BUILDDATE   AGE
ei-b907910b   deployed   longhornio/longhorn-engine:master-head   0          3d23h       4m19s
```
And engine binary exist on host
```
> ls /var/lib/longhorn/engine-binaries/
longhornio-longhorn-engine-master-head
> ls /var/lib/longhorn/engine-binaries/longhornio-longhorn-engine-master-head/
longhorn

```
And volume can create and attach.

### Test remove engine binary in engine image pod should recover
**Given** EngineImage custom resource deployed
```
> kubectl -n longhorn-system get engineimage
NAME          STATE      IMAGE                                    REFCOUNT   BUILDDATE   AGE
ei-b907910b   deployed   longhornio/longhorn-engine:master-head   0          3d23h       14m
```
And engine image pods `Ready` are `1/1`.
```
> kubectl -n longhorn-system get pod | grep engine-image
engine-image-ei-b907910b-g4kpd   1/1   Running   0             14m
engine-image-ei-b907910b-46k6t   1/1   Running   0             14m
engine-image-ei-b907910b-t6wnd   1/1   Running   1 (11m ago)   14m
```
**When** Delete engine binary on in pod
```
> kubectl -n longhorn-system exec -it engine-image-ei-b907910b-46k6t -- rm /data/longhorn
```
**Then** engine image pod restarted
And engine image pods `Ready` are `1/1`.
```
> kubectl -n longhorn-system get pod | grep engine-image
engine-image-ei-b907910b-g4kpd   1/1   Running   0               18m
engine-image-ei-b907910b-t6wnd   1/1   Running   1 (14m ago)     18m
engine-image-ei-b907910b-46k6t   1/1   Running   1 (2m21s ago)   18m

```
And EngineImage custom resource state `deployed`
```
> kubectl -n longhorn-system get engineimage
NAME          STATE      IMAGE                                    REFCOUNT   BUILDDATE   AGE
ei-b907910b   deployed   longhornio/longhorn-engine:master-head   0          3d23h       18m
```
And engine binary exist in pod
```
> kubectl -n longhorn-system exec -it engine-image-ei-b907910b-46k6t -- ls /data/longhorn
/data/longhorn

> kubectl -n longhorn-system exec -it engine-image-ei-b907910b-46k6t -- /data/longhorn -v
longhorn version f0a92283
```
And volume can create and attach.
