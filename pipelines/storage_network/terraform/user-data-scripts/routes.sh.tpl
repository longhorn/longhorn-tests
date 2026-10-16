#!/bin/bash
set -eu

# This is Jenkins-owned provisioning, not Longhorn-managed host networking.
# Install the rendered setup so reboot and eth1 recreation restore the path.
sudo tee /usr/local/sbin/longhorn-storage-network > /dev/null <<'SETUP'
#!/bin/bash
set -euo pipefail

# Keep these prefixes in sync with flannel.sh.tpl and the Multus NADs.
STORAGE_NETWORK_PREFIX="192.168"
STORAGE_NETWORK_PREFIX_V6="fd00:168"

MASTER=eth1
HOST_INTERFACE=lhstoragehost
FLANNEL_DIR=/run/flannel
MTU=${mtu}
NODE_IPV4=("${N1}" "${N2}" "${N3}")
NODE_IPV6=("${N1_v6}" "${N2_v6}" "${N3_v6}")

# Install fail-closed catch routes before changing the more-specific paths.
# Removing a storage route must not send storage traffic through eth0's default.
ip -4 route replace unreachable "$STORAGE_NETWORK_PREFIX.0.0/16" metric 32760
ip -6 route replace unreachable "$STORAGE_NETWORK_PREFIX_V6::/32" metric 32760

LOCAL_NODE=-1
for attempt in $(seq 1 60); do
    for index in 0 1 2; do
        if ip -4 -o address show dev "$MASTER" scope global | awk '{print $4}' | cut -d/ -f1 | grep -Fxq "$${NODE_IPV4[$index]}" &&
           ip -6 -o address show dev "$MASTER" scope global | awk '!/tentative|dadfailed/ {print $4}' | cut -d/ -f1 | grep -Fxq "$${NODE_IPV6[$index]}"; then
            LOCAL_NODE=$index
            break
        fi
    done
    if (( LOCAL_NODE >= 0 )); then
        break
    fi
    sleep 2
done
if (( LOCAL_NODE < 0 )); then
    echo "eth1 has no expected storage-underlay IPv4/IPv6 address pair" >&2
    exit 1
fi

NET=$((LOCAL_NODE + 1))
# host-local IPAM always excludes the default gateway (subnet base + 1).
# Use that reserved address, not .254 or another allocatable pod address.
HOST_IPV4="$STORAGE_NETWORK_PREFIX.$NET.1"
HOST_IPV6="$STORAGE_NETWORK_PREFIX_V6:$NET::1"

if ip link show dev "$HOST_INTERFACE" > /dev/null 2>&1; then
    # Never silently reuse an unrelated link with our reserved name.
    if ! ip -d -o link show dev "$HOST_INTERFACE" | grep -F "$HOST_INTERFACE@$MASTER:" | grep -Eq 'ipvlan[[:space:]]+mode[[:space:]]+l3([[:space:]]|$)'; then
        echo "$HOST_INTERFACE is not an ipvlan L3 child of $MASTER" >&2
        exit 1
    fi
else
    ip link add "$HOST_INTERFACE" link "$MASTER" type ipvlan mode l3
fi
ip link set dev "$HOST_INTERFACE" mtu "$MTU" up
ip -4 address replace "$HOST_IPV4/24" dev "$HOST_INTERFACE"
ip -6 address replace "$HOST_IPV6/64" dev "$HOST_INTERFACE" nodad
ip -4 route replace "$STORAGE_NETWORK_PREFIX.$NET.0/24" dev "$HOST_INTERFACE" src "$HOST_IPV4"
ip -6 route replace "$STORAGE_NETWORK_PREFIX_V6:$NET::/64" dev "$HOST_INTERFACE" src "$HOST_IPV6"

for index in 0 1 2; do
    subnet=$((index + 1))
    # Remove only the legacy addresses/routes owned by this pipeline. The
    # old /80 routes did not cover the delegated IPv6 /64 pod subnet.
    if (( index == LOCAL_NODE )); then
        ip -6 address del "$STORAGE_NETWORK_PREFIX_V6:$subnet::1/80" dev "$MASTER" 2>/dev/null || true
        continue
    fi
    ip -4 route replace "$STORAGE_NETWORK_PREFIX.$subnet.0/24" via "$${NODE_IPV4[$index]}" dev "$MASTER" src "$${NODE_IPV4[$LOCAL_NODE]}"
    ip -6 route replace "$STORAGE_NETWORK_PREFIX_V6:$subnet::/64" via "$${NODE_IPV6[$index]}" dev "$MASTER" src "$${NODE_IPV6[$LOCAL_NODE]}"
    ip -6 route del "$STORAGE_NETWORK_PREFIX_V6:$subnet::/80" via "$${NODE_IPV6[$index]}" dev "$MASTER" 2>/dev/null || true
done

# /run is volatile. Recreate the delegated subnet files before K3s starts.
mkdir -p "$FLANNEL_DIR"
cat > "$FLANNEL_DIR/multus-subnet-$STORAGE_NETWORK_PREFIX.0.0.env" <<EOF
FLANNEL_NETWORK=$STORAGE_NETWORK_PREFIX.0.0/16
FLANNEL_SUBNET=$STORAGE_NETWORK_PREFIX.$NET.0/24
FLANNEL_MTU=$MTU
FLANNEL_IPMASQ=true
EOF
cat > "$FLANNEL_DIR/multus-subnet-$STORAGE_NETWORK_PREFIX_V6.0.0.env" <<EOF
FLANNEL_NETWORK=$STORAGE_NETWORK_PREFIX_V6::/32
FLANNEL_SUBNET=$STORAGE_NETWORK_PREFIX_V6:$NET::/64
FLANNEL_MTU=$MTU
FLANNEL_IPMASQ=false
EOF

# Route-only readiness assertions require no test listener or CLI release.
for subnet in 1 2 3; do
    expected=$MASTER
    if (( subnet == NET )); then
        expected=$HOST_INTERFACE
    fi
    for family in 4 6; do
        target="$STORAGE_NETWORK_PREFIX.$subnet.2"
        if (( family == 6 )); then
            target="$STORAGE_NETWORK_PREFIX_V6:$subnet::2"
        fi
        route=$(ip -"$family" route get "$target")
        if ! grep -Fq " dev $expected " <<< "$route "; then
            echo "Unexpected storage route: $route; expected $expected" >&2
            exit 1
        fi
    done
done
SETUP
sudo chmod 0755 /usr/local/sbin/longhorn-storage-network

sudo tee /etc/systemd/system/longhorn-storage-network.service > /dev/null <<'UNIT'
[Unit]
Description=Longhorn Jenkins storage-network host compatibility
Wants=network-online.target
After=network-online.target sys-subsystem-net-devices-eth1.device
BindsTo=sys-subsystem-net-devices-eth1.device
Before=k3s.service k3s-agent.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/longhorn-storage-network
RemainAfterExit=yes
TimeoutStartSec=150

[Install]
WantedBy=multi-user.target
UNIT

# Event-driven restoration after parent-device recreation, not polling.
sudo tee /etc/udev/rules.d/90-longhorn-storage-network.rules > /dev/null <<'RULE'
ACTION=="add", SUBSYSTEM=="net", KERNEL=="eth1", TAG+="systemd", ENV{SYSTEMD_WANTS}+="longhorn-storage-network.service"
RULE
sudo udevadm control --reload-rules
sudo systemctl daemon-reload
sudo systemctl enable longhorn-storage-network.service
sudo systemctl restart longhorn-storage-network.service
