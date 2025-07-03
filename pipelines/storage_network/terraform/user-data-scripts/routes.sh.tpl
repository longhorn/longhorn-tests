#!/bin/bash

STORAGE_NETWORK_PREFIX="192.168"
STORAGE_NETWORK_PREFIX_V6="fd00:168"
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

ETH1_IPV6=$(ip -6 -o addr show dev eth1 scope global | awk '{print $4}' | cut -d/ -f1 || true)

if [[ $ETH1_IPV6 != ${N1_v6} ]]; then
  echo "Adding IPv6 route to $STORAGE_NETWORK_PREFIX_V6:1::/80 via ${N1_v6} dev eth1"
  sudo ip -6 route $ACTION $STORAGE_NETWORK_PREFIX_V6:1::/80 via ${N1_v6} dev eth1
else
  echo "Adding address to eth1: ip -6 r $ACTION $STORAGE_NETWORK_PREFIX_V6:1::1/80 dev eth1"
  sudo ip -6 addr $ACTION $STORAGE_NETWORK_PREFIX_V6:1::1/80 dev eth1
fi

if [[ $ETH1_IPV6 != ${N2_v6} ]]; then
  echo "Adding IPv6 route to $STORAGE_NETWORK_PREFIX_V6:2::/80 via ${N2_v6} dev eth1"
  sudo ip -6 route $ACTION $STORAGE_NETWORK_PREFIX_V6:2::/80 via ${N2_v6} dev eth1
else
  echo "Adding address to eth1: ip -6 r $ACTION $STORAGE_NETWORK_PREFIX_V6:2::1/80 dev eth1"
  sudo ip -6 addr $ACTION $STORAGE_NETWORK_PREFIX_V6:2::1/80 dev eth1
fi

if [[ $ETH1_IPV6 != ${N3_v6} ]]; then
  echo "Adding IPv6 route to $STORAGE_NETWORK_PREFIX_V6:3::/80 via ${N3_v6} dev eth1"
  sudo ip -6 route $ACTION $STORAGE_NETWORK_PREFIX_V6:3::/80 via ${N3_v6} dev eth1
else
  echo "Adding address to eth1: ip -6 r $ACTION $STORAGE_NETWORK_PREFIX_V6:3::1/80 dev eth1"
  sudo ip -6 addr $ACTION $STORAGE_NETWORK_PREFIX_V6:3::1/80 dev eth1
fi
