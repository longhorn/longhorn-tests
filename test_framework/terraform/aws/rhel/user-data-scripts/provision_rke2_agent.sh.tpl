#!/bin/bash

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
    sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
    sudo setenforce  0
fi

sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools nc
sudo systemctl -q enable iscsid
sudo systemctl start iscsid
sudo systemctl disable nm-cloud-setup.service nm-cloud-setup.timer

if [ -b "/dev/xvdh" ]; then
  sudo mkfs.ext4 -E nodiscard /dev/xvdh
  sudo mkdir /var/lib/longhorn
  sudo mount /dev/xvdh /var/lib/longhorn
fi

RKE_SERVER_IP=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $1}'`
RKE_SERVER_PORT=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $2}'`

while ! nc -z $${RKE_SERVER_IP} $${RKE_SERVER_PORT}; do   
  sleep 10 #
done

curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="${rke2_version}" sh -

sudo mkdir -p /etc/rancher/rke2

sudo cat << EOF > /etc/rancher/rke2/config.yaml
server: ${rke2_server_url}
token: ${rke2_cluster_secret}
EOF

sudo systemctl enable rke2-agent.service
sudo systemctl start rke2-agent.service
exit $?
