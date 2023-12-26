*** Settings ***
Documentation       Kubelet keywords

Library             ../libs/keywords/kubelet_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py

*** Variables ***


*** Keywords ***
Stop volume node kubelet of statefulset ${idx} for ${stop_time_in_sec} seconds
    ${volume_name} =    get_workload_volume_name    ${statefulset_list}[${idx}]
    ${node_name} =    get_volume_node    ${volume_name}
    restart_kubelet    ${node_name}    ${stop_time_in_sec}
