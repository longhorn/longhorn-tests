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

*** Keywords ***
Power Off Node With Anti-Affinity Settings
    [Arguments]    ${disk_affinity}=true    ${node_affinity}=false    ${zone_affinity}=true    ${node_type}=volume    ${power_off_time}=3
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/10210#issuecomment-2600594553
    ...                Keyword to test node power off behavior with different anti-affinity settings.
    ...                Notice that the default value of replica-zone-soft-anti-affinity is true
    ...                Arguments:
    ...                - ${disk_affinity}: Replica Disk Level Soft Anti-Affinity setting (true/false).
    ...                - ${node_affinity}: Replica Node Level Soft Anti-Affinity setting (true/false).
    ...                - ${zone_affinity}: Replica Zone Level Soft Anti-Affinity setting (true/false).
    ...                - ${node_type}: Volume node or replica node to power off (e.g., "volume" or "replica").
    ...                - ${power_off_time}: Duration (in minutes) to power off the node.
    Given Setting replica-replenishment-wait-interval is set to 180
    And Setting replica-disk-soft-anti-affinity is set to ${disk_affinity}
    And Setting replica-soft-anti-affinity is set to ${node_affinity}
    And Setting replica-zone-soft-anti-affinity is set to ${zone_affinity}

    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Record volume 0 replica names

    IF    '${node_type}' == 'volume'
        ${node_id} =    Set Variable    0
    ELSE
        ${node_id} =    Set Variable    1
    END

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Power off node ${node_id} for ${power_off_time} mins
        Then Wait for longhorn ready
        And Wait for volume 0 healthy

        Run Keyword If    '${node_affinity}' == 'false'
        ...    And Check volume 0 replica names are as recorded
    END

*** Test Cases ***
Power Off Replica Node More Than 3 Mins With Default Soft Anti Affinity Setting
    Power Off Node With Anti-Affinity Settings    node_type=replica    power_off_time=4

Power Off Replica Node More Than 3 Mins With Zone Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=false    zone_affinity=true    node_type=replica    power_off_time=4

Power Off Replica Node More Than 3 Mins With Disk Soft Anti Affinity Disabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=true    zone_affinity=true    node_type=replica    power_off_time=4

Power Off Replica Node More Than 3 Mins With All Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=true    node_affinity=true    zone_affinity=true    node_type=replica    power_off_time=4

Power Off Replica Node Less Than 3 Mins With Default Soft Anti Affinity Setting
    Power Off Node With Anti-Affinity Settings    node_type=replica    power_off_time=2

Power Off Replica Node Less Than 3 Mins With Zone Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=false    zone_affinity=true    node_type=replica    power_off_time=2

Power Off Replica Node Less Than 3 Mins With Disk Soft Anti Affinity Disabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=true    zone_affinity=true    node_type=replica    power_off_time=2

Power Off Replica Node Less Than 3 Mins With All Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=true    node_affinity=true    zone_affinity=true    node_type=replica    power_off_time=2

Power Off Volume Node More Than 3 Mins With Default Soft Anti Affinity Setting
    Power Off Node With Anti-Affinity Settings    node_type=volume    power_off_time=4

Power Off Volume Node More Than 3 Mins With Zone Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=false    zone_affinity=true    node_type=volume    power_off_time=4

Power Off Volume Node More Than 3 Mins With Disk Soft Anti Affinity Disabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=true    zone_affinity=true    node_type=volume    power_off_time=4

Power Off Volume Node More Than 3 Mins With All Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=true    node_affinity=true    zone_affinity=true    node_type=volume    power_off_time=4

Power Off Volume Node Less Than 3 Mins With Default Soft Anti Affinity Setting
    Power Off Node With Anti-Affinity Settings    node_type=volume    power_off_time=2

Power Off Volume Node Less Than 3 Mins With Zone Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=false    zone_affinity=true    node_type=volume    power_off_time=2

Power Off Volume Node Less Than 3 Mins With Disk Soft Anti Affinity Disabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=false    node_affinity=true    zone_affinity=true    node_type=volume    power_off_time=2

Power Off Volume Node Less Than 3 Mins With All Soft Anti Affinity Enabled
    Power Off Node With Anti-Affinity Settings    disk_affinity=true    node_affinity=true    zone_affinity=true    node_type=volume    power_off_time=2

