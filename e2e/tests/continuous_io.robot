*** Settings ***
Documentation    Continuous IO Test

Test Tags    pre-release    continuous-io

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/metrics.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${TEST_DURATION_IN_HOURS}    72

*** Test Cases ***
Continuous IO Test
     [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12140
    ...    Continuous I/O for > 72 hours
    ...    And monitoring memory/cpu usage at the same time
    Given Get Longhorn components resource usage

    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create storageclass strict-local with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-4-2 with    nfsOptions=vers=4.2,noresvport,timeo=450,retrans=8    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-hard-mount with    nfsOptions=hard,timeo=50,retrans=1    dataEngine=${DATA_ENGINE}
    And Create storageclass nfs-soft-mount with    nfsOptions=soft,timeo=250,retrans=5    dataEngine=${DATA_ENGINE}
    And Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    And Create storageclass sc-bi with    backingImage=bi    dataEngine=v1

    And Create persistentvolumeclaim rwo-pvc    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim rwx-pvc    volume_type=RWX    sc_name=longhorn-test
    And Create persistentvolumeclaim strict-local-pvc    volume_type=RWO    sc_name=strict-local
    And Create persistentvolumeclaim rwx-nfs-4-2-pvc    volume_type=RWX    sc_name=nfs-4-2
    And Create persistentvolumeclaim rwx-nfs-hard-mount-pvc    volume_type=RWX    sc_name=nfs-hard-mount
    And Create persistentvolumeclaim rwx-nfs-soft-mount-pvc    volume_type=RWX    sc_name=nfs-soft-mount
    And Create persistentvolumeclaim bi-pvc    sc_name=sc-bi

    And Create deployment rwo-deploy with persistentvolumeclaim rwo-pvc
    And Create deployment rwx-deploy with persistentvolumeclaim rwx-pvc
    And Create deployment strict-local-deploy with persistentvolumeclaim strict-local-pvc
    And Create deployment rwx-nfs-4-2rwx-nfs-4-2-deploy with persistentvolumeclaim rwx-nfs-4-2-pvc
    And Create deployment rwx-nfs-hard-mount-deploy with persistentvolumeclaim rwx-nfs-hard-mount-pvc
    And Create deployment rwx-nfs-soft-mount-deploy with persistentvolumeclaim rwx-nfs-soft-mount-pvc
    And Create deployment bi-deploy with persistentvolumeclaim bi-pvc

    # continuous io in the background
    And Keep writing data to pod of deployment rwo-deploy
    And Keep writing data to pod of deployment rwx-deploy
    And Keep writing data to pod of deployment strict-local-deploy
    And Keep writing data to pod of deployment rwx-nfs-4-2rwx-nfs-4-2-deploy
    And Keep writing data to pod of deployment rwx-nfs-hard-mount-deploy
    And Keep writing data to pod of deployment rwx-nfs-soft-mount-deploy
    And Keep writing data to pod of deployment bi-deploy

    # data integrity check in the foreground
    ${start}=    Get Time    epoch
    ${duration}=    Evaluate    int(${TEST_DURATION_IN_HOURS}) * 60 * 60    # seconds
    ${current}=    Get Time    epoch
    WHILE    ${current} - ${start} < ${duration}
        When Write 100 MB data to file data.txt in deployment rwo-deploy
        And Write 100 MB data to file data.txt in deployment rwx-deploy
        And Write 100 MB data to file data.txt in deployment strict-local-deploy
        And Write 100 MB data to file data.txt in deployment rwx-nfs-4-2rwx-nfs-4-2-deploy
        And Write 100 MB data to file data.txt in deployment rwx-nfs-hard-mount-deploy
        And Write 100 MB data to file data.txt in deployment rwx-nfs-soft-mount-deploy
        And Write 100 MB data to file data.txt in deployment bi-deploy

        Then Check deployment rwo-deploy data in file data.txt is intact
        And Check deployment rwx-deploy data in file data.txt is intact
        And Check deployment strict-local-deploy data in file data.txt is intact
        And Check deployment rwx-nfs-4-2rwx-nfs-4-2-deploy data in file data.txt is intact
        And Check deployment rwx-nfs-hard-mount-deploy data in file data.txt is intact
        And Check deployment rwx-nfs-soft-mount-deploy data in file data.txt is intact
        And Check deployment bi-deploy data in file data.txt is intact
        ${current}=    Get Time    epoch

        And Check Longhorn components resource usage
    END
