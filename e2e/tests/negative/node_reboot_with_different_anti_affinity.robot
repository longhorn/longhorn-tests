*** Settings ***
Documentation    Power off node with different anti-affinity combinations
...              - Issue: https://github.com/longhorn/longhorn/issues/10210
...              - Replica Disk Level Soft Anti-Affinity the default value which is true
...              - Replica Node Level Soft Anti-Affinity the default value which is false
...              - Replica Zone Level Soft Anti-Affinity the default value which is true
...              - Create a testvol of 3 replicas and attach it to ${node_num}
...              - Turn off ${node_num}
...              - Wait for ${power_off_time} minutes, turn on the ${node_num}
...              - The volume should reuse the failed replica to rebuild.
...              - Volume should become healthy again
...
...              - Note: Test cases with replica-zone-soft-anti-affinity=false are skipped
...              - because the volume cannot be healthy in a single-zone cluster.

Test Tags    manual    negative    replica    reboot    anti-affinity    longhorn-10210

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource


Test Setup    Set up test environment
Test Teardown    Cleanup test resources
Test Template    Power Off Node With Anti-Affinity Settings

*** Keywords ***
Power Off Node With Anti-Affinity Settings
    [Arguments]    ${description}    ${disk_affinity}    ${node_affinity}    ${zone_affinity}    ${node_num}    ${power_off_time}
    [Documentation]    Keyword to test node power off behavior with different anti-affinity settings.
    ...                Arguments:
    ...                - ${disk_affinity}: Replica Disk Level Soft Anti-Affinity setting (true/false).
    ...                - ${node_affinity}: Replica Node Level Soft Anti-Affinity setting (true/false).
    ...                - ${zone_affinity}: Replica Zone Level Soft Anti-Affinity setting (true/false).
    ...                - ${node_num}: Number of node to power off (e.g., 0 or 1).
    ...                - ${power_off_time}: Duration (in minutes) to power off the node.
    Given Set setting replica-replenishment-wait-interval to 180
    And Set setting replica-disk-soft-anti-affinity to ${disk_affinity}
    And Set setting replica-soft-anti-affinity to ${node_affinity}
    And Set setting replica-zone-soft-anti-affinity to ${zone_affinity}
    IF    "${DATA_ENGINE}" == "v2"
        And Set setting v2-data-engine-fast-replica-rebuilding to true
    END

    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Record volume 0 replica names

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Power off node ${node_num} for ${power_off_time} mins
        Then Wait for longhorn ready
        And Wait for volume 0 healthy

        Run Keyword If    '${node_affinity}' == 'false'
        ...    And Check volume 0 replica names are as recorded
    END

*** Test Cases ***    DESCRIPTION    DISK-AFFINITY    NODE-AFFINITY    ZONE-AFFINITY    NODE#    POWER-OFF-TIMEZONE
Power Off Replica Node More Than 3 Mins With Different Anti-Affinity Combinations
    Zone Level Enabled    false    false    true     1       4
    Disk Level Disabled    false    true     true     1       4
    Node Level Disabled    true     false    true     1       4
    All Enabled    true     true     true     1       4

Power Off Replica Node Less Than 3 Mins With Different Anti-Affinity Combinations
    Zone Level Enabled    false    false    true     1       2
    Disk Level Disabled    false    true     true     1       2
    Node Level Disabled    true     false    true     1       2
    All Enabled    true     true     true     1       2

Power Off Volume Node More Than 3 Mins With Different Anti-Affinity Combinations
    Zone Level Enabled    false    false    true     0       4
    Disk Level Disabled    false    true     true     0       4
    Node Level Disabled    true     false    true     0       4
    All Enabled    true     true     true     0       4

Power Off Volume Node Less Than 3 Mins With Different Anti-Affinity Combinations
    Zone Level Enabled    false    false    true     0       2
    Disk Level Disabled    false    true     true     0       2
    Node Level Disabled    true     false    true     0       2
    All Enabled    true     true     true     0       2
