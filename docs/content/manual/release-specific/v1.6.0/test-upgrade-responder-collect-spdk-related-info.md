---
title: Test upgrade responder should collect SPDK related info
---

## Related issue
https://github.com/longhorn/longhorn/issues/6033

## Test step

### Prerequisite

**Given** Patch build and deploy Longhorn.  
```
diff --git a/controller/setting_controller.go b/controller/setting_controller.go
index de77b7246..ac6263ac5 100644
--- a/controller/setting_controller.go
+++ b/controller/setting_controller.go
@@ -49,7 +49,7 @@ const (
 var (
 	upgradeCheckInterval          = time.Hour
 	settingControllerResyncPeriod = time.Hour
-	checkUpgradeURL               = "https://longhorn-upgrade-responder.rancher.io/v1/checkupgrade"
+	checkUpgradeURL               = "http://longhorn-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade"
 )

 type SettingController struct {
```
> Match the checkUpgradeURL with the application name: `http://<APP_NAME>-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade`

**And** Set setting `v2-data-engine` to `true`.  
**And** [Add two block-type Disks in Longhorn Nodes](https://longhorn.io/docs/1.5.3/spdk/quick-start/#add-block-type-disks-in-longhorn-nodes).  

#### Test Collecting Longhorn Disk Type

**Given** [Prerequisite](#prerequisite).
**And** [Deploy upgrade responder stack](https://github.com/longhorn/longhorn/tree/master/dev/upgrade-responder).  

**When** Wait 1~2 hours for collection data to send to the influxDB database.  

**Then** `longhorn_disk_block_Count` should exist the influxDB database.  
         `longhorn_disk_filesystem_Count` should exist the influxDB database.  
```bash
> app_name="longhorn"
> influxdb_pod=$(kubectl get pod | grep influxdb | awk '{print $1}' | head -n 1)
> kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW FIELD KEYS FROM upgrade_request' -database="${app_name}_upgrade_responder" | grep longhorn_disk
longhorn_disk_block_count                                           float
longhorn_disk_filesystem_count                                      float
```

**And** the value in `longhorn_disk_filesystem_Count` should equal to the number of volume using the V1 engine.  
```bash
> kubectl exec -it ${influxdb_pod} -- influx -execute 'SELECT "longhorn_disk_filesystem_count" FROM "upgrade_request"' -database="${app_name}_upgrade_responder"
name: upgrade_request
time                longhorn_disk_filesystem_count
----                ------------------------------
1702351841122419036 1
1702351841563938125 1
1702351842436864452 1
```
**And** the value in `longhorn_disk_block_Count` should equal to the number of volume using the V2 engine.  
```bash
> kubectl exec -it ${influxdb_pod} -- influx -execute 'SELECT "longhorn_disk_block_count" FROM "upgrade_request"' -database="${app_name}_upgrade_responder"
name: upgrade_request
time                longhorn_disk_block_count
----                -------------------------
1702351841122419036 2
1702351841563938125 2
1702351842436864452 2
```

#### Test Collecting Volume Backend Store Driver

**Given** [Prerequisite](#prerequisite).
**And** Create one volume using V1 engine.
        Create two volume using V2 engine.
**And** [Deploy upgrade responder stack](https://github.com/longhorn/longhorn/tree/master/dev/upgrade-responder).  

**When** Wait 1~2 hours for collection data to send to the influxDB database.  

**Then** `longhorn_volume_backend_store_driver_v1_count` should exist the influxDB database.  
         `longhorn_volume_backend_store_driver_v2_count` should exist the influxDB database.  
```bash
> app_name="longhorn"
> influxdb_pod=$(kubectl get pod | grep influxdb | awk '{print $1}' | head -n 1)
> kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW FIELD KEYS FROM upgrade_request' -database="${app_name}_upgrade_responder" | grep longhorn_volume_backend_store_driver
longhorn_volume_backend_store_driver_v1_count                       float
longhorn_volume_backend_store_driver_v2_count                       float
```

**And** the value in `longhorn_volume_backend_store_driver_v1_count` should equal to the number of volume using the V1 engine.  
```bash
> kubectl exec -it ${influxdb_pod} -- influx -execute 'SELECT "longhorn_volume_backend_store_driver_v1_count" FROM "upgrade_request"' -database="${app_name}_upgrade_responder"
name: upgrade_request
time                longhorn_volume_backend_store_driver_v1_count
----                ---------------------------------------------
1702351841122419036 3
```
**And** the value in `longhorn_volume_backend_store_driver_v2_count` should equal to the number of volume using the V2 engine.  
```bash
> kubectl exec -it ${influxdb_pod} -- influx -execute 'SELECT "longhorn_volume_backend_store_driver_v2_count" FROM "upgrade_request"' -database="${app_name}_upgrade_responder"
name: upgrade_request
time                longhorn_volume_backend_store_driver_v2_count
----                ---------------------------------------------
1702351841122419036 2
```
