#!/bin/bash

STORAGE_NETWORK_PREFIX="192.168"
ACTION="add"

ETH1_IP=`ip a | grep eth1 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*'  | awk '{print $2}'`

if [[ $ETH1_IP != ${N1} ]]; then
  sudo ip r $ACTION $STORAGE_NETWORK_PREFIX.1.0/24 via ${N1} dev eth1
fi

if [[ $ETH1_IP != ${N2} ]]; then
  sudo ip r $ACTION $STORAGE_NETWORK_PREFIX.2.0/24 via ${N2} dev eth1
fi

if [[ $ETH1_IP != ${N3} ]]; then
  sudo ip r $ACTION $STORAGE_NETWORK_PREFIX.3.0/24 via ${N3} dev eth1
fi