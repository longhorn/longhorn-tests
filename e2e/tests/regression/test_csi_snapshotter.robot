*** Settings ***
Documentation    CSI Volume Snapshot Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/csi_volume_snapshot.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test CSI Volume Snapshot Associated With Longhorn Snapshot With Deletion Policy Delete
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and healthy
    And Write 256 MB data to file data.txt in deployment 0
    And Record file data.txt checksum in deployment 0 as checksum 0

    When Create csi volume snapshot class 0    type=snap    deletionPolicy=Delete
    And Create csi volume snapshot 0 for persistentvolumeclaim 0
    Then Wait for csi volume snapshot 0 to be ready
    And Longhorn snapshot associated with csi volume snapshot 0 of deployment 0 should be created

    When Create persistentvolumeclaim 1 from csi volume snapshot 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 1 attached and healthy
    Then Check deployment 1 file data.txt checksum matches checksum 0

    When Delete csi volume snapshot 0
    Then Longhorn snapshot associated with csi volume snapshot 0 of deployment 0 should be deleted

Test CSI Volume Snapshot Associated With Longhorn Backup With Deletion Policy Delete
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and healthy
    And Write 256 MB data to file data.txt in deployment 0
    And Record file data.txt checksum in deployment 0 as checksum 0

    When Create csi volume snapshot class 0    type=bak    deletionPolicy=Delete
    And Create csi volume snapshot 0 for persistentvolumeclaim 0
    Then Wait for csi volume snapshot 0 to be ready
    And Wait for backup associated with csi volume snapshot 0 of deployment 0 to be created

    When Create volume 1 from deployment 0 volume latest backup
    And Create persistentvolume for volume 1
    And Create persistentvolumeclaim for volume 1
    And Create pod 1 using volume 1
    And Wait for pod 1 running
    Then Check pod 1 file data.txt checksum matches checksum 0

    When Delete csi volume snapshot 0
    Then Wait for backup associated with csi volume snapshot 0 of deployment 0 to be deleted

Test CSI Volume Snapshot Associated With Longhorn Snapshot With Deletion Policy Retain
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and healthy
    And Write 256 MB data to file data.txt in deployment 0
    And Record file data.txt checksum in deployment 0 as checksum 0

    When Create csi volume snapshot class 0    type=snap    deletionPolicy=Retain
    And Create csi volume snapshot 0 for persistentvolumeclaim 0
    Then Wait for csi volume snapshot 0 to be ready
    And Longhorn snapshot associated with csi volume snapshot 0 of deployment 0 should be created

    When Create persistentvolumeclaim 1 from csi volume snapshot 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 1 attached and healthy
    Then Check deployment 1 file data.txt checksum matches checksum 0

    When Delete csi volume snapshot 0
    Then Longhorn snapshot associated with csi volume snapshot 0 of deployment 0 should still exist

Test CSI Volume Snapshot Associated With Longhorn Backup With Deletion Policy Retain
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and healthy
    And Write 256 MB data to file data.txt in deployment 0
    And Record file data.txt checksum in deployment 0 as checksum 0

    When Create csi volume snapshot class 0    type=bak    deletionPolicy=Retain
    And Create csi volume snapshot 0 for persistentvolumeclaim 0
    Then Wait for csi volume snapshot 0 to be ready
    And Wait for backup associated with csi volume snapshot 0 of deployment 0 to be created

    When Create volume 1 from deployment 0 volume latest backup
    And Create persistentvolume for volume 1
    And Create persistentvolumeclaim for volume 1
    And Create pod 1 using volume 1
    And Wait for pod 1 running
    Then Check pod 1 file data.txt checksum matches checksum 0

    When Delete csi volume snapshot 0
    Then Backup associated with csi volume snapshot 0 of deployment 0 should still exist
