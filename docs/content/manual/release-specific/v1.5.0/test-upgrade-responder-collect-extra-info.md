---
title: Test upgrade responder collecting extra info
---

## Related issue
https://github.com/longhorn/longhorn/issues/5235

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

**And** [Deploy upgrade responder stack](https://github.com/longhorn/longhorn/tree/master/dev/upgrade-responder). 
 
**When** Wait 1~2 hours for collection data to send to the influxDB database.  
**Then** Collection data should exist the influxDB database.
```bash
app_name="longhorn"
influxdb_pod=$(kubectl get pod | grep influxdb | awk '{print $1}' | head -n 1)

kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW TAG KEYS FROM upgrade_request' -database="${app_name}_upgrade_responder"
```
Sample output:
```
name: upgrade_request
tagKey
------
app_version
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
longhorn_setting_backup_target
longhorn_setting_crd_api_version
longhorn_setting_create_default_disk_labeled_nodes
longhorn_setting_default_data_locality
longhorn_setting_disable_revision_counter
longhorn_setting_disable_scheduling_on_cordoned_node
longhorn_setting_fast_replica_rebuild_enabled
longhorn_setting_kubernetes_cluster_autoscaler_enabled
longhorn_setting_node_down_pod_deletion_policy
longhorn_setting_node_drain_policy
longhorn_setting_offline_replica_rebuilding
longhorn_setting_orphan_auto_deletion
longhorn_setting_priority_class
longhorn_setting_registry_secret
longhorn_setting_remove_snapshots_during_filesystem_trim
longhorn_setting_replica_auto_balance
longhorn_setting_replica_soft_anti_affinity
longhorn_setting_replica_zone_soft_anti_affinity
longhorn_setting_restore_volume_recurring_jobs
longhorn_setting_snapshot_data_integrity
longhorn_setting_snapshot_data_integrity_cronjob
longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation
longhorn_setting_storage_network
longhorn_setting_system_managed_components_node_selector
longhorn_setting_system_managed_pods_image_pull_policy
longhorn_setting_taint_toleration
longhorn_setting_v2_data_engine
```

```bash
kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW FIELD KEYS FROM upgrade_request' -database="${app_name}_upgrade_responder"
```
Sample output:
```
name: upgrade_request
fieldKey                                                            fieldType
--------                                                            ---------
longhorn_instance_manager_average_cpu_usage_milli_cores             float
longhorn_instance_manager_average_memory_usage_bytes                float
longhorn_manager_average_cpu_usage_milli_cores                      float
longhorn_manager_average_memory_usage_bytes                         float
longhorn_namespace_uid                                              string
longhorn_node_count                                                 float
longhorn_node_disk_ssd_count                                        float
longhorn_setting_backing_image_cleanup_wait_interval                float
longhorn_setting_backing_image_recovery_wait_interval               float
longhorn_setting_backup_concurrent_limit                            float
longhorn_setting_backupstore_poll_interval                          float
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
longhorn_volume_access_mode_rwo_count                               float
longhorn_volume_access_mode_rwx_count                               float
longhorn_volume_average_actual_size_bytes                           float
longhorn_volume_average_number_of_replicas                          float
longhorn_volume_average_size_bytes                                  float
longhorn_volume_average_snapshot_count                              float
longhorn_volume_data_locality_best_effort_count                     float
longhorn_volume_data_locality_disabled_count                        float
longhorn_volume_data_locality_strict_local_count                    float
longhorn_volume_frontend_blockdev_count                             float
longhorn_volume_offline_replica_rebuilding_disabled_count           float
longhorn_volume_offline_replica_rebuilding_enabled_count            float
longhorn_volume_replica_auto_balance_disabled_count                 float
longhorn_volume_replica_soft_anti_affinity_false_count              float
longhorn_volume_replica_zone_soft_anti_affinity_true_count          float
longhorn_volume_restore_volume_recurring_job_false_count            float
longhorn_volume_snapshot_data_integrity_disabled_count              float
longhorn_volume_snapshot_data_integrity_fast_check_count            float
longhorn_volume_unmap_mark_snap_chain_removed_false_count           float
value                                                               integer
```

**When** Restart the upgrade responder pods.
```bash
app_name="longhorn"
kubectl scale deployment ${app_name}-upgrade-responder --replicas=0
kubectl scale deployment ${app_name}-upgrade-responder --replicas=3
```  
**Then** Upgrade responder should create continuous queries in influxDB.
```bash
kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW CONTINUOUS QUERIES' -database="${app_name}_upgrade_responder"
```
Sample output:
```
name: _internal
name query
---- -----

name: longhorn_upgrade_responder
name                                                                                                 query
----                                                                                                 -----
cq_upgrade_request_down_sampling                                                                     CREATE CONTINUOUS QUERY cq_upgrade_request_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.upgrade_request_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_app_version_down_sampling                                                                      CREATE CONTINUOUS QUERY cq_by_app_version_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_app_version_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), app_version END
cq_by_country_code_down_sampling                                                                     CREATE CONTINUOUS QUERY cq_by_country_code_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_country_code_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), country_isocode END
cq_by_longhorn_setting_replica_zone_soft_anti_affinity_down_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_zone_soft_anti_affinity_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_zone_soft_anti_affinity_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_zone_soft_anti_affinity END
cq_by_longhorn_setting_create_default_disk_labeled_nodes_down_sampling                               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_create_default_disk_labeled_nodes_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_create_default_disk_labeled_nodes_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_create_default_disk_labeled_nodes END
cq_by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_down_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_kubernetes_cluster_autoscaler_enabled END
cq_by_host_os_distro_down_sampling                                                                   CREATE CONTINUOUS QUERY cq_by_host_os_distro_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_host_os_distro_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), host_os_distro END
cq_by_longhorn_setting_recurring_successful_jobs_history_limit_down_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_recurring_successful_jobs_history_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_recurring_successful_jobs_history_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_recurring_successful_jobs_history_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_down_sampling              CREATE CONTINUOUS QUERY cq_by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_namespace_uid_down_sampling                                                           CREATE CONTINUOUS QUERY cq_by_longhorn_namespace_uid_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(longhorn_namespace_uid) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_namespace_uid_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_backupstore_poll_interval_down_sampling                                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backupstore_poll_interval_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_backupstore_poll_interval) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backupstore_poll_interval_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_snapshot_data_integrity_fast_check_count_down_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_volume_snapshot_data_integrity_fast_check_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_snapshot_data_integrity_fast_check_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_snapshot_data_integrity_fast_check_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_node_disk_ssd_count_down_sampling                                                     CREATE CONTINUOUS QUERY cq_by_longhorn_node_disk_ssd_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_node_disk_ssd_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_node_disk_ssd_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_support_bundle_failed_history_limit_down_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_support_bundle_failed_history_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_support_bundle_failed_history_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_support_bundle_failed_history_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_default_data_locality_down_sampling                                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_default_data_locality_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_default_data_locality_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_default_data_locality END
cq_by_longhorn_setting_remove_snapshots_during_filesystem_trim_down_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_remove_snapshots_during_filesystem_trim_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_remove_snapshots_during_filesystem_trim_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_remove_snapshots_during_filesystem_trim END
cq_by_longhorn_setting_allow_volume_creation_with_degraded_availability_down_sampling                CREATE CONTINUOUS QUERY cq_by_longhorn_setting_allow_volume_creation_with_degraded_availability_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_allow_volume_creation_with_degraded_availability_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_allow_volume_creation_with_degraded_availability END
cq_by_longhorn_setting_node_drain_policy_down_sampling                                               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_node_drain_policy_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_node_drain_policy_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_node_drain_policy END
cq_by_longhorn_setting_fast_replica_rebuild_enabled_down_sampling                                    CREATE CONTINUOUS QUERY cq_by_longhorn_setting_fast_replica_rebuild_enabled_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_fast_replica_rebuild_enabled_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_fast_replica_rebuild_enabled END
cq_by_longhorn_volume_average_snapshot_count_down_sampling                                           CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_snapshot_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_average_snapshot_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_snapshot_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_system_managed_pods_image_pull_policy_down_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_system_managed_pods_image_pull_policy_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_system_managed_pods_image_pull_policy_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_system_managed_pods_image_pull_policy END
cq_by_longhorn_volume_restore_volume_recurring_job_false_count_down_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_volume_restore_volume_recurring_job_false_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_restore_volume_recurring_job_false_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_restore_volume_recurring_job_false_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_storage_over_provisioning_percentage_down_sampling                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_over_provisioning_percentage_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_storage_over_provisioning_percentage) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_over_provisioning_percentage_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_manager_average_cpu_usage_milli_cores_down_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_manager_average_cpu_usage_milli_cores_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_manager_average_cpu_usage_milli_cores) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_manager_average_cpu_usage_milli_cores_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_data_locality_strict_local_count_down_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_volume_data_locality_strict_local_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_data_locality_strict_local_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_data_locality_strict_local_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_backing_image_cleanup_wait_interval_down_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backing_image_cleanup_wait_interval_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_backing_image_cleanup_wait_interval) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backing_image_cleanup_wait_interval_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_unmap_mark_snap_chain_removed_false_count_down_sampling                        CREATE CONTINUOUS QUERY cq_by_longhorn_volume_unmap_mark_snap_chain_removed_false_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_unmap_mark_snap_chain_removed_false_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_unmap_mark_snap_chain_removed_false_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_host_kernel_release_down_sampling                                                              CREATE CONTINUOUS QUERY cq_by_host_kernel_release_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_host_kernel_release_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), host_kernel_release END
cq_by_longhorn_setting_priority_class_down_sampling                                                  CREATE CONTINUOUS QUERY cq_by_longhorn_setting_priority_class_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_priority_class_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_priority_class END
cq_by_longhorn_setting_disable_scheduling_on_cordoned_node_down_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_disable_scheduling_on_cordoned_node_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_disable_scheduling_on_cordoned_node_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_disable_scheduling_on_cordoned_node END
cq_by_longhorn_setting_system_managed_components_node_selector_down_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_system_managed_components_node_selector_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_system_managed_components_node_selector_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_system_managed_components_node_selector END
cq_by_longhorn_setting_registry_secret_down_sampling                                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_registry_secret_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_registry_secret_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_registry_secret END
cq_by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_down_sampling CREATE CONTINUOUS QUERY cq_by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation END
cq_by_longhorn_volume_average_number_of_replicas_down_sampling                                       CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_number_of_replicas_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_average_number_of_replicas) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_number_of_replicas_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_manager_average_memory_usage_bytes_down_sampling                                      CREATE CONTINUOUS QUERY cq_by_longhorn_manager_average_memory_usage_bytes_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_manager_average_memory_usage_bytes) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_manager_average_memory_usage_bytes_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_offline_replica_rebuilding_down_sampling                                      CREATE CONTINUOUS QUERY cq_by_longhorn_setting_offline_replica_rebuilding_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_offline_replica_rebuilding_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_offline_replica_rebuilding END
cq_by_longhorn_setting_auto_cleanup_system_generated_snapshot_down_sampling                          CREATE CONTINUOUS QUERY cq_by_longhorn_setting_auto_cleanup_system_generated_snapshot_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_auto_cleanup_system_generated_snapshot_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_auto_cleanup_system_generated_snapshot END
cq_by_longhorn_setting_backup_concurrent_limit_down_sampling                                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backup_concurrent_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_backup_concurrent_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backup_concurrent_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_average_size_bytes_down_sampling                                               CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_size_bytes_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_average_size_bytes) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_size_bytes_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_failed_backup_ttl_down_sampling                                               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_failed_backup_ttl_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_failed_backup_ttl) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_failed_backup_ttl_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_access_mode_rwo_count_down_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_volume_access_mode_rwo_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_access_mode_rwo_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_access_mode_rwo_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_value_down_sampling                                                                            CREATE CONTINUOUS QUERY cq_by_value_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_value_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_recurring_failed_jobs_history_limit_down_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_recurring_failed_jobs_history_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_recurring_failed_jobs_history_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_recurring_failed_jobs_history_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_restore_volume_recurring_jobs_down_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_restore_volume_recurring_jobs_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_restore_volume_recurring_jobs_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_restore_volume_recurring_jobs END
cq_by_longhorn_setting_auto_salvage_down_sampling                                                    CREATE CONTINUOUS QUERY cq_by_longhorn_setting_auto_salvage_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_auto_salvage_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_auto_salvage END
cq_by_longhorn_setting_backup_compression_method_down_sampling                                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backup_compression_method_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backup_compression_method_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backup_compression_method END
cq_by_longhorn_setting_backup_target_down_sampling                                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backup_target_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backup_target_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backup_target END
cq_by_longhorn_setting_disable_revision_counter_down_sampling                                        CREATE CONTINUOUS QUERY cq_by_longhorn_setting_disable_revision_counter_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_disable_revision_counter_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_disable_revision_counter END
cq_by_longhorn_instance_manager_average_memory_usage_bytes_down_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_instance_manager_average_memory_usage_bytes_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_instance_manager_average_memory_usage_bytes) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_instance_manager_average_memory_usage_bytes_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_engine_replica_timeout_down_sampling                                          CREATE CONTINUOUS QUERY cq_by_longhorn_setting_engine_replica_timeout_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_engine_replica_timeout) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_engine_replica_timeout_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_storage_reserved_percentage_for_default_disk_down_sampling                    CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_reserved_percentage_for_default_disk_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_storage_reserved_percentage_for_default_disk) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_reserved_percentage_for_default_disk_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_replica_zone_soft_anti_affinity_true_count_down_sampling                       CREATE CONTINUOUS QUERY cq_by_longhorn_volume_replica_zone_soft_anti_affinity_true_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_replica_zone_soft_anti_affinity_true_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_replica_zone_soft_anti_affinity_true_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_restore_concurrent_limit_down_sampling                                        CREATE CONTINUOUS QUERY cq_by_longhorn_setting_restore_concurrent_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_restore_concurrent_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_restore_concurrent_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_replica_soft_anti_affinity_false_count_down_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_volume_replica_soft_anti_affinity_false_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_replica_soft_anti_affinity_false_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_replica_soft_anti_affinity_false_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_snapshot_data_integrity_cronjob_down_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_snapshot_data_integrity_cronjob_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_snapshot_data_integrity_cronjob_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_snapshot_data_integrity_cronjob END
cq_by_longhorn_setting_orphan_auto_deletion_down_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_orphan_auto_deletion_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_orphan_auto_deletion_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_orphan_auto_deletion END
cq_by_longhorn_setting_guaranteed_instance_manager_cpu_down_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_guaranteed_instance_manager_cpu_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_guaranteed_instance_manager_cpu_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_guaranteed_instance_manager_cpu END
cq_by_longhorn_volume_snapshot_data_integrity_disabled_count_down_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_volume_snapshot_data_integrity_disabled_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_snapshot_data_integrity_disabled_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_snapshot_data_integrity_disabled_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_offline_replica_rebuilding_enabled_count_down_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_volume_offline_replica_rebuilding_enabled_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_offline_replica_rebuilding_enabled_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_offline_replica_rebuilding_enabled_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_snapshot_data_integrity_down_sampling                                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_snapshot_data_integrity_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_snapshot_data_integrity_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_snapshot_data_integrity END
cq_by_longhorn_setting_replica_replenishment_wait_interval_down_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_replenishment_wait_interval_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_replica_replenishment_wait_interval) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_replenishment_wait_interval_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_replica_file_sync_http_client_timeout_down_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_file_sync_http_client_timeout_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_replica_file_sync_http_client_timeout) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_file_sync_http_client_timeout_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_v2_data_engine_down_sampling                                                  CREATE CONTINUOUS QUERY cq_by_longhorn_setting_v2_data_engine_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_v2_data_engine_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_v2_data_engine END
cq_by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_down_sampling               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly END
cq_by_longhorn_volume_data_locality_disabled_count_down_sampling                                     CREATE CONTINUOUS QUERY cq_by_longhorn_volume_data_locality_disabled_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_data_locality_disabled_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_data_locality_disabled_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_default_replica_count_down_sampling                                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_default_replica_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_default_replica_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_default_replica_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_down_sampling                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_concurrent_volume_backup_restore_per_node_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_data_locality_best_effort_count_down_sampling                                  CREATE CONTINUOUS QUERY cq_by_longhorn_volume_data_locality_best_effort_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_data_locality_best_effort_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_data_locality_best_effort_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_down_sampling                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_concurrent_replica_rebuild_per_node_limit) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_kubernetes_version_down_sampling                                                               CREATE CONTINUOUS QUERY cq_by_kubernetes_version_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_kubernetes_version_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), kubernetes_version END
cq_by_longhorn_setting_replica_auto_balance_down_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_auto_balance_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_auto_balance_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_auto_balance END
cq_by_longhorn_volume_replica_auto_balance_disabled_count_down_sampling                              CREATE CONTINUOUS QUERY cq_by_longhorn_volume_replica_auto_balance_disabled_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_replica_auto_balance_disabled_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_replica_auto_balance_disabled_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_frontend_blockdev_count_down_sampling                                          CREATE CONTINUOUS QUERY cq_by_longhorn_volume_frontend_blockdev_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_frontend_blockdev_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_frontend_blockdev_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_allow_recurring_job_while_volume_detached_down_sampling                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_allow_recurring_job_while_volume_detached_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_allow_recurring_job_while_volume_detached_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_allow_recurring_job_while_volume_detached END
cq_by_longhorn_node_count_down_sampling                                                              CREATE CONTINUOUS QUERY cq_by_longhorn_node_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_node_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_node_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_storage_network_down_sampling                                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_network_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_network_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_storage_network END
cq_by_longhorn_volume_average_actual_size_bytes_down_sampling                                        CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_actual_size_bytes_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_average_actual_size_bytes) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_actual_size_bytes_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_volume_offline_replica_rebuilding_disabled_count_down_sampling                        CREATE CONTINUOUS QUERY cq_by_longhorn_volume_offline_replica_rebuilding_disabled_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_offline_replica_rebuilding_disabled_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_offline_replica_rebuilding_disabled_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_replica_soft_anti_affinity_down_sampling                                      CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_soft_anti_affinity_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_soft_anti_affinity_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_soft_anti_affinity END
cq_by_kubernetes_node_provider_down_sampling                                                         CREATE CONTINUOUS QUERY cq_by_kubernetes_node_provider_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_kubernetes_node_provider_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), kubernetes_node_provider END
cq_by_longhorn_setting_backing_image_recovery_wait_interval_down_sampling                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backing_image_recovery_wait_interval_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_backing_image_recovery_wait_interval) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backing_image_recovery_wait_interval_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_node_down_pod_deletion_policy_down_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_node_down_pod_deletion_policy_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_node_down_pod_deletion_policy_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_node_down_pod_deletion_policy END
cq_by_longhorn_setting_storage_minimal_available_percentage_down_sampling                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_minimal_available_percentage_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_setting_storage_minimal_available_percentage) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_minimal_available_percentage_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_taint_toleration_down_sampling                                                CREATE CONTINUOUS QUERY cq_by_longhorn_setting_taint_toleration_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_taint_toleration_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_taint_toleration END
cq_by_longhorn_volume_access_mode_rwx_count_down_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_volume_access_mode_rwx_count_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_volume_access_mode_rwx_count) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_access_mode_rwx_count_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_setting_crd_api_version_down_sampling                                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_crd_api_version_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_crd_api_version_count_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_crd_api_version END
cq_by_longhorn_instance_manager_average_cpu_usage_milli_cores_down_sampling                          CREATE CONTINUOUS QUERY cq_by_longhorn_instance_manager_average_cpu_usage_milli_cores_down_sampling ON longhorn_upgrade_responder BEGIN SELECT mean(longhorn_instance_manager_average_cpu_usage_milli_cores) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_instance_manager_average_cpu_usage_milli_cores_mean_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
```

**And** Wait for couple hours.  
**Then** Measurements created.
```bash
kubectl exec -it ${influxdb_pod} -- influx -execute 'SHOW MEASUREMENTS' -database="${app_name}_upgrade_responder"
```
Sample output:
```
name: measurements
name
----
by_app_version_down_sampling
by_country_code_down_sampling
by_host_kernel_release_count_down_sampling
by_host_os_distro_count_down_sampling
by_kubernetes_node_provider_count_down_sampling
by_kubernetes_version_count_down_sampling
by_longhorn_instance_manager_average_cpu_usage_milli_cores_mean_down_sampling
by_longhorn_instance_manager_average_memory_usage_bytes_mean_down_sampling
by_longhorn_manager_average_cpu_usage_milli_cores_mean_down_sampling
by_longhorn_manager_average_memory_usage_bytes_mean_down_sampling
by_longhorn_namespace_uid_count_down_sampling
by_longhorn_node_count_mean_down_sampling
by_longhorn_node_disk_ssd_count_mean_down_sampling
by_longhorn_setting_allow_recurring_job_while_volume_detached_count_down_sampling
by_longhorn_setting_allow_volume_creation_with_degraded_availability_count_down_sampling
by_longhorn_setting_auto_cleanup_system_generated_snapshot_count_down_sampling
by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_count_down_sampling
by_longhorn_setting_auto_salvage_count_down_sampling
by_longhorn_setting_backing_image_cleanup_wait_interval_mean_down_sampling
by_longhorn_setting_backing_image_recovery_wait_interval_mean_down_sampling
by_longhorn_setting_backup_compression_method_count_down_sampling
by_longhorn_setting_backup_concurrent_limit_mean_down_sampling
by_longhorn_setting_backup_target_count_down_sampling
by_longhorn_setting_backupstore_poll_interval_mean_down_sampling
by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_mean_down_sampling
by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_mean_down_sampling
by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_mean_down_sampling
by_longhorn_setting_crd_api_version_count_down_sampling
by_longhorn_setting_create_default_disk_labeled_nodes_count_down_sampling
by_longhorn_setting_default_data_locality_count_down_sampling
by_longhorn_setting_default_replica_count_mean_down_sampling
by_longhorn_setting_disable_revision_counter_count_down_sampling
by_longhorn_setting_disable_scheduling_on_cordoned_node_count_down_sampling
by_longhorn_setting_engine_replica_timeout_mean_down_sampling
by_longhorn_setting_failed_backup_ttl_mean_down_sampling
by_longhorn_setting_fast_replica_rebuild_enabled_count_down_sampling
by_longhorn_setting_guaranteed_instance_manager_cpu_count_down_sampling
by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_count_down_sampling
by_longhorn_setting_node_down_pod_deletion_policy_count_down_sampling
by_longhorn_setting_node_drain_policy_count_down_sampling
by_longhorn_setting_offline_replica_rebuilding_count_down_sampling
by_longhorn_setting_orphan_auto_deletion_count_down_sampling
by_longhorn_setting_priority_class_count_down_sampling
by_longhorn_setting_recurring_failed_jobs_history_limit_mean_down_sampling
by_longhorn_setting_recurring_successful_jobs_history_limit_mean_down_sampling
by_longhorn_setting_registry_secret_count_down_sampling
by_longhorn_setting_remove_snapshots_during_filesystem_trim_count_down_sampling
by_longhorn_setting_replica_auto_balance_count_down_sampling
by_longhorn_setting_replica_file_sync_http_client_timeout_mean_down_sampling
by_longhorn_setting_replica_replenishment_wait_interval_mean_down_sampling
by_longhorn_setting_replica_soft_anti_affinity_count_down_sampling
by_longhorn_setting_replica_zone_soft_anti_affinity_count_down_sampling
by_longhorn_setting_restore_concurrent_limit_mean_down_sampling
by_longhorn_setting_restore_volume_recurring_jobs_count_down_sampling
by_longhorn_setting_snapshot_data_integrity_count_down_sampling
by_longhorn_setting_snapshot_data_integrity_cronjob_count_down_sampling
by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_count_down_sampling
by_longhorn_setting_storage_minimal_available_percentage_mean_down_sampling
by_longhorn_setting_storage_network_count_down_sampling
by_longhorn_setting_storage_over_provisioning_percentage_mean_down_sampling
by_longhorn_setting_storage_reserved_percentage_for_default_disk_mean_down_sampling
by_longhorn_setting_support_bundle_failed_history_limit_mean_down_sampling
by_longhorn_setting_system_managed_components_node_selector_count_down_sampling
by_longhorn_setting_system_managed_pods_image_pull_policy_count_down_sampling
by_longhorn_setting_taint_toleration_count_down_sampling
by_longhorn_setting_v2_data_engine_count_down_sampling
by_longhorn_volume_access_mode_rwo_count_mean_down_sampling
by_longhorn_volume_access_mode_rwx_count_mean_down_sampling
by_longhorn_volume_average_actual_size_bytes_mean_down_sampling
by_longhorn_volume_average_number_of_replicas_mean_down_sampling
by_longhorn_volume_average_size_bytes_mean_down_sampling
by_longhorn_volume_average_snapshot_count_mean_down_sampling
by_longhorn_volume_data_locality_best_effort_count_mean_down_sampling
by_longhorn_volume_data_locality_disabled_count_mean_down_sampling
by_longhorn_volume_data_locality_strict_local_count_mean_down_sampling
by_longhorn_volume_frontend_blockdev_count_mean_down_sampling
by_longhorn_volume_offline_replica_rebuilding_disabled_count_mean_down_sampling
by_longhorn_volume_offline_replica_rebuilding_enabled_count_mean_down_sampling
by_longhorn_volume_replica_auto_balance_disabled_count_mean_down_sampling
by_longhorn_volume_replica_soft_anti_affinity_false_count_mean_down_sampling
by_longhorn_volume_replica_zone_soft_anti_affinity_true_count_mean_down_sampling
by_longhorn_volume_restore_volume_recurring_job_false_count_mean_down_sampling
by_longhorn_volume_snapshot_data_integrity_disabled_count_mean_down_sampling
by_longhorn_volume_snapshot_data_integrity_fast_check_count_mean_down_sampling
by_longhorn_volume_unmap_mark_snap_chain_removed_false_count_mean_down_sampling
by_value_count_down_sampling
upgrade_request
upgrade_request_down_sampling
```

**When** [Setup Grafana upgrade responder panels](https://github.com/longhorn/upgrade-responder#2-creating-grafana-dashboard).  
**Then** Should see visualized data.
