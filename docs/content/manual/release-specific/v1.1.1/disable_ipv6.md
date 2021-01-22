---
title: Test Disable IPv6
---

## Related issue

https://github.com/longhorn/longhorn/issues/2136
https://github.com/longhorn/longhorn/issues/2197

Longhorn v1.1.1 should work with IPv6 disabled.

## Scenario
1. Install Kubernetes
2. Disable IPv6 on all the nodes using the following commands
```
sysctl -w net.ipv6.conf.all.disable_ipv6=1
sysctl -w net.ipv6.conf.default.disable_ipv6=1
```
3. Deploy Longhorn and test basic use cases.
    1. Accessing the UI for CRUD RWO/RWX volumes
    2. Use kubectl to create workloads using RWO/RWX volumes.
4. Re-enable ipv6 on all the nodes using:
```
sysctl -w net.ipv6.conf.all.disable_ipv6=0
sysctl -w net.ipv6.conf.default.disable_ipv6=0
```
5. Make sure the basic use cases still works.
