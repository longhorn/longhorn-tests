---
title: Test PVC Name and Namespace included in the volume metrics
---

## Related issues

- https://github.com/longhorn/longhorn/issues/5297
- https://github.com/longhorn/longhorn-manager/pull/2284

## Test step

**Given** created 2 volumes (volume-1, volume-2)

**When** PVC created for volume (volume-1)
And attached volumes (volume-1, volume-2)

**Then** metrics with `longhorn_volume_` prefix should include `pvc="volume-1"`

```bash
curl -sSL http://10.0.2.212:32744/metrics | grep longhorn_volume | grep ip-10-0-2-151 | grep volume-1
longhorn_volume_actual_size_bytes{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_capacity_bytes{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 1.073741824e+09
longhorn_volume_read_iops{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_read_latency{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_read_throughput{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_robustness{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 1
longhorn_volume_state{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 2
longhorn_volume_write_iops{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_write_latency{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_write_throughput{namespace="default",node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
```

And metrics with `longhorn_volume_` prefix should include `pvc=""` for (volume-2)

```bash
> curl -sSL http://10.0.2.212:32744/metrics | grep longhorn_volume | grep ip-10-0-2-151 | grep volume-2
longhorn_volume_actual_size_bytes{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_capacity_bytes{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 1.073741824e+09
longhorn_volume_read_iops{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_read_latency{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_read_throughput{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_robustness{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 1
longhorn_volume_state{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 2
longhorn_volume_write_iops{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_write_latency{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_write_throughput{namespace="",node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
```
