---
title: Test IM Proxy connection metrics
---

## Related issue
https://github.com/longhorn/longhorn/issues/2821
https://github.com/longhorn/longhorn/issues/4038

## Test gRPC proxy

**Given** Longhorn exist in the cluster.

*And* Monitoring stack exist in the cluster.

**When** Execute `longhorn_instance_manager_proxy_grpc_connection` in Prometheus UI.

**Then** Metric data shows in Prometheus UI.

**When** Monitor `longhorn_instance_manager_proxy_grpc_connection` in Grafana UI Panel.

*And* Run automation regression.

**Then** Connections should return to 0 when tests complete.
