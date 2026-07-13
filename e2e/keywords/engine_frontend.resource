*** Settings ***
Library    ../libs/keywords/host_keywords.py

*** Keywords ***
Make enginefrontend metadata directory immutable on node ${node_id}
    Run command on node    ${node_id}
    ...    sudo chattr +i -R /var/lib/longhorn/metadata/enginefrontends/
    Log To Console    Made enginefrontend directory immutable on node ${node_id}

Make enginefrontend metadata directory mutable on node ${node_id}
    Run command on node    ${node_id}
    ...    sudo chattr -i -R /var/lib/longhorn/metadata/enginefrontends/
    Log To Console    Restored enginefrontend directory to mutable on node ${node_id}

Clean enginefrontend files on node ${node_id}
    Run command on node    ${node_id}
    ...    sudo rm -rf /var/lib/longhorn/metadata/enginefrontends/*
    Log To Console    Cleaned enginefrontend files on node ${node_id}

