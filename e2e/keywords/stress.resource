*** Settings ***
Documentation       Stress Node Keywords

Library             ../libs/keywords/stress_keywords.py

*** Keywords ***
Stress CPU of all ${role} nodes
    stress_node_cpu_by_role    ${role}

Stress CPU of node with volume ${volume_id}
   ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    stress_node_cpu_by_volume    ${volume_name}

Stress CPU of volume nodes
    stress_node_cpu_of_all_volumes

Stress memory of all ${role} nodes
    stress_node_memory_by_role    ${role}

Stress memory of node with volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    stress_node_memory_by_volume    ${volume_name}

Stress memory of volume nodes
    stress_node_memory_of_all_volumes
