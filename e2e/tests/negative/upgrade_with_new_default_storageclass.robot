*** Settings ***
Documentation    Manual Test Cases
Test Tags    upgrade    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test system upgrade with a new storage class being default
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    Given Set setting deleting-confirmation-flag to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    And Create storageclass longhorn-rep-2 with    dataEngine=${DATA_ENGINE}    numberOfReplicas=2
    And Set storageclass longhorn-rep-2 as default
    And Remove default from storageClass longhorn
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=${None}
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=${None}
    And Assert persistentvolumeclaim 0 is using storageclass longhorn-rep-2
    And Assert persistentvolumeclaim 1 is using storageclass longhorn-rep-2
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 100 MB data to file data.bin in deployment 0
    And Write 100 MB data to file data.bin in deployment 1

    When Upgrade Longhorn to custom version
    And Assert storageClass longhorn-rep-2 is default storageclass
    And Create persistentvolumeclaim 2    volume_type=RWO    sc_name=longhorn-rep-2
    And Create persistentvolumeclaim 3    volume_type=RWX    sc_name=longhorn
    And Assert persistentvolumeclaim 2 is using storageclass longhorn-rep-2
    And Assert persistentvolumeclaim 3 is using storageclass longhorn
    And Create deployment 2 with persistentvolumeclaim 2
    And Create deployment 3 with persistentvolumeclaim 3
    And Wait for volume of deployment 2 healthy
    And Wait for volume of deployment 3 healthy
    And Write 100 MB data to file data.bin in deployment 2
    And Write 100 MB data to file data.bin in deployment 3

    When Check deployment 0 data in file data.bin is intact
    And Check deployment 1 data in file data.bin is intact
    And Check deployment 2 data in file data.bin is intact
    And Check deployment 3 data in file data.bin is intact
