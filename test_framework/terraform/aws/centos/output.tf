# Generate RKE config file (for amd64 only)
output "rke_config" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane_rke,
    aws_instance.lh_aws_instance_worker_rke,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc_rke,
    null_resource.wait_for_docker_start_controlplane,
    null_resource.wait_for_docker_start_worker
  ]

  value = var.k8s_distro_name == "rke" ? yamlencode({
    "kubernetes_version": var.k8s_distro_version,
    "nodes": concat(
     [
      for controlplane_instance in aws_instance.lh_aws_instance_controlplane_rke : {
           "address": controlplane_instance.public_ip,
           "hostname_override": controlplane_instance.tags.Name,
           "user": "centos",
           "role": ["controlplane","etcd"]
          }

     ],
     [
      for worker_instance in aws_instance.lh_aws_instance_worker_rke : {
           "address": worker_instance.private_ip,
           "hostname_override": worker_instance.tags.Name,
           "user": "centos",
           "role": ["worker"]
         }
     ]
    ),
    "bastion_host": {
      "address": aws_eip.lh_aws_eip_controlplane[0].public_ip
      "user": "centos"
      "port":  22
      "ssh_key_path": var.aws_ssh_private_key_file_path
    }
  }) : null
}

output "load_balancer_url" {
  depends_on = [
    aws_lb.lh_aws_lb
  ]

  value = var.create_load_balancer ? aws_lb.lh_aws_lb[0].dns_name : null
}
