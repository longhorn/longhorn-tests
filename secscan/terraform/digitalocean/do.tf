variable "do_token" {
	type = string
}

variable "do_region" {
	type = string
}

variable "hostname_prefix" {
	type = string
}

variable "instance_count" {
	type = number
}

variable "instance_type" {
	type = string
}

variable "tf_workspace" {
	type = string
}

variable "SEVERITY" {
	type = string
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_ssh_key" "do-ssh-key" {
  name = "longhorn-secscan-ssh-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

resource "digitalocean_droplet" "longhorn-tests" {
  count    = var.instance_count
  image    = "ubuntu-20-04-x64"
  name     = "${var.hostname_prefix}-0${count.index}"
  region   = "nyc3"
  size     = "s-4vcpu-8gb"
  ssh_keys = [digitalocean_ssh_key.do-ssh-key.fingerprint]
  tags     = ["longhorn-secscan", "DoNotDelete"]
  user_data = "apt-get update -y && apt-get dist-upgrade -yyq"

}


resource "null_resource" "provision" {
  count = var.instance_count

  provisioner "remote-exec" {
    connection {
      host         = element(digitalocean_droplet.longhorn-tests.*.ipv4_address, count.index)
      type         = "ssh"
      user         = "root"
      private_key  = file("~/.ssh/id_rsa")
    }

    scripts = [
      "${var.tf_workspace}/scripts/provision.sh",
    ]
  }

  provisioner "file" {
     connection {
      host         = element(digitalocean_droplet.longhorn-tests.*.ipv4_address, count.index)
      type         = "ssh"
      user         = "root"
      private_key  = file("~/.ssh/id_rsa")
    }

    source      = "${var.tf_workspace}/scripts/secscan.sh"
    destination = "/tmp/secscan.sh"
  }

  provisioner "remote-exec" {
     connection {
      host         = element(digitalocean_droplet.longhorn-tests.*.ipv4_address, count.index)
      type         = "ssh"
      user         = "root"
      private_key  = file("~/.ssh/id_rsa")
    }
   
    inline = [
      "chmod +x /tmp/secscan.sh",
      "/tmp/secscan.sh ${var.SEVERITY}",
    ]
  }

  provisioner "local-exec" {
    working_dir = var.tf_workspace
    command = "rsync -aPvz -e 'ssh -l root -o StrictHostKeyChecking=no' --exclude .cache ${element(digitalocean_droplet.longhorn-tests.*.ipv4_address, count.index)}:/junit-reports ."
  }
}
