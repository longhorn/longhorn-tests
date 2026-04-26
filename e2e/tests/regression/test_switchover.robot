*** Settings ***
Documentation    Longhorn v2 live switchover test

Test Tags    live-switchover    v2    data-engine

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/live_switchover.resource

Test Setup    Set up live switchover test environment
Test Teardown    Cleanup live switchover test resources    ${LIVE_SWITCHOVER_CLAIM_ID}    ${LIVE_SWITCHOVER_POD_ID}

*** Variables ***
${LIVE_SWITCHOVER_NAME_PREFIX}         live-switchover
${LIVE_SWITCHOVER_STORAGECLASS}        longhorn-v2-data-engine
${LIVE_SWITCHOVER_CLAIM_ID}            live-switchover
${LIVE_SWITCHOVER_POD_ID}              live-switchover
${LIVE_SWITCHOVER_POST_WRITE_SECONDS}  120

*** Test Cases ***
Live Switchover Keeps Workload IO Running
    [Tags]    switchover    uninstall
    [Documentation]    Verify v2 live switchover keeps workload write I/O running across
    ...    Node A -> B -> C -> B -> A, with the pod stable and the volume attached.
    ...    Volume and EngineFrontend stay on Node A while only the active Engine moves
    ...    according to volume.spec.engineNodeID.
    Given Enable v2 data engine and add block disks
    And Create persistentvolumeclaim ${LIVE_SWITCHOVER_CLAIM_ID}    sc_name=${LIVE_SWITCHOVER_STORAGECLASS}    storage_size=2Gi
    And Create pod ${LIVE_SWITCHOVER_POD_ID} using persistentvolumeclaim ${LIVE_SWITCHOVER_CLAIM_ID}
    And Wait for pod ${LIVE_SWITCHOVER_POD_ID} running
    And Wait for volume of persistentvolumeclaim ${LIVE_SWITCHOVER_CLAIM_ID} healthy
    And Assert live switchover resources for persistentvolumeclaim ${LIVE_SWITCHOVER_CLAIM_ID} start on the same node

    When Start live switchover IO in pod ${LIVE_SWITCHOVER_POD_ID}
    And Run live switchover sequence for persistentvolumeclaim ${LIVE_SWITCHOVER_CLAIM_ID} and pod ${LIVE_SWITCHOVER_POD_ID}    post_write_seconds=${LIVE_SWITCHOVER_POST_WRITE_SECONDS}
    And Stop live switchover IO in pod ${LIVE_SWITCHOVER_POD_ID}

    Then Verify live switchover checksum in pod ${LIVE_SWITCHOVER_POD_ID}
    And Verify live switchover final state for persistentvolumeclaim ${LIVE_SWITCHOVER_CLAIM_ID} and pod ${LIVE_SWITCHOVER_POD_ID}
