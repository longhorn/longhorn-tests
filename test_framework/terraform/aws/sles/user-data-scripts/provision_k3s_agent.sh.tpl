#!/bin/bash

set -e

# Sometimes, registration fails on the first boot, which causes the default repositories to be missing from zypper,
# preventing it from installing any packages.
# In some cases, even manually executing systemctl restart guestregister can fail.
sudo systemctl restart guestregister || true
if ! SUSEConnect --status 2>/dev/null | grep -q "Registered"; then
  sudo systemctl enable guestregister.service || true
  sudo registercloudguest --force-new || true
fi
sudo zypper --gpg-auto-import-keys ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client cryptsetup device-mapper samba

sudo mkdir -p /etc/certs
sudo ln -s /var/lib/ca-certificates/ca-bundle.pem /etc/certs/ca-certificates.crt
sudo ln -s /var/lib/ca-certificates/pem /etc/ssl/certs

sudo systemctl -q enable iscsid
sudo systemctl start iscsid

modprobe uio
modprobe uio_pci_generic
modprobe vfio_pci
modprobe nvme-tcp
modprobe dm_crypt
touch /etc/modules-load.d/modules.conf
cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
vfio_pci
nvme-tcp
dm_crypt
EOF

echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf

if [[ "${extra_block_device}" != true ]]; then
  if [[ -b "/dev/nvme1n1" ]]; then
    mkfs.ext4 -E nodiscard /dev/nvme1n1
    mkdir /mnt/sda1
    mount /dev/nvme1n1 /mnt/sda1

    mkdir /mnt/sda1/local
    mkdir /opt/local-path-provisioner
    mount --bind /mnt/sda1/local /opt/local-path-provisioner

    mkdir /mnt/sda1/longhorn
    mkdir /var/lib/longhorn
    mount --bind /mnt/sda1/longhorn /var/lib/longhorn
  elif [ -b "/dev/xvdh" ]; then
    mkfs.ext4 -E nodiscard /dev/xvdh
    mkdir /var/lib/longhorn
    mount /dev/xvdh /var/lib/longhorn
  fi
fi

if [[ "${network_stack}" == "ipv6" ]]; then
  echo -e "net.ipv6.conf.eth0.accept_ra = 2\nnet.ipv6.conf.default.accept_ra = 2" | tee /etc/sysctl.d/99-ipv6.conf
  sysctl --system
  cat <<EOF > /etc/resolv.conf
nameserver 2606:4700:4700::1111
nameserver 2001:4860:4860::8888
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
  chattr +i /etc/resolv.conf || true
  IP=$(ip -6 addr show scope global | awk '/inet6/ && !/fe80/ {print $2}' | cut -d/ -f1 | head -n1)
else
  IP=$(hostname -I | awk '{print $1}')
fi

# TODO: It looks like "set -e" will break the intended functionality of the remaining code. Consider a refactor.
set +e

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent --node-ip=$IP --token ${k3s_cluster_secret}" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi