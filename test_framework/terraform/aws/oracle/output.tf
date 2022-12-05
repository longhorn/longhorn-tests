output "load_balancer_url" {
  depends_on = [
    aws_lb.lh_aws_lb
  ]

  value = var.create_load_balancer ? aws_lb.lh_aws_lb[0].dns_name : null
}
