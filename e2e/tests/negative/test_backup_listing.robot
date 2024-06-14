*** Settings ***
Documentation    Test backup listing
...              https://longhorn.github.io/longhorn-tests/manual/pre-release/stress/backup-listing/

Test Tags    manual

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource


Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1001
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Keywords ***
Verify backup ${backup_id} count for ${workload_kind} ${workload_id} volume 
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    ${expected_backup_count}=  Evaluate  ${backup_id} + 1
    verify_backup_count    ${volume_name}    ${expected_backup_count}

Create volume ${volume_id} from ${workload_kind} ${workload_id} volume random backup
    ${volume_id}=  Convert To String  ${volume_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name}=    get_workload_volume_name    ${workload_name}
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    ${backup_id}=  Evaluate  random.randint(0, ${LOOP_COUNT}-1)
    ${backup_id}=  Convert To String  ${backup_id}
    ${backup_url}=    get_backup_url    ${backup_id}    ${workload_volume_name}
    create_volume   ${volume_name}    size=3Gi    numberOfReplicas=3    fromBackup=${backup_url}    dataEngine=${DATA_ENGINE}
    Set Test Variable    ${random_backup_id}    ${backup_id}

Create deployment ${deployment_id} with volume ${volume_id}
    ${volume_id}=  Convert To String  ${volume_id}
    Create persistentvolume for volume ${volume_id}
    Create persistentvolumeclaim for volume ${volume_id}
    ${deployment_name}=    generate_name_with_suffix    deployment    ${deployment_id}
    ${pvc_name}=    generate_name_with_suffix    volume    ${volume_id}
    create_deployment    ${deployment_name}   ${pvc_name}

Check volume ${volume_id} data is ${workload_kind} ${workload_id} volume backup ${backup_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name}=    get_workload_volume_name    ${workload_name}
    ${backup_name}=    get_backup_name    ${backup_id}    ${workload_volume_name}
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    check_restored_volume_checksum    ${volume_name}    ${backup_name}

Check volume ${volume_id} data is intact
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    check_data_checksum    ${volume_name}

Check volume ${volume_id} data is data ${data_id}
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    check_data_checksum    ${volume_name}    ${data_id}

Get ${workload_kind} ${workload_id} volume data in file ${file_name}
    ${workload_name}=    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${current_file_checksum}=    get_workload_pod_data_checksum    ${workload_name}    ${file_name}
    [Return]  ${current_file_checksum}

Volume ${volume_id} data should same as ${workload_kind} ${workload_id} volume
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name}=    get_workload_volume_name    ${workload_name}
    ${backup_name}=    get_backup_name    ${random_backup_id}    ${workload_volume_name}
    ${expected_file_checksum}=    get_restored_checksum    ${backup_name}
    ${current_file_checksum}=  Get ${workload_kind} ${volume_id} volume data in file data
    Should Be Equal  ${current_file_checksum}  ${expected_file_checksum}

Perform backup 1001 times for deployment 0 volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Create backup ${i} for deployment 0 volume
        Delete snapshot ${i} of deployment 0 volume
        IF    ${i} % 249 == 0
            ${workload_name}=   generate_name_with_suffix    deployment    0
            ${volume_name}=    get_workload_volume_name    ${workload_name}
            purge_snapshot    ${volume_name}
        END
        Verify backup list contains backup no error for deployment 0 volume
        Verify backup ${i} count for deployment 0 volume
        Verify backup list contains backup ${i} of deployment 0 volume 
    END

Create pod ${pod_id} mount ${size} GB volume ${volume_id}
    Create volume ${volume_id} with    size=${size}Gi    numberOfReplicas=3
    Create persistentvolume for volume ${volume_id}
    Create persistentvolumeclaim for volume ${volume_id}
    Create pod ${pod_id} using volume ${volume_id}
    Wait for pod ${pod_id} running

Volume ${volume_id} backup ${backup_id} should be able to create
    Create backup ${backup_id} for volume ${volume_id}
    Verify backup list contains no error for volume ${volume_id}
    Verify backup list contains backup ${backup_id} of volume ${volume_id}

Write data to file in deployment 0
    Write 100 MB data to file data in deployment 0

Write 210 GB data in pod 2
    FOR    ${i}    IN RANGE    21
        Write 10 GB data to file ${i} in pod 2
    END

Write 150 GB data in pod 3
    FOR    ${i}    IN RANGE    15
        Write 10 GB data to file ${i} in pod 3
    END

Write 40 GB data in pod 3
    FOR    ${i}    IN RANGE    15    19
        Write 10 GB data to file ${i} in pod 3
    END

*** Test Cases ***
Backup listing with more than 1000 backups
    [Tags]  manual  longhorn-8355
    [Documentation]    Test backup listing
    Given Create persistentvolumeclaim 0 using RWO volume
    And Create deployment 0 with persistentvolumeclaim 0
    And Write data to file in deployment 0
    Then Perform backup 1001 times for deployment 0 volume
    Then Create volume 1 from deployment 0 volume random backup
    And Create deployment 1 with volume 1
    Then Get deployment 1 volume data in file data
    And Volume 1 data should same as deployment 0 volume

Backup listing of volume bigger than 200 Gi
    [Tags]  manual  longhorn-8355
    [Documentation]    Test backup bigger than 200 Gi
    Given Create persistentvolumeclaim 0 using RWO volume
    And Create deployment 0 with persistentvolumeclaim 0
    And Write data to file in deployment 0
    Then Perform backup 1001 times for deployment 0 volume
    Then Create volume 1 from deployment 0 volume random backup
    And Create deployment 1 with volume 1
    Then Get deployment 1 volume data in file data
    And Volume 1 data should same as deployment 0 volume
    Then Create pod 2 mount 250 GB volume 2
    And Write 210 GB data in pod 2
    Then Volume 2 backup 0 should be able to create
    Then Create pod 3 mount 200 GB volume 3
    And Write 150 GB data in pod 3
    Then Volume 3 backup 0 should be able to create
    And Write 40 GB data in pod 3
    Then Volume 3 backup 1 should be able to create