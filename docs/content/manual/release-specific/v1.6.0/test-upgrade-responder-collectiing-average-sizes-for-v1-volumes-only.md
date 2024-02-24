---
Test upgrade-responder: Collecting Average Sizes for V1 Volumes Only
---

## Related issues

- https://github.com/longhorn/longhorn/issues/7380

## Test step

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

**And** setting `v2-data-engine` value is `true`.  
**And** add a block disk to cluster nodes.  
**And** [deploy upgrade responder stack](https://github.com/longhorn/longhorn/tree/master/dev/upgrade-responder).  

**When** create 50 mi volume `lhv-v1` using v1 data engine.  
**And** create 50 mi volume `lhv-v2` using v2 data engine.  
**And** attach volume `lhv-v1` and write some data.  
**And** attach volume `lhv-v2` and write some data.  
**And** Wait 1~2 hours for collection data to send to the influxDB database.  

**Then** the value of field `longhorn_volume_average_size_bytes` in the influxdb should equal to the average size of all v1 volumes (excluding v2 volumes).  
**And** the value of field `longhorn_volume_average_actual_size_bytes` in the influxdb should be equal or simular to the average actual size of all v1 volumes (excluding v2 volumes).  
> It's OK for the actual size to be slightly off due to ongoing workload activities, such as data writing by the upgrade-responder.  
```bash
# Get the sizes in the influxdb.
#
# Sample:
# > name: upgrade_request
#   time                longhorn_volume_average_actual_size_bytes longhorn_volume_average_size_bytes
#   ----                ----------------------------------------- ----------------------------------
#   1703045996398941914 73269248                                  1449132032
#   1703046063248379696 73284266                                  1449132032
app_name="longhorn"
influxdb_pod=$(kubectl get pod | grep influxdb | awk '{print $1}' | head -n 1)
kubectl exec -it ${influxdb_pod} -- influx -execute 'SELECT "longhorn_volume_average_actual_size_bytes", "longhorn_volume_average_size_bytes" FROM "upgrade_request"' -database="${app_name}_upgrade_responder"
```

```bash
# Get the sizes from Longhorn volumes.

v1_volume_count=$(kubectl get volumes -n longhorn-system -o=jsonpath='{range .items[*]}{.spec.backendStoreDriver}{"\n"}{end}' | grep -c 'v1')
echo "Number of V1 volumes: $v1_volume_count"

# Get the expected average size.
# > Total size: 4347396096
# > Average size: 1449132032
total_size=$(kubectl get volumes -n longhorn-system -o=json | jq -r '[.items[] | select(.spec.backendStoreDriver != "v2") | .spec.size | tonumber] | add')
echo "Total size: $total_size"

average_size=$(echo "scale=0; $total_size / $v1_volume_count" | bc)
echo "Average size: $average_size"

# Get the expected average actual size.
#
# Sample:
# > Total actualSize: 220368896
# > Average actual size: 73456298
total_actual_size=$(kubectl get volumes -n longhorn-system -o=json | jq -r '[.items[] | select(.spec.backendStoreDriver != "v2") | .status.actualSize | tonumber] | add')
echo "Total actualSize: $total_actual_size"

average_total_actual_size=$(echo "scale=0; $total_actual_size / $v1_volume_count" | bc)
echo "Average actual size: $average_total_actual_size"
```
