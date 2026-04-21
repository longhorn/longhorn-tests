*** Settings ***
Documentation    Metric Test Cases

Test Tags    regression    metric

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/metrics.resource
Resource    ../keywords/setting.resource

Test Setup    Set up v2 test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks

*** Test Cases ***
Test Longhorn Metrics
    [Documentation]
    ...    Issue: https://github.com/longhorn/longhorn/issues/11949
    ...           https://github.com/longhorn/longhorn/issues/11387
    ...    Notice that some metrics are only collected and stored by its owner node,
    ...    so we can only iterate all nodes to collect the complete metrics
    Given Create volume vol-1 with    size=2Gi    dataEngine=v1
    And Create volume vol-2 with    size=4Gi    dataEngine=v2
    Then Metric longhorn_node_storage_scheduled_bytes value should be 6Gi

    When Attach volume vol-1 to node 0
    And Attach volume vol-2 to node 1
    And Wait for volume vol-1 healthy
    And Wait for volume vol-2 healthy
    And Create backup 0 for volume vol-1
    And Create backup 0 for volume vol-2
    # longhorn_backup_target_backup_volume_count{backup_target="default"} 2
    Then Metric longhorn_backup_target_backup_volume_count value should be 2
    ${vol_1_backup_volume_name} =    Run command
    ...    kubectl get backupvolume -n longhorn-system -o jsonpath='{.items[?(@.spec.volumeName=="vol-1")].metadata.name}'
    ${vol_2_backup_volume_name} =    Run command
    ...    kubectl get backupvolume -n longhorn-system -o jsonpath='{.items[?(@.spec.volumeName=="vol-2")].metadata.name}'
    # longhorn_backup_volume_backups_count{backup_volume="vol-1-xxx"} 1
    And Metric longhorn_backup_volume_backups_count value with label {"backup_volume": "${vol_1_backup_volume_name}"} should be 1
    # longhorn_backup_volume_backups_count{backup_volume="vol-2-xxx"} 1
    And Metric longhorn_backup_volume_backups_count value with label {"backup_volume": "${vol_2_backup_volume_name}"} should be 1
    # longhorn_backup_uploaded_data_size_bytes{backup="backup-1659544965b943dc",recurring_job="",volume="vol-1"} 0
    And Metric longhorn_backup_uploaded_data_size_bytes value with label {"volume": "vol-1"} should be 0
    # longhorn_backup_uploaded_data_size_bytes{backup="backup-6d79f07d12e24dd1",recurring_job="",volume="vol-2"} 0
    And Metric longhorn_backup_uploaded_data_size_bytes value with label {"volume": "vol-2"} should be 0

Test Disable Node Disk Health Monitoring
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12300
    ${HOST_PROVIDER}=    Get Environment Variable    HOST_PROVIDER    vagrant
    IF    '${HOST_PROVIDER}' == "harvester"
        Skip    HAL nodes don't collect SMART metrics
    END
    Given Setting node-disk-health-monitoring is set to true
    Then Metric longhorn_disk_health value should be 1
    And Metric longhorn_disk_health_attribute_raw value should be 0

    When Setting node-disk-health-monitoring is set to false
    Then There should be no longhorn_disk_health metric
    And There should be no longhorn_disk_health_attribute_raw metric
