# Generate RKE config file (for amd64 only)
output "rke_config" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_instance.lh_aws_instance_worker,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc,
    null_resource.wait_for_docker_start_controlplane,
    null_resource.wait_for_docker_start_worker
  ]

  value = var.k8s_distro_name == "rke" ? yamlencode({
    "kubernetes_version": var.k8s_distro_version,
    "nodes": concat(
     [
      for controlplane_instance in aws_instance.lh_aws_instance_controlplane : {
           "address": controlplane_instance.public_ip,
           "hostname_override": controlplane_instance.tags.Name,
           "user": "rocky",
           "role": ["controlplane","etcd"]
          }

     ],
     [
      for worker_instance in aws_instance.lh_aws_instance_worker : {
           "address": worker_instance.private_ip,
           "hostname_override": worker_instance.tags.Name,
           "user": "rocky",
           "role": ["worker"]
         }
     ]
    ),
    "bastion_host": {
      "address": aws_eip.lh_aws_eip_controlplane[0].public_ip
      "user": "rocky"
      "port":  22
      "ssh_key_path": var.aws_ssh_private_key_file_path
    }
  }) : null
}
