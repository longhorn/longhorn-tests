*** Settings ***
Documentation       Global Variables

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${VOLUME_TYPE}    RWO
${CONTROL_PLANE_NODE_NETWORK_LATENCY_IN_MS}    0
${RWX_VOLUME_FAST_FAILOVER}    false
${DATA_ENGINE}    v1
${VOLUME_STATE_CHECK_TIMEOUT}    120
${LONGHORN_NAMESPACE}    longhorn-system

@{powered_off_nodes}=

&{volume_checksums}=

@{evicted_nodes}=
