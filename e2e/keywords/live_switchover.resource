*** Settings ***
Documentation    Live Switchover Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/live_switchover_keywords.py
Library    String

*** Keywords ***
Set up live switchover test environment
    ${suffix}=    Generate Random String    8    [LOWER][NUMBERS]
    Set Test Variable    ${LIVE_SWITCHOVER_CLAIM_ID}    ${LIVE_SWITCHOVER_NAME_PREFIX}-${suffix}
    Set Test Variable    ${LIVE_SWITCHOVER_POD_ID}    ${LIVE_SWITCHOVER_NAME_PREFIX}-${suffix}
    Set up test environment

Assert live switchover resources for persistentvolumeclaim ${claim_id} start on the same node
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${node_a} =    assert_live_switchover_resources_start_on_same_node    ${claim_name}
    RETURN    ${node_a}

Start live switchover IO in pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    start_live_switchover_io    ${pod_name}

Run ${rounds} live switchover rounds for persistentvolumeclaim ${claim_id} and pod ${pod_id}
    [Arguments]    ${post_write_seconds}=180
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    run_live_switchover_rounds    ${claim_name}    ${pod_name}    rounds=${rounds}    post_write_seconds=${post_write_seconds}

Run live switchover sequence for persistentvolumeclaim ${claim_id} and pod ${pod_id}
    [Arguments]    ${post_write_seconds}=180
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    run_live_switchover_sequence    ${claim_name}    ${pod_name}    post_write_seconds=${post_write_seconds}

Stop live switchover IO in pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    stop_live_switchover_io    ${pod_name}

Stop live switchover IO in pod ${pod_id} if running
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    stop_live_switchover_io_if_running    ${pod_name}

Verify live switchover checksum in pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    verify_live_switchover_checksum    ${pod_name}

Verify live switchover final state for persistentvolumeclaim ${claim_id} and pod ${pod_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    verify_live_switchover_final_state    ${claim_name}    ${pod_name}

Cleanup live switchover test resources
    [Arguments]    ${claim_id}    ${pod_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    cleanup_live_switchover_resources    ${claim_name}    ${pod_name}
