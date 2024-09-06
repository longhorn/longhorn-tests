data "aws_ami" "talos" {
  most_recent = true
  filter {
    name   = "name"
    values = ["talos-v${var.os_distro_version}-${var.arch}"]
  }
  owners = [var.aws_ami_talos_account_number]
}
