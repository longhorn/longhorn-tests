*** Settings ***
Documentation    NFS Backup Target Negative Test Cases

Test Tags    nfs    negative    backup

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/persistentvolume.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/network.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/node.resource

Test Setup    Set up test environment
Test Teardown    Cleanup NFS backup target test resources

*** Variables ***
${nfs_server_ip}    ${EMPTY}

*** Keywords ***
Cleanup NFS backup target test resources
    Run Keyword If    '${nfs_server_ip}' != '${EMPTY}'
    ...    Run Keyword And Ignore Error    Cleanup NFS backup target latency toward ${nfs_server_ip}
    Reset default backupstore
    Cleanup test resources

*** Test Cases ***
NFS Backup Target Should Not Cause Zombie Inspect Processes Under Network Delay
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12896
    ...
    ...    Verify that injecting 30s network delay toward the NFS backup target server
    ...    does not cause longhorn backup inspect processes to accumulate on nodes.
    ...    With soft NFS mount enforcement (fix), processes time out and exit cleanly.
    ...    Without the fix (hard mount), processes hang and accumulate indefinitely.
    ...
    ...    Requires: NFS backup target configured via LONGHORN_BACKUPSTORE env var.
    Skip If    '%{LONGHORN_BACKUPSTORE}'.split('://')[0] != 'nfs'
    ...    reason=Backup target is not NFS; skipping NFS-specific test

    Given Set default backupstore
    And Wait for backupstore ready
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Create backup 0 for volume 0
    And Wait for backup 0 of volume 0 to exist in backup list

    When Set backupstore poll interval to 10 seconds
    ${nfs_server_ip} =    Get NFS backup target server IP
    Set Test Variable    ${nfs_server_ip}
    And Inject NFS backup target latency 30000 ms toward ${nfs_server_ip}
    And Sleep    90s

    Then Backup inspect processes should not exceed 3
