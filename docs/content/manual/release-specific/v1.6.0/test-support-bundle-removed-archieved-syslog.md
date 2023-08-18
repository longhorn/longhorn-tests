---
title: Test Support Bundle Removed Archieved Syslog
---

## Related issue
https://github.com/longhorn/longhorn/issues/6338

## Test step

**Given** Longhorn nodes have archieved syslogs.
```
> ls /var/log | grep messages
messages
messages-20230818.xz
```
> Note that other operating system might be using the path /var/log/syslog

**When** generated support-bundle

**Then** collected syslog should not have archived files
