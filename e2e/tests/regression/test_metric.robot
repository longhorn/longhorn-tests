*** Settings ***
Documentation    Metric Test Cases

Test Tags    regression    metric

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/metrics.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource

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
    ${ARCH}=    Get Environment Variable    ARCH    amd64
    IF    '${HOST_PROVIDER}' == "harvester"
        Skip    HAL nodes don't collect SMART metrics
    ELSE IF    "${ARCH}" == "amd64"
        Skip    Require Nitro type instance to collect SMART metrics, which is not available in t2.xlarge instance type that we use for amd64
    END
    Given Setting node-disk-health-monitoring is set to true
    Then Metric longhorn_disk_health value should be 1
    And Metric longhorn_disk_health_attribute_raw value should be 0

    When Setting node-disk-health-monitoring is set to false
    Then There should be no longhorn_disk_health metric
    And There should be no longhorn_disk_health_attribute_raw metric

Test Metrics Scrape Sources NetworkPolicy
    [Tags]    uninstall    helm
    [Documentation]
    ...    Issue: https://github.com/longhorn/longhorn/issues/13947
    ...    1. With networkPolicies.restrictInternalTraffic enabled (default) and
    ...       networkPolicies.metricsScrapeSources left at its default `[]`, a scraper
    ...       pod running in another namespace cannot reach longhorn-manager on TCP/9500,
    ...       so no longhorn_* metrics are visible to it.
    ...    2. After setting networkPolicies.metricsScrapeSources to a peer combining a
    ...       namespaceSelector and podSelector matching the scraper pod, and upgrading
    ...       the chart, the scraper pod can reach TCP/9500 and see longhorn_* metrics.
    ...    3. The chart still renders the same when metricsScrapeSources is left as
    ...       the default empty list, i.e. the existing internal-only policy is unchanged.
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    This test only applies to helm install method
    END

    # deploy a Prometheus-like scraper pod in another namespace
    Given Run command
    ...    kubectl create namespace monitoring
    And Run command
    ...    kubectl run prometheus-scraper -n monitoring --image=curlimages/curl --labels="app=prometheus-scraper" --command -- sleep infinity
    And Run command and wait for output
    ...    kubectl get pods -n monitoring -l app=prometheus-scraper --field-selector=status.phase=Running
    ...    prometheus-scraper

    # by default, networkPolicies.metricsScrapeSources is [], so the scraper pod
    # in another namespace cannot reach longhorn-manager metrics on TCP/9500
    Then Run command in pod monitoring/prometheus-scraper and wait for output
    ...    curl --max-time 5 http://longhorn-backend.longhorn-system:9500/metrics
    ...    Failed to connect to longhorn-backend.longhorn-system:9500

    # opt-in to allow the scraper pod by combining namespaceSelector and podSelector
    # in a single NetworkPolicy peer
    When Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
    ...    custom_cmd=yq -i '.networkPolicies.metricsScrapeSources = [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "monitoring"}}, "podSelector": {"matchLabels": {"app": "prometheus-scraper"}}}]' values.yaml

    # the scraper pod can now reach longhorn-manager metrics on TCP/9500
    Then Run command in pod monitoring/prometheus-scraper and wait for output
    ...    curl --max-time 5 http://longhorn-backend.longhorn-system:9500/metrics | grep "longhorn_node_count_total 3"
    ...    longhorn_node_count_total 3

    [Teardown]    Run Keywords
    ...    Run command    kubectl delete namespace monitoring --ignore-not-found
    ...    AND    Cleanup test resources
