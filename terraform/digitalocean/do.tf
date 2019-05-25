variable "do_token" {}
variable "tf_workspace" {}

provider "digitalocean" {
  token = "${var.do_token}"
}

resource "digitalocean_ssh_key" "do-ssh-key" {
  name = "longhorn-test-ssh-key"
  public_key = "${file("~/.ssh/id_rsa.pub")}"
}

resource "digitalocean_droplet" "longhorn-tests-controller" {
  image    = "ubuntu-18-04-x64"
  name     = "longhorn-tests-01"
  region   = "nyc3"
  size     = "s-2vcpu-4gb"
  ssh_keys = ["${digitalocean_ssh_key.do-ssh-key.fingerprint}"]
  tags     = ["longhorn-tests", "DoNotDelete", "k8s-controller"]

  provisioner "remote-exec" {
    connection {
      host         = "${digitalocean_droplet.longhorn-tests-controller.ipv4_address}"
      type         = "ssh"
      user         = "root"
      private_key  = "${file("~/.ssh/id_rsa")}"
    }

    scripts = [
      "${var.tf_workspace}/scripts/provision.sh"
    ]
  }

}

resource "digitalocean_droplet" "longhorn-tests-worker-1" {
  image    = "ubuntu-18-04-x64"
  name     = "longhorn-tests-02"
  region   = "nyc3"
  size     = "s-2vcpu-4gb"
  ssh_keys = ["${digitalocean_ssh_key.do-ssh-key.fingerprint}"]
  tags     = ["longhorn-tests", "DoNotDelete", "k8s-worker"]

  provisioner "remote-exec" {
    connection {
      host         = "${digitalocean_droplet.longhorn-tests-worker-1.ipv4_address}"
      type         = "ssh"
      user         = "root"
      private_key  = "${file("~/.ssh/id_rsa")}"
    }

    scripts = [
      "${var.tf_workspace}/scripts/provision.sh"
    ]
  }

}

resource "digitalocean_droplet" "longhorn-tests-worker-2" {
  image    = "ubuntu-18-04-x64"
  name     = "longhorn-tests-03"
  region   = "nyc3"
  size     = "s-2vcpu-4gb"
  ssh_keys = ["${digitalocean_ssh_key.do-ssh-key.fingerprint}"]
  tags     = ["longhorn-tests", "DoNotDelete", "k8s-worker"]

  provisioner "remote-exec" {
    connection {
      host         = "${digitalocean_droplet.longhorn-tests-worker-2.ipv4_address}"
      type         = "ssh"
      user         = "root"
      private_key  = "${file("~/.ssh/id_rsa")}"
    }

    scripts = [
      "${var.tf_workspace}/scripts/provision.sh" 
    ]
  }

}

output "k8s-controller" {
  value = "${digitalocean_droplet.longhorn-tests-controller.ipv4_address}"
}

output "k8s-worker-1" {
  value = "${digitalocean_droplet.longhorn-tests-worker-1.ipv4_address}"
}

output "k8s-worker-2" {
  value = "${digitalocean_droplet.longhorn-tests-worker-2.ipv4_address}"
}
