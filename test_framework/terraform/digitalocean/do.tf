variable "do_token" {}
variable "tf_workspace" {}

provider "digitalocean" {
  token = "${var.do_token}"
}

resource "digitalocean_ssh_key" "do-ssh-key" {
  name = "longhorn-test-ssh-key"
  public_key = "${file("~/.ssh/id_rsa.pub")}"
}

resource "digitalocean_droplet" "longhorn-tests" {
  count    = 4
  image    = "ubuntu-18-04-x64"
  name     = "longhorn-tests-0${count.index}"
  region   = "nyc3"
  size     = "s-2vcpu-4gb"
  ssh_keys = ["${digitalocean_ssh_key.do-ssh-key.fingerprint}"]
  tags     = ["longhorn-tests", "k8s-controller"]

}


resource "null_resource" "provision" {
  count = 4

  provisioner "remote-exec" {
    connection {
      host         = "${element(digitalocean_droplet.longhorn-tests.*.ipv4_address, count.index)}"
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
  value = "${element(digitalocean_droplet.longhorn-tests.*.ipv4_address, 0)}"
}

output "k8s-worker-1" {
  value = "${element(digitalocean_droplet.longhorn-tests.*.ipv4_address, 1)}"
}

output "k8s-worker-2" {
  value = "${element(digitalocean_droplet.longhorn-tests.*.ipv4_address, 2)}"
}

output "k8s-worker-3" {
  value = "${element(digitalocean_droplet.longhorn-tests.*.ipv4_address, 3)}"
}
