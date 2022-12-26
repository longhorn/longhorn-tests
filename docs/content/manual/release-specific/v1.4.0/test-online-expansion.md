---
title: Test Online Expansion
---

## Related issue
https://github.com/longhorn/longhorn/issues/1674

## Test online expansion with continuous reading/writing

**Given** Prepare a relatively large file (5Gi for example) with the checksum calculated.

*And* Create and attach a volume.

*And* Monitor the instance manager pod logs.

**When** Use `dd` to copy data from the file to the Longhorn block device.

```
dd if=/mnt/data of=/dev/longhorn/vol bs=1M
```

*And* Do online expansion for the volume during the copying.

**Then** The expansion should success. The corresponding block device on the attached node is expanded.

*And* Should not see any io or tgt related error logs in the instance manager pods.

**When** Use `dd` to calculate the data checksum for the Longhorn block device..

```
dd if=/dev/longhorn/vol bs=1M count=5000 status=none | md5sum
```

*And* Do online expansion for the volume during the calculation.

**Then** The expansion should success. The corresponding block device on the attached node is expanded.

*And* Should not see any io or tgt related error logs in the instance manager pods.

*And* The checksum matches.


## Test online expansion with upgrade

**Given** Deploy an old version Longhorn, v1.3.2 for example.

*And* Create and attach 2 volumes.

*And* Upgrade Longhorn to the latest version.

**When** Do online expansion for volume 1.

**Then** The expansion of volume 1 should get stuck. (old engine image + old instance manager)

*And* The engine CR of volume 1 should contain the expansion error. e.g.,
```yaml
status:
  lastExpansionError: cannot do online expansion for the old engine vol-e-b2d9b924
  with cli API version 6
  lastExpansionFailedAt: 2022-12-29 02:44:15.481809613 +0000 UTC m=+146155.850227034
```

*And* Expansion can be canceled.

**When** Do live upgrade for volume 1.

*And* Retry online expansion.

**Then** The expansion should get stuck. (new engine image + old instance manager)

*And* The engine CR should contain the expansion error.

*And* The expansion can be canceled.

**When** Detach and reattach volume 1.

*And* Retry online expansion.

**Then** The expansion should success. The corresponding block device on the attached node is expanded. (new engine image + new instance manager)

**When** Directly detach and reattach volume 2.

*And* Do online expansion for volume 2.

**Then** The expansion should get stuck. (old engine image + new instance manager)

*And* The engine CR of volume 2 should contain the expansion error.

*And* The expansion can be canceled.

**When** Do live upgrade for volume 2.

*And* Retry online expansion.

**Then** The expansion should success. The corresponding block device on the attached node is expanded. (new engine image + new instance manager)
