*** Settings ***
Documentation    Deployment Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Setting Node Selector To Schedule Deployment Pod To Different Nodes
    [Documentation]    https://github.com/longhorn/longhorn/issues/1985#issuecomment-854883843
    ...                1. Create a deployment
    ...                2. Set the node selector to force the Pod to be recreated on a different node
    ...                3. Check if the workload pod can be created and running on the correct node
    Given Create persistentvolumeclaim 0
    And Create deployment 0 on node 0 with persistentvolumeclaim 0
    And Write 128 MB data to file data.bin in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Schedule deployment 0 to node 1
        Then Wait for deployment 0 pods creating on node 1
        And Wait for deployment 0 pods running on node 1
        And Check deployment 0 data in file data.bin is intact

        When Schedule deployment 0 to node 2
        Then Wait for deployment 0 pods creating on node 2
        And Wait for deployment 0 pods running on node 2
        And Check deployment 0 data in file data.bin is intact
    END

Test Setting Node Affinity To Schedule Deployment Pod To Different Nodes
    [Documentation]    https://github.com/longhorn/longhorn/issues/1985#issuecomment-1783490726
    ...                1. Create a deployment
    ...                2. Change the node affinity to force the Pod to be recreated on a different node
    ...                3. Check if the workload pod can be created and running on the correct node
    Given Create persistentvolumeclaim 0
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 128 MB data to file data.bin in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Set deployment 0 node affinity to node 0
        Then Wait for deployment 0 pods creating on node 0
        And Wait for deployment 0 pods running on node 0
        And Check deployment 0 data in file data.bin is intact

        When Set deployment 0 node affinity to node 1
        Then Wait for deployment 0 pods creating on node 1
        And Wait for deployment 0 pods running on node 1
        And Check deployment 0 data in file data.bin is intact

        When Set deployment 0 node affinity to node 2
        Then Wait for deployment 0 pods creating on node 2
        And Wait for deployment 0 pods running on node 2
        And Check deployment 0 data in file data.bin is intact
    END