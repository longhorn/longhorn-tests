*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/network_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py

*** Variables ***


*** Keywords ***
Disconnect volume node network of statefulset ${statefulset_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    statefulset    ${statefulset_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    disconnect_node_network    ${node_name}    ${duration}
