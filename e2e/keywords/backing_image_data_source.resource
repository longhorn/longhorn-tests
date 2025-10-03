*** Settings ***
Documentation    Backing Image Data Source Keywords

Library    ../libs/keywords/backing_image_data_source_keywords.py
Library    ../libs/keywords/network_keywords.py

*** Keywords ***
Wait for backing image data source ${backing_image_data_source_name} created
    wait_for_backing_image_data_source_created    ${backing_image_data_source_name}

Disconnect backing image data source ${backing_image_data_source_name} network for ${duration} seconds
    ${node_name} =    get_backing_image_data_source_node_id    ${backing_image_data_source_name}
    disconnect_node_network_without_waiting_completion    ${node_name}    ${duration}

Backing image data source ${backing_image_data_source_name} should not be in state ${state}
    backing_image_data_source_should_not_be_in_state    ${backing_image_data_source_name}    ${state}

Wait for backing image data source ${backing_image_data_source_name} state ${state}
    wait_for_backing_image_data_source_state    ${backing_image_data_source_name}    ${state}
