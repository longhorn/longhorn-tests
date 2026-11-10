*** Settings ***
Documentation    DaemonSet Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/daemonset_keywords.py
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create daemonset ${daemonset_id} with persistentvolumeclaim ${claim_id}
    [Arguments]    &{config}
    ${daemonset_name} =    generate_name_with_suffix    daemonset    ${daemonset_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_daemonset    ${daemonset_name}    ${claim_name}    &{config}

Delete daemonset ${daemonset_id}
    ${daemonset_name} =    generate_name_with_suffix    daemonset    ${daemonset_id}
    delete_daemonset    ${daemonset_name}

