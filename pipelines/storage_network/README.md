# Storage-network Jenkins environment

This pipeline owns the test hosts' storage networking. Longhorn still initiates
NVMe/TCP connections in the instance-manager pod network namespace. Affected
kernels may reconnect from the host namespace, so both namespaces need a valid
storage path. This infrastructure workaround does not change Longhorn's data
path or configure production hosts.

See [Longhorn's storage-network prerequisites](https://longhorn.io/docs/1.14.0/advanced-resources/deploy/storage-network/)
and [longhorn/longhorn#13971](https://github.com/longhorn/longhorn/issues/13971).

## Host compatibility topology

The existing three-node AWS/K3s topology uses `eth0` for primary networking and
`eth1` for the storage underlay. The Multus NADs delegate IPv4 `/24` or IPv6 `/64`
subnets through Flannel to ipvlan L3 interfaces with host-local IPAM.

On node N (1, 2, or 3), Terraform installs:

| Path | Interface | Destination | Preferred source |
| --- | --- | --- | --- |
| Local IPv4 pods | `lhstoragehost` (ipvlan L3 child of `eth1`) | `192.168.N.0/24` | `192.168.N.1` |
| Local IPv6 pods | `lhstoragehost` | `fd00:168:N::/64` | `fd00:168:N::1` |
| Remote IPv4 pods | `eth1`, via the remote node's storage-underlay IPv4 address | remote `192.168.N.0/24` | local `eth1` IPv4 address |
| Remote IPv6 pods | `eth1`, via the remote node's storage-underlay IPv6 address | remote `fd00:168:N::/64` | local `eth1` IPv6 address |

ipvlan isolates its parent from its children. Assigning a storage address to
`eth1` alone is therefore not a host-to-local-pod solution. The sibling host
child provides that path without moving the initial NVMe connection into the
host namespace or binding transport sockets to an interface.

The `.1` / `::1` host addresses are reserved: host-local IPAM excludes each
subnet's default gateway (subnet base + 1), including explicit requests for that
address. Do not change the NAD's IPAM gateway or replace host-local without
revisiting this reservation. No pod range is reduced and no allocatable `.254`
address is appropriated.

IPv6 remote routes cover the full delegated `/64`, not just the old `/80`.
Legacy pipeline-owned `/80` routes and the parent interface's local `::1/80`
address are removed when setup is reapplied.

## Persistence and fail-closed routing

`routes.sh.tpl` installs `/usr/local/sbin/longhorn-storage-network` and enables
`longhorn-storage-network.service`. The oneshot runs before K3s on boot,
recreates the host child and the volatile `/run/flannel/multus-subnet-*.env`
files, and replaces routes/addresses idempotently. An `eth1` udev add event also
starts the service; its device dependency stops it when the parent disappears.
This is event-driven infrastructure provisioning, not a Longhorn runtime monitor.

The service installs less-specific unreachable routes for `192.168.0.0/16` and
`fd00:168::/32` before configuring the storage paths. Specific local/remote
storage routes take precedence. If a storage route or the local child is lost,
the unreachable aggregate prevents fallback through `eth0`'s default route.
Do not delete these guard routes or install competing primary-network routes
for the storage prefixes. They are specific to this test topology, not a general
firewall policy for arbitrary policy-routing tables or operator route changes.

The script waits for the expected `eth1` address pair and validates selected
local and remote route devices. Terraform fails provisioning if setup fails.
Route checks do not prove a listener is reachable; validate transport connectivity
with a live storage-network Jenkins run. Host
firewall, AWS source/destination checks, and return-path configuration remain
owned by the pipeline infrastructure.

For maintenance, reapply once with:

```sh
sudo systemctl restart longhorn-storage-network.service
sudo systemctl status longhorn-storage-network.service
sudo journalctl -u longhorn-storage-network.service
```

## Validation

From the root of `longhorn/longhorn-tests`, run the existing repository checks:

```sh
make validate
```

Run the storage-network Jenkins job against a branch containing this change for
end-to-end AWS/K3s networking and volume recovery coverage.

Nothing in this setup depends on an unreleased CLI binary. To additionally run
`longhornctl check preflight --storage-network-targets ...
--storage-network-interfaces lhstoragehost,eth1`, use a CLI binary and checker
image containing those flags and real reachable storage listeners. Preflight is
read-only and point-in-time; it does not replace the persistent provisioning above.
