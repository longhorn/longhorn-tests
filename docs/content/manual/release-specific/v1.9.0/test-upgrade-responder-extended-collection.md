---
title: Test upgrade responder extended collection
---

## Related issue
- https://github.com/longhorn/longhorn/issues/7047
- https://github.com/longhorn/longhorn/issues/7599

## Test step

**Given** [Deploy upgrade responder stack](https://github.com/longhorn/longhorn/tree/master/dev/upgrade-responder).

**And** Update `upgrade-responder-url` setting to `http://longhorn-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade`
```bash
> k -n longhorn-system get setting upgrade-responder-url
NAME                    VALUE                                                                              APPLIED   AGE
upgrade-responder-url   http://longhorn-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade   true      22m
```
> Match the checkUpgradeURL with the application name: `http://<APP_NAME>-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade`

**When** Create unencrypted volume.  
**And** Create encrypted volume.  
```bash
> kubectl get volume -n longhorn-system -o custom-columns=":metadata.name,:spec.encrypted"

vol-encrypted       true
vol-unencrypted     false
```

**And** Create backing image.
```bash
> k -n longhorn-system get backingimage
NAME   UUID       SOURCETYPE   SIZE      VIRTUALSIZE   AGE
bi-0   1d0a5149   download     1161728   0             15s
```

**And** Setting `orphan-auto-deletion` is `false`.
```bash
> k -n longhorn-system get setting orphan-auto-deletion
NAME                   VALUE   APPLIED   AGE
orphan-auto-deletion   false   true      27h
```

**And** Create orphan directory.
> Ref: https://github.com/longhorn/longhorn-tests/blob/da2e5641e3ee3b8c90f6f246e2772460317c9bda/manager/integration/tests/test_orphan.py#L73-L86

**And** Orphan CR exists.
```bash
> k -n longhorn-system get orphans.longhorn.io
NAME                                                                      TYPE      NODE
orphan-6d553a4a2eef5271787ea28b21a386ebe4b3607f9016fb9c248fa4cf600e64f8   replica   ip-10-0-2-5
```

**And** Wait 1~2 hours for collection data to send to the influxDB database.

**Then** `host_arch` should exist in influxDB database.
```bash
app_name="longhorn"
influxdb_pod=$(kubectl get pod | grep influxdb | awk '{print $1}' | head -n 1)

kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW TAG KEYS FROM upgrade_request' -database="${app_name}_upgrade_responder"
```
Sample output:
```sql
name: upgrade_request
tagKey
------
app_version
host_arch
host_kernel_release
host_os_distro
kubernetes_node_provider
kubernetes_version
longhorn_setting_allow_recurring_job_while_volume_detached
longhorn_setting_allow_volume_creation_with_degraded_availability
longhorn_setting_auto_cleanup_system_generated_snapshot
longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly
longhorn_setting_auto_salvage
longhorn_setting_backup_compression_method
longhorn_setting_crd_api_version
longhorn_setting_create_default_disk_labeled_nodes
longhorn_setting_default_data_locality
longhorn_setting_disable_revision_counter
longhorn_setting_disable_scheduling_on_cordoned_node
longhorn_setting_fast_replica_rebuild_enabled
longhorn_setting_kubernetes_cluster_autoscaler_enabled
longhorn_setting_node_down_pod_deletion_policy
longhorn_setting_node_drain_policy
longhorn_setting_orphan_auto_deletion
longhorn_setting_priority_class
longhorn_setting_registry_secret
longhorn_setting_remove_snapshots_during_filesystem_trim
longhorn_setting_replica_auto_balance
longhorn_setting_replica_disk_soft_anti_affinity
longhorn_setting_replica_soft_anti_affinity
longhorn_setting_replica_zone_soft_anti_affinity
longhorn_setting_restore_volume_recurring_jobs
longhorn_setting_rwx_volume_fast_failover
longhorn_setting_snapshot_data_integrity
longhorn_setting_snapshot_data_integrity_cronjob
longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation
longhorn_setting_storage_network
longhorn_setting_system_managed_components_node_selector
longhorn_setting_system_managed_pods_image_pull_policy
longhorn_setting_taint_toleration
longhorn_setting_v1_data_engine
longhorn_setting_v2_data_engine
```

**And** `longhorn_volume_encrypted_false_count` should exist in influxDB database.  
**And** `longhorn_volume_encrypted_true_count` should exist in influxDB database.  
**And** `longhorn_volume_number_of_replicas` should exist in influxDB database.  
**And** `longhorn_volume_number_of_snapshots` should exist in influxDB database.  
**And** `longhorn_backing_image_count` should exist in influxDB database.  
**And** `longhorn_orphan_count` should exist in influxDB database.  

```bash
kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW FIELD KEYS FROM upgrade_request' -database="${app_name}_upgrade_responder"
```
Sample output:
```sql
name: upgrade_request
fieldKey                                                            fieldType
--------                                                            ---------
longhorn_backing_image_count                                        float
longhorn_disk_filesystem_count                                      float
longhorn_instance_manager_average_cpu_usage_milli_cores             float
longhorn_instance_manager_average_memory_usage_bytes                float
longhorn_manager_average_cpu_usage_milli_cores                      float
longhorn_manager_average_memory_usage_bytes                         float
longhorn_namespace_uid                                              string
longhorn_node_count                                                 float
longhorn_node_disk_ssd_count                                        float
longhorn_orphan_count                                               float
longhorn_setting_backing_image_cleanup_wait_interval                float
longhorn_setting_backing_image_recovery_wait_interval               float
longhorn_setting_backup_concurrent_limit                            float
longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit float
longhorn_setting_concurrent_replica_rebuild_per_node_limit          float
longhorn_setting_concurrent_volume_backup_restore_per_node_limit    float
longhorn_setting_default_replica_count                              float
longhorn_setting_engine_replica_timeout                             float
longhorn_setting_failed_backup_ttl                                  float
longhorn_setting_guaranteed_instance_manager_cpu                    float
longhorn_setting_recurring_failed_jobs_history_limit                float
longhorn_setting_recurring_successful_jobs_history_limit            float
longhorn_setting_replica_file_sync_http_client_timeout              float
longhorn_setting_replica_replenishment_wait_interval                float
longhorn_setting_restore_concurrent_limit                           float
longhorn_setting_storage_minimal_available_percentage               float
longhorn_setting_storage_over_provisioning_percentage               float
longhorn_setting_storage_reserved_percentage_for_default_disk       float
longhorn_setting_support_bundle_failed_history_limit                float
longhorn_setting_v2_data_engine_guaranteed_instance_manager_cpu     float
longhorn_volume_access_mode_rwo_count                               float
longhorn_volume_access_mode_rwx_count                               float
longhorn_volume_average_actual_size_bytes                           float
longhorn_volume_average_number_of_replicas                          float
longhorn_volume_average_size_bytes                                  float
longhorn_volume_average_snapshot_count                              float
longhorn_volume_data_locality_disabled_count                        float
longhorn_volume_encrypted_false_count                               float
longhorn_volume_encrypted_true_count                                float
longhorn_volume_frontend_blockdev_count                             float
longhorn_volume_number_of_replicas                                  float
longhorn_volume_number_of_snapshots                                 float
longhorn_volume_replica_auto_balance_disabled_count                 float
longhorn_volume_replica_disk_soft_anti_affinity_true_count          float
longhorn_volume_replica_soft_anti_affinity_false_count              float
longhorn_volume_replica_zone_soft_anti_affinity_true_count          float
longhorn_volume_restore_volume_recurring_job_false_count            float
longhorn_volume_snapshot_data_integrity_fast_check_count            float
longhorn_volume_unmap_mark_snap_chain_removed_false_count           float
value                                                               integer
```
