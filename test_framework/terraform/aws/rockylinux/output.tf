output "load_balancer_url" {
  depends_on = [
    aws_lb.lh_aws_lb
  ]

  value = var.create_load_balancer ? aws_lb.lh_aws_lb[0].dns_name : null
}

output "instance_mapping" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_instance.lh_aws_instance_worker,
  ]

  value = jsonencode(
    concat(
     [
      for controlplane_instance in aws_instance.lh_aws_instance_controlplane : {
           "name": controlplane_instance.private_dns,
           "id": controlplane_instance.id
          }

     ],
     [
      for worker_instance in aws_instance.lh_aws_instance_worker : {
           "name": worker_instance.private_dns,
           "id": worker_instance.id
         }
     ]
    )
  )
}

output "public_ip_mapping" {
  value = jsonencode(
    concat(
      [
        for controlplane_instance in aws_instance.lh_aws_instance_controlplane : {
          "name" = controlplane_instance.private_dns,
          "ip"   = controlplane_instance.public_ip
        }
      ],
      [
        for worker_instance in aws_instance.lh_aws_instance_worker : {
          "name" = worker_instance.private_dns,
          "ip"   = worker_instance.public_ip
        }
      ]
    )
  )
}

output "controlplane_public_ip" {
  depends_on = [
    aws_eip.lh_aws_eip_controlplane
  ]
  value = aws_eip.lh_aws_eip_controlplane[0].public_ip
}

output "resource_suffix" {
  depends_on = [
    random_string.random_suffix
  ]

  value = random_string.random_suffix.id
}