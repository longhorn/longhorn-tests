provider "aws" {
  region = var.aws_region
  access_key = var.lh_aws_access_key
  secret_key = var.lh_aws_secret_key
}

# Create a random string suffix for instance names
resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

# Create a VPC
resource "aws_vpc" "lh-secscan_aws_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "${var.lh-secscan_aws_vpc_name}-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create internet gateway
resource "aws_internet_gateway" "lh-secscan_aws_igw" {
  vpc_id = aws_vpc.lh-secscan_aws_vpc.id

  tags = {
    Name = "lh-secscan_igw-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create secscan security group
resource "aws_security_group" "lh-secscan_aws_secgrp" {
  name        = "lh-secscan_aws_secgrp"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.lh-secscan_aws_vpc.id

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lh-secscan_aws_sec_grp_secscan-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create Public subnet
resource "aws_subnet" "lh-secscan_aws_public_subnet" {
  vpc_id     = aws_vpc.lh-secscan_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "lh-secscan_public_subnet-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create route table for public subnets
resource "aws_route_table" "lh-secscan_aws_public_rt" {
  depends_on = [
    aws_internet_gateway.lh-secscan_aws_igw,
  ]

  vpc_id = aws_vpc.lh-secscan_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lh-secscan_aws_igw.id
  }

  tags = {
    Name = "lh-secscan_aws_public_rt-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Assciate public subnet to public route table
resource "aws_route_table_association" "lh-secscan_aws_public_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh-secscan_aws_public_subnet,
    aws_route_table.lh-secscan_aws_public_rt
  ]

  subnet_id      = aws_subnet.lh-secscan_aws_public_subnet.id
  route_table_id = aws_route_table.lh-secscan_aws_public_rt.id
}

# Create AWS key pair
resource "aws_key_pair" "lh-secscan_aws_pair_key" {
  key_name   = format("%s_%s", "lh-secscan_aws_key_pair", "${random_string.random_suffix.id}")
  public_key = file(var.aws_ssh_public_key_file_path)

  tags = {
    Name = "lh-secscan_aws_key_pair-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create aws instance
resource "aws_instance" "lh-secscan_aws_instance" {
 depends_on = [
    aws_subnet.lh-secscan_aws_public_subnet,
  ]

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_ubuntu.id
  instance_type = var.lh-secscan_aws_instance_type

  subnet_id = aws_subnet.lh-secscan_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh-secscan_aws_secgrp.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh-secscan_aws_instance_root_block_device_size
  }

  key_name = aws_key_pair.lh-secscan_aws_pair_key.key_name
  user_data = file("${path.module}/user-data-scripts/provision.sh")

  tags = {
    Name = "${var.lh-secscan_aws_instance_name}-${random_string.random_suffix.id}"
    DoNotDelete	= "true"
    Owner = "longhorn-infra"
  }
}

resource "aws_eip" "lh-secscan_aws_eip_secscan" {
  vpc      = true

  tags = {
    Name = "lh-secscan_aws_eip-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Associate every EIP with secscan instance
resource "aws_eip_association" "lh-secscan_aws_eip_assoc" {
  depends_on = [
    aws_instance.lh-secscan_aws_instance,
    aws_eip.lh-secscan_aws_eip_secscan
  ]

  instance_id   = aws_instance.lh-secscan_aws_instance.id
  allocation_id = aws_eip.lh-secscan_aws_eip_secscan.id
}

# wait for docker to start on instances (for rke on amd64 only)
resource "null_resource" "wait_for_docker_start" {
  depends_on = [
    aws_instance.lh-secscan_aws_instance,
    aws_eip.lh-secscan_aws_eip_secscan,
    aws_eip_association.lh-secscan_aws_eip_assoc
  ]

  provisioner "remote-exec" {
    inline = ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"]

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = aws_eip.lh-secscan_aws_eip_secscan.public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}

resource "null_resource" "secscan" {
  depends_on = [
    aws_instance.lh-secscan_aws_instance,
    aws_eip.lh-secscan_aws_eip_secscan,
    aws_eip_association.lh-secscan_aws_eip_assoc,
    null_resource.wait_for_docker_start
  ]

  provisioner "file" {
    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = aws_eip.lh-secscan_aws_eip_secscan.public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }

    source      = "${var.tf_workspace}/scripts/secscan.sh"
    destination = "/home/ubuntu/secscan.sh"
  }

  provisioner "remote-exec" {
    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = aws_eip.lh-secscan_aws_eip_secscan.public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }

    inline = [
      "chmod +x /home/ubuntu/secscan.sh",
      "sudo /home/ubuntu/secscan.sh \"${var.severity}\"",
    ]
  }

  provisioner "local-exec" {
    working_dir = var.tf_workspace
    command = "rsync -aPvz -e 'ssh -l ubuntu -o StrictHostKeyChecking=no' --exclude .cache ${aws_eip.lh-secscan_aws_eip_secscan.public_ip}:/junit-reports ."
  }
}
