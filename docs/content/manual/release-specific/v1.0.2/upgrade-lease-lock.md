---
title: Upgrade Lease Lock
---
The time it takes between the Longhorn Manager starting up and the upgrade completing for that Longhorn Manager can be used to determine if the upgrade lock was released correctly:
1. Create a fresh Longhorn installation or delete all of the Longhorn Manager Pods in the existing installation.
2. Check the logs for the Longhorn Manager Pods and note the timestamps for the first line in the log and the timestamp for when the upgrade has completed. 
For example, in this log, the relevant timestamps are `2020-08-03T22:55:39Z` and `2020-08-03T22:56:24Z`:
```
time="2020-08-03T22:55:39Z" level=info msg="Start overwriting built-in settings with customized values"
E0803 22:55:40.141071       1 leaderelection.go:310] error initially creating leader election record: leases.coordination.k8s.io "longhorn-manager-upgrade-lock" already exists
time="2020-08-03T22:55:43Z" level=info msg="New upgrade leader elected: 74.207.240.60"
time="2020-08-03T22:56:01Z" level=info msg="New upgrade leader elected: 96.126.101.152"
time="2020-08-03T22:56:24Z" level=info msg="Start upgrading"
time="2020-08-03T22:56:24Z" level=info msg="No API version upgrade is needed"
time="2020-08-03T22:56:24Z" level=info msg="Finish upgrading"
```
3. Calculate the amount of time between the two timestamps. 
If the lock was released successfully, then it should take no longer than about 15 seconds for the upgrade process to complete on each Pod:
- `longhorn-manager-k95bm`: 2020-08-03T23:04:14Z - 2020-08-03T23:04:20Z **(6 seconds)**
- `longhorn-manager-rgpvt`: 2020-08-03T23:04:14Z - 2020-08-03T23:04:15Z **(1 second)**
- `longhorn-manager-z2jd9`: 2020-08-03T23:04:21Z - 2020-08-03T23:04:21Z **(0 seconds)**

Here is an example of a failing case with the Longhorn Manager attempting to upgrade and the upgrade lock not being released successfully.
- `longhorn-manager-82kt4`: 2020-08-03T22:55:39Z - 2020-08-03T22:55:40Z **(1 second)**
- `longhorn-manager-lpbth`: 2020-08-03T22:55:40Z - 2020-08-03T22:56:00Z **(20 seconds)**
- `longhorn-manager-pdmrv`: 2020-08-03T22:55:39Z - 2020-08-03T22:56:24Z **(45 seconds)**
