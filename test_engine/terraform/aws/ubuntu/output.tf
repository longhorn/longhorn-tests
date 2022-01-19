output "config" {
  depends_on = [
    aws_instance.build_engine_aws_instance,
    aws_eip.build_engine_aws_eip_controlplane,
    aws_eip_association.build_engine_aws_eip_assoc,
    null_resource.wait_for_docker_start
  ]

  value = yamlencode({
    "nodes": concat(
     [
      for controlplane_instance in aws_instance.build_engine_aws_instance : {
           "address": controlplane_instance.public_ip,
           "hostname_override": controlplane_instance.tags.Name,
           "user": "ubuntu",
          }
     ]
    ),
  })
}
