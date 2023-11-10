---
title: Test PVC Name included in the volume metrics
---

## Related issue

https://github.com/longhorn/longhorn/issues/5297

## Test step

**Given** created 2 volumes (volume-1, volume-2)

**When** PVC created for volume (volume-1)
And attached volumes (volume-1, volume-2)

**Then** metrics with `longhorn_volume_` prefix should include `pvc="volume-1"`

```bash
curl -sSL http://10.0.2.212:32744/metrics | grep longhorn_volume | grep ip-10-0-2-151 | grep volume-1
longhorn_volume_actual_size_bytes{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_capacity_bytes{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 1.073741824e+09
longhorn_volume_read_iops{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_read_latency{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_read_throughput{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_robustness{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 1
longhorn_volume_state{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 2
longhorn_volume_write_iops{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_write_latency{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
longhorn_volume_write_throughput{node="ip-10-0-2-151",pvc="volume-1",volume="volume-1"} 0
```

And metrics with `longhorn_volume_` prefix should include `pvc=""` for (volume-2)

```bash
> curl -sSL http://10.0.2.212:32744/metrics | grep longhorn_volume | grep ip-10-0-2-151 | grep volume-2
longhorn_volume_actual_size_bytes{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_capacity_bytes{node="ip-10-0-2-151",pvc="",volume="volume-2"} 1.073741824e+09
longhorn_volume_read_iops{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_read_latency{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_read_throughput{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_robustness{node="ip-10-0-2-151",pvc="",volume="volume-2"} 1
longhorn_volume_state{node="ip-10-0-2-151",pvc="",volume="volume-2"} 2
longhorn_volume_write_iops{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_write_latency{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
longhorn_volume_write_throughput{node="ip-10-0-2-151",pvc="",volume="volume-2"} 0
```
