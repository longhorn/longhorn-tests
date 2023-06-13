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

kubectl exec -it ${influxdb_pod} -- influx -execute 'SELECT * FROM upgrade_request' -database="${app_name}_upgrade_responder"
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
name: longhorn_upgrade_responder
name                                                                                            query
----                                                                                            -----
cq_by_app_version_down_sampling                                                                 CREATE CONTINUOUS QUERY cq_by_app_version_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_app_version_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), app_version END
cq_by_country_code_down_sampling                                                                CREATE CONTINUOUS QUERY cq_by_country_code_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_country_code_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), country_isocode END
cq_upgrade_request_down_sampling                                                                CREATE CONTINUOUS QUERY cq_upgrade_request_down_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.upgrade_request_down_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h) END
cq_by_longhorn_instance_manager_average_cpu_usage_core_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_instance_manager_average_cpu_usage_core_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_instance_manager_average_cpu_usage_core_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_instance_manager_average_cpu_usage_core END
cq_by_longhorn_manager_average_memory_usage_mib_sampling                                        CREATE CONTINUOUS QUERY cq_by_longhorn_manager_average_memory_usage_mib_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_manager_average_memory_usage_mib_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_manager_average_memory_usage_mib END
cq_by_longhorn_setting_crd_api_version_sampling                                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_crd_api_version_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_crd_api_version_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_crd_api_version END
cq_by_longhorn_setting_fast_replica_rebuild_enabled_sampling                                    CREATE CONTINUOUS QUERY cq_by_longhorn_setting_fast_replica_rebuild_enabled_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_fast_replica_rebuild_enabled_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_fast_replica_rebuild_enabled END
cq_by_longhorn_setting_restore_concurrent_limit_sampling                                        CREATE CONTINUOUS QUERY cq_by_longhorn_setting_restore_concurrent_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_restore_concurrent_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_restore_concurrent_limit END
cq_by_longhorn_setting_storage_network_sampling                                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_network_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_network_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_storage_network END
cq_by_host_kernel_release_sampling                                                              CREATE CONTINUOUS QUERY cq_by_host_kernel_release_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_host_kernel_release_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), host_kernel_release END
cq_by_longhorn_node_disk_nvme_count_sampling                                                    CREATE CONTINUOUS QUERY cq_by_longhorn_node_disk_nvme_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_node_disk_nvme_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_node_disk_nvme_count END
cq_by_longhorn_setting_auto_cleanup_system_generated_snapshot_sampling                          CREATE CONTINUOUS QUERY cq_by_longhorn_setting_auto_cleanup_system_generated_snapshot_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_auto_cleanup_system_generated_snapshot_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_auto_cleanup_system_generated_snapshot END
cq_by_longhorn_setting_backupstore_poll_interval_sampling                                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backupstore_poll_interval_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backupstore_poll_interval_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backupstore_poll_interval END
cq_by_longhorn_setting_replica_auto_balance_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_auto_balance_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_auto_balance_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_auto_balance END
cq_by_longhorn_ui_average_memory_usage_mib_sampling                                             CREATE CONTINUOUS QUERY cq_by_longhorn_ui_average_memory_usage_mib_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_ui_average_memory_usage_mib_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_ui_average_memory_usage_mib END
cq_by_longhorn_setting_replica_zone_soft_anti_affinity_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_zone_soft_anti_affinity_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_zone_soft_anti_affinity_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_zone_soft_anti_affinity END
cq_by_longhorn_volume_access_mode_rwo_count_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_volume_access_mode_rwo_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_access_mode_rwo_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_access_mode_rwo_count END
cq_by_longhorn_setting_restore_volume_recurring_jobs_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_restore_volume_recurring_jobs_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_restore_volume_recurring_jobs_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_restore_volume_recurring_jobs END
cq_by_kubernetes_version_sampling                                                               CREATE CONTINUOUS QUERY cq_by_kubernetes_version_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_kubernetes_version_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), kubernetes_version END
cq_by_longhorn_setting_storage_minimal_available_percentage_sampling                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_minimal_available_percentage_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_minimal_available_percentage_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_storage_minimal_available_percentage END
cq_by_longhorn_setting_backing_image_cleanup_wait_interval_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backing_image_cleanup_wait_interval_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backing_image_cleanup_wait_interval_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backing_image_cleanup_wait_interval END
cq_by_longhorn_setting_system_managed_components_node_selector_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_system_managed_components_node_selector_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_system_managed_components_node_selector_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_system_managed_components_node_selector END
cq_by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_kubernetes_cluster_autoscaler_enabled END
cq_by_longhorn_volume_average_number_of_replicas_sampling                                       CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_number_of_replicas_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_number_of_replicas_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_average_number_of_replicas END
cq_by_longhorn_setting_node_down_pod_deletion_policy_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_node_down_pod_deletion_policy_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_node_down_pod_deletion_policy_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_node_down_pod_deletion_policy END
cq_by_longhorn_setting_replica_soft_anti_affinity_sampling                                      CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_soft_anti_affinity_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_soft_anti_affinity_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_soft_anti_affinity END
cq_by_host_os_distro_sampling                                                                   CREATE CONTINUOUS QUERY cq_by_host_os_distro_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_host_os_distro_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), host_os_distro END
cq_by_longhorn_node_count_sampling                                                              CREATE CONTINUOUS QUERY cq_by_longhorn_node_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_node_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_node_count END
cq_by_longhorn_setting_allow_node_drain_with_last_healthy_replica_sampling                      CREATE CONTINUOUS QUERY cq_by_longhorn_setting_allow_node_drain_with_last_healthy_replica_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_allow_node_drain_with_last_healthy_replica_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_allow_node_drain_with_last_healthy_replica END
cq_by_longhorn_setting_allow_volume_creation_with_degraded_availability_sampling                CREATE CONTINUOUS QUERY cq_by_longhorn_setting_allow_volume_creation_with_degraded_availability_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_allow_volume_creation_with_degraded_availability_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_allow_volume_creation_with_degraded_availability END
cq_by_longhorn_setting_snapshot_data_integrity_sampling                                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_snapshot_data_integrity_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_snapshot_data_integrity_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_snapshot_data_integrity END
cq_by_longhorn_namespace_uid_sampling                                                           CREATE CONTINUOUS QUERY cq_by_longhorn_namespace_uid_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_namespace_uid_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_namespace_uid END
cq_by_longhorn_setting_engine_replica_timeout_sampling                                          CREATE CONTINUOUS QUERY cq_by_longhorn_setting_engine_replica_timeout_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_engine_replica_timeout_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_engine_replica_timeout END
cq_by_longhorn_setting_default_data_locality_sampling                                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_default_data_locality_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_default_data_locality_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_default_data_locality END
cq_by_longhorn_setting_registry_secret_sampling                                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_registry_secret_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_registry_secret_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_registry_secret END
cq_by_longhorn_setting_failed_backup_ttl_sampling                                               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_failed_backup_ttl_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_failed_backup_ttl_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_failed_backup_ttl END
cq_by_longhorn_instance_manager_average_memory_usage_mib_sampling                               CREATE CONTINUOUS QUERY cq_by_longhorn_instance_manager_average_memory_usage_mib_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_instance_manager_average_memory_usage_mib_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_instance_manager_average_memory_usage_mib END
cq_by_longhorn_setting_recurring_failed_jobs_history_limit_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_recurring_failed_jobs_history_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_recurring_failed_jobs_history_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_recurring_failed_jobs_history_limit END
cq_by_kubernetes_node_provider_sampling                                                         CREATE CONTINUOUS QUERY cq_by_kubernetes_node_provider_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_kubernetes_node_provider_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), kubernetes_node_provider END
cq_by_longhorn_setting_storage_over_provisioning_percentage_sampling                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_over_provisioning_percentage_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_over_provisioning_percentage_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_storage_over_provisioning_percentage END
cq_by_longhorn_volume_average_actual_size_sampling                                              CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_actual_size_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_actual_size_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_average_actual_size END
cq_by_longhorn_volume_frontend_blockdev_count_sampling                                          CREATE CONTINUOUS QUERY cq_by_longhorn_volume_frontend_blockdev_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_frontend_blockdev_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_frontend_blockdev_count END
cq_by_longhorn_engine_image_average_memory_usage_mib_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_engine_image_average_memory_usage_mib_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_engine_image_average_memory_usage_mib_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_engine_image_average_memory_usage_mib END
cq_by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_sampling                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_concurrent_replica_rebuild_per_node_limit END
cq_by_longhorn_setting_backing_image_recovery_wait_interval_sampling                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backing_image_recovery_wait_interval_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backing_image_recovery_wait_interval_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backing_image_recovery_wait_interval END
cq_by_longhorn_setting_disable_scheduling_on_cordoned_node_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_disable_scheduling_on_cordoned_node_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_disable_scheduling_on_cordoned_node_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_disable_scheduling_on_cordoned_node END
cq_by_longhorn_setting_backup_target_sampling                                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backup_target_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backup_target_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backup_target END
cq_by_longhorn_setting_priority_class_sampling                                                  CREATE CONTINUOUS QUERY cq_by_longhorn_setting_priority_class_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_priority_class_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_priority_class END
cq_by_longhorn_ui_average_cpu_usage_core_sampling                                               CREATE CONTINUOUS QUERY cq_by_longhorn_ui_average_cpu_usage_core_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_ui_average_cpu_usage_core_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_ui_average_cpu_usage_core END
cq_by_longhorn_setting_guaranteed_replica_manager_cpu_sampling                                  CREATE CONTINUOUS QUERY cq_by_longhorn_setting_guaranteed_replica_manager_cpu_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_guaranteed_replica_manager_cpu_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_guaranteed_replica_manager_cpu END
cq_by_longhorn_setting_node_drain_policy_sampling                                               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_node_drain_policy_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_node_drain_policy_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_node_drain_policy END
cq_by_longhorn_setting_support_bundle_failed_history_limit_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_support_bundle_failed_history_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_support_bundle_failed_history_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_support_bundle_failed_history_limit END
cq_by_longhorn_setting_default_replica_count_sampling                                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_default_replica_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_default_replica_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_default_replica_count END
cq_by_longhorn_volume_average_snapshot_count_sampling                                           CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_snapshot_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_snapshot_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_average_snapshot_count END
cq_by_longhorn_setting_system_managed_pods_image_pull_policy_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_system_managed_pods_image_pull_policy_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_system_managed_pods_image_pull_policy_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_system_managed_pods_image_pull_policy END
cq_by_longhorn_setting_disable_revision_counter_sampling                                        CREATE CONTINUOUS QUERY cq_by_longhorn_setting_disable_revision_counter_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_disable_revision_counter_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_disable_revision_counter END
cq_by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_sampling              CREATE CONTINUOUS QUERY cq_by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit END
cq_by_longhorn_setting_snapshot_data_integrity_cronjob_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_snapshot_data_integrity_cronjob_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_snapshot_data_integrity_cronjob_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_snapshot_data_integrity_cronjob END
cq_by_longhorn_setting_backup_compression_method_sampling                                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backup_compression_method_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backup_compression_method_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backup_compression_method END
cq_by_longhorn_setting_guaranteed_instance_manager_cpu_sampling                                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_guaranteed_instance_manager_cpu_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_guaranteed_instance_manager_cpu_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_guaranteed_instance_manager_cpu END
cq_by_longhorn_setting_allow_recurring_job_while_volume_detached_sampling                       CREATE CONTINUOUS QUERY cq_by_longhorn_setting_allow_recurring_job_while_volume_detached_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_allow_recurring_job_while_volume_detached_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_allow_recurring_job_while_volume_detached END
cq_by_longhorn_engine_image_average_cpu_usage_core_sampling                                     CREATE CONTINUOUS QUERY cq_by_longhorn_engine_image_average_cpu_usage_core_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_engine_image_average_cpu_usage_core_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_engine_image_average_cpu_usage_core END
cq_by_longhorn_setting_guaranteed_engine_manager_cpu_sampling                                   CREATE CONTINUOUS QUERY cq_by_longhorn_setting_guaranteed_engine_manager_cpu_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_guaranteed_engine_manager_cpu_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_guaranteed_engine_manager_cpu END
cq_by_longhorn_volume_data_locality_disabled_count_sampling                                     CREATE CONTINUOUS QUERY cq_by_longhorn_volume_data_locality_disabled_count_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_data_locality_disabled_count_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_data_locality_disabled_count END
cq_by_longhorn_setting_replica_replenishment_wait_interval_sampling                             CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_replenishment_wait_interval_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_replenishment_wait_interval_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_replenishment_wait_interval END
cq_by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_sampling CREATE CONTINUOUS QUERY cq_by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation END
cq_by_longhorn_manager_average_cpu_usage_core_sampling                                          CREATE CONTINUOUS QUERY cq_by_longhorn_manager_average_cpu_usage_core_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_manager_average_cpu_usage_core_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_manager_average_cpu_usage_core END
cq_by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_sampling               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly END
cq_by_longhorn_setting_taint_toleration_sampling                                                CREATE CONTINUOUS QUERY cq_by_longhorn_setting_taint_toleration_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_taint_toleration_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_taint_toleration END
cq_by_longhorn_setting_storage_reserved_percentage_for_default_disk_sampling                    CREATE CONTINUOUS QUERY cq_by_longhorn_setting_storage_reserved_percentage_for_default_disk_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_storage_reserved_percentage_for_default_disk_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_storage_reserved_percentage_for_default_disk END
cq_by_longhorn_setting_recurring_successful_jobs_history_limit_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_recurring_successful_jobs_history_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_recurring_successful_jobs_history_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_recurring_successful_jobs_history_limit END
cq_by_longhorn_setting_replica_file_sync_http_client_timeout_sampling                           CREATE CONTINUOUS QUERY cq_by_longhorn_setting_replica_file_sync_http_client_timeout_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_replica_file_sync_http_client_timeout_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_replica_file_sync_http_client_timeout END
cq_by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_sampling                 CREATE CONTINUOUS QUERY cq_by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_concurrent_volume_backup_restore_per_node_limit END
cq_by_longhorn_setting_create_default_disk_labeled_nodes_sampling                               CREATE CONTINUOUS QUERY cq_by_longhorn_setting_create_default_disk_labeled_nodes_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_create_default_disk_labeled_nodes_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_create_default_disk_labeled_nodes END
cq_by_longhorn_setting_orphan_auto_deletion_sampling                                            CREATE CONTINUOUS QUERY cq_by_longhorn_setting_orphan_auto_deletion_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_orphan_auto_deletion_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_orphan_auto_deletion END
cq_by_longhorn_setting_remove_snapshots_during_filesystem_trim_sampling                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_remove_snapshots_during_filesystem_trim_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_remove_snapshots_during_filesystem_trim_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_remove_snapshots_during_filesystem_trim END
cq_by_longhorn_setting_auto_salvage_sampling                                                    CREATE CONTINUOUS QUERY cq_by_longhorn_setting_auto_salvage_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_auto_salvage_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_auto_salvage END
cq_by_longhorn_setting_backup_concurrent_limit_sampling                                         CREATE CONTINUOUS QUERY cq_by_longhorn_setting_backup_concurrent_limit_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_setting_backup_concurrent_limit_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_setting_backup_concurrent_limit END
cq_by_longhorn_volume_average_size_sampling                                                     CREATE CONTINUOUS QUERY cq_by_longhorn_volume_average_size_sampling ON longhorn_upgrade_responder BEGIN SELECT count(value) AS total INTO longhorn_upgrade_responder.autogen.by_longhorn_volume_average_size_sampling FROM longhorn_upgrade_responder.autogen.upgrade_request GROUP BY time(1h), longhorn_volume_average_size END

name: _internal
name query
---- -----
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
by_host_kernel_release_sampling
by_host_os_distro_sampling
by_kubernetes_node_provider_sampling
by_kubernetes_version_sampling
by_longhorn_engine_image_average_cpu_usage_core_sampling
by_longhorn_engine_image_average_memory_usage_mib_sampling
by_longhorn_instance_manager_average_cpu_usage_core_sampling
by_longhorn_instance_manager_average_memory_usage_mib_sampling
by_longhorn_manager_average_cpu_usage_core_sampling
by_longhorn_manager_average_memory_usage_mib_sampling
by_longhorn_namespace_uid_sampling
by_longhorn_node_count_sampling
by_longhorn_node_disk_nvme_count_sampling
by_longhorn_setting_allow_node_drain_with_last_healthy_replica_sampling
by_longhorn_setting_allow_recurring_job_while_volume_detached_sampling
by_longhorn_setting_allow_volume_creation_with_degraded_availability_sampling
by_longhorn_setting_auto_cleanup_system_generated_snapshot_sampling
by_longhorn_setting_auto_delete_pod_when_volume_detached_unexpectedly_sampling
by_longhorn_setting_auto_salvage_sampling
by_longhorn_setting_backing_image_cleanup_wait_interval_sampling
by_longhorn_setting_backing_image_recovery_wait_interval_sampling
by_longhorn_setting_backup_compression_method_sampling
by_longhorn_setting_backup_concurrent_limit_sampling
by_longhorn_setting_backup_target_sampling
by_longhorn_setting_backupstore_poll_interval_sampling
by_longhorn_setting_concurrent_automatic_engine_upgrade_per_node_limit_sampling
by_longhorn_setting_concurrent_replica_rebuild_per_node_limit_sampling
by_longhorn_setting_concurrent_volume_backup_restore_per_node_limit_sampling
by_longhorn_setting_crd_api_version_sampling
by_longhorn_setting_create_default_disk_labeled_nodes_sampling
by_longhorn_setting_default_data_locality_sampling
by_longhorn_setting_default_replica_count_sampling
by_longhorn_setting_disable_revision_counter_sampling
by_longhorn_setting_disable_scheduling_on_cordoned_node_sampling
by_longhorn_setting_engine_replica_timeout_sampling
by_longhorn_setting_failed_backup_ttl_sampling
by_longhorn_setting_fast_replica_rebuild_enabled_sampling
by_longhorn_setting_guaranteed_engine_manager_cpu_sampling
by_longhorn_setting_guaranteed_instance_manager_cpu_sampling
by_longhorn_setting_guaranteed_replica_manager_cpu_sampling
by_longhorn_setting_kubernetes_cluster_autoscaler_enabled_sampling
by_longhorn_setting_node_down_pod_deletion_policy_sampling
by_longhorn_setting_node_drain_policy_sampling
by_longhorn_setting_orphan_auto_deletion_sampling
by_longhorn_setting_priority_class_sampling
by_longhorn_setting_recurring_failed_jobs_history_limit_sampling
by_longhorn_setting_recurring_successful_jobs_history_limit_sampling
by_longhorn_setting_registry_secret_sampling
by_longhorn_setting_remove_snapshots_during_filesystem_trim_sampling
by_longhorn_setting_replica_auto_balance_sampling
by_longhorn_setting_replica_file_sync_http_client_timeout_sampling
by_longhorn_setting_replica_replenishment_wait_interval_sampling
by_longhorn_setting_replica_soft_anti_affinity_sampling
by_longhorn_setting_replica_zone_soft_anti_affinity_sampling
by_longhorn_setting_restore_concurrent_limit_sampling
by_longhorn_setting_restore_volume_recurring_jobs_sampling
by_longhorn_setting_snapshot_data_integrity_cronjob_sampling
by_longhorn_setting_snapshot_data_integrity_immediate_check_after_snapshot_creation_sampling
by_longhorn_setting_snapshot_data_integrity_sampling
by_longhorn_setting_storage_minimal_available_percentage_sampling
by_longhorn_setting_storage_network_sampling
by_longhorn_setting_storage_over_provisioning_percentage_sampling
by_longhorn_setting_storage_reserved_percentage_for_default_disk_sampling
by_longhorn_setting_support_bundle_failed_history_limit_sampling
by_longhorn_setting_system_managed_components_node_selector_sampling
by_longhorn_setting_system_managed_pods_image_pull_policy_sampling
by_longhorn_setting_taint_toleration_sampling
by_longhorn_ui_average_cpu_usage_core_sampling
by_longhorn_ui_average_memory_usage_mib_sampling
by_longhorn_volume_access_mode_rwo_count_sampling
by_longhorn_volume_average_actual_size_sampling
by_longhorn_volume_average_number_of_replicas_sampling
by_longhorn_volume_average_size_sampling
by_longhorn_volume_average_snapshot_count_sampling
by_longhorn_volume_data_locality_disabled_count_sampling
by_longhorn_volume_frontend_blockdev_count_sampling
upgrade_request
upgrade_request_down_sampling
```

**When** [Setup Grafana upgrade responder panels](https://github.com/longhorn/upgrade-responder#2-creating-grafana-dashboard).  
**Then** Should see visualized data.
