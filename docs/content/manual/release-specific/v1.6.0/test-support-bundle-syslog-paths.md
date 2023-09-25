---
title: Test Support Bundle Syslog Paths
---

## Related issue
https://github.com/longhorn/longhorn/issues/6544

## Test /var/log/messages

**Given** Longhorn installed on SUSE Linux  
**When** generated support-bundle  
**And** syslog exists in the messages file

## Test /var/log/syslog

**Given** Longhorn installed on Ubuntu Linux  
**When** generated support-bundle  
**And** syslog exists in the syslog file
