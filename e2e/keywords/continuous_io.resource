*** Settings ***
Documentation    Continuous IO Keywords

*** Keywords ***
Run continuous fio test
    [Documentation]    Run fio with multiple threads writing multiple files, verifying crc32c in every cycle.
    [Arguments]    ${volume_type}    ${duration_in_hours}    ${volume_size}
    Create storageclass longhorn-test with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    Create persistentvolumeclaim fio    volume_type=${volume_type}    sc_name=longhorn-test    storage_size=${volume_size}
    # fio is not in the workload image, so the pod installs it before idling.
    Create deployment fio with persistentvolumeclaim fio
    ...    args=apk add --no-cache fio && sleep infinity
    Wait for volume of deployment fio healthy
    Wait for workloads pods stable    deployment fio

    ${duration_in_second} =    Evaluate    int(${duration_in_hours}) * 60 * 60
    Start continuous fio write with crc32c verify in deployment fio for ${duration_in_second}
    Wait for continuous fio in deployment fio to complete    ${duration_in_second}
    Verify continuous fio crc32c data in deployment fio have no errors

Run continuous multi-pod fio test
    [Documentation]    Run fio in every pod sharing the volume and verify crc32c data integrity in all of them.
    [Arguments]    ${volume_type}    ${duration_in_hours}    ${volume_size}
    Create storageclass longhorn-test with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    Create persistentvolumeclaim fio    volume_type=${volume_type}    sc_name=longhorn-test    storage_size=${volume_size}
    IF    '${volume_type}' == 'RWX'
        Create deployment fio with persistentvolumeclaim fio
        ...    replicaset=2
        ...    args=apk add --no-cache fio && sleep infinity
    ELSE
        # An RWO volume is attached to one node, so all of its pods have to land there.
        Create deployment fio with persistentvolumeclaim fio
        ...    replicaset=2
        ...    args=apk add --no-cache fio && sleep infinity
        ...    node_selector={"kubernetes.io/hostname":"${NODE_0}"}
    END
    Wait for volume of deployment fio healthy
    Wait for workloads pods stable    deployment fio

    ${duration_in_second} =    Evaluate    int(${duration_in_hours}) * 60 * 60
    Start continuous fio write with crc32c verify in all pods of deployment fio for ${duration_in_second}
    Wait for continuous fio in all pods of deployment fio to complete    ${duration_in_second}
    Verify continuous fio crc32c data in all pods of deployment fio have no errors

Run continuous fio test on block volume
    [Documentation]    Run fio directly against the block device and verify crc32c data integrity.
    [Arguments]    ${volume_type}    ${duration_in_hours}    ${volume_size}
    Create storageclass longhorn-test with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    Create persistentvolumeclaim fio    volume_type=${volume_type}    sc_name=longhorn-test    storage_size=${volume_size}    volumeMode=Block
    Create deployment fio with block persistentvolumeclaim fio
    ...    args=apk add --no-cache fio && sleep infinity
    Wait for volume of deployment fio healthy
    Wait for workloads pods stable    deployment fio

    ${duration_in_second} =    Evaluate    int(${duration_in_hours}) * 60 * 60
    Start continuous fio write with crc32c verify on block device in deployment fio for ${duration_in_second}
    Wait for continuous fio in deployment fio to complete    ${duration_in_second}
    Verify continuous fio crc32c data in deployment fio have no errors
