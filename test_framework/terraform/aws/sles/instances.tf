# Create controlplane instances
resource "aws_instance" "lh_aws_instance_controlplane" {
 depends_on = [
    aws_subnet.lh_aws_public_subnet,
  ]

  count = var.lh_aws_instance_count_controlplane

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_sles.id
  instance_type = var.lh_aws_instance_type_controlplane

  subnet_id = aws_subnet.lh_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp.id
  ]

  ipv6_address_count = 1

  root_block_device {
    delete_on_termination = true
    volume_size = var.block_device_size_controlplane
  }

  key_name = aws_key_pair.lh_aws_pair_key.key_name

  user_data = var.k8s_distro_name == "k3s" ? data.template_file.provision_k3s_server.rendered : data.template_file.provision_rke2_server.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

# Create worker instances
resource "aws_instance" "lh_aws_instance_worker" {
  depends_on = [
    aws_route_table_association.lh_aws_public_subnet_rt_association,
    aws_instance.lh_aws_instance_controlplane
  ]

  count = var.lh_aws_instance_count_worker

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_sles.id
  instance_type = var.lh_aws_instance_type_worker

  subnet_id = aws_subnet.lh_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp.id
  ]

  ipv6_address_count = 1
  associate_public_ip_address = true

  root_block_device {
    delete_on_termination = true
    volume_size = var.block_device_size_worker
  } 

  key_name = aws_key_pair.lh_aws_pair_key.key_name

  user_data = var.k8s_distro_name == "k3s" ? data.template_file.provision_k3s_agent.rendered : data.template_file.provision_rke2_agent.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "aws_volume_attachment" "lh_aws_hdd_volume_att" {
  count = var.use_hdd ? var.lh_aws_instance_count_worker : 0
  device_name  = "/dev/xvdh"
  volume_id    = aws_ebs_volume.lh_aws_hdd_volume[count.index].id
  instance_id  = aws_instance.lh_aws_instance_worker[count.index].id
  force_detach = true
}

resource "aws_volume_attachment" "lh_aws_ssd_volume_att" {
  count = var.extra_block_device ? var.lh_aws_instance_count_worker : 0
  device_name  = "/dev/xvdh"
  volume_id    = aws_ebs_volume.lh_aws_ssd_volume[count.index].id
  instance_id  = aws_instance.lh_aws_instance_worker[count.index].id
  force_detach = true
}

resource "aws_lb_target_group_attachment" "lh_aws_lb_tg_443_attachment" {

  depends_on = [
    aws_lb_target_group.lh_aws_lb_tg_443,
    aws_instance.lh_aws_instance_worker
  ]

  count            = var.create_load_balancer ? length(aws_instance.lh_aws_instance_worker) : 0

  target_group_arn = aws_lb_target_group.lh_aws_lb_tg_443[0].arn
  target_id        = aws_instance.lh_aws_instance_worker[count.index].id
}

# Associate every EIP with controlplane instance
resource "aws_eip_association" "lh_aws_eip_assoc" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_eip.lh_aws_eip_controlplane
  ]

  count = var.lh_aws_instance_count_controlplane

  instance_id   = element(aws_instance.lh_aws_instance_controlplane, count.index).id
  allocation_id = element(aws_eip.lh_aws_eip_controlplane, count.index).id
}

# Download KUBECONFIG file for k3s
resource "null_resource" "rsync_kubeconfig_file_k3s" {

  count = var.k8s_distro_name == "k3s" ? 1 : 0

  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  provisioner "remote-exec" {

    inline = [
      "cloud-init status --wait",
      "if [ \"`cloud-init status | grep error`\" ]; then sudo cat /var/log/cloud-init-output.log; fi",
      "RETRY=0; MAX_RETRY=450; until([ -f /etc/rancher/k3s/k3s.yaml ] && [ `sudo /usr/local/bin/kubectl get node -o jsonpath='{.items[*].status.conditions}'  | jq '.[] | select(.type  == \"Ready\").status' | grep -ci true` -eq $((${var.lh_aws_instance_count_controlplane} + ${var.lh_aws_instance_count_worker})) ]); do echo \"waiting for k3s cluster nodes to be running\"; sleep 2; if [ $RETRY -eq $MAX_RETRY ]; then echo \"cluster nodes initialization timeout ...\"; sleep 86400; fi; RETRY=$((RETRY+1)); done"
    ]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = <<EOT
    export K3S_SERVER_IP=$(
        [ "${var.network_stack}" = "ipv6" ] && echo "[${aws_instance.lh_aws_instance_controlplane[0].ipv6_addresses[0]}]" || echo ${aws_eip.lh_aws_eip_controlplane[0].public_ip}
    )

    export LOCAL_IP=$(
        [ "${var.network_stack}" = "ipv6" ] && echo "\[::1\]" || echo "127.0.0.1"
    )

    rsync -aPvz --rsync-path="sudo rsync" -e "ssh -o StrictHostKeyChecking=no -l ec2-user -i ${var.aws_ssh_private_key_file_path}" "${aws_eip.lh_aws_eip_controlplane[0].public_ip}:/etc/rancher/k3s/k3s.yaml" . && \
    sed -i "s#https://$LOCAL_IP:6443#https://$K3S_SERVER_IP:6443#" k3s.yaml
EOT
  }
}

# Download KUBECONFIG file for rke2
resource "null_resource" "rsync_kubeconfig_file_rke2" {

  count = var.k8s_distro_name == "rke2" ? 1 : 0

  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  provisioner "remote-exec" {
    inline = ["RETRY=0; MAX_RETRY=450; until([ -f /etc/rancher/rke2/rke2.yaml ] && [ `sudo KUBECONFIG=/etc/rancher/rke2/rke2.yaml /var/lib/rancher/rke2/bin/kubectl get node -o jsonpath='{.items[*].status.conditions}'  | jq '.[] | select(.type  == \"Ready\").status' | grep -ci true` -eq $((${var.lh_aws_instance_count_controlplane} + ${var.lh_aws_instance_count_worker})) ]); do echo \"waiting for rke2 cluster nodes to be running\"; sleep 2; if [ $RETRY -eq $MAX_RETRY ]; then break; fi; RETRY=$((RETRY+1)); done"]


    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = <<EOT
    export RKE2_SERVER_IP=$(
        [ "${var.network_stack}" = "ipv6" ] && echo "[${aws_instance.lh_aws_instance_controlplane[0].ipv6_addresses[0]}]" || echo ${aws_eip.lh_aws_eip_controlplane[0].public_ip}
    )
    export LOCAL_IP=$(
        [ "${var.network_stack}" = "ipv6" ] && echo "\[::1\]" || echo "127.0.0.1"
    )
    rsync -aPvz --rsync-path="sudo rsync" -e "ssh -o StrictHostKeyChecking=no -l ec2-user -i ${var.aws_ssh_private_key_file_path}" "${aws_eip.lh_aws_eip_controlplane[0].public_ip}:/etc/rancher/rke2/rke2.yaml" . && \
    sed -i "s#https://$LOCAL_IP:6443#https://$RKE2_SERVER_IP:6443#" rke2.yaml
EOT
  }
}
