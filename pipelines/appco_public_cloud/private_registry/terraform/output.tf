output "registry_url" {

  depends_on = [
    null_resource.post_setup
  ]

  value = aws_route53_record.lh_registry.fqdn
}

output "registry_username" {
  value = local.registry_username
}

output "registry_password" {
  value = local.registry_password
}
