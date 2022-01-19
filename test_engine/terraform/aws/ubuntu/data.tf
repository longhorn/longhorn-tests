# Query AWS for Ubuntu AMI
data "aws_ami" "aws_ami_ubuntu" {
  most_recent      = true
  owners           = [var.aws_ami_ubuntu_account_number]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu*${var.distro_version}-${var.build_engine_arch}-server-*"]
  }
}
