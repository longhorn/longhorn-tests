*** Settings ***
Documentation       Support Bundle keywords

Library             ../libs/keywords/support_bundle_keywords.py
Library             ../libs/keywords/host_keywords.py

*** Variables ***

*** Keywords ***
Create support bundle
    generate_support_bundle

Create support bundle and download
    generate_support_bundle    download=${True}

Support bundle logs of node ${node_id} should contain host Logs
    ${node_name} =    get_node_by_index    ${node_id}
    check_bundle_contains_host_logs    ${host_log_files}    ${node_name}
