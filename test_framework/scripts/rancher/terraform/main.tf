terraform {
  required_providers {
    rancher2 = {
      source  = "rancher/rancher2"
      version = "~> 1.24"
    }
  }
}

provider "rancher2" {
  api_url   = var.api_url
  insecure  = true
  access_key = var.access_key
  secret_key = var.secret_key
}

resource "rancher2_catalog_v2" "longhorn_repo" {
  cluster_id = "local"
  name = "longhorn-repo"
  git_repo = var.rancher_chart_git_repo
  git_branch = var.rancher_chart_git_branch
}

resource "rancher2_app_v2" "longhorn_app" {
  cluster_id = "local"
  name = "longhorn-app"
  namespace = "longhorn-system"
  repo_name = "longhorn-repo"
  chart_name = "longhorn"
  chart_version = var.rancher_chart_install_version
  values = <<-EOF
privateRegistry:
  createSecret: true
  registryUrl: ${var.registry_url}
  registryUser: ${var.registry_user}
  registryPasswd: ${var.registry_passwd}
  registrySecret: ${var.registry_secret}
image:
  csi:
    attacher:
      repository: longhornio/csi-attacher
    nodeDriverRegistrar:
      repository: longhornio/csi-node-driver-registrar
    provisioner:
      repository: longhornio/csi-provisioner
    resizer:
      repository: longhornio/csi-resizer
    snapshotter:
      repository: longhornio/csi-snapshotter
  longhorn:
    backingImageManager:
      repository: longhornio/backing-image-manager
    engine:
      repository: longhornio/longhorn-engine
    instanceManager:
      repository: longhornio/longhorn-instance-manager
    manager:
      repository: longhornio/longhorn-manager
    shareManager:
      repository: longhornio/longhorn-share-manager
    ui:
      repository: longhornio/longhorn-ui
EOF
  wait = true
}