# Create controlplane instances for k3s
resource "aws_instance" "lh_aws_instance_controlplane_k3s" {
 depends_on = [
    aws_subnet.lh_aws_public_subnet,
  ]

  count = var.k8s_distro_name == "k3s" ? var.lh_aws_instance_count_controlplane : 0

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_sles.id
  instance_type = var.lh_aws_instance_type_controlplane

  subnet_id = aws_subnet.lh_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp_controlplane.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh_aws_instance_root_block_device_size_controlplane
  }

  key_name = aws_key_pair.lh_aws_pair_key.key_name

  user_data = data.template_file.provision_k3s_server.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

# Create worker instances for k3s
resource "aws_instance" "lh_aws_instance_worker_k3s" {
  depends_on = [
    aws_route_table_association.lh_aws_private_subnet_rt_association,
    aws_instance.lh_aws_instance_controlplane_k3s
  ]

  count = var.k8s_distro_name == "k3s" ? var.lh_aws_instance_count_worker : 0

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_sles.id
  instance_type = var.lh_aws_instance_type_worker

  subnet_id = aws_subnet.lh_aws_private_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp_worker.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh_aws_instance_root_block_device_size_worker
  } 

  key_name = aws_key_pair.lh_aws_pair_key.key_name

  user_data = data.template_file.provision_k3s_agent.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "aws_volume_attachment" "lh_aws_hdd_volume_att_k3s" {

  count = var.use_hdd && var.k8s_distro_name == "k3s" ? var.lh_aws_instance_count_worker : 0

  device_name  = "/dev/xvdh"
  volume_id    = aws_ebs_volume.lh_aws_hdd_volume[count.index].id
  instance_id  = aws_instance.lh_aws_instance_worker_k3s[count.index].id
  force_detach = true
}

resource "aws_lb_target_group_attachment" "lh_aws_lb_tg_443_attachment_k3s" {

  depends_on = [
    aws_lb_target_group.lh_aws_lb_tg_443,
    aws_instance.lh_aws_instance_worker_k3s
  ]

  count            = var.create_load_balancer ? length(aws_instance.lh_aws_instance_worker_k3s) : 0
  target_group_arn = aws_lb_target_group.lh_aws_lb_tg_443[0].arn
  target_id        = aws_instance.lh_aws_instance_worker_k3s[count.index].id
}

# Associate every EIP with controlplane instance
resource "aws_eip_association" "lh_aws_eip_assoc_k3s" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane_k3s,
    aws_eip.lh_aws_eip_controlplane
  ]

  count = var.k8s_distro_name == "k3s" ? var.lh_aws_instance_count_controlplane : 0

  instance_id   = element(aws_instance.lh_aws_instance_controlplane_k3s, count.index).id
  allocation_id = element(aws_eip.lh_aws_eip_controlplane, count.index).id
}

# Download KUBECONFIG file for k3s
resource "null_resource" "rsync_kubeconfig_file" {
  count = var.k8s_distro_name == "k3s" ? 1 : 0

  depends_on = [
    aws_instance.lh_aws_instance_controlplane_k3s,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc_k3s
  ]

  provisioner "remote-exec" {

    inline = [
      "cloud-init status --wait",
      "if [ \"`cloud-init status | grep error`\" ]; then sudo cat /var/log/cloud-init-output.log; fi",
      "RETRY=0; MAX_RETRY=450; until([ -f /etc/rancher/k3s/k3s.yaml ] && [ `sudo /usr/local/bin/kubectl get node -o jsonpath='{.items[*].status.conditions}'  | jq '.[] | select(.type  == \"Ready\").status' | grep -ci true` -eq $((${var.lh_aws_instance_count_controlplane} + ${var.lh_aws_instance_count_worker})) ]); do echo \"waiting for k3s cluster nodes to be running\"; sleep 2; if [ $RETRY -eq $MAX_RETRY ]; then break; fi; RETRY=$((RETRY+1)); done"
    ]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = "rsync -aPvz --rsync-path=\"sudo rsync\" -e \"ssh -o StrictHostKeyChecking=no -l ec2-user -i ${var.aws_ssh_private_key_file_path}\" ${aws_eip.lh_aws_eip_controlplane[0].public_ip}:/etc/rancher/k3s/k3s.yaml .  && sed -i 's#https://127.0.0.1:6443#https://${aws_eip.lh_aws_eip_controlplane[0].public_ip}:6443#' k3s.yaml"
  }
}
