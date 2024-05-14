*** Settings ***
Documentation       Stress Node Keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/stress_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py

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

Stress filesystem of volume ${volume_id} volume node
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    stress_nodes_filesystem    ${node_name}

Stress filesystem of statefulset ${statefulset_id} volume node
    ${workload_name} =   generate_name_with_suffix    statefulset    ${statefulset_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    stress_nodes_filesystem   ${node_name}

Stress filesystem of all worker nodes
    ${worker_nodes} =    get_worker_nodes
    stress_nodes_filesystem   ${worker_nodes}
