#!/bin/bash
STORAGE_NETWORK_PREFIX="192.168"

ETH1_IP=`ip a | grep eth1 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*'  | awk '{print $2}'`

count=1
for n in ${N1} ${N2} ${N3}; do
    [[ $ETH1_IP != $n ]] && ((count=count+1)) && continue

    NET=$count
    break
done

cat << EOF | sudo tee -a /run/flannel/multus-subnet-$STORAGE_NETWORK_PREFIX.0.0.env
FLANNEL_NETWORK=$STORAGE_NETWORK_PREFIX.0.0/16
FLANNEL_SUBNET=$STORAGE_NETWORK_PREFIX.$NET.0/24
FLANNEL_MTU=${mtu}
FLANNEL_IPMASQ=true
EOF