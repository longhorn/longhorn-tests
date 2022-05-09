# Create controlplane instances for rke2
resource "aws_instance" "lh_aws_instance_controlplane_rke2" {
 depends_on = [
    aws_subnet.lh_aws_public_subnet,
  ]

  count = var.k8s_distro_name == "rke2" ? var.lh_aws_instance_count_controlplane : 0

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_rhel.id
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

  user_data = data.template_file.provision_rke2_server.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = "longhorn-infra"
  }
}

# Create worker instances for rke2
resource "aws_instance" "lh_aws_instance_worker_rke2" {
  depends_on = [
    aws_internet_gateway.lh_aws_igw,
    aws_subnet.lh_aws_private_subnet,
    aws_instance.lh_aws_instance_controlplane_rke2
  ]

  count = var.k8s_distro_name == "rke2" ? var.lh_aws_instance_count_worker : 0

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_rhel.id
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

  user_data = data.template_file.provision_rke2_agent.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = "longhorn-infra"
  }
} 

# Associate every EIP with controlplane instance
resource "aws_eip_association" "lh_aws_eip_assoc_rke2" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane_rke2,
    aws_eip.lh_aws_eip_controlplane
  ]

  count = var.k8s_distro_name == "rke2" ? var.lh_aws_instance_count_controlplane : 0

  instance_id   = element(aws_instance.lh_aws_instance_controlplane_rke2, count.index).id
  allocation_id = element(aws_eip.lh_aws_eip_controlplane, count.index).id
}

# Download KUBECONFIG file for rke2
resource "null_resource" "rsync_kubeconfig_file_rke2" {
  count = var.k8s_distro_name == "rke2" ? 1 : 0

  depends_on = [
    aws_instance.lh_aws_instance_controlplane_rke2,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc_rke2
  ]

  provisioner "remote-exec" {
    inline = ["until([ -f /etc/rancher/rke2/rke2.yaml ] && [ `sudo KUBECONFIG=/etc/rancher/rke2/rke2.yaml /var/lib/rancher/rke2/bin/kubectl get node -o jsonpath='{.items[*].status.conditions}'  | jq '.[] | select(.type  == \"Ready\").status' | grep -ci true` -eq $((${var.lh_aws_instance_count_controlplane} + ${var.lh_aws_instance_count_worker})) ]); do echo \"waiting for rke2 cluster nodes to be running\"; sleep 2; done"]


    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = "rsync -aPvz --rsync-path=\"sudo rsync\" -e \"ssh -o StrictHostKeyChecking=no -l ec2-user -i ${var.aws_ssh_private_key_file_path}\" ${aws_eip.lh_aws_eip_controlplane[0].public_ip}:/etc/rancher/rke2/rke2.yaml .  && sed -i 's#https://127.0.0.1:6443#https://${aws_eip.lh_aws_eip_controlplane[0].public_ip}:6443#' rke2.yaml" 
  }
}
