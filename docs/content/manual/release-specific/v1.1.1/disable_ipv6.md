---
title: Test Disable IPv6
---

## Related issue

https://github.com/longhorn/longhorn/issues/2136
https://github.com/longhorn/longhorn/issues/2197

Longhorn v1.1.1 should work with IPv6 disabled.

## Scenario
1. Install Kubernetes 
2. Disable IPv6 on all the worker nodes using the following 
```
Go to the folder /etc/default
In the grub file, edit the value GRUB_CMDLINE_LINUX_DEFAULT="ipv6.disable=1"
Once the file is saved update by the command update-grub
Reboot the node and once the node becomes active, 
use the command cat /proc/cmdline to verify "ipv6.disable=1" is reflected in the values 
```
3. Deploy Longhorn and test basic use cases.
    1. Accessing the UI for CRUD RWO/RWX volumes
    2. Use kubectl to create workloads using RWO/RWX volumes.
4. Re-enable ipv6 on all the nodes using:
```
By deleting the "ipv6.disable=1" from the GRUB_CMDLINE_LINUX_DEFAULT accessing grub file from
/etc/default
Perform a reboot and once the node comes active 
use the command cat /proc/cmdline to verify "ipv6.disable=1" is not reflected in the values
5. Make sure the basic use cases still works.
