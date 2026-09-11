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

output "controlplane_public_ip" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane
  ]
  value = aws_instance.lh_aws_instance_controlplane[0].public_ip
}

output "resource_suffix" {
  depends_on = [
    random_string.random_suffix
  ]

  value = random_string.random_suffix.id
}
