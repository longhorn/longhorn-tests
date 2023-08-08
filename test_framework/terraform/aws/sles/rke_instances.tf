# Create controlplane instances for rke
resource "aws_instance" "lh_aws_instance_controlplane_rke" {
 depends_on = [
    aws_subnet.lh_aws_public_subnet,
  ]

  count = var.k8s_distro_name == "rke" ? var.lh_aws_instance_count_controlplane : 0

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

  user_data = file("${path.module}/user-data-scripts/provision_rke.sh")

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = "longhorn-infra"
  }
}

# wait for docker to start on controlplane instances for rke
resource "null_resource" "wait_for_docker_start_controlplane" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane_rke,
    aws_instance.lh_aws_instance_worker_rke,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc_rke
  ]

  count = var.k8s_distro_name == "rke" ? var.lh_aws_instance_count_controlplane : 0

  provisioner "remote-exec" {

    inline = ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = element(aws_eip.lh_aws_eip_controlplane, count.index).public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}

# Create worker instances for rke
resource "aws_instance" "lh_aws_instance_worker_rke" {
  depends_on = [
    aws_route_table_association.lh_aws_private_subnet_rt_association,
    aws_instance.lh_aws_instance_controlplane_rke
  ]

  count = var.k8s_distro_name == "rke" ? var.lh_aws_instance_count_worker : 0

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

  user_data = file("${path.module}/user-data-scripts/provision_rke.sh")

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = "longhorn-infra"
  }
}

resource "aws_volume_attachment" "lh_aws_hdd_volume_att_rke" {

  count = var.use_hdd && var.k8s_distro_name == "rke" ? var.lh_aws_instance_count_worker : 0

  device_name  = "/dev/xvdh"
  volume_id    = aws_ebs_volume.lh_aws_hdd_volume[count.index].id
  instance_id  = aws_instance.lh_aws_instance_worker_rke[count.index].id
  force_detach = true
}

resource "aws_lb_target_group_attachment" "lh_aws_lb_tg_443_attachment_rke" {

  depends_on = [
    aws_lb_target_group.lh_aws_lb_tg_443,
    aws_instance.lh_aws_instance_worker_rke
  ]

  count            = var.create_load_balancer ? length(aws_instance.lh_aws_instance_worker_rke) : 0
  target_group_arn = aws_lb_target_group.lh_aws_lb_tg_443[0].arn
  target_id        = aws_instance.lh_aws_instance_worker_rke[count.index].id
}

# Associate every EIP with controlplane instance 
resource "aws_eip_association" "lh_aws_eip_assoc_rke" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane_rke,
    aws_eip.lh_aws_eip_controlplane
  ]

  count = var.k8s_distro_name == "rke" ? var.lh_aws_instance_count_controlplane : 0

  instance_id   = element(aws_instance.lh_aws_instance_controlplane_rke, count.index).id
  allocation_id = element(aws_eip.lh_aws_eip_controlplane, count.index).id
}


# wait for docker to start on worker instances (for rke on rke only)
resource "null_resource" "wait_for_docker_start_worker" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane_rke,
    aws_instance.lh_aws_instance_worker_rke,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc_rke
  ]

  count = var.k8s_distro_name == "rke" ? var.lh_aws_instance_count_worker : 0 

  provisioner "remote-exec" {
    inline = ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = element(aws_instance.lh_aws_instance_worker_rke, count.index).private_ip
      private_key = file(var.aws_ssh_private_key_file_path)
      bastion_user     = "ec2-user"
      bastion_host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      bastion_private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}
