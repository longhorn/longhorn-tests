*** Settings ***
Documentation       Metrics Keywords

Library             ../libs/keywords/metrics_keywords.py

*** Keywords ***
Check if nodes are under memory pressure
    ${worker_nodes} =    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        get_node_memory_usage_in_percentage    ${worker_node}
        check_if_node_under_memory_pressure    ${worker_node}
    END

Metric ${metric_name} value should be ${expected_value}
    check_longhorn_metric    metric_name=${metric_name}    expected_value=${expected_value}

Get Longhorn components resource usage
    get_longhorn_components_memory_cpu_usage

Check Longhorn components resource usage
    check_longhorn_components_memory_cpu_usage
