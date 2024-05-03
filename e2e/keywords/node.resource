*** Settings ***
Documentation    Node Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/node_keywords.py

*** Keywords ***
Add ${disk_type} type disk ${disk_path} for all worker nodes
    ${worker_nodes}=    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    ${worker_node}    ${disk_type}    ${disk_path}
    END
