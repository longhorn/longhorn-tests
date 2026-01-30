output "network_interface_ids" {
  depends_on = [
    aws_network_interface.instance_eth0,
    aws_network_interface.instance_eth1
  ]
  value = join(" ", concat(aws_network_interface.instance_eth0[*].id, aws_network_interface.instance_eth1[*].id))
}

output "instance_mapping" {
  value = jsonencode(
    concat(
      [
        for instance in aws_instance.aws_instance : {
          "name" = instance.private_dns,
          "id"   = instance.id
        }
      ]
    )
  )
}

output "controlplane_public_ip" {
  depends_on = [
    aws_eip.aws_eip,
    aws_instance.aws_instance
  ]
  value = var.network_stack == "ipv6" ? "[${aws_instance.aws_instance[0].ipv6_addresses[0]}]" : aws_eip.aws_eip[0].public_ip
}
