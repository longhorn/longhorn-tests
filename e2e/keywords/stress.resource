*** Settings ***
Documentation       Stress Node Keywords

Library             ../libs/keywords/stress_keywords.py

*** Keywords ***
Stress the CPU of all ${role} nodes
    stress_node_cpu_by_role    ${role}

Stress the CPU of all volume nodes
    stress_node_cpu_by_volumes    ${volume_list}

Stress the memory of all ${role} nodes
    stress_node_memory_by_role    ${role}

Stress the memory of all volume nodes
    stress_node_memory_by_volumes    ${volume_list}
