data "template_file" "kubeconfig_template" {
  depends_on = [
    aws_eks_cluster.eks_cluster,
    data.aws_eks_cluster_auth.eks_cluster_auth
  ]
  template = file("${path.module}/kubeconfig.tpl")
  vars = {
    cluster_ca_certificate = aws_eks_cluster.eks_cluster.certificate_authority[0].data
    endpoint = aws_eks_cluster.eks_cluster.endpoint
    context =  data.aws_eks_cluster_auth.eks_cluster_auth.name
    token = data.aws_eks_cluster_auth.eks_cluster_auth.token
  }
}